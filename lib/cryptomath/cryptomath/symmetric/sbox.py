"""S-box (vectorial Boolean function) analysis: DDT, LAT, BCT and friends.

An S-box is a list/array ``S`` of length 2^n with values in [0, 2^m).

References
----------
* E. Biham, A. Shamir, "Differential cryptanalysis of DES-like
  cryptosystems", J. Cryptology 1991 (DDT).
* M. Matsui, "Linear cryptanalysis method for DES cipher", EUROCRYPT 1993 (LAT).
* K. Nyberg, "Differentially uniform mappings for cryptography", EUROCRYPT 1993.
* C. Cid, T. Huang, T. Peyrin, Y. Sasaki, L. Song, "Boomerang Connectivity
  Table: a new cryptanalysis tool", EUROCRYPT 2018 (BCT).
* C. Boura, A. Canteaut, "On the boomerang uniformity of cryptographic
  S-boxes", ToSC 2018 (boomerang uniformity).
* A. Bogdanov et al., "PRESENT: an ultra-lightweight block cipher", CHES 2007.
* J. Daemen, V. Rijmen, *The Design of Rijndael*, Springer 2002 (branch number).
"""
from __future__ import annotations

import numpy as np

from .boolean import algebraic_degree as _bf_degree
from .boolean import fwht, popcount

PRESENT_SBOX = [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]
# GIFT S-box (Banik et al., CHES 2017)
GIFT_SBOX = [0x1, 0xA, 0x4, 0xC, 0x6, 0xF, 0x3, 0x9, 0x2, 0xD, 0xB, 0x7, 0x5, 0x0, 0x8, 0xE]
IDENTITY4 = list(range(16))


def _arr(S) -> tuple[np.ndarray, int, int]:
    s = np.asarray(S, dtype=np.int64).ravel()
    n = int(s.size).bit_length() - 1
    if s.size != 1 << n:
        raise ValueError("S-box length must be a power of two")
    m = max(1, int(s.max()).bit_length()) if s.size else 1
    return s, n, max(m, 1)


def out_bits(S, m: int | None = None) -> int:
    return m if m is not None else _arr(S)[2]


def ddt(S, m: int | None = None) -> np.ndarray:
    """Difference distribution table D[a, b] = #{x : S(x) ^ S(x ^ a) = b}."""
    s, n, mm = _arr(S)
    m = mm if m is None else m
    N, M = 1 << n, 1 << m
    x = np.arange(N)
    D = np.zeros((N, M), dtype=np.int64)
    for a in range(N):
        D[a] = np.bincount(s ^ s[x ^ a], minlength=M)
    return D


def lat(S, m: int | None = None) -> np.ndarray:
    """Linear approximation table L[a, b] = #{x : a.x = b.S(x)} - 2^(n-1).

    Correlation of the approximation is c = 2 L[a, b] / 2^n.
    """
    s, n, mm = _arr(S)
    m = mm if m is None else m
    N, M = 1 << n, 1 << m
    L = np.zeros((N, M), dtype=np.int64)
    parity = np.array([popcount(v) & 1 for v in range(M)], dtype=np.int64)
    for b in range(M):
        f = parity[s & b]                 # component function b.S(x)
        L[:, b] = fwht(1 - 2 * f) // 2   # W_{b.S}(a) / 2
    return L


def walsh_spectrum(S, m: int | None = None) -> np.ndarray:
    """W[a, b] = sum_x (-1)^(b.S(x) + a.x) (= 2 * LAT)."""
    return 2 * lat(S, m)


def inverse_sbox(S) -> list[int]:
    s = list(int(v) for v in S)
    inv = [0] * len(s)
    if sorted(s) != list(range(len(s))):
        raise ValueError("S-box is not a permutation")
    for x, y in enumerate(s):
        inv[y] = x
    return inv


def is_permutation(S) -> bool:
    return sorted(int(v) for v in S) == list(range(len(S)))


def bct(S) -> np.ndarray:
    """Boomerang connectivity table (Cid et al. 2018), bijective S only.

    BCT[a, b] = #{x : S^-1(S(x) ^ b) ^ S^-1(S(x ^ a) ^ b) = a}.
    """
    s, n, _ = _arr(S)
    inv = np.asarray(inverse_sbox(S), dtype=np.int64)
    N = 1 << n
    x = np.arange(N)
    B = np.zeros((N, N), dtype=np.int64)
    bcol = np.arange(N)[:, None]
    left = inv[s[None, :] ^ bcol]                  # [b, x] -> S^-1(S(x) ^ b)
    for a in range(N):
        right = inv[s[x ^ a][None, :] ^ bcol]
        B[a] = np.count_nonzero((left ^ right) == a, axis=1)
    return B


def differential_uniformity(S, m: int | None = None) -> int:
    """max_{a != 0, b} DDT[a, b]."""
    return int(ddt(S, m)[1:].max())


def is_apn(S) -> bool:
    """Almost perfect nonlinear: differential uniformity 2."""
    return differential_uniformity(S) == 2


def linearity(S, m: int | None = None) -> int:
    """max_{a, b != 0} |W_S(a, b)|."""
    return int(np.abs(walsh_spectrum(S, m)[:, 1:]).max())


def nonlinearity(S, m: int | None = None) -> int:
    """NL(S) = 2^(n-1) - linearity / 2 (AES S-box: 112)."""
    _, n, _ = _arr(S)
    return (1 << (n - 1)) - linearity(S, m) // 2


def boomerang_uniformity(S) -> int:
    """max_{a, b != 0} BCT[a, b] (Boura–Canteaut 2018; AES S-box: 6)."""
    return int(bct(S)[1:, 1:].max())


def coordinate(S, i: int) -> np.ndarray:
    """Truth table of output bit i."""
    s, _, _ = _arr(S)
    return (s >> i) & 1


def component(S, b: int) -> np.ndarray:
    """Truth table of the component function b.S(x)."""
    s, _, _ = _arr(S)
    return np.array([popcount(int(v) & b) & 1 for v in s], dtype=np.int64)


def algebraic_degree(S, m: int | None = None) -> int:
    """max degree of the coordinate functions (= max over all components)."""
    mm = out_bits(S, m)
    return max(_bf_degree(coordinate(S, i)) for i in range(mm))


def min_component_degree(S, m: int | None = None) -> int:
    """min over nonzero components b.S of their algebraic degree."""
    mm = out_bits(S, m)
    return min(_bf_degree(component(S, b)) for b in range(1, 1 << mm))


def differential_branch_number(S) -> int:
    """min_{x != y} wt(x ^ y) + wt(S(x) ^ S(y))."""
    s, n, _ = _arr(S)
    best = 10 ** 9
    D = ddt(S)
    for a in range(1, 1 << n):
        for b in np.nonzero(D[a])[0]:
            best = min(best, popcount(a) + popcount(int(b)))
    return best


def linear_branch_number(S) -> int:
    """min over (a, b) != 0 with LAT[a, b] != 0 of wt(a) + wt(b)."""
    L = lat(S)
    best = 10 ** 9
    for a in range(L.shape[0]):
        for b in range(L.shape[1]):
            if (a or b) and L[a, b] != 0:
                best = min(best, popcount(a) + popcount(b))
    return best


def fixed_points(S) -> list[int]:
    return [x for x, y in enumerate(S) if int(y) == x]


def sbox_report(S) -> dict:
    """One-shot summary dictionary of the standard S-box criteria."""
    rep = {
        "n": _arr(S)[1],
        "bijective": is_permutation(S),
        "differential_uniformity": differential_uniformity(S),
        "linearity": linearity(S),
        "nonlinearity": nonlinearity(S),
        "algebraic_degree": algebraic_degree(S),
        "min_component_degree": min_component_degree(S),
        "differential_branch_number": differential_branch_number(S),
        "linear_branch_number": linear_branch_number(S),
        "fixed_points": len(fixed_points(S)),
    }
    if rep["bijective"]:
        rep["boomerang_uniformity"] = boomerang_uniformity(S)
    return rep
