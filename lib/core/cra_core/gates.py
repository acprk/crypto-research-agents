"""Mechanical part of the phase gates P0..P8 (see workflows/PHASES.md).

Checks (each yields PASS / FAIL / WARN):

  all phases  STATE.md has a gate section for the phase (a heading containing "Gate" and
              "P<k>") whose checkboxes are all ticked ("- [x]"); "- [~] ... WAIVED: <reason>
              (DECISIONS D-<n>)" waives an item.
  >= P6       CLAIMS.md: no claim is `open`; every `survived`/`weakened` claim has EVIDENCE refs
              and a non-empty falsifier-evidence cell.  EVIDENCE logs exist and are unchanged
              since recorded (.cra/evidence-hashes.json).
  >= P7       with a paper dir: every number-with-unit in the .tex sources ("3.2x", "41%",
              "2^{128}", "12.5 ms") appears in the EVIDENCE column "number/fact as printed in
              paper" unless the line carries "% no-evidence: <reason>"; every \\claimref{C<n>}
              names a survived/weakened claim; every \\evid{E<n>} / \\ev{E<n>} names a ledger row.
  >= P8       refs.bib exists; bib-verify-report.md is fresh for it (its "bib-sha256:" line
              equals sha256(refs.bib); legacy reports fall back to git commit time, then mtime)
              and lists only VERIFIED entries.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess

PHASES = [f"P{i}" for i in range(9)]

NUM_PAT = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?\s*(?:\\times|×|x\b|\\%|%|\s?(?:ms|s|us|µs|MB|MiB|KB|KiB|GB|GiB|bits?)\b)"
                     r"|2\^\{?\d+\}?)")
CLAIMREF = re.compile(r"\\claimref\{([^}]*)\}")
EVREF = re.compile(r"\\evid?\{([^}]*)\}")


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
    d, f = os.path.split(os.path.abspath(path))
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--", f], cwd=d, capture_output=True, text=True, timeout=10)
        if dirty.returncode != 0 or dirty.stdout.strip():
            return None
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", f], cwd=d, capture_output=True, text=True, timeout=10)
        return int(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def report_fresh(bib: str, rep: str) -> tuple[bool, str]:
    """Is the bib-verify report up to date for refs.bib?  Returns (fresh, method)."""
    with open(rep, encoding="utf-8") as fh:
        m = re.search(r"^bib-sha256:\s*([0-9a-f]{64})\s*$", fh.read(), re.M)
    if m:
        with open(bib, "rb") as fh:
            return m.group(1) == hashlib.sha256(fh.read()).hexdigest(), "sha256"
    tb, tr = _git_commit_time(bib), _git_commit_time(rep)
    if tb is not None and tr is not None:
        return tr >= tb, "git commit time"
    return os.path.getmtime(rep) >= os.path.getmtime(bib), "file mtime"


def _tex_files(root: str):
    for d, _, files in os.walk(root):
        for f in sorted(files):
            if f.endswith(".tex"):
                yield os.path.join(d, f)


def check_gate(project: str, phase: str, paper: str | None = None) -> list[tuple[str, str]]:
    from .project import Project

    P = Project(project)
    res: list[tuple[str, str]] = []
    if phase not in PHASES:
        return [("FAIL", f"unknown phase {phase!r}; expected one of P0..P8")]
    k = PHASES.index(phase)
    state = P.read("STATE.md")
    if state is None:
        return [("FAIL", "STATE.md missing")]
    sec = gate_section(state, phase)
    if sec is None:
        res.append(("FAIL", f"STATE.md has no gate section for {phase} (add a heading '## Gate {phase}' with '- [ ]' items)"))
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

    claims = P.claims()
    if k >= 6:
        if P.read("CLAIMS.md") is None:
            res.append(("FAIL", "CLAIMS.md missing"))
        elif not claims:
            res.append(("FAIL", "CLAIMS.md: no claims table found"))
        n_fail = 0
        for c in claims:
            if c.status == "open":
                res.append(("FAIL", f"claim {c.id} still open (falsifier has not ruled)")); n_fail += 1
            elif c.status in ("survived", "weakened"):
                if not c.refs.strip():
                    res.append(("FAIL", f"claim {c.id} {c.status} but has no EVIDENCE refs")); n_fail += 1
                if not c.falsifier.strip():
                    res.append(("FAIL", f"claim {c.id} {c.status} but falsifier-evidence cell is empty")); n_fail += 1
            elif c.status != "refuted":
                res.append(("WARN", f"claim {c.id}: unknown status '{c.status}'"))
        if claims and not n_fail:
            res.append(("PASS", f"CLAIMS.md: {len(claims)} claims ruled on"))
        ev_issues = P.check_evidence()
        res += ev_issues
        if not any(s == "FAIL" for s, _ in ev_issues):
            res.append(("PASS", f"EVIDENCE.md: {len(P.evidence())} rows, logs present"))

    if k >= 7 and paper:
        res += paper_checks(P, paper, numbers=True)

    if k >= 8:
        bib, rep = P.path("refs.bib"), P.path("bib-verify-report.md")
        if not os.path.exists(bib):
            res.append(("FAIL", "refs.bib missing"))
        elif not os.path.exists(rep):
            res.append(("FAIL", "bib-verify-report.md missing (run verify_bib.py refs.bib > bib-verify-report.md)"))
        else:
            fresh, how = report_fresh(bib, rep)
            txt = P.read("bib-verify-report.md") or ""
            if not fresh:
                res.append(("FAIL", f"bib-verify report is stale for refs.bib ({how}); re-run verify_bib.py"))
            else:
                if how != "sha256":
                    res.append(("WARN", f"bib-verify report has no bib-sha256 line; freshness judged by {how}. "
                                        "Re-run verify_bib.py to stamp it."))
                if re.search(r"\| (MISMATCH|NOT_FOUND|WEAK|UNCHECKED) \|", txt):
                    res.append(("FAIL", "bib-verify report still lists non-VERIFIED entries"))
                else:
                    res.append(("PASS", "bib-verify report clean"))
    return res


def paper_checks(P, paper: str, numbers: bool = True) -> list[tuple[str, str]]:
    """Provenance checks on the .tex sources under ``paper`` (relative to the project)."""
    res: list[tuple[str, str]] = []
    ev = P.evidence()
    printed = {r["printed"].replace(" ", "") for r in ev if r["printed"]}
    ev_ids = {r["id"] for r in ev}
    by_claim = {c.id: c for c in P.claims()}
    missing, bad_claims, bad_ev = [], [], []
    for f in _tex_files(P.path(paper)):
        rel = os.path.relpath(f, P.root)
        with open(f, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
        for ln, line in enumerate(lines, 1):
            code = re.split(r"(?<!\\)%", line)[0]
            if code.lstrip().startswith(("\\newcommand", "\\renewcommand", "\\providecommand", "\\def")):
                continue
            for m in CLAIMREF.finditer(code):
                for cid in [x.strip() for x in m.group(1).split(",") if x.strip()]:
                    c = by_claim.get(cid)
                    if c is None:
                        bad_claims.append(f"{rel}:{ln}: \\claimref{{{cid}}} not in CLAIMS.md")
                    elif c.status not in ("survived", "weakened"):
                        bad_claims.append(f"{rel}:{ln}: \\claimref{{{cid}}} is '{c.status}' (needs survived/weakened)")
            for m in EVREF.finditer(code):
                for eid in [x.strip() for x in m.group(1).split(",") if x.strip()]:
                    if eid not in ev_ids:
                        bad_ev.append(f"{rel}:{ln}: \\evid{{{eid}}} not in EVIDENCE.md")
            if not numbers or "% no-evidence:" in line:
                continue
            for m in NUM_PAT.finditer(code):
                tok = m.group(1).replace(" ", "")
                if not any(tok in p or p in tok for p in printed):
                    missing.append(f"{rel}:{ln}: {m.group(1)}")
    res += [("FAIL", f"number without EVIDENCE row: {mm}") for mm in missing]
    res += [("FAIL", f"claim reference: {b}") for b in bad_claims]
    res += [("FAIL", f"evidence tag: {b}") for b in bad_ev]
    if numbers and not missing:
        res.append(("PASS", "every number in the paper has an EVIDENCE row"))
    if not bad_claims and not bad_ev:
        res.append(("PASS", "every \\claimref / \\evid tag resolves"))
    return res


def check_invariants(project: str, paper: str | None = "paper") -> list[tuple[str, str]]:
    """Phase-independent invariants -- safe to run on every commit (``cra check``, pre-commit hook).

    Always: CLAIMS/EVIDENCE tables parse, IDs are unique, evidence logs exist and are unchanged,
    every \\claimref names a survived/weakened claim, every \\evid tag resolves.
    From P7 on: also every number in the paper has an EVIDENCE row.
    """
    from .project import Project

    P = Project(project)
    res: list[tuple[str, str]] = []
    for rel, ids in (("CLAIMS.md", [c.id for c in P.claims()]), ("EVIDENCE.md", [r["id"] for r in P.evidence()])):
        text = P.read(rel)
        if text is None:
            continue
        if not ids and "|" in text and re.search(r"^\|\s*(C|E)\d+\s*\|", text, re.M):
            res.append(("FAIL", f"{rel}: rows present but the table header was not recognised"))
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            res.append(("FAIL", f"{rel}: duplicate IDs {', '.join(dup)}"))
    for c in P.claims():
        if c.status not in ("open", "survived", "weakened", "refuted"):
            res.append(("FAIL", f"claim {c.id}: unknown status '{c.status}'"))
    res += P.check_evidence()
    ph = P.phase()
    if paper and os.path.isdir(P.path(paper)):
        late = ph is not None and PHASES.index(ph) >= 7
        res += paper_checks(P, paper, numbers=late)
    if not any(s == "FAIL" for s, _ in res):
        res.append(("PASS", "blackboard invariants hold"))
    return res
