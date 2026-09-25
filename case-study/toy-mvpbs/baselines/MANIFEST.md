# baselines/MANIFEST — owner: `baseline-engineer` (TEACHING EXAMPLE)

| baseline | source | pinned version | build recipe | how measured | fairness notes |
|---|---|---|---|---|---|
| **per-bit PBS** (strongest fair baseline, CJP21-style programmable bootstrapping, one PBS per output bit) | in-tree: `lib/cryptomath/cryptomath/fhe/tfhe.py` (`TFHE.pbs`) called from `code/sbox_fhe.py::per_bit_pbs` | repo commit eb1f494; SHA-256 prefix 366fbc560360 (results/CODE-SHA256.txt) | none (pure Python, numpy) | `code/bench_sbox.py --method perbit` via crbench | same keys (seed), same encoding (p = 16, one padding bit), same parameter set, same timer scope (evaluation only), same thread count (1), interleaved with the candidate |
| vpack (CMux tree, CGGI17) | in-tree `code/sbox_fhe.py::vpack_eval` | same | none | `--method vpack` | **not a like-for-like baseline**: consumes GGSW inputs; reported only to illustrate claim C5's refutation |
| TFHE-rs / tfhe (C++) | see `references/baselines/MANIFEST.md` | – | – | **not used** | a production comparison would be a different claim (absolute speed), out of scope by DECISIONS D-1 |

## Fairness checklist (signed 2026-09-18, baseline-engineer)
- [x] Baseline and candidate share the key material, parameters and message encoding.
- [x] Baseline is not handicapped: it is the library's own `pbs`, unchanged.
- [x] Timed region identical (homomorphic evaluation of all inputs; key generation and encryption excluded) — see `code/bench_sbox.py`.
- [x] Correctness asserted inside every timed execution (exit code 1 on a wrong output at T1).
- [x] Published numbers reproduced: n/a (in-tree toy baseline; no published number exists for it).
