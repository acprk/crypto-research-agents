import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from crbench import parsers  # noqa: E402
from crbench.parsers import Record, parse_text, register_parser, values  # noqa: E402

# All logs below are SYNTHETIC, written to mimic each tool's output format.


class TestParsers(unittest.TestCase):
    def test_generic(self):
        txt = "keygen time: 12.5 ms\nEncrypt elapsed = 3 us\nbootstrap took 1.5 s\nRESULT name=toy t=2.5ms mults=26 status=CORRECT\n"
        recs = parse_text(txt, "generic")
        t = values(recs, "time")
        self.assertAlmostEqual(t[0], 0.0125)
        self.assertAlmostEqual(t[1], 3e-6)
        self.assertAlmostEqual(t[2], 1.5)
        self.assertAlmostEqual(values(recs, "t", "toy")[0], 0.0025)
        self.assertEqual(values(recs, "mults", "toy"), [26.0])
        self.assertTrue(any(r.metric == "status" and r.value == "CORRECT" for r in recs))

    def test_criterion(self):
        txt = "pbs/toy_param_2bit\n                        time:   [11.200 ms 11.350 ms 11.500 ms]\n"
        recs = parse_text(txt, "auto")
        mid = [r for r in recs if r.metric == "time"][0]
        self.assertAlmostEqual(mid.value, 0.01135)
        self.assertEqual(mid.label, "pbs/toy_param_2bit")
        self.assertAlmostEqual(values(recs, "time_lo")[0], 0.0112)

    def test_gobench(self):
        txt = "goos: linux\nBenchmarkToyMul/logN=10-8   \t    1000\t   1234567 ns/op\t  4096 B/op\t  12 allocs/op\nPASS\n"
        recs = parse_text(txt, "auto")
        self.assertAlmostEqual(values(recs, "time")[0], 1.234567e-3)
        self.assertEqual(recs[0].label, "BenchmarkToyMul/logN=10")
        self.assertEqual(values(recs, "alloc"), [4096.0])

    def test_gbench(self):
        txt = ("-----------------------------------------------------------\n"
               "Benchmark                 Time             CPU   Iterations\n"
               "-----------------------------------------------------------\n"
               "BM_ToyEvalMult         1.50 ms         1.49 ms          466\n")
        recs = parse_text(txt, "auto")
        self.assertAlmostEqual(values(recs, "time")[0], 1.5e-3)
        self.assertAlmostEqual(values(recs, "cpu_time")[0], 1.49e-3)

    def test_helib(self):
        txt = "  recrypt: 40.5 / 3 = 13.5   [recryption.cpp]\n  multiplyBy: 2.4 / 12 = 0.2   [Ctxt.cpp]\n"
        recs = parse_text(txt, "auto")
        self.assertEqual(values(recs, "time", "recrypt"), [13.5])
        self.assertEqual(values(recs, "count", "multiplyBy"), [12.0])

    def test_openfhe(self):
        txt = "Bootstrapping time: 812.4 ms\nEvalMult time [ms]: 4.2\n"
        recs = parse_text(txt, "openfhe")
        self.assertAlmostEqual(values(recs, "time")[0], 0.8124)
        self.assertAlmostEqual(values(recs, "time")[1], 0.0042)

    def test_lattice_estimator(self):
        txt = ("usvp                 :: rop: ≈2^131.2, red: ≈2^131.2, δ: 1.004000, β: 385, d: 1900, tag: usvp\n"
               "bdd                  :: rop: ≈2^129.8, red: ≈2^129.0, svp: ≈2^128.1, β: 377, η: 400, d: 1880, tag: bdd\n"
               "dual_hybrid          :: rop: ≈2^135.0, red: ≈2^134.9, guess: ≈2^127.3, β: 395, p: 3, zeta: 0, tag: dual_hybrid\n")
        recs = parse_text(txt, "auto")
        self.assertEqual(values(recs, "rop_bits", "bdd"), [129.8])
        self.assertEqual(values(recs, "beta", "usvp"), [385.0])
        sec = [r for r in recs if r.metric == "security_bits"][0]
        self.assertEqual(sec.value, 129.8)
        self.assertEqual(sec.label, "min:bdd")

    def test_sat(self):
        txt = "c some banner\ns UNSATISFIABLE\nc total process time since initialization:         2.41    seconds\n"
        recs = parse_text(txt, "auto")
        self.assertEqual(values(recs, "time"), [2.41])
        self.assertTrue(any(r.value == "UNSATISFIABLE" for r in recs))

    def test_mpspdz(self):
        txt = "Time = 0.512 seconds \nData sent = 1.5 MB in ~42 rounds (party 0)\nGlobal data sent = 3 MB (all parties)\n"
        recs = parse_text(txt, "auto")
        self.assertEqual(values(recs, "time"), [0.512])
        self.assertEqual(values(recs, "comm"), [1.5e6])
        self.assertEqual(values(recs, "rounds"), [42.0])
        self.assertEqual(values(recs, "comm_global"), [3e6])

    def test_gnu_time(self):
        txt = "\tElapsed (wall clock) time (h:mm:ss or m:ss): 1:02.50\n\tMaximum resident set size (kbytes): 2048\n"
        recs = parse_text(txt, "auto")
        self.assertEqual(values(recs, "time"), [62.5])
        self.assertEqual(values(recs, "max_rss"), [2048 * 1024.0])

    def test_register_custom(self):
        @register_parser("toytool", "custom", sniff=r"^TOYTOOL")
        def _p(text):
            return [Record("time", float(text.split()[-1]), "s", "toy", 1)]

        self.assertIn("toytool", parsers.REGISTRY)
        self.assertEqual(values(parse_text("TOYTOOL v1 0.25", "auto")), [0.25])
        parsers.REGISTRY.pop("toytool")

    def test_regex_parser_builder(self):
        parsers.regex_parser("toyrx", r"^lat=(?P<value>\d+(?:\.\d+)?)(?P<unit>ms)", description="x")
        self.assertEqual(values(parse_text("lat=3ms\n", "toyrx")), [0.003])
        parsers.REGISTRY.pop("toyrx")

    def test_adapters_reference_real_parsers(self):
        from crbench.adapters import ADAPTERS
        for name, a in ADAPTERS.items():
            self.assertIn(a["parser"], parsers.REGISTRY, name)

    def test_unknown(self):
        with self.assertRaises(KeyError):
            parse_text("x", "nope")
        with self.assertRaises(ValueError):
            parsers.to_seconds(1, "fortnights")


if __name__ == "__main__":
    unittest.main()
