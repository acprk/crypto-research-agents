"""``crbench`` command-line interface.

Sub-commands
------------
run         interleaved A/B/... benchmark:   crbench run -a base='./old' -a new='./new' -n 5 --log-dir results/x
stats       summarise a sample or a run.json: crbench stats results/x/run.json --baseline base
env         print environment snapshot:       crbench env --target ./build
parse       parse a log with a parser:        crbench parse log.txt --parser criterion
parsers     list registered parsers
table       run.json -> Markdown/LaTeX table: crbench table results/x/run.json --baseline base --latex
evidence    ledger ops:  crbench evidence add EVIDENCE.md --printed '1.23 s' --command '...' --log results/x/run.json
                         crbench evidence check EVIDENCE.md --root .
audit-tex   crbench audit-tex paper.tex EVIDENCE.md   (exit 1 if any number is untraced)
adapters    crbench adapters [NAME]                 (recipes: parser + typical command)
stale       crbench stale ./build/bench src/          (exit 1 if sources are newer than the binary)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, evidence, parsers, stats, tables
from .envcapture import capture_env, git_info, warn_env
from .runner import load_run, run_interleaved, stale_build_check


def _cmd_run(a) -> int:
    arms = {}
    for spec in a.arm:
        if "=" not in spec:
            print(f"--arm expects NAME=COMMAND, got {spec!r}", file=sys.stderr)
            return 2
        k, v = spec.split("=", 1)
        arms[k.strip()] = v
    if len(arms) < 1:
        print("need at least one --arm", file=sys.stderr)
        return 2
    res = run_interleaved(arms, repeats=a.repeats, warmup=a.warmup, order=a.order, parser=a.parser, metric=a.metric,
                          label=a.label, reduce=a.reduce, log_dir=a.log_dir, timeout=a.timeout, threads=a.threads,
                          cpus=a.cpus, use_lock=not a.no_lock, lock_path=a.lock, target_dir=a.target, seed=a.seed,
                          verbose=not a.quiet)
    for w in res.warnings:
        print("WARNING:", w, file=sys.stderr)
    out = {"summary": res.summary()}
    base = a.baseline or next(iter(arms))
    if len(arms) > 1:
        out["speedup_vs_" + base] = res.speedups(base)
    print(json.dumps(out, indent=2))
    if a.min_repeats and any(len(res.samples(k)) < a.min_repeats for k in arms):
        print(f"ERROR: fewer than {a.min_repeats} successful repeats for some arm", file=sys.stderr)
        return 1
    return 0 if not res.failures() else 3


def _cmd_stats(a) -> int:
    if a.input.endswith(".json"):
        r = load_run(a.input)
        out = {"summary": r.summary()}
        base = a.baseline or next(iter(r.arms))
        if len(r.arms) > 1:
            out["speedup_vs_" + base] = r.speedups(base)
    else:
        with open(a.input) if a.input != "-" else sys.stdin as f:
            xs = [float(t) for t in f.read().split()]
        out = stats.summarize(xs).to_dict()
    print(json.dumps(out, indent=2))
    return 0


def _cmd_env(a) -> int:
    e = capture_env(a.target)
    print(json.dumps(e, indent=2))
    for w in warn_env(e):
        print("WARNING:", w, file=sys.stderr)
    return 0


def _cmd_parse(a) -> int:
    recs = parsers.parse_file(a.log, a.parser)
    if a.metric:
        recs = [r for r in recs if r.metric == a.metric]
    print(json.dumps([r.to_dict() for r in recs], indent=2, ensure_ascii=False))
    return 0 if recs else 1


def _cmd_parsers(_a) -> int:
    for name, p in sorted(parsers.REGISTRY.items()):
        print(f"{name:20s} {p.description}")
    return 0


def _cmd_table(a) -> int:
    r = load_run(a.run)
    base = a.baseline or next(iter(r.arms))
    ev = dict(kv.split("=", 1) for kv in (a.evidence or []))
    rows, cols = tables.from_run_summary(r.summary(), r.speedups(base) if len(r.arms) > 1 else {}, ev)
    if a.latex:
        print(tables.to_latex(rows, cols, a.caption, a.label, visible=a.visible))
    else:
        print(tables.to_markdown(rows, cols, a.caption))
    return 0


def _auto_commit(target: str | None) -> str:
    gi = git_info(target or os.getcwd())
    c = gi.get("git_commit")
    return (c[:12] + ("+dirty" if gi.get("git_dirty") else "")) if c else ""


def _cmd_evidence(a) -> int:
    if a.ev_cmd == "add":
        commit = _auto_commit(a.target) if a.commit == "auto" else a.commit
        machine = ("host:" + capture_env()["host_id"]) if a.machine == "auto" else a.machine
        rid = evidence.append_row(a.ledger, a.printed, a.command, a.log, commit, machine, a.date, a.runs, a.id)
        print(rid)
        return 0
    rows = evidence.read_ledger(a.ledger)
    issues = evidence.validate_ledger(rows, a.root)
    for i in issues:
        print(i)
    errs = sum(i.severity == "error" for i in issues)
    print(f"{len(rows)} rows, {errs} errors, {len(issues) - errs} warnings", file=sys.stderr)
    return 1 if errs else 0


def _cmd_audit(a) -> int:
    rows = evidence.read_ledger(a.ledger)
    if not rows:
        print(f"no evidence rows parsed from {a.ledger}", file=sys.stderr)
    issues = evidence.validate_ledger(rows, a.root) if a.check_ledger else []
    issues += evidence.audit_tex(a.tex, rows, strict=a.strict, body_only=not a.whole_file)
    for i in issues:
        print(i)
    errs = sum(i.severity == "error" for i in issues)
    print(f"audit-tex: {errs} errors, {len(issues) - errs} warnings ({len(rows)} ledger rows)", file=sys.stderr)
    return 1 if errs else 0


def _cmd_adapters(a) -> int:
    from .adapters import ADAPTERS, describe

    for n in ([a.name] if a.name else sorted(ADAPTERS)):
        print(describe(n))
    return 0


def _cmd_stale(a) -> int:
    newer = stale_build_check(a.binary, a.sources)
    for p in newer:
        print("newer than binary:", p)
    return 1 if newer else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="crbench", description="Crypto research benchmark harness")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="interleaved A/B benchmark")
    r.add_argument("-a", "--arm", action="append", default=[], help="NAME=COMMAND (repeatable)")
    r.add_argument("-n", "--repeats", type=int, default=5)
    r.add_argument("-w", "--warmup", type=int, default=1)
    r.add_argument("--min-repeats", type=int, default=3, help="fail if fewer successful repeats (default 3)")
    r.add_argument("--order", default="alternate", choices=["alternate", "shuffle", "fixed"])
    r.add_argument("--parser", default=None, help="parse metric from output instead of wall time")
    r.add_argument("--metric", default="time")
    r.add_argument("--label", default=None)
    r.add_argument("--reduce", default="first", choices=["first", "last", "sum", "median"])
    r.add_argument("--log-dir", default=None)
    r.add_argument("--timeout", type=float, default=None)
    r.add_argument("--threads", type=int, default=None, help="sets OMP/MKL/RAYON/GOMAXPROCS thread vars")
    r.add_argument("--cpus", default=None, help="taskset CPU list, e.g. 2-3")
    r.add_argument("--baseline", default=None)
    r.add_argument("--target", default=None, help="directory whose git commit is recorded")
    r.add_argument("--lock", default=None)
    r.add_argument("--no-lock", action="store_true")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("-q", "--quiet", action="store_true")
    r.set_defaults(fn=_cmd_run)

    s = sub.add_parser("stats", help="summarise samples (file of numbers, '-' for stdin, or run.json)")
    s.add_argument("input")
    s.add_argument("--baseline", default=None)
    s.set_defaults(fn=_cmd_stats)

    e = sub.add_parser("env", help="environment snapshot")
    e.add_argument("--target", default=None)
    e.set_defaults(fn=_cmd_env)

    pa = sub.add_parser("parse", help="parse a log file")
    pa.add_argument("log")
    pa.add_argument("--parser", default="auto")
    pa.add_argument("--metric", default=None)
    pa.set_defaults(fn=_cmd_parse)

    sub.add_parser("parsers", help="list parsers").set_defaults(fn=_cmd_parsers)

    t = sub.add_parser("table", help="run.json -> table")
    t.add_argument("run")
    t.add_argument("--baseline", default=None)
    t.add_argument("--latex", action="store_true")
    t.add_argument("--visible", action="store_true", help="show evidence IDs as superscripts")
    t.add_argument("--caption", default=None)
    t.add_argument("--label", default=None)
    t.add_argument("--evidence", nargs="*", help="ARM=ID or ARM:speedup=ID")
    t.set_defaults(fn=_cmd_table)

    ev = sub.add_parser("evidence", help="EVIDENCE.md ledger")
    evs = ev.add_subparsers(dest="ev_cmd", required=True)
    add = evs.add_parser("add")
    add.add_argument("ledger")
    add.add_argument("--printed", required=True)
    add.add_argument("--command", required=True)
    add.add_argument("--log", required=True)
    add.add_argument("--commit", default="auto")
    add.add_argument("--machine", default="auto")
    add.add_argument("--date", default=None)
    add.add_argument("--runs", default="")
    add.add_argument("--id", default=None)
    add.add_argument("--target", default=None)
    chk = evs.add_parser("check")
    chk.add_argument("ledger")
    chk.add_argument("--root", default=None, help="resolve log paths relative to this dir and require they exist")
    ev.set_defaults(fn=_cmd_evidence)

    au = sub.add_parser("audit-tex", help="every paper number must be in EVIDENCE.md")
    au.add_argument("tex")
    au.add_argument("ledger")
    au.add_argument("--strict", action="store_true", help="audit every number, including bare integers")
    au.add_argument("--whole-file", action="store_true", help="also audit the preamble")
    au.add_argument("--check-ledger", action="store_true", help="also validate ledger rows")
    au.add_argument("--root", default=None)
    au.set_defaults(fn=_cmd_audit)

    ad = sub.add_parser("adapters", help="benchmark recipes per baseline library")
    ad.add_argument("name", nargs="?")
    ad.set_defaults(fn=_cmd_adapters)

    st = sub.add_parser("stale", help="detect stale builds")
    st.add_argument("binary")
    st.add_argument("sources", nargs="+")
    st.set_defaults(fn=_cmd_stale)
    return p


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
