"""Symbolic cost formulas (sympy) and algorithm comparison reports.

* :class:`CostFormula` -- ``{op: sympy expression}`` in named parameters;
  evaluate, add, scale, weight, compare asymptotically, find crossover points.
* :func:`compare` -- run two Python implementations under counters and
  produce a Markdown table (counts, weighted totals, ratio).
* A few classic formulas (Paterson--Stockmeyer, BSGS linear transform,
  Karatsuba vs schoolbook) as ready-made examples.

References
----------
* M. S. Paterson, L. J. Stockmeyer, "On the number of nonscalar
  multiplications necessary to evaluate polynomials", SIAM J. Comput. 2(1), 1973.
* S. Halevi, V. Shoup, "Algorithms in HElib", CRYPTO 2014, ePrint 2014/106
  (BSGS for linear maps).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import sympy as sp

from .counter import CMULT, DEFAULT_WEIGHTS, PMULT, ROT, Counter

__all__ = ["CostFormula", "compare", "markdown_table", "ps_formula",
           "bsgs_lintrans_formula", "karatsuba_formula", "schoolbook_formula", "symbols"]


def symbols(names: str):
    """sympy positive symbols, e.g. ``n, d = symbols('n d')``."""
    return sp.symbols(names, positive=True)


@dataclass
class CostFormula:
    terms: Dict[str, sp.Expr] = field(default_factory=dict)
    name: str = ""

    def __add__(self, other: "CostFormula") -> "CostFormula":
        t = dict(self.terms)
        for k, v in other.terms.items():
            t[k] = t.get(k, 0) + v
        return CostFormula(t, f"{self.name}+{other.name}")

    def __mul__(self, c) -> "CostFormula":
        return CostFormula({k: v * c for k, v in self.terms.items()}, self.name)

    __rmul__ = __mul__

    def weighted(self, weights: Optional[Dict[str, float]] = None) -> sp.Expr:
        w = DEFAULT_WEIGHTS if weights is None else weights
        return sp.simplify(sum(sp.nsimplify(w.get(k, 0)) * v for k, v in self.terms.items()))

    def evaluate(self, **params) -> Dict[str, float]:
        subs = {sp.Symbol(k, positive=True): v for k, v in params.items()}
        return {k: float(sp.N(v.subs(subs))) for k, v in self.terms.items()}

    def total(self, weights: Optional[Dict[str, float]] = None, **params) -> float:
        subs = {sp.Symbol(k, positive=True): v for k, v in params.items()}
        return float(sp.N(self.weighted(weights).subs(subs)))

    def leading(self, var: str, weights: Optional[Dict[str, float]] = None) -> sp.Expr:
        """Leading asymptotic term of the weighted cost in ``var`` -> oo."""
        x = sp.Symbol(var, positive=True)
        expr = sp.expand(self.weighted(weights))
        return sp.limit(expr / sp.Order(expr, (x, sp.oo)).expr, x, sp.oo) * sp.Order(expr, (x, sp.oo)).expr

    def crossover(self, other: "CostFormula", var: str, lo: float = 1, hi: float = 1e6,
                  weights: Optional[Dict[str, float]] = None, **fixed) -> Optional[float]:
        """Smallest integer value of ``var`` in [lo, hi] where self becomes cheaper than other."""
        x = sp.Symbol(var, positive=True)
        subs = {sp.Symbol(k, positive=True): v for k, v in fixed.items()}
        diff = sp.lambdify(x, (self.weighted(weights) - other.weighted(weights)).subs(subs), "math")
        v = int(lo)
        while v <= hi:
            if diff(v) < 0:
                return v
            v = v + 1 if v < 64 else int(v * 1.05) + 1
        return None


def markdown_table(rows: Dict[str, Dict[str, float]], columns: Optional[Sequence[str]] = None) -> str:
    """rows: {row_name: {col: value}} -> Markdown table string."""
    cols = list(columns) if columns else sorted({c for r in rows.values() for c in r})
    lines = ["| | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for name, r in rows.items():
        cells = []
        for c in cols:
            v = r.get(c, 0)
            cells.append(f"{v:.4g}" if isinstance(v, float) else str(v))
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def compare(fa: Callable, fb: Callable, *args, names: Tuple[str, str] = ("A", "B"),
            weights: Optional[Dict[str, float]] = None, check_equal: bool = True, **kwargs) -> Dict:
    """Run ``fa(*args)`` and ``fb(*args)`` under counters; return counts + report.

    If ``check_equal`` the two outputs must compare equal (functional
    equivalence is the first thing to screen).
    """
    with Counter(names[0]) as ca:
        ra = fa(*args, **kwargs)
    with Counter(names[1]) as cb:
        rb = fb(*args, **kwargs)
    if check_equal:
        va = getattr(ra, "value", ra)
        vb = getattr(rb, "value", rb)
        try:
            equal = bool(va == vb) if not hasattr(va, "__len__") else list(va) == list(vb)
        except Exception:
            equal = False
    else:
        equal = None
    ta, tb = ca.total(weights), cb.total(weights)
    rows = {names[0]: dict(ca.as_dict(), weighted=ta), names[1]: dict(cb.as_dict(), weighted=tb)}
    return {
        "counts": {names[0]: ca.as_dict(), names[1]: cb.as_dict()},
        "weighted": {names[0]: ta, names[1]: tb},
        "ratio": (ta / tb) if tb else float("inf"),
        "equal_outputs": equal,
        "report": markdown_table(rows),
    }


# ---- ready-made formulas -------------------------------------------------

def ps_formula() -> CostFormula:
    """Paterson--Stockmeyer nonscalar mults for degree d: about sqrt(2d) + log2(d)."""
    d = sp.Symbol("d", positive=True)
    return CostFormula({CMULT: sp.sqrt(2 * d) + sp.log(d, 2)}, "PS")


def bsgs_lintrans_formula() -> CostFormula:
    """BSGS diagonal method on n diagonals with n1 baby steps: rotations n1 + n/n1 - 2, ptxt mults n."""
    n, n1 = sp.symbols("n n1", positive=True)
    return CostFormula({ROT: n1 + n / n1 - 2, PMULT: n}, "BSGS-LT")


def schoolbook_formula() -> CostFormula:
    n = sp.Symbol("n", positive=True)
    return CostFormula({"field_mult": n ** 2}, "schoolbook")


def karatsuba_formula() -> CostFormula:
    n = sp.Symbol("n", positive=True)
    return CostFormula({"field_mult": n ** sp.log(3, 2)}, "karatsuba")
