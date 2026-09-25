"""Tests for cryptomath.protocols."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptomath.ec import ECGroup, ModPGroup  # noqa: E402
from cryptomath.protocols import (  # noqa: E402
    DHOPRFServer, Pedersen, SchnorrProver, Transcript, additive_reconstruct, additive_share,
    adder_cost, beaver_multiply, beaver_triple, circuit_psi_cost, compare_psi, dh_psi,
    dh_psi_cost, equality_cost, fuzzy_intersection, hamming, hamming_ball_size, hash_commit,
    hash_verify, iknp_cost, kkrt_cost, kos_cost, l2, oprf_eval, parse_bristol,
    random_close_pair, replicated_mul_to_additive, replicated_reconstruct, replicated_share,
    run_simplest_ot, schnorr_extract, schnorr_nizk_prove, schnorr_nizk_verify,
    schnorr_simulate, schnorr_verify, shamir_add, shamir_reconstruct, shamir_share,
    threshold_match, vole_psi_cost,
)

P61 = 2 ** 61 - 1


class TestSharing(unittest.TestCase):
    def test_shamir(self):
        rng = random.Random(1)
        sh = shamir_share(424242, 3, 5, P61, rng)
        for subset in ([0, 1, 2], [1, 3, 4], [0, 2, 4], [0, 1, 2, 3, 4]):
            self.assertEqual(shamir_reconstruct([sh[i] for i in subset], P61), 424242)
        self.assertNotEqual(shamir_reconstruct(sh[:2], P61), 424242)
        s2 = shamir_share(1000, 3, 5, P61, rng)
        self.assertEqual(shamir_reconstruct(shamir_add(sh, s2, P61)[2:], P61), 425242)

    def test_additive_replicated(self):
        m = 2 ** 32
        self.assertEqual(additive_reconstruct(additive_share(77, 4, m), m), 77)
        rx, ry = replicated_share(123, m), replicated_share(456, m)
        for pair in ((0, 1), (1, 2), (0, 2)):
            self.assertEqual(replicated_reconstruct(rx, m, pair), 123)
        self.assertEqual(sum(replicated_mul_to_additive(rx, ry, m)) % m, 123 * 456 % m)

    def test_beaver(self):
        p = 101
        rng = random.Random(3)
        for x, y in ((3, 7), (0, 55), (100, 100)):
            xs, ys = additive_share(x, 3, p, rng), additive_share(y, 3, p, rng)
            z, tr = beaver_multiply(xs, ys, beaver_triple(3, p, rng), p)
            self.assertEqual(sum(z) % p, x * y % p)


class TestOTOPRF(unittest.TestCase):
    def test_ot_modp(self):
        m0, m1 = b"left message....", b"right message..."
        self.assertEqual(run_simplest_ot(m0, m1, 0), m0)
        self.assertEqual(run_simplest_ot(m0, m1, 1), m1)

    def test_ot_ec(self):
        G = ECGroup.small(10007)
        self.assertEqual(run_simplest_ot(b"aa", b"bb", 1, G), b"bb")

    def test_oprf(self):
        S = DHOPRFServer(ModPGroup(), key=123456789)
        self.assertEqual(oprf_eval(S, b"alice"), S.evaluate(b"alice"))
        self.assertNotEqual(oprf_eval(S, b"alice"), S.evaluate(b"bob"))
        X = {b"a", b"b", b"c", b"d"}
        Y = {b"c", b"d", b"e"}
        self.assertEqual(dh_psi(X, Y), {b"c", b"d"})

    def test_iknp(self):
        c = iknp_cost(2 ** 20, 128)
        self.assertEqual(c.comm_bits_receiver, 2 ** 20 * 128)
        self.assertEqual(c.comm_bits_sender, 2 ** 21 * 128)
        self.assertGreater(kos_cost(2 ** 20, 128).comm_bits_receiver, c.comm_bits_receiver)


class TestCommitFS(unittest.TestCase):
    def test_hash_commit(self):
        C, r = hash_commit(b"bid=5")
        self.assertTrue(hash_verify(C, b"bid=5", r))
        self.assertFalse(hash_verify(C, b"bid=6", r))

    def test_pedersen(self):
        P = Pedersen()
        c1, r1 = P.commit(10)
        c2, r2 = P.commit(32)
        self.assertTrue(P.verify(P.add(c1, c2), 42, r1 + r2))
        self.assertFalse(P.verify(c1, 11, r1))

    def test_transcript(self):
        t1, t2 = Transcript(b"d"), Transcript(b"d")
        t1.append(b"a", b"xy")
        t2.append(b"a", b"x")
        t2.append(b"", b"y")
        self.assertNotEqual(t1.challenge_bytes(b"c"), t2.challenge_bytes(b"c"))
        t3 = Transcript(b"d")
        t3.append(b"a", b"xy")
        self.assertEqual(Transcript(b"d").challenge_scalar(b"c", 101), Transcript(b"d").challenge_scalar(b"c", 101))
        self.assertEqual(len(t3.challenge_bytes(b"c", 80)), 80)

    def test_schnorr(self):
        G = ModPGroup()
        P = SchnorrProver(987654321, G)
        t = P.commit()
        s = P.respond(55)
        self.assertTrue(schnorr_verify(G, P.y, t, 55, s))
        s2 = P.respond(77)
        self.assertEqual(schnorr_extract(G, t, 55, s, 77, s2), 987654321 % G.order)
        ts, cs, ss = schnorr_simulate(G, P.y, 99)
        self.assertTrue(schnorr_verify(G, P.y, ts, cs, ss))
        y, proof = schnorr_nizk_prove(31337, G, b"ctx")
        self.assertTrue(schnorr_nizk_verify(G, y, proof, b"ctx"))
        self.assertFalse(schnorr_nizk_verify(G, y, proof, b"other"))


class TestCostsMatching(unittest.TestCase):
    def test_psi_costs(self):
        n = 2 ** 20
        rows = {r["protocol"]: r for r in compare_psi(n)}
        self.assertLess(rows["naive-hash (insecure)"]["comm_bits"], rows["KKRT16"]["comm_bits"])
        self.assertGreater(dh_psi_cost(n, n).public_key_ops, n)
        self.assertEqual(kkrt_cost(1000, 1000).comm_rounds, 3)
        self.assertGreater(circuit_psi_cost(n, n).comm_bits, vole_psi_cost(n, n).comm_bits)

    def test_gc(self):
        bristol = """3 7
2 2 2
1 1
2 1 0 2 4 AND
2 1 1 3 5 XOR
2 1 4 5 6 AND
"""
        g = parse_bristol(bristol)
        self.assertEqual((g.AND, g.XOR, g.and_depth), (2, 1, 2))
        self.assertEqual(g.garbled_bits("half-gates", 128), 2 * 256)
        self.assertEqual(g.garbled_bits("classical", 128), 3 * 512)
        self.assertEqual(g.garbled_bits("three-halves", 128), 2 * (192 + 5))
        self.assertEqual(adder_cost(32).AND, 31)
        self.assertEqual(equality_cost(64).and_depth, 6)

    def test_matching(self):
        self.assertEqual(hamming(0b1011, 0b0010), 2)
        self.assertEqual(hamming([1, 0, 1], [1, 1, 1]), 1)
        self.assertAlmostEqual(l2([0, 0], [3, 4]), 5.0)
        self.assertTrue(threshold_match([0, 0], [3, 4], 5, "l2"))
        self.assertEqual(hamming_ball_size(10, 2), 1 + 10 + 45)
        import numpy as np
        x, y = random_close_pair(128, 7, np.random.default_rng(0))
        self.assertEqual(hamming(x, y), 7)
        self.assertEqual(fuzzy_intersection([0b0000, 0b1111], [0b0001, 0b0111], 1), [(0, 0), (1, 1)])


if __name__ == "__main__":
    unittest.main()
