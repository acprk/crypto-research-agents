"""Project: typed, validated, locked access to a research project's blackboard."""
from __future__ import annotations

import contextlib
import datetime as _dt
import getpass
import hashlib
import json
import os
import re
from dataclasses import dataclass, asdict

from .mdtable import Document, Table
from .schema import (CLAIM_HEADER, CLAIM_HINTS, DECISION_HEADER, DECISION_HINTS, EVIDENCE_HEADER, EVIDENCE_HINTS,
                     STATUSES)


class CraError(ValueError):
    """An operation was refused because it would break a blackboard invariant."""


@dataclass
class Claim:
    id: str
    claim: str
    proposer: str
    status: str
    falsifier: str
    refs: str
    line: int = 0


def _today() -> str:
    return _dt.date.today().isoformat()


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


@contextlib.contextmanager
def _file_lock(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fh = open(path, "a+")
    try:
        try:
            import fcntl
            fcntl.flock(fh, fcntl.LOCK_EX)
        except ImportError:  # Windows
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
        yield
    finally:
        try:
            try:
                import fcntl
                fcntl.flock(fh, fcntl.LOCK_UN)
            except ImportError:
                import msvcrt
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            fh.close()


PHASE_RX = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?phase(?:\*\*)?\s*:?\s*(?:\*\*)?\s*:?\s*(P[0-8])\b", re.I | re.M)


class Project:
    """A research project directory (the one created by ``/cra-init`` or ``cra init``)."""

    def __init__(self, root: str = ".", actor: str | None = None):
        self.root = os.path.abspath(root)
        self.actor = actor or os.environ.get("CRA_ACTOR") or "unknown"

    # ------------------------------------------------------------- paths & io
    def path(self, rel: str) -> str:
        """Resolve ``rel`` inside the project; refuse anything that escapes the root."""
        p = os.path.realpath(os.path.join(self.root, rel))
        root = os.path.realpath(self.root)
        if p != root and not p.startswith(root + os.sep):
            raise CraError(f"path escapes the project root: {rel}")
        return p

    def read(self, rel: str) -> str | None:
        try:
            with open(self.path(rel), encoding="utf-8") as fh:
                return fh.read()
        except FileNotFoundError:
            return None

    def _write(self, rel: str, text: str) -> None:
        p = self.path(rel)
        tmp = p + ".cra-tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp, p)

    def lock(self):
        return _file_lock(self.path(".cra/lock"))

    def log_event(self, action: str, target: str = "", **detail) -> None:
        ev = {"ts": _now(), "actor": self.actor, "action": action, "target": target}
        if detail:
            ev["detail"] = detail
        p = self.path(".cra/events.jsonl")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    def events(self, limit: int = 50) -> list[dict]:
        txt = self.read(".cra/events.jsonl") or ""
        out = []
        for line in txt.splitlines()[-limit:]:
            with contextlib.suppress(json.JSONDecodeError):
                out.append(json.loads(line))
        return out

    # ------------------------------------------------------------- tables
    def _table(self, rel: str, hints, required, header, create: bool = False) -> tuple[Document, Table | None]:
        text = self.read(rel)
        if text is None:
            if not create:
                return Document(""), None
            text = f"# {os.path.splitext(os.path.basename(rel))[0]}\n"
        doc = Document(text)
        t = doc.find(hints, required)
        if t is None and create:
            t = doc.add_table(header, hints)
        return doc, t

    @staticmethod
    def _next_id(values: list[str], prefix: str) -> str:
        nums = [int(m.group(1)) for v in values if (m := re.fullmatch(rf"{prefix}(\d+)", v.strip("*` ")))]
        return f"{prefix}{max(nums, default=0) + 1}"

    # ------------------------------------------------------------- claims
    def claims(self) -> list[Claim]:
        doc, t = self._table("CLAIMS.md", CLAIM_HINTS, ("id", "status"), CLAIM_HEADER)
        if t is None:
            return []
        return [Claim(t.value(r, "id").strip("*` "), t.value(r, "claim"), t.value(r, "proposer"),
                      t.value(r, "status").strip("*` ").lower(), t.value(r, "falsifier"), t.value(r, "refs"), r.line)
                for r in t.rows if t.value(r, "id").strip()]

    def claim(self, cid: str) -> Claim:
        for c in self.claims():
            if c.id == cid:
                return c
        raise CraError(f"no claim {cid} in CLAIMS.md")

    def add_claim(self, text: str, proposer: str, kill: str = "", refs: str = "") -> str:
        """Register a new falsifiable claim with status ``open``.  Returns its ID."""
        if len(text.strip()) < 10:
            raise CraError("claim text too short to be falsifiable")
        with self.lock():
            doc, t = self._table("CLAIMS.md", CLAIM_HINTS, ("id", "status"), CLAIM_HEADER, create=True)
            cid = self._next_id([t.value(r, "id") for r in t.rows], "C")
            body = text.strip() + (f" Kill: {kill.strip()}" if kill.strip() else "")
            t.append({"id": cid, "claim": body, "proposer": proposer, "status": "open", "falsifier": "", "refs": refs})
            self._write("CLAIMS.md", doc.render())
            self.log_event("claim.register", cid, proposer=proposer)
        return cid

    def set_verdict(self, cid: str, status: str, evidence: str, refs: str | None = None,
                    weakened_wording: str | None = None, decision: str | None = None) -> Claim:
        """Record the falsifier's ruling.  Enforces the falsify-first rules (agents/pi-orchestrator.md)."""
        status = status.lower().strip()
        if status not in STATUSES:
            raise CraError(f"status must be one of {STATUSES}")
        if status != "open" and not evidence.strip():
            raise CraError(f"a '{status}' verdict needs falsifier evidence (script/log path or counterexample)")
        if status == "weakened" and not (weakened_wording or "").strip():
            raise CraError("a 'weakened' verdict needs the weakened wording that is actually defensible")
        with self.lock():
            doc, t = self._table("CLAIMS.md", CLAIM_HINTS, ("id", "status"), CLAIM_HEADER)
            if t is None:
                raise CraError("CLAIMS.md has no claims table")
            row = next((r for r in t.rows if t.value(r, "id").strip("*` ") == cid), None)
            if row is None:
                raise CraError(f"no claim {cid} in CLAIMS.md")
            old = t.value(row, "status").strip("*` ").lower()
            if old == "refuted" and status != "refuted" and not decision:
                raise CraError(f"{cid} is refuted; reviving it needs a DECISIONS id (decision='D-n')")
            new_refs = refs if refs is not None else t.value(row, "refs")
            if status in ("survived", "weakened") and not new_refs.strip():
                raise CraError(f"a '{status}' claim needs EVIDENCE/THEORY refs (e.g. 'E3, THEORY T1')")
            t.set(row, "status", status)
            prev = t.value(row, "falsifier").strip()
            stamp = f"[{_today()} {self.actor}] {evidence.strip()}"
            t.set(row, "falsifier", f"{prev} {stamp}".strip() if prev else stamp)
            if refs is not None:
                t.set(row, "refs", refs)
            if status == "weakened":
                orig = t.value(row, "claim")
                if "Adopted weakened wording" not in orig:
                    t.set(row, "claim", f"*Original:* {orig} *Adopted weakened wording:* {weakened_wording.strip()}")
            self._write("CLAIMS.md", doc.render())
            self.log_event("claim.verdict", cid, old=old, new=status, decision=decision)
        return self.claim(cid)

    # ------------------------------------------------------------- evidence
    def evidence(self) -> list[dict[str, str]]:
        doc, t = self._table("EVIDENCE.md", EVIDENCE_HINTS, ("id", "printed"), EVIDENCE_HEADER)
        if t is None:
            return []
        rows = [d for d in t.as_dicts() if d["id"].strip()]
        for d in rows:
            d["id"] = d["id"].strip("*` ")
        return rows

    def _hashes(self) -> dict:
        return json.loads(self.read(".cra/evidence-hashes.json") or "{}")

    def add_evidence(self, printed: str, command: str, log: str, meaning: str = "", commit: str = "",
                     machine: str = "", date: str | None = None, runs: str = "") -> str:
        """Append an EVIDENCE row.  Measured rows must point at existing logs; their sha256 is recorded
        in ``.cra/evidence-hashes.json`` so later edits to a log are detected."""
        if not printed.strip() or not command.strip():
            raise CraError("evidence needs the value as printed in the paper and the command that produced it")
        derived = command.lower().startswith("derived")
        logs = [l.strip("` ") for l in re.split(r"[,;]\s*", log or "") if l.strip("` -")]
        if not derived:
            if not logs:
                raise CraError("measured evidence needs a log path (or command 'derived: E1/E2')")
            for lp in logs:
                if not os.path.exists(self.path(lp)):
                    raise CraError(f"log not found under project: {lp}")
        with self.lock():
            doc, t = self._table("EVIDENCE.md", EVIDENCE_HINTS, ("id", "printed"), EVIDENCE_HEADER, create=True)
            ids = [t.value(r, "id").strip("*` ") for r in t.rows]
            if derived:
                for ref in re.findall(r"\b(E\d+)\b", command):
                    if ref not in ids:
                        raise CraError(f"derived evidence references unknown {ref}")
            eid = self._next_id(ids, "E")
            t.append({"id": eid, "printed": printed, "meaning": meaning, "command": command,
                      "log": ", ".join(logs) if logs else "-", "commit": commit, "machine": machine,
                      "date": date or _today(), "runs": runs})
            self._write("EVIDENCE.md", doc.render())
            if logs and not derived:
                h = self._hashes()
                h[eid] = {lp: sha256_file(self.path(lp)) for lp in logs}
                os.makedirs(self.path(".cra"), exist_ok=True)
                self._write(".cra/evidence-hashes.json", json.dumps(h, indent=1, sort_keys=True) + "\n")
            self.log_event("evidence.add", eid, printed=printed)
        return eid

    def check_evidence(self) -> list[tuple[str, str]]:
        """(severity, message) for missing logs, duplicate IDs and logs changed since they were recorded."""
        out, seen = [], set()
        hashes = self._hashes()
        for r in self.evidence():
            if r["id"] in seen:
                out.append(("FAIL", f"duplicate evidence ID {r['id']}"))
            seen.add(r["id"])
            if r["command"].lower().startswith("derived"):
                continue
            for lp in [l.strip("` ") for l in re.split(r"[,;]\s*", r["log"]) if l.strip("` -")]:
                try:
                    p = self.path(lp)
                except CraError as e:
                    out.append(("FAIL", f"{r['id']}: {e}"))
                    continue
                if not os.path.exists(p):
                    out.append(("WARN" if os.path.isabs(lp) else "FAIL", f"{r['id']}: log not found: {lp}"))
                elif lp in hashes.get(r["id"], {}) and hashes[r["id"]][lp] != sha256_file(p):
                    out.append(("FAIL", f"{r['id']}: {lp} changed since the evidence row was recorded"))
        return out

    # ------------------------------------------------------------- state
    def phase(self) -> str | None:
        m = PHASE_RX.search(self.read("STATE.md") or "")
        return m.group(1).upper() if m else None

    def status(self) -> dict:
        """Everything an agent (or human) needs to resume: phase, gate result, open work, recent events."""
        from .gates import check_gate
        ph = self.phase()
        claims = self.claims()
        res = check_gate(self.root, ph, "paper" if os.path.isdir(self.path("paper")) else None) if ph else []
        return {
            "project": self.root,
            "phase": ph,
            "gate": [{"level": s, "message": m} for s, m in res],
            "gate_passes": bool(res) and not any(s == "FAIL" for s, _ in res),
            "claims": {s: [c.id for c in claims if c.status == s] for s in STATUSES},
            "evidence_rows": len(self.evidence()),
            "evidence_issues": [{"level": s, "message": m} for s, m in self.check_evidence()],
            "recent_events": self.events(10),
        }

    # ------------------------------------------------------------- decisions & phases
    def add_decision(self, decision: str, options: str = "", evidence: str = "", by: str = "",
                     revisit: str = "") -> str:
        """Append a dated go/no-go entry to DECISIONS.md.  Returns its id ``D-<n>``."""
        if len(decision.strip()) < 10:
            raise CraError("a decision needs a one-line statement plus rationale")
        with self.lock():
            doc, t = self._table("DECISIONS.md", DECISION_HINTS, ("date", "decision"), DECISION_HEADER, create=True)
            text = self.read("DECISIONS.md") or ""
            nums = [int(n) for n in re.findall(r"\bD-?(\d+)\b", text)]
            did = f"D-{max(nums, default=0) + 1}"
            t.append({"date": _today(), "decision": f"**{did}** {decision.strip()}", "options": options,
                      "evidence": evidence, "by": by or self.actor, "revisit": revisit})
            self._write("DECISIONS.md", doc.render())
            self.log_event("decision.add", did)
        return did

    def tick_gate_item(self, phase: str, item: str, waive_reason: str = "", decision: str = "") -> str:
        """Tick (``[x]``) or waive (``[~] ... WAIVED: reason (DECISIONS D-n)``) one gate item matched by substring."""
        from .gates import gate_section
        state = self.read("STATE.md")
        if state is None:
            raise CraError("STATE.md missing")
        if gate_section(state, phase) is None:
            raise CraError(f"STATE.md has no gate section for {phase}")
        if waive_reason and not re.fullmatch(r"D-?\d+", decision.strip()):
            raise CraError("waiving a gate item needs a DECISIONS id (decision='D-n'); log it with decision_log first")
        lines = state.split("\n")
        start = next(i for i, l in enumerate(lines)
                     if l.lstrip().startswith("#") and "gate" in l.lower() and re.search(rf"\b{phase}\b", l))
        level = len(lines[start]) - len(lines[start].lstrip("#"))
        hits = []
        for i in range(start + 1, len(lines)):
            l = lines[i]
            if l.lstrip().startswith("#") and len(l) - len(l.lstrip("#")) <= level:
                break
            if re.match(r"\s*[-*] \[[ xX~]\]", l) and item.lower() in l.lower():
                hits.append(i)
        if len(hits) != 1:
            raise CraError(f"item text matches {len(hits)} gate items in {phase}; give a longer, unique substring")
        i = hits[0]
        if waive_reason:
            body = re.sub(r"^(\s*[-*]) \[[ xX~]\]\s*", "", lines[i])
            lines[i] = re.match(r"^(\s*[-*])", lines[i]).group(1) + f" [~] {body} WAIVED: {waive_reason.strip()} (DECISIONS {decision.strip()})"
        else:
            lines[i] = re.sub(r"\[[ ~]\]", "[x]", lines[i], count=1)
        with self.lock():
            self._write("STATE.md", "\n".join(lines))
            self.log_event("gate.tick" if not waive_reason else "gate.waive", phase, item=lines[i].strip())
        return lines[i].strip()

    def advance_phase(self, to: str, rationale: str, paper: str | None = None) -> dict:
        """Move the project to phase ``to``.  Forward moves (one step) require the current gate to pass;
        backward moves (feedback loops) need a rationale naming the trigger.  Both are logged in DECISIONS."""
        from .gates import PHASES, check_gate, gate_section
        from .phases import PHASE_INFO, gate_section_text
        cur = self.phase()
        if cur is None:
            raise CraError("STATE.md has no 'phase: P<k>' line")
        if to not in PHASES:
            raise CraError(f"unknown phase {to}")
        ci, ti = PHASES.index(cur), PHASES.index(to)
        if ti == ci:
            raise CraError(f"already in {cur}")
        if len(rationale.strip()) < 10:
            raise CraError("give a rationale (for a backward move: the CLAIMS/REVIEWS id that triggered it)")
        if ti > ci + 1:
            raise CraError(f"cannot skip phases: {cur} -> {to}; advance one phase at a time")
        if ti == ci + 1:
            if paper is None and os.path.isdir(self.path("paper")) and ci >= 7:
                paper = "paper"
            res = check_gate(self.root, cur, paper)
            fails = [m for s, m in res if s == "FAIL"]
            if fails:
                raise CraError(f"gate {cur} does not pass: " + "; ".join(fails[:8]))
        did = self.add_decision(f"{'Advance' if ti > ci else 'Back'} {cur} -> {to}. {rationale.strip()}",
                                evidence=f"cra gate {cur}" if ti > ci else "", by=self.actor)
        with self.lock():
            state = self.read("STATE.md") or ""
            m = PHASE_RX.search(state)
            seg = state[m.start(1):]
            name = PHASE_INFO[cur][0].split()[0]
            new_seg = re.sub(rf"^{cur}(\s+{re.escape(name)}\b)?", f"{to} {PHASE_INFO[to][0]}" if m.group(0).strip().startswith(("-", "*")) else to, seg, count=1)
            state = state[:m.start(1)] + new_seg
            if gate_section(state, to) is None:
                state = state.rstrip("\n") + "\n\n" + gate_section_text(to)
            self._write("STATE.md", state)
            self.log_event("phase.advance", to, frm=cur, decision=did)
        return {"from": cur, "to": to, "decision": did}

    def claims_as_dicts(self) -> list[dict]:
        return [asdict(c) for c in self.claims()]
