import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sympy as sp  # noqa: E402

from cryptomath.costmodel import (  # noqa: E402
    CMULT, NTT, ROT, SMULT, CostFormula, Counter, Traced, bsgs_lintrans_formula,
    compare, count, counted, karatsuba_formula, ps_formula, schoolbook_formula,
)


@counted(NTT)
def fake_ntt(v):
    return v


def schoolbook(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            count("field_mult")
            out[i + j] += x * y
    return out


def karatsuba(a, b):
    n = len(a)
    if n == 1:
        count("field_mult")
        return [a[0] * b[0]]
    h = n // 2
    a0, a1, b0, b1 = a[:h], a[h:], b[:h], b[h:]
    z0 = karatsuba(a0, b0)
    z2 = karatsuba(a1, b1)
    z1 = karatsuba([x + y for x, y in zip(a0, a1)], [x + y for x, y in zip(b0, b1)])
    z1 = [m - p - q for m, p, q in zip(z1, z0, z2)]
    out = [0] * (2 * n - 1)
    for i, v in enumerate(z0):
        out[i] += v
    for i, v in enumerate(z1):
        out[i + h] += v
    for i, v in enumerate(z2):
        out[i + 2 * h] += v
    return out


class TestCounter(unittest.TestCase):
    def test_nesting_and_decorator(self):
        with Counter("outer") as outer:
            fake_ntt([1])
            with Counter("inner") as inner:
                fake_ntt([1])
                count(ROT, 3)
        self.assertEqual(outer[NTT], 2)
        self.assertEqual(inner[NTT], 1)
        self.assertEqual(outer[ROT], 3)
        count(ROT)  # no active counter: no-op
        self.assertEqual(outer[ROT], 3)

    def test_traced(self):
        with Counter() as c:
            x = Traced(3)
            y = x * x * x + x * 2 + 1
        self.assertEqual(y.value, 34)
        self.assertEqual(c[CMULT], 2)
        self.assertEqual(c[SMULT], 1)
        self.assertEqual(y.depth, 2)
        self.assertEqual(c.max_depth, 2)
        with Counter() as c2:
            z = Traced(2) ** 13
        self.assertEqual(z.value, 2 ** 13)
        self.assertEqual(z.depth, 4)
        ck = Traced(1.0, scalar_uses_level=True) * 0.5
        self.assertEqual(ck.depth, 1)

    def test_compare(self):
        a = list(range(1, 9))
        b = list(range(2, 10))
        rep = compare(schoolbook, karatsuba, a, b, names=("school", "kara"),
                      weights={"field_mult": 1.0})
        self.assertTrue(rep["equal_outputs"])
        self.assertEqual(rep["counts"]["school"]["field_mult"], 64)
        self.assertEqual(rep["counts"]["kara"]["field_mult"], 27)
        self.assertIn("| school |", rep["report"])


class TestFormulas(unittest.TestCase):
    def test_eval_and_crossover(self):
        ps = ps_formula()
        self.assertAlmostEqual(ps.evaluate(d=32)[CMULT], 8 + 5)
        lt = bsgs_lintrans_formula()
        self.assertEqual(lt.evaluate(n=64, n1=8)[ROT], 14)
        s, k = schoolbook_formula(), karatsuba_formula()
        self.assertEqual(k.crossover(s, "n", weights={"field_mult": 1}), 2)
        both = s + k
        self.assertIn("field_mult", both.terms)
        f = CostFormula({CMULT: sp.Symbol("n", positive=True) ** 2 + 5 * sp.Symbol("n", positive=True)})
        self.assertEqual(sp.simplify(f.leading("n", {CMULT: 1}) - sp.Symbol("n", positive=True) ** 2), 0)


if __name__ == "__main__":
    unittest.main()
