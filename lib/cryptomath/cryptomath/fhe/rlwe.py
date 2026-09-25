# TOY: not secure
"""Shared RLWE machinery for the toy BGV / BFV / CKKS implementations.

* :class:`Ciphertext` -- list of ring elements + level (+ scale for CKKS).
* integer gadget decomposition in base w (non-negative digits),
* key-switching keys in the BV / "digit decomposition" style
  (Brakerski--Vaikuntanathan, FOCS 2011, ePrint 2011/344):
      ksk_i = (-a_i s + E e_i + w^i s', a_i)   mod Q_top
  where E = t for BGV and E = 1 for BFV/CKKS.  At a lower level l the same
  key reduced mod Q_l is used.  (Real libraries use RNS + special primes,
  ePrint 2018/931; the noise shape is similar, only constants differ.)

All ring elements are numpy object arrays of Python ints (exact).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import numpy as np

from ..algebra.poly import PolyRing, center
from ..costmodel.counter import KS, count
from ..lattice.distributions import discrete_gaussian_vec, ternary_vec

__all__ = ["Ciphertext", "decompose", "num_digits", "gen_ksk", "apply_ksk", "small_poly"]


@dataclass
class Ciphertext:
    parts: List[np.ndarray]
    level: int
    scale: float = 1.0          # CKKS scaling factor (1 for BGV/BFV)
    meta: dict = field(default_factory=dict)

    def __len__(self):
        return len(self.parts)

    def copy(self) -> "Ciphertext":
        return Ciphertext([p.copy() for p in self.parts], self.level, self.scale, dict(self.meta))


def small_poly(R: PolyRing, kind: str, rng: random.Random, sigma: float = 3.19):
    if kind == "ternary":
        return R.from_list(ternary_vec(R.n, rng))
    if kind == "gaussian":
        return R.from_list(discrete_gaussian_vec(R.n, sigma, rng))
    raise ValueError(kind)


def num_digits(Q: int, w: int) -> int:
    return max(1, math.ceil(math.log(Q, w) - 1e-12))


def decompose(a: np.ndarray, Q: int, w: int) -> List[np.ndarray]:
    """Base-w digits of the coefficients of a (taken in [0, Q)): a = sum_i w^i D_i."""
    a = np.mod(np.asarray(a, dtype=object), Q)
    out = []
    for _ in range(num_digits(Q, w)):
        out.append(np.mod(a, w))
        a = a // w
    return out


def gen_ksk(R_top: PolyRing, s_from: np.ndarray, s_to: np.ndarray, w: int, err_mult: int,
            rng: random.Random, sigma: float = 3.19, P: int = 1):
    """Key-switching key from s_from to s_to.

    With a special modulus P > 1 (hybrid / GHS-style key switching,
    Gentry--Halevi--Smart ePrint 2012/099), R_top must be the ring mod Q*P;
    the keys encrypt P * w^i * s_from and :func:`apply_ksk` divides by P,
    which shrinks the key-switching noise by a factor P.
    """
    QP = R_top.q
    Q = QP // P
    keys = []
    for i in range(num_digits(Q, w)):
        a = R_top.uniform(rng)
        e = small_poly(R_top, "gaussian", rng, sigma)
        k0 = R_top.add(R_top.add(R_top.neg(R_top.mul(a, s_to)), R_top.scalar(e, err_mult)),
                       R_top.scalar(s_from, P * pow(w, i, QP) % QP))
        keys.append((k0, a))
    return keys


def apply_ksk(R: PolyRing, d: np.ndarray, keys, w: int, P: int = 1):
    """Return (u0, u1) with u0 + u1 s = d s' + small  (mod R.q)."""
    count(KS)
    digits = decompose(d, R.q, w)
    RP = R if P == 1 else R.change_modulus(R.q * P)
    u0, u1 = RP.zero(), RP.zero()
    for Di, (k0, k1) in zip(digits, keys):
        u0 = RP.add(u0, RP.mul(Di, np.mod(k0, RP.q)))
        u1 = RP.add(u1, RP.mul(Di, np.mod(k1, RP.q)))
    if P == 1:
        return u0, u1
    out = []
    for u in (u0, u1):
        uc = center(u, RP.q)
        out.append(R.reduce(np.array([(2 * int(x) + P) // (2 * P) for x in uc], dtype=object)))
    return out[0], out[1]
