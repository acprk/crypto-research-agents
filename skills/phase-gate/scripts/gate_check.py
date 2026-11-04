#!/usr/bin/env python3
"""gate_check.py -- mechanical part of a phase gate on the research blackboard.

    python3 gate_check.py --project . --phase P6
    python3 gate_check.py --project . --phase P7 --paper paper/
    python3 gate_check.py --selftest

Checks (each prints PASS/FAIL/WARN; exit 1 if any FAIL):

  all phases  STATE.md has a gate section for the phase ("## Gate P<k>" or any heading containing
              "Gate" and "P<k>") and every checkbox in it is ticked ("- [x]").
              Unticked boxes may be waived with "- [~] ... WAIVED: <reason> (DECISIONS D-<n>)".
  >= P6       CLAIMS.md: no claim in status `open`; every `survived`/`weakened` claim has at
              least one EVIDENCE ref and a non-empty falsifier-evidence cell.
  >= P7       with --paper DIR: every number-with-unit in the .tex sources (e.g. "3.2x", "41%",
              "2^{128}", "12.5 ms") must appear verbatim in the EVIDENCE.md column
              "number/fact as printed in paper", unless the line carries "% no-evidence: <reason>".
  >= P8       refs.bib exists and bib-verify-report.md is fresh for it and lists only VERIFIED entries.
              Freshness: the report's "bib-sha256: <hex>" line must equal sha256(refs.bib)
              (written by verify_bib.py). Legacy reports without that line fall back to git
              commit times (both files tracked and unmodified), then to file mtimes (WARN).

Blackboard formats follow SPEC section 3 (tables with a header row; column order as in SPEC).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile

PHASES = [f"P{i}" for i in range(9)]


def read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return None


def md_table(text: str, must_have: str) -> list[dict]:
    """Parse the first Markdown table whose header contains `must_have` (case-insensitive)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and must_have.lower() in line.lower():
            header = [h.strip().lower() for h in line.strip().strip("|").split("|")]
            rows = []
            for row in lines[i + 2:]:
                if not row.strip().startswith("|"):
                    break
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                cells += [""] * (len(header) - len(cells))
                rows.append(dict(zip(header, cells)))
            return rows
    return []


def col(row: dict, *prefixes: str) -> str:
    for k, v in row.items():
        if any(k.startswith(p) for p in prefixes):
            return v
    return ""


def gate_section(state: str, phase: str) -> list[str] | None:
    lines = state.splitlines()
    start = None
    for i, l in enumerate(lines):
        if l.lstrip().startswith("#") and "gate" in l.lower() and re.search(rf"\b{phase}\b", l):
            start = i
            break
    if start is None:
        return None
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    out = []
    for l in lines[start + 1:]:
        if l.lstrip().startswith("#") and len(l) - len(l.lstrip("#")) <= level:
            break
        out.append(l)
    return out


def _git_commit_time(path: str) -> int | None:
    """Commit time of the last commit touching `path`, or None if untracked / modified / no git."""
    d, f = os.path.split(os.path.abspath(path))
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", f], cwd=d,
                               capture_output=True, text=True, timeout=10)
        if dirty.returncode != 0 or dirty.stdout.strip():
            return None
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", f], cwd=d,
                             capture_output=True, text=True, timeout=10)
        return int(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def report_fresh(bib: str, rep: str) -> tuple[bool, str]:
    """Is the bib-verify report up to date for refs.bib?  Returns (fresh, method)."""
    m = re.search(r"^bib-sha256:\s*([0-9a-f]{64})\s*$", read(rep) or "", re.M)
    if m:
        with open(bib, "rb") as fh:
            return m.group(1) == hashlib.sha256(fh.read()).hexdigest(), "sha256"
    tb, tr = _git_commit_time(bib), _git_commit_time(rep)
    if tb is not None and tr is not None:
        return tr >= tb, "git commit time"
    return os.path.getmtime(rep) >= os.path.getmtime(bib), "file mtime"


NUM_PAT = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?\s*(?:\\times|×|x\b|\\%|%|\s?(?:ms|s|us|µs|MB|MiB|KB|KiB|GB|GiB|bits?)\b)"
                     r"|2\^\{?\d+\}?)")


def check(project: str, phase: str, paper: str | None) -> list[tuple[str, str]]:
    res: list[tuple[str, str]] = []
    k = PHASES.index(phase)
    state = read(os.path.join(project, "STATE.md"))
    if state is None:
        return [("FAIL", "STATE.md missing")]
    sec = gate_section(state, phase)
    if sec is None:
        res.append(("FAIL", f"STATE.md has no gate section for {phase}"))
    else:
        boxes = [l for l in sec if re.match(r"\s*[-*] \[[ xX~]\]", l)]
        open_ = [l.strip() for l in boxes if re.match(r"\s*[-*] \[ \]", l)]
        waived = [l.strip() for l in boxes if re.match(r"\s*[-*] \[~\]", l)]
        bad_waive = [w for w in waived if not re.search(r"WAIVED:.*D-?\d+", w)]
        if not boxes:
            res.append(("FAIL", f"gate {phase}: no checklist items"))
        for l in open_:
            res.append(("FAIL", f"gate {phase}: unticked: {l}"))
        for w in bad_waive:
            res.append(("FAIL", f"gate {phase}: waiver without DECISIONS reference: {w}"))
        if boxes and not open_ and not bad_waive:
            res.append(("PASS", f"gate {phase}: {len(boxes)} items ticked ({len(waived)} waived)"))
    if k >= 6:
        claims = read(os.path.join(project, "CLAIMS.md"))
        if claims is None:
            res.append(("FAIL", "CLAIMS.md missing"))
        else:
            rows = md_table(claims, "status")
            if not rows:
                res.append(("FAIL", "CLAIMS.md: no claims table found"))
            for r in rows:
                cid, st = col(r, "id"), col(r, "status").lower()
                if st == "open":
                    res.append(("FAIL", f"claim {cid} still open (falsifier has not ruled)"))
                elif st in ("survived", "weakened"):
                    if not col(r, "evidence ref"):
                        res.append(("FAIL", f"claim {cid} {st} but has no EVIDENCE refs"))
                    if not col(r, "falsifier"):
                        res.append(("FAIL", f"claim {cid} {st} but falsifier-evidence cell is empty"))
                elif st not in ("refuted",):
                    res.append(("WARN", f"claim {cid}: unknown status '{st}'"))
            if rows and not any(s == "FAIL" and "claim" in m for s, m in res):
                res.append(("PASS", f"CLAIMS.md: {len(rows)} claims ruled on"))
    if k >= 7 and paper:
        ev = read(os.path.join(project, "EVIDENCE.md")) or ""
        printed = {col(r, "number") for r in md_table(ev, "number")}
        printed = {p.replace(" ", "") for p in printed if p}
        missing = []
        for root, _, files in os.walk(os.path.join(project, paper)):
            for f in files:
                if not f.endswith(".tex"):
                    continue
                for ln, line in enumerate(read(os.path.join(root, f)).splitlines(), 1):
                    code = re.split(r"(?<!\\)%", line)[0] if "% no-evidence:" not in line else ""
                    for m in NUM_PAT.finditer(code):
                        tok = m.group(1).replace(" ", "")
                        if not any(tok in p or p in tok for p in printed):
                            missing.append(f"{f}:{ln}: {m.group(1)}")
        for mm in missing:
            res.append(("FAIL", f"number without EVIDENCE row: {mm}"))
        if not missing:
            res.append(("PASS", "every number in the paper has an EVIDENCE row"))
    if k >= 8:
        bib = os.path.join(project, "refs.bib")
        rep = os.path.join(project, "bib-verify-report.md")
        if not os.path.exists(bib):
            res.append(("FAIL", "refs.bib missing"))
        elif not os.path.exists(rep):
            res.append(("FAIL", "bib-verify-report.md missing (run verify_bib.py refs.bib > bib-verify-report.md)"))
        else:
            fresh, how = report_fresh(bib, rep)
            txt = read(rep)
            if not fresh:
                res.append(("FAIL", f"bib-verify report is stale for refs.bib ({how}); re-run verify_bib.py"))
            elif how != "sha256":
                res.append(("WARN", f"bib-verify report has no bib-sha256 line; freshness judged by {how}. "
                                    "Re-run verify_bib.py to stamp it."))
            if not fresh:
                pass
            elif re.search(r"\| (MISMATCH|NOT_FOUND|WEAK|UNCHECKED) \|", txt):
                res.append(("FAIL", "bib-verify report still lists non-VERIFIED entries"))
            else:
                res.append(("PASS", "bib-verify report clean"))
    return res


def selftest() -> int:
    with tempfile.TemporaryDirectory() as d:
        w = lambda n, t: open(os.path.join(d, n), "w").write(t)
        w("STATE.md", "# STATE\nphase: P7\n## Gate P7 (writing)\n- [x] outline approved\n"
                      "- [~] figure 3 WAIVED: no data yet (DECISIONS D-4)\n## Active tasks\n- [ ] x\n")
        w("CLAIMS.md", "| ID | claim (falsifiable) | proposer | status | falsifier evidence | EVIDENCE refs |\n"
                       "|---|---|---|---|---|---|\n| C1 | toy is 2x faster | idea-miner | survived | reran, holds | E1 |\n"
                       "| C2 | toy is optimal | theorist | refuted | counterexample n=6 | |\n")
        w("EVIDENCE.md", "| ID | number/fact as printed in paper | command | log path | commit | machine | date | runs/median |\n"
                         "|---|---|---|---|---|---|---|---|\n| E1 | 2.0x | make bench | logs/a | abc | m1 | 2099-01-01 | 5 |\n")
        os.makedirs(os.path.join(d, "paper"))
        w("paper/main.tex", "We are 2.0x faster.\nAlso 17\\% smaller. % no-evidence: quoted from [X]\n")
        r = check(d, "P7", "paper")
        assert all(s != "FAIL" for s, _ in r), r
        w("paper/main.tex", "We are 2.0x faster and 3.5x smaller, 12\\% less memory. % 99x in a comment is ignored\n")
        r = check(d, "P7", "paper")
        assert any("3.5x" in m for s, m in r if s == "FAIL"), r
        assert any("12" in m for s, m in r if s == "FAIL") and not any("99x" in m for _, m in r), r
        w("CLAIMS.md", "| ID | claim | proposer | status | falsifier evidence | EVIDENCE refs |\n|---|---|---|---|---|---|\n"
                       "| C1 | x | y | open | | |\n")
        assert any("still open" in m for s, m in check(d, "P6", None))
        # P8 bib freshness: content hash, not mtime
        w("STATE.md", "# STATE\n## Gate P8\n- [x] done\n")
        w("CLAIMS.md", "| ID | claim | proposer | status | falsifier evidence | EVIDENCE refs |\n"
                       "|---|---|---|---|---|---|\n| C1 | x | y | survived | ok | E1 |\n")
        w("refs.bib", "@misc{a, title={A}}\n")
        sha = hashlib.sha256(b"@misc{a, title={A}}\n").hexdigest()
        w("bib-verify-report.md", f"# bib-verify report\n\nbib-sha256: {sha}\n\n| status | key |\n|---|---|\n| VERIFIED | `a` |\n")
        os.utime(os.path.join(d, "bib-verify-report.md"), (0, 0))   # mtime older than refs.bib: must not matter
        assert any(s == "PASS" and "bib-verify" in m for s, m in check(d, "P8", None)), check(d, "P8", None)
        w("refs.bib", "@misc{a, title={A}}\n@misc{b, title={B}}\n")   # bib changed after verification
        assert any(s == "FAIL" and "stale" in m for s, m in check(d, "P8", None))
    print("selftest: OK")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--phase", choices=PHASES)
    ap.add_argument("--paper", help="paper directory relative to project (enables number check at P7+)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.phase:
        ap.error("--phase is required")
    res = check(a.project, a.phase, a.paper)
    for s, m in res:
        print(f"{s:4s}  {m}")
    fails = sum(s == "FAIL" for s, _ in res)
    print(f"\nGate {a.phase}: {'PASS' if not fails else f'FAIL ({fails} blocking items)'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
