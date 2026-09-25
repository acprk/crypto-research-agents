"""Tests for cryptomath.symmetric (run: python3 -m unittest discover -s tests)."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np  # noqa: E402

from cryptomath.symmetric import (  # noqa: E402
    AES_SBOX, AES128, GF2n, PRESENT_SBOX, ToyFeistel, ToyGrain, ToySPN, LFSR, CNF,
    aes_decrypt, aes_encrypt, algebraic_degree, algebraic_immunity, anf_to_tt,
    bct, best_trail_bnb, best_trail_exhaustive, boolean_degree, boomerang_uniformity,
    correlation_immunity, cube_sum_degree_lower_bound, ddt, degree_upper_bounds,
    differential_branch_number, differential_uniformity, exact_output_degrees, hades_cost,
    inverse_map, is_apn, is_bent, is_gold_exponent, is_irreducible_gf2, is_kasami_exponent,
    lat, majority, mimc_cost, min_active_sboxes_exhaustive, mobius, nonlinearity,
    power_map, power_mult_cost, present_permutation, rasta_cost, resiliency,
    run_sat_solver, spn_active_sbox_cnf, spn_active_sbox_milp, square_distinguisher,
    trail_to_assignment, walsh, berlekamp_massey, DEFAULT_MODULI, aes128_boolean_cost,
    gold_is_apn, lowmc_cost,
)


class TestGF2n(unittest.TestCase):
    def test_default_moduli_irreducible(self):
        for n, m in DEFAULT_MODULI.items():
            self.assertTrue(is_irreducible_gf2(m), n)
        self.assertFalse(is_irreducible_gf2(0b10101))  # (x^2+x+1)^2

    def test_fips197_mul(self):
        F = GF2n(8)
        self.assertEqual(F.mul(0x57, 0x83), 0xC1)
        self.assertEqual(F.mul(0x57, 0x13), 0xFE)
        for a in range(1, 256):
            self.assertEqual(F.mul(a, F.inv(a)), 1)

    def test_cube_apn_odd_n(self):
        for n in (3, 5, 7, 9):
            self.assertTrue(is_apn(power_map(3, n)), n)

    def test_gold_kasami(self):
        self.assertEqual(is_gold_exponent(3, 5), 1)
        self.assertEqual(is_gold_exponent(5, 5), 2)
        self.assertTrue(gold_is_apn(2, 5) and is_apn(power_map(5, 5)))
        self.assertEqual(is_kasami_exponent(13, 7), 2)   # 2^4 - 2^2 + 1
        self.assertTrue(is_apn(power_map(13, 7)))
        self.assertIsNone(is_gold_exponent(7, 5))

    def test_inverse_map(self):
        inv8 = inverse_map(8)
        self.assertEqual(differential_uniformity(inv8), 4)
        self.assertEqual(nonlinearity(inv8), 112)
        self.assertTrue(is_apn(inverse_map(5)))       # odd n: inverse is APN


class TestBoolean(unittest.TestCase):
    def test_mobius_involution(self):
        rng = np.random.default_rng(1)
        tt = rng.integers(0, 2, 64)
        self.assertTrue(np.array_equal(anf_to_tt(mobius(tt)), tt))

    def test_bent(self):
        tt = [((x & 1) & (x >> 1 & 1)) ^ ((x >> 2 & 1) & (x >> 3 & 1)) for x in range(16)]
        self.assertTrue(is_bent(tt))
        self.assertTrue(np.all(np.abs(walsh(tt)) == 4))
        self.assertEqual(boolean_degree(tt), 2)
        self.assertFalse(is_bent([0] * 16))

    def test_ci_resiliency(self):
        # x0 ^ x1 ^ x2 is 2-resilient on 3 variables
        tt = [bin(x).count("1") & 1 for x in range(8)]
        self.assertEqual(correlation_immunity(tt), 2)
        self.assertEqual(resiliency(tt), 2)
        self.assertEqual(resiliency([1] + [0] * 7), -1)

    def test_algebraic_immunity(self):
        self.assertEqual(algebraic_immunity(majority(5)), 3)
        self.assertEqual(algebraic_immunity(majority(4)), 2)
        self.assertEqual(algebraic_immunity([x & 1 for x in range(16)]), 1)


class TestSbox(unittest.TestCase):
    def test_present(self):
        D = ddt(PRESENT_SBOX)
        self.assertEqual(int(D[1:].max()), 4)
        self.assertEqual(int(D.sum()), 256)
        self.assertEqual(nonlinearity(PRESENT_SBOX), 4)
        self.assertEqual(algebraic_degree(PRESENT_SBOX), 3)
        self.assertEqual(differential_branch_number(PRESENT_SBOX), 3)

    def test_aes_sbox(self):
        self.assertEqual(AES_SBOX[0x00], 0x63)
        self.assertEqual(AES_SBOX[0x53], 0xED)
        self.assertEqual(differential_uniformity(AES_SBOX), 4)
        self.assertEqual(nonlinearity(AES_SBOX), 112)
        self.assertEqual(algebraic_degree(AES_SBOX), 7)
        self.assertEqual(boomerang_uniformity(AES_SBOX), 6)

    def test_lat_parseval(self):
        L = lat(PRESENT_SBOX)
        W = 2 * L
        for b in range(16):
            self.assertEqual(int((W[:, b] ** 2).sum()), 256)

    def test_bct_ge_ddt(self):
        B, D = bct(PRESENT_SBOX), ddt(PRESENT_SBOX)
        self.assertTrue(np.all(B >= D))
        self.assertTrue(np.all(B[0] == 16) and np.all(B[:, 0] == 16))


class TestCiphers(unittest.TestCase):
    def test_aes_fips197(self):
        k = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
        p = bytes.fromhex("00112233445566778899aabbccddeeff")
        c = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")
        self.assertEqual(aes_encrypt(p, k), c)
        self.assertEqual(aes_decrypt(c, k), p)
        k2 = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
        self.assertEqual(aes_encrypt(bytes.fromhex("3243f6a8885a308d313198a2e0370734"), k2).hex(),
                         "3925841d02dc09fbdc118597196a0b32")

    def test_aes_round_reduced(self):
        k = bytes(range(16))
        for r in (1, 2, 4, 7):
            for fmc in (False, True):
                A = AES128(k, r, fmc)
                p = bytes(random.Random(r).getrandbits(8) for _ in range(16))
                self.assertEqual(A.decrypt(A.encrypt(p)), p)

    def test_aes_3round_integral(self):
        # classic 3-round integral: 256 plaintexts, one active byte -> all bytes balanced
        k = bytes(range(16))
        acc = bytearray(16)
        for v in range(256):
            c = aes_encrypt(bytes([v]) + bytes(15), k, rounds=3, final_mixcolumns=True)
            acc = bytearray(a ^ b for a, b in zip(acc, c))
        self.assertEqual(bytes(acc), bytes(16))

    def test_spn_feistel_roundtrip(self):
        for B in (8, 16, 32, 64):
            s = ToySPN(B, 5, seed=B)
            for x in (0, 1, (1 << B) - 1, 0x1234 % (1 << B)):
                self.assertEqual(s.decrypt(s.encrypt(x)), x)
        f = ToyFeistel(8, 6, seed=3)
        self.assertTrue(all(f.decrypt(f.encrypt(x)) == x for x in range(0, 65536, 97)))
        self.assertEqual(sorted(present_permutation(16)), list(range(16)))

    def test_stream(self):
        self.assertEqual(LFSR(16, [0, 2, 3, 5], 1).period(), 65535)
        L, C = berlekamp_massey(LFSR(16, [0, 2, 3, 5], 0xACE1).keystream(64))
        self.assertEqual(L, 16)
        ks = ToyGrain(0x1234, 0xABC).keystream(256)
        self.assertGreater(berlekamp_massey(ks)[0], 100)
        self.assertNotEqual(ks, ToyGrain(0x1235, 0xABC).keystream(256))


class TestTrails(unittest.TestCase):
    perm = present_permutation(16)

    def test_bnb_matches_exhaustive(self):
        for kind in ("diff", "linear"):
            ex = best_trail_exhaustive(PRESENT_SBOX, self.perm, 4, kind)
            bb, tr = best_trail_bnb(PRESENT_SBOX, self.perm, 4, kind)
            self.assertEqual(ex, bb, kind)
            self.assertEqual(len(tr.rounds), 4)
        self.assertEqual(best_trail_exhaustive(PRESENT_SBOX, self.perm, 1), [2.0])

    def test_trail_is_valid(self):
        _, tr = best_trail_bnb(PRESENT_SBOX, self.perm, 3)
        D = ddt(PRESENT_SBOX)
        w = 0.0
        for r, (a, b) in enumerate(tr.rounds):
            for j in range(4):
                ai, bi = (a >> 4 * j) & 15, (b >> 4 * j) & 15
                self.assertGreater(D[ai, bi], 0)
                if ai:
                    w += -np.log2(D[ai, bi] / 16)
            if r + 1 < len(tr.rounds):
                self.assertEqual(ToySPN(16, 1).p_layer(b), tr.rounds[r + 1][0])
        self.assertAlmostEqual(w, tr.weight)

    def test_milp_min_active(self):
        ex = min_active_sboxes_exhaustive(PRESENT_SBOX, self.perm, 3)
        for R in (1, 2, 3):
            M = spn_active_sbox_milp(PRESENT_SBOX, self.perm, R)
            lp = M.to_lp()
            self.assertIn("Minimize", lp)
            self.assertIn("Binary", lp)
            res = M.solve_scipy()
            if res is None:
                self.skipTest("scipy not installed")
            self.assertEqual(int(res[0]), ex[R - 1])

    def test_cnf_accepts_real_trail(self):
        bb, tr = best_trail_bnb(PRESENT_SBOX, self.perm, 3)
        nact = sum(((a >> 4 * j) & 15) != 0 for a, _ in tr.rounds for j in range(4))
        cnf, mv = spn_active_sbox_cnf(PRESENT_SBOX, self.perm, 3, nact)
        asg = trail_to_assignment(mv, tr, 4)
        base = CNF()
        base.clauses = [c for c in cnf.clauses if all(abs(l) in asg for l in c)]
        self.assertTrue(base.evaluate(asg))
        # corrupt the last-round output nibble into an impossible transition
        D = ddt(PRESENT_SBOX)
        aL, bL = tr.rounds[-1]
        j = next(j for j in range(4) if (aL >> 4 * j) & 15)
        aj = (aL >> 4 * j) & 15
        bad_b = next(b for b in range(16) if D[aj, b] == 0)
        bL2 = (bL & ~(15 << 4 * j)) | (bad_b << 4 * j)
        bad = type(tr)(tr.weight, tr.rounds[:-1] + [(aL, bL2)])
        self.assertFalse(base.evaluate(trail_to_assignment(mv, bad, 4)))

    def test_cnf_with_solver_if_available(self):
        ex = min_active_sboxes_exhaustive(PRESENT_SBOX, self.perm, 3)[2]
        cnf, _ = spn_active_sbox_cnf(PRESENT_SBOX, self.perm, 3, ex - 1)
        r = run_sat_solver(cnf)
        if r is None:
            self.skipTest("no SAT solver on PATH")
        self.assertFalse(r[0])
        cnf, _ = spn_active_sbox_cnf(PRESENT_SBOX, self.perm, 3, ex)
        sat, model = run_sat_solver(cnf)
        self.assertTrue(sat and cnf.evaluate(model))

    def test_xor_and_cardinality_encodings(self):
        for native in (False, True):
            for k in (1, 3, 6):
                cnf = CNF()
                vs = cnf.new_vars(k)
                cnf.add_xor(vs, 1, native=native, chunk=3)
                aux = cnf.nvars
                for m in range(1 << k):
                    asg = {v: (m >> i) & 1 for i, v in enumerate(vs)}
                    # search aux values (Tseitin) exhaustively
                    extra = list(range(k + 1, aux + 1))
                    ok = any(cnf.evaluate({**asg, **{e: (z >> t) & 1 for t, e in enumerate(extra)}})
                             for z in range(1 << len(extra)))
                    self.assertEqual(ok, bin(m).count("1") % 2 == 1)
        cnf = CNF()
        xs = cnf.new_vars(5)
        cnf.at_most_k(xs, 2)
        extra = list(range(6, cnf.nvars + 1))
        for m in range(32):
            asg = {v: (m >> i) & 1 for i, v in enumerate(xs)}
            ok = any(cnf.evaluate({**asg, **{e: (z >> t) & 1 for t, e in enumerate(extra)}})
                     for z in range(1 << len(extra)))
            self.assertEqual(ok, bin(m).count("1") <= 2)
        c2 = CNF()
        c2.add_xor(c2.new_vars(3), 0, native=True)
        self.assertIn("x-1 2 3 0", c2.to_dimacs())


class TestIntegralDegree(unittest.TestCase):
    def test_square(self):
        r3 = square_distinguisher(16, 3, active_nibbles=(0,))
        self.assertEqual(r3["fraction"], 1.0)
        r6 = square_distinguisher(16, 6, active_nibbles=(0,))
        self.assertLess(r6["fraction"], 0.5)

    def test_degree_bounds(self):
        ub = degree_upper_bounds(PRESENT_SBOX, 16, 3)
        for R in (1, 2, 3):
            d = max(exact_output_degrees(ToySPN(16, R, seed=7)))
            self.assertLessEqual(d, ub[R - 1])
            lb = cube_sum_degree_lower_bound(lambda x: ToySPN(16, R, seed=7).encrypt(x), 16, d, samples=10)
            self.assertLessEqual(lb, d)
        self.assertEqual(ub[0], 3)


class TestAFCost(unittest.TestCase):
    def test_formulas(self):
        self.assertEqual(power_mult_cost(3), (2, 2))
        self.assertEqual(power_mult_cost(5), (3, 3))
        self.assertEqual(power_mult_cost(7), (4, 3))
        m = mimc_cost(129)
        self.assertEqual(m.nonlinear_ops, 82)          # ceil(129 / log2 3)
        h = hades_cost(3, 8, 57, 5)
        self.assertEqual(h.nonlinear_ops, 3 * 8 + 57)
        self.assertEqual(h.mults, 81 * 3)
        self.assertEqual(rasta_cost(351, 6).mult_depth, 6)
        self.assertEqual(aes128_boolean_cost().mults, 6400)
        self.assertEqual(lowmc_cost(10, 20, 128).mults, 600)


if __name__ == "__main__":
    unittest.main()
