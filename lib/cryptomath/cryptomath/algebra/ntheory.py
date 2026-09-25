"""Elementary number theory used throughout lattice / FHE work.

Covers: factorisation of small integers, Euler phi, Carmichael lambda,
multiplicative order, primitive roots, the unit group (Z/m)^* with its
subgroups and cosets, and NTT-friendly prime search.

References
----------
* H. Cohen, *A Course in Computational Algebraic Number Theory*, GTM 138,
  Springer 1993, ch. 1 (orders, primitive roots).
* V. Shoup, *A Computational Introduction to Number Theory and Algebra*,
  2nd ed., CUP 2009 (freely available), ch. 2 and 7.
"""
from __future__ import annotations

import math
import random
from functools import reduce
from itertools import product
from typing import Dict, Iterable, List, Sequence, Tuple

__all__ = [
    "is_prime", "factorint", "divisors", "euler_phi", "carmichael_lambda",
    "mult_order", "primitive_root", "is_primitive_root", "inv_mod", "crt",
    "units", "subgroup_generated", "cosets", "coset_representatives",
    "unit_group_generators", "find_ntt_prime", "find_ntt_primes",
    "root_of_unity",
]


# --------------------------------------------------------------------------
# primality / factorisation (fine for integers < 2^64 and small cofactors)
# --------------------------------------------------------------------------

_MR_BASES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def is_prime(n: int) -> bool:
    """Deterministic Miller--Rabin for n < 3.3e24; probabilistic beyond."""
    if n < 2:
        return False
    for p in _MR_BASES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in _MR_BASES:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _pollard_rho(n: int) -> int:
    if n % 2 == 0:
        return 2
    while True:
        c = random.randrange(1, n)
        f = lambda x: (x * x + c) % n  # noqa: E731
        x = y = random.randrange(2, n)
        d = 1
        while d == 1:
            x = f(x)
            y = f(f(y))
            d = math.gcd(abs(x - y), n)
        if d != n:
            return d


def factorint(n: int) -> Dict[int, int]:
    """Prime factorisation ``{p: e}`` (trial division + Pollard rho)."""
    if n < 1:
        raise ValueError("n must be positive")
    out: Dict[int, int] = {}

    def rec(m: int) -> None:
        if m == 1:
            return
        if is_prime(m):
            out[m] = out.get(m, 0) + 1
            return
        for p in (2, 3, 5, 7, 11, 13):
            if m % p == 0:
                rec(p)
                rec(m // p)
                return
        d = _pollard_rho(m)
        rec(d)
        rec(m // d)

    rec(n)
    return dict(sorted(out.items()))


def divisors(n: int) -> List[int]:
    """Sorted list of positive divisors of n."""
    fs = factorint(n)
    ds = [1]
    for p, e in fs.items():
        ds = [d * p ** k for d in ds for k in range(e + 1)]
    return sorted(ds)


def euler_phi(n: int) -> int:
    """Euler's totient phi(n) = |(Z/n)^*| = deg Phi_n."""
    r = n
    for p in factorint(n):
        r = r // p * (p - 1)
    return r


def carmichael_lambda(n: int) -> int:
    """Exponent of (Z/n)^* (Carmichael function)."""
    if n == 1:
        return 1
    parts = []
    for p, e in factorint(n).items():
        if p == 2 and e >= 3:
            parts.append(2 ** (e - 2))
        else:
            parts.append((p - 1) * p ** (e - 1))
    return reduce(lambda a, b: a * b // math.gcd(a, b), parts, 1)


def inv_mod(a: int, m: int) -> int:
    """Modular inverse; raises ValueError if gcd(a, m) != 1."""
    return pow(a, -1, m)


def crt(residues: Sequence[int], moduli: Sequence[int]) -> Tuple[int, int]:
    """Chinese remaindering for pairwise-coprime moduli. Returns (x, M)."""
    x, M = 0, 1
    for r, m in zip(residues, moduli):
        # solve x' = x mod M, x' = r mod m
        t = ((r - x) * inv_mod(M, m)) % m
        x += M * t
        M *= m
    return x % M, M


def mult_order(a: int, m: int) -> int:
    """Multiplicative order of a modulo m (requires gcd(a, m) = 1).

    For p prime with p not dividing m, ``mult_order(p, m)`` is the residue
    degree d of p in Q(zeta_m); Phi_m splits into phi(m)/d factors mod p.
    """
    a %= m
    if math.gcd(a, m) != 1:
        raise ValueError(f"{a} is not a unit mod {m}")
    if m == 1:
        return 1
    lam = carmichael_lambda(m)
    order = lam
    for p in factorint(lam):
        while order % p == 0 and pow(a, order // p, m) == 1:
            order //= p
    return order


def is_primitive_root(g: int, m: int) -> bool:
    return math.gcd(g, m) == 1 and mult_order(g, m) == euler_phi(m)


def primitive_root(m: int) -> int:
    """Smallest generator of (Z/m)^*; raises if the group is not cyclic."""
    phi = euler_phi(m)
    if carmichael_lambda(m) != phi:
        raise ValueError(f"(Z/{m})^* is not cyclic")
    if m <= 2:
        return 1
    ps = list(factorint(phi))
    for g in range(2, m):
        if math.gcd(g, m) == 1 and all(pow(g, phi // p, m) != 1 for p in ps):
            return g
    raise RuntimeError("unreachable")


# --------------------------------------------------------------------------
# (Z/m)^* structure
# --------------------------------------------------------------------------

def units(m: int) -> List[int]:
    """Sorted list of units of Z/m."""
    return [a for a in range(1, m) if math.gcd(a, m) == 1] if m > 1 else [0]


def subgroup_generated(gens: Iterable[int], m: int) -> List[int]:
    """Sorted subgroup of (Z/m)^* generated by ``gens`` (BFS closure)."""
    gens = [g % m for g in gens]
    H = {1 % m}
    frontier = [1 % m]
    while frontier:
        nxt = []
        for h in frontier:
            for g in gens:
                x = h * g % m
                if x not in H:
                    H.add(x)
                    nxt.append(x)
        frontier = nxt
    return sorted(H)


def cosets(H: Iterable[int], m: int) -> List[List[int]]:
    """Partition (Z/m)^* into cosets aH of subgroup H (each sorted)."""
    H = sorted(set(h % m for h in H))
    seen = set()
    out = []
    for a in units(m):
        if a in seen:
            continue
        c = sorted({a * h % m for h in H})
        seen.update(c)
        out.append(c)
    return out


def coset_representatives(H: Iterable[int], m: int) -> List[int]:
    """Minimal representative of each coset of H in (Z/m)^*."""
    return [c[0] for c in cosets(H, m)]


def unit_group_generators(m: int) -> List[Tuple[int, int]]:
    """Generators of (Z/m)^* as a product of cyclic groups (via CRT).

    Returns a list of ``(g, ord(g))``; the group is the internal direct product
    of the cyclic groups <g>.  For each prime power p^e || m one gets one
    generator (two for 2^e, e>=3: -1 and 5), lifted by CRT to be 1 on the
    other prime-power components.  This is the standard decomposition used for
    hypercube slot layouts (Halevi--Shoup, "Algorithms in HElib", CRYPTO 2014,
    ePrint 2014/106).
    """
    fs = factorint(m) if m > 1 else {}
    pps = [p ** e for p, e in fs.items()]
    out = []
    for p, e in fs.items():
        q = p ** e
        others = [x for x in pps if x != q]
        local_gens: List[Tuple[int, int]] = []
        if p == 2:
            if e == 2:
                local_gens = [(3, 2)]
            elif e >= 3:
                local_gens = [(q - 1, 2), (5, 2 ** (e - 2))]
        else:
            local_gens = [(primitive_root(q), euler_phi(q))]
        for g, o in local_gens:
            res = [g] + [1] * len(others)
            G, _ = crt(res, [q] + others)
            out.append((G, o))
    return out


# --------------------------------------------------------------------------
# NTT-friendly primes
# --------------------------------------------------------------------------

def find_ntt_primes(bits: int, m: int, count: int = 1, below: int | None = None) -> List[int]:
    """Return ``count`` primes q < 2^bits (descending) with q = 1 mod m.

    Such q admit a primitive m-th root of unity, so Phi_m splits completely
    and a length-m (or negacyclic length m/2) NTT exists.
    """
    top = (1 << bits) if below is None else below
    q = top - ((top - 1) % m)  # largest value <= top with q = 1 mod m
    if q >= top:
        q -= m
    out = []
    while q > m and len(out) < count:
        if is_prime(q):
            out.append(q)
        q -= m
    if len(out) < count:
        raise ValueError("not enough NTT primes of that size")
    return out


def find_ntt_prime(bits: int, m: int) -> int:
    return find_ntt_primes(bits, m, 1)[0]


def root_of_unity(order: int, q: int) -> int:
    """A primitive ``order``-th root of unity mod prime q (order | q-1)."""
    if (q - 1) % order:
        raise ValueError(f"{order} does not divide q-1")
    g = primitive_root(q)
    return pow(g, (q - 1) // order, q)


def _all_tuples(bounds: Sequence[int]):  # small helper for hypercube enumeration
    return product(*[range(b) for b in bounds])
