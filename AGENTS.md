# crypto-research-agents — instructions for Codex / generic coding agents

This repo is a **toolkit**, not a research project. Research happens in a separate
project directory initialised with `/cra-init <dir>` (see `docs/QUICKSTART.md`).

When working *in a research project* that uses this system:
1. Read `STATE.md` first. The `pi-orchestrator` agent (agents/pi-orchestrator.md) owns phase changes.
2. Hand work between agents **only through blackboard files** (`templates/blackboard/`).
3. Invariants (never break):
   - A statement enters `paper/` only if its `CLAIMS.md` status is `survived` (or `weakened`, using the weakened wording).
   - A number enters `paper/` only if it has an `EVIDENCE.md` row; run `crbench audit-tex paper/main.tex EVIDENCE.md`.
   - A bib entry stays only if `skills/bib-verify` confirmed it exists.
   - Nothing leaves the machine (submission, e-mail, eprint, public repo) without explicit human approval.
4. Prefer `lib/cryptomath` + `lib/bench` over ad-hoc scripts; put throw-away scripts under `falsify/<claim-id>/` or `results/<exp>/`.
5. Toy implementations in `lib/cryptomath/fhe|lattice|protocols` are **insecure** and only for reasoning / small experiments.

When working *on this repo*: follow `SPEC.md` (names, formats, the no-private-content rule).

## Using the agents without Claude Code subagents
Each file in `agents/` is a self-contained role prompt. In tools without subagents,
"become" an agent by reading its file and following its Procedure; skills in
`skills/<name>/SKILL.md` are plain Markdown procedures with optional scripts.
Slash commands in `commands/` are equivalent to typing their body as a prompt.
