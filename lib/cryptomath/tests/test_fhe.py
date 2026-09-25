import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from cryptomath.algebra import PolyRing  # noqa: E402
from cryptomath.costmodel import CMULT, KS, PBS, ROT, Counter, Traced  # noqa: E402
from cryptomath.fhe import BFV, BGV, CKKS, TFHE, TFHEParams  # noqa: E402
from cryptomath.fhe import noise as nz  # noqa: E402
from cryptomath.fhe.bootstrap import (  # noqa: E402
    CKKSRotOps, bgv_digit_extraction_cost, bsgs_matvec, bsgs_rotation_count,
    chebyshev_interpolate, diag_matvec, fft_lintrans_cost, mod_reduction_double_angle,
    mod_reduction_error, mod_reduction_sine,
)
from cryptomath.fhe.polyeval import (  # noqa: E402
    bsgs_counts, bsgs_eval, bsgs_eval_chebyshev, cheb_divmod, eval_cheb_series,
    horner, paterson_stockmeyer, ps_nonscalar_count,
)
from cryptomath.fhe.tfhe import Q, encode, gadget_decompose, negacyclic_mul_int, poly_mul_xk  # noqa: E402


class TestBGV(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bgv = BGV(N=16, t=257, levels=2, seed=1)
        cls.Rt = PolyRing(m=32, q=257)

    def test_arith_chain(self):
        bgv, Rt = self.bgv, self.Rt
        rng = random.Random(1)
        a = [rng.randrange(257) for _ in range(16)]
        b = [rng.randrange(257) for _ in range(16)]
        ca, cb = bgv.encrypt(a), bgv.encrypt(b)
        self.assertEqual(bgv.decrypt(ca), a)
        self.assertEqual(bgv.decrypt(bgv.add(ca, cb)), list(Rt.add(a, b)))
        self.assertEqual(bgv.decrypt(bgv.mul_plain(ca, b)), list(Rt.mul(a, b)))
        with Counter() as c:
            ab = bgv.mul(ca, cb)
        self.assertEqual(c[CMULT], 1)
        self.assertEqual(c[KS], 1)
        ab_ms = bgv.mod_switch(ab)
        self.assertEqual(bgv.decrypt(ab_ms), list(Rt.mul(a, b)))
        sq = bgv.mul(ab_ms, ab_ms)
        self.assertEqual(bgv.decrypt(sq), list(Rt.mul(Rt.mul(a, b), Rt.mul(a, b))))
        self.assertGreater(bgv.noise_budget(ab_ms), 0)
        self.assertLess(bgv.noise_budget(ab), bgv.noise_budget(ca))

    def test_galois_and_slots(self):
        bgv, Rt = self.bgv, self.Rt
        rng = random.Random(2)
        a = [rng.randrange(257) for _ in range(16)]
        self.assertEqual(bgv.decrypt(bgv.apply_galois(bgv.encrypt(a), 5)), list(Rt.automorphism(a, 5)))
        v = [rng.randrange(257) for _ in range(16)]
        w = [rng.randrange(257) for _ in range(16)]
        ct = bgv.mul(bgv.encrypt(bgv.encode_slots(v)), bgv.encrypt(bgv.encode_slots(w)))
        self.assertEqual(bgv.encoder.decode_constants(bgv.decrypt(ct)), [x * y % 257 for x, y in zip(v, w)])

    def test_fresh_noise_model(self):
        pred = nz.budget_bits(nz.bgv_fresh(16, 257, 3.19), self.bgv.Q[-1])
        meas = self.bgv.noise_budget(self.bgv.encrypt([0] * 16))
        self.assertLess(abs(pred - meas), 4)


class TestBFV(unittest.TestCase):
    def test_mul_depth2(self):
        bfv = BFV(N=16, t=17, qbits=80, seed=2)
        Rt = PolyRing(m=32, q=17)
        rng = random.Random(3)
        a = [rng.randrange(17) for _ in range(16)]
        b = [rng.randrange(17) for _ in range(16)]
        ca, cb = bfv.encrypt(a), bfv.encrypt(b)
        ab = bfv.mul(ca, cb)
        self.assertEqual(bfv.decrypt(ab), list(Rt.mul(a, b)))
        self.assertEqual(bfv.decrypt(bfv.mul(ab, ab)), list(Rt.mul(Rt.mul(a, b), Rt.mul(a, b))))
        self.assertEqual(bfv.decrypt(bfv.add_plain(ca, b)), list(Rt.add(a, b)))
        f0, f1 = bfv.noise_budget(ca), bfv.noise_budget(ab)
        self.assertGreater(f0, f1)
        # model vs measurement for a fresh ciphertext (budget = log2(Q/(2 t |v|)))
        pred = math.log2(bfv.q / (2 * 17 * nz.tail_bound(nz.bfv_fresh(16, 3.19))))
        self.assertLess(abs(pred - f0), 4)


class TestCKKS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ck = CKKS(N=32, levels=3, seed=3)
        rng = np.random.default_rng(0)
        cls.z = rng.uniform(-1, 1, 16) + 1j * rng.uniform(-1, 1, 16)

    def test_encode_roundtrip(self):
        enc = self.ck.enc
        c = enc.encode(self.z, 2.0 ** 30)
        self.assertLess(np.max(np.abs(enc.decode(c, 2.0 ** 30) - self.z)), 1e-6)

    def test_mul_rescale_rotate(self):
        ck, z = self.ck, self.z
        cz = ck.encrypt(z)
        self.assertLess(ck.error(cz, z), 1e-4)
        sq = ck.rescale(ck.mul(cz, cz))
        self.assertLess(ck.error(sq, z * z), 1e-4)
        self.assertEqual(sq.level, ck.L - 1)
        q4 = ck.rescale(ck.mul(sq, sq))
        self.assertLess(ck.error(q4, z ** 4), 1e-3)
        self.assertLess(ck.error(ck.rotate(cz, 5), np.roll(z, -5)), 1e-4)
        self.assertLess(ck.error(ck.conjugate(cz), np.conj(z)), 1e-4)
        self.assertGreater(ck.precision_bits(q4, z ** 4), 10)

    def test_bsgs_linear_transform(self):
        ck, z = self.ck, self.z
        M = np.random.default_rng(1).uniform(-1, 1, (16, 16))
        with Counter() as c:
            out = bsgs_matvec(M, ck.encrypt(z), n1=4, ops=CKKSRotOps(ck))
        self.assertLess(ck.error(out, M @ z), 1e-3)
        self.assertEqual(c[ROT], bsgs_rotation_count(16, 4)["rotations"])


class TestTFHE(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.P = TFHEParams()
        cls.tf = TFHE(cls.P, seed=5)

    def test_primitives(self):
        rng = np.random.default_rng(0)
        x = rng.integers(0, Q, 64, dtype=np.int64)
        d = gadget_decompose(x, 8, 4)
        rec = sum(d[j].astype(object) * (1 << (32 - 8 * (j + 1))) for j in range(4))
        self.assertTrue(all((int(r) - int(v)) % Q in (0,) for r, v in zip(rec, x)))
        self.assertTrue(np.all(np.abs(d) <= 128))
        a = rng.integers(0, Q, 16, dtype=np.int64)
        mono = np.zeros(16, dtype=np.int64)
        mono[3] = 1
        self.assertTrue(np.array_equal(poly_mul_xk(a, 3), negacyclic_mul_int(mono, a)))
        self.assertTrue(np.array_equal(poly_mul_xk(poly_mul_xk(a, 20), -20), a))

    def test_pbs_lut(self):
        tf, p = self.tf, 8
        f = lambda m: (3 * m + 1) % p  # noqa: E731
        with Counter() as c:
            for m in range(p):
                self.assertEqual(tf.decrypt(tf.pbs(tf.encrypt(m, p), f, p), p), f(m))
        self.assertEqual(c[PBS], p)

    def test_pbs_noise_model(self):
        tf, P, p = self.tf, self.P, 4
        errs = []
        for i in range(16):
            m = i % p
            out = tf.pbs(tf.encrypt(m, p), lambda x: x, p)
            ph = tf.lwe_phase(out, tf.s)
            errs.append(((ph - encode(m, p) + Q // 2) % Q - Q // 2) / Q)
        meas = float(np.std(errs))
        pred = nz.tfhe_pbs(P.n, P.N, P.k, P.bg_bits, P.l, P.glwe_sigma ** 2,
                           P.ks_bits, P.ks_l, P.lwe_sigma ** 2).std
        self.assertTrue(pred / 3 < meas < pred * 3, (meas, pred))
        self.assertLess(nz.tfhe_failure_prob_log2(P.lwe_sigma ** 2, P.n, P.N, p), -40)


class TestPolyEval(unittest.TestCase):
    def test_equivalence_and_counts(self):
        from fractions import Fraction
        rng = random.Random(4)
        for d in (1, 3, 7, 16, 31, 60):
            c = [rng.randint(-9, 9) for _ in range(d + 1)]
            c[-1] = c[-1] or 1
            x = Fraction(2, 5)
            ref = horner(c, x)
            with Counter() as c1:
                y1 = paterson_stockmeyer(c, Traced(x))
            with Counter() as c2:
                y2 = bsgs_eval(c, Traced(x))
            self.assertEqual(y1.value, ref)
            self.assertEqual(y2.value, ref)
            self.assertEqual(c1[CMULT], ps_nonscalar_count(d))
            self.assertLessEqual(c2[CMULT], bsgs_counts(d)["nonscalar"])
            self.assertLessEqual(y2.depth, math.ceil(math.log2(d + 1)) + 1)
            with Counter() as c3:
                y3 = horner(c, Traced(x))
            self.assertEqual(c3[CMULT], d - 1 if d > 1 else 0)  # top step is scalar

    def test_chebyshev(self):
        rng = np.random.default_rng(2)
        c = list(rng.uniform(-1, 1, 40))
        q, r = cheb_divmod(c, 8)
        for x in (-0.9, 0.1, 0.77):
            T8 = math.cos(8 * math.acos(x))
            self.assertAlmostEqual(eval_cheb_series(q, x) * T8 + eval_cheb_series(r, x), eval_cheb_series(c, x), places=9)
            self.assertAlmostEqual(bsgs_eval_chebyshev(c, x), eval_cheb_series(c, x), places=9)
        coeffs = chebyshev_interpolate(np.exp, 12)
        self.assertLess(abs(eval_cheb_series(coeffs, 0.3) - math.exp(0.3)), 1e-10)


class TestBootstrapBlocks(unittest.TestCase):
    def test_mod_reduction(self):
        K, eps = 6, 2.0 ** -8
        e1 = mod_reduction_error(mod_reduction_sine(K, 64), K, eps)
        e2 = mod_reduction_error(mod_reduction_double_angle(K, 24, 3), K, eps)
        self.assertLess(e1, 1e-5)   # dominated by sin(2 pi x)/(2 pi) vs x
        self.assertLess(e2, 1e-5)
        with Counter() as c:
            y = mod_reduction_double_angle(K, 24, 3)(Traced(0.25))
        self.assertAlmostEqual(y.value, 1 / (2 * math.pi), places=6)
        self.assertGreater(c[CMULT], 3)

    def test_linear_transform_counts(self):
        M = np.arange(64, dtype=float).reshape(8, 8)
        z = np.arange(8, dtype=float)
        with Counter() as c1:
            r1 = diag_matvec(M, z)
        with Counter() as c2:
            r2 = bsgs_matvec(M, z, n1=4)
        self.assertTrue(np.allclose(r1, M @ z) and np.allclose(r2, M @ z))
        self.assertEqual(c1[ROT], 7)
        self.assertEqual(c2[ROT], 3 + 1)
        cost = fft_lintrans_cost(1024, 3)
        self.assertEqual(sum(s["layers"] for s in cost["stages"]), 10)

    def test_digit_extraction_cost(self):
        c = bgv_digit_extraction_cost(2, 8, 4)
        self.assertEqual(c["F_evals"], 7 + 6 + 5 + 4)
        self.assertEqual(c["depth"], 7)


if __name__ == "__main__":
    unittest.main()
