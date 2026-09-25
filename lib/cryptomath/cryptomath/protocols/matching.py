"""Fuzzy / threshold matching helpers (plaintext reference for fuzzy-PSI experiments).

These compute what a fuzzy-PSI or biometric-matching protocol is supposed to
output, so a secure protocol's result can be checked against it, and give
simple size estimates used in cost screening.

References
----------
* G. Garimella, M. Rosulek, J. Singh, "Structure-aware private set
  intersection, with applications to fuzzy matching", CRYPTO 2022.
* A. van Baarsen, M. Stevens, "Fuzzy private set intersection with large
  hyperballs", EUROCRYPT 2024.
"""
from __future__ import annotations

from math import comb

import numpy as np


def hamming(a, b) -> int:
    """Hamming distance of ints (bit strings) or equal-length sequences."""
    if isinstance(a, int) and isinstance(b, int):
        return bin(a ^ b).count("1")
    return int(np.count_nonzero(np.asarray(a) != np.asarray(b)))


def l2(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)))


def l2_squared(a, b) -> float:
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    return float(d @ d)


def linf(a, b) -> float:
    return float(np.max(np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float))))


def cosine_similarity(a, b) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


_DIST = {"hamming": hamming, "l2": l2, "l2sq": l2_squared, "linf": linf}


def threshold_match(a, b, t: float, metric: str = "hamming") -> bool:
    return _DIST[metric](a, b) <= t


def fuzzy_intersection(X, Y, t: float, metric: str = "hamming") -> list[tuple[int, int]]:
    """All index pairs (i, j) with dist(X[i], Y[j]) <= t (quadratic reference)."""
    f = _DIST[metric]
    return [(i, j) for i, x in enumerate(X) for j, y in enumerate(Y) if f(x, y) <= t]


def hamming_ball_size(n: int, t: int) -> int:
    """|B(n, t)| = sum_{i <= t} C(n, i): items per point if one expands the ball."""
    return sum(comb(n, i) for i in range(t + 1))


def linf_ball_size(d: int, delta: int) -> int:
    """Integer points in an L_inf ball of radius delta in dimension d: (2 delta + 1)^d."""
    return (2 * delta + 1) ** d


def grid_cells_touched(d: int, delta: int, cell: int) -> int:
    """Upper bound on grid cells of side ``cell`` hit by an L_inf ball (cell >= 2 delta): 2^d."""
    if cell < 2 * delta:
        raise ValueError("cell side should be >= 2*delta for the 2^d bound")
    return 2 ** d


def random_close_pair(n_bits: int, t: int, rng=None) -> tuple[int, int]:
    """(x, y) with Hamming distance exactly t (for tests / synthetic data)."""
    rng = rng or np.random.default_rng()
    x = int(rng.integers(0, 2 ** min(n_bits, 62))) if n_bits <= 62 else int.from_bytes(rng.bytes((n_bits + 7) // 8), "big") % (1 << n_bits)
    flips = rng.choice(n_bits, size=t, replace=False)
    y = x
    for f in flips:
        y ^= 1 << int(f)
    return x, y
