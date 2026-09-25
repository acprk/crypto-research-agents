# TOY: not secure
"""Correctness tests.  Run:  /usr/bin/python3 -m pytest -q code/   (or python3 code/test_sbox_fhe.py)"""
from __future__ import annotations

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sbox_fhe import (PARAMS, P_IN, PRESENT_SBOX, Q, TFHE, bit_luts, d_norm2, d_poly, evaluate,  # noqa: E402
                      mv_pbs, negacyclic_mul_int, per_bit_pbs, torus_mod, v0_poly)


def mul_torus_int(v, d):
    return negacyclic_mul_int(d, v)


class TestFactorisation(unittest.TestCase):
    def test_identity_random_luts(self):
        """T_f == v0 * d_f exactly (mod X^N+1, mod 2^32) for random LUTs Z_p -> Z_p."""
        tf = TFHE(PARAMS["T1"], seed=1)
        rng = np.random.default_rng(0)
        for p in (2, 4, 8, 16):
            for _ in range(20):
                table = rng.integers(0, p, size=p)
                f = lambda m, t=table: int(t[m % p])  # noqa: E731
                T = tf.test_polynomial(f, p)
                got = mul_torus_int(v0_poly(tf.P.N, p), d_poly(f, tf.P.N, p))
                self.assertTrue(np.array_equal(torus_mod(T), got))

    def test_norm_bound_boolean(self):
        """||d_f||^2 <= 18 for every Boolean f on Z_16 (Lemma L2); PRESENT bits give 10,10,8,8."""
        N = 512
        worst = max(d_norm2(lambda m, b=b: (b >> m) & 1, N, 16) for b in range(1 << 16))
        self.assertEqual(worst, 18)
        self.assertEqual([d_norm2(f, N, 16) for f in bit_luts()], [10, 10, 8, 8])


class TestEvaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tf = TFHE(PARAMS["T1"], seed=11)

    def _check(self, method):
        for m in range(16):
            outs = evaluate(method, self.tf, m)
            got = sum(self.tf.decrypt(o, P_IN) << i for i, o in enumerate(outs))
            self.assertEqual(got, PRESENT_SBOX[m], f"{method} m={m}")

    def test_perbit(self):
        self._check("perbit")

    def test_mvpbs(self):
        self._check("mvpbs")

    def test_vpack(self):
        self._check("vpack")

    def test_mvpbs_general_lut(self):
        """MV-PBS with non-Boolean LUTs (full nibble output, p = 16)."""
        fs = [lambda m: PRESENT_SBOX[m], lambda m: (3 * m + 1) % 16]
        for m in (0, 5, 15):
            outs = mv_pbs(self.tf, self.tf.encrypt(m, P_IN), fs)
            self.assertEqual([self.tf.decrypt(o, P_IN) for o in outs], [f(m) for f in fs])

    def test_same_as_pbs_noise_free(self):
        """Without key switching MV-PBS and PBS agree on the decrypted value."""
        fs = bit_luts()
        ct = self.tf.encrypt(9, P_IN)
        a = [self.tf.decrypt(o, P_IN, key=self.tf.s_ext) for o in mv_pbs(self.tf, ct, fs, keyswitch=False)]
        b = [self.tf.decrypt(o, P_IN, key=self.tf.s_ext) for o in per_bit_pbs(self.tf, ct, fs, keyswitch=False)]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
