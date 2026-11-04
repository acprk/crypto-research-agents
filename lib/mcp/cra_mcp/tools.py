"""Tool implementations, host-independent.

Every tool is a plain function returning the envelope

    {"ok": bool, "data": ..., "violations": [str], "next_actions": [str]}

Refusals (a write that would break a blackboard invariant) are returned as ok=False with the
reason in ``violations`` rather than raised, because weaker models recover from a readable
refusal much better than from a protocol error.

Design rules (see docs/integrations/COMPATIBILITY.md):
* names are snake_case, <= 32 chars, so ``mcp__cra__<tool>`` fits every host's limit;
* parameters are flat primitives / enums with plain defaults (no Optional=None unions, no
  nested models -> no anyOf/$ref in the schema, which Gemini/OpenAI-strict reject);
* results stay below ~40 000 characters (long texts are paged with ``offset``);
* every tool declares readOnly / destructive / idempotent / openWorld hints.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Literal

from cra_core import CraError, Project
from cra_core.gates import PHASES, check_gate, check_invariants
from cra_core.phases import AGENTS, PHASE_INFO
from cra_core.planner import next_actions
from cra_core.toolkit import init_project, toolkit_root

MAX_CHARS = 40_000
SCRIPT_TIMEOUT = 55  # stay under the 60 s default tool timeout of Codex / Cline

Phase = Literal["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
PhaseOrCurrent = Literal["current", "P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
Status = Literal["survived", "weakened", "refuted", "open"]
StatusFilter = Literal["all", "open", "survived", "weakened", "refuted"]
Agent = Literal["pi-orchestrator", "lit-scout", "math-librarian", "idea-miner", "theorist", "baseline-engineer",
                "experimenter", "falsifier", "writer", "figure-artist", "reviewer-sim", "submission-rebuttal"]
Skill = Literal["abstract-craft", "anonymize-check", "artifact-pack", "baseline-pin", "bench-protocol", "bib-verify",
                "camera-ready", "eprint-search", "experiments-writing", "falsify", "figure-harvest",
                "idea-mining-loop", "lean-bridge", "lit-matrix", "log-to-evidence", "mock-review", "paper-figures",
                "paper-playbook", "param-estimation", "phase-gate", "polish-writing", "reading-notes", "rebuttal",
                "related-work-writing", "sage-check", "technique-overview", "textbook-index", "venue-calibration"]
Board = Literal["STATE.md", "CLAIMS.md", "EVIDENCE.md", "DECISIONS.md", "IDEAS.md", "LITERATURE.md", "MATH-REFS.md",
                "THEORY.md", "REVIEWS.md", "SUBMISSION.md", "refs.bib", "bib-verify-report.md",
                "baselines/MANIFEST.md", "workflows/PHASES.md"]

# files only the typed tools may change (so their invariants cannot be bypassed via file_write)
PROTECTED = {"CLAIMS.md", "EVIDENCE.md", "DECISIONS.md", "bib-verify-report.md"}

RULES = (
    "Rules: read STATE.md first (cra_resume). Falsify first: register claims (claim_register) before "
    "developing them; the falsifier attacks open claims first. Only survived/weakened claims and numbers "
    "with an EVIDENCE row may enter paper/. Never invent numbers: run the experiment and cite the log. "
    "Nothing leaves the machine without explicit human approval."
)


def ok(data=None, next_actions: list[str] | None = None, violations: list[str] | None = None) -> dict:
    return {"ok": not violations, "data": data, "violations": violations or [], "next_actions": next_actions or []}


def refused(msg: str, hint: str = "") -> dict:
    return {"ok": False, "data": None, "violations": [msg], "next_actions": [hint] if hint else []}


def _page(text: str, offset: int = 0) -> dict:
    chunk = text[offset:offset + MAX_CHARS]
    more = offset + MAX_CHARS < len(text)
    return {"text": chunk, "offset": offset, "total_chars": len(text),
            "next_offset": offset + MAX_CHARS if more else -1}


def _results(res: list[tuple[str, str]]) -> tuple[list[dict], list[str]]:
    items = [{"level": s, "message": m} for s, m in res]
    return items, [m for s, m in res if s == "FAIL"]


@dataclass
class ToolSpec:
    name: str
    fn: Callable
    title: str
    read_only: bool
    destructive: bool = False
    idempotent: bool = False
    open_world: bool = False
    profiles: tuple[str, ...] = ("core", "full", "remote")
    meta: dict = field(default_factory=dict)


class Context:
    def __init__(self, project: str, actor: str = "mcp", toolkit: str | None = None):
        self.project = os.path.abspath(project)
        self.actor = actor
        self._toolkit = toolkit

    @property
    def P(self) -> Project:
        return Project(self.project, actor=self.actor)

    @property
    def toolkit(self) -> str:
        if self._toolkit is None:
            self._toolkit = toolkit_root()
        return self._toolkit

    def script(self, rel: str, args: list[str], timeout: int = SCRIPT_TIMEOUT) -> dict:
        path = os.path.join(self.toolkit, rel)
        try:
            # in a frozen app sys.executable is the app itself; it runs bundled scripts via --run-script
            cmd = [sys.executable, "--run-script", path] if getattr(sys, "frozen", False) else [sys.executable, path]
            p = subprocess.run([*cmd, *args], cwd=self.project, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"exit": -1, "stdout": "", "stderr": f"timed out after {timeout}s; run it in a shell instead: "
                                                        f"python3 {path} {' '.join(args)}"}
        return {"exit": p.returncode, "stdout": p.stdout[-MAX_CHARS:], "stderr": p.stderr[-4000:]}


def build_tools(ctx: Context) -> list[ToolSpec]:
    T: list[ToolSpec] = []

    def tool(name, title, read_only, destructive=False, idempotent=False, open_world=False,
             profiles=("core", "full", "remote")):
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", name), name

        def deco(fn):
            T.append(ToolSpec(name, fn, title, read_only, destructive, idempotent or read_only, open_world, profiles))
            return fn
        return deco

    # ------------------------------------------------------------------ orientation
    @tool("cra_resume", "Where are we, what next", read_only=True)
    def cra_resume() -> dict:
        """START HERE in every session (also after context compaction). Returns the current phase, gate
        status, claims by status, evidence-ledger problems, recent events and the next tasks (agent,
        inputs, output, tool to call, do-not-do list), plus the project rules."""
        P = ctx.P
        if P.read("STATE.md") is None:
            return refused(f"no research project at {P.root} (STATE.md missing)",
                           "call project_init to scaffold one, or start cra-mcp with --project <dir>")
        st = P.status()
        st["next_tasks"] = next_actions(P)
        st["rules"] = RULES
        if st["phase"]:
            name, owners, _ = PHASE_INFO[st["phase"]]
            st["phase_name"], st["phase_owners"] = name, owners
        return ok(st, [f"{t['agent']}: {t['task'][:120]} -> {t['tool']}" for t in st["next_tasks"]])

    @tool("role_card", "Load an agent role", read_only=True)
    def role_card(agent: Agent, offset: int = 0) -> dict:
        """Return the full role prompt of one of the 12 research agents (mission, inputs, outputs, procedure,
        hand-off contract). Adopt it before doing that agent's task; hosts without sub-agents do every role
        this way, one at a time."""
        with open(os.path.join(ctx.toolkit, "agents", f"{agent}.md"), encoding="utf-8") as fh:
            return ok(_page(fh.read(), offset))

    @tool("skill_guide", "Load a skill procedure", read_only=True)
    def skill_guide(skill: Skill, offset: int = 0) -> dict:
        """Return a skill's step-by-step procedure (SKILL.md), e.g. falsify, bib-verify, bench-protocol,
        paper-playbook. Scripts it mentions live under skills/<name>/scripts/ of the toolkit."""
        with open(os.path.join(ctx.toolkit, "skills", skill, "SKILL.md"), encoding="utf-8") as fh:
            return ok(_page(fh.read(), offset))

    @tool("blackboard_read", "Read a blackboard file", read_only=True)
    def blackboard_read(file: Board, offset: int = 0) -> dict:
        """Read one blackboard file of the project (or the toolkit's workflows/PHASES.md). Long files are
        paged: call again with offset=next_offset."""
        if file == "workflows/PHASES.md":
            path = os.path.join(ctx.toolkit, file)
            text = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        else:
            text = ctx.P.read(file)
        if text is None:
            return refused(f"{file} does not exist in the project")
        return ok(_page(text, offset))

    # ------------------------------------------------------------------ claims
    @tool("claim_list", "List claims", read_only=True)
    def claim_list(status: StatusFilter = "all") -> dict:
        """List CLAIMS.md rows (id, claim, proposer, status, falsifier evidence, refs), optionally by status."""
        rows = [c for c in ctx.P.claims_as_dicts() if status == "all" or c["status"] == status]
        return ok(rows)

    @tool("claim_register", "Register a falsifiable claim", read_only=False)
    def claim_register(claim: str, proposer: Agent, kill: str, refs: str = "") -> dict:
        """Register a new claim with status 'open' BEFORE anyone develops or writes it. `claim` must be
        precise and falsifiable, with its parameter range; `kill` says what observation would refute it.
        Returns the allocated id (C<n>). The falsifier attacks it next."""
        if len(kill.strip()) < 5:
            return refused("give a kill criterion: the observation that would refute the claim")
        try:
            cid = ctx.P.add_claim(claim, proposer, kill, refs)
        except CraError as e:
            return refused(str(e))
        return ok({"id": cid}, [f"falsifier: attack {cid} (role_card falsifier, skill_guide falsify), "
                                f"then claim_verdict"])

    @tool("claim_verdict", "Record a falsifier verdict", read_only=False)
    def claim_verdict(claim_id: str, status: Status, evidence: str, refs: str = "", weakened_wording: str = "",
                      decision: str = "") -> dict:
        """Record the falsifier's ruling on a claim. survived/weakened need `evidence` (what was tried, with
        script/log paths) and `refs` (EVIDENCE/THEORY ids, e.g. 'E3, THEORY T1'); weakened needs
        `weakened_wording` (the narrower statement that IS defensible); refuted needs the counterexample in
        `evidence`. Reviving a refuted claim needs `decision` = a DECISIONS id."""
        try:
            c = ctx.P.set_verdict(claim_id, status, evidence, refs or None, weakened_wording or None, decision or None)
        except CraError as e:
            return refused(str(e))
        return ok({"id": c.id, "status": c.status, "claim": c.claim})

    # ------------------------------------------------------------------ evidence
    @tool("evidence_list", "List evidence rows", read_only=True)
    def evidence_list() -> dict:
        """List EVIDENCE.md rows (id, value as printed in the paper, command, log path, commit, machine, date,
        runs) and any ledger problems (missing logs, logs edited after recording)."""
        P = ctx.P
        items, fails = _results(P.check_evidence())
        rows = [{k: v for k, v in r.items() if k != "_line"} for r in P.evidence()]
        return ok({"rows": rows, "issues": items}, violations=fails)

    @tool("evidence_add", "Add an evidence row", read_only=False)
    def evidence_add(printed: str, command: str, log: str, meaning: str = "", commit: str = "", machine: str = "",
                     runs: str = "") -> dict:
        """Add a row to EVIDENCE.md for a number that may appear in the paper. `printed` is the value exactly
        as it will be printed (e.g. '3.86x'); `command` reproduces it; `log` is the project-relative path of
        the log/run.json it came from (must exist; its sha256 is recorded). For derived values use
        command='derived: E1/E2' and log='-'. Never add a number you did not actually measure."""
        try:
            eid = ctx.P.add_evidence(printed, command, log, meaning, commit, machine, None, runs)
        except CraError as e:
            return refused(str(e))
        return ok({"id": eid}, [f"cite it in LaTeX as {printed}\\evid{{{eid}}}"])

    # ------------------------------------------------------------------ gates & phases
    @tool("gate_check", "Run a phase gate", read_only=True)
    def gate_check(phase: PhaseOrCurrent = "current", paper: str = "paper") -> dict:
        """Run the mechanical phase gate (checklist ticked; from P6: no open claims, evidence intact; from P7:
        every paper number has an EVIDENCE row and every \\claimref/\\evid resolves; P8: bib-verify fresh and
        clean). phase='current' uses STATE.md."""
        P = ctx.P
        ph = P.phase() if phase == "current" else phase
        if ph is None:
            return refused("STATE.md has no phase line")
        pdir = paper if paper and os.path.isdir(P.path(paper)) else None
        items, fails = _results(check_gate(P.root, ph, pdir))
        return ok({"phase": ph, "passes": not fails, "results": items}, violations=fails)

    @tool("gate_tick", "Tick or waive a gate item", read_only=False, idempotent=True)
    def gate_tick(phase: Phase, item: str, waive_reason: str = "", decision: str = "") -> dict:
        """Tick one checklist item of a phase gate in STATE.md, matched by a unique substring of its text.
        Only tick what is actually done. To waive instead, give `waive_reason` AND `decision` (a DECISIONS
        id from decision_log)."""
        try:
            line = ctx.P.tick_gate_item(phase, item, waive_reason, decision)
        except CraError as e:
            return refused(str(e))
        return ok({"line": line})

    @tool("phase_advance", "Change the research phase", read_only=False, destructive=True)
    def phase_advance(to_phase: Phase, rationale: str) -> dict:
        """pi-orchestrator only. Move the project one phase forward (refused unless the current gate passes)
        or back along a feedback loop (P6->P2/P3/P5, P8->P7/P5; rationale must name the triggering
        CLAIMS/REVIEWS id). Logs a DECISIONS entry and adds the new gate checklist to STATE.md."""
        try:
            r = ctx.P.advance_phase(to_phase, rationale)
        except CraError as e:
            return refused(str(e), "run gate_check and fix the FAIL items first")
        return ok(r, ["call cra_resume for the new phase's tasks"])

    @tool("decision_log", "Log a decision", read_only=False)
    def decision_log(decision: str, options: str = "", evidence: str = "", revisit: str = "") -> dict:
        """Append a dated go/no-go decision to DECISIONS.md (statement + rationale, options considered,
        evidence ids, reversal trigger). Returns its id D-<n>, e.g. for waiving a gate item."""
        try:
            return ok({"id": ctx.P.add_decision(decision, options, evidence, "", revisit)})
        except CraError as e:
            return refused(str(e))

    @tool("invariants_check", "Check blackboard invariants", read_only=True)
    def invariants_check(paper: str = "paper") -> dict:
        """Phase-independent invariants: tables parse, IDs unique, evidence logs unchanged, every \\claimref
        names a survived/weakened claim, every \\evid names a ledger row (and from P7 every number has an
        EVIDENCE row). Run after editing paper/ or the ledgers."""
        items, fails = _results(check_invariants(ctx.P.root, paper))
        return ok(items, violations=fails)

    # ------------------------------------------------------------------ literature
    @tool("bib_verify", "Verify refs.bib", read_only=False, idempotent=True, open_world=True)
    def bib_verify(only: str = "", offline: bool = False) -> dict:
        """Check every refs.bib entry against IACR ePrint / Crossref / DBLP and write bib-verify-report.md
        (stamped with the bib's sha256 for the P8 gate). `only`: comma-separated keys for a quick re-check
        (does not stamp). Entries not VERIFIED must be fixed or removed, never guessed."""
        P = ctx.P
        if P.read("refs.bib") is None:
            return refused("refs.bib missing")
        args = ["refs.bib", "--delay", "0.3"] + (["--only", only] if only else []) + (["--offline"] if offline else [])
        r = ctx.script("skills/bib-verify/scripts/verify_bib.py", args, timeout=SCRIPT_TIMEOUT)
        if r["exit"] in (0, 1) and r["stdout"].startswith("# bib-verify report") and not only and not offline:
            P._write("bib-verify-report.md", r["stdout"])
            P.log_event("bib.verify", "refs.bib", exit=r["exit"])
        bad = re.findall(r"^\| (MISMATCH|NOT_FOUND|WEAK|UNCHECKED) \| `([^`]+)`", r["stdout"], re.M)
        return ok({"report": r["stdout"], "stderr": r["stderr"][-1500:]},
                  violations=[f"{k}: {s}" for s, k in bad] or ([r["stderr"][-300:]] if r["exit"] not in (0, 1) else []))

    @tool("eprint_search", "Search IACR ePrint / DBLP", read_only=True, open_world=True, profiles=("full",))
    def eprint_search(query: str, months: int = 12, dblp: bool = False) -> dict:
        """Novelty / pre-emption search on IACR ePrint (optionally DBLP) for the last `months` months. Record
        what you reviewed in LITERATURE.md's novelty log."""
        args = [query, "--months", str(months), "--json"] + (["--dblp"] if dblp else [])
        r = ctx.script("skills/eprint-search/scripts/eprint_search.py", args)
        try:
            return ok(json.loads(r["stdout"]))
        except json.JSONDecodeError:
            return ok(r, violations=[] if r["exit"] == 0 else [r["stderr"][-300:]])

    @tool("lit_matrix_check", "Lint the related-work matrix", read_only=True, profiles=("full",))
    def lit_matrix_check(max_novelty_age_days: int = 30) -> dict:
        """Lint LITERATURE.md: matrix rows cite bib keys, numbers have sources, novelty log is fresh and not
        'taken'."""
        args = ["LITERATURE.md", "--max-novelty-age", str(max_novelty_age_days)]
        if ctx.P.read("refs.bib") is not None:
            args += ["--bib", "refs.bib"]
        r = ctx.script("skills/lit-matrix/scripts/lit_matrix.py", args)
        return ok(r, violations=[] if r["exit"] == 0 else ["lit-matrix lint failed (see stdout)"])

    # ------------------------------------------------------------------ analysis helpers
    @tool("param_estimate", "Core-SVP screen for LWE", read_only=True, profiles=("full",))
    def param_estimate(n: int, log2q: float, sigma: float, secret_sigma: float = 0.0) -> dict:
        """Quick core-SVP security screen for LWE(n, q=2^log2q, sigma) (primal uSVP, GSA). A screen, not a
        security proof: confirm with the lattice-estimator before quoting any number."""
        args = [str(n), str(log2q), str(sigma)] + (["--secret-sigma", str(secret_sigma)] if secret_sigma else [])
        return ok(ctx.script("skills/param-estimation/scripts/core_svp_screen.py", args))

    @tool("audit_tex", "Audit a .tex file against EVIDENCE", read_only=True, profiles=("full",))
    def audit_tex(tex: str = "paper/main.tex", strict: bool = False) -> dict:
        """crbench audit-tex: every measurement-like number in the .tex body must be in EVIDENCE.md or
        tagged \\evid{E<n>} with a matching value."""
        try:
            from crbench import evidence as ev
        except ImportError:
            return refused("crbench not installed (pip install -e lib/bench)")
        P = ctx.P
        try:
            path = P.path(tex)
        except CraError as e:
            return refused(str(e))
        if not os.path.exists(path):
            return refused(f"{tex} not found")
        issues = ev.audit_tex(path, ev.read_ledger(P.path("EVIDENCE.md")), strict=strict)
        return ok([str(i) for i in issues], violations=[str(i) for i in issues if i.severity == "error"])

    @tool("anon_check", "Anonymity scan", read_only=True, profiles=("full",))
    def anon_check(path: str = "paper", deny: str = "") -> dict:
        """Pre-submission anonymity scan of LaTeX/bib/PDF/artifact files (author names from `deny`,
        comma-separated, plus e-mails, self-citations, personal URLs, local paths, PDF metadata)."""
        try:
            ctx.P.path(path)
        except CraError as e:
            return refused(str(e))
        args = [path, "--json"] + (["--deny", deny] if deny else [])
        r = ctx.script("skills/anonymize-check/scripts/anon_check.py", args)
        try:
            data = json.loads(r["stdout"])
        except json.JSONDecodeError:
            data = r
        return ok(data, violations=[] if r["exit"] == 0 else ["anonymity findings (see data)"])

    # ------------------------------------------------------------------ project & files
    @tool("project_init", "Scaffold a research project", read_only=False, idempotent=True, profiles=("full", "remote"))
    def project_init() -> dict:
        """Create the blackboard files and paper skeleton in the server's project directory (never
        overwrites). Then fill STATE.md: thesis, venue, deadline."""
        made = init_project(ctx.project)
        return ok({"project": ctx.project, "created": made}, ["edit STATE.md (thesis, venue, deadline)", "cra_resume"])

    @tool("file_list", "List project files", read_only=True, profiles=("full", "remote"))
    def file_list(subdir: str = ".", contains: str = "") -> dict:
        """List files under a project subdirectory (relative paths; skips .git and caches). `contains` filters
        by substring of the path."""
        P = ctx.P
        try:
            base = P.path(subdir)
        except CraError as e:
            return refused(str(e))
        out = []
        for d, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x not in (".git", "__pycache__", ".lake", "node_modules")]
            for f in files:
                rel = os.path.relpath(os.path.join(d, f), P.root)
                if contains in rel:
                    out.append(rel)
            if len(out) > 2000:
                break
        return ok(sorted(out)[:2000])

    @tool("file_read", "Read a project file", read_only=True, profiles=("full", "remote"))
    def file_read(path: str, offset: int = 0) -> dict:
        """Read a text file inside the project (paged by `offset`). For hosts without local file access
        (ChatGPT, claude.ai)."""
        try:
            text = ctx.P.read(path)
        except CraError as e:
            return refused(str(e))
        if text is None:
            return refused(f"{path} not found")
        return ok(_page(text, offset))

    @tool("file_write", "Write a project file", read_only=False, destructive=True, profiles=("full", "remote"))
    def file_write(path: str, content: str) -> dict:
        """Create or overwrite a text file inside the project (paper sections, notes, scripts under
        falsify/<id>/ or results/<exp>/). CLAIMS/EVIDENCE/DECISIONS are refused: use the claim_*, evidence_*
        and decision_log tools. After writing under paper/, the invariants are re-checked and reported."""
        P = ctx.P
        norm = os.path.normpath(path)
        if norm in PROTECTED or norm.startswith(".cra") or norm.startswith(".git"):
            return refused(f"{path} is a ledger file: use the typed tools (claim_*, evidence_*, decision_log)")
        try:
            full = P.path(norm)
        except CraError as e:
            return refused(str(e))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with P.lock():
            P._write(norm, content)
        P.log_event("file.write", norm, chars=len(content))
        if norm.startswith("paper" + os.sep) or norm == "paper":
            items, fails = _results(check_invariants(P.root, "paper"))
            return ok({"path": norm}, violations=fails)
        return ok({"path": norm})

    # ------------------------------------------------------------------ ChatGPT deep research / company knowledge
    @tool("search", "Search the project", read_only=True, profiles=("remote",))
    def search(query: str) -> dict:
        """Full-text search over the project's Markdown/LaTeX/BibTeX files. Returns {results: [{id, title,
        url}]} (ChatGPT deep-research compatible); pass an id to fetch."""
        P = ctx.P
        terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 1]
        hits = []
        for d, dirs, files in os.walk(P.root):
            dirs[:] = [x for x in dirs if not x.startswith(".")]
            for f in files:
                if not f.endswith((".md", ".tex", ".bib")):
                    continue
                rel = os.path.relpath(os.path.join(d, f), P.root)
                text = (P.read(rel) or "").lower()
                score = sum(text.count(t) for t in terms)
                if score:
                    hits.append((score, rel))
        hits.sort(reverse=True)
        return {"results": [{"id": rel, "title": rel, "url": f"cra://project/{rel}"} for _, rel in hits[:20]]}

    @tool("fetch", "Fetch a project document", read_only=True, profiles=("remote",))
    def fetch(id: str) -> dict:
        """Return one project document found by search: {id, title, text, url, metadata}."""
        try:
            text = ctx.P.read(id)
        except CraError as e:
            return refused(str(e))
        if text is None:
            return refused(f"{id} not found")
        return {"id": id, "title": id, "text": text[:MAX_CHARS], "url": f"cra://project/{id}",
                "metadata": {"truncated": len(text) > MAX_CHARS}}

    return T


PROFILES = ("core", "full", "remote")


def select(tools: list[ToolSpec], profile: str) -> list[ToolSpec]:
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of {PROFILES}")
    return [t for t in tools if profile in t.profiles]
