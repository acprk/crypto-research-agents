"""Integral (square) distinguishers and algebraic-degree estimation on toy SPNs.

References
----------
* J. Daemen, L. R. Knudsen, V. Rijmen, "The block cipher Square", FSE 1997.
* L. R. Knudsen, D. Wagner, "Integral cryptanalysis", FSE 2002.
* X. Lai, "Higher order derivatives and differential cryptanalysis", 1994;
  I. Dinur, A. Shamir, "Cube attacks on tweakable black box polynomials",
  EUROCRYPT 2009 (cube sums).
* C. Boura, A. Canteaut, C. De Cannière, "Higher-order differential
  properties of Keccak and Luffa", FSE 2011 (degree bound through an
  S-box layer, used in ``degree_upper_bounds``).
* Y. Todo, "Structural evaluation by generalized integral property",
  EUROCRYPT 2015 (division property -- the next tool to reach for).
"""
from __future__ import annotations

import random
from itertools import combinations

import numpy as np

from .boolean import algebraic_degree as bf_degree
from .sbox import coordinate
from .spn import ToySPN


def integral_sum(cipher, active_bits, rounds: int | None = None, const: int = 0) -> int:
    """XOR of E(x) over the affine set {const + span(active_bits)}."""
    acc = 0
    active_bits = list(active_bits)
    base = const
    for b in active_bits:
        base &= ~(1 << b)
    for m in range(1 << len(active_bits)):
        x = base
        for i, b in enumerate(active_bits):
            if (m >> i) & 1:
                x |= 1 << b
        acc ^= cipher.encrypt(x, rounds) if rounds is not None else cipher.encrypt(x)
    return acc


def balanced_bits(make_cipher, active_bits, rounds: int, trials: int = 8, seed: int = 0) -> list[int]:
    """Output bits whose integral sum was 0 for all ``trials`` random keys/constants.

    ``make_cipher(seed) -> cipher`` with ``encrypt(x, rounds)``.  Empirical: a
    bit listed here is a *candidate* balanced bit (prove it with division
    property / degree arguments before claiming).
    """
    rng = random.Random(seed)
    zero = None
    for t in range(trials):
        c = make_cipher(rng.getrandbits(32))
        s = integral_sum(c, active_bits, rounds, const=rng.getrandbits(c.B))
        zero = (~s) if zero is None else (zero & ~s)
    B = make_cipher(0).B
    return [i for i in range(B) if (zero >> i) & 1]


def square_distinguisher(block_bits: int = 16, rounds: int = 3, active_nibbles=(0,),
                         trials: int = 8, seed: int = 0) -> dict:
    """Run an integral test on ToySPN with the given active nibbles.

    Returns {'balanced_bits': [...], 'fraction': |balanced| / B}.
    A random permutation gives ~0 balanced bits once trials >= 8.
    """
    act = [4 * n + i for n in active_nibbles for i in range(4)]
    mk = lambda s: ToySPN(block_bits, rounds, seed=s)
    bal = balanced_bits(mk, act, rounds, trials=trials, seed=seed)
    return {"balanced_bits": bal, "fraction": len(bal) / block_bits}


def exact_output_degrees(cipher, rounds: int | None = None) -> list[int]:
    """Exact ANF degree (in plaintext bits) of every output bit; B <= 20."""
    B = cipher.B
    if B > 20:
        raise ValueError("only for tiny blocks")
    cb = np.array([cipher.encrypt(x, rounds) for x in range(1 << B)], dtype=np.int64)
    return [bf_degree((cb >> i) & 1) for i in range(B)]


def cube_sum_degree_lower_bound(encrypt, nbits: int, max_dim: int, samples: int = 20,
                                seed: int = 0) -> int:
    """Largest d <= max_dim for which some random d-cube has a nonzero sum.

    Since a nonzero d-th derivative implies degree >= d, this is a *lower*
    bound on the algebraic degree of ``encrypt`` (as a vectorial function).
    """
    rng = random.Random(seed)
    best = 0
    for d in range(1, max_dim + 1):
        for _ in range(samples):
            cube = rng.sample(range(nbits), d)
            const = rng.getrandbits(nbits)
            for b in cube:
                const &= ~(1 << b)
            s = 0
            for m in range(1 << d):
                x = const
                for i, b in enumerate(cube):
                    if (m >> i) & 1:
                        x |= 1 << b
                s ^= encrypt(x)
            if s:
                best = d
                break
    return best


def _product_degree(sbox, idx) -> int:
    t = np.ones(len(sbox), dtype=np.int64)
    for i in idx:
        t &= coordinate(sbox, i)
    return bf_degree(t)


def bcd_gamma(sbox) -> float:
    """gamma = max_{1 <= i <= n0-1} (n0 - i) / (n0 - delta_i) (Boura–Canteaut–De Cannière 2011).

    delta_i is the max degree of a product of i coordinates of the S-box.
    """
    n0 = (len(sbox) - 1).bit_length()
    g = 0.0
    for i in range(1, n0):
        di = max(_product_degree(sbox, c) for c in combinations(range(n0), i))
        if di >= n0:
            return float(n0 - 1)
        g = max(g, (n0 - i) / (n0 - di))
    return g


def degree_upper_bounds(sbox, block_bits: int, rounds: int) -> list[int]:
    """Upper bounds on deg(E_r), r = 1..rounds, for an SPN with this S-box layer.

    deg_{r+1} <= min(deg(S) * deg_r,  n - (n - deg_r) / gamma,  n - 1)
    (the second term is the BCD11 theorem applied to prepending one round).
    """
    from .sbox import algebraic_degree as sdeg
    ds = sdeg(sbox)
    g = bcd_gamma(sbox)
    n = block_bits
    out, d = [], 1
    for _ in range(rounds):
        cand = min(ds * d, n - 1)
        bcd = n - (n - d) / g
        d = int(min(cand, np.floor(bcd + 1e-9)))
        out.append(d)
    return out
