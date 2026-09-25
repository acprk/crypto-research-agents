"""Boolean functions f: F_2^n -> F_2 given by truth tables.

Convention: ``tt[x]`` is f(x) where the integer x encodes (x_0, ..., x_{n-1})
with x_i = bit i.  ANF coefficient ``anf[u]`` multiplies the monomial
prod_{i in u} x_i.

References
----------
* C. Carlet, *Boolean Functions for Cryptography and Coding Theory*,
  Cambridge Univ. Press, 2021 (all notions here).
* O. S. Rothaus, "On 'bent' functions", J. Comb. Theory A, 1976.
* T. Siegenthaler, "Correlation-immunity of nonlinear combining functions
  for cryptographic applications", IEEE Trans. IT, 1984.
* G.-Z. Xiao, J. L. Massey, "A spectral characterization of
  correlation-immune combining functions", IEEE Trans. IT, 1988.
* W. Meier, E. Pasalic, C. Carlet, "Algebraic attacks and decomposition of
  Boolean functions", EUROCRYPT 2004 (algebraic immunity).
"""
from __future__ import annotations

from itertools import combinations

import numpy as np


def _as_tt(tt) -> tuple[np.ndarray, int]:
    a = np.asarray(tt, dtype=np.int64).ravel() & 1
    n = int(a.size).bit_length() - 1
    if a.size != 1 << n:
        raise ValueError("truth table length must be a power of two")
    return a, n


def popcount(x: int) -> int:
    return bin(x).count("1")


def mobius(tt) -> np.ndarray:
    """Binary Möbius transform (its own inverse): truth table <-> ANF."""
    a, n = _as_tt(tt)
    a = a.copy()
    h = 1
    while h < a.size:
        a = a.reshape(-1, 2, h)
        a[:, 1, :] ^= a[:, 0, :]
        a = a.reshape(-1)
        h <<= 1
    return a


def tt_to_anf(tt) -> np.ndarray:
    return mobius(tt)


def anf_to_tt(anf) -> np.ndarray:
    return mobius(anf)


def algebraic_degree(tt) -> int:
    """Degree of the ANF (the zero function is given degree 0)."""
    anf = mobius(tt)
    nz = np.nonzero(anf)[0]
    if nz.size == 0:
        return 0
    return max(popcount(int(u)) for u in nz)


def anf_string(tt, var: str = "x") -> str:
    """Human-readable ANF, e.g. ``x0*x1 + x2 + 1``."""
    anf = mobius(tt)
    terms = []
    for u in np.nonzero(anf)[0]:
        u = int(u)
        if u == 0:
            terms.append("1")
        else:
            terms.append("*".join(f"{var}{i}" for i in range(u.bit_length()) if u >> i & 1))
    terms.sort(key=lambda s: (-s.count("*"), s))
    return " + ".join(terms) if terms else "0"


def fwht(values) -> np.ndarray:
    """Fast Walsh–Hadamard transform of an integer vector (no normalisation)."""
    a = np.array(values, dtype=np.int64).ravel()
    h = 1
    while h < a.size:
        a = a.reshape(-1, 2, h)
        x, y = a[:, 0, :].copy(), a[:, 1, :].copy()
        a[:, 0, :] = x + y
        a[:, 1, :] = x - y
        a = a.reshape(-1)
        h <<= 1
    return a


def walsh(tt) -> np.ndarray:
    """Walsh spectrum W_f(a) = sum_x (-1)^(f(x) + a.x)."""
    a, _ = _as_tt(tt)
    return fwht(1 - 2 * a)


def is_balanced(tt) -> bool:
    return int(walsh(tt)[0]) == 0


def nonlinearity(tt) -> int:
    """NL(f) = 2^(n-1) - max|W_f| / 2."""
    a, n = _as_tt(tt)
    return (1 << (n - 1)) - int(np.max(np.abs(walsh(a)))) // 2


def is_bent(tt) -> bool:
    """Rothaus 1976: |W_f(a)| = 2^(n/2) for all a (n even)."""
    a, n = _as_tt(tt)
    if n % 2:
        return False
    return bool(np.all(np.abs(walsh(a)) == (1 << (n // 2))))


def correlation_immunity(tt) -> int:
    """Largest t with W_f(a) = 0 for all 1 <= wt(a) <= t (Xiao–Massey 1988)."""
    a, n = _as_tt(tt)
    W = walsh(a)
    wts = np.array([popcount(i) for i in range(1 << n)])
    t = 0
    for k in range(1, n + 1):
        if np.all(W[wts == k] == 0):
            t = k
        else:
            break
    return t


def resiliency(tt) -> int:
    """Resiliency order (balanced and t-CI); -1 if unbalanced."""
    if not is_balanced(tt):
        return -1
    return correlation_immunity(tt)


def autocorrelation(tt) -> np.ndarray:
    """r_f(a) = sum_x (-1)^(f(x) + f(x+a)) via Wiener–Khinchin (W^2 transformed)."""
    W = walsh(tt)
    return fwht(W * W) // W.size


def _gf2_rank(rows: list[int]) -> int:
    """Rank of GF(2) row vectors encoded as ints."""
    rank = 0
    rows = list(rows)
    pivots: dict[int, int] = {}
    for r in rows:
        while r:
            p = r.bit_length() - 1
            if p in pivots:
                r ^= pivots[p]
            else:
                pivots[p] = r
                rank += 1
                break
    return rank


def _has_annihilator(support: list[int], n: int, d: int) -> bool:
    """Is there a nonzero g with deg g <= d vanishing on ``support``?"""
    monos = [sum(1 << i for i in c) for k in range(d + 1) for c in combinations(range(n), k)]
    # matrix: rows = monomials, columns = support points; g exists iff rank < #monos
    # (equivalently, columns = points, kernel of evaluation map on coefficient space)
    rows = []
    for m in monos:
        v = 0
        for j, x in enumerate(support):
            if x & m == m:
                v |= 1 << j
        rows.append(v)
    return _gf2_rank(rows) < len(monos)


def algebraic_immunity(tt) -> int:
    """AI(f) = min deg of nonzero g with f*g = 0 or (f+1)*g = 0 (small n only)."""
    a, n = _as_tt(tt)
    supp1 = [int(x) for x in np.nonzero(a == 1)[0]]
    supp0 = [int(x) for x in np.nonzero(a == 0)[0]]
    for d in range(0, n + 1):
        # g annihilates f  <=> g vanishes on supp(f)
        if _has_annihilator(supp1, n, d) or _has_annihilator(supp0, n, d):
            return d
    return n


def boolean_from_callable(func, n: int) -> np.ndarray:
    """Truth table of ``func(bits)`` where bits = [x_0..x_{n-1}]."""
    return np.array([func([(x >> i) & 1 for i in range(n)]) & 1 for x in range(1 << n)], dtype=np.int64)


def majority(n: int) -> np.ndarray:
    """Majority function (optimal algebraic immunity ceil(n/2), Dalai et al. 2006)."""
    return np.array([1 if popcount(x) > n // 2 else 0 for x in range(1 << n)], dtype=np.int64)
