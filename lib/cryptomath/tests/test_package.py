import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cryptomath  # noqa: E402


class TestPackage(unittest.TestCase):
    def test_lazy_imports(self):
        self.assertIn("algebra", cryptomath.SUBPACKAGES)
        av = cryptomath.available()
        for name in ("algebra", "lattice", "fhe", "costmodel"):
            self.assertTrue(av[name], name)
        self.assertTrue(hasattr(cryptomath.algebra, "cyclotomic_poly"))
        with self.assertRaises(AttributeError):
            cryptomath.does_not_exist  # noqa: B018

    def test_toy_markers(self):
        for sub in ("fhe", "lattice"):
            d = os.path.join(ROOT, "cryptomath", sub)
            for fn in os.listdir(d):
                if fn.endswith(".py") and fn not in ("params.py",):
                    with open(os.path.join(d, fn)) as fh:
                        first = fh.readline()
                    self.assertIn("TOY: not secure", first, fn)

    def test_no_forbidden_strings(self):
        # patterns are assembled from pieces so this file does not match itself
        pieces = [("order", "-?4"), ("order", " four"), ("symmetry", "-graded"), ("#5", "28"),
                  ("#6", "99"), ("19" + "2", r"\.168\."), ("/home/", "luck"), ("ac", "pk"),
                  ("soseri", "halsona")]
        pat = re.compile("|".join(a + b for a, b in pieces),
                       re.IGNORECASE)
        for sub in ("algebra", "lattice", "fhe", "costmodel"):
            d = os.path.join(ROOT, "cryptomath", sub)
            for fn in os.listdir(d):
                if fn.endswith(".py"):
                    with open(os.path.join(d, fn)) as fh:
                        self.assertIsNone(pat.search(fh.read()), fn)

    def test_doctests(self):
        import doctest
        import importlib

        import numpy as np
        for name in ("cryptomath.fhe.bgv", "cryptomath.fhe.bfv", "cryptomath.fhe.ckks",
                     "cryptomath.fhe.tfhe", "cryptomath.algebra.slots",
                     "cryptomath.algebra.finite_field"):
            res = doctest.testmod(importlib.import_module(name), extraglobs={"np": np})
            self.assertEqual(res.failed, 0, name)


if __name__ == "__main__":
    unittest.main()
