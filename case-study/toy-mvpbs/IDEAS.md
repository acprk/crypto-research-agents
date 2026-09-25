# IDEAS — output of `idea-miner` (TEACHING EXAMPLE)

Produced with `skills/idea-mining-loop` (probe → free a fixed parameter → cost screen →
anomaly → algebraic explanation → controlled experiment → real-system check → generalise).

## I1: one blind rotation for all four output bits (multi-value PBS)
- **Probe / anomaly observed:** the four per-bit PBS calls for the same input nibble run four
  *identical* blind rotations up to the test polynomial; only the LUT differs
  (`cryptomath.costmodel.Counter`: 4 × 32 CMux per S-box).
- **Algebraic / structural explanation:** T_f · (1 − X) = Δ·d_f with d_f an integer polynomial
  with ≤ p non-zero coefficients, and (1 − X) is invertible in Z[1/2][X]/(X^N+1). So
  T_f = v0 · d_f with v0 independent of f (THEORY L1). This is exactly CIM19's factorisation.
- **Controlled experiment:** code/bench_sbox.py, perbit vs mvpbs, same keys/encoding/timer.
- **Expected gain (cost model):** 4 blind rotations → 1; the extra work is 4 integer
  polynomial products with ≤ 16 non-zero coefficients (negligible next to 32 CMux) → ≈ 4×.
- **Kill criteria:** measured speed-up at k = 4 below 2×, or any wrong output at T1.
- **Pre-emption check:** published (CIM19, 2019). We re-implement a known technique on purpose.
- **Status:** promoted to CLAIMS (C1, C2, C3, C4)

## I2: re-order the input encoding (Gray code) to shrink ‖d_i‖
- **Probe / anomaly observed:** ‖d_i‖² counts the value changes of bit i along m = 0..15
  (10, 10, 8, 8 for PRESENT). A different ordering of the 16 inputs would give fewer changes.
- **Algebraic / structural explanation:** d_f is the discrete derivative of f along the order
  in which the inputs sit in the test polynomial; the order is fixed by the input encoding
  m ↦ m·q/(2p).
- **Controlled experiment:** not run.
- **Expected gain (cost model):** at best −1 to −2 bits of noise, zero speed gain.
- **Kill criteria:** re-encoding the input costs anything homomorphically.
- **Pre-emption check:** n/a.
- **Status:** **killed** (2026-09-16, falsifier screen): the encoding of m is produced by the
  previous layer; changing the order is itself a LUT evaluation (one more PBS), which costs
  more than all four PBS we try to save. Dead on arrival — kept here because killed ideas are data.

## I3: CMux tree / vertical packing (CGGI17) instead of any PBS
- **Probe / anomaly observed:** with the input bits available as GGSW ciphertexts, the whole
  S-box is 4 CMux + 4 sample extractions (cost counter).
- **Algebraic / structural explanation:** rotate one packed LUT polynomial by X^{-4m} bit by bit.
- **Controlled experiment:** `vpack` arm of results/bench_T1_k4.
- **Expected gain (cost model):** ≈ 8× over MV-PBS in the toy — *if* inputs are GGSW.
- **Kill criteria:** end-to-end cost from an LWE input (bit extraction + circuit bootstrapping)
  exceeds one MV-PBS.
- **Pre-emption check:** published (CGGI17).
- **Status:** promoted to CLAIMS as C5 → refuted at P6 (input-format fairness); parked.
