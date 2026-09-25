"""Arithmetic in GF(2^n) and vectorial power maps x -> x^d.

Elements are Python ints whose bit i is the coefficient of X^i in the
polynomial basis defined by an irreducible modulus.

References
----------
* R. Lidl, H. Niederreiter, *Finite Fields*, 1997 (field arithmetic).
* R. Gold, "Maximal recursive sequences with 3-valued recursive
  cross-correlation functions", IEEE Trans. IT, 1968 (Gold exponents).
* T. Kasami, "The weight enumerators for several classes of subcodes of
  2nd order binary Reed-Muller codes", Inform. Control, 1971 (Kasami exponents).
* K. Nyberg, "Differentially uniform mappings for cryptography",
  EUROCRYPT 1993 (APN power maps, inverse map).
"""
from __future__ import annotations

from math import gcd

# Default irreducible polynomials (bit i = coefficient of X^i).
DEFAULT_MODULI = {
    2: 0b111,
    3: 0b1011,
    4: 0b10011,
    5: 0b100101,
    6: 0b1000011,
    7: 0b10000011,
    8: 0x11B,          # AES polynomial X^8+X^4+X^3+X+1
    9: 0x211,          # X^9+X^4+1
    10: 0x409,         # X^10+X^3+1
    11: 0x805,         # X^11+X^2+1
    12: 0x1053,        # X^12+X^6+X^4+X+1
    13: 0x201B,        # X^13+X^4+X^3+X+1
    14: 0x4443,        # X^14+X^10+X^6+X+1
    15: 0x8003,        # X^15+X+1
    16: 0x1002D,       # X^16+X^5+X^3+X^2+1
}


def _poly_mod(a: int, m: int) -> int:
    dm = m.bit_length() - 1
    while a.bit_length() - 1 >= dm:
        a ^= m << (a.bit_length() - 1 - dm)
    return a


def _poly_mulmod(a: int, b: int, m: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if a >> (m.bit_length() - 1):
            a ^= m
    return r


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, _poly_mod(a, b)
    return a


def is_irreducible_gf2(m: int) -> bool:
    """Rabin-style irreducibility test of a binary polynomial ``m``."""
    n = m.bit_length() - 1
    if n <= 0:
        return False
    if n == 1:
        return True
    # X^(2^n) == X mod m, and gcd(X^(2^(n/r)) - X, m) == 1 for prime r | n
    def x_pow_2k(k: int) -> int:
        t = 0b10
        for _ in range(k):
            t = _poly_mulmod(t, t, m)
        return t

    if x_pow_2k(n) != 0b10:
        return False
    for r in {r for r in range(2, n + 1) if n % r == 0 and all(r % s for s in range(2, r))}:
        if _poly_gcd(m, x_pow_2k(n // r) ^ 0b10) != 1:
            return False
    return True


class GF2n:
    """The field GF(2^n) in polynomial basis.

    >>> F = GF2n(8)
    >>> F.mul(0x57, 0x83)   # FIPS-197 Sec. 4.2 example
    193
    """

    def __init__(self, n: int, modulus: int | None = None):
        if modulus is None:
            if n not in DEFAULT_MODULI:
                raise ValueError(f"no default modulus for n={n}; pass one")
            modulus = DEFAULT_MODULI[n]
        if modulus.bit_length() - 1 != n:
            raise ValueError("modulus degree must equal n")
        self.n = n
        self.modulus = modulus
        self.order = 1 << n
        self._exp = None
        self._log = None

    def add(self, a: int, b: int) -> int:
        return a ^ b

    def mul(self, a: int, b: int) -> int:
        return _poly_mulmod(a, b, self.modulus)

    def pow(self, a: int, e: int) -> int:
        if e < 0:
            a, e = self.inv(a), -e
        r = 1
        while e:
            if e & 1:
                r = self.mul(r, a)
            a = self.mul(a, a)
            e >>= 1
        return r

    def inv(self, a: int) -> int:
        """Multiplicative inverse; by convention inv(0) = 0 (as in AES)."""
        if a == 0:
            return 0
        return self.pow(a, self.order - 2)

    def trace(self, a: int) -> int:
        """Absolute trace Tr(a) = a + a^2 + ... + a^(2^(n-1)) in {0,1}."""
        t, x = 0, a
        for _ in range(self.n):
            t ^= x
            x = self.mul(x, x)
        return t & 1


def power_map(d: int, n: int, modulus: int | None = None) -> list[int]:
    """Look-up table of x -> x^d over GF(2^n) (0^d := 0)."""
    F = GF2n(n, modulus)
    return [0 if x == 0 else F.pow(x, d) for x in range(1 << n)]


def inverse_map(n: int, modulus: int | None = None) -> list[int]:
    """x -> x^(2^n - 2) (the 'patched inverse', Nyberg 1993)."""
    return power_map((1 << n) - 2, n, modulus)


def cyclotomic_class(d: int, n: int) -> set[int]:
    """{d * 2^i mod (2^n - 1)}: exponents giving linearly equivalent power maps."""
    N = (1 << n) - 1
    return {(d << i) % N for i in range(n)}


def is_gold_exponent(d: int, n: int) -> int | None:
    """Return k if d is (cyclotomic-equivalent to) the Gold exponent 2^k + 1.

    Gold maps x^(2^k+1) are APN over GF(2^n) iff gcd(k, n) = 1.
    """
    cls = cyclotomic_class(d, n)
    for k in range(1, n):
        if ((1 << k) + 1) % ((1 << n) - 1) in cls:
            return k
    return None


def is_kasami_exponent(d: int, n: int) -> int | None:
    """Return k if d is cyclotomic-equivalent to 2^(2k) - 2^k + 1 (k >= 2).

    Kasami maps are APN over GF(2^n) iff gcd(k, n) = 1.
    """
    cls = cyclotomic_class(d, n)
    for k in range(2, n):
        if ((1 << (2 * k)) - (1 << k) + 1) % ((1 << n) - 1) in cls:
            return k
    return None


def gold_is_apn(k: int, n: int) -> bool:
    """Theoretical criterion (Gold 1968; Nyberg 1993): gcd(k, n) == 1."""
    return gcd(k, n) == 1


def kasami_is_apn(k: int, n: int) -> bool:
    """Theoretical criterion (Kasami 1971; Dillon-Dobbertin 2004): gcd(k, n) == 1."""
    return gcd(k, n) == 1


def is_permutation_exponent(d: int, n: int) -> bool:
    """x^d permutes GF(2^n) iff gcd(d, 2^n - 1) == 1."""
    return gcd(d, (1 << n) - 1) == 1
