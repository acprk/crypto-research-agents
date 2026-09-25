# TOY: not secure
"""Error and secret distributions for LWE-type toy experiments.

Samplers use ``random.Random`` (or numpy Generator) -- NOT cryptographically
secure and NOT constant time.  They exist to generate test instances and to
provide exact variances for noise analysis.

* discrete Gaussian D_{Z,sigma,c} via rejection sampling from a bounded
  uniform (tail cut 12 sigma);  variance ~ sigma^2 for sigma >~ 1.
* centered binomial CBD_eta (Kyber style), variance eta/2.
* uniform ternary {-1,0,1} (variance 2/3), binary {0,1}, sparse ternary with
  fixed Hamming weight h (variance h/n), uniform mod q.

Convention: sigma is the *standard deviation*; the "width" s used in some
papers is s = sigma * sqrt(2 pi).

References
----------
* C. Peikert, "An efficient and parallel Gaussian sampler for lattices",
  CRYPTO 2010, ePrint 2010/088.
* J. Bos et al., "CRYSTALS-Kyber", EuroS&P 2018, ePrint 2017/634 (CBD).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional

__all__ = ["discrete_gaussian", "discrete_gaussian_vec", "centered_binomial_vec",
           "ternary_vec", "binary_vec", "sparse_ternary_vec", "uniform_vec",
           "Distribution", "GAUSSIAN", "TERNARY", "BINARY", "sparse_ternary", "cbd",
           "sigma_to_width", "width_to_sigma"]


def sigma_to_width(sigma: float) -> float:
    return sigma * math.sqrt(2 * math.pi)


def width_to_sigma(s: float) -> float:
    return s / math.sqrt(2 * math.pi)


def discrete_gaussian(sigma: float, rng: Optional[random.Random] = None, c: float = 0.0, tail: float = 12.0) -> int:
    """Sample D_{Z,sigma,c} (rho(x) = exp(-(x-c)^2 / (2 sigma^2)))."""
    rng = rng or random
    if sigma <= 0:
        return int(round(c))
    lo = int(math.floor(c - tail * sigma))
    hi = int(math.ceil(c + tail * sigma))
    while True:
        x = rng.randint(lo, hi)
        if rng.random() < math.exp(-((x - c) ** 2) / (2 * sigma * sigma)):
            return x


def discrete_gaussian_vec(n: int, sigma: float, rng: Optional[random.Random] = None) -> List[int]:
    return [discrete_gaussian(sigma, rng) for _ in range(n)]


def centered_binomial_vec(n: int, eta: int, rng: Optional[random.Random] = None) -> List[int]:
    rng = rng or random
    return [sum(rng.getrandbits(1) for _ in range(eta)) - sum(rng.getrandbits(1) for _ in range(eta)) for _ in range(n)]


def ternary_vec(n: int, rng: Optional[random.Random] = None) -> List[int]:
    rng = rng or random
    return [rng.choice((-1, 0, 1)) for _ in range(n)]


def binary_vec(n: int, rng: Optional[random.Random] = None) -> List[int]:
    rng = rng or random
    return [rng.getrandbits(1) for _ in range(n)]


def sparse_ternary_vec(n: int, h: int, rng: Optional[random.Random] = None) -> List[int]:
    rng = rng or random
    v = [0] * n
    for i in rng.sample(range(n), h):
        v[i] = rng.choice((-1, 1))
    return v


def uniform_vec(n: int, q: int, rng: Optional[random.Random] = None) -> List[int]:
    rng = rng or random
    return [rng.randrange(q) for _ in range(n)]


@dataclass(frozen=True)
class Distribution:
    """Description of a distribution for samplers *and* estimators.

    kind: 'gaussian' | 'ternary' | 'binary' | 'sparse_ternary' | 'cbd' | 'uniform'
    """
    kind: str
    param: float = 0.0  # sigma, h, eta or q

    def sample(self, n: int, rng: Optional[random.Random] = None) -> List[int]:
        if self.kind == "gaussian":
            return discrete_gaussian_vec(n, self.param, rng)
        if self.kind == "ternary":
            return ternary_vec(n, rng)
        if self.kind == "binary":
            return binary_vec(n, rng)
        if self.kind == "sparse_ternary":
            return sparse_ternary_vec(n, int(self.param), rng)
        if self.kind == "cbd":
            return centered_binomial_vec(n, int(self.param), rng)
        if self.kind == "uniform":
            return uniform_vec(n, int(self.param), rng)
        raise ValueError(self.kind)

    def variance(self, n: int = 1) -> float:
        """Per-coefficient variance (for sparse ternary: h/n)."""
        if self.kind == "gaussian":
            return self.param ** 2
        if self.kind == "ternary":
            return 2.0 / 3.0
        if self.kind == "binary":
            return 0.25
        if self.kind == "sparse_ternary":
            return self.param / n
        if self.kind == "cbd":
            return self.param / 2.0
        if self.kind == "uniform":
            return (self.param ** 2 - 1) / 12.0
        raise ValueError(self.kind)

    def mean(self) -> float:
        return 0.5 if self.kind == "binary" else 0.0

    def stddev(self, n: int = 1) -> float:
        return math.sqrt(self.variance(n))


GAUSSIAN = lambda sigma=3.19: Distribution("gaussian", sigma)  # noqa: E731
TERNARY = Distribution("ternary")
BINARY = Distribution("binary")
sparse_ternary = lambda h: Distribution("sparse_ternary", h)  # noqa: E731
cbd = lambda eta: Distribution("cbd", eta)  # noqa: E731
