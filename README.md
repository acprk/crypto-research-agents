# crypto-research-agents

**A multi-agent research system for cryptography papers** — from literature search to camera-ready —
packaged as Claude Code agents, skills and slash commands (also usable from Codex via `AGENTS.md`),
with a Python algorithm library, a fair-benchmarking harness, a figure kit and a worked toy example.

[中文说明](docs/zh/README.md) · [BIGMAP](docs/BIGMAP.md) · [Quickstart](docs/QUICKSTART.md) · [Case study](case-study/WALKTHROUGH.md)

![BIGMAP](docs/bigmap/bigmap.png)

## Why

Most failed crypto papers do not fail on ideas; they fail on *process*: a claim that was never
attacked, a speedup against the wrong baseline, a number nobody can trace to a log, a reference
that does not exist, a rebuttal that answers the wrong question. This repo encodes a process that
makes those failures structurally hard:

- **Falsify first** — ideas become falsifiable rows in `CLAIMS.md`; a dedicated `falsifier`
  agent (with veto) attacks them before any prose is written.
- **Every number has a log** — `EVIDENCE.md` + `crbench audit-tex` block untraceable numbers.
- **Every reference exists** — `bib-verify` checks bib entries against DBLP/Crossref/ePrint.
- **Agents talk through files** — a shared blackboard makes hand-offs explicit and auditable.

## What is inside

| Directory | Contents |
|---|---|
| `agents/` | 12 subagents: pi-orchestrator, lit-scout, math-librarian, idea-miner, theorist, baseline-engineer, experimenter, falsifier, writer, figure-artist, reviewer-sim, submission-rebuttal |
| `skills/` | ~30 skills: eprint-search, bib-verify, lit-matrix, textbook-index, idea-mining-loop, sage-check, lean-bridge, param-estimation, baseline-pin, bench-protocol, log-to-evidence, falsify, paper-playbook (13 section guides), abstract-craft, technique-overview, venue-calibration, mock-review, rebuttal, anonymize-check, camera-ready, artifact-pack, paper-figures, figure-harvest, … |
| `commands/` | `/cra-init`, `/cra-status`, `/cra-phase`, `/cra-lit`, `/cra-ideas`, `/cra-falsify`, `/cra-bench`, `/cra-write`, `/cra-figure`, `/cra-review`, `/cra-rebuttal`, `/cra-submit` |
| `workflows/` | phase playbook P0–P8 with gates + multi-agent Workflow scripts (lit-sweep, idea-tournament, falsify-round, mock-review-panel) |
| `lib/cryptomath/` | algebra (GF(p^k), cyclotomics, Galois, CRT slots, NTT, Z_{p^e}, digit extraction, characters), lattice (LWE/RLWE/NTRU, estimators, BKZ sim, LLL), FHE toys (BGV, BFV, CKKS, TFHE/PBS, noise models, PS/BSGS, Chebyshev), symmetric (DDT/LAT/BCT, Boolean functions, APN, AES/SPN, SAT/MILP trail models, AO-cipher costs), protocols (SS, OT, OPRF, PSI/GC cost), EC (curves, DLP), costmodel |
| `lib/bench/` | `crbench`: interleaved A/B runs, robust stats, env capture, parsers for OpenFHE/HElib/Lattigo/TFHE-rs/…, LaTeX tables, EVIDENCE ledger, `audit-tex` |
| `lib/lean-template/` | Lean 4 + Mathlib project template with the proposition ↔ Lean-name table pattern |
| `figures/` | house mplstyles (LNCS/ACM/IEEE), 16 matplotlib + 5 TikZ templates, figure harvester + pattern catalog |
| `templates/` | blackboard files, LNCS paper skeleton, rebuttal & hand-off templates |
| `references/` | textbook catalog with tables of contents + topic map, reading lists per area, baseline MANIFEST (29 libraries) + fetch script |
| `case-study/` | a complete toy project (TFHE S-box evaluation) run through all phases, with real toy measurements |

## Install

```bash
git clone <this repo> ~/crypto-research-agents
cd ~/crypto-research-agents
pip install -e lib/cryptomath -e lib/bench          # python ≥ 3.10
./install.sh /path/to/my-paper                        # or: ./install.sh --user  (all projects)
```
Or as a Claude Code plugin: `claude plugin install <path-or-url>`.

Then, inside Claude Code in your project:
```
/cra-init .                       # blackboard + paper skeleton
/cra-phase P1                     # literature
/cra-ideas "<bottleneck>"         # idea mining
/cra-falsify                      # red-team every open claim
/cra-status                       # where are we, what next
```
See [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Scope and honesty
- Toy implementations in `lib/cryptomath` are **not secure**; they exist to reason, count and
  sanity-check on small parameters.
- Venue page limits / rebuttal budgets in `skills/venue-calibration` are orientation only —
  always read the current CFP.
- The system never sends anything off your machine (submissions, e-mails, public repos)
  without your explicit approval.

## License
MIT
