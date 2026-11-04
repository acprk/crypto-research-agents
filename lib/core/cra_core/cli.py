"""`cra` -- command-line front end of cra_core (same operations as the cra-mcp server).

    cra init <dir>                              scaffold blackboard + paper skeleton
    cra status [--json]                         phase, gate, open claims, evidence issues
    cra gate P6 [--paper paper]                 mechanical phase gate (exit 1 on FAIL)
    cra claim list [--status open] [--json]
    cra claim add "<falsifiable claim>" --proposer idea-miner [--kill "..."]
    cra claim verdict C3 refuted --evidence "k=64: 43.7x < 57.6, falsify/C3/x.log"
    cra evidence add --printed "3.86x" --command "crbench run ..." --log results/a/run.json
    cra evidence check
    cra check [--paper paper]                   phase-independent invariants (pre-commit)
    cra hook install                            git pre-commit hook running `cra check`
All commands take -p/--project (default: .) and --actor (recorded in .cra/events.jsonl).
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys

from .gates import PHASES, check_gate, check_invariants
from .project import CraError, Project


def _print_results(res, as_json: bool, title: str) -> int:
    fails = sum(s == "FAIL" for s, _ in res)
    if as_json:
        print(json.dumps({"ok": not fails, "results": [{"level": s, "message": m} for s, m in res]}, indent=1))
    else:
        for s, m in res:
            print(f"{s:4s}  {m}")
        print(f"\n{title}: {'PASS' if not fails else f'FAIL ({fails} blocking items)'}")
    return 1 if fails else 0


def _hook_text(project_rel: str) -> str:
    return f"""#!/bin/sh
# installed by `cra hook install` -- blocks commits that break blackboard invariants
# (claim refs to non-survived claims, unknown evidence tags, changed evidence logs, ...).
# Bypass once (not recommended): git commit --no-verify
command -v cra >/dev/null 2>&1 || {{ echo "cra not on PATH; skipping cra check" >&2; exit 0; }}
exec cra -p "{project_rel}" check
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cra", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-p", "--project", default=".")
    ap.add_argument("--actor", default=None, help="who is acting (agent id or human); default $CRA_ACTOR")
    sub = ap.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("init", help="scaffold a research project")
    i.add_argument("dir")

    st = sub.add_parser("status", help="phase, gate, claims, evidence issues")
    st.add_argument("--json", action="store_true")

    g = sub.add_parser("gate", help="mechanical phase gate")
    g.add_argument("phase", choices=PHASES)
    g.add_argument("--paper", default=None)
    g.add_argument("--json", action="store_true")

    c = sub.add_parser("claim", help="CLAIMS.md ledger")
    cs = c.add_subparsers(dest="ccmd", required=True)
    cl = cs.add_parser("list"); cl.add_argument("--status"); cl.add_argument("--json", action="store_true")
    ca = cs.add_parser("add"); ca.add_argument("text"); ca.add_argument("--proposer", required=True)
    ca.add_argument("--kill", default=""); ca.add_argument("--refs", default="")
    cv = cs.add_parser("verdict"); cv.add_argument("id"); cv.add_argument("status", choices=["open", "survived", "weakened", "refuted"])
    cv.add_argument("--evidence", required=True); cv.add_argument("--refs"); cv.add_argument("--wording")
    cv.add_argument("--decision", help="DECISIONS id, required to revive a refuted claim")

    e = sub.add_parser("evidence", help="EVIDENCE.md ledger")
    es = e.add_subparsers(dest="ecmd", required=True)
    ea = es.add_parser("add")
    for k in ("printed", "command", "log"):
        ea.add_argument(f"--{k}", required=(k != "log"), default="")
    for k in ("meaning", "commit", "machine", "date", "runs"):
        ea.add_argument(f"--{k}", default="" if k != "date" else None)
    ec = es.add_parser("check"); ec.add_argument("--json", action="store_true")

    ck = sub.add_parser("check", help="phase-independent invariants (used by the pre-commit hook)")
    ck.add_argument("--paper", default="paper"); ck.add_argument("--json", action="store_true")

    h = sub.add_parser("hook", help="git hooks")
    hs = h.add_subparsers(dest="hcmd", required=True)
    hs.add_parser("install")

    a = ap.parse_args(argv)
    P = Project(a.project, actor=a.actor)
    try:
        if a.cmd == "init":
            from .toolkit import init_project
            made = init_project(a.dir)
            print("created: " + (", ".join(made) if made else "(nothing new)"))
            print(f"next: fill STATE.md (thesis, venue, deadline), then `cra -p {a.dir} gate P0`")
            return 0
        if a.cmd == "status":
            s = P.status()
            if a.json:
                print(json.dumps(s, indent=1, ensure_ascii=False))
            else:
                print(f"project: {s['project']}\nphase:   {s['phase'] or '(not set in STATE.md)'}")
                print("claims:  " + ", ".join(f"{k}={len(v)}" for k, v in s["claims"].items()))
                if s["claims"]["open"]:
                    print("  open (falsifier first): " + ", ".join(s["claims"]["open"]))
                print(f"evidence rows: {s['evidence_rows']}")
                for x in s["evidence_issues"]:
                    print(f"  {x['level']}  {x['message']}")
                print(f"gate {s['phase']}: {'PASS' if s['gate_passes'] else 'not yet'}")
                for x in s["gate"]:
                    if x["level"] != "PASS":
                        print(f"  {x['level']}  {x['message']}")
            return 0
        if a.cmd == "gate":
            return _print_results(check_gate(P.root, a.phase, a.paper), a.json, f"Gate {a.phase}")
        if a.cmd == "claim":
            if a.ccmd == "list":
                rows = [c for c in P.claims_as_dicts() if not a.status or c["status"] == a.status]
                if a.json:
                    print(json.dumps(rows, indent=1, ensure_ascii=False))
                else:
                    for c in rows:
                        print(f"{c['id']:5s} {c['status']:9s} {c['claim'][:100]}")
                return 0
            if a.ccmd == "add":
                print(P.add_claim(a.text, a.proposer, a.kill, a.refs))
                return 0
            c = P.set_verdict(a.id, a.status, a.evidence, a.refs, a.wording, a.decision)
            print(f"{c.id} -> {c.status}")
            return 0
        if a.cmd == "evidence":
            if a.ecmd == "add":
                print(P.add_evidence(a.printed, a.command, a.log, a.meaning, a.commit, a.machine, a.date, a.runs))
                return 0
            return _print_results(P.check_evidence() or [("PASS", "evidence ledger consistent")], a.json, "evidence")
        if a.cmd == "check":
            return _print_results(check_invariants(P.root, a.paper), a.json, "cra check")
        if a.cmd == "hook":
            top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=P.root, capture_output=True, text=True)
            if top.returncode != 0:
                raise CraError("not inside a git repository")
            git_dir = subprocess.run(["git", "rev-parse", "--git-path", "hooks"], cwd=P.root, capture_output=True, text=True).stdout.strip()
            hooks = os.path.join(P.root, git_dir) if not os.path.isabs(git_dir) else git_dir
            os.makedirs(hooks, exist_ok=True)
            hp = os.path.join(hooks, "pre-commit")
            if os.path.exists(hp) and "cra hook install" not in open(hp).read():
                raise CraError(f"{hp} exists and was not written by cra; add `cra check -p <project>` to it by hand")
            rel = os.path.relpath(P.root, top.stdout.strip())
            with open(hp, "w") as fh:
                fh.write(_hook_text(rel))
            os.chmod(hp, os.stat(hp).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            print(f"installed {hp}")
            return 0
    except (CraError, FileNotFoundError) as ex:
        print(f"cra: {ex}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
