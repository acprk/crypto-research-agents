# TOY: not secure
"""Bootstrapping building blocks (plaintext-level models + cost counts).

CKKS (Cheon--Han--Kim--Kim--Song, EUROCRYPT 2018, ePrint 2018/153):
  * :func:`chebyshev_interpolate` -- Chebyshev interpolant of any f on [a, b].
  * :func:`mod_reduction_sine` / :func:`mod_reduction_double_angle` --
    approximations of x -> x - round(x) near integers by sin(2 pi x)/(2 pi),
    directly or via cos with r double-angle steps (Han--Ki, CT-RSA 2020,
    ePrint 2019/688).  Returned objects evaluate on floats *or* on
    :class:`~cryptomath.costmodel.Traced` values (to count mults / depth).
  * :func:`mod_reduction_error` -- measured max error on the union of
    intervals [i - eps, i + eps], |i| <= K.

Linear transforms (Halevi--Shoup, CRYPTO 2014, ePrint 2014/106):
  * :func:`diag_matvec`, :func:`bsgs_matvec` -- diagonal method with any
    rotation back end (numpy vectors or the toy CKKS scheme).
  * :func:`bsgs_rotation_count`, :func:`fft_lintrans_cost` -- rotation /
    plaintext-mult counts, the latter for FFT-like CoeffToSlot / SlotToCoeff
    split into ``levels`` stages (Chen--Chillotti--Song, ePrint 2018/1043).

BGV/BFV digit extraction: :func:`bgv_digit_extraction_cost` combines the
Halevi--Shoup procedure (cryptomath.algebra.padic) with PS counts.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np

from ..algebra.padic import hs_digit_extraction_counts
from ..costmodel.counter import PMULT, ROT, CADD, count
from .polyeval import bsgs_eval_chebyshev, eval_cheb_series, ps_nonscalar_count

__all__ = ["chebyshev_interpolate", "ChebApprox", "mod_reduction_sine",
           "mod_reduction_double_angle", "mod_reduction_error", "NumpyRotOps",
           "CKKSRotOps", "diag_matvec", "bsgs_matvec", "bsgs_rotation_count",
           "fft_lintrans_cost", "bgv_digit_extraction_cost"]


def chebyshev_interpolate(f: Callable[[np.ndarray], np.ndarray], deg: int) -> np.ndarray:
    """Coefficients c_0..c_deg of the interpolant sum c_k T_k on [-1, 1]."""
    n = deg + 1
    j = np.arange(n)
    x = np.cos(np.pi * (j + 0.5) / n)
    y = f(x)
    c = np.array([2.0 / n * np.sum(y * np.cos(k * np.pi * (j + 0.5) / n)) for k in range(n)])
    c[0] /= 2
    return c


class ChebApprox:
    """p(x) = sum c_k T_k((x - mid)/half) on [a, b], optionally followed by
    r double-angle steps y -> 2 y^2 - 1 and a final scalar factor."""

    def __init__(self, coeffs, a: float, b: float, double_angle: int = 0, post_scale: float = 1.0):
        self.c = list(coeffs)
        self.a, self.b = a, b
        self.r = double_angle
        self.post = post_scale

    @property
    def degree(self) -> int:
        return len(self.c) - 1

    def __call__(self, x):
        mid, half = (self.a + self.b) / 2, (self.b - self.a) / 2
        u = (x - mid) * (1.0 / half)
        if isinstance(x, (float, int, np.floating)):
            y = eval_cheb_series(self.c, u)
        else:
            y = bsgs_eval_chebyshev(self.c, u)
        for _ in range(self.r):
            y = (y * y) * 2 - 1
        return y * self.post


def mod_reduction_sine(K: int, deg: int) -> ChebApprox:
    """Approximate sin(2 pi x)/(2 pi) on [-(K+1), K+1] with a degree-deg interpolant."""
    B = K + 1
    c = chebyshev_interpolate(lambda u: np.sin(2 * np.pi * u * B) / (2 * np.pi), deg)
    return ChebApprox(c, -B, B)


def mod_reduction_double_angle(K: int, deg: int, r: int) -> ChebApprox:
    """cos(2 pi (x - 1/4) / 2^r) interpolated, then r double angles -> sin(2 pi x); / 2 pi."""
    B = K + 1
    c = chebyshev_interpolate(lambda u: np.cos(2 * np.pi * (u * B - 0.25) / 2 ** r), deg)
    return ChebApprox(c, -B, B, double_angle=r, post_scale=1 / (2 * np.pi))


def mod_reduction_error(approx: Callable[[float], float], K: int, eps: float, samples: int = 2001) -> float:
    """max |approx(x) - (x - round(x))| over x in [i - eps, i + eps], |i| <= K."""
    worst = 0.0
    offs = np.linspace(-eps, eps, max(3, samples // (2 * K + 1)))
    for i in range(-K, K + 1):
        for o in offs:
            worst = max(worst, abs(approx(i + float(o)) - float(o)))
    return worst


# ------------------------------------------------------------ linear maps

class NumpyRotOps:
    """Rotation back end on plain numpy slot vectors (rotate(v, r)[j] = v[j + r])."""

    def rotate(self, v, r):
        count(ROT)
        return np.roll(v, -r)

    def mul_plain(self, v, d):
        count(PMULT)
        return v * d

    def add(self, a, b):
        count(CADD)
        return a + b

    def finish(self, v):
        return v


class CKKSRotOps:
    """Adapter running the same algorithms on the toy CKKS scheme."""

    def __init__(self, ckks, scale: Optional[float] = None):
        self.ck = ckks
        self.scale = scale or ckks.scale

    def rotate(self, ct, r):
        return self.ck.rotate(ct, r)

    def mul_plain(self, ct, d):
        return self.ck.mul_plain(ct, d, self.scale)

    def add(self, a, b):
        return self.ck.add(a, b)

    def finish(self, ct):
        return self.ck.rescale(ct)


def _diag(M: np.ndarray, i: int) -> np.ndarray:
    n = M.shape[0]
    return np.array([M[j, (j + i) % n] for j in range(n)])


def diag_matvec(M: np.ndarray, z, ops=None):
    """M z = sum_i diag_i(M) * rot(z, i)  (n - 1 rotations, n ptxt mults)."""
    ops = ops or NumpyRotOps()
    n = M.shape[0]
    acc = None
    for i in range(n):
        d = _diag(M, i)
        if not np.any(d):
            continue
        zi = z if i == 0 else ops.rotate(z, i)
        t = ops.mul_plain(zi, d)
        acc = t if acc is None else ops.add(acc, t)
    return ops.finish(acc)


def bsgs_matvec(M: np.ndarray, z, n1: Optional[int] = None, ops=None):
    """Baby-step giant-step diagonal method: n1 - 1 + n2 - 1 rotations (n = n1 n2).

    M z = sum_j rot( sum_i rot(diag_{j n1 + i}, -j n1) * rot(z, i), j n1 ).
    """
    ops = ops or NumpyRotOps()
    n = M.shape[0]
    n1 = n1 or 1 << max(0, (int(math.log2(n)) + 1) // 2)
    n2 = math.ceil(n / n1)
    baby = {0: z}
    for i in range(1, n1):
        baby[i] = ops.rotate(z, i)
    acc = None
    for j in range(n2):
        inner = None
        for i in range(n1):
            k = j * n1 + i
            if k >= n:
                break
            d = np.roll(_diag(M, k), j * n1)  # rot(diag, -j n1)
            if not np.any(d):
                continue
            t = ops.mul_plain(baby[i], d)
            inner = t if inner is None else ops.add(inner, t)
        if inner is None:
            continue
        if j:
            inner = ops.rotate(inner, j * n1)
        acc = inner if acc is None else ops.add(acc, inner)
    return ops.finish(acc)


def bsgs_rotation_count(num_diagonals: int, n1: Optional[int] = None) -> Dict[str, int]:
    n1 = n1 or max(1, int(round(math.sqrt(num_diagonals))))
    n2 = math.ceil(num_diagonals / n1)
    return {"n1": n1, "n2": n2, "rotations": (n1 - 1) + (n2 - 1), "ptxt_mults": num_diagonals}


def fft_lintrans_cost(n_slots: int, levels: int) -> Dict[str, object]:
    """Approximate cost of an FFT-like CoeffToSlot split into ``levels`` stages.

    log2(n) butterfly layers are merged into ``levels`` groups; a group of
    g layers is a sparse matrix with 2^{g+1} - 1 nonzero diagonals, evaluated
    with BSGS.  Returns per-stage and total rotations / ptxt mults; depth =
    levels.
    """
    L = int(math.log2(n_slots))
    base, extra = divmod(L, levels)
    stages = []
    for s in range(levels):
        g = base + (1 if s < extra else 0)
        diags = (1 << (g + 1)) - 1
        stages.append(dict(layers=g, diagonals=diags, **bsgs_rotation_count(diags)))
    return {"stages": stages,
            "rotations": sum(s["rotations"] for s in stages),
            "ptxt_mults": sum(s["ptxt_mults"] for s in stages),
            "depth": levels}


def bgv_digit_extraction_cost(p: int, e: int, r: int) -> Dict[str, int]:
    """HS15 digit removal: #F evaluations x PS nonscalar mults for degree-p F."""
    c = hs_digit_extraction_counts(p, e, r)
    per = ps_nonscalar_count(p)
    return {"F_evals": c["F_evals"], "nonscalar_per_F": per,
            "nonscalar_total": c["F_evals"] * per, "depth": c["depth"]}
