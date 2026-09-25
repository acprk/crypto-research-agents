"""Robust statistics for benchmark samples.

Conventions
-----------
* Report the **median**, never the mean, as the headline number.
* Report dispersion as the **IQR** (Q3 - Q1) and, when comparing, a **bootstrap
  confidence interval** of the speed-up ratio of medians.
* All random resampling is seeded so that a table can be regenerated bit-exactly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np


def _arr(xs: Sequence[float]) -> np.ndarray:
    a = np.asarray(list(xs), dtype=float)
    if a.size == 0:
        raise ValueError("empty sample")
    if not np.all(np.isfinite(a)):
        raise ValueError("sample contains NaN/inf")
    return a


def median(xs: Sequence[float]) -> float:
    return float(np.median(_arr(xs)))


def quantile(xs: Sequence[float], q: float) -> float:
    """Linear-interpolation quantile (numpy default, a.k.a. type 7)."""
    return float(np.quantile(_arr(xs), q))


def iqr(xs: Sequence[float]) -> float:
    a = _arr(xs)
    return float(np.quantile(a, 0.75) - np.quantile(a, 0.25))


def bootstrap_ci(
    xs: Sequence[float],
    stat=np.median,
    level: float = 0.95,
    n_boot: int = 2000,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI of ``stat`` (default: median)."""
    a = _arr(xs)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, a.size, size=(n_boot, a.size))
    boots = np.apply_along_axis(stat, 1, a[idx])
    lo = (1.0 - level) / 2.0
    return float(np.quantile(boots, lo)), float(np.quantile(boots, 1.0 - lo))


@dataclass
class Summary:
    n: int
    median: float
    q1: float
    q3: float
    iqr: float
    min: float
    max: float
    ci_low: float
    ci_high: float

    def to_dict(self) -> dict:
        return asdict(self)


def summarize(xs: Sequence[float], level: float = 0.95, seed: int = 0) -> Summary:
    a = _arr(xs)
    lo, hi = bootstrap_ci(a, level=level, seed=seed)
    q1, q3 = float(np.quantile(a, 0.25)), float(np.quantile(a, 0.75))
    return Summary(
        n=int(a.size),
        median=float(np.median(a)),
        q1=q1,
        q3=q3,
        iqr=q3 - q1,
        min=float(a.min()),
        max=float(a.max()),
        ci_low=lo,
        ci_high=hi,
    )


@dataclass
class Speedup:
    ratio: float  # median(baseline) / median(candidate)
    ci_low: float
    ci_high: float
    n_baseline: int
    n_candidate: int

    def to_dict(self) -> dict:
        return asdict(self)

    def fmt(self, digits: int = 2) -> str:
        return f"{self.ratio:.{digits}f}x [{self.ci_low:.{digits}f}, {self.ci_high:.{digits}f}]"


def speedup(
    baseline: Sequence[float],
    candidate: Sequence[float],
    level: float = 0.95,
    n_boot: int = 2000,
    seed: int = 0,
    paired: bool = False,
) -> Speedup:
    """Speed-up of ``candidate`` over ``baseline`` = median(baseline)/median(candidate).

    ``paired=True`` resamples index pairs jointly (use it for interleaved runs where
    round *i* of A and B shared machine conditions); requires equal lengths.
    """
    b, c = _arr(baseline), _arr(candidate)
    if np.any(c <= 0) or np.any(b <= 0):
        raise ValueError("times must be positive")
    rng = np.random.default_rng(seed)
    ratio = float(np.median(b) / np.median(c))
    if paired:
        if b.size != c.size:
            raise ValueError("paired bootstrap needs equal-length samples")
        idx = rng.integers(0, b.size, size=(n_boot, b.size))
        boots = np.median(b[idx], axis=1) / np.median(c[idx], axis=1)
    else:
        ib = rng.integers(0, b.size, size=(n_boot, b.size))
        ic = rng.integers(0, c.size, size=(n_boot, c.size))
        boots = np.median(b[ib], axis=1) / np.median(c[ic], axis=1)
    lo = (1.0 - level) / 2.0
    return Speedup(
        ratio=ratio,
        ci_low=float(np.quantile(boots, lo)),
        ci_high=float(np.quantile(boots, 1.0 - lo)),
        n_baseline=int(b.size),
        n_candidate=int(c.size),
    )


def relative_spread(xs: Sequence[float]) -> float:
    """IQR / median -- a quick noise indicator; > 0.10 usually means a noisy machine."""
    m = median(xs)
    return iqr(xs) / m if m else float("inf")


if __name__ == "__main__":  # self-check
    s = summarize([1.0, 2.0, 3.0, 4.0, 100.0])
    assert s.median == 3.0 and s.iqr == 2.0, s
    sp = speedup([10, 11, 9, 10], [5, 5, 6, 4])
    assert abs(sp.ratio - 2.0) < 1e-9, sp
    print("stats self-check OK:", s, sp.fmt())
