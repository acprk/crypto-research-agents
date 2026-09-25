import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from cryptomath.algebra import PolyRing  # noqa: E402
from cryptomath.lattice import (  # noqa: E402
    GAUSSIAN, TERNARY, Distribution, bkz_simulate, beta_for_delta, core_svp_cost,
    delta_bkz, discrete_gaussian_vec, dual_simple, estimate_lwe, gram_schmidt,
    is_lll_reduced, lattice_estimator_available, lll_reduce, lwe_sample, max_logq,
    min_ring_dim, mlwe_sample, ntru_keygen, primal_embedding_basis, primal_usvp,
    qary_lwe_profile, rlwe_sample, root_hermite_from_profile, sparse_ternary,
    gsa_log_profile,
)


class TestDistributions(unittest.TestCase):
    def test_gaussian_variance(self):
        rng = random.Random(1)
        xs = discrete_gaussian_vec(20000, 3.2, rng)
        self.assertAlmostEqual(float(np.var(xs)), 3.2 ** 2, delta=0.5)
        self.assertAlmostEqual(float(np.mean(xs)), 0.0, delta=0.1)

    def test_other(self):
        rng = random.Random(2)
        v = sparse_ternary(8).sample(64, rng)
        self.assertEqual(sum(1 for x in v if x), 8)
        self.assertAlmostEqual(TERNARY.variance(), 2 / 3)
        c = Distribution("cbd", 2).sample(10000, rng)
        self.assertAlmostEqual(float(np.var(c)), 1.0, delta=0.1)


class TestSamplers(unittest.TestCase):
    def test_instances(self):
        rng = random.Random(3)
        self.assertTrue(lwe_sample(16, 32, 3329, rng=rng).check())
        R = PolyRing(m=64, q=7681)
        self.assertTrue(rlwe_sample(R, rng=rng).check())
        self.assertTrue(mlwe_sample(R, 2, rng=rng).check())
        self.assertTrue(ntru_keygen(PolyRing(m=64, q=2 ** 11), rng=rng).check())
        self.assertTrue(ntru_keygen(PolyRing(m=64, q=12289), rng=rng).check())


class TestEstimates(unittest.TestCase):
    def test_delta(self):
        self.assertAlmostEqual(delta_bkz(2), 1.0219)
        ds = [delta_bkz(b) for b in (10, 50, 100, 200, 400)]
        self.assertTrue(all(a > b for a, b in zip(ds, ds[1:])))
        self.assertAlmostEqual(delta_bkz(100), 1.00927, places=4)
        self.assertLessEqual(delta_bkz(beta_for_delta(1.005)), 1.005)

    def test_monotone_security(self):
        a = primal_usvp(512, 2 ** 20, 3.2, math.sqrt(2 / 3))
        b = primal_usvp(512, 2 ** 30, 3.2, math.sqrt(2 / 3))
        c = primal_usvp(1024, 2 ** 30, 3.2, math.sqrt(2 / 3))
        self.assertGreater(a["beta"], b["beta"])
        self.assertGreater(c["beta"], b["beta"])
        self.assertAlmostEqual(a["log2_cost"], core_svp_cost(a["beta"]))

    def test_he_standard_sanity(self):
        # the built-in core-SVP model should put the HE-standard 128-bit rows in a
        # plausible range (core-SVP is known to be below the estimator's rop)
        r = estimate_lwe(1024, 2 ** max_logq(1024), 3.19, math.sqrt(2 / 3))
        self.assertTrue(80 < r["min_classical_bits"] < 160)
        self.assertEqual(min_ring_dim(100), 4096)
        self.assertIsNone(min_ring_dim(5000))
        d = dual_simple(256, 2 ** 12, 3.2)
        self.assertTrue(d["log2_cost"] > 0)

    def test_estimator_wrapper_guarded(self):
        self.assertIn(lattice_estimator_available(), (True, False))

    def test_bkz_sim(self):
        p = qary_lwe_profile(80, 80, 2 ** 16)
        s = bkz_simulate(p, 60, tours=12)
        self.assertAlmostEqual(sum(s), sum(p), places=6)
        self.assertAlmostEqual(root_hermite_from_profile(s), delta_bkz(60), delta=0.002)
        g = gsa_log_profile(100, 100 * math.log(7), 80)
        self.assertAlmostEqual(root_hermite_from_profile(g), delta_bkz(80), places=9)


class TestLLL(unittest.TestCase):
    def test_lll_properties(self):
        rng = random.Random(5)
        B = [[rng.randrange(-50, 50) for _ in range(8)] for _ in range(8)]
        L = lll_reduce(B)
        self.assertTrue(is_lll_reduced(L))
        _, n1 = gram_schmidt(B)
        _, n2 = gram_schmidt(L)
        self.assertEqual(math.prod(n1), math.prod(n2))  # same volume

    def test_toy_primal_attack(self):
        inst = lwe_sample(6, 12, 97, secret=TERNARY, error=GAUSSIAN(1.0), rng=random.Random(11))
        L = lll_reduce(primal_embedding_basis(inst.A.tolist(), inst.b.tolist(), 97))
        target = [int(x) for x in inst.e] + [-int(x) for x in inst.s] + [1]
        self.assertTrue(any(v == target or v == [-x for x in target] for v in L))


if __name__ == "__main__":
    unittest.main()
