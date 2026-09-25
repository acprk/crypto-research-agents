# TOY: not secure
"""Toy BFV (Brakerski, CRYPTO 2012, ePrint 2012/078; Fan--Vercauteren,
ePrint 2012/144): scale-invariant RLWE.

Ciphertext (c0, c1) with  c0 + c1 s = Delta m + v + Q k,  Delta = floor(Q/t).
Multiplication: exact tensor over Z (centered lifts), then round(t/Q * .)
and relinearise with base-w key switching.  Noise is reported as the
*invariant noise budget* log2(Q / (2 ||t c(s) mod Q||)) as in SEAL.
"""
from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence

import numpy as np

from ..algebra.poly import PolyRing, center
from ..costmodel.counter import CADD, CMULT, PMULT, RELIN, count
from .rlwe import Ciphertext, apply_ksk, gen_ksk, small_poly

__all__ = ["BFV"]


def _round_div(x: np.ndarray, num: int, den: int) -> np.ndarray:
    """round(x * num / den) for object arrays (exact, round half up)."""
    return np.array([(2 * int(v) * num + den) // (2 * den) for v in x], dtype=object)


class BFV:
    """>>> bfv = BFV(N=16, t=17, qbits=80, seed=1)
    >>> ct = bfv.encrypt([3, 1]); bfv.decrypt(bfv.mul(ct, ct))[:3]
    [9, 6, 1]
    """

    def __init__(self, N: int = 16, t: int = 17, qbits: int = 80, w_bits: int = 16,
                 sigma: float = 3.19, seed: Optional[int] = None, q: Optional[int] = None):
        self.N, self.t, self.sigma = N, t, sigma
        self.rng = random.Random(seed)
        self.q = q if q is not None else (1 << qbits) + 1  # any modulus works for BFV
        self.delta = self.q // t
        self.R = PolyRing(m=2 * N, q=self.q)
        self.RZ = PolyRing(m=2 * N, q=None)
        self.w = 1 << w_bits
        self.keygen()

    def keygen(self):
        R = self.R
        self.s = small_poly(R, "ternary", self.rng)
        a = R.uniform(self.rng)
        e = small_poly(R, "gaussian", self.rng, self.sigma)
        self.pk = (R.add(R.neg(R.mul(a, self.s)), e), a)
        self.rlk = gen_ksk(R, R.mul(self.s, self.s), self.s, self.w, 1, self.rng, self.sigma)

    def encrypt(self, m: Sequence[int]) -> Ciphertext:
        R = self.R
        mm = R.from_list([x % self.t for x in m])
        u = small_poly(R, "ternary", self.rng)
        e0 = small_poly(R, "gaussian", self.rng, self.sigma)
        e1 = small_poly(R, "gaussian", self.rng, self.sigma)
        c0 = R.add(R.add(R.mul(self.pk[0], u), e0), R.scalar(mm, self.delta))
        c1 = R.add(R.mul(self.pk[1], u), e1)
        return Ciphertext([c0, c1], 0)

    def _raw(self, ct: Ciphertext) -> np.ndarray:
        R = self.R
        acc, spow = R.zero(), R.one()
        for part in ct.parts:
            acc = R.add(acc, R.mul(part, spow))
            spow = R.mul(spow, self.s)
        return acc

    def decrypt(self, ct: Ciphertext) -> List[int]:
        v = self._raw(ct)
        return [int(x) % self.t for x in _round_div(np.mod(v, self.q), self.t, self.q)]

    def noise_budget(self, ct: Ciphertext) -> float:
        v = np.mod(self._raw(ct) * self.t, self.q)
        r = center(v, self.q)
        mx = max(1, max(abs(int(x)) for x in r))
        return math.log2(self.q / (2 * mx))

    def add(self, a: Ciphertext, b: Ciphertext) -> Ciphertext:
        count(CADD)
        R = self.R
        n = max(len(a), len(b))
        return Ciphertext([R.add(a.parts[i] if i < len(a) else R.zero(), b.parts[i] if i < len(b) else R.zero())
                           for i in range(n)], 0)

    def add_plain(self, a: Ciphertext, m: Sequence[int]) -> Ciphertext:
        R = self.R
        parts = [p.copy() for p in a.parts]
        parts[0] = R.add(parts[0], R.scalar(R.from_list([x % self.t for x in m]), self.delta))
        return Ciphertext(parts, 0)

    def mul_plain(self, a: Ciphertext, m: Sequence[int]) -> Ciphertext:
        count(PMULT)
        R = self.R
        mm = R.from_list(list(center(np.array([x % self.t for x in m], dtype=object), self.t)))
        return Ciphertext([R.mul(p, mm) for p in a.parts], 0)

    def mul(self, a: Ciphertext, b: Ciphertext, relin: bool = True) -> Ciphertext:
        count(CMULT)
        R, RZ, q, t = self.R, self.RZ, self.q, self.t
        a0, a1 = (center(p, q) for p in a.parts)
        b0, b1 = (center(p, q) for p in b.parts)
        d = [RZ.mul(a0, b0), RZ.add(RZ.mul(a0, b1), RZ.mul(a1, b0)), RZ.mul(a1, b1)]
        parts = [R.reduce(_round_div(x, t, q)) for x in d]
        ct = Ciphertext(parts, 0)
        return self.relinearize(ct) if relin else ct

    def relinearize(self, ct: Ciphertext) -> Ciphertext:
        count(RELIN)
        R = self.R
        u0, u1 = apply_ksk(R, ct.parts[2], self.rlk, self.w)
        return Ciphertext([R.add(ct.parts[0], u0), R.add(ct.parts[1], u1)], 0)
