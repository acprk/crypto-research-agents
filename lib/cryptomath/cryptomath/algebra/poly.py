"""Univariate polynomial arithmetic over Z and Z/q, and cyclotomic rings.

Two layers:

1. **List layer** -- polynomials are Python lists of ints, lowest degree first
   (``[a0, a1, ..., ad]``).  Exact for any modulus (or none).  Division is only
   by *monic* divisors for composite q; gcd / inverse need prime q (or use the
   Newton-lifting inverse :func:`poly_inv_mod_pe` for q = p^e).
2. :class:`PolyRing` -- the quotient ring R_q = Z_q[X]/(f) with f = Phi_m or
   any monic f, using numpy *object* arrays (exact Python ints, arbitrary q).
   Power-of-two cyclotomics (f = X^N + 1) use a negacyclic fast path.

Includes cyclotomic polynomials Phi_m and the Galois automorphisms
sigma_k : X -> X^k (k in (Z/m)^*) acting on R = Z[X]/Phi_m.

References
----------
* V. Lyubashevsky, C. Peikert, O. Regev, "A Toolkit for Ring-LWE
  Cryptography", EUROCRYPT 2013, ePrint 2013/293 (cyclotomic rings, Galois).
* L. C. Washington, *Introduction to Cyclotomic Fields*, GTM 83, ch. 2.
* J. von zur Gathen, J. Gerhard, *Modern Computer Algebra*, 3rd ed., CUP 2013,
  ch. 2-4 (division, gcd, Newton inversion) and ch. 9 (Newton/Hensel).
"""
from __future__ import annotations

import random
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

from .ntheory import divisors, euler_phi, factorint

__all__ = [
    "poly_trim", "poly_deg", "poly_add", "poly_sub", "poly_neg", "poly_scale",
    "poly_mul", "poly_divmod", "poly_mod", "poly_eval", "poly_powmod",
    "poly_gcd", "poly_xgcd", "poly_inv_mod", "poly_inv_mod_pe", "poly_compose",
    "poly_monic", "poly_derivative", "cyclotomic_poly", "is_power_of_two",
    "PolyRing", "center",
]

Poly = List[int]


# --------------------------------------------------------------------------
# list layer
# --------------------------------------------------------------------------

def poly_trim(a: Sequence[int], q: Optional[int] = None) -> Poly:
    """Reduce coefficients mod q (if given) and strip leading zeros."""
    a = [x % q for x in a] if q else list(a)
    while a and a[-1] == 0:
        a.pop()
    return a


def poly_deg(a: Sequence[int]) -> int:
    """Degree; -1 for the zero polynomial (after trimming)."""
    a = poly_trim(a)
    return len(a) - 1


def poly_add(a, b, q=None) -> Poly:
    n = max(len(a), len(b))
    return poly_trim([(a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0) for i in range(n)], q)


def poly_neg(a, q=None) -> Poly:
    return poly_trim([-x for x in a], q)


def poly_sub(a, b, q=None) -> Poly:
    return poly_add(a, [-x for x in b], q)


def poly_scale(a, c, q=None) -> Poly:
    return poly_trim([c * x for x in a], q)


def poly_mul(a, b, q=None) -> Poly:
    """Schoolbook product (exact ints)."""
    if not a or not b:
        return []
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x == 0:
            continue
        for j, y in enumerate(b):
            out[i + j] += x * y
    return poly_trim(out, q)


def poly_divmod(a, b, q=None) -> Tuple[Poly, Poly]:
    """Division with remainder.

    Over Z (q=None) or composite q the divisor must be monic (leading coeff
    a unit is enough when q is given).  Over a prime q any nonzero b works.
    """
    a = poly_trim(a, q)
    b = poly_trim(b, q)
    if not b:
        raise ZeroDivisionError("division by zero polynomial")
    lb = b[-1]
    if q:
        inv_lb = pow(lb, -1, q)
    elif lb not in (1, -1):
        raise ValueError("over Z the divisor must be monic")
    else:
        inv_lb = lb
    db = len(b) - 1
    quo = [0] * max(len(a) - db, 0)
    r = list(a)
    for i in range(len(a) - 1, db - 1, -1):
        c = r[i] * inv_lb
        if q:
            c %= q
        if c == 0:
            continue
        quo[i - db] = c
        for j in range(db + 1):
            r[i - db + j] -= c * b[j]
        if q:
            for j in range(db + 1):
                r[i - db + j] %= q
    return poly_trim(quo, q), poly_trim(r[:db] if db > 0 else [], q)


def poly_mod(a, b, q=None) -> Poly:
    return poly_divmod(a, b, q)[1]


def poly_eval(a: Sequence[int], x, q=None):
    """Horner evaluation (x may be int, float, complex, or a ring element)."""
    acc = 0
    for c in reversed(list(a)):
        acc = acc * x + c
        if q:
            acc %= q
    return acc


def poly_powmod(a, e: int, f, q=None) -> Poly:
    """a^e mod (f, q) by square-and-multiply."""
    result = [1]
    base = poly_mod(a, f, q)
    while e > 0:
        if e & 1:
            result = poly_mod(poly_mul(result, base, q), f, q)
        base = poly_mod(poly_mul(base, base, q), f, q)
        e >>= 1
    return result


def poly_monic(a, q) -> Poly:
    a = poly_trim(a, q)
    if not a:
        return a
    return poly_scale(a, pow(a[-1], -1, q), q)


def poly_gcd(a, b, q) -> Poly:
    """Monic gcd over the field F_q (q prime)."""
    a, b = poly_trim(a, q), poly_trim(b, q)
    while b:
        a, b = b, poly_mod(a, b, q)
    return poly_monic(a, q)


def poly_xgcd(a, b, q) -> Tuple[Poly, Poly, Poly]:
    """Extended Euclid over F_q: returns (g, s, t) with s*a + t*b = g monic."""
    r0, r1 = poly_trim(a, q), poly_trim(b, q)
    s0, s1, t0, t1 = [1], [], [], [1]
    while r1:
        quo, r = poly_divmod(r0, r1, q)
        r0, r1 = r1, r
        s0, s1 = s1, poly_sub(s0, poly_mul(quo, s1, q), q)
        t0, t1 = t1, poly_sub(t0, poly_mul(quo, t1, q), q)
    if not r0:
        return [], s0, t0
    inv = pow(r0[-1], -1, q)
    return poly_scale(r0, inv, q), poly_scale(s0, inv, q), poly_scale(t0, inv, q)


def poly_inv_mod(a, f, q) -> Poly:
    """Inverse of a modulo (f, q) for q prime."""
    g, s, _ = poly_xgcd(a, f, q)
    if g != [1]:
        raise ValueError("not invertible")
    return poly_mod(s, f, q)


def poly_inv_mod_pe(a, f, p: int, e: int) -> Poly:
    """Inverse of a modulo (f, p^e) by Newton lifting u <- u(2 - a u).

    f must be monic.  Invertibility is decided mod p.
    """
    u = poly_inv_mod(a, f, p)
    mod = p
    while mod < p ** e:
        mod = min(mod * mod, p ** e)
        au = poly_mod(poly_mul(a, u, mod), f, mod)
        u = poly_mod(poly_mul(u, poly_sub([2], au, mod), mod), f, mod)
    return u


def poly_compose(a, b, q=None) -> Poly:
    """a(b(X))."""
    acc: Poly = []
    for c in reversed(list(a)):
        acc = poly_add(poly_mul(acc, b, q), [c], q)
    return acc


def poly_derivative(a, q=None) -> Poly:
    return poly_trim([i * a[i] for i in range(1, len(a))], q)


# --------------------------------------------------------------------------
# cyclotomic polynomials
# --------------------------------------------------------------------------

def is_power_of_two(n: int) -> bool:
    return n > 0 and n & (n - 1) == 0


@lru_cache(maxsize=None)
def _cyclo(m: int) -> Tuple[int, ...]:
    # Phi_m = prod_{d | m} (X^d - 1)^{mu(m/d)}; compute by exact division:
    # X^m - 1 = prod_{d | m} Phi_d.
    if m == 1:
        return (-1, 1)
    num = [-1] + [0] * (m - 1) + [1]
    for d in divisors(m):
        if d < m:
            num, r = poly_divmod(num, list(_cyclo(d)))
            assert not r
    return tuple(num)


def cyclotomic_poly(m: int) -> Poly:
    """Coefficient list of the m-th cyclotomic polynomial Phi_m (over Z)."""
    if m < 1:
        raise ValueError("m >= 1")
    return list(_cyclo(m))


def center(x, q):
    """Centered representative in (-q/2, q/2]; works on ints and object arrays."""
    if isinstance(x, np.ndarray):
        r = np.mod(x, q)
        return np.where(r > q // 2, r - q, r)
    r = x % q
    return r - q if r > q // 2 else r


# --------------------------------------------------------------------------
# quotient ring Z_q[X]/(f)
# --------------------------------------------------------------------------

class PolyRing:
    """R_q = Z_q[X] / (f), elements are length-n numpy object arrays.

    Parameters
    ----------
    m : cyclotomic index; the modulus is Phi_m (n = phi(m)).
    q : coefficient modulus (any integer >= 2), or None for Z[X]/(f).
    modulus : explicit monic modulus polynomial instead of Phi_m.

    ``PolyRing(m=2*N, q=q)`` is the usual negacyclic ring Z_q[X]/(X^N+1).
    """

    def __init__(self, m: Optional[int] = None, q: Optional[int] = None,
                 modulus: Optional[Sequence[int]] = None):
        if modulus is None:
            if m is None:
                raise ValueError("give m or modulus")
            modulus = cyclotomic_poly(m)
        self.m = m
        self.q = q
        self.f = [int(c) for c in modulus]
        if self.f[-1] != 1:
            raise ValueError("modulus must be monic")
        self.n = len(self.f) - 1
        self.negacyclic = self.f == [1] + [0] * (self.n - 1) + [1]

    # -- construction ----------------------------------------------------
    def __repr__(self):
        return f"PolyRing(m={self.m}, n={self.n}, q={self.q})"

    def zero(self):
        return np.array([0] * self.n, dtype=object)

    def one(self):
        v = self.zero()
        v[0] = 1
        return v

    def monomial(self, k: int):
        """X^k reduced in the ring (k may be >= n or negative for Phi_m rings with m set)."""
        if self.m is not None:
            k %= self.m
        coeffs = [0] * k + [1]
        return self.from_list(coeffs)

    def from_list(self, a: Iterable[int]):
        a = [int(x) for x in a]
        if len(a) > self.n:
            a = poly_mod(a, self.f, None)
        v = np.array(a + [0] * (self.n - len(a)), dtype=object)
        return self.reduce(v)

    def reduce(self, v):
        v = np.asarray(v, dtype=object)
        if self.q:
            v = np.mod(v, self.q)
        return v

    def centered(self, v):
        return center(np.asarray(v, dtype=object), self.q) if self.q else v

    def uniform(self, rng: Optional[random.Random] = None):
        rng = rng or random
        return np.array([rng.randrange(self.q) for _ in range(self.n)], dtype=object)

    # -- arithmetic ------------------------------------------------------
    def add(self, a, b):
        return self.reduce(np.asarray(a, dtype=object) + np.asarray(b, dtype=object))

    def sub(self, a, b):
        return self.reduce(np.asarray(a, dtype=object) - np.asarray(b, dtype=object))

    def neg(self, a):
        return self.reduce(-np.asarray(a, dtype=object))

    def scalar(self, a, c):
        return self.reduce(np.asarray(a, dtype=object) * c)

    def _full_product(self, a, b):
        a = np.asarray(a, dtype=object)
        b = np.asarray(b, dtype=object)
        out = np.zeros(len(a) + len(b) - 1, dtype=object)
        for i in range(len(a)):
            if a[i] != 0:
                out[i:i + len(b)] += a[i] * b
        return out

    def mul(self, a, b):
        full = self._full_product(a, b)
        n = self.n
        if self.negacyclic:
            res = full[:n].copy()
            res[: len(full) - n] -= full[n:]
            return self.reduce(res)
        return self.reduce(self._reduce_full(full))

    def _reduce_full(self, full):
        # generic reduction mod monic f (object arrays, top-down)
        full = full.copy()
        n, f = self.n, self.f
        for i in range(len(full) - 1, n - 1, -1):
            c = full[i]
            if c != 0:
                for j in range(n):
                    if f[j]:
                        full[i - n + j] -= c * f[j]
                full[i] = 0
        return full[:n]

    def pow(self, a, e: int):
        r = self.one()
        while e:
            if e & 1:
                r = self.mul(r, a)
            a = self.mul(a, a)
            e >>= 1
        return r

    def automorphism(self, a, k: int):
        """sigma_k : X -> X^k (requires self.m set, gcd(k, m) = 1)."""
        if self.m is None:
            raise ValueError("automorphism needs a cyclotomic ring")
        a = np.asarray(a, dtype=object)
        m, n = self.m, self.n
        k %= m
        if self.negacyclic:  # X^N = -1, m = 2N
            out = np.zeros(n, dtype=object)
            for i in range(n):
                j = i * k % m
                if j < n:
                    out[j] += a[i]
                else:
                    out[j - n] -= a[i]
            return self.reduce(out)
        big = np.zeros(m, dtype=object)
        for i in range(n):
            big[i * k % m] += a[i]
        return self.reduce(self._reduce_full(big))

    def to_list(self, a) -> List[int]:
        return [int(x) for x in a]

    def inf_norm(self, a) -> int:
        c = self.centered(a)
        return int(max(abs(int(x)) for x in c)) if len(c) else 0

    def change_modulus(self, q_new: Optional[int]) -> "PolyRing":
        return PolyRing(m=self.m, q=q_new, modulus=self.f)


def _selftest():  # pragma: no cover
    assert cyclotomic_poly(12) == [1, 0, -1, 0, 1]
    R = PolyRing(m=16, q=97)
    a = R.from_list([1, 2, 3])
    assert list(R.automorphism(R.automorphism(a, 3), 11)) == list(a)  # 3*11=33=1 mod 16
    print("poly ok")


if __name__ == "__main__":  # pragma: no cover
    _selftest()
