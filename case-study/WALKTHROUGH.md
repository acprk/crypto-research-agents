# WALKTHROUGH — toy-mvpbs, phase by phase (TEACHING EXAMPLE)

> **What this is.** A complete, runnable toy research project that shows how the 12 agents of
> this toolkit hand work to each other through the blackboard files. The topic is public and
> textbook-level: evaluating a 4-bit S-box (PRESENT) on toy-TFHE ciphertexts with
> (a) one PBS per output bit, (b) multi-value PBS (Carpov–Izabachène–Mollimard, CT-RSA 2019,
> ePrint 2018/622), (c) a CMux tree / vertical packing (CGGI, ASIACRYPT 2017).
> Parameters are insecure; timings are pure-Python CPU times; dates in DECISIONS.md are
> illustrative. **Nothing here is a research result.**
>
> **How it was produced.** One Claude Code session played every role in turn, each time
> following the corresponding `agents/<id>.md` file and skill. With the plugin installed you
> drive the same flow with the slash commands shown below (or let `pi-orchestrator` dispatch
> the agents with `/cra-phase P<k>`). All numbers in the project were really measured by the
> scripts listed here, on 2026-09-25.

Project directory: `case-study/toy-mvpbs/` (blackboard files at its top level).

## Reproduce everything (≈ 4 min of compute, 1 core)

```bash
cd case-study/toy-mvpbs
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
/usr/bin/python3 code/sbox_fhe.py                        # self-check, 3 strategies, 16 inputs (~6 s)
/usr/bin/python3 code/test_sbox_fhe.py                   # 7 unit tests (~10 s)
/usr/bin/python3 theory/check_mvpbs_noise.py > theory/check_mvpbs_noise.log   # P3 (~7 s)
python3 ../../skills/bib-verify/scripts/verify_bib.py refs.bib > bib-verify-report.md  # P1 (network)
/usr/bin/python3 code/run_experiments.py                 # P5 via crbench (~2.5 min)
for s in falsify/C*/*.py; do /usr/bin/python3 "$s" | tee "${s%.py}.log"; done   # P6 (~1 min)
/usr/bin/python3 code/run_experiments.py --sanitise-only # scrub paths/hostnames in results/
/usr/bin/python3 code/make_figures.py                    # P7 figure from results/ only
(cd paper && make && latexmk -c)                         # P7 PDF (llncs from the TeX tree)
for f in paper/main.tex paper/sections/*.tex; do
  PYTHONPATH=../../lib/bench /usr/bin/python3 -m crbench audit-tex "$f" EVIDENCE.md --check-ledger --root .
done                                                     # P7 gate: every number has a ledger row
for ph in P0 P1 P2 P3 P4 P5 P6 P7 P8; do
  /usr/bin/python3 ../../skills/phase-gate/scripts/gate_check.py --project . --phase $ph --paper paper
done                                                     # mechanical gate checks
```

`/usr/bin/python3` is used because it has numpy; the code puts `lib/cryptomath` and `lib/bench`
on `sys.path` itself (no install needed). The C3 falsifier re-runs its own crbench experiment
(k = 64); pass `--reuse` to only re-parse its logs.

## The phases

### P0 — Scoping · `/cra-init case-study/toy-mvpbs` then `/cra-phase P0`
- **Agent:** `pi-orchestrator`.
- **Read:** the human's one-line topic; `workflows/PHASES.md`.
- **Wrote:** `STATE.md` (thesis v0: *"MV-PBS evaluates the S-box k× faster with no loss of
  correctness"* — deliberately too strong, it is the thing the falsifier will cut down), kill date,
  mock venue; `DECISIONS.md` **D-1**: only the bit-sliced case is interesting — if a single
  nibble ciphertext suffices, one PBS with f = S already does the job.
- **Gate P0:** thesis falsifiable, venue chosen, kill date set → PASS.

### P1 — Literature · `/cra-lit "multi-value bootstrapping TFHE LUT"`
- **Agents:** `lit-scout` (skills `eprint-search`, `lit-matrix`, `bib-verify`), `math-librarian`
  (skill `textbook-index`).
- **Read:** `references/reading-lists/fhe-bootstrapping.md`, ePrint/Crossref;
  `references/textbooks/CATALOG.md`, `TOPIC-MAP.md`.
- **Wrote:** `LITERATURE.md` (8 public works: CGGI16/17/20, DM15, CJP21, CIM19, GBA21,
  PRESENT07; strongest baseline = per-bit PBS in the same library), `refs.bib`,
  `bib-verify-report.md` (**8/8 VERIFIED**; LNCS volume numbers could not be machine-verified and
  were *removed rather than guessed*), `MATH-REFS.md` (Dummit–Foote for the quotient ring and
  cyclotomic facts, Meyer for structured matrices; one gap — no probability textbook in the
  catalog — reported to the PI).
- **Gate P1:** "≥ 15 works" item **waived** with a DECISIONS reference (D-2) — `gate_check.py`
  accepts `- [~] … WAIVED: … (DECISIONS D-2)` and nothing else.

### P2 — Ideation · `/cra-ideas "4 blind rotations for one S-box"`
- **Agent:** `idea-miner` (skill `idea-mining-loop`; optional `workflows/idea-tournament.js`);
  the `falsifier` screens ideas before they become claims.
- **Read:** `LITERATURE.md`, operation counts from `cryptomath.costmodel.Counter`
  (4 × 32 CMux per S-box for per-bit PBS).
- **Wrote:** `IDEAS.md` — **I1** (share the blind rotation = MV-PBS) promoted;
  **I2** (Gray-code re-ordering of the inputs to shrink ‖d_i‖) **killed** at screening: re-encoding
  the input is itself a LUT evaluation, i.e. one more PBS; **I3** (CMux tree) promoted as a claim
  and later refuted. `CLAIMS.md` rows C1–C5 with status `open`, each with a kill criterion.
- **Gate P2:** ≥ 1 idea with a cost-model gain and kill criterion; claims registered → PASS.

### P3 — Theory · `/cra-phase P3` (dispatches `theorist`)
- **Agent:** `theorist` (skills `sage-check`, `param-estimation` — the latter skipped by D-1:
  toy parameters are insecure by design); `math-librarian` answers "where is (1 − X) a unit?".
- **Read:** `IDEAS.md` I1, `MATH-REFS.md`, `lib/cryptomath/cryptomath/fhe/noise.py`.
- **Wrote:** `THEORY.md` — Lemma L1 (T_f = v0·d_f), Lemma L2 (‖d_f‖² ≤ p + 2, tight), Theorem T1
  (output variance ‖d_f‖²·Var_BR + Var_KS); `theory/check_mvpbs_noise.py` in the sage-check
  format (one JSON line per statement, exit 1 on a counterexample) and its log: L1 on 66 564 LUTs,
  L2 exhaustive, T1a Monte-Carlo ratio 0.955–1.029.
- **Finding that changed the plan:** at the default set T1 the key-switch noise (2^-12.13)
  dominates the blind-rotation noise (2^-14.47), so the MV-PBS amplification is invisible and
  claim C2 cannot be attacked there. → **D-3**: add a deliberately noisy set T2 (GLWE σ = 2^-22).
- **Gate P3:** every lemma numerically checked → PASS.

### P4 — Baselines · `/cra-phase P4` (dispatches `baseline-engineer`)
- **Agent:** `baseline-engineer` (skill `baseline-pin`).
- **Read:** `references/baselines/MANIFEST.md` (TFHE-rs, tfhe C++ recipes).
- **Wrote:** `baselines/MANIFEST.md`: the fair baseline is the library's own `pbs` with the same
  keys, encoding, parameters, timer scope and thread count; `vpack` is flagged *not like-for-like*
  (GGSW inputs) before any number exists; production libraries are out of scope (D-1).
- **Gate P4:** fairness checklist signed → PASS.

### P5 — Experiments · `/cra-bench "perbit vs mvpbs vs vpack, k-scan, noise at T1/T2"`
- **Agent:** `experimenter` (skills `bench-protocol`, `log-to-evidence`; library `crbench`).
- **Read:** `baselines/MANIFEST.md`, `THEORY.md` (T2 definition).
- **Ran:** `code/run_experiments.py` → `crbench.runner.run_interleaved` (rotating arm order,
  1 warm-up + 5 rounds, threads = 1, env capture, lock). Each execution writes
  `results/<exp>/<arm>/r<k>.log`; each experiment writes `run.json` and `summary.log`.
- **Loop inside P5 (D-4):** the first run used wall time while the shared machine's load average
  reached 70; per-bit PBS had IQR 257 ms on a 383 ms median and the k = 4 speed-up CI was
  [3.10, 6.25]. The experimenter switched the metric to process CPU time (the code is single-
  threaded; wall time is still logged next to every sample) and re-ran: IQR 0.5 ms, CI [3.79, 3.95].
  The superseded numbers never entered the ledger.
- **Wrote:** `EVIDENCE.md` (E1–E22: value as printed, command, log path, code hash, hashed host,
  date, runs/statistic); `crbench evidence check EVIDENCE.md --root .` → 22 rows, 0 errors.
- **Headline measurements:** per-bit PBS 291.2 ms vs MV-PBS 75.4 ms per S-box → **3.86×
  [3.79, 3.95]**; k-scan 0.96×, 2.00×, 2.95×, 3.96× for k = 1..4; at T2 the MV-PBS S-box failure
  rate is 14/128 (k = 1) … **32/128 (k = 4)** while per-bit PBS has 0/128.
- **Gate P5:** interleaved, ≥ 3 repeats, medians, env captured, every candidate number in the
  ledger → PASS.

### P6 — Falsification gate · `/cra-falsify` (or `workflows/falsify-round.js`)
- **Agent:** `falsifier` (skill `falsify`, attack order definitions → quantifiers → edge parameters
  → numeric recomputation → baseline fairness → literature). Every attack is a script in
  `falsify/<claim>/` with its output next to it (`.log`).
- **Verdicts written to `CLAIMS.md`:**

| claim | verdict | how it was decided |
|---|---|---|
| C1 correctness at T1 | **survived** | 3 key seeds × all inputs + extreme LUTs (max ‖d‖² = 18): 256/256 correct |
| C2 "same correctness as per-bit PBS" | **weakened** | at T2 the MV-PBS failure CI lies above the per-bit CI for every k; adopted wording: same correctness *only if* ‖d_i‖²·Var_BR + Var_KS fits the margin |
| C3 "speed-up ≥ 0.9k for all k ≤ 64" | **refuted** | proposer only measured k ≤ 4; the falsifier ran crbench at the edge of the range: k = 64 gives 43.67× [42.53, 44.63] < 57.6 (Amdahl: per-LUT work does not amortise) |
| C4 "k = 4 speed-up in [3, 4)" | **survived** (with evidence) | recomputed from the raw per-execution logs, same configuration, all outputs correct: 3.86× [3.79, 3.95] |
| C5 "CMux tree ≥ 5× faster than MV-PBS" | **refuted** | raw 7.81× is real but compares GGSW inputs with an LWE input; with bit extraction + the cheapest circuit bootstrap the end-to-end bound is ≥ 376 ms, i.e. ≤ 0.20× |
| C6 saturation (replaces C3) | **survived** | proposed by the falsifier, re-parsed from raw logs |

- **Where work was sent back:** C3's refutation went to the PI, who replaced it by C6 instead of
  shrinking the claimed range to k ≤ 4 (that would hide the effect) — **D-5**. C5's refutation
  removed the vpack number from the narrative. C2's weakened wording became the text of
  Theorem 1's consequence in the paper.
- **Gate P6:** no open claims; refuted claims out of the narrative; weakened wording adopted →
  `gate_check.py --phase P6` PASS.

### P7 — Writing + figures · `/cra-write <section>` and `/cra-figure "speed-up vs k; failure vs k"`
- **Agents:** `writer` (skill `paper-playbook`), `figure-artist` (skill `paper-figures`,
  pattern P01 from `figures/PATTERNS.md`, `figures/style/palette.py`).
- **Read:** `CLAIMS.md` (only C1, C2 weakened, C4, C6), `EVIDENCE.md`, `THEORY.md`, `results/`.
- **Wrote:** `paper/` copied from `templates/paper/` (LNCS, anonymous build), sections filled,
  `\evid{E…}` tags after numbers; `paper/figs/fig_speedup_failure.pdf` generated by
  `code/make_figures.py` directly from the logs (no hand-typed numbers); `paper/main.pdf` (5 pages).
- **Checks:** `crbench audit-tex` on `main.tex` and each `sections/*.tex` → 0 errors
  (`paper/audit-tex.log`). The mechanical `gate_check.py --paper` found two numbers the crbench
  auditor had accepted (`95\%`, `2^{32}` — its matcher is stricter than crbench's normaliser);
  both are definitions, so the lines carry `% no-evidence: <reason>` as the gate script prescribes.
  It also caught a header mismatch in `CLAIMS.md` (column must start with "EVIDENCE refs").
- **Gate P7:** PASS.

### P8 — Review → submit (mock) · `/cra-review "LNCS short paper"` then `/cra-submit`
- **Agents:** `reviewer-sim` (skills `venue-calibration`, `mock-review`; optional
  `workflows/mock-review-panel.js`), `submission-rebuttal` (skills `anonymize-check`,
  `camera-ready`, `artifact-pack`).
- **Wrote:** `REVIEWS.md` — round R1 with three personas (expert-skeptic, generalist, data
  auditor), meta-review and 5 routed action items; **D-6** sent the draft back to P7 once (add the
  saturation sentence, state CPU time, say that a nibble output needs only one PBS); all items
  closed. `SUBMISSION.md` — format/anonymity/consistency/reference checklist mostly ticked;
  `anon_check.py` with a private deny-list: HIGH=0 MEDIUM=0 LOW=3 (informational);
  `pdf_checks.py`: RESULT OK. The actual upload is intentionally **not** done (the toolkit never
  sends anything off the machine without the human).
- **Gate P8:** PASS (`gate-check.log`).

## What to copy from this example into a real project
1. Write the *strong* thesis first and let the falsifier cut it down (C2, C3).
2. Attack speed-up claims at the edge of the claimed range, not where they were measured (C3).
3. Check input/output formats before comparing methods (C5).
4. On a shared machine, decide the timing metric explicitly and log the decision (D-4).
5. Refuted claims stay in `CLAIMS.md`; replacements get their own ID (C6).
6. Run both `crbench audit-tex` and `gate_check.py`: they overlap but are not identical.
