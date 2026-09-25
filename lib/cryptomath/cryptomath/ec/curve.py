# TOY: not secure (not constant time, no side-channel protection, tiny curves)
"""Short Weierstrass curves y^2 = x^3 + a x + b over prime fields.

Affine points are tuples (x, y); the point at infinity is ``None``.
Jacobian points are tuples (X, Y, Z) representing (X/Z^2, Y/Z^3); infinity has Z = 0.

References
----------
* H. Cohen, G. Frey et al., *Handbook of Elliptic and Hyperelliptic Curve
  Cryptography*, CRC 2005 (formulas, Jacobian coordinates).
* D. Hankerson, A. Menezes, S. Vanstone, *Guide to Elliptic Curve
  Cryptography*, Springer 2004.
* P. L. Montgomery, "Speeding the Pollard and elliptic curve methods of
  factorization", Math. Comp. 1987 (ladder).
* SEC 2: Recommended Elliptic Curve Domain Parameters, v2, 2010 (secp256k1).
"""
from __future__ import annotations

import random

from sympy import isprime, factorint


def legendre(a: int, p: int) -> int:
    a %= p
    if a == 0:
        return 0
    return 1 if pow(a, (p - 1) // 2, p) == 1 else -1


def sqrt_mod(a: int, p: int) -> int | None:
    """Tonelli–Shanks square root mod an odd prime p (None if non-residue)."""
    a %= p
    if a == 0:
        return 0
    if legendre(a, p) != 1:
        return None
    if p % 4 == 3:
        return pow(a, (p + 1) // 4, p)
    q, s = p - 1, 0
    while q % 2 == 0:
        q, s = q // 2, s + 1
    z = 2
    while legendre(z, p) != -1:
        z += 1
    m, c, t, r = s, pow(z, q, p), pow(a, q, p), pow(a, (q + 1) // 2, p)
    while t != 1:
        i, t2 = 0, t
        while t2 != 1:
            t2, i = t2 * t2 % p, i + 1
        b = pow(c, 1 << (m - i - 1), p)
        m, c, t, r = i, b * b % p, t * b * b % p, r * b % p
    return r


class EllipticCurve:
    """E: y^2 = x^3 + a x + b over GF(p), p > 3 prime."""

    def __init__(self, p: int, a: int, b: int, check: bool = True):
        self.p, self.a, self.b = p, a % p, b % p
        if check and (4 * self.a ** 3 + 27 * self.b ** 2) % p == 0:
            raise ValueError("singular curve")
        self._order = None

    def __repr__(self):
        return f"EllipticCurve(y^2 = x^3 + {self.a}x + {self.b} mod {self.p})"

    # --- affine ------------------------------------------------------------
    def is_on_curve(self, P) -> bool:
        if P is None:
            return True
        x, y = P
        return (y * y - (x * x * x + self.a * x + self.b)) % self.p == 0

    def neg(self, P):
        return None if P is None else (P[0], (-P[1]) % self.p)

    def add(self, P, Q):
        p = self.p
        if P is None:
            return Q
        if Q is None:
            return P
        x1, y1 = P
        x2, y2 = Q
        if x1 == x2:
            if (y1 + y2) % p == 0:
                return None
            lam = (3 * x1 * x1 + self.a) * pow(2 * y1, -1, p) % p
        else:
            lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
        x3 = (lam * lam - x1 - x2) % p
        return (x3, (lam * (x1 - x3) - y1) % p)

    def double(self, P):
        return self.add(P, P)

    def mul(self, k: int, P):
        """Left-to-right double-and-add (negative k allowed)."""
        if k < 0:
            k, P = -k, self.neg(P)
        R = None
        for bit in bin(k)[2:] if k else "":
            R = self.add(R, R)
            if bit == "1":
                R = self.add(R, P)
        return R

    def ladder(self, k: int, P):
        """Montgomery ladder (uniform operation sequence; still not constant time)."""
        R0, R1 = None, P
        for bit in bin(k)[2:] if k > 0 else "":
            if bit == "1":
                R0, R1 = self.add(R0, R1), self.add(R1, R1)
            else:
                R0, R1 = self.add(R0, R0), self.add(R0, R1)
        return R0

    # --- Jacobian ------------------------------------------------------------
    def to_jacobian(self, P):
        return (1, 1, 0) if P is None else (P[0], P[1], 1)

    def from_jacobian(self, J):
        X, Y, Z = J
        if Z % self.p == 0:
            return None
        zi = pow(Z, -1, self.p)
        return (X * zi * zi % self.p, Y * zi * zi * zi % self.p)

    def jdouble(self, J):
        p = self.p
        X, Y, Z = J
        if Z == 0 or Y == 0:
            return (1, 1, 0)
        YY = Y * Y % p
        S = 4 * X * YY % p
        M = (3 * X * X + self.a * pow(Z, 4, p)) % p
        X3 = (M * M - 2 * S) % p
        Y3 = (M * (S - X3) - 8 * YY * YY) % p
        Z3 = 2 * Y * Z % p
        return (X3, Y3, Z3)

    def jadd(self, J1, J2):
        p = self.p
        X1, Y1, Z1 = J1
        X2, Y2, Z2 = J2
        if Z1 == 0:
            return J2
        if Z2 == 0:
            return J1
        Z1Z1, Z2Z2 = Z1 * Z1 % p, Z2 * Z2 % p
        U1, U2 = X1 * Z2Z2 % p, X2 * Z1Z1 % p
        S1, S2 = Y1 * Z2 * Z2Z2 % p, Y2 * Z1 * Z1Z1 % p
        if U1 == U2:
            if S1 != S2:
                return (1, 1, 0)
            return self.jdouble(J1)
        H, R = (U2 - U1) % p, (S2 - S1) % p
        HH = H * H % p
        HHH = H * HH % p
        V = U1 * HH % p
        X3 = (R * R - HHH - 2 * V) % p
        Y3 = (R * (V - X3) - S1 * HHH) % p
        Z3 = H * Z1 * Z2 % p
        return (X3, Y3, Z3)

    def jmul(self, k: int, P):
        """Scalar multiplication in Jacobian coordinates, affine in/out."""
        if k < 0:
            k, P = -k, self.neg(P)
        J, R = self.to_jacobian(P), (1, 1, 0)
        for bit in bin(k)[2:] if k else "":
            R = self.jdouble(R)
            if bit == "1":
                R = self.jadd(R, J)
        return self.from_jacobian(R)

    # --- points & counting ---------------------------------------------------
    def lift_x(self, x: int):
        y = sqrt_mod(x ** 3 + self.a * x + self.b, self.p)
        return None if y is None else (x % self.p, y)

    def random_point(self, rng: random.Random | None = None):
        rng = rng or random.Random()
        while True:
            P = self.lift_x(rng.randrange(self.p))
            if P is not None:
                return P if rng.getrandbits(1) else self.neg(P)

    def points(self):
        """All affine points (small p only)."""
        pts = []
        for x in range(self.p):
            rhs = (x ** 3 + self.a * x + self.b) % self.p
            y = sqrt_mod(rhs, self.p)
            if y is None:
                continue
            pts.append((x, y))
            if y != 0:
                pts.append((x, self.p - y))
        return pts

    def order(self) -> int:
        """#E(F_p) = p + 1 + sum_x legendre(x^3 + ax + b) -- naive O(p)."""
        if self._order is None:
            if self.p > 10 ** 7:
                raise ValueError("naive point counting only for p <= 1e7")
            s = sum(legendre(x ** 3 + self.a * x + self.b, self.p) for x in range(self.p))
            self._order = self.p + 1 + s
        return self._order

    def point_order(self, P, n: int | None = None) -> int:
        """Order of P given a multiple n of it (default: the group order)."""
        n = n if n is not None else self.order()
        for q, e in factorint(n).items():
            for _ in range(e):
                if self.mul(n // q, P) is None:
                    n //= q
                else:
                    break
        return n


def find_prime_order_curve(p: int, seed: int = 0, max_tries: int = 10000):
    """Search random (a, b) until #E(F_p) is prime; returns (curve, generator)."""
    rng = random.Random(seed)
    for _ in range(max_tries):
        a, b = rng.randrange(p), rng.randrange(p)
        try:
            E = EllipticCurve(p, a, b)
        except ValueError:
            continue
        if isprime(E.order()):
            G = E.random_point(rng)
            return E, G
    raise RuntimeError("no prime-order curve found")


# secp256k1 (SEC 2) -- a real curve, used here only for arithmetic self-tests.
SECP256K1 = dict(
    p=2 ** 256 - 2 ** 32 - 977, a=0, b=7,
    Gx=0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    Gy=0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
    n=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141,
)


def secp256k1():
    c = SECP256K1
    return EllipticCurve(c["p"], c["a"], c["b"]), (c["Gx"], c["Gy"]), c["n"]
