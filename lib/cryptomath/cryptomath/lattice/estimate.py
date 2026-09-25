# TOY: not secure
"""LWE security estimation: built-in first-order models + optional wrapper
around the lattice-estimator (Albrecht et al.).

Built-in models (fast, transparent, *approximate*; use the real estimator
for any number that goes into a paper):

* root-Hermite factor delta(beta) of BKZ-beta (Chen 2013 asymptotic formula
  for beta >= 50; linear interpolation from LLL's 1.0219 below),
* geometric series assumption (GSA) profile,
* core-SVP cost: 0.292 beta (classical sieve, BDGL16), 0.265 beta (quantum,
  Laarhoven 2015), 0.2075 beta ("paranoid" lower bound, ADPS16),
* primal uSVP success condition (ADPS16 / AGVW17):
      sqrt(beta) * sigma_e <= delta(beta)^(2 beta - d) * Vol(L)^(1/d)
  with Kannan embedding, d = m + n + 1 and Bai--Galbraith rescaling for
  small secrets, Vol = q^m * (sigma_e/sigma_s)^n,
* a simple dual (distinguishing) attack: shortest dual vector length
  ell = delta^m q^(n/m), advantage eps = exp(-2 pi^2 (ell sigma_e / q)^2),
  cost = 2^(c beta) * max(1, 1/eps^2).

References
----------
* Y. Chen, *Réduction de réseau et sécurité concrète du chiffrement
  complètement homomorphe*, PhD thesis, 2013 (delta(beta) formula).
* E. Alkim, L. Ducas, T. Pöppelmann, P. Schwabe, "Post-quantum key
  exchange -- a new hope", USENIX Security 2016, ePrint 2015/1092.
* M. R. Albrecht, F. Göpfert, F. Virdia, T. Wunderer, "Revisiting the
  expected cost of solving uSVP and applications to LWE", ASIACRYPT 2017,
  ePrint 2017/815.
* M. R. Albrecht, R. Player, S. Scott, "On the concrete hardness of Learning
  with Errors", J. Math. Cryptol. 2015, ePrint 2015/046.
* A. Becker, L. Ducas, N. Gama, T. Laarhoven, "New directions in nearest
  neighbor searching...", SODA 2016, ePrint 2015/1128 (0.292).
* lattice-estimator: https://github.com/malb/lattice-estimator
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional

__all__ = ["delta_bkz", "beta_for_delta", "gsa_profile", "core_svp_cost",
           "primal_usvp", "dual_simple", "estimate_lwe", "lattice_estimator_available",
           "estimate_with_lattice_estimator", "COST_MODELS"]

COST_MODELS = {"classical": 0.292, "quantum": 0.265, "paranoid": 0.2075}


def delta_bkz(beta: float) -> float:
    """Root-Hermite factor delta(beta) achieved by BKZ-beta (heuristic)."""
    if beta <= 2:
        return 1.0219
    if beta < 50:
        d50 = delta_bkz(50)
        return 1.0219 + (d50 - 1.0219) * (beta - 2) / 48.0
    b = float(beta)
    return ((math.pi * b) ** (1.0 / b) * b / (2 * math.pi * math.e)) ** (1.0 / (2 * (b - 1)))


def beta_for_delta(delta: float) -> int:
    """Smallest integer beta with delta_bkz(beta) <= delta."""
    b = 2
    while delta_bkz(b) > delta:
        b += 1
        if b > 5000:
            raise ValueError("delta too small")
    return b


def gsa_profile(d: int, log_vol: float, beta: float) -> List[float]:
    """GSA: natural-log Gram--Schmidt norms log||b_i*||, i = 0..d-1."""
    ld = math.log(delta_bkz(beta))
    return [(d - 1 - 2 * i) * ld + log_vol / d for i in range(d)]


def core_svp_cost(beta: float, model: str = "classical") -> float:
    """log2 cost of one SVP-beta call under the core-SVP model."""
    return COST_MODELS[model] * beta


def primal_usvp(n: int, q: int, sigma_e: float, sigma_s: Optional[float] = None,
                m_max: Optional[int] = None, model: str = "classical") -> Dict[str, float]:
    """Minimal beta for the primal uSVP attack (2016 estimate), optimising m.

    sigma_s: secret std dev (None = same as error, i.e. normal-form LWE).
    """
    sigma_s = sigma_e if sigma_s is None else sigma_s
    m_max = m_max or 2 * n
    nu = sigma_e / sigma_s
    lq, lnu = math.log(q), math.log(nu)
    best = None
    for beta in range(40, n + m_max + 1):
        ld = math.log(delta_bkz(beta))
        lhs = 0.5 * math.log(beta) + math.log(sigma_e)
        # try m values (coarse then local)
        for m in range(max(1, beta - n), m_max + 1, max(1, m_max // 64)):
            d = m + n + 1
            if beta > d:
                continue
            rhs = (2 * beta - d) * ld + (m * lq + n * lnu) / d
            if lhs <= rhs:
                best = (beta, m, d)
                break
        if best:
            break
    if best is None:
        return {"beta": float("inf"), "m": m_max, "d": float("inf"), "log2_cost": float("inf")}
    beta, m, d = best
    return {"beta": beta, "m": m, "d": d, "delta": delta_bkz(beta),
            "log2_cost": core_svp_cost(beta, model)}


def dual_simple(n: int, q: int, sigma_e: float, m_max: Optional[int] = None,
                model: str = "classical") -> Dict[str, float]:
    """Plain dual distinguishing attack (no secret rescaling, no hybrid)."""
    m_max = m_max or 2 * n
    best = {"log2_cost": float("inf")}
    for beta in range(40, m_max + 1, 2):
        ld = math.log(delta_bkz(beta))
        for m in range(max(beta, 1), m_max + 1, max(1, m_max // 64)):
            log_ell = m * ld + n * math.log(q) / m
            log_tau = log_ell + math.log(sigma_e) - math.log(q)
            if log_tau > 10:
                continue
            tau = math.exp(log_tau)
            log2_eps = -2 * math.pi ** 2 * tau ** 2 / math.log(2)
            cost = core_svp_cost(beta, model) + max(0.0, -2 * log2_eps)
            if cost < best["log2_cost"]:
                best = {"beta": beta, "m": m, "log2_eps": log2_eps, "log2_cost": cost}
    return best


def estimate_lwe(n: int, q: int, sigma_e: float, sigma_s: Optional[float] = None,
                 m_max: Optional[int] = None) -> Dict[str, Dict[str, float]]:
    """Summary of the built-in models (classical and quantum core-SVP)."""
    pr = primal_usvp(n, q, sigma_e, sigma_s, m_max)
    du = dual_simple(n, q, sigma_e, m_max)
    return {
        "primal_usvp": pr,
        "dual_simple": du,
        "min_classical_bits": min(pr["log2_cost"], du["log2_cost"]),
        "min_quantum_bits": min(COST_MODELS["quantum"] * pr.get("beta", float("inf")),
                                COST_MODELS["quantum"] / COST_MODELS["classical"] * du["log2_cost"]),
    }


def lattice_estimator_available() -> bool:
    try:
        import estimator  # noqa: F401  (lattice-estimator, needs Sage)
        return True
    except Exception:
        return False


def estimate_with_lattice_estimator(n: int, q: int, sigma_e: float, secret: str = "ternary",
                                    hw: Optional[int] = None, m: Optional[int] = None):
    """Call ``estimator.LWE.estimate.rough`` if lattice-estimator is importable.

    Returns the estimator's result dict, or None when unavailable (Sage and
    the estimator must be on sys.path; see baseline MANIFEST).
    """
    if not lattice_estimator_available():
        return None
    from estimator import LWE, ND  # type: ignore
    if secret == "ternary":
        Xs = ND.SparseTernary(n, hw // 2, hw - hw // 2) if hw else ND.UniformMod(3)
    elif secret == "binary":
        Xs = ND.Uniform(0, 1)
    else:
        Xs = ND.DiscreteGaussian(sigma_e)
    params = LWE.Parameters(n=n, q=q, Xs=Xs, Xe=ND.DiscreteGaussian(sigma_e),
                            m=m if m is not None else float("inf"))
    return LWE.estimate.rough(params)
