import json
import os
import shlex
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from crbench import runner  # noqa: E402
from crbench.envcapture import capture_env, warn_env  # noqa: E402
from crbench.lock import BenchLock, LockTimeout  # noqa: E402

PY = shlex.quote(sys.executable)


def py(code: str) -> str:
    return f"{PY} -c {shlex.quote(code)}"


class TestRunner(unittest.TestCase):
    def test_round_order_alternates(self):
        import random
        rng = random.Random(0)
        orders = [runner.round_order(["A", "B", "C"], r, "alternate", rng) for r in range(3)]
        self.assertEqual(orders, [["A", "B", "C"], ["B", "C", "A"], ["C", "A", "B"]])
        firsts = {runner.round_order(["A", "B"], r, "alternate", rng)[0] for r in range(2)}
        self.assertEqual(firsts, {"A", "B"})
        with self.assertRaises(ValueError):
            runner.round_order(["A"], 0, "bogus", rng)

    def test_interleaved_parsed_metric_and_logs(self):
        d = tempfile.mkdtemp()
        # An order-recording side channel proves interleaving really happens.
        trace = os.path.join(d, "trace.txt")
        arms = {
            "A": py(f"open({trace!r},'a').write('A');print('time: 4 ms')"),
            "B": py(f"open({trace!r},'a').write('B');print('time: 2 ms')"),
        }
        res = runner.run_interleaved(arms, repeats=4, warmup=1, parser="generic", log_dir=os.path.join(d, "logs"),
                                     use_lock=True, lock_path=os.path.join(d, "l.lock"), threads=1)
        self.assertEqual(open(trace).read(), "ABBAABBAAB")  # alternate order, 5 rounds
        self.assertEqual(res.samples("A"), [0.004] * 4)
        sp = res.speedups("A")["B"]
        self.assertAlmostEqual(sp["ratio"], 2.0)
        self.assertTrue(os.path.exists(os.path.join(d, "logs", "run.json")))
        self.assertTrue(os.path.exists(os.path.join(d, "logs", "A", "r000_warmup.log")))
        loaded = runner.load_run(os.path.join(d, "logs", "run.json"))
        self.assertEqual(loaded.samples("B"), [0.002] * 4)
        self.assertEqual(res.env["bench"]["threads"], 1)

    def test_failures_kept_not_counted(self):
        arms = {"ok": py("print('time: 1 s')"), "bad": py("import sys; print('time: 1 s'); sys.exit(134)"),
                "nometric": py("print('nothing')")}
        res = runner.run_interleaved(arms, repeats=2, warmup=0, parser="generic", use_lock=False)
        self.assertEqual(len(res.samples("ok")), 2)
        self.assertEqual(res.samples("bad"), [])
        self.assertEqual(len(res.failures("bad")), 2)
        self.assertIn("not found", res.failures("nometric")[0].error)
        self.assertEqual(res.summary()["bad"]["failures"], 2)

    def test_wall_clock_and_extract(self):
        res = runner.run_interleaved({"s": py("pass")}, repeats=2, warmup=0, use_lock=False)
        self.assertEqual(res.metric, "wall")
        self.assertTrue(all(v > 0 for v in res.samples("s")))
        res2 = runner.run_interleaved({"x": py("print(42)")}, repeats=1, warmup=0, use_lock=False,
                                      extract=lambda out: float(out.split()[0]))
        self.assertEqual(res2.samples("x"), [42.0])

    def test_timeout(self):
        res = runner.run_interleaved({"slow": py("import time; time.sleep(5)")}, repeats=1, warmup=0,
                                     timeout=0.3, use_lock=False)
        self.assertIn("timeout", res.failures("slow")[0].error)

    def test_stale_build(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "src")
        os.makedirs(src)
        binary = os.path.join(d, "bench")
        open(binary, "w").write("x")
        old = time.time() - 100
        os.utime(binary, (old, old))
        open(os.path.join(src, "k.cpp"), "w").write("int main(){}")
        self.assertEqual(len(runner.stale_build_check(binary, [src])), 1)
        os.utime(binary, None)
        self.assertEqual(runner.stale_build_check(binary, [src]), [])
        self.assertTrue(runner.stale_build_check(os.path.join(d, "missing"), [src]))


class TestEnvLock(unittest.TestCase):
    def test_capture_env(self):
        e = capture_env(os.getcwd())
        self.assertIn("cpu", e)
        self.assertIn("python", e)
        self.assertEqual(len(e["host_id"]), 12)
        json.dumps(e)
        self.assertIsInstance(warn_env(e), list)

    def test_warn_env(self):
        w = warn_env({"cpu": {"governor": "powersave", "loadavg": [50.0, 0, 0], "logical_cpus": 8},
                      "target": {"git_dirty": True}})
        self.assertEqual(len(w), 3)

    def test_lock_exclusive(self):
        p = os.path.join(tempfile.mkdtemp(), "b.lock")
        with BenchLock(p, label="first") as lk:
            self.assertEqual(lk.holder()["label"], "first")
            with self.assertRaises(LockTimeout):
                BenchLock(p, timeout=0.2, poll=0.05).acquire()
        with BenchLock(p, timeout=0.2):
            pass


if __name__ == "__main__":
    unittest.main()
