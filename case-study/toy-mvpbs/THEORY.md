# THEORY — statements, proof status, formalisation (owner: `theorist`) — TEACHING EXAMPLE

| paper label | statement (short) | proof status (sketch/full/checked) | numeric check (script) | Lean name | sorry-free? |
|---|---|---|---|---|---|
| L1 (lem:factor) | T_f = v0 · d_f in Z_q[X]/(X^N+1) for every f : Z_p → Z_p (p ∣ N, q = 2^32, Δ = q/2p even) | full (below) + checked | theory/check_mvpbs_noise.py `L1`: 66 564 LUTs, 0 counterexamples | – (not formalised; see note) | – |
| L2 (lem:norm) | max over Boolean f of ‖d_f‖² equals p + 2 (= 18 for p = 16); PRESENT bits: 10, 10, 8, 8 | full (below) + checked | `L2`: exhaustive for p = 2, 4, 8, 16 | – | – |
| T1 (thm:noise) | output variance of MV-PBS for LUT f: ‖d_f‖²·Var_BR + Var_KS (per-bit PBS: Var_BR + Var_KS), under the usual independence heuristic for the accumulator noise | sketch (heuristic, standard) + checked | `T1a`: Monte Carlo ratio 0.955–1.029 (4 LUTs); `T1b`: model prediction; measured in results/noise_T{1,2} | – | – |

Script output: `theory/check_mvpbs_noise.log` (exit 0). Run: `/usr/bin/python3 theory/check_mvpbs_noise.py` (≈ 7 s).

## Setting
Torus Z_q with q = 2^32, ring R = Z[X]/(X^N+1) (N a power of two, so X^N+1 = Φ_{2N}),
message space Z_p with one padding bit, Δ = q/(2p). The standard PBS test polynomial for
f : Z_p → Z_p is T_f = Σ_{j<N} Δ·f(⌊jp/N⌋)·X^j (code: `TFHE.test_polynomial`). Blind rotation
of T_f by the (mod-switched, offset) phase and sample extraction at index 0 yields an LWE
encryption of Δ·f(m) (CGGI20, CJP21).

## L1 — factorisation (CIM19's idea, re-derived for this encoding)
Define the integer polynomial d_f by d_f[0] = f(0) + f(p−1), d_f[kN/p] = f(k) − f(k−1) for
k = 1..p−1, and 0 elsewhere; and v0 = (Δ/2)·(1 + X + … + X^{N−1}).

*Proof.* In R, (1 − X)(1 + X + … + X^{N−1}) = 1 − X^N = 2, so v0·(1 − X) = Δ. Compute
T_f·(1 − X): coefficient j ≥ 1 is t_j − t_{j−1}, non-zero only at block boundaries j = kN/p
where it equals Δ(f(k) − f(k−1)); coefficient 0 is t_0 − (−t_{N−1}) = Δ(f(0) + f(p−1)) by
negacyclicity. Hence T_f·(1 − X) = Δ·d_f. Since (1 − X) is a unit in Z[1/2][X]/(X^N+1)
with inverse (1/2)Σ X^j, T_f = (1 − X)^{−1}·Δ·d_f = v0·d_f. All coefficients
of v0 are the integer Δ/2 (Δ even), so the identity holds in Z_q[X]/(X^N+1). ∎

Because blind rotation only multiplies the accumulator by monomials X^{a} and adds GGSW-
selected differences (both R-linear), rotating v0 and multiplying by d_f afterwards equals
rotating T_f. One blind rotation of v0 therefore serves every f (MV-PBS).

## L2 — norm bound for Boolean LUTs
For f : Z_p → {0,1}: |d_f[0]| ≤ 2 and |d_f[kN/p]| ≤ 1, so ‖d_f‖² = (f(0) + f(p−1))² + #{k : f(k) ≠ f(k−1)}.
If f(0) = f(p−1) = 1 the number of changes along 0..p−1 is even, hence ≤ p − 2, giving ≤ 4 + p − 2 = p + 2;
otherwise ≤ 1 + (p − 1) = p. The maximum p + 2 is attained (f = 1 on {0, p−1} and on even k). ∎
PRESENT S-box output bits (LSB first): ‖d‖² = 10, 10, 8, 8.

## T1 — noise of MV-PBS
Let the accumulator after blind rotation of v0 be a GLWE encryption of X^{−φ̃}·v0 with noise
polynomial e whose coefficients are (heuristically) independent, centred, variance Var_BR
(the same Var_BR as a normal PBS; `cryptomath.fhe.noise.tfhe_blind_rotate`). Multiplying by
the plaintext integer polynomial d_f multiplies the message by d_f and the noise by d_f;
coefficient 0 of d_f·e has variance ‖d_f‖²·Var_BR. Sample extraction is exact; key switching
adds Var_KS (`tfhe_keyswitch`). So

    Var_out(MV-PBS, f) = ‖d_f‖² · Var_BR + Var_KS,      Var_out(PBS, f) = Var_BR + Var_KS.

Decoding fails when |error| ≥ 1/(4p) = 2^−6 (p = 16 with one padding bit).

**Numbers (from theory/check_mvpbs_noise.log, T1b):**

| set | GLWE σ | std_BR | std_KS | per-bit std | MV std (bits 0,1 / 2,3) | predicted P[S-box wrong], MV, k=4 |
|---|---|---|---|---|---|---|
| T1 | 2^−28 | 2^−14.47 | 2^−12.13 | 2^−12.10 | 2^−11.89 / 2^−11.93 | ≈ 0 |
| T2 | 2^−22 | 2^−8.5 | 2^−12.13 | 2^−8.5 | 2^−6.84 / 2^−7.0 | 0.219 (independence approx.) |

Observation that led to decision D-3: at T1 the key-switch noise dominates, so the √10
amplification of the blind-rotation noise (+1.66 bits) is invisible at the output; the claim
C2 can only be attacked where Var_BR dominates (T2).

**Measured (results/noise_T2/summary.log):** MV std 2^−6.74 (bit 0; model 2^−6.84), per-bit std
2^−8.54 (bit 0; model 2^−8.50); S-box failure 32/128 at k = 4 (model 0.219). The model is used
only as a prediction; every paper number is the measured one.

## Notes
- **Lean:** not attempted — L1 is a two-line ring identity and the proof above plus an
  exhaustive check is the proportionate level of assurance for a toy (skills/lean-bridge
  recommends formalising only the algebraic core of a *real* main theorem).
- **Security:** T1/T2 are insecure by design (n = 32). No `param-estimation` run (DECISIONS D-1).
- **Textbook facts used:** see MATH-REFS.md.
