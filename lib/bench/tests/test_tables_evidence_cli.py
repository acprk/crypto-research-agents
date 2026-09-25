import io
import os
import shlex
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from crbench import cli, evidence, tables  # noqa: E402
from crbench.tables import Cell, Column  # noqa: E402

TOY_TEX = r"""\documentclass{llncs}
\usepackage{booktabs}
\setlength{\tabcolsep}{4.5pt}
\begin{document}
\section{Evaluation}
On the toy ring ($n=1024$) keygen takes 1.23 s and our variant 0.61 s,
a 2.02$\times$ speed-up\evid{E3} (see Table~\ref{tab:x3} and~\cite{toy2024}).
Memory drops from 1{,}536 MB to 768 MB.
The estimator reports $2^{128.4}$ operations.
An untraced claim: 17.5 ms per gate.
Here 99.9 ms is ignored % crbench:ignore
We use 3 parties and the year 2024.
\end{document}
"""


def _write_ledger(path):
    evidence.append_row(path, "1.23 s", "crbench run -a base=... ", "results/toy/run.json", "abc1234", "host:aa", "2026-01-01", "5/median")
    evidence.append_row(path, "0.61 s", "crbench run -a new=...", "results/toy/run.json", "abc1234", "host:aa", "2026-01-01", "5/median")
    evidence.append_row(path, "2.02×", "derived: E1/E2", "-", date="2026-01-01")
    evidence.append_row(path, "1,536 MB → 768 MB", "gnu-time", "results/toy/mem.log", "abc1234", "host:aa", "2026-01-01", "3/median")
    evidence.append_row(path, "2^128.4", "sage -python est.py", "results/toy/est.log", "def5678", "host:aa", "2026-01-01", "1")


class TestTables(unittest.TestCase):
    def test_markdown_latex(self):
        rows = [{"s": "toy", "t": Cell(1.5, "E1"), "x": Cell(2.0, "E2", ".2f")}, {"s": "b_2", "t": 3, "x": None}]
        cols = [Column("s", "Scheme", align="l"), Column("t", "Time (s)", ".2f"), Column("x", "Gain", suffix="×")]
        md = tables.to_markdown(rows, cols, "cap")
        self.assertIn("1.50[^E1]", md)
        self.assertIn("2.00×[^E2]", md)
        self.assertIn("[^E1]: EVIDENCE.md row E1", md)
        tex = tables.to_latex(rows, cols, "cap", "tab:t", visible=True)
        self.assertIn(r"\toprule", tex)
        self.assertIn(r"2.00$\times$\evid{E2}", tex)
        self.assertIn(r"b\_2", tex)
        self.assertIn(r"\textsuperscript", tex)

    def test_from_run_summary(self):
        summary = {"A": {"n": 3, "median": 2.0, "iqr": 0.1}, "B": {"n": 3, "median": 1.0, "iqr": 0.05}}
        sp = {"B": {"ratio": 2.0, "ci_low": 1.9, "ci_high": 2.1}}
        rows, cols = tables.from_run_summary(summary, sp, {"B": "E7"})
        self.assertIn(r"\evid{E7}", tables.to_latex(rows, cols))


class TestEvidence(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.led = os.path.join(self.d, "EVIDENCE.md")
        _write_ledger(self.led)
        self.tex = os.path.join(self.d, "paper.tex")
        open(self.tex, "w").write(TOY_TEX)

    def test_read_and_ids(self):
        rows = evidence.read_ledger(self.led)
        self.assertEqual([r["id"] for r in rows], ["E1", "E2", "E3", "E4", "E5"])
        self.assertEqual(rows[2]["command"], "derived: E1/E2")
        self.assertEqual(evidence.next_id(rows), "E6")
        with self.assertRaises(ValueError):
            evidence.append_row(self.led, "1", "c", "l", id="E1")

    def test_normalize(self):
        self.assertEqual(evidence.normalize_number("1{,}536"), "1536")
        self.assertEqual(evidence.normalize_number("2.50"), "2.5")
        self.assertEqual(evidence.numbers_in("1,536 MB → 768 MB"), ["1536", "768"])

    def test_validate_ledger(self):
        rows = evidence.read_ledger(self.led)
        errs = [i for i in evidence.validate_ledger(rows, root=self.d) if i.severity == "error"]
        self.assertTrue(all(i.kind == "log-not-found" for i in errs))
        for rel in ("results/toy/run.json", "results/toy/mem.log", "results/toy/est.log"):
            os.makedirs(os.path.join(self.d, os.path.dirname(rel)), exist_ok=True)
            open(os.path.join(self.d, rel), "w").write("x")
        errs = [i for i in evidence.validate_ledger(rows, root=self.d) if i.severity == "error"]
        self.assertEqual(errs, [])
        bad = rows + [{"id": "E1", "printed": "", "command": "derived: E99", "log": "", "commit": "", "machine": "", "date": "", "runs": "", "_line": 99},
                      {"id": "E8", "printed": "3 s", "command": "x", "log": "-", "commit": "", "machine": "", "date": "", "runs": "", "_line": 100}]
        kinds = {i.kind for i in evidence.validate_ledger(bad)}
        self.assertTrue({"duplicate-id", "missing-field", "bad-derivation", "missing-log"} <= kinds)

    def test_audit_tex(self):
        rows = evidence.read_ledger(self.led)
        issues = evidence.audit_tex(self.tex, rows)
        untraced = [i.number for i in issues if i.kind == "untraced"]
        self.assertEqual(untraced, ["17.5"])  # 99.9 ignored, n=1024/3/2024 not measurement-like, 4.5pt in preamble
        strict = [i.number for i in evidence.audit_tex(self.tex, rows, strict=True) if i.kind == "untraced"]
        self.assertIn("1024", strict)
        self.assertIn("2024", strict)

    def test_audit_evid_mismatch_and_unknown(self):
        rows = evidence.read_ledger(self.led)
        p = os.path.join(self.d, "bad.tex")
        open(p, "w").write("A 2.05$\\times$ gain\\evid{E3}; also 1.23 s\\evid{E42}.\n")
        kinds = sorted(i.kind for i in evidence.audit_tex(p, rows))
        self.assertIn("mismatch", kinds)
        self.assertIn("unknown-id", kinds)

    def test_cli(self):
        buf, err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf), redirect_stderr(err):
            rc = cli.main(["audit-tex", self.tex, self.led])
        self.assertEqual(rc, 1)
        self.assertIn("17.5", buf.getvalue())
        with redirect_stdout(io.StringIO()) as o, redirect_stderr(io.StringIO()):
            rc = cli.main(["evidence", "add", self.led, "--printed", "17.5 ms", "--command", "crbench run ...",
                           "--log", "results/toy/gate.log", "--commit", "abc", "--machine", "host:aa", "--runs", "5/median"])
        self.assertEqual(rc, 0)
        self.assertEqual(o.getvalue().strip(), "E6")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["audit-tex", self.tex, self.led]), 0)
            self.assertEqual(cli.main(["evidence", "check", self.led]), 0)
            self.assertEqual(cli.main(["parsers"]), 0)

    def test_cli_run_table(self):
        py = shlex.quote(sys.executable)
        logd = os.path.join(self.d, "run")
        with redirect_stdout(io.StringIO()) as o, redirect_stderr(io.StringIO()):
            rc = cli.main(["run", "-a", f"base={py} -c \"print('time: 2 ms')\"", "-a", f"new={py} -c \"print('time: 1 ms')\"",
                           "-n", "3", "-w", "0", "--parser", "generic", "--log-dir", logd, "--no-lock", "-q"])
        self.assertEqual(rc, 0)
        self.assertIn("speedup_vs_base", o.getvalue())
        with redirect_stdout(io.StringIO()) as o:
            cli.main(["table", os.path.join(logd, "run.json"), "--latex", "--evidence", "new:speedup=E9"])
        self.assertIn(r"\evid{E9}", o.getvalue())
        with redirect_stdout(io.StringIO()) as o:
            cli.main(["stats", os.path.join(logd, "run.json")])
        self.assertIn('"median"', o.getvalue())


if __name__ == "__main__":
    unittest.main()
