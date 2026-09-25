"""Dirichlet characters of (Z/m)^* and character sums (complex-valued).

A character is stored by its exponent vector with respect to the generators
returned by :func:`cryptomath.algebra.ntheory.unit_group_generators`:
chi(g_i) = exp(2 pi i a_i / ord(g_i)).

Provides: enumeration of all phi(m) characters, evaluation, orthogonality,
conductor / primitivity, the character group restricted to a subgroup H
(characters trivial on H <-> characters of the quotient), Gauss sums,
and generic sums  sum_{a in S} chi(a) zeta_m^{a b}.

References
----------
* T. M. Apostol, *Introduction to Analytic Number Theory*, Springer 1976,
  ch. 6 and 8 (Dirichlet characters, Gauss sums).
* H. Iwaniec, E. Kowalski, *Analytic Number Theory*, AMS 2004, ch. 3.
"""
from __future__ import annotations

import cmath
import math
from functools import lru_cache
from itertools import product
from typing import Dict, Iterable, List, Sequence, Tuple

from .ntheory import divisors, euler_phi, unit_group_generators, units

__all__ = ["DirichletGroup", "Character", "gauss_sum", "character_sum",
           "exponential_sum"]


class Character:
    def __init__(self, G: "DirichletGroup", exps: Tuple[int, ...]):
        self.G = G
        self.exps = tuple(exps)

    def __call__(self, a: int) -> complex:
        a %= self.G.m
        if math.gcd(a, self.G.m) != 1:
            return 0j
        dl = self.G.dlog[a]
        ang = sum(x * y / o for x, y, (_, o) in zip(self.exps, dl, self.G.gens))
        return cmath.exp(2j * math.pi * ang)

    def __mul__(self, other: "Character") -> "Character":
        return Character(self.G, tuple((x + y) % o for x, y, (_, o) in zip(self.exps, other.exps, self.G.gens)))

    def conj(self) -> "Character":
        return Character(self.G, tuple((-x) % o for x, (_, o) in zip(self.exps, self.G.gens)))

    def order(self) -> int:
        o = 1
        for x, (_, oi) in zip(self.exps, self.G.gens):
            k = oi // math.gcd(x, oi)
            o = o * k // math.gcd(o, k)
        return o

    def is_trivial(self) -> bool:
        return all(x == 0 for x in self.exps)

    def is_even(self) -> bool:
        return abs(self(-1) - 1) < 1e-9

    def is_trivial_on(self, H: Iterable[int]) -> bool:
        return all(abs(self(h) - 1) < 1e-9 for h in H)

    def conductor(self) -> int:
        """Least d | m such that chi is trivial on {a = 1 mod d}."""
        m = self.G.m
        for d in divisors(m):
            if all(abs(self(a) - 1) < 1e-9 for a in self.G.units if a % d == 1 % d):
                return d
        return m

    def is_primitive(self) -> bool:
        return self.conductor() == self.G.m

    def values(self) -> Dict[int, complex]:
        return {a: self(a) for a in self.G.units}

    def __repr__(self):
        return f"chi_{self.G.m}{self.exps}"


class DirichletGroup:
    """The group of Dirichlet characters mod m (isomorphic to (Z/m)^*)."""

    def __init__(self, m: int):
        self.m = m
        self.units = units(m)
        self.gens = unit_group_generators(m) if m > 2 else ([(m - 1, 1)] if m == 2 else [])
        if m <= 2:
            self.gens = [(1, 1)]
        # discrete-log table w.r.t. the generator decomposition
        self.dlog: Dict[int, Tuple[int, ...]] = {}
        for exps in product(*[range(o) for _, o in self.gens]):
            a = 1
            for (g, _), x in zip(self.gens, exps):
                a = a * pow(g, x, m) % m
            self.dlog[a % m if m > 1 else 0] = exps
        assert len(self.dlog) == euler_phi(m), "generator decomposition failed"

    def __len__(self):
        return euler_phi(self.m)

    def __iter__(self):
        for exps in product(*[range(o) for _, o in self.gens]):
            yield Character(self, exps)

    def trivial(self) -> Character:
        return Character(self, tuple(0 for _ in self.gens))

    def annihilator(self, H: Iterable[int]) -> List[Character]:
        """Characters trivial on subgroup H (= characters of (Z/m)^*/H)."""
        H = list(H)
        return [chi for chi in self if chi.is_trivial_on(H)]


def gauss_sum(chi: Character, b: int = 1) -> complex:
    """g(chi, b) = sum_{a mod m} chi(a) exp(2 pi i a b / m); |g| = sqrt(m) for primitive chi."""
    m = chi.G.m
    return sum(chi(a) * cmath.exp(2j * math.pi * a * b / m) for a in chi.G.units)


def character_sum(chi: Character, S: Iterable[int]) -> complex:
    """sum_{a in S} chi(a)."""
    return sum(chi(a) for a in S)


def exponential_sum(S: Iterable[int], m: int, b: int = 1) -> complex:
    """sum_{a in S} exp(2 pi i a b / m) -- e.g. Gaussian periods when S is a coset."""
    return sum(cmath.exp(2j * math.pi * a * b / m) for a in S)
