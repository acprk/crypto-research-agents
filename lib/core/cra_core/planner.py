"""Next-step planning from the blackboard: what should happen now, by whom, with which tool.

The output is deliberately explicit (agent, inputs, output, tool to call, do-not-do list) so
that weaker models and hosts without sub-agents can follow the pipeline step by step, and hosts
with sub-agents can fan the independent tasks out in parallel.
"""
from __future__ import annotations

import re

from .gates import check_gate, gate_section
from .phases import PHASE_INFO


def next_actions(P, limit: int = 6) -> list[dict]:
    acts: list[dict] = []
    ph = P.phase()
    if ph is None:
        return [{"agent": "pi-orchestrator", "task": "STATE.md has no phase line; write 'phase: P0' and the P0 gate",
                 "tool": "file_write or edit STATE.md", "inputs": ["STATE.md"], "output": "STATE.md"}]
    for c in P.claims():
        if c.status == "open":
            acts.append({
                "agent": "falsifier",
                "task": f"Try hard to REFUTE claim {c.id}: {c.claim[:300]}",
                "inputs": ["CLAIMS.md", "EVIDENCE.md", "THEORY.md", f"falsify/{c.id}/"],
                "output": f"verdict via claim_verdict({c.id}, survived|weakened|refuted, evidence=<script/log path>)",
                "tool": "claim_verdict",
                "rules": "write scripts under falsify/<id>/ and keep their logs; report real output, never invent "
                         "numbers; if unsure answer 'weakened' with a wording you CAN defend",
            })
    for s, m in P.check_evidence():
        if s == "FAIL":
            acts.append({"agent": "experimenter", "task": f"fix evidence ledger: {m}", "inputs": ["EVIDENCE.md", "results/"],
                         "output": "EVIDENCE.md consistent", "tool": "evidence_add / re-run the experiment"})
    sec = gate_section(P.read("STATE.md") or "", ph) or []
    owners = PHASE_INFO[ph][1]
    for l in sec:
        if re.match(r"\s*[-*] \[ \]", l):
            item = re.sub(r"^\s*[-*] \[ \]\s*", "", l).strip()
            acts.append({"agent": owners[0], "task": f"{ph} gate item: {item}",
                         "inputs": ["STATE.md"], "output": "the artefact named in the item",
                         "tool": f"then gate_tick({ph!r}, <unique substring of the item>)"})
    if not acts:
        res = check_gate(P.root, ph, "paper" if ph >= "P7" else None)
        fails = [m for s, m in res if s == "FAIL"]
        if fails:
            acts += [{"agent": "pi-orchestrator", "task": f"gate {ph} blocker: {m}", "tool": "gate_check",
                      "inputs": ["STATE.md"], "output": "blocker resolved"} for m in fails]
        elif ph != "P8":
            nxt = f"P{int(ph[1]) + 1}"
            acts.append({"agent": "pi-orchestrator", "task": f"gate {ph} passes: advance to {nxt}",
                         "tool": f"phase_advance({nxt!r}, rationale)", "inputs": ["STATE.md"], "output": "STATE.md, DECISIONS.md"})
        else:
            acts.append({"agent": "submission-rebuttal", "task": "P8 gate passes: prepare the submission checklist "
                         "for HUMAN approval (nothing leaves the machine without it)", "tool": "none (human step)",
                         "inputs": ["SUBMISSION.md"], "output": "SUBMISSION.md"})
    acts = acts[:limit]
    for i, a in enumerate(acts):
        a["id"] = f"T{i + 1}"
        a["do_not"] = [f"{b['agent']}: {b['task'][:80]}" for b in acts if b is not a]
    return acts
