# TOY: not secure
"""Exact-rational LLL for small dimensions (<= ~30) and helpers.

Implementation follows H. Cohen, *A Course in Computational Algebraic Number
Theory*, Algorithm 2.6.3, using only the Gram matrix and Fractions, so it is
exact (and slow): use it to check small examples, never for real attacks
(use fpylll for that).

Reference: A. K. Lenstra, H. W. Lenstra, L. Lovász, "Factoring polynomials
with rational coefficients", Math. Ann. 261, 1982.
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import List, Sequence, Tuple

__all__ = ["gram_schmidt", "lll_reduce", "is_lll_reduced", "root_hermite_factor",
           "primal_embedding_basis"]

Vec = List[int]


def _dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def gram_schmidt(B: Sequence[Sequence[int]]) -> Tuple[List[List[Fraction]], List[Fraction]]:
    """Return (mu, Bstar_sqnorms) of the rows of B (exact)."""
    n = len(B)
    Bs: List[List[Fraction]] = []
    mu = [[Fraction(0)] * n for _ in range(n)]
    norms: List[Fraction] = []
    for i in range(n):
        v = [Fraction(x) for x in B[i]]
        for j in range(i):
            mu[i][j] = _dot(B[i], Bs[j]) / norms[j]
            v = [a - mu[i][j] * b for a, b in zip(v, Bs[j])]
        Bs.append(v)
        norms.append(_dot(v, v))
    return mu, norms


def lll_reduce(B: Sequence[Sequence[int]], delta: Fraction = Fraction(99, 100)) -> List[Vec]:
    """LLL-reduce the rows of an integer basis B (rows linearly independent)."""
    b = [list(map(int, row)) for row in B]
    n = len(b)
    if n <= 1:
        return b
    mu = [[Fraction(0)] * n for _ in range(n)]
    Bn = [Fraction(0)] * n
    Bn[0] = Fraction(_dot(b[0], b[0]))
    k, kmax = 1, 0

    def red(k, l):
        if abs(mu[k][l]) > Fraction(1, 2):
            r = math.floor(mu[k][l] + Fraction(1, 2))
            b[k] = [x - r * y for x, y in zip(b[k], b[l])]
            mu[k][l] -= r
            for i in range(l):
                mu[k][i] -= r * mu[l][i]

    def swap(k):
        b[k], b[k - 1] = b[k - 1], b[k]
        for j in range(k - 1):
            mu[k][j], mu[k - 1][j] = mu[k - 1][j], mu[k][j]
        m_ = mu[k][k - 1]
        Bt = Bn[k] + m_ * m_ * Bn[k - 1]
        mu[k][k - 1] = m_ * Bn[k - 1] / Bt
        Bn[k] = Bn[k - 1] * Bn[k] / Bt
        Bn[k - 1] = Bt
        for i in range(k + 1, kmax + 1):
            t = mu[i][k]
            mu[i][k] = mu[i][k - 1] - m_ * t
            mu[i][k - 1] = t + mu[k][k - 1] * mu[i][k]

    while k < n:
        if k > kmax:
            kmax = k
            r = [Fraction(0)] * k
            for j in range(k):
                r[j] = Fraction(_dot(b[k], b[j])) - sum(mu[j][i] * r[i] for i in range(j))
                mu[k][j] = r[j] / Bn[j]
            Bn[k] = Fraction(_dot(b[k], b[k])) - sum(mu[k][j] * r[j] for j in range(k))
            if Bn[k] == 0:
                raise ValueError("rows are linearly dependent")
        red(k, k - 1)
        if Bn[k] < (delta - mu[k][k - 1] ** 2) * Bn[k - 1]:
            swap(k)
            k = max(1, k - 1)
            continue
        for l in range(k - 2, -1, -1):
            red(k, l)
        k += 1
    return b


def is_lll_reduced(B: Sequence[Sequence[int]], delta: Fraction = Fraction(99, 100)) -> bool:
    mu, nrm = gram_schmidt(B)
    n = len(B)
    for i in range(n):
        for j in range(i):
            if abs(mu[i][j]) > Fraction(1, 2):
                return False
    return all(nrm[k] >= (delta - mu[k][k - 1] ** 2) * nrm[k - 1] for k in range(1, n))


def root_hermite_factor(B: Sequence[Sequence[int]]) -> float:
    """(||b_1|| / vol^(1/d))^(1/(d-1)) for a full-rank basis (rows)."""
    _, nrm = gram_schmidt(B)
    d = len(B)
    log_vol = 0.5 * sum(math.log(float(x)) for x in nrm)
    return math.exp((0.5 * math.log(_dot(B[0], B[0])) - log_vol / d) / (d - 1))


def primal_embedding_basis(A, b, q: int, M: int = 1) -> List[Vec]:
    """Kannan embedding basis (rows) for LWE b = A s + e mod q (A: m x n).

    Lattice {(x, y, t)}: rows  [q e_i | 0 | 0] (i<m),  [A^T_j | e_j | 0]
    (j<n), [b | 0 | M].  Contains the short vector (e, -s, M) up to sign.
    Dimension m + n + 1 (fine for LLL only when tiny).
    """
    m = len(A)
    n = len(A[0])
    rows: List[Vec] = []
    for i in range(m):
        rows.append([q if k == i else 0 for k in range(m)] + [0] * n + [0])
    for j in range(n):
        rows.append([int(A[i][j]) % q for i in range(m)] + [1 if k == j else 0 for k in range(n)] + [0])
    rows.append([int(x) % q for x in b] + [0] * n + [M])
    return rows
