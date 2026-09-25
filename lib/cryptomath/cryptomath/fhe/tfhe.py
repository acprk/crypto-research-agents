# TOY: not secure
"""Toy TFHE / CGGI over the discretised torus Z_{2^32}.

Implements LWE, GLWE and GGSW encryption, signed gadget decomposition,
external product, CMux, blind rotation, sample extraction, LWE key
switching and programmable bootstrapping (PBS) with an arbitrary look-up
table f : Z_p -> Z_p (one bit of padding, message encoded as m * q/(2p)).

Small default parameters (n=32, N=512, k=1) run a PBS in a few tens of ms
with numpy int64 negacyclic convolutions.  Noise is set tiny: the goal is
to exercise the algorithms and noise formulas, not security.

References
----------
* I. Chillotti, N. Gama, M. Georgieva, M. Izabachène, "TFHE: fast fully
  homomorphic encryption over the torus", J. Cryptology 33, 2020,
  ePrint 2018/421.
* I. Chillotti, M. Joye, P. Paillier, "Programmable bootstrapping enables
  efficient homomorphic inference of deep neural networks", CSCML 2021,
  ePrint 2021/091.
* L. Ducas, D. Micciancio, "FHEW: bootstrapping homomorphic encryption in
  less than a second", EUROCRYPT 2015, ePrint 2014/816.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

import numpy as np

from ..costmodel.counter import CMUX, EXTPROD, KS, PBS, count

__all__ = ["TFHEParams", "TFHE", "Q_BITS", "Q", "torus_mod", "poly_mul_xk",
           "negacyclic_mul_int", "gadget_decompose", "encode", "decode"]

Q_BITS = 32
Q = 1 << Q_BITS
MASK = Q - 1


def torus_mod(x):
    return np.asarray(x, dtype=np.int64) & MASK


def centered_torus(x):
    x = torus_mod(x)
    return np.where(x >= Q // 2, x - Q, x)


def encode(m: int, p: int) -> int:
    """m in [0, p) -> torus value m * q / (2p) (top bit = padding)."""
    return (m % p) * (Q // (2 * p))


def decode(phase: int, p: int) -> int:
    return int(round(int(phase) * 2 * p / Q)) % (2 * p)


def poly_mul_xk(a: np.ndarray, k: int) -> np.ndarray:
    """a * X^k in Z_q[X]/(X^N+1) (k any integer)."""
    N = a.shape[-1]
    k %= 2 * N
    neg = k >= N
    if neg:
        k -= N
    out = np.roll(a, k, axis=-1)
    out[..., :k] = -out[..., :k]
    if neg:
        out = -out
    return torus_mod(out)


def negacyclic_mul_int(small: np.ndarray, a: np.ndarray) -> np.ndarray:
    """small (signed ints, |.| < 2^12) times torus poly a, mod X^N+1, mod 2^32."""
    N = a.shape[-1]
    full = np.convolve(small.astype(np.int64), a.astype(np.int64))
    res = full[:N].copy()
    res[: N - 1] -= full[N:]
    return torus_mod(res)


def gadget_decompose(x: np.ndarray, base_bits: int, levels: int) -> np.ndarray:
    """Signed base-2^base_bits digits of round(x) (top levels*base_bits bits).

    Returns array of shape (levels,) + x.shape; digit j has weight q / B^{j+1}
    and lies in [-B/2, B/2).
    """
    x = torus_mod(x)
    total = base_bits * levels
    if total > Q_BITS:
        raise ValueError("levels * base_bits > 32")
    shift = Q_BITS - total
    xr = ((x + ((1 << shift) >> 1)) >> shift) if shift else x.copy()
    xr &= (1 << total) - 1
    B = 1 << base_bits
    digits = np.zeros((levels,) + x.shape, dtype=np.int64)
    carry = np.zeros_like(xr)
    for j in range(levels - 1, -1, -1):
        d = (xr & (B - 1)) + carry
        xr >>= base_bits
        carry = (d >= B // 2).astype(np.int64)
        digits[j] = d - carry * B
    return digits


@dataclass
class TFHEParams:
    n: int = 32            # LWE dimension
    N: int = 512           # ring dimension
    k: int = 1             # GLWE dimension
    bg_bits: int = 7       # PBS gadget base 2^bg_bits
    l: int = 3             # PBS gadget levels
    ks_bits: int = 4       # key-switch base 2^ks_bits
    ks_l: int = 5          # key-switch levels
    lwe_sigma: float = 2.0 ** -20   # std dev as a fraction of the torus
    glwe_sigma: float = 2.0 ** -28


class TFHE:
    """>>> tf = TFHE(seed=1); p = 8
    >>> ct = tf.encrypt(3, p); tf.decrypt(tf.pbs(ct, lambda m: (m * m) % p, p), p)
    1
    """

    def __init__(self, params: Optional[TFHEParams] = None, seed: Optional[int] = None):
        self.P = params or TFHEParams()
        self.rng = np.random.default_rng(seed)
        self.keygen()

    # ------------------------------------------------------------ sampling
    def _noise(self, shape, sigma: float) -> np.ndarray:
        return np.rint(self.rng.normal(0.0, sigma * Q, size=shape)).astype(np.int64)

    def _uniform(self, shape) -> np.ndarray:
        return self.rng.integers(0, Q, size=shape, dtype=np.int64)

    # ---------------------------------------------------------- primitives
    def lwe_encrypt(self, mu: int, s: np.ndarray, sigma: Optional[float] = None) -> Tuple[np.ndarray, int]:
        sigma = self.P.lwe_sigma if sigma is None else sigma
        a = self._uniform(len(s))
        b = int(torus_mod(int(np.dot(a, s) & MASK) + mu + int(self._noise((), sigma))))
        return a, b

    @staticmethod
    def lwe_phase(ct, s) -> int:
        a, b = ct
        return int((b - int(np.dot(a, s))) & MASK)

    def glwe_encrypt(self, M: np.ndarray, S: np.ndarray, sigma: Optional[float] = None) -> np.ndarray:
        """Returns array (k+1, N): rows A_1..A_k, B = sum A_i S_i + M + E."""
        sigma = self.P.glwe_sigma if sigma is None else sigma
        k, N = S.shape
        A = self._uniform((k, N))
        B = torus_mod(M + self._noise(N, sigma))
        for i in range(k):
            B = torus_mod(B + negacyclic_mul_int(S[i], A[i]))
        return np.vstack([A, B[None, :]])

    @staticmethod
    def glwe_phase(ct: np.ndarray, S: np.ndarray) -> np.ndarray:
        B = ct[-1].copy()
        for i in range(S.shape[0]):
            B = torus_mod(B - negacyclic_mul_int(S[i], ct[i]))
        return B

    def ggsw_encrypt(self, mu: int, S: np.ndarray) -> np.ndarray:
        """Array ((k+1)*l, k+1, N): row (i, j) = GLWE(0) + mu * q/B^{j+1} on component i."""
        P = self.P
        k, N = S.shape
        rows = []
        for i in range(k + 1):
            for j in range(P.l):
                c = self.glwe_encrypt(np.zeros(N, dtype=np.int64), S)
                g = 1 << (Q_BITS - P.bg_bits * (j + 1))
                c[i, 0] = (c[i, 0] + mu * g) & MASK
                rows.append(c)
        return np.array(rows)

    def external_product(self, C: np.ndarray, d: np.ndarray) -> np.ndarray:
        count(EXTPROD)
        P = self.P
        kp1, N = d.shape
        dec = gadget_decompose(d, P.bg_bits, P.l)  # (l, k+1, N)
        out = np.zeros((kp1, N), dtype=np.int64)
        for i in range(kp1):
            for j in range(P.l):
                row = C[i * P.l + j]
                dig = dec[j, i]
                for c in range(kp1):
                    out[c] = torus_mod(out[c] + negacyclic_mul_int(dig, row[c]))
        return out

    def cmux(self, C: np.ndarray, d0: np.ndarray, d1: np.ndarray) -> np.ndarray:
        count(CMUX)
        return torus_mod(d0 + self.external_product(C, torus_mod(d1 - d0)))

    @staticmethod
    def sample_extract(ct: np.ndarray, idx: int = 0) -> Tuple[np.ndarray, int]:
        """LWE encryption of coefficient idx of the GLWE plaintext, key = flattened S."""
        kp1, N = ct.shape
        a = []
        for i in range(kp1 - 1):
            A = ct[i]
            # coefficient idx of A*S: sum_j A_{idx-j} S_j with negacyclic sign
            ai = np.concatenate([A[idx::-1], -A[:idx:-1]])
            a.append(ai)
        return torus_mod(np.concatenate(a)), int(ct[-1, idx])

    # ---------------------------------------------------------------- keys
    def keygen(self):
        P = self.P
        self.s = self.rng.integers(0, 2, size=P.n, dtype=np.int64)
        self.S = self.rng.integers(0, 2, size=(P.k, P.N), dtype=np.int64)
        self.s_ext = self.S.reshape(-1)
        self.bsk = [self.ggsw_encrypt(int(si), self.S) for si in self.s]
        # key switching key: LWE_s(s_ext[i] * q / B^{j+1})
        kN = P.k * P.N
        self.ksk_a = self._uniform((kN, P.ks_l, P.n))
        noise = self._noise((kN, P.ks_l), P.lwe_sigma)
        g = np.array([1 << (Q_BITS - P.ks_bits * (j + 1)) for j in range(P.ks_l)], dtype=np.int64)
        dots = torus_mod(np.einsum("ijk,k->ij", self.ksk_a, self.s))
        self.ksk_b = torus_mod(dots + noise + self.s_ext[:, None] * g[None, :])

    # ------------------------------------------------------ user interface
    def encrypt(self, m: int, p: int) -> Tuple[np.ndarray, int]:
        return self.lwe_encrypt(encode(m, p), self.s)

    def decrypt(self, ct, p: int, key: Optional[np.ndarray] = None) -> int:
        return decode(self.lwe_phase(ct, self.s if key is None else key), p) % p

    def add(self, c1, c2):
        return torus_mod(c1[0] + c2[0]), int((c1[1] + c2[1]) & MASK)

    def keyswitch(self, ct) -> Tuple[np.ndarray, int]:
        count(KS)
        P = self.P
        a_big, b = ct
        D = gadget_decompose(a_big, P.ks_bits, P.ks_l).T  # (kN, ks_l)
        a = torus_mod(-np.einsum("ij,ijk->k", D, self.ksk_a))
        b = int(torus_mod(b - int(np.sum(D * self.ksk_b) & MASK)))
        return a, b

    def test_polynomial(self, f: Callable[[int], int], p: int) -> np.ndarray:
        N = self.P.N
        return np.array([encode(f(j * p // N), p) for j in range(N)], dtype=np.int64)

    def blind_rotate(self, ct, v: np.ndarray, offset: int = 0) -> np.ndarray:
        P = self.P
        a, b = ct
        twoN = 2 * P.N
        shift = Q_BITS - int(math.log2(twoN))
        a_t = ((a + (1 << (shift - 1))) >> shift) % twoN
        b_t = ((b + (1 << (shift - 1))) >> shift) % twoN
        acc = np.zeros((P.k + 1, P.N), dtype=np.int64)
        acc[-1] = poly_mul_xk(v, -(b_t + offset))
        for ai, C in zip(a_t, self.bsk):
            if ai == 0:
                continue
            acc = self.cmux(C, acc, poly_mul_xk(acc, int(ai)))
        return acc

    def pbs(self, ct, f: Callable[[int], int], p: int, keyswitch: bool = True):
        """Programmable bootstrap: returns LWE(f(m)) under s (or s_ext if keyswitch=False)."""
        count(PBS)
        v = self.test_polynomial(f, p)
        acc = self.blind_rotate(ct, v, offset=self.P.N // (2 * p))
        out = self.sample_extract(acc, 0)
        return self.keyswitch(out) if keyswitch else out
