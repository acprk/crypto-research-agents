# TOY: not secure
"""Toy BGV (Brakerski--Gentry--Vaikuntanathan, ITCS 2012, ePrint 2011/277).

Ring R = Z[X]/(X^N+1), plaintext modulus t, modulus chain
Q_l = q_0 q_1 ... q_l with every q_i = 1 mod 2N and q_i = 1 mod t
(so modulus switching does not rescale the message; see Gentry--Halevi--
Smart, "Homomorphic evaluation of the AES circuit", ePrint 2012/099).

Ciphertext (c0, c1) at level l decrypts as  [c0 + c1 s]_{Q_l} = m + t v.

Implemented: keygen (ternary s, public key), encrypt (public/secret key),
decrypt, add/sub, plaintext add/mul, ciphertext mul (tensor), relinearise,
modulus switch, Galois automorphisms / slot rotations (with key switching),
slot encoding via :class:`cryptomath.algebra.slots.SlotEncoder`, and
measured noise budget.  Every homomorphic op reports to the cost model.
"""
from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence

import numpy as np

from ..algebra.ntheory import find_ntt_primes
from ..algebra.poly import PolyRing, center
from ..costmodel.counter import CADD, CMULT, MODSWITCH, PMULT, RELIN, ROT, count
from .rlwe import Ciphertext, apply_ksk, gen_ksk, small_poly

__all__ = ["BGV"]


class BGV:
    """>>> bgv = BGV(N=16, t=257, levels=2, seed=1)
    >>> ct = bgv.encrypt([1, 2, 3]); bgv.decrypt(bgv.mul(ct, ct))[:5]
    [1, 4, 10, 12, 9]
    """

    def __init__(self, N: int = 16, t: int = 257, levels: int = 2, qbits: int = 30,
                 w_bits: int = 12, sigma: float = 3.19, seed: Optional[int] = None):
        self.N, self.t, self.sigma = N, t, sigma
        self.rng = random.Random(seed)
        step = 2 * N * t // math.gcd(2 * N, t)
        self.primes = find_ntt_primes(qbits, step, levels + 1)
        self.L = levels
        self.Q = [math.prod(self.primes[: l + 1]) for l in range(levels + 1)]
        self.rings = [PolyRing(m=2 * N, q=Q) for Q in self.Q]
        self.Rt = PolyRing(m=2 * N, q=t)
        self.w = 1 << w_bits
        self._encoder = None
        self.keygen()

    # ----------------------------------------------------------------- keys
    def keygen(self):
        R = self.rings[-1]
        self.s = small_poly(R, "ternary", self.rng)
        a = R.uniform(self.rng)
        e = small_poly(R, "gaussian", self.rng, self.sigma)
        self.pk = (R.add(R.neg(R.mul(a, self.s)), R.scalar(e, self.t)), a)
        s2 = R.mul(self.s, self.s)
        self.rlk = gen_ksk(R, s2, self.s, self.w, self.t, self.rng, self.sigma)
        self.galois_keys: Dict[int, list] = {}

    def gen_galois_key(self, k: int):
        R = self.rings[-1]
        k %= 2 * self.N
        if k not in self.galois_keys:
            sk = R.automorphism(self.s, k)
            self.galois_keys[k] = gen_ksk(R, sk, self.s, self.w, self.t, self.rng, self.sigma)
        return self.galois_keys[k]

    # ------------------------------------------------------------ encoding
    @property
    def encoder(self):
        """CRT slot encoder (needs prime t not dividing 2N)."""
        if self._encoder is None:
            from ..algebra.slots import SlotEncoder
            self._encoder = SlotEncoder(m=2 * self.N, p=self.t, e=1)
        return self._encoder

    def encode_slots(self, values: Sequence) -> List[int]:
        return self.encoder.encode(values)

    def decode_slots(self, poly: Sequence[int]):
        return self.encoder.decode(poly)

    # ------------------------------------------------------------- enc/dec
    def encrypt(self, m: Sequence[int], level: Optional[int] = None) -> Ciphertext:
        level = self.L if level is None else level
        R = self.rings[-1]
        mm = R.from_list([x % self.t for x in m])
        u = small_poly(R, "ternary", self.rng)
        e0 = small_poly(R, "gaussian", self.rng, self.sigma)
        e1 = small_poly(R, "gaussian", self.rng, self.sigma)
        c0 = R.add(R.add(R.mul(self.pk[0], u), R.scalar(e0, self.t)), mm)
        c1 = R.add(R.mul(self.pk[1], u), R.scalar(e1, self.t))
        ct = Ciphertext([c0, c1], self.L)
        while ct.level > level:
            ct = self.mod_switch(ct)
        return ct

    def _raw(self, ct: Ciphertext) -> np.ndarray:
        R = self.rings[ct.level]
        acc = R.zero()
        spow = R.one()
        sl = np.mod(self.s, R.q)
        for part in ct.parts:
            acc = R.add(acc, R.mul(part, spow))
            spow = R.mul(spow, sl)
        return R.centered(acc)

    def decrypt(self, ct: Ciphertext) -> List[int]:
        v = self._raw(ct)
        return [int(x) % self.t for x in v]

    def noise(self, ct: Ciphertext) -> int:
        """||[c(s)]_Q||_inf  (includes the message)."""
        return int(max(abs(int(x)) for x in self._raw(ct)))

    def noise_budget(self, ct: Ciphertext) -> float:
        """log2(Q_l / 2) - log2 ||c(s)||_inf ; decryption correct while > 0."""
        return math.log2(self.Q[ct.level] / 2) - math.log2(max(1, self.noise(ct)))

    # ---------------------------------------------------------- arithmetic
    def _align(self, a: Ciphertext, b: Ciphertext):
        while a.level > b.level:
            a = self.mod_switch(a)
        while b.level > a.level:
            b = self.mod_switch(b)
        return a, b

    def add(self, a: Ciphertext, b: Ciphertext) -> Ciphertext:
        count(CADD)
        a, b = self._align(a, b)
        R = self.rings[a.level]
        n = max(len(a), len(b))
        parts = [R.add(a.parts[i] if i < len(a) else R.zero(), b.parts[i] if i < len(b) else R.zero()) for i in range(n)]
        return Ciphertext(parts, a.level)

    def sub(self, a: Ciphertext, b: Ciphertext) -> Ciphertext:
        R = self.rings[b.level]
        return self.add(a, Ciphertext([R.neg(p) for p in b.parts], b.level))

    def add_plain(self, a: Ciphertext, m: Sequence[int]) -> Ciphertext:
        R = self.rings[a.level]
        parts = [p.copy() for p in a.parts]
        parts[0] = R.add(parts[0], R.from_list([x % self.t for x in m]))
        return Ciphertext(parts, a.level)

    def mul_plain(self, a: Ciphertext, m: Sequence[int]) -> Ciphertext:
        count(PMULT)
        R = self.rings[a.level]
        mm = R.from_list(list(center(np.array([x % self.t for x in m], dtype=object), self.t)))
        return Ciphertext([R.mul(p, mm) for p in a.parts], a.level)

    def mul(self, a: Ciphertext, b: Ciphertext, relin: bool = True) -> Ciphertext:
        count(CMULT)
        a, b = self._align(a, b)
        assert len(a) == 2 and len(b) == 2, "relinearise first"
        R = self.rings[a.level]
        d0 = R.mul(a.parts[0], b.parts[0])
        d1 = R.add(R.mul(a.parts[0], b.parts[1]), R.mul(a.parts[1], b.parts[0]))
        d2 = R.mul(a.parts[1], b.parts[1])
        ct = Ciphertext([d0, d1, d2], a.level)
        return self.relinearize(ct) if relin else ct

    def relinearize(self, ct: Ciphertext) -> Ciphertext:
        count(RELIN)
        R = self.rings[ct.level]
        u0, u1 = apply_ksk(R, ct.parts[2], self.rlk, self.w)
        return Ciphertext([R.add(ct.parts[0], u0), R.add(ct.parts[1], u1)], ct.level)

    def mod_switch(self, ct: Ciphertext) -> Ciphertext:
        """Q_l -> Q_{l-1}: c' = (c - delta)/q_l, delta = c mod q_l, delta = 0 mod t."""
        count(MODSWITCH)
        if ct.level == 0:
            raise ValueError("already at level 0")
        ql = self.primes[ct.level]
        t = self.t
        Rn = self.rings[ct.level - 1]
        inv = pow(ql, -1, t)
        parts = []
        for c in ct.parts:
            c = np.asarray(c, dtype=object)
            cq = center(np.mod(c, ql), ql)
            corr = np.mod(-cq * inv, t)
            corr = center(corr, t)
            delta = cq + ql * corr
            parts.append(Rn.reduce((c - delta) // ql))
        return Ciphertext(parts, ct.level - 1)

    # -------------------------------------------------------- automorphisms
    def apply_galois(self, ct: Ciphertext, k: int) -> Ciphertext:
        """sigma_k on the plaintext (X -> X^k), k odd."""
        count(ROT)
        keys = self.gen_galois_key(k)
        R = self.rings[ct.level]
        c0 = R.automorphism(ct.parts[0], k)
        c1 = R.automorphism(ct.parts[1], k)
        u0, u1 = apply_ksk(R, c1, keys, self.w)
        return Ciphertext([R.add(c0, u0), u1], ct.level)
