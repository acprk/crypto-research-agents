import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptomath.algebra import (  # noqa: E402
    GF, CyclotomicNTT, DirichletGroup, PolyRing, SlotEncoder, canonical_poly_function,
    carmichael_lambda, chen_han_degree_bound, count_polynomial_functions, cosets,
    crt, cyclotomic_poly, decomposition, dft_bluestein, dft_naive, digits,
    euler_phi, factor_cyclotomic_mod_p, factorint, find_ntt_prime, find_ntt_primes,
    frobenius_subgroup, gauss_sum, hensel_lift_root, hs_digit_extract,
    hs_digit_extraction_counts, hs_lift_poly, intt_cyclic, intt_negacyclic,
    is_irreducible, is_null_poly, is_prime, kempner, lowest_digit_retain_poly,
    mult_order, negacyclic_mul_ntt, ntt_cyclic, ntt_negacyclic, null_poly_min,
    poly_divmod, poly_eval, poly_mul, primitive_root, quotient_generators,
    root_of_unity, subgroup_generated, unit_group_generators, units,
)


class TestNumberTheory(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(factorint(360), {2: 3, 3: 2, 5: 1})
        self.assertEqual(euler_phi(105), 48)
        self.assertEqual(carmichael_lambda(16), 4)
        self.assertEqual(mult_order(2, 7), 3)
        self.assertEqual(mult_order(2, 31), 5)
        self.assertTrue(is_prime(2 ** 61 - 1))
        self.assertFalse(is_prime(561))
        self.assertEqual(primitive_root(7), 3)
        x, M = crt([2, 3, 2], [3, 5, 7])
        self.assertEqual((x, M), (23, 105))

    def test_unit_group(self):
        for m in (8, 15, 16, 40, 63, 64):
            gens = unit_group_generators(m)
            H = subgroup_generated([g for g, _ in gens], m)
            self.assertEqual(H, units(m))
            prod = 1
            for _, o in gens:
                prod *= o
            self.assertEqual(prod, euler_phi(m))
        cs = cosets(frobenius_subgroup(2, 31), 31)
        self.assertEqual(len(cs), 6)
        self.assertTrue(all(len(c) == 5 for c in cs))

    def test_quotient_generators(self):
        for p, m in ((2, 31), (3, 40), (5, 63)):
            H = frobenius_subgroup(p, m)
            gens = quotient_generators(m, H)
            size = 1
            for _, o in gens:
                size *= o
            self.assertEqual(size * len(H), euler_phi(m))

    def test_ntt_primes(self):
        for q in find_ntt_primes(30, 128, 3):
            self.assertTrue(is_prime(q) and q % 128 == 1 and q < 2 ** 30)
        q = find_ntt_prime(20, 64)
        w = root_of_unity(64, q)
        self.assertEqual(pow(w, 64, q), 1)
        self.assertNotEqual(pow(w, 32, q), 1)


class TestPoly(unittest.TestCase):
    def test_cyclotomic(self):
        self.assertEqual(cyclotomic_poly(1), [-1, 1])
        self.assertEqual(cyclotomic_poly(8), [1, 0, 0, 0, 1])
        self.assertEqual(cyclotomic_poly(12), [1, 0, -1, 0, 1])
        # Phi_105 is the first with a coefficient -2
        self.assertIn(-2, cyclotomic_poly(105))
        for m in (9, 20, 21, 30):
            self.assertEqual(len(cyclotomic_poly(m)) - 1, euler_phi(m))

    def test_divmod(self):
        a = [random.randrange(-50, 50) for _ in range(12)]
        b = [3, 0, 1, 1]
        q, r = poly_divmod(a, b)
        back = poly_mul(q, b)
        back = [x + (r[i] if i < len(r) else 0) for i, x in enumerate(back + [0] * (len(a) - len(back)))]
        self.assertEqual(back[: len(a)], a)

    def test_ring_and_automorphisms(self):
        for m, q in ((16, 97), (15, 31), (12, 13)):
            R = PolyRing(m=m, q=q)
            a, b = R.uniform(), R.uniform()
            # automorphisms are ring homomorphisms and compose correctly
            for k in units(m)[:4]:
                self.assertTrue(all(R.automorphism(R.mul(a, b), k) == R.mul(R.automorphism(a, k), R.automorphism(b, k))))
            k1, k2 = units(m)[1], units(m)[-1]
            self.assertTrue(all(R.automorphism(R.automorphism(a, k1), k2) == R.automorphism(a, k1 * k2 % m)))
            # X^m = 1
            self.assertTrue(all(R.pow(R.monomial(1), m) == R.one()))

    def test_negacyclic_matches_generic(self):
        R1 = PolyRing(m=32, q=257)
        R2 = PolyRing(modulus=[1] + [0] * 15 + [1], q=257)
        a, b = R1.uniform(), R1.uniform()
        self.assertTrue(all(R1.mul(a, b) == R2._reduce_full(R2._full_product(a, b)) % 257))


class TestFiniteField(unittest.TestCase):
    def test_gf256(self):
        F = GF(2, 8, modulus=[1, 1, 0, 1, 1, 0, 0, 0, 1])
        a = F.from_int(0x53)
        self.assertEqual((a * a.inverse()).to_int(), 1)
        self.assertEqual(a.inverse().to_int(), 0xCA)  # classic AES example
        g = F.primitive_element()
        self.assertEqual(len({(g ** i).to_int() for i in range(255)}), 255)

    def test_prime_power_fields(self):
        for p, k in ((3, 2), (5, 3), (7, 2)):
            F = GF(p, k)
            self.assertTrue(is_irreducible(F.modulus, p))
            x = F.random(random.Random(1))
            self.assertEqual(x ** F.order, x)  # Frobenius^k = id
            mp = F.gen.minpoly()
            self.assertEqual(mp, F.modulus)


class TestSlots(unittest.TestCase):
    def test_decomposition(self):
        for p, m in ((2, 7), (3, 45), (17, 32), (5, 63)):
            d = decomposition(p, m)
            self.assertEqual(d["e"] * d["f"] * d["g"], euler_phi(m))

    def test_factor_cyclotomic(self):
        reps, fs = factor_cyclotomic_mod_p(21, 2)
        self.assertEqual(len(fs), euler_phi(21) // mult_order(2, 21))
        prod = [1]
        for f in fs:
            prod = poly_mul(prod, f, 2)
        self.assertEqual(prod, [c % 2 for c in cyclotomic_poly(21)])

    def test_encoder_roundtrip_and_homomorphism(self):
        rng = random.Random(7)
        for m, p, e in ((7, 2, 1), (15, 2, 3), (16, 17, 1), (21, 5, 2)):
            enc = SlotEncoder(m, p, e)
            t = enc.t
            R = PolyRing(m=m, q=t)
            xs = [[rng.randrange(t) for _ in range(enc.slot_degree)] for _ in range(enc.num_slots)]
            ys = [[rng.randrange(t) for _ in range(enc.slot_degree)] for _ in range(enc.num_slots)]
            a, b = enc.encode(xs), enc.encode(ys)
            norm = lambda v: [c % t for c in v] + [0] * (enc.slot_degree - len(v))  # noqa: E731
            self.assertEqual([norm(v) for v in enc.decode(a)], [norm(v) for v in xs])
            # products are slot-wise
            prod = enc.decode(list(R.mul(a, b)))
            for i, Fi in enumerate(enc.factors):
                ref = poly_divmod(poly_mul(xs[i], ys[i], t), Fi, t)[1] or [0]
                self.assertEqual(prod[i], ref)
            # constants
            self.assertEqual(enc.decode_constants(enc.encode(list(range(enc.num_slots)))), list(range(enc.num_slots)))

    def test_frobenius_acts_inside_slots(self):
        enc = SlotEncoder(31, 2, 1)
        R = PolyRing(m=31, q=2)
        x = enc.encode([[1, 1], [0, 1, 1], [1], [0, 0, 1], [1, 0, 1], [0, 1]])
        fx = enc.decode(list(R.automorphism(x, 2)))
        for i, (s, Fi) in enumerate(zip(enc.decode(x), enc.factors)):
            self.assertEqual(fx[i], poly_divmod(poly_mul(s, s, 2), Fi, 2)[1] or [0])


class TestNTT(unittest.TestCase):
    def test_cyclic_and_negacyclic(self):
        q = find_ntt_prime(30, 128)
        a = [random.randrange(q) for _ in range(64)]
        self.assertEqual(intt_cyclic(ntt_cyclic(a, q), q), a)
        self.assertEqual(intt_negacyclic(ntt_negacyclic(a, q), q), a)
        w = root_of_unity(64, q)
        self.assertEqual(ntt_cyclic(a, q, w), dft_naive(a, q, w))
        b = [random.randrange(q) for _ in range(64)]
        R = PolyRing(m=128, q=q)
        self.assertEqual(negacyclic_mul_ntt(a, b, q), [int(x) for x in R.mul(a, b)])

    def test_bluestein(self):
        n = 15
        q = find_ntt_prime(40, 2 * n * 64)  # also admits the power-of-two convolution
        w = root_of_unity(n, q)
        a = [random.randrange(q) for _ in range(n)]
        self.assertEqual(dft_bluestein(a, q, w), dft_naive(a, q, w))

    def test_cyclotomic_ntt(self):
        for m in (21, 16, 15):
            q = find_ntt_prime(30, 2 * m)
            C = CyclotomicNTT(m, q)
            R = PolyRing(m=m, q=q)
            x = [random.randrange(q) for _ in range(C.n)]
            y = [random.randrange(q) for _ in range(C.n)]
            self.assertEqual(C.inverse(C.forward(x)), x)
            self.assertEqual([u * v % q for u, v in zip(C.forward(x), C.forward(y))], C.forward([int(c) for c in R.mul(x, y)]))


class TestPadic(unittest.TestCase):
    def test_hensel_and_digits(self):
        r = hensel_lift_root([-2, 0, 1], 3, 7, 5)  # sqrt(2) in Z_7
        self.assertEqual((r * r - 2) % 7 ** 5, 0)
        self.assertEqual(digits(-1, 3, 3, balanced=True), [-1, 0, 0])

    def test_kempner_and_null(self):
        self.assertEqual([kempner(n) for n in (2, 4, 8, 9, 16, 27)], [2, 4, 4, 6, 6, 9])
        self.assertTrue(is_null_poly(null_poly_min(16), 16))
        self.assertEqual(count_polynomial_functions(4), 64)
        # brute-force count for n = 4: all functions coming from polynomials of degree < 4
        from itertools import product
        funcs = set()
        for c in product(range(4), repeat=4):
            funcs.add(tuple(poly_eval(c, x, 4) for x in range(4)))
        self.assertEqual(len(funcs), 64)

    def test_canonical_function(self):
        self.assertIsNone(canonical_poly_function(lambda x: x // 2, 4))
        P = canonical_poly_function(lambda x: x ** 5 + 3, 8)
        self.assertLessEqual(len(P) - 1, kempner(8) - 1)

    def test_hs_lifting(self):
        for p, e in ((2, 4), (3, 3), (5, 2), (7, 2)):
            F = hs_lift_poly(p, e)
            self.assertEqual(len(F) - 1, p)
            for z0 in range(p):
                for ep in range(1, e + 1):
                    for z1 in range(-3, 4):
                        self.assertEqual((poly_eval(F, z0 + p ** ep * z1, p ** (ep + 1)) - z0) % p ** (ep + 1), 0)

    def test_digit_extraction(self):
        for p, e, r in ((2, 5, 2), (3, 4, 2), (5, 3, 1)):
            for z in range(p ** e):
                out = hs_digit_extract(z, p, e, r)
                self.assertEqual(out["result"], z // p ** r)
            c = hs_digit_extraction_counts(p, e, r)
            self.assertEqual(c["F_evals"], out["F_evals"])
            self.assertEqual(c["depth"], out["depth"])

    def test_lowest_digit_retain(self):
        for p, e in ((2, 3), (3, 3), (5, 2), (5, 3)):
            G = lowest_digit_retain_poly(p, e)
            self.assertLessEqual(len(G) - 1, chen_han_degree_bound(p, e))
            for x in range(p ** e):
                d = x % p
                if d > p // 2 and p > 2:
                    d -= p
                self.assertEqual(poly_eval(G, x, p ** e), d % p ** e)


class TestCharacters(unittest.TestCase):
    def test_orthogonality_and_gauss(self):
        m = 20
        G = DirichletGroup(m)
        chars = list(G)
        self.assertEqual(len(chars), euler_phi(m))
        for chi in chars:
            s = sum(chi(a) for a in units(m))
            self.assertAlmostEqual(abs(s), 0 if not chi.is_trivial() else euler_phi(m), places=8)
        for chi in DirichletGroup(11):
            if not chi.is_trivial():
                self.assertAlmostEqual(abs(gauss_sum(chi)), 11 ** 0.5, places=8)
        H = frobenius_subgroup(3, m)
        self.assertEqual(len(G.annihilator(H)), euler_phi(m) // len(H))


if __name__ == "__main__":
    unittest.main()
