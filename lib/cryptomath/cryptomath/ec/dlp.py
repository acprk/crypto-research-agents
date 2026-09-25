"""Generic discrete-log algorithms for attack experiments on small groups.

Work with any object exposing the ``groups`` interface (``op``, ``exp``,
``inv``, ``identity``, ``order``, ``key``).  Expected costs: BSGS
O(sqrt n) time and memory; Pollard rho O(sqrt n) time, O(1) memory;
Pohlig–Hellman reduces to the prime factors of the order.

References
----------
* D. Shanks, "Class number, a theory of factorization and genera", 1971 (BSGS).
* J. M. Pollard, "Monte Carlo methods for index computation (mod p)",
  Math. Comp. 1978 (rho).
* E. Teske, "Speeding up Pollard's rho method for computing discrete
  logarithms", ANTS 1998 (r-adding walks).
* S. Pohlig, M. Hellman, "An improved algorithm for computing logarithms
  over GF(p) ...", IEEE Trans. IT 1978.
* V. Shoup, "Lower bounds for discrete logarithms and related problems",
  EUROCRYPT 1997 (generic-group lower bound Omega(sqrt n)).
"""
from __future__ import annotations

import math
import random

from sympy import factorint
from sympy.ntheory.modular import crt


def bsgs(group, g, h, n: int | None = None):
    """Return x in [0, n) with g^x = h, or None.  Uses ceil(sqrt n) memory."""
    n = n if n is not None else group.order
    m = math.isqrt(n - 1) + 1 if n > 1 else 1
    table = {}
    e = group.identity
    for j in range(m):
        table.setdefault(group.key(e), j)
        e = group.op(e, g)
    step = group.inv(group.exp(g, m))
    gamma = h
    for i in range(m + 1):
        j = table.get(group.key(gamma))
        if j is not None:
            x = (i * m + j) % n
            if group.eq(group.exp(g, x), h):
                return x
        gamma = group.op(gamma, step)
    return None


def pollard_rho(group, g, h, n: int | None = None, seed: int = 0, partitions: int = 16,
                max_restarts: int = 20):
    """Pollard rho with a Teske r-adding walk and Floyd cycle detection.

    n must be the (prime) order of g.  Returns x with g^x = h, or None.
    """
    n = n if n is not None else group.order
    rng = random.Random(seed)
    for _ in range(max_restarts):
        M = [(rng.randrange(n), rng.randrange(n)) for _ in range(partitions)]
        Mel = [group.op(group.exp(g, a), group.exp(h, b)) for a, b in M]

        def f(state):
            X, a, b = state
            i = hash(group.key(X)) % partitions
            return group.op(X, Mel[i]), (a + M[i][0]) % n, (b + M[i][1]) % n

        a0, b0 = rng.randrange(n), rng.randrange(n)
        start = (group.op(group.exp(g, a0), group.exp(h, b0)), a0, b0)
        tort, hare = f(start), f(f(start))
        for _ in range(8 * (math.isqrt(n) + 10)):
            if group.eq(tort[0], hare[0]):
                break
            tort, hare = f(tort), f(f(hare))
        else:
            continue
        # g^a1 h^b1 = g^a2 h^b2  ->  x (b1 - b2) = a2 - a1 (mod n)
        db = (tort[2] - hare[2]) % n
        if db == 0:
            continue
        da = (hare[1] - tort[1]) % n
        gd = math.gcd(db, n)
        if gd == 1:
            x = da * pow(db, -1, n) % n
            if group.eq(group.exp(g, x), h):
                return x
            continue
        # non-prime n: try all gd candidates
        if da % gd:
            continue
        x0 = (da // gd) * pow(db // gd, -1, n // gd) % (n // gd)
        for k in range(gd):
            x = x0 + k * (n // gd)
            if group.eq(group.exp(g, x), h):
                return x
    return None


def pohlig_hellman(group, g, h, n: int, solver=bsgs):
    """Reduce DLP in a group of composite order n to its prime-power factors."""
    rems, mods = [], []
    for q, e in factorint(n).items():
        qe = q ** e
        g1 = group.exp(g, n // qe)
        h1 = group.exp(h, n // qe)
        # solve g1^x = h1 in order q^e, digit by digit
        x = 0
        gq = group.exp(g1, qe // q)          # order q
        for k in range(e):
            hk = group.op(h1, group.inv(group.exp(g1, x)))
            hk = group.exp(hk, qe // q ** (k + 1))
            d = solver(group, gq, hk, q)
            if d is None:
                return None
            x += d * q ** k
        rems.append(x)
        mods.append(qe)
    r = crt(mods, rems)
    return None if r is None else int(r[0]) % n


def expected_generic_cost(n: int) -> dict:
    """Rough generic-attack cost (group operations) for a prime-order-n group."""
    return {
        "bsgs_ops": 2 * math.isqrt(n) + 2,
        "bsgs_memory": math.isqrt(n) + 1,
        "rho_ops_expected": math.sqrt(math.pi * n / 2),
        "security_bits": math.log2(n) / 2,
    }
