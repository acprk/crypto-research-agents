# TOY: not secure
"""BKZ behaviour simulators working on Gram--Schmidt log-profiles.

* :func:`gsa_log_profile` -- geometric series assumption.
* :func:`bkz_simulate` -- Chen--Nguyen style simulator (Y. Chen, P. Q.
  Nguyen, "BKZ 2.0: Better lattice security estimates", ASIACRYPT 2011).
  Simplification: the Gaussian heuristic is used for *all* block sizes; CN11
  replace it by an HKZ-average table for blocks < 45, so the last ~45 entries
  of the simulated profile are less accurate here.  The head of the profile
  (hence the root-Hermite factor) is the quantity of interest.

Profiles are natural logs of ||b_i*||.
"""
from __future__ import annotations

import math
from typing import List, Sequence

from .estimate import delta_bkz

__all__ = ["log_gh", "gsa_log_profile", "bkz_simulate", "root_hermite_from_profile",
           "qary_lwe_profile"]


def log_gh(dim: int, log_vol: float = 0.0) -> float:
    """log of Gaussian-heuristic length: Gamma(d/2+1)^(1/d) / sqrt(pi) * vol^(1/d)."""
    return (math.lgamma(dim / 2 + 1) - dim / 2 * math.log(math.pi) + log_vol) / dim


def gsa_log_profile(d: int, log_vol: float, beta: float) -> List[float]:
    ld = math.log(delta_bkz(beta))
    return [(d - 1 - 2 * i) * ld + log_vol / d for i in range(d)]


def qary_lwe_profile(n: int, m: int, q: int) -> List[float]:
    """Profile of the q-ary basis [[qI_m, 0], [A^T, I_n]]-type LWE lattice (dim m+n, vol q^m)."""
    lq = math.log(q)
    return [lq] * m + [0.0] * n


def bkz_simulate(profile: Sequence[float], beta: int, tours: int = 8) -> List[float]:
    l = list(profile)
    d = len(l)
    for _ in range(tours):
        new = [0.0] * d
        phi = True
        for k in range(d - 1):
            bs = min(beta, d - k)
            f = k + bs
            log_v = sum(l[:f]) - sum(new[:k])
            g = log_gh(bs, log_v)
            if phi:
                if g < l[k]:
                    new[k] = g
                    phi = False
                else:
                    new[k] = l[k]
            else:
                new[k] = g
        new[d - 1] = sum(l) - sum(new[:d - 1])
        if phi:
            break
        l = new
    return l


def root_hermite_from_profile(profile: Sequence[float]) -> float:
    d = len(profile)
    return math.exp((profile[0] - sum(profile) / d) / (d - 1))
