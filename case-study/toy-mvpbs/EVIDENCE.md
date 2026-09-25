# EVIDENCE — every number in the paper traces to a log (TEACHING EXAMPLE)

> Owner: `experimenter`. Audited by `falsifier` and by `crbench audit-tex paper/main.tex EVIDENCE.md`.
> **All timings are toy pure-Python numbers** (numpy, single thread, process CPU time of the
> homomorphic evaluation only; wall time is logged next to each sample). They measure an
> algorithmic *ratio* inside one toy library and say nothing about production TFHE libraries.
> Machine: shared 104-CPU workstation (Intel Xeon Gold 6230R, governor `powersave`, 1-min load
> 19–37 during the runs; crbench warned about the governor). Host id is crbench's salted hash.
> Code: repo commit eb1f494 + untracked `case-study/`; per-file SHA-256 in `results/CODE-SHA256.txt`
> (column "commit" gives `sbox_fhe.py`'s hash prefix).

| ID | number/fact as printed in paper | meaning | command | log path | commit | machine | date | runs/median |
|---|---|---|---|---|---|---|---|---|
| E1 | 291.2 ms | per-bit PBS, one PRESENT S-box (4 output bits), set T1, CPU time per S-box | `python3 code/run_experiments.py --only bench_T1_k4` | results/bench_T1_k4/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved (+1 warm-up), 16 inputs each, median |
| E2 | 75.4 ms | MV-PBS, same setting as E1 | same as E1 | results/bench_T1_k4/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved (+1), median |
| E3 | 3.86× [3.79, 3.95] (95% CI) | speed-up MV-PBS vs per-bit PBS, k=4, T1 (ratio of medians, paired bootstrap 95% CI) | same as E1 | results/bench_T1_k4/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 paired rounds |
| E4 | 9.6 ms (7.81× vs MV-PBS, GGSW input) | vpack (CMux tree) S-box from GGSW-encrypted input bits — different input format, see C5 | same as E1 | results/bench_T1_k4/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved (+1), median |
| E5 | 0.96× [0.90, 1.09] | speed-up at k=1 LUT | `python3 code/run_experiments.py --only bench_T1_kscan` | results/bench_T1_kscan/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved (+1), 4 inputs each |
| E6 | 2.00× [1.98, 2.02] | speed-up at k=2 | same as E5 | results/bench_T1_kscan/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved (+1) |
| E7 | 2.95× [2.89, 3.13] | speed-up at k=3 | same as E5 | results/bench_T1_kscan/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved (+1) |
| E8 | 3.96× [3.83, 4.18] | speed-up at k=4 (4-input k-scan; consistent with E3) | same as E5 | results/bench_T1_kscan/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved (+1) |
| E9 | 43.67× [42.53, 44.63] | speed-up at k=64 LUTs (4 S-box bits + 60 random Boolean LUTs), T1; per-bit 4565.5 ms vs MV-PBS 104.6 ms | `python3 falsify/C3_linear_speedup/check_linear_speedup.py` | results/falsify_C3_k64/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 5 interleaved, 1 input each |
| E10 | 32/128 (0.25) [0.183, 0.332] | MV-PBS S-box failure rate (any of the 4 bits wrong), noisy set T2, Wilson 95% | `python3 code/run_experiments.py --only noise_T2` | results/noise_T2/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 128 trials (inputs cycle 0..15) |
| E11 | 14/128 (0.109), 22/128, 27/128 | MV-PBS failure rate at k = 1, 2, 3, T2 | same as E10 | results/noise_T2/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 128 trials |
| E12 | 0/128 [0, 0.029] | per-bit PBS S-box failure rate at T2, every k | same as E10 | results/noise_T2/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 128 trials |
| E13 | 2^-6.74 (model 2^-6.84) | measured std of MV-PBS output bit 0 at T2 (torus fraction) vs Theorem T1 | same as E10 | results/noise_T2/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 128 samples, sample std |
| E14 | 2^-8.54 (model 2^-8.50) | measured std of per-bit PBS output bit 0 at T2 vs model | same as E10 | results/noise_T2/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 128 samples |
| E15 | 10, 10, 8, 8; max 18 | ‖d_i‖² of the PRESENT output bits; maximum over all Boolean LUTs on Z_16 | `python3 theory/check_mvpbs_noise.py` | theory/check_mvpbs_noise.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 | 2026-09-25 | exhaustive (65 536 LUTs) |
| E16 | 0 of 384 | wrong output bits at T1 (48 trials × 4 bits × 2 methods) | `python3 code/run_experiments.py --only noise_T1` | results/noise_T1/summary.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 / 1 thr | 2026-09-25 | 48 trials per method |
| E17 | 256/256 | correct outputs in the C1 falsification attack (3 key seeds × 16 inputs × 4 bits + 64 edge-LUT outputs) | `python3 falsify/C1_correctness/attack_correctness.py` | falsify/C1_correctness/attack_correctness.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 | 2026-09-25 | exhaustive over inputs |
| E18 | 0.219 | model-predicted MV-PBS S-box failure probability at T2, k=4 (independence approximation) | `python3 theory/check_mvpbs_noise.py` | theory/check_mvpbs_noise.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 | 2026-09-25 | analytic |
| E19 | ≥ 376 ms, ≤ 0.20× | end-to-end lower bound for vpack from an LWE input (bit extraction + 4 circuit bootstraps with ℓ_cb = 1) and resulting ratio vs MV-PBS | `python3 falsify/C5_vpack_fairness/cost_end_to_end.py` | falsify/C5_vpack_fairness/cost_end_to_end.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 | 2026-09-25 | derived from medians of E1, E2, E4 |
| E20 | 2^-28, 2^-22, 2^-6, 2^-20, q = 2^32, 2^7, 2^4 | parameter definitions: GLWE σ of T1 and T2; decoding margin 1/(4p) for p = 16; LWE σ; torus modulus; gadget and key-switch bases (not measurements) | definition in `code/sbox_fhe.py` (`PARAMS`) | code/sbox_fhe.py | eb1f494+cs:f60ed7ff1ad5 | – | 2026-09-25 | definition |
| E21 | 2^-14.47, 2^-12.13, 2^-8.5 | model std: blind rotation at T1, key switch, blind rotation at T2 | `python3 theory/check_mvpbs_noise.py` | theory/check_mvpbs_noise.log | eb1f494+cs:f60ed7ff1ad5 | host:1a8729448f93 | 2026-09-25 | analytic |
| E22 | 1.66 bits | noise growth of MV-PBS output bit 0 over the blind-rotation noise: log2 √10 | derived: E15 | - | - | - | 2026-09-25 | - |

Notes
- Superseded first P5 run (wall-clock timing under load; IQR 257 ms on a 383 ms median) is not
  in the ledger; its effect is recorded in DECISIONS D-4. Superseded numbers never go in the paper.
- `crbench evidence check EVIDENCE.md --root .` output: see SUBMISSION.md.
