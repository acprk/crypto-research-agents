# Lean 4 + Mathlib template

A minimal project for machine-checking the *algebraic core* of a crypto paper.
The toy lemmas are about 4th roots of unity in `ZMod 17` and the cyclotomic
polynomial Φ₄. Replace them with your own statements.

## Setup

```bash
cp -r lib/lean-template my-paper-lean && cd my-paper-lean
# 1. toolchain: lean-toolchain pins Lean; lakefile.toml pins Mathlib to the SAME version tag
# 2. fetch prebuilt Mathlib oleans (minutes, not hours):
lake exe cache get
# 3. build = certificate
lake build
# 4. zero-sorry gate (also run in CI)
./scripts_check_no_sorry.sh
```

### Mathlib cache pitfalls

- **Version skew.** The Mathlib `rev` in `lakefile.toml` must match the Lean version in
  `lean-toolchain`. If they drift apart, `lake exe cache get` finds no matching oleans and
  `lake build` compiles Mathlib from source (hours, many GB of RAM).
- **Run `lake exe cache get` after every `lake update`**, and whenever `lake-manifest.json`
  changes. Commit `lake-manifest.json` so collaborators resolve the same Mathlib commit.
- **Do not `import Mathlib`** in project files. It pulls in the whole library and makes each
  check slow. Import only the modules you need, e.g. `Mathlib.FieldTheory.Finite.Basic`.
- **Corrupted or partial cache.** Symptom: "object file ... does not exist" or a rebuild of
  Mathlib files. Fix: `lake exe cache clean && lake exe cache get`. Last resort: delete
  `.lake/packages/mathlib/.lake/build` and fetch again.
- **Cold-start latency.** The first `lake env lean File.lean` after a cache fetch can take
  minutes while oleans are memory-mapped. Time a green `lake build` once before you
  assume a proof is looping.
- **Renamed lemmas.** Mathlib renames things often. Look names up with the LSP tools
  below (or `#check`/`exact?`), not from memory or an old paper's appendix.

## Proposition ↔ Lean-name table (keep this in sync with the paper)

Each proposition in the paper gets one row. A reviewer can then open the file and
check the statement without reading Lean proofs. State **what is modelled** and what
is not. For example, if noise is a *prescribed model* rather than something derived
from ciphertext semantics, say so. The paper must not claim more than the Lean
statement proves.

| paper statement | Lean name | file | modelling notes |
|---|---|---|---|
| Prop 1: `A² = -1 ⇒ A⁴ = 1` in any commutative ring | `CryptoTemplate.RootsOfUnity.pow_four_of_sq_neg_one` | `RootsOfUnity.lean` | fully general |
| Prop 2: `A^r = 1 ⇒ A^k = A^(k mod r)` | `CryptoTemplate.RootsOfUnity.pow_mod_of_pow_eq_one` | `RootsOfUnity.lean` | any monoid |
| Example 3: `4² = -1` in `ZMod 17` | `CryptoTemplate.RootsOfUnity.four_sq_zmod17` | `RootsOfUnity.lean` | concrete, `decide` |
| Cor.: `4⁴ = 1` in `ZMod 17` | `CryptoTemplate.RootsOfUnity.four_pow_four_zmod17` | `RootsOfUnity.lean` | |
| Lemma 4 (Fermat): `a ≠ 0 ⇒ a^(p-1) = 1` in `ZMod p` | `CryptoTemplate.RootsOfUnity.fermat` | `RootsOfUnity.lean` | wraps Mathlib |
| Lemma 5: `Φ₄ = X² + 1` (any comm. ring; ℤ corollary) | `CryptoTemplate.Cyclotomic.cyclotomic_four`, `..._int` | `Cyclotomic.lean` | |
| Lemma 6: `A² = -1 ⇒ Φ₄(A) = 0` | `CryptoTemplate.Cyclotomic.cyclotomic_four_eval` | `Cyclotomic.lean` | any commutative ring |

## Zero-sorry policy

- `sorry`, `admit`, new `axiom`s and `native_decide` are forbidden in the published tree.
  `native_decide` trusts the compiler, so it is outside the kernel-checked guarantee.
- The gate script greps for them. Also run `#print axioms <thm>`, or the LSP tool
  `lean_verify`, on every headline theorem. Only `propext`, `Classical.choice` and
  `Quot.sound` should appear.
- Work-in-progress proofs live on a branch. The paper cites only theorems that are green on the
  published commit, and it records that commit hash.

## Using the lean-lsp MCP tools (if configured)

| task | tool |
|---|---|
| does this snippet compile? | `lean_run_code` (self-contained, include imports) |
| proof state at a line | `lean_goal` |
| errors / warnings in a file | `lean_diagnostic_messages` |
| find a Mathlib lemma by name fragment | `lean_local_search` (fast, local) |
| natural-language → lemma | `lean_leansearch`, `lean_leanfinder` (rate-limited) |
| type-pattern search | `lean_loogle` (rate-limited) |
| try several tactics at once | `lean_multi_attempt` (`["simp", "ring", "omega", "decide"]`) |
| axiom audit of a theorem | `lean_verify` with the fully qualified name |
| rebuild after adding imports | `lean_build` (slow; `fetch_cache=true` only if oleans are missing) |
