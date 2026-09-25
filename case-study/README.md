# case-study/ — end-to-end example (TEACHING EXAMPLE)

A toy research project run through all phases P0–P8 with the 12 agents, using only public,
textbook-level material and insecure toy parameters. **Do not cite any number from here.**

| path | what |
|---|---|
| [`WALKTHROUGH.md`](WALKTHROUGH.md) | phase-by-phase narration: command → agent → files read/written → gate → loops; exact reproduction commands |
| [`../docs/zh/case-study-walkthrough.md`](../docs/zh/case-study-walkthrough.md) | Chinese version |
| [`toy-mvpbs/`](toy-mvpbs/) | the project: blackboard files (`STATE.md`, `CLAIMS.md`, `EVIDENCE.md`, …) at its top level |
| `toy-mvpbs/code/` | MV-PBS, per-bit PBS and CMux-tree S-box on `cryptomath.fhe.tfhe`; tests; crbench-driven experiments; figure script |
| `toy-mvpbs/falsify/` | one script per claim + its `.log` (the attacks that refuted C3/C5 and weakened C2) |
| `toy-mvpbs/theory/` | sage-check-style numeric checks of the lemmas (+ log) |
| `toy-mvpbs/results/` | crbench logs (`run.json`, per-execution `r*.log`, `summary.log`), sanitised |
| `toy-mvpbs/paper/` | 5-page LNCS write-up (`main.pdf`), audit-tex / anon-check / pdf-check logs |

Topic: 4-bit S-box (PRESENT) on toy-TFHE ciphertexts — one PBS per output bit vs multi-value PBS
(Carpov–Izabachène–Mollimard, CT-RSA 2019) vs CMux tree (CGGI, ASIACRYPT 2017).
Outcome: MV-PBS 3.86× faster at k = 4 (toy, CPU time); speed-up saturates for many LUTs;
noise grows by ‖d_i‖², visible at a deliberately noisy parameter set.

Quick start: `cd toy-mvpbs && /usr/bin/python3 code/test_sbox_fhe.py && /usr/bin/python3 code/run_experiments.py --quick` (smoke run into `results-quick/`; the full run that produced the evidence is `code/run_experiments.py` without flags, ≈ 2.5 min, plus the falsify scripts ≈ 1 min).
