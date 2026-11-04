"""cra_core -- the single structured read/write path for a crypto-research-agents blackboard.

Markdown stays the canonical, human-readable storage (no format migration); this package
parses it losslessly, enforces the invariants that used to live only in prompts, allocates
IDs, serialises concurrent writers with a lock file and appends every write to
``.cra/events.jsonl``.

    from cra_core import Project
    p = Project("path/to/my-paper")
    cid = p.add_claim("For all n <= 2^16 ...", proposer="idea-miner", kill="dies if ...")
    p.set_verdict(cid, "refuted", evidence="counterexample n=6, falsify/C7/x.log", actor="falsifier")
"""
from .mdtable import Document, Table
from .project import Claim, Project, CraError
from .gates import check_gate, PHASES

__all__ = ["Document", "Table", "Project", "Claim", "CraError", "check_gate", "PHASES"]
__version__ = "0.2.0"
