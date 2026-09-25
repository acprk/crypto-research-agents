# TOY: not secure
"""Polynomial evaluation strategies for homomorphic computation.

All evaluators use only ``+``, ``-``, ``*`` on the input ``x`` and on
Python numbers, so they work with floats, Fractions, modular ints (via a
small wrapper), toy ciphertext wrappers, or :class:`cryptomath.costmodel.Traced`
(to count nonscalar multiplications and depth).

* :func:`horner`                   d nonscalar mults, depth d
* :func:`paterson_stockmeyer`      classic PS: ~ k + d/k nonscalar mults
  (k ~ sqrt(d)), depth ~ log k + d/k
* :func:`bsgs_eval`                depth-optimal baby-step giant-step in the
  power basis: baby powers x^1..x^{2^b}, giant powers x^{2^{b+i}},
  recursive split; depth ceil(log2(d+1)) (when k is a power of two)
* :func:`bsgs_eval_chebyshev`      same in the Chebyshev basis on [-1,1]
  (used for CKKS bootstrapping, cf. Han--Ki, ePrint 2019/688; Bossuat et al.,
  EUROCRYPT 2021, ePrint 2020/1203)
* :func:`ps_nonscalar_count`, :func:`bsgs_counts` closed forms.

References
----------
* M. S. Paterson, L. J. Stockmeyer, SIAM J. Comput. 2(1), 1973.
* H. Chen, I. Chillotti, Y. Song, "Improved bootstrapping for approximate
  homomorphic encryption", EUROCRYPT 2019, ePrint 2018/1043.
* J.-P. Bossuat, C. Mouchet, J. Troncoso-Pastoriza, J.-P. Hubaux,
  "Efficient bootstrapping for approximate homomorphic encryption with
  non-sparse keys", EUROCRYPT 2021, ePrint 2020/1203.
"""
from __future__ import annotations

import math
from typing import Dict, List, Sequence

__all__ = ["horner", "powers", "paterson_stockmeyer", "bsgs_eval", "cheb_divmod",
           "chebyshev_powers", "bsgs_eval_chebyshev", "ps_nonscalar_count",
           "bsgs_counts", "eval_cheb_series"]


def _trim(c: Sequence) -> List:
    c = list(c)
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    return c


def horner(coeffs: Sequence, x):
    """sum c_i x^i by Horner (coeffs low -> high)."""
    c = _trim(coeffs)
    acc = c[-1]
    for a in reversed(c[:-1]):
        acc = acc * x + a
    return acc


def powers(x, k: int) -> Dict[int, object]:
    """{1: x, 2: x^2, ..., k: x^k} with minimal depth (x^i = x^{2^j} * x^{i-2^j})."""
    P = {1: x}
    for i in range(2, k + 1):
        hi = 1 << (i.bit_length() - 1)
        P[i] = P[hi // 2] * P[hi // 2] if hi == i else P[hi] * P[i - hi]
    return P


def _poly_from_powers(c: Sequence, P: Dict[int, object]):
    """sum c_i P[i] + c_0 using only scalar mults and additions."""
    acc = None
    for i in range(1, len(c)):
        if c[i] != 0:
            term = P[i] * c[i]
            acc = term if acc is None else acc + term
    if acc is None:
        return c[0]
    return acc + c[0] if c[0] != 0 else acc


def paterson_stockmeyer(coeffs: Sequence, x, k: int | None = None):
    """Classic PS: p(x) = sum_j q_j(x) (x^k)^j evaluated by Horner in y = x^k."""
    c = _trim(coeffs)
    d = len(c) - 1
    if d <= 1:
        return horner(c, x)
    if k is None:
        k = max(1, int(round(math.sqrt(d / 2))))
    k = min(k, d)
    P = powers(x, k)
    y = P[k]
    blocks = [c[i:i + k] for i in range(0, d + 1, k)]
    acc = _poly_from_powers(blocks[-1], P)
    for blk in reversed(blocks[:-1]):
        acc = acc * y + _poly_from_powers(blk, P)
    return acc


def bsgs_eval(coeffs: Sequence, x, baby_log: int | None = None):
    """Recursive baby-step giant-step evaluation in the power basis."""
    c = _trim(coeffs)
    d = len(c) - 1
    if d <= 1:
        return horner(c, x)
    m = max(1, math.ceil(math.log2(d + 1)))
    b = baby_log if baby_log is not None else max(1, m // 2)
    k = 1 << b
    P = powers(x, k)
    giants = {}
    g = P[k]
    i = 0
    while (k << i) <= d:
        giants[i] = g
        i += 1
        if (k << i) <= d:
            g = g * g

    def rec(cs: List, level: int):
        cs = _trim(cs)
        if len(cs) <= k:
            return _poly_from_powers(cs, P) if len(cs) > 1 else cs[0]
        # split at giant power x^{k 2^level'} with k 2^level' <= deg
        deg = len(cs) - 1
        lv = level
        while (k << lv) > deg:
            lv -= 1
        split = k << lv
        lo, hi = cs[:split], cs[split:]
        qv = rec(hi, lv - 1)
        rv = rec(lo, lv - 1)
        return giants[lv] * qv + rv

    return rec(c, max(giants) if giants else 0)


# ---------------------------------------------------------------- Chebyshev

def eval_cheb_series(c: Sequence[float], x: float) -> float:
    """Clenshaw evaluation of sum c_i T_i(x) (plaintext reference)."""
    b1 = b2 = 0.0
    for a in reversed(list(c)[1:]):
        b1, b2 = 2 * x * b1 - b2 + a, b1
    return x * b1 - b2 + c[0]


def cheb_divmod(c: Sequence, k: int):
    """Divide a Chebyshev series by T_k:  p = q * T_k + r, deg r < k.

    Uses T_i = 2 T_{i-k} T_k - T_{|i-2k|} for i > k and T_k = T_0 T_k.
    """
    c = list(c)
    d = len(c) - 1
    if d < k:
        return [0], c
    q = [0] * (d - k + 1)
    r = list(c)
    for i in range(d, k - 1, -1):
        a = r[i]
        if a == 0:
            continue
        r[i] = 0
        if i == k:
            q[0] += a
        else:
            q[i - k] += 2 * a
            r[abs(i - 2 * k)] -= a
    return q, r[:k]


def chebyshev_powers(x, k: int) -> Dict[int, object]:
    """{1: T_1(x), ..., k: T_k(x)} via T_{2n} = 2T_n^2 - 1, T_{m+n} = 2T_mT_n - T_{m-n}."""
    T = {1: x}
    for i in range(2, k + 1):
        hi = 1 << (i.bit_length() - 1)
        if hi == i:
            h = i // 2
            T[i] = (T[h] * T[h]) * 2 - 1
        else:
            a, b = hi, i - hi
            diff = a - b
            T[i] = (T[a] * T[b]) * 2 - (T[diff] if diff else 1)
    return T


def bsgs_eval_chebyshev(c: Sequence, x, baby_log: int | None = None):
    """Evaluate sum c_i T_i(x) with BSGS in the Chebyshev basis (x in [-1, 1])."""
    c = _trim(c)
    d = len(c) - 1
    if d == 0:
        return c[0]
    m = max(1, math.ceil(math.log2(d + 1)))
    b = baby_log if baby_log is not None else max(1, m // 2)
    k = 1 << b
    T = chebyshev_powers(x, min(k, max(d, 1)))
    giants = {}
    if k <= d:
        g = T[k]
        i = 0
        while (k << i) <= d:
            giants[i] = g
            i += 1
            if (k << i) <= d:
                g = (g * g) * 2 - 1   # T_{2m} = 2 T_m^2 - 1
    def rec(cs: List, lv: int):
        cs = _trim(cs)
        if len(cs) <= k:
            return _poly_from_powers(cs, T) if len(cs) > 1 else cs[0]
        deg = len(cs) - 1
        while (k << lv) > deg:
            lv -= 1
        split = k << lv
        qc, rc = cheb_divmod(cs, split)
        return giants[lv] * rec(qc, lv - 1) + rec(rc, lv - 1)

    return rec(c, max(giants) if giants else 0)


# ------------------------------------------------------------ closed forms

def ps_nonscalar_count(d: int, k: int | None = None) -> int:
    """Nonscalar mults of :func:`paterson_stockmeyer` (baby powers + Horner steps)."""
    if d <= 1:
        return 0
    if k is None:
        k = max(1, int(round(math.sqrt(d / 2))))
    k = min(k, d)
    baby = k - 1
    giant_steps = math.ceil((d + 1) / k) - 1
    # the leading block is a constant when k | d, so the first Horner step is scalar
    return baby + giant_steps - (1 if d % k == 0 else 0)


def bsgs_counts(d: int, baby_log: int | None = None) -> Dict[str, int]:
    """Nonscalar mults (upper bound) and depth of :func:`bsgs_eval` for a dense degree-d poly."""
    if d <= 1:
        return {"baby": 0, "giant": 0, "recursion": 0, "nonscalar": 0, "depth": 0}
    m = max(1, math.ceil(math.log2(d + 1)))
    b = baby_log if baby_log is not None else max(1, m // 2)
    k = 1 << b
    giants = 0
    while (k << giants) <= d:
        giants += 1
    baby = k - 1
    # recursion multiplies: one per internal node of the split tree
    blocks = math.ceil((d + 1) / k)
    return {"baby": baby, "giant": max(0, giants - 1), "recursion": max(0, blocks - 1),
            "nonscalar": baby + max(0, giants - 1) + max(0, blocks - 1),
            "depth": max(b, math.ceil(math.log2(d + 1)))}
