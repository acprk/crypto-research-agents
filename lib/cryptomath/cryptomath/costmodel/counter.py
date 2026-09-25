"""Abstract operation counting.

Use it to *screen ideas before implementing them*: write the algorithm once
in plain Python against abstract operations, run it under a ``Counter`` and
compare the counts (or a weighted cost) with a baseline.

    from cryptomath.costmodel import Counter, count, counted, CMULT, ROT

    @counted(ROT)
    def rotate(v, k): return v[k:] + v[:k]

    with Counter() as c:
        rotate([1, 2, 3], 1)
        count(CMULT, 3)
    c.counts  # {'rotation': 1, 'ctxt_mult': 3}

Counters nest: every active counter on the stack sees every event, so an
outer counter can total a whole pipeline while inner ones measure phases.
When no counter is active, :func:`count` is a cheap no-op, so library code
(the toy FHE schemes) can call it unconditionally.

Standard op names are module constants (strings) so reports line up.
"""
from __future__ import annotations

import functools
import threading
from collections import Counter as _PyCounter
from typing import Callable, Dict, Iterable, List, Optional

__all__ = [
    "CMULT", "PMULT", "SMULT", "CADD", "ROT", "KS", "RELIN", "RESCALE", "MODSWITCH",
    "NTT", "INTT", "AND", "XOR", "NOT", "FMUL", "FADD", "FINV", "PBS", "EXTPROD", "CMUX",
    "Counter", "count", "counted", "note_depth", "active_counters", "DEFAULT_WEIGHTS",
]

CMULT = "ctxt_mult"        # ciphertext x ciphertext (nonscalar) multiplication
PMULT = "ptxt_mult"        # ciphertext x plaintext polynomial
SMULT = "scalar_mult"      # ciphertext x constant
CADD = "ctxt_add"
ROT = "rotation"           # slot rotation / Galois automorphism (incl. its key switch)
KS = "keyswitch"
RELIN = "relin"
RESCALE = "rescale"
MODSWITCH = "modswitch"
NTT = "ntt"
INTT = "intt"
AND = "and"
XOR = "xor"
NOT = "not"
FMUL = "field_mult"
FADD = "field_add"
FINV = "field_inv"
PBS = "pbs"
EXTPROD = "external_product"
CMUX = "cmux"

# Rough relative weights for a leveled RLWE scheme at a fixed level
# (ctxt-mult incl. relinearisation ~ key switch; additions ~ free).  Replace
# with measured numbers from lib/bench before drawing conclusions.
DEFAULT_WEIGHTS: Dict[str, float] = {
    CMULT: 1.0, RELIN: 0.0, KS: 1.0, ROT: 1.0, PMULT: 0.05, SMULT: 0.01,
    CADD: 0.01, RESCALE: 0.05, MODSWITCH: 0.05, NTT: 0.02, INTT: 0.02,
    AND: 1.0, XOR: 0.0, NOT: 0.0, FMUL: 1.0, FADD: 0.0, FINV: 10.0,
    PBS: 1.0, EXTPROD: 1.0, CMUX: 1.0,
}

_local = threading.local()


def active_counters() -> List["Counter"]:
    if not hasattr(_local, "stack"):
        _local.stack = []
    return _local.stack


class Counter:
    """Context manager accumulating op counts (and optional max depth)."""

    def __init__(self, name: str = ""):
        self.name = name
        self.counts: _PyCounter = _PyCounter()
        self.max_depth = 0

    def __enter__(self) -> "Counter":
        active_counters().append(self)
        return self

    def __exit__(self, *exc):
        st = active_counters()
        if st and st[-1] is self:
            st.pop()
        else:  # pragma: no cover - defensive
            st.remove(self)
        return False

    def add(self, op: str, n: int = 1) -> None:
        self.counts[op] += n

    def note_depth(self, d: int) -> None:
        if d > self.max_depth:
            self.max_depth = d

    def __getitem__(self, op: str) -> int:
        return self.counts.get(op, 0)

    def total(self, weights: Optional[Dict[str, float]] = None) -> float:
        w = DEFAULT_WEIGHTS if weights is None else weights
        return sum(w.get(op, 0.0) * n for op, n in self.counts.items())

    def as_dict(self) -> Dict[str, int]:
        d = dict(self.counts)
        if self.max_depth:
            d["depth"] = self.max_depth
        return d

    def __repr__(self):
        return f"Counter({self.name!r}, {self.as_dict()})"


def count(op: str, n: int = 1) -> None:
    """Record ``n`` occurrences of ``op`` in every active counter."""
    for c in active_counters():
        c.add(op, n)


def note_depth(d: int) -> None:
    for c in active_counters():
        c.note_depth(d)


def counted(op: str, n: int = 1) -> Callable:
    """Decorator: each call of the function records ``n`` x ``op``."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            count(op, n)
            return fn(*a, **kw)
        return wrapper
    return deco
