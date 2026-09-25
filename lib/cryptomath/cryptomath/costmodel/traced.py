"""``Traced`` values: run ordinary arithmetic code and get op counts + depth.

A :class:`Traced` wraps an (optional) concrete value.  Arithmetic between two
Traced values is a *nonscalar* multiplication (``ctxt_mult``) and increases
multiplicative depth; arithmetic with plain numbers is a scalar operation.
Every operation is reported to the active :class:`~cryptomath.costmodel.Counter`.

This lets you count nonscalar multiplications and depth of e.g. a polynomial
evaluation algorithm *without* any FHE library:

    from cryptomath.costmodel import Counter, Traced
    from cryptomath.fhe.polyeval import paterson_stockmeyer
    with Counter() as c:
        y = paterson_stockmeyer(coeffs, Traced(0.3))
    c['ctxt_mult'], y.depth, y.value

If ``scalar_uses_level=True`` (CKKS-style, where multiplying by a
non-integer constant consumes a rescale), scalar multiplications by
non-integers also add one level.
"""
from __future__ import annotations

from typing import Any, Optional

from .counter import CADD, CMULT, SMULT, count, note_depth

__all__ = ["Traced"]


class Traced:
    __slots__ = ("value", "depth", "scalar_uses_level")

    def __init__(self, value: Any = None, depth: int = 0, scalar_uses_level: bool = False):
        self.value = value
        self.depth = depth
        self.scalar_uses_level = scalar_uses_level

    def _new(self, value, depth):
        note_depth(depth)
        return Traced(value, depth, self.scalar_uses_level)

    @staticmethod
    def _v(x):
        return x.value if isinstance(x, Traced) else x

    def _combine(self, other, fn):
        a, b = self.value, self._v(other)
        if a is None or b is None:
            return None
        return fn(a, b)

    # additive ops: free in depth
    def __add__(self, o):
        count(CADD)
        d = max(self.depth, o.depth) if isinstance(o, Traced) else self.depth
        return self._new(self._combine(o, lambda a, b: a + b), d)

    __radd__ = __add__

    def __sub__(self, o):
        count(CADD)
        d = max(self.depth, o.depth) if isinstance(o, Traced) else self.depth
        return self._new(self._combine(o, lambda a, b: a - b), d)

    def __rsub__(self, o):
        count(CADD)
        return self._new(self._combine(o, lambda a, b: b - a), self.depth)

    def __neg__(self):
        return self._new(None if self.value is None else -self.value, self.depth)

    def __mul__(self, o):
        if isinstance(o, Traced):
            count(CMULT)
            return self._new(self._combine(o, lambda a, b: a * b), max(self.depth, o.depth) + 1)
        if o == 0:
            return self._new(0 * self.value if self.value is not None else None, 0)
        count(SMULT)
        extra = 1 if (self.scalar_uses_level and not float(o).is_integer()) else 0
        return self._new(self._combine(o, lambda a, b: a * b), self.depth + extra)

    __rmul__ = __mul__

    def __pow__(self, e: int):
        """Square-and-multiply (counts its own multiplications)."""
        if e < 1:
            raise ValueError("positive exponents only")
        result, base = None, self
        while e:
            if e & 1:
                result = base if result is None else result * base
            e >>= 1
            if e:
                base = base * base
        return result

    def __repr__(self):
        return f"Traced({self.value!r}, depth={self.depth})"
