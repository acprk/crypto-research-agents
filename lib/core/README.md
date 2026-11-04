# cra_core — the blackboard state layer

`cra_core` is the one structured read/write path for a research project's blackboard
(`STATE.md`, `CLAIMS.md`, `EVIDENCE.md`, …). The `phase-gate` script, the `cra` CLI and the
`cra-mcp` server all use it, so every platform enforces the same rules.

- **Markdown stays canonical.** Tables are parsed and edited losslessly. Untouched rows, prose
  and other tables are preserved byte-for-byte, and headers are matched by meaning rather
  than exact wording.
- **Invariants in code, not prompts:**
  - `survived`/`weakened` need falsifier evidence and EVIDENCE/THEORY refs.
  - `weakened` needs the defensible wording.
  - Reviving a `refuted` claim needs a DECISIONS id.
  - Measured evidence needs an existing log, and its sha256 is recorded so later edits to the
    log are detected.
  - Paths cannot escape the project.
- **IDs, locking, audit:** `C<n>`/`E<n>` are allocated under a file lock (`.cra/lock`), and every
  write is appended to `.cra/events.jsonl`.
- **Paper provenance tags** (see `templates/paper/macros.tex`):
  - `\evid{E3}` (alias `\ev`) must name a ledger row.
  - `\claimref{C4}` must name a `survived`/`weakened` claim.

```bash
pip install -e lib/core            # zero dependencies; Python >= 3.10
cra init ~/papers/my-paper         # same as /cra-init
cra -p ~/papers/my-paper status
cra -p ~/papers/my-paper claim add "For all n <= 2^16 ..." --proposer idea-miner --kill "dies if ..."
cra -p ~/papers/my-paper claim verdict C1 refuted --evidence "n=6 counterexample, falsify/C1/x.log"
cra -p ~/papers/my-paper evidence add --printed "3.86x" --command "crbench run ..." --log results/a/run.json
cra -p ~/papers/my-paper gate P6
cra -p ~/papers/my-paper hook install   # git pre-commit hook: `cra check` on every commit (any IDE/agent)
```

```python
from cra_core import Project
p = Project("~/papers/my-paper", actor="falsifier")
p.set_verdict("C3", "weakened", evidence="k=64 gives 43.7x", refs="E9", weakened_wording="sub-linear in k")
```

Tests: `cd lib/core && python3 -m pytest -q`.
