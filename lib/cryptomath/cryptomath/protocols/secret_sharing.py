# TOY: not secure (no authenticated channels, no malicious security, Python RNG unless given)
"""Secret sharing and Beaver-triple multiplication.

References
----------
* A. Shamir, "How to share a secret", CACM 1979.
* D. Beaver, "Efficient multiparty protocols using circuit randomization",
  CRYPTO 1991 (multiplication triples).
* T. Araki, J. Furukawa, Y. Lindell, A. Nof, K. Ohara, "High-throughput
  semi-honest secure three-party computation with an honest majority",
  CCS 2016 (replicated 3-party sharing, local multiplication).
* R. Cramer, I. Damgård, J. B. Nielsen, *Secure Multiparty Computation and
  Secret Sharing*, Cambridge 2015.
"""
from __future__ import annotations

import random
import secrets


def _rng(rng):
    return rng if rng is not None else secrets.SystemRandom()


# ---------------------------------------------------------------------------
# Shamir
# ---------------------------------------------------------------------------
def shamir_share(secret: int, t: int, n: int, p: int, rng=None) -> list[tuple[int, int]]:
    """Degree-(t-1) polynomial sharing: any t of the n shares reconstruct.

    Returns [(i, f(i)) for i = 1..n] with f(0) = secret mod p.
    """
    if not 1 <= t <= n < p:
        raise ValueError("need 1 <= t <= n < p")
    r = _rng(rng)
    coeffs = [secret % p] + [r.randrange(p) for _ in range(t - 1)]
    shares = []
    for i in range(1, n + 1):
        y = 0
        for c in reversed(coeffs):
            y = (y * i + c) % p
        shares.append((i, y))
    return shares


def lagrange_at(points: list[tuple[int, int]], x: int, p: int) -> int:
    """Interpolate the unique polynomial through ``points`` and evaluate at x."""
    acc = 0
    for j, (xj, yj) in enumerate(points):
        num, den = 1, 1
        for m, (xm, _) in enumerate(points):
            if m != j:
                num = num * (x - xm) % p
                den = den * (xj - xm) % p
        acc = (acc + yj * num * pow(den, -1, p)) % p
    return acc


def shamir_reconstruct(shares: list[tuple[int, int]], p: int) -> int:
    return lagrange_at(list(shares), 0, p)


def shamir_add(sa, sb, p: int):
    """Local addition of two sharings (same evaluation points)."""
    return [(i, (a + b) % p) for (i, a), (_, b) in zip(sa, sb)]


# ---------------------------------------------------------------------------
# additive
# ---------------------------------------------------------------------------
def additive_share(secret: int, n: int, modulus: int, rng=None) -> list[int]:
    r = _rng(rng)
    sh = [r.randrange(modulus) for _ in range(n - 1)]
    sh.append((secret - sum(sh)) % modulus)
    return sh


def additive_reconstruct(shares, modulus: int) -> int:
    return sum(shares) % modulus


# ---------------------------------------------------------------------------
# replicated 3-party (2-out-of-3)
# ---------------------------------------------------------------------------
def replicated_share(secret: int, modulus: int, rng=None) -> list[tuple[int, int]]:
    """x = x1 + x2 + x3; party i holds (x_i, x_{i+1}) (indices mod 3)."""
    x = additive_share(secret, 3, modulus, rng)
    return [(x[i], x[(i + 1) % 3]) for i in range(3)]


def replicated_reconstruct(shares, modulus: int, parties=(0, 1)) -> int:
    """Any two parties together know all three additive shares."""
    known = {}
    for i in parties:
        a, b = shares[i]
        known[i], known[(i + 1) % 3] = a, b
    if len(known) < 3:
        raise ValueError("need two distinct parties")
    return sum(known.values()) % modulus


def replicated_mul_to_additive(sx, sy, modulus: int) -> list[int]:
    """Local product: party i outputs z_i with sum z_i = x*y (Araki et al. 2016).

    (The real protocol re-randomises with a zero-sharing and re-shares.)
    """
    return [(sx[i][0] * sy[i][0] + sx[i][0] * sy[i][1] + sx[i][1] * sy[i][0]) % modulus
            for i in range(3)]


# ---------------------------------------------------------------------------
# Beaver triples
# ---------------------------------------------------------------------------
def beaver_triple(n: int, modulus: int, rng=None):
    """Trusted-dealer triple (a, b, c = ab), additively shared among n parties."""
    r = _rng(rng)
    a, b = r.randrange(modulus), r.randrange(modulus)
    c = a * b % modulus
    return (additive_share(a, n, modulus, r), additive_share(b, n, modulus, r),
            additive_share(c, n, modulus, r))


def beaver_multiply(xs, ys, triple, modulus: int):
    """Multiply additively shared x, y with a triple.

    Opens d = x - a and e = y - b; party i sets
    z_i = c_i + d b_i + e a_i (+ d e for party 0).
    Returns (z shares, transcript {'d': d, 'e': e}).
    """
    A, B, C = triple
    n = len(xs)
    d = sum((xs[i] - A[i]) for i in range(n)) % modulus
    e = sum((ys[i] - B[i]) for i in range(n)) % modulus
    z = [(C[i] + d * B[i] + e * A[i]) % modulus for i in range(n)]
    z[0] = (z[0] + d * e) % modulus
    return z, {"d": d, "e": e}
