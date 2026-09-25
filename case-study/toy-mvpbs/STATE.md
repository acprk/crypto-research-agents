# STATE — toy-mvpbs (TEACHING EXAMPLE)

> Owner: `pi-orchestrator`. Every agent reads this first; only the PI changes `phase`.
> **This whole project is a didactic toy.** All parameters are insecure, all timings are
> single-threaded pure-Python numbers on a shared workstation, all dates in DECISIONS.md are
> illustrative. Nothing here is a research result.

- **Phase:** P8 Review → Submit (mock) — **closed** (project finished; no real submission)
- **Target venue / deadline:** *mock* "LNCS short paper" profile / 2026-10-01 (illustrative)
- **One-sentence thesis (as finally adopted, after P6):** For a 4-bit S-box whose output bits
  are needed as separate TFHE ciphertexts, multi-value PBS (one blind rotation of a common
  polynomial v0, then one small integer polynomial product per output bit) is 3.86× faster
  than one PBS per bit at our toy parameters, at the price of multiplying the blind-rotation
  noise variance by ‖d_i‖² ≤ 18, which is harmless at T1 and fatal at the noisy set T2.
- **Last updated:** 2026-09-25 by pi-orchestrator

## Phase history (gate log)

| phase | owner | opened | gate passed | went back? | key artefacts |
|---|---|---|---|---|---|
| P0 Scoping | pi-orchestrator | 2026-09-14 | 2026-09-14 | – | this file, DECISIONS D1 |
| P1 Literature | lit-scout (+ math-librarian) | 2026-09-14 | 2026-09-15 (waiver D2) | – | LITERATURE.md, refs.bib, bib-verify-report.md, MATH-REFS.md |
| P2 Ideation | idea-miner | 2026-09-15 | 2026-09-16 | – | IDEAS.md (I1 promoted, I2 killed, I3 parked), CLAIMS C1–C5 open |
| P3 Theory | theorist | 2026-09-16 | 2026-09-18 | – | THEORY.md, theory/check_mvpbs_noise.py (+ .log) |
| P4 Baselines | baseline-engineer | 2026-09-18 | 2026-09-18 | – | baselines/MANIFEST.md |
| P5 Experiments | experimenter | 2026-09-18 | 2026-09-25 | re-run once (D4: wall → CPU time) | results/, EVIDENCE.md |
| P6 Falsification | falsifier | 2026-09-25 | 2026-09-25 | C3 refuted → C6 replaces it (D5); C5 refuted → vpack out of the narrative | CLAIMS.md verdicts, falsify/ |
| P7 Writing + figures | writer, figure-artist | 2026-09-25 | 2026-09-25 | 1 loop from P8 (D6) | paper/, paper/figs/ |
| P8 Review / submit | reviewer-sim, submission-rebuttal | 2026-09-25 | 2026-09-25 (mock) | R1 items → P7 | REVIEWS.md, SUBMISSION.md |

## Gate P0 (scoping)
- [x] thesis is one falsifiable sentence (initial: "MV-PBS evaluates the S-box k× faster with no loss of correctness")
- [x] venue profile chosen (mock LNCS short paper, 3–5 pages)
- [x] kill date set: drop the project if MV-PBS is not ≥ 2× faster at k = 4 by 2026-09-25

## Gate P1 (literature)
- [x] strongest baseline named: one PBS per output bit with the *same* toy library and parameters (CJP21-style programmable bootstrapping)
- [~] matrix ≥ 15 verified works — WAIVED: teaching toy, 8 verified public works suffice (DECISIONS D-2)
- [x] pre-emption search < 7 days old (2026-09-15; topic is textbook-level and published since 2019 — we claim nothing new)
- [x] `bib-verify` passes (8/8 VERIFIED, see bib-verify-report.md)

## Gate P2 (ideation)
- [x] ≥ 1 idea with cost-model gain and kill criterion (I1: 4 blind rotations → 1)
- [x] top idea registered as claims C1–C5 (status open)

## Gate P3 (theory)
- [x] every lemma numerically checked on small params (L1, L2, T1a in theory/check_mvpbs_noise.log, exit 0)
- [x] main statement proof complete (Theorem T1 — short, by linearity; see THEORY.md)
- [x] parameters stated as INSECURE toy sets T1/T2 (security estimation deliberately skipped, D1)

## Gate P4 (baselines)
- [x] baseline builds at pinned commit (in-tree toy per-bit PBS, same file, same parameters)
- [x] fairness checklist signed (same keys, same encoding, same timer scope, same thread count)

## Gate P5 (experiments)
- [x] interleaved runs, ≥ 3 repeats, medians (5 rounds + 1 warm-up, rotating order)
- [x] env captured (results/*/run.json; host id hashed, paths sanitised)
- [x] every candidate paper number has an EVIDENCE row (E1–E22)

## Gate P6 (falsification)
- [x] no `open` claims (C1 survived, C2 weakened, C3 refuted, C4 survived, C5 refuted, C6 survived)
- [x] refuted claims removed from narrative (C3 linear scaling, C5 vpack speed-up)
- [x] weakened wording adopted (C2 wording is the one in paper/sections/construction.tex)

## Gate P7 (writing + figures)
- [x] playbook sections complete (abstract, intro, prelim, construction, experiments, conclusion)
- [x] `crbench audit-tex` passes on main.tex and every section (paper/audit-tex.log: 0 errors)
- [x] 0 undefined references (paper/build.log)
- [x] figures in house style (figures/style/palette.py, pattern P01 + error bars)

## Gate P8 (review → submit, mock)
- [x] mock-review action items closed (REVIEWS.md R1: 5/5 closed)
- [x] `anon_check` clean (SUBMISSION.md)
- [x] checklist done (SUBMISSION.md) — the "submit" step is intentionally NOT performed

## Active tasks
| task | owner agent | input | expected output | status |
|---|---|---|---|---|
| (none — project closed) | | | | |

## Blockers / questions for the human
- None. Reminder: this is a teaching example; do not cite its numbers.
