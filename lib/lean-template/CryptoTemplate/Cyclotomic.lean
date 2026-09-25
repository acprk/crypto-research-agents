/-
  Toy formalisation: the 4th cyclotomic polynomial.
  (Checked against Mathlib v4.33.1 with `lake env lean`; no errors, no warnings.)
-/
import Mathlib.RingTheory.Polynomial.Cyclotomic.Basic

namespace CryptoTemplate.Cyclotomic

open Polynomial

/-- Lemma 5 (toy). `Φ₄(X) = X² + 1` over any commutative ring. -/
theorem cyclotomic_four (R : Type*) [CommRing R] : cyclotomic 4 R = X ^ 2 + 1 := by
  have h := cyclotomic_prime_pow_eq_geom_sum (R := R) (p := 2) (n := 1) Nat.prime_two
  have h4 : (2 : ℕ) ^ (1 + 1) = 4 := by norm_num
  rw [h4] at h
  rw [h, Finset.sum_range_succ, Finset.sum_range_one]
  ring

/-- Lemma 5 specialised to `ℤ`. -/
theorem cyclotomic_four_int : cyclotomic 4 ℤ = X ^ 2 + 1 := cyclotomic_four ℤ

/-- Lemma 6 (toy). Any `A` with `A² = -1` is a root of `Φ₄` in any commutative ring. -/
theorem cyclotomic_four_eval {R : Type*} [CommRing R] {A : R} (h : A ^ 2 = -1) :
    (cyclotomic 4 R).eval A = 0 := by
  rw [cyclotomic_four]
  simp [h]

end CryptoTemplate.Cyclotomic
