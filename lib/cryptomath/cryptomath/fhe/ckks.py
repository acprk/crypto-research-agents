# TOY: not secure
"""Toy CKKS (Cheon--Kim--Kim--Song, ASIACRYPT 2017, ePrint 2016/421).

* Canonical-embedding encode/decode of N/2 complex slots at the roots
  zeta^{5^j} (zeta = exp(i pi / N)), j < N/2, and their conjugates.
* Modulus chain q_0 (base, ~ q0_bits) and `levels` primes close to the scale
  Delta = 2^scale_bits; all primes = 1 mod 2N.
* add, plaintext/constant mul, ciphertext mul + relinearisation, rescale,
  rotations (sigma_{5^r}) and conjugation (sigma_{-1}) with hybrid key
  switching (base-w digits + special prime P, noise divided by P).
* Approximate error tracking: :meth:`CKKS.error` and :meth:`precision_bits`
  compare a decryption against the exact expected slot vector.
"""
from __future__ import annotations

import math
import random
from typing import Optional, Sequence

import numpy as np

from ..algebra.ntheory import find_ntt_primes
from ..algebra.poly import PolyRing, center
from ..costmodel.counter import CADD, CMULT, PMULT, RELIN, RESCALE, ROT, SMULT, count
from .rlwe import Ciphertext, apply_ksk, gen_ksk, small_poly

__all__ = ["CKKSEncoder", "CKKS"]


class CKKSEncoder:
    """sigma^{-1} / sigma for Z[X]/(X^N+1) restricted to the N/2 'slot' roots."""

    def __init__(self, N: int):
        self.N = N
        self.slots = N // 2
        self.rot_group = [pow(5, j, 2 * N) for j in range(self.slots)]
        roots = np.exp(1j * np.pi * np.array(self.rot_group) / N)
        self.E = roots[:, None] ** np.arange(N)[None, :]  # slots x N

    def embed(self, coeffs: Sequence[float]) -> np.ndarray:
        """Real coefficient vector -> slot values."""
        return self.E @ np.asarray(coeffs, dtype=float)

    def unembed(self, z: Sequence[complex]) -> np.ndarray:
        """Slot values -> real coefficient vector (exact inverse of embed)."""
        z = np.asarray(z, dtype=complex)
        return (2.0 / self.N) * np.real(np.conj(self.E).T @ z)

    def encode(self, z: Sequence[complex], scale: float) -> list:
        z = np.asarray(z, dtype=complex)
        if len(z) < self.slots:
            z = np.concatenate([z, np.zeros(self.slots - len(z))])
        c = self.unembed(z) * scale
        return [int(round(x)) for x in c]

    def decode(self, coeffs: Sequence[int], scale: float) -> np.ndarray:
        c = np.array([float(x) for x in coeffs]) / scale
        return self.embed(c)


class CKKS:
    """>>> ck = CKKS(N=16, seed=0); z = [0.5, -0.25j, 1, 0.1]
    >>> ct = ck.rescale(ck.mul(ck.encrypt(z), ck.encrypt(z)))
    >>> bool(np.max(np.abs(ck.decrypt(ct)[:4] - np.array(z)**2)) < 1e-3)
    True
    """

    def __init__(self, N: int = 16, levels: int = 3, scale_bits: int = 26, q0_bits: int = 40,
                 w_bits: int = 14, sigma: float = 3.19, special_bits: int = 40,
                 seed: Optional[int] = None):
        self.N, self.sigma = N, sigma
        self.rng = random.Random(seed)
        self.enc = CKKSEncoder(N)
        self.scale = float(1 << scale_bits)
        q0 = find_ntt_primes(q0_bits, 2 * N, 1)[0]
        mids = find_ntt_primes(scale_bits + 1, 2 * N, 2 * levels + 4, below=int(self.scale * (1 + 2.0 ** -12)))
        # choose primes closest to Delta (alternating above/below keeps scale stable)
        mids = sorted(mids, key=lambda p: abs(p - self.scale))[:levels]
        self.primes = [q0] + mids
        self.L = levels
        self.Q = [math.prod(self.primes[: l + 1]) for l in range(levels + 1)]
        self.rings = [PolyRing(m=2 * N, q=Q) for Q in self.Q]
        # special prime P for hybrid key switching (noise / P)
        cands = find_ntt_primes(special_bits, 2 * N, levels + 3)
        self.P = next(p for p in cands if p not in self.primes)
        self.RQP = PolyRing(m=2 * N, q=self.Q[-1] * self.P)
        self.w = 1 << w_bits
        self.keygen()

    # ----------------------------------------------------------------- keys
    def keygen(self):
        R, RP = self.rings[-1], self.RQP
        self.s = small_poly(R, "ternary", self.rng)
        a = R.uniform(self.rng)
        e = small_poly(R, "gaussian", self.rng, self.sigma)
        self.pk = (R.add(R.neg(R.mul(a, self.s)), e), a)
        s_qp = RP.from_list(list(R.centered(self.s)))
        self.s_qp = s_qp
        self.rlk = gen_ksk(RP, RP.mul(s_qp, s_qp), s_qp, self.w, 1, self.rng, self.sigma, P=self.P)
        self.galois_keys = {}

    def gen_galois_key(self, k: int):
        k %= 2 * self.N
        if k not in self.galois_keys:
            RP = self.RQP
            self.galois_keys[k] = gen_ksk(RP, RP.automorphism(self.s_qp, k), self.s_qp, self.w, 1,
                                          self.rng, self.sigma, P=self.P)
        return self.galois_keys[k]

    # ------------------------------------------------------------- enc/dec
    def encode(self, z, scale: Optional[float] = None) -> list:
        return self.enc.encode(z, scale or self.scale)

    def encrypt(self, z: Sequence[complex], scale: Optional[float] = None) -> Ciphertext:
        scale = scale or self.scale
        R = self.rings[-1]
        m = R.from_list(self.enc.encode(z, scale))
        u = small_poly(R, "ternary", self.rng)
        e0 = small_poly(R, "gaussian", self.rng, self.sigma)
        e1 = small_poly(R, "gaussian", self.rng, self.sigma)
        c0 = R.add(R.add(R.mul(self.pk[0], u), e0), m)
        c1 = R.add(R.mul(self.pk[1], u), e1)
        return Ciphertext([c0, c1], self.L, scale)

    def decrypt_poly(self, ct: Ciphertext) -> np.ndarray:
        R = self.rings[ct.level]
        acc, spow = R.zero(), R.one()
        sl = np.mod(self.s, R.q)
        for part in ct.parts:
            acc = R.add(acc, R.mul(part, spow))
            spow = R.mul(spow, sl)
        return R.centered(acc)

    def decrypt(self, ct: Ciphertext) -> np.ndarray:
        return self.enc.decode(self.decrypt_poly(ct), ct.scale)

    def error(self, ct: Ciphertext, expected: Sequence[complex]) -> float:
        exp = np.asarray(expected, dtype=complex)
        return float(np.max(np.abs(self.decrypt(ct)[: len(exp)] - exp)))

    def precision_bits(self, ct: Ciphertext, expected: Sequence[complex]) -> float:
        return -math.log2(max(self.error(ct, expected), 2.0 ** -60))

    # ---------------------------------------------------------- arithmetic
    def _drop_to(self, ct: Ciphertext, level: int) -> Ciphertext:
        if ct.level == level:
            return ct
        R = self.rings[level]
        return Ciphertext([R.reduce(p) for p in ct.parts], level, ct.scale)

    def _align(self, a, b):
        lvl = min(a.level, b.level)
        return self._drop_to(a, lvl), self._drop_to(b, lvl)

    def add(self, a: Ciphertext, b: Ciphertext) -> Ciphertext:
        count(CADD)
        a, b = self._align(a, b)
        if abs(a.scale / b.scale - 1) > 1e-3:
            raise ValueError("scale mismatch; rescale first")
        R = self.rings[a.level]
        return Ciphertext([R.add(x, y) for x, y in zip(a.parts, b.parts)], a.level, a.scale)

    def sub(self, a: Ciphertext, b: Ciphertext) -> Ciphertext:
        R = self.rings[b.level]
        return self.add(a, Ciphertext([R.neg(p) for p in b.parts], b.level, b.scale))

    def add_plain(self, a: Ciphertext, z) -> Ciphertext:
        R = self.rings[a.level]
        parts = [p.copy() for p in a.parts]
        parts[0] = R.add(parts[0], R.from_list(self.enc.encode(z, a.scale)))
        return Ciphertext(parts, a.level, a.scale)

    def mul_plain(self, a: Ciphertext, z, scale: Optional[float] = None) -> Ciphertext:
        """Multiply by an encoded plaintext vector (scale multiplies; rescale after)."""
        count(PMULT)
        scale = scale or self.scale
        R = self.rings[a.level]
        m = R.from_list(self.enc.encode(z, scale))
        return Ciphertext([R.mul(p, m) for p in a.parts], a.level, a.scale * scale)

    def mul_const_int(self, a: Ciphertext, c: int) -> Ciphertext:
        count(SMULT)
        R = self.rings[a.level]
        return Ciphertext([R.scalar(p, c) for p in a.parts], a.level, a.scale)

    def mul(self, a: Ciphertext, b: Ciphertext, relin: bool = True) -> Ciphertext:
        count(CMULT)
        a, b = self._align(a, b)
        R = self.rings[a.level]
        d0 = R.mul(a.parts[0], b.parts[0])
        d1 = R.add(R.mul(a.parts[0], b.parts[1]), R.mul(a.parts[1], b.parts[0]))
        d2 = R.mul(a.parts[1], b.parts[1])
        ct = Ciphertext([d0, d1, d2], a.level, a.scale * b.scale)
        return self.relinearize(ct) if relin else ct

    def relinearize(self, ct: Ciphertext) -> Ciphertext:
        count(RELIN)
        R = self.rings[ct.level]
        u0, u1 = apply_ksk(R, ct.parts[2], self.rlk, self.w, P=self.P)
        return Ciphertext([R.add(ct.parts[0], u0), R.add(ct.parts[1], u1)], ct.level, ct.scale)

    def rescale(self, ct: Ciphertext) -> Ciphertext:
        """Divide by the top prime q_l with rounding; scale /= q_l."""
        count(RESCALE)
        if ct.level == 0:
            raise ValueError("no level left")
        ql = self.primes[ct.level]
        Rn = self.rings[ct.level - 1]
        parts = []
        for c in ct.parts:
            cc = center(np.asarray(c, dtype=object), self.Q[ct.level])
            parts.append(Rn.reduce(np.array([(2 * int(x) + ql) // (2 * ql) for x in cc], dtype=object)))
        return Ciphertext(parts, ct.level - 1, ct.scale / ql)

    def _galois(self, ct: Ciphertext, k: int) -> Ciphertext:
        count(ROT)
        keys = self.gen_galois_key(k)
        R = self.rings[ct.level]
        c0 = R.automorphism(ct.parts[0], k)
        c1 = R.automorphism(ct.parts[1], k)
        u0, u1 = apply_ksk(R, c1, keys, self.w, P=self.P)
        return Ciphertext([R.add(c0, u0), u1], ct.level, ct.scale)

    def rotate(self, ct: Ciphertext, r: int) -> Ciphertext:
        """Slot rotation: result[j] = input[j + r] (cyclic over N/2 slots)."""
        return self._galois(ct, pow(5, r % (self.N // 2), 2 * self.N))

    def conjugate(self, ct: Ciphertext) -> Ciphertext:
        return self._galois(ct, 2 * self.N - 1)
