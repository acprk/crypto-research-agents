/-
  Toy formalisation: roots of unity in commutative rings and in `ZMod p`.
  Pattern to copy: one paper proposition = one Lean theorem, named in README.md's
  proposition ↔ Lean-name table.  No proof escape hatches (gate: scripts_check_no_sorry.sh).
-/
import Mathlib.FieldTheory.Finite.Basic

namespace CryptoTemplate.RootsOfUnity

/-- Prop 1 (toy). If `A² = -1` then `A⁴ = 1`, i.e. `A` is a 4th root of unity. -/
theorem pow_four_of_sq_neg_one {R : Type*} [CommRing R] {A : R} (h : A ^ 2 = -1) :
    A ^ 4 = 1 := by
  calc A ^ 4 = (A ^ 2) ^ 2 := by ring
    _ = 1 := by rw [h]; ring

/-- Prop 2 (toy). If `A^r = 1` then `A^k = A^(k mod r)`: the action is `r`-periodic. -/
theorem pow_mod_of_pow_eq_one {M : Type*} [Monoid M] {A : M} {r : ℕ} (h : A ^ r = 1)
    (k : ℕ) : A ^ k = A ^ (k % r) := by
  conv_lhs => rw [← Nat.div_add_mod k r, pow_add, pow_mul, h, one_pow, one_mul]

/-- Example 3 (toy, concrete). `4` is a square root of `-1` modulo `17`. Checked by `decide`. -/
theorem four_sq_zmod17 : (4 : ZMod 17) ^ 2 = -1 := by decide

/-- Corollary of Prop 1 + Example 3: `4` has multiplicative order dividing 4 in `ZMod 17`. -/
theorem four_pow_four_zmod17 : (4 : ZMod 17) ^ 4 = 1 :=
  pow_four_of_sq_neg_one four_sq_zmod17

/-- Lemma 4 (Fermat). Every nonzero `a : ZMod p` satisfies `a^(p-1) = 1`. -/
theorem fermat {p : ℕ} [Fact p.Prime] {a : ZMod p} (ha : a ≠ 0) : a ^ (p - 1) = 1 :=
  ZMod.pow_card_sub_one_eq_one ha

end CryptoTemplate.RootsOfUnity
