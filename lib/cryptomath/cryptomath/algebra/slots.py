"""Plaintext slots of Z_t[X]/Phi_m for t = p^e (toy CRT packing).

For p not dividing m, Phi_m factors mod p into g = phi(m)/d distinct
irreducible factors of degree d = ord_m(p); by Hensel's lemma the same
factorisation lifts to Z_{p^e}.  CRT gives the ring isomorphism

    Z_{p^e}[X]/Phi_m  ~=  prod_{i=1}^{g} Z_{p^e}[X]/F_i(X)   ("slots"),

each slot a Galois ring GR(p^e, d).  The Galois group (Z/m)^* acts on slots;
the Frobenius X -> X^p fixes every slot and acts inside it, while the quotient
(Z/m)^*/<p> permutes slots transitively.

Factors are indexed by coset representatives a of <p> in (Z/m)^*:
F_a is the minimal polynomial of zeta^a for a fixed primitive m-th root zeta.

References
----------
* N. P. Smart, F. Vercauteren, "Fully homomorphic SIMD operations",
  DCC 71(1), 2014, ePrint 2011/133.
* C. Gentry, S. Halevi, N. P. Smart, "Fully homomorphic encryption with
  polylog overhead", EUROCRYPT 2012, ePrint 2011/566.
* S. Halevi, V. Shoup, "Algorithms in HElib", CRYPTO 2014, ePrint 2014/106.
"""
from __future__ import annotations

import random
from functools import lru_cache
from typing import Dict, List, Sequence

from .finite_field import GF, random_irreducible
from .ntheory import (coset_representatives, euler_phi, factorint,
                      mult_order, subgroup_generated, units)
from .poly import (cyclotomic_poly, poly_divmod, poly_mod, poly_mul,
                   poly_inv_mod_pe, poly_sub, poly_trim, poly_add, poly_inv_mod)

__all__ = ["decomposition", "frobenius_subgroup", "quotient_generators",
           "factor_cyclotomic_mod_p", "hensel_lift_factors", "SlotEncoder"]


def decomposition(p: int, m: int) -> Dict[str, int]:
    """Splitting of prime p in Q(zeta_m).

    Returns e (ramification index), f (residue degree = ord_{m'}(p)),
    g (number of primes above p = number of plaintext slots), with m = p^v m'.
    Always e * f * g = phi(m).
    """
    v, mp = 0, m
    while mp % p == 0:
        mp //= p
        v += 1
    e = euler_phi(p ** v) if v else 1
    f = mult_order(p, mp) if mp > 1 else 1
    g = euler_phi(mp) // f
    return {"p": p, "m": m, "v": v, "m_prime": mp, "e": e, "f": f, "g": g,
            "slots": g, "phi_m": euler_phi(m)}


def frobenius_subgroup(p: int, m: int) -> List[int]:
    """The decomposition group <p> inside (Z/m)^* (p coprime to m)."""
    return subgroup_generated([p], m)


def quotient_generators(m: int, H: Sequence[int]) -> List[tuple]:
    """Greedy generators of the quotient (Z/m)^*/H with their orders.

    Returns ``[(g1, o1), (g2, o2), ...]`` such that every coset of H is
    uniquely g1^i1 g2^i2 ... H with 0 <= ij < oj (a "hypercube" layout).
    Greedy picks elements of maximal quotient order; for cyclic quotients one
    generator suffices.  (Greedy need not find the *minimal* number of
    dimensions for every m; it always returns a valid layout.)
    """
    Hs = set(h % m for h in H)
    G = units(m)
    covered = set(Hs)
    gens = []

    def quo_order(g, cov):
        o, x = 1, g
        while x not in cov:
            x = x * g % m
            o += 1
            if o > len(G):
                break
        return o

    while len(covered) < len(G):
        best, best_o = None, 0
        for g in G:
            if g in covered:
                continue
            o = quo_order(g, covered)
            if o > best_o:
                best, best_o = g, o
        gens.append((best, best_o))
        new = set()
        x = 1
        for _ in range(best_o):
            new |= {c * x % m for c in covered}
            x = x * best % m
        covered = new
    return gens


def _root_of_unity(F: GF, m: int, rng: random.Random):
    n = F.order - 1
    assert n % m == 0
    ps = list(factorint(m)) if m > 1 else []
    while True:
        x = F.random(rng)
        if x.is_zero():
            continue
        y = x ** (n // m)
        if all(y ** (m // r) != F.one for r in ps):
            return y


@lru_cache(maxsize=64)
def _factor_cached(p: int, m: int, seed: int):
    rng = random.Random(seed)
    d = mult_order(p, m)
    F = GF(p, d, modulus=random_irreducible(p, d, rng) if d > 1 else None)
    zeta = _root_of_unity(F, m, rng)
    H = frobenius_subgroup(p, m)
    reps = coset_representatives(H, m)
    factors = [tuple((zeta ** a).minpoly()) for a in reps]
    return tuple(reps), tuple(factors)


def factor_cyclotomic_mod_p(m: int, p: int, seed: int = 0):
    """Factor Phi_m mod p (p prime, p not dividing m).

    Returns (reps, factors): factors[i] is the minimal polynomial of zeta^reps[i]
    for a fixed primitive m-th root of unity zeta in GF(p^d).
    """
    if m % p == 0:
        raise ValueError("p must not divide m")
    reps, fs = _factor_cached(p, m, seed)
    return list(reps), [list(f) for f in fs]


def hensel_lift_factors(f: Sequence[int], factors: Sequence[Sequence[int]], p: int, e: int) -> List[List[int]]:
    """Lift a factorisation f = prod g_i mod p (monic, pairwise coprime) to mod p^e.

    Uses linear Hensel lifting one power of p at a time (von zur Gathen &
    Gerhard, Modern Computer Algebra, sec. 15.4).
    """
    factors = [poly_trim(g, p) for g in factors]
    if len(factors) == 1:
        return [poly_trim(f, p ** e)]
    g = factors[0]
    h = [1]
    for x in factors[1:]:
        h = poly_mul(h, x, p)
    # s g + t h = 1 mod p
    from .poly import poly_xgcd
    one, s, t = poly_xgcd(g, h, p)
    assert one == [1], "factors not coprime"
    for k in range(1, e):
        pk = p ** k
        err = poly_sub(f, poly_mul(g, h), p ** (k + 1))
        err = [c // pk % p for c in err]  # divisible by p^k
        te = poly_mul(t, err, p)
        _, dg = poly_divmod(te, g, p)
        rem = poly_sub(err, poly_mul(dg, h, p), p)
        dh, r0 = poly_divmod(rem, g, p)
        assert not r0
        g = poly_add(g, [pk * c for c in dg], p ** (k + 1))
        h = poly_add(h, [pk * c for c in dh], p ** (k + 1))
    rest = hensel_lift_factors(h, factors[1:], p, e)
    return [poly_trim(g, p ** e)] + rest


class SlotEncoder:
    """CRT slot packing for plaintext modulus t = p^e in Z_t[X]/Phi_m.

    >>> enc = SlotEncoder(m=7, p=2, e=1)   # Phi_7 = two cubics mod 2
    >>> enc.num_slots, enc.slot_degree
    (2, 3)
    >>> a = enc.encode([[1], [0, 1]]); enc.decode(a)
    [[1], [0, 1]]

    Slot values are coefficient lists of degree < d (d = ord_m(p)); plain ints
    are accepted and mean constant slot values.  TOY: O(phi(m)^2) arithmetic.
    """

    def __init__(self, m: int, p: int, e: int = 1, seed: int = 0):
        self.m, self.p, self.e = m, p, e
        self.t = p ** e
        self.phi = cyclotomic_poly(m)
        self.n = len(self.phi) - 1
        reps, fs = factor_cyclotomic_mod_p(m, p, seed)
        self.reps = reps
        self.factors = hensel_lift_factors(self.phi, fs, p, e) if e > 1 else fs
        self.num_slots = len(self.factors)
        self.slot_degree = self.n // self.num_slots
        t = self.t
        self.idempotents = []
        for i, Fi in enumerate(self.factors):
            other = [1]
            for j, Fj in enumerate(self.factors):
                if j != i:
                    other = poly_mul(other, Fj, t)
            inv = poly_inv_mod_pe(poly_mod(other, Fi, t), Fi, p, e) if e > 1 else poly_inv_mod(poly_mod(other, Fi, t), Fi, p)
            self.idempotents.append(poly_mod(poly_mul(other, inv, t), self.phi, t))

    def encode(self, slots: Sequence) -> List[int]:
        if len(slots) != self.num_slots:
            raise ValueError(f"need {self.num_slots} slot values")
        acc: List[int] = []
        for s, E in zip(slots, self.idempotents):
            s = [s] if isinstance(s, int) else list(s)
            acc = poly_add(acc, poly_mul(s, E, self.t), self.t)
        acc = poly_mod(acc, self.phi, self.t)
        return acc + [0] * (self.n - len(acc))

    def decode(self, a: Sequence[int]) -> List[List[int]]:
        out = []
        for Fi in self.factors:
            r = poly_mod(list(a), Fi, self.t)
            out.append(r if r else [0])
        return out

    def decode_constants(self, a: Sequence[int]) -> List[int]:
        """Decode assuming each slot holds a constant (degree-0) value."""
        return [s[0] for s in self.decode(a)]
