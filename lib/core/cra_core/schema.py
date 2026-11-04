"""Column semantics of the blackboard tables (SPEC section 3), tolerant to header wording."""
from __future__ import annotations

STATUSES = ("open", "survived", "weakened", "refuted")

def _is(*names):
    return lambda h: h in names

def _has(*subs, unless=()):
    return lambda h: any(s in h for s in subs) and not any(u in h for u in unless)

def _starts(*pre):
    return lambda h: any(h.startswith(p) for p in pre)

CLAIM_HINTS = [
    ("id", _is("id")),
    ("status", _is("status", "verdict")),
    ("falsifier", _has("falsifier", "counterexample")),
    ("refs", _has("ref")),
    ("proposer", _has("proposer", "owner", "author")),
    ("claim", _starts("claim", "statement")),
]
CLAIM_HEADER = ["ID", "claim (precise, falsifiable, with parameter range)", "proposer", "status",
                "falsifier evidence / counterexample", "EVIDENCE / THEORY refs"]

EVIDENCE_HINTS = [
    ("id", _is("id")),
    ("printed", _has("printed", "number", "value", "fact")),
    ("meaning", _has("meaning", "what")),
    ("command", _has("command", "cmd")),
    ("log", _has("log")),
    ("commit", _has("commit")),
    ("machine", _has("machine", "host")),
    ("date", _has("date")),
    ("runs", _has("runs", "median", "repeat", "statistic")),
]
EVIDENCE_HEADER = ["ID", "number/fact as printed in paper", "command", "log path", "commit", "machine",
                   "date", "runs/median"]

TASK_HINTS = [
    ("id", _is("id", "task id")),
    ("owner", _has("owner", "agent")),
    ("task", _is("task", "description")),
    ("inputs", _has("input")),
    ("output", _has("output")),
    ("due", _has("due")),
    ("status", _is("status")),
]

DECISION_HINTS = [
    ("date", _is("date")),
    ("decision", _is("decision")),
    ("options", _has("option")),
    ("evidence", _has("evidence")),
    ("by", _has("decided", "by", "owner")),
    ("revisit", _has("revisit", "reversal")),
]
DECISION_HEADER = ["date", "decision", "options considered", "evidence", "decided by", "revisit when"]
