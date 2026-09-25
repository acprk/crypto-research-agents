# TOY: not secure
"""S-box evaluation on toy-TFHE ciphertexts: three strategies (teaching example).

Strategies for a 4-bit S-box S : Z_16 -> Z_16 whose four output *bits* are needed
as separate ciphertexts (e.g. for a bit-sliced linear layer):

* ``perbit``  -- one programmable bootstrap (PBS) per output bit: 4 blind rotations.
* ``mvpbs``   -- multi-value PBS (Carpov-Izabachene-Mollimard, CT-RSA 2019,
                 ePrint 2018/622): ONE blind rotation of a common polynomial v0,
                 then one cheap plaintext-integer polynomial product per LUT,
                 using the factorisation  T_i(X) = v0(X) * d_i(X)  mod X^N+1.
* ``vpack``   -- CMux-tree / vertical packing of all 16x4 LUT entries into one
                 polynomial (TFHE JoC 2020, "LUT evaluation with CMux trees").
                 It consumes the 4 input bits as GGSW ciphertexts, i.e. a
                 DIFFERENT input format (see claim C5 in CLAIMS.md).

Factorisation used by ``mvpbs`` (derivation in THEORY.md, Lemma L1): let
t_j = Delta * f(floor(j p / N)) be the coefficients of the standard test
polynomial T_f (Delta = q/(2p)).  Then T_f * (1 - X) = Delta * d_f with the
*small integer* polynomial

    d_f[0] = f(0) + f(p-1),   d_f[k N/p] = f(k) - f(k-1)  (k = 1..p-1),  0 elsewhere,

and (1 - X)^{-1} = (1/2)(1 + X + ... + X^{N-1}) in Z[1/2][X]/(X^N+1), so
T_f = v0 * d_f with v0 = (Delta/2) * (1 + X + ... + X^{N-1}).  v0 does not depend
on f, so one blind rotation of v0 serves every LUT; multiplying the rotated
accumulator by d_f commutes with the rotation.  Noise cost: the blind-rotation
noise is multiplied by ||d_f||_2 (Theorem T1 in THEORY.md).
"""
from __future__ import annotations

import os
import sys
from typing import Callable, List, Sequence, Tuple

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
for sub in ("lib/cryptomath", "lib/bench"):
    p = os.path.join(REPO, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from cryptomath.fhe.tfhe import (TFHE, TFHEParams, Q, Q_BITS, encode, torus_mod,  # noqa: E402
                                 negacyclic_mul_int, poly_mul_xk)
from cryptomath.costmodel.counter import count, PBS, KS  # noqa: E402

# PRESENT S-box (Bogdanov et al., CHES 2007) -- public, used only as a toy LUT.
PRESENT_SBOX = [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]
P_IN = 16  # message space of the input nibble (one padding bit on top)

# Parameter sets (TOY, not secure).  T1 = library default (noise tiny);
# T2 = same except a much noisier bootstrapping key, chosen so that per-bit PBS
# almost never fails while the MV-PBS noise amplification becomes visible.
PARAMS = {
    "T1": TFHEParams(),
    "T2": TFHEParams(glwe_sigma=2.0 ** -22),
}


def bit_luts(sbox: Sequence[int] = PRESENT_SBOX, k: int = 4) -> List[Callable[[int], int]]:
    """The first k output-bit functions f_i(m) = bit i of S(m)."""
    return [(lambda m, i=i: (sbox[m % len(sbox)] >> i) & 1) for i in range(k)]


def luts(k: int, sbox: Sequence[int] = PRESENT_SBOX) -> List[Callable[[int], int]]:
    """k Boolean LUTs of the same nibble: the 4 S-box output bits, then (k > 4) extra
    pseudo-random Boolean tables (fixed seed) -- used only to probe amortisation (claim C3)."""
    fs = bit_luts(sbox, min(k, 4))
    rng = np.random.default_rng(12345)
    for _ in range(4, k):
        t = rng.integers(0, 2, size=16)
        fs.append(lambda m, t=t: int(t[m % 16]))
    return fs


# ----------------------------------------------------------------------------- MV-PBS
def v0_poly(N: int, p: int) -> np.ndarray:
    """Common factor v0 = (Delta/2) (1 + X + ... + X^{N-1}),  Delta = q/(2p)."""
    delta = Q // (2 * p)
    if delta % 2:
        raise ValueError("Delta must be even (q = 2^32, p <= 2^30)")
    return np.full(N, delta // 2, dtype=np.int64)


def d_poly(f: Callable[[int], int], N: int, p: int) -> np.ndarray:
    """Small integer polynomial d_f with T_f = v0 * d_f  (mod X^N+1, mod q)."""
    if N % p:
        raise ValueError("need p | N")
    w = N // p
    d = np.zeros(N, dtype=np.int64)
    d[0] = f(0) + f(p - 1)
    for k in range(1, p):
        d[k * w] = f(k) - f(k - 1)
    return d


def d_norm2(f: Callable[[int], int], N: int, p: int) -> int:
    d = d_poly(f, N, p)
    return int(np.dot(d, d))


def mv_pbs(tf: TFHE, ct, fs: Sequence[Callable[[int], int]], p: int = P_IN,
           keyswitch: bool = True) -> List[Tuple[np.ndarray, int]]:
    """Multi-value PBS: one blind rotation, len(fs) outputs."""
    count(PBS)  # one blind rotation (counted as one PBS-equivalent)
    N = tf.P.N
    acc = tf.blind_rotate(ct, v0_poly(N, p), offset=N // (2 * p))
    outs = []
    for f in fs:
        d = d_poly(f, N, p)
        acc_f = np.vstack([negacyclic_mul_int(d, acc[c]) for c in range(acc.shape[0])])
        o = tf.sample_extract(acc_f, 0)
        outs.append(tf.keyswitch(o) if keyswitch else o)
    return outs


def per_bit_pbs(tf: TFHE, ct, fs: Sequence[Callable[[int], int]], p: int = P_IN,
                keyswitch: bool = True) -> List[Tuple[np.ndarray, int]]:
    """Baseline: one full PBS per LUT."""
    return [tf.pbs(ct, f, p, keyswitch=keyswitch) for f in fs]


# ------------------------------------------------------- CMux tree / vertical packing
def vpack_encrypt_input(tf: TFHE, m: int, bits: int = 4) -> List[np.ndarray]:
    """GGSW encryptions of the input bits (client-side; a different input format!)."""
    return [tf.ggsw_encrypt((m >> j) & 1, tf.S) for j in range(bits)]


def vpack_lut_poly(tf: TFHE, sbox: Sequence[int], k: int, p: int = P_IN) -> np.ndarray:
    """Coefficient k*m + i = encode(bit_i(S(m)))  (all LUTs packed in one polynomial)."""
    N = tf.P.N
    if len(sbox) * k > N:
        raise ValueError("LUTs do not fit into one polynomial")
    L = np.zeros(N, dtype=np.int64)
    for m, y in enumerate(sbox):
        for i in range(k):
            L[k * m + i] = encode((y >> i) & 1, p)
    return L


def vpack_eval(tf: TFHE, ggsw_bits: Sequence[np.ndarray], sbox: Sequence[int] = PRESENT_SBOX,
               k: int = 4, p: int = P_IN, keyswitch: bool = True) -> List[Tuple[np.ndarray, int]]:
    """Rotate the packed LUT by X^{-k m} with one CMux per input bit, then extract."""
    N = tf.P.N
    acc = np.zeros((tf.P.k + 1, N), dtype=np.int64)
    acc[-1] = vpack_lut_poly(tf, sbox, k, p)
    for j, C in enumerate(ggsw_bits):
        acc = tf.cmux(C, acc, poly_mul_xk(acc, -k * (1 << j)))
    outs = []
    for i in range(k):
        o = tf.sample_extract(acc, i)
        outs.append(tf.keyswitch(o) if keyswitch else o)
    return outs


# ----------------------------------------------------------------------- helpers
def phase_error(tf: TFHE, ct, expected: int, p: int = P_IN, key=None) -> int:
    """Signed torus error (integer units of 2^-32) of ct w.r.t. encode(expected, p)."""
    ph = tf.lwe_phase(ct, tf.s if key is None else key)
    e = (ph - encode(expected, p)) & (Q - 1)
    return e - Q if e >= Q // 2 else e


def evaluate(method: str, tf: TFHE, m: int, k: int = 4, sbox=PRESENT_SBOX):
    """Encrypt m, evaluate the first k output bits with ``method``; return output cts."""
    fs = bit_luts(sbox, k)
    if method == "vpack":
        return vpack_eval(tf, vpack_encrypt_input(tf, m), sbox, k)
    ct = tf.encrypt(m, P_IN)
    if method == "perbit":
        return per_bit_pbs(tf, ct, fs)
    if method == "mvpbs":
        return mv_pbs(tf, ct, fs)
    raise ValueError(method)


if __name__ == "__main__":
    # self-check: exhaustive correctness at T1 for all three strategies
    tf = TFHE(PARAMS["T1"], seed=7)
    for method in ("perbit", "mvpbs", "vpack"):
        bad = 0
        for m in range(16):
            outs = evaluate(method, tf, m)
            got = sum(tf.decrypt(o, P_IN) << i for i, o in enumerate(outs))
            bad += got != PRESENT_SBOX[m]
        print(f"{method:7s}: {16 - bad}/16 inputs correct")
        assert bad == 0
    print("self-check OK")
