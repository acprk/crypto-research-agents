# TOY: not secure
"""Toy LWE / RLWE / MLWE / NTRU instance generators.

Each returns the public data together with the secret so experiments
(attacks, noise checks) can verify ground truth.

* LWE (Regev 2005): b = A s + e mod q, A in Z_q^{m x n}.
* RLWE (Lyubashevsky--Peikert--Regev, EUROCRYPT 2010, ePrint 2012/230):
  b = a s + e in R_q = Z_q[X]/Phi_m.
* MLWE (Langlois--Stehle, DCC 2015, ePrint 2012/090): b = A s + e over R_q^k.
* NTRU (Hoffstein--Pipher--Silverman, ANTS 1998): h = g / f in R_q with
  small f, g; here in Z_q[X]/(X^N + 1) (or any Phi_m) with f invertible mod q.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from ..algebra.ntheory import is_prime
from ..algebra.poly import PolyRing, poly_inv_mod, poly_inv_mod_pe, center
from ..algebra.ntheory import factorint
from .distributions import Distribution, GAUSSIAN, TERNARY

__all__ = ["LWEInstance", "lwe_sample", "RLWEInstance", "rlwe_sample",
           "MLWEInstance", "mlwe_sample", "NTRUInstance", "ntru_keygen",
           "lwe_to_matrix_rlwe"]


@dataclass
class LWEInstance:
    A: np.ndarray  # m x n, object ints mod q
    b: np.ndarray  # m
    s: np.ndarray  # n
    e: np.ndarray  # m
    q: int

    def check(self) -> bool:
        return all((self.A.dot(self.s) + self.e - self.b) % self.q == 0)


def lwe_sample(n: int, m: int, q: int, secret: Distribution = TERNARY,
               error: Distribution = GAUSSIAN(3.19), rng: Optional[random.Random] = None) -> LWEInstance:
    rng = rng or random.Random()
    A = np.array([[rng.randrange(q) for _ in range(n)] for _ in range(m)], dtype=object)
    s = np.array(secret.sample(n, rng), dtype=object)
    e = np.array(error.sample(m, rng), dtype=object)
    b = (A.dot(s) + e) % q
    return LWEInstance(A, b, s, e, q)


@dataclass
class RLWEInstance:
    R: PolyRing
    a: np.ndarray
    b: np.ndarray
    s: np.ndarray
    e: np.ndarray

    def check(self) -> bool:
        return all(self.R.sub(self.b, self.R.add(self.R.mul(self.a, self.s), self.e)) == 0)


def rlwe_sample(R: PolyRing, secret: Distribution = TERNARY, error: Distribution = GAUSSIAN(3.19),
                rng: Optional[random.Random] = None) -> RLWEInstance:
    rng = rng or random.Random()
    a = R.uniform(rng)
    s = R.from_list(secret.sample(R.n, rng))
    e = R.from_list(error.sample(R.n, rng))
    b = R.add(R.mul(a, s), e)
    return RLWEInstance(R, a, b, s, e)


@dataclass
class MLWEInstance:
    R: PolyRing
    A: list  # k x k list of ring elements
    b: list
    s: list
    e: list

    def check(self) -> bool:
        R = self.R
        for i, row in enumerate(self.A):
            acc = self.e[i]
            for aij, sj in zip(row, self.s):
                acc = R.add(acc, R.mul(aij, sj))
            if any(R.sub(acc, self.b[i]) != 0):
                return False
        return True


def mlwe_sample(R: PolyRing, k: int, secret: Distribution = TERNARY, error: Distribution = GAUSSIAN(1.0),
                rng: Optional[random.Random] = None, rows: Optional[int] = None) -> MLWEInstance:
    rng = rng or random.Random()
    rows = rows or k
    A = [[R.uniform(rng) for _ in range(k)] for _ in range(rows)]
    s = [R.from_list(secret.sample(R.n, rng)) for _ in range(k)]
    e = [R.from_list(error.sample(R.n, rng)) for _ in range(rows)]
    b = []
    for i in range(rows):
        acc = e[i]
        for j in range(k):
            acc = R.add(acc, R.mul(A[i][j], s[j]))
        b.append(acc)
    return MLWEInstance(R, A, b, s, e)


def lwe_to_matrix_rlwe(R: PolyRing, a: np.ndarray) -> np.ndarray:
    """Matrix of multiplication-by-a in the power basis (columns = a * X^j)."""
    cols = [R.mul(a, R.monomial(j)) for j in range(R.n)]
    return np.array(cols, dtype=object).T


@dataclass
class NTRUInstance:
    R: PolyRing
    h: np.ndarray
    f: np.ndarray
    g: np.ndarray
    p: int

    def check(self) -> bool:
        R = self.R
        return all(R.sub(R.mul(self.h, self.f), R.scalar(self.g, self.p)) == 0)


def _inverse_in_ring(R: PolyRing, a) -> np.ndarray:
    q = R.q
    fs = factorint(q)
    lst = [int(x) for x in a]
    if len(fs) == 1:
        (p, e), = fs.items()
        inv = poly_inv_mod(lst, R.f, p) if e == 1 else poly_inv_mod_pe(lst, R.f, p, e)
        return R.from_list(inv)
    raise ValueError("toy NTRU supports prime-power q only")


def ntru_keygen(R: PolyRing, p: int = 3, rng: Optional[random.Random] = None, max_tries: int = 100,
                small: Distribution = TERNARY) -> NTRUInstance:
    """h = p g f^{-1} mod q with small f, g (f invertible mod q)."""
    rng = rng or random.Random()
    for _ in range(max_tries):
        f = R.from_list(small.sample(R.n, rng))
        g = R.from_list(small.sample(R.n, rng))
        try:
            finv = _inverse_in_ring(R, f)
        except ValueError:
            continue
        h = R.scalar(R.mul(g, finv), p)
        return NTRUInstance(R, h, f, g, p)
    raise RuntimeError("no invertible f found")
