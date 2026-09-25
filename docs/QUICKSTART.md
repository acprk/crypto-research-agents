# Quickstart

## 1. Install
```bash
pip install -e lib/cryptomath -e lib/bench
./install.sh ~/papers/my-new-paper          # copies agents/skills/commands into .claude/
cd ~/papers/my-new-paper && claude
```
Optional tools the agents use when present: SageMath, lattice-estimator, Lean 4 + Mathlib
(lean-lsp MCP), Mathematica MCP, `latexmk`, `pdffonts`, SAT solvers (cadical / cryptominisat), HiGHS/scipy.

## 2. A typical week-by-week run
| Step | You type | What happens |
|---|---|---|
| 1 | `/cra-init .` | blackboard files + `paper/` skeleton; you give thesis, venue, deadline |
| 2 | `/cra-lit "TFHE programmable bootstrapping many LUTs"` | lit-scout builds the matrix, verifies every bib entry, flags pre-emption |
| 3 | `/cra-ideas "PBS dominates the cost of evaluating S-boxes"` | idea-miner runs the 8-step loop, cost-models ideas, registers claims |
| 4 | `/cra-phase P3` | theorist proves / numerically checks, estimates parameters, optionally formalises in Lean |
| 5 | `/cra-phase P4` then `/cra-bench "<A vs B spec>"` | baselines pinned and reproduced; interleaved benchmarks → EVIDENCE |
| 6 | `/cra-falsify` | falsifier attacks every open claim; refuted ones go back to P2/P3 |
| 7 | `/cra-write intro`, `/cra-figure "speedup vs #LUTs"` | only survived claims and logged numbers are used |
| 8 | `/cra-review EUROCRYPT` → fix → `/cra-submit` | mock review, anonymisation, checklist, artifact |
| 9 | `/cra-rebuttal reviews.txt 700` | triage + short submitted version + detailed internal version |

At any time: `/cra-status`.

## 3. Heavy multi-agent rounds (optional)
With Claude Code's Workflow tool:
```
Workflow({scriptPath: ".cra/workflows/falsify-round.js", args: {project: "<abs path>"}})
```
Other scripts: `lit-sweep.js`, `idea-tournament.js`, `mock-review-panel.js`.

## 4. Adapting to your group
- Add venue profiles in `skills/venue-calibration/SKILL.md`.
- Add your own baselines to `references/baselines/MANIFEST.md`.
- Add figure patterns by harvesting your own corpus: `python3 figures/harvester/harvest.py <pdf-dir> --out figures/gallery`.
- New agent: copy any `agents/*.md`, keep the section structure (Mission / Inputs / Outputs / Procedure / Skills / Library / Hand-off / Lessons), and register its blackboard file in `SPEC.md`.
