import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from crbench import stats  # noqa: E402


class TestStats(unittest.TestCase):
    def test_median_iqr(self):
        self.assertEqual(stats.median([3, 1, 2]), 2.0)
        self.assertEqual(stats.iqr([1, 2, 3, 4, 5]), 2.0)

    def test_outlier_robust(self):
        s = stats.summarize([10, 10.1, 9.9, 10.05, 1000])
        self.assertAlmostEqual(s.median, 10.05)
        self.assertLess(s.iqr, 1.0)

    def test_bootstrap_ci_contains_median_and_is_deterministic(self):
        xs = [1.0, 1.1, 0.9, 1.05, 0.95, 1.2, 0.8]
        lo, hi = stats.bootstrap_ci(xs, seed=1)
        self.assertLessEqual(lo, stats.median(xs))
        self.assertGreaterEqual(hi, stats.median(xs))
        self.assertEqual((lo, hi), stats.bootstrap_ci(xs, seed=1))

    def test_speedup(self):
        sp = stats.speedup([10, 10, 10, 11, 9], [5, 5, 5, 6, 4])
        self.assertAlmostEqual(sp.ratio, 2.0)
        self.assertLessEqual(sp.ci_low, 2.0)
        self.assertGreaterEqual(sp.ci_high, 2.0)
        sp2 = stats.speedup([10, 11, 9], [5, 6, 4], paired=True)
        self.assertAlmostEqual(sp2.ratio, 2.0)
        self.assertIn("x [", sp.fmt())

    def test_errors(self):
        with self.assertRaises(ValueError):
            stats.median([])
        with self.assertRaises(ValueError):
            stats.speedup([1, 2], [0, 1])
        with self.assertRaises(ValueError):
            stats.speedup([1, 2], [1], paired=True)

    def test_relative_spread(self):
        self.assertAlmostEqual(stats.relative_spread([1, 1, 1]), 0.0)


if __name__ == "__main__":
    unittest.main()
