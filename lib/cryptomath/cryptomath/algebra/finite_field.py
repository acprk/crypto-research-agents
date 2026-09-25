"""Finite fields GF(p) and GF(p^k) = F_p[X]/(f) for an irreducible f.

Elements are immutable :class:`GFElem` objects supporting ``+ - * / **``,
equality and hashing, so they can be used as dictionary keys or inside
generic algorithms (e.g. :func:`cryptomath.algebra.poly.poly_eval`).

Irreducibility uses Rabin's test; random irreducible polynomials are found by
rejection sampling (about 1/k of monic degree-k polynomials are irreducible).

References
----------
* M. O. Rabin, "Probabilistic algorithms in finite fields", SIAM J. Comput.
  9(2), 1980 (irreducibility test).
* R. Lidl, H. Niederreiter, *Finite Fields*, 2nd ed., CUP 1997, ch. 2-3.
"""
from __future__ import annotations

import random
from typing import Iterable, List, Optional, Sequence

from .ntheory import factorint, is_prime
from .poly import (poly_divmod, poly_gcd, poly_inv_mod, poly_mod, poly_mul,
                   poly_powmod, poly_sub, poly_trim)

__all__ = ["is_irreducible", "random_irreducible", "conway_like_irreducible",
           "GF", "GFElem"]


def is_irreducible(f: Sequence[int], p: int) -> bool:
    """Rabin's test: monic f of degree k irreducible over F_p iff
    X^{p^k} = X mod f and gcd(X^{p^{k/r}} - X, f) = 1 for all primes r | k."""
    f = poly_trim(f, p)
    k = len(f) - 1
    if k < 1:
        return False
    if k == 1:
        return True
    f = poly_mul(f, [pow(f[-1], -1, p)], p)
    x = [0, 1]
    for r in factorint(k):
        h = poly_sub(poly_powmod(x, p ** (k // r), f, p), x, p)
        if poly_gcd(h, f, p) != [1]:
            return False
    return poly_sub(poly_powmod(x, p ** k, f, p), x, p) == []


def random_irreducible(p: int, k: int, rng: Optional[random.Random] = None) -> List[int]:
    """Random monic irreducible polynomial of degree k over F_p."""
    rng = rng or random
    while True:
        f = [rng.randrange(p) for _ in range(k)] + [1]
        if f[0] != 0 and is_irreducible(f, p):
            return f


def conway_like_irreducible(p: int, k: int) -> List[int]:
    """Deterministic choice: lexicographically first monic irreducible of degree k.

    (Not a Conway polynomial -- just reproducible.)
    """
    if k == 1:
        return [0, 1]
    for idx in range(p ** k):
        coeffs = []
        t = idx
        for _ in range(k):
            coeffs.append(t % p)
            t //= p
        f = coeffs + [1]
        if f[0] and is_irreducible(f, p):
            return f
    raise RuntimeError("no irreducible found")  # impossible


class GF:
    """The field GF(p^k).

    >>> F = GF(2, 8, modulus=[1,1,0,1,1,0,0,0,1])   # AES field
    >>> a = F([0,1,1]); (a * a.inverse()) == F.one
    True
    """

    def __init__(self, p: int, k: int = 1, modulus: Optional[Sequence[int]] = None):
        if not is_prime(p):
            raise ValueError("p must be prime")
        self.p, self.k = p, k
        if k == 1:
            modulus = [0, 1]
        elif modulus is None:
            modulus = conway_like_irreducible(p, k)
        modulus = poly_trim(modulus, p)
        if len(modulus) - 1 != k or not is_irreducible(modulus, p):
            raise ValueError("modulus must be irreducible of degree k")
        self.modulus = modulus
        self.order = p ** k
        self.zero = self([0])
        self.one = self([1])

    def __call__(self, x) -> "GFElem":
        if isinstance(x, GFElem):
            return x
        if isinstance(x, int):
            x = [x]
        return GFElem(self, poly_mod(list(x), self.modulus, self.p) if self.k > 1 else [int(x[0]) % self.p] if x else [])

    def __repr__(self):
        return f"GF({self.p}^{self.k})"

    def __eq__(self, other):
        return isinstance(other, GF) and (self.p, self.modulus) == (other.p, other.modulus)

    def __hash__(self):
        return hash((self.p, tuple(self.modulus)))

    @property
    def gen(self) -> "GFElem":
        """The class of X (a generator of the field over F_p)."""
        return self([0, 1]) if self.k > 1 else self([1])

    def elements(self):
        for idx in range(self.order):
            c, t = [], idx
            for _ in range(self.k):
                c.append(t % self.p)
                t //= self.p
            yield self(c)

    def from_int(self, idx: int) -> "GFElem":
        """Base-p digits of idx as coefficients (the usual integer encoding)."""
        c = []
        for _ in range(self.k):
            c.append(idx % self.p)
            idx //= self.p
        return self(c)

    def random(self, rng: Optional[random.Random] = None) -> "GFElem":
        rng = rng or random
        return self([rng.randrange(self.p) for _ in range(self.k)])

    def primitive_element(self) -> "GFElem":
        n = self.order - 1
        ps = list(factorint(n)) if n > 1 else []
        for a in self.elements():
            if a.is_zero():
                continue
            if all((a ** (n // r)) != self.one for r in ps):
                return a
        raise RuntimeError("unreachable")

    def root_of_unity(self, m: int) -> "GFElem":
        """A primitive m-th root of unity (requires m | p^k - 1)."""
        n = self.order - 1
        if n % m:
            raise ValueError(f"{m} does not divide {n}")
        return self.primitive_element() ** (n // m)


class GFElem:
    __slots__ = ("F", "c")

    def __init__(self, F: GF, coeffs: List[int]):
        self.F = F
        self.c = tuple(poly_trim(coeffs))

    # helpers
    def _coerce(self, o):
        return o if isinstance(o, GFElem) else self.F(o)

    def is_zero(self):
        return not self.c

    def __add__(self, o):
        o = self._coerce(o)
        n = max(len(self.c), len(o.c))
        a = [(self.c[i] if i < len(self.c) else 0) + (o.c[i] if i < len(o.c) else 0) for i in range(n)]
        return GFElem(self.F, [x % self.F.p for x in a])

    __radd__ = __add__

    def __neg__(self):
        return GFElem(self.F, [(-x) % self.F.p for x in self.c])

    def __sub__(self, o):
        return self + (-self._coerce(o))

    def __rsub__(self, o):
        return self._coerce(o) - self

    def __mul__(self, o):
        o = self._coerce(o)
        prod = poly_mul(list(self.c), list(o.c), self.F.p)
        if self.F.k > 1:
            prod = poly_mod(prod, self.F.modulus, self.F.p)
        return GFElem(self.F, prod)

    __rmul__ = __mul__

    def inverse(self):
        if self.is_zero():
            raise ZeroDivisionError
        if self.F.k == 1:
            return GFElem(self.F, [pow(self.c[0], -1, self.F.p)])
        return GFElem(self.F, poly_inv_mod(list(self.c), self.F.modulus, self.F.p))

    def __truediv__(self, o):
        return self * self._coerce(o).inverse()

    def __rtruediv__(self, o):
        return self._coerce(o) * self.inverse()

    def __pow__(self, e: int):
        if e < 0:
            return self.inverse() ** (-e)
        r, b = self.F.one, self
        while e:
            if e & 1:
                r = r * b
            b = b * b
            e >>= 1
        return r

    def __eq__(self, o):
        if isinstance(o, int):
            o = self.F(o)
        return isinstance(o, GFElem) and self.F == o.F and self.c == o.c

    def __hash__(self):
        return hash((self.F.p, self.c))

    def frobenius(self, j: int = 1):
        return self ** (self.F.p ** j)

    def to_int(self) -> int:
        return sum(c * self.F.p ** i for i, c in enumerate(self.c))

    def coeffs(self) -> List[int]:
        return list(self.c) + [0] * (self.F.k - len(self.c))

    def minpoly(self) -> List[int]:
        """Minimal polynomial over F_p (product over Frobenius conjugates)."""
        conj = [self]
        x = self.frobenius()
        while x != self:
            conj.append(x)
            x = x.frobenius()
        poly = [self.F.one]
        for r in conj:  # multiply by (X - r)
            new = [self.F.zero] * (len(poly) + 1)
            for i, a in enumerate(poly):
                new[i + 1] = new[i + 1] + a
                new[i] = new[i] - a * r
            poly = new
        out = []
        for a in poly:
            if len(a.c) > 1:
                raise AssertionError("minpoly coefficient not in F_p")
            out.append(a.c[0] if a.c else 0)
        return out

    def __repr__(self):
        if self.F.k == 1:
            return f"{self.c[0] if self.c else 0}"
        return f"GF{self.F.p}^{self.F.k}{list(self.coeffs())}"
