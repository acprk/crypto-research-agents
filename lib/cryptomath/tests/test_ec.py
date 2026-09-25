"""Tests for cryptomath.ec."""
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cryptomath.ec import (  # noqa: E402
    ECGroup, EllipticCurve, ModPGroup, ZpStarGroup, bsgs, expected_generic_cost,
    find_prime_order_curve, pohlig_hellman, pollard_rho, secp256k1, sqrt_mod,
)


class TestCurve(unittest.TestCase):
    def test_sqrt_mod(self):
        for p in (13, 17, 97, 10009, 65537):
            for a in range(1, 60):
                r = sqrt_mod(a, p)
                if r is not None:
                    self.assertEqual(r * r % p, a % p)

    def test_count_matches_enumeration(self):
        for p, a, b in ((97, 2, 3), (101, 1, 1), (103, 0, 7)):
            E = EllipticCurve(p, a, b)
            self.assertEqual(E.order(), len(E.points()) + 1)
            self.assertLessEqual(abs(E.order() - p - 1), 2 * p ** 0.5)  # Hasse

    def test_group_law(self):
        E = EllipticCurve(10007, 3, 5)
        rng = random.Random(1)
        P, Q, R = (E.random_point(rng) for _ in range(3))
        self.assertEqual(E.add(E.add(P, Q), R), E.add(P, E.add(Q, R)))
        self.assertEqual(E.add(P, Q), E.add(Q, P))
        self.assertIsNone(E.add(P, E.neg(P)))
        self.assertIsNone(E.mul(E.order(), P))
        for k in (0, 1, 2, 17, 12345, -5):
            self.assertEqual(E.mul(k, P), E.jmul(k, P))
            if k >= 0:
                self.assertEqual(E.mul(k, P), E.ladder(k, P))

    def test_secp256k1(self):
        E, G, n = secp256k1()
        self.assertTrue(E.is_on_curve(G))
        self.assertIsNone(E.jmul(n, G))
        self.assertEqual(E.jmul(n + 5, G), E.jmul(5, G))
        # 2G known x-coordinate
        self.assertEqual(E.jmul(2, G)[0],
                         0xC6047F9441ED7D6D3045406E95C07CD85C778E4B8CEF3CA7ABAC09B95C709EE5)


class TestDLP(unittest.TestCase):
    def test_bsgs_ec(self):
        G = ECGroup.small(10007, seed=3)
        for x in (0, 1, 1234, G.order - 1):
            h = G.exp(G.generator, x)
            self.assertEqual(bsgs(G, G.generator, h), x % G.order)

    def test_bsgs_modp_and_rho(self):
        M = ModPGroup.small(36)
        x = 0x5DEECE66D % M.q
        h = M.exp(M.g, x)
        self.assertEqual(bsgs(M, M.g, h), x)
        self.assertEqual(pollard_rho(M, M.g, h, seed=2), x)

    def test_rho_ec(self):
        E, Gp = find_prime_order_curve(100003, seed=5)
        G = ECGroup(E, Gp, E.order())
        h = G.exp(Gp, 31337)
        self.assertEqual(pollard_rho(G, Gp, h), 31337 % G.order)

    def test_pohlig_hellman(self):
        Z = ZpStarGroup(8101, 6)          # 8100 = 2^2 3^4 5^2, 6 is a primitive root
        for x in (1, 4321, 8099):
            self.assertEqual(pohlig_hellman(Z, 6, pow(6, x, 8101), 8100), x)

    def test_hash_to_group_and_cost(self):
        G = ECGroup.small(10007)
        P = G.hash_to_group(b"hello")
        self.assertTrue(G.contains(P))
        M = ModPGroup()
        self.assertTrue(M.contains(M.hash_to_group(b"x")))
        c = expected_generic_cost(2 ** 64)
        self.assertEqual(c["security_bits"], 32)


if __name__ == "__main__":
    unittest.main()
