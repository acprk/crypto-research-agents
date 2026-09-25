# SPEC — build contract for crypto-research-agents

Every contributor (human or agent) building this repo follows this file.
It is the single source of truth for names, formats and hand-off contracts.

## 0. Hard rules (non-negotiable)

1. **No private research content.** Do NOT copy any unpublished paper title, venue
   submission number, author name, reviewer text, real benchmark number, server address,
   e-mail, review-system transcript, or unpublished theorem from the maintainers' private
   workspaces. Distil *methods* only. Examples must use **toy / synthetic** problems.
   Before every push run `scripts/privacy_scan.sh`, which greps the tree against a local,
   **git-ignored** deny-list `.privacy-denylist` (one regex per line; each maintainer keeps
   their own). Referring to a *public* published paper by its public ePrint number is fine.
2. **No copyrighted PDFs, no harvested figure images** in git. Textbooks appear as
   bibliographic entry + table of contents + topic tags only.
3. **No third-party source trees** in git. Baselines = MANIFEST entry (url, pinned
   commit/tag, build recipe) + fetch script.
4. Every piece of code ships with a test or a runnable `__main__` self-check.
   Python ≥3.10, deps: numpy, sympy, matplotlib, pymupdf (optional), sage (optional,
   guarded import). Toy implementations are marked `# TOY: not secure` at top.
5. Bilingual: English for agent/skill/code/README; Chinese mirror docs in `docs/zh/`.

## 1. Repository layout

```
.claude-plugin/plugin.json   Claude Code plugin manifest
agents/<name>.md             12 subagent definitions (Claude Code format)
skills/<name>/SKILL.md       reusable skills (+ optional scripts/, references/)
commands/<name>.md           slash commands that kick off workflows
workflows/                   phase playbooks + Workflow-tool scripts (*.js)
lib/cryptomath/              Python algorithm library (package `cryptomath`)
lib/bench/                   benchmarking harness (package `crbench`)
lib/lean-template/           Lean4+Mathlib project template
figures/                     mplstyle, template scripts, harvester, gallery index
templates/                   blackboard, paper skeletons, MANIFEST/HANDOFF/rebuttal
references/                  textbook catalog (TOCs), reading lists, baseline MANIFEST
case-study/                  toy end-to-end example run through all phases
docs/                        BIGMAP, quickstart, methodology; docs/zh/ Chinese mirror
AGENTS.md                    Codex / generic-agent entry point (mirrors CLAUDE.md)
CLAUDE.md                    Claude Code entry point
install.sh                   installs agents/skills/commands into a target project
```

## 2. The 12 agents (file = `agents/<id>.md`)

| id | role | owns blackboard file(s) |
|---|---|---|
| `pi-orchestrator` | phase gates, task dispatch, conflict arbitration | `STATE.md`, `DECISIONS.md` |
| `lit-scout` | search, related-work matrix, reading notes, **bib verification** | `LITERATURE.md`, `refs.bib` |
| `math-librarian` | textbook TOC index → "which book/chapter proves X" | `MATH-REFS.md` |
| `idea-miner` | 8-step idea mining loop | `IDEAS.md` |
| `theorist` | proofs, Sage/Mathematica checks, Lean4 formalisation, parameter/security estimation | `THEORY.md`, `lean/` |
| `baseline-engineer` | fetch/pin/build baselines, recipes | `baselines/MANIFEST.md` |
| `experimenter` | bench protocol, logs → tables, evidence ledger | `EVIDENCE.md`, `results/` |
| `falsifier` | red team: tries to refute every claim; veto power | `CLAIMS.md` (verdict column) |
| `writer` | section-by-section writing via playbook | `paper/` |
| `figure-artist` | figures in house style, harvest good figure patterns | `paper/figs/` |
| `reviewer-sim` | venue-calibrated mock review | `REVIEWS.md` |
| `submission-rebuttal` | checklist, anonymisation, artifact, rebuttal, camera-ready | `SUBMISSION.md` |

Agent file format (Claude Code subagent):

```markdown
---
name: <id>
description: <when the orchestrator should use it; 1-3 sentences, starts with a verb>
tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch   # least privilege
model: inherit
---
# <Title>
## Mission
## Inputs (blackboard files read)
## Outputs (blackboard files written, exact format)
## Procedure (numbered)
## Skills used (links to skills/<name>)
## Library used (lib modules)
## Hand-off contract (what "done" means; which agent is next)
## Failure modes & lessons (distilled, generic)
```

## 3. Blackboard (shared state in the *user's research project*, templates in `templates/blackboard/`)

- `STATE.md` — current phase (P0..P8), gate checklist, active tasks, owner.
- `CLAIMS.md` — table: `ID | claim (falsifiable) | proposer | status {open,survived,refuted,weakened} | falsifier evidence | EVIDENCE refs`.
- `EVIDENCE.md` — table: `ID | number/fact as printed in paper | command | log path | commit | machine | date | runs/median`.
  Rule: **no number enters the paper without an EVIDENCE row.**
- `DECISIONS.md` — dated go/no-go decisions with rationale.
- `IDEAS.md`, `LITERATURE.md`, `MATH-REFS.md`, `THEORY.md`, `REVIEWS.md`, `SUBMISSION.md`.

## 4. Phases (workflow)

P0 Scoping → P1 Literature → P2 Ideation → P3 Theory → P4 Baselines → P5 Experiments
→ P6 Falsification gate → P7 Writing+Figures → P8 Review→Submit→Rebuttal→Camera-ready.
Loops: P6 can send back to P2/P3/P5. P8 review can send back to P7/P5.

## 5. Library scope (`lib/cryptomath`)

Subpackages (each with `__init__.py`, docstrings, tests in `lib/cryptomath/tests/`):
- `algebra/` finite fields, poly rings mod (q, Φ_m), cyclotomics, Galois group of Q(ζ_m),
  CRT/slots, NTT (radix-2 & generic), p-adic / Z_{p^e} helpers, null polynomials,
  lifting/digit-extraction polynomials, characters of (Z/m)^*.
- `lattice/` LWE/RLWE/NTRU samplers, error distributions, security estimation
  (wrapper around lattice-estimator if installed + built-in core-SVP / BKZ root-Hermite
  model), BKZ/GSA simulator, LLL (toy).
- `fhe/` toy BGV, BFV, CKKS (encode/decode canonical embedding, rescale, approx),
  TFHE (LWE/GLWE/GGSW, gadget decomposition, blind rotation, PBS, programmable LUT),
  noise estimators for each, bootstrapping building blocks (Paterson–Stockmeyer,
  BSGS polynomial evaluation, Chebyshev approx, homomorphic linear transforms counts).
- `symmetric/` SPN/Feistel toys, S-box analysis (DDT, LAT, BCT, differential
  uniformity, nonlinearity, algebraic degree, APN check), Boolean functions (Walsh,
  ANF), toy AES, Grain/LFSR, trail search via SAT/MILP model export (CNF/LP writer),
  FHE-friendly cipher cost models (multiplicative depth / AND-count).
- `protocols/` secret sharing (Shamir, additive, replicated), OT (toy), OPRF, PSI
  cost models, garbled-circuit cost counter, commitment, Fiat–Shamir helpers.
- `ec/` (small) prime-field EC arithmetic, pairing-free toy group ops, discrete-log
  baby-step giant-step (for toy attack experiments).
- `costmodel/` operation counting framework (count ops symbolically through a
  program; used to compare algorithms before implementing).

## 6. Bench scope (`lib/bench` → package `crbench`)

Generic harness: interleaved A/B runs, median + IQR + bootstrap CI, warm-up,
CPU pinning / thread control, environment capture (CPU, compiler, commit, flags),
lock file to avoid concurrent benches, log parser registry, LaTeX/Markdown table
generator, EVIDENCE ledger writer. Adapters (recipes, not vendored code) for:
OpenFHE, HElib, SEAL, Lattigo, TFHE-rs, tfhe (C++), Concrete, lattice-estimator,
MP-SPDZ, emp-toolkit, APSI/VOLE-PSI, CryptoSMT / SAT solvers (cadical, cryptominisat),
Gurobi/HiGHS MILP, SageMath scripts.

## 7. Figures

`figures/style/crypto.mplstyle` (LNCS column widths, colour-blind-safe palette),
`figures/templates/*.py` each producing a PDF+PNG from synthetic data,
`figures/harvester/` — tool that scans a local PDF corpus, extracts figures
(raster + vector clip by caption), classifies by type, scores, and writes a local
gallery (`figures/gallery/` is **gitignored**; only `gallery_index.template.md` and
a *pattern catalog* describing good figure patterns in words are committed).

## 8. Naming

kebab-case for agents/skills/commands; snake_case for Python modules.
