"""cryptomath.symmetric -- S-box / Boolean-function analysis, toy ciphers, trail search.

Modules
-------
gf2n      GF(2^n) arithmetic, power maps x^d, Gold / Kasami exponent checks
boolean   truth table <-> ANF (Möbius), Walsh–Hadamard, bent, CI, resiliency, AI
sbox      DDT, LAT, BCT, differential uniformity, (non)linearity, degree, APN,
          boomerang uniformity, branch numbers, ``sbox_report``
aes       AES-128 reference (FIPS-197 validated) with round-reduced variants
spn       PRESENT-like ToySPN (8/16/32/64-bit), ToyFeistel            # TOY
stream    LFSR, NLFSR, Berlekamp–Massey, ToyGrain                     # TOY
trails    Matsui branch-and-bound, exhaustive DP, CNF (DIMACS) and MILP (LP)
          exporters for differential/linear active-S-box models
integral  square/integral distinguisher, exact degree, cube lower bound,
          Boura–Canteaut–De Cannière degree upper bound
afcost    cost formulas for MiMC, HADES/Poseidon, Rasta, LowMC, Trivium-like, AES

Quick start::

    from cryptomath.symmetric import PRESENT_SBOX, sbox_report, best_trail_bnb, ToySPN
    sbox_report(PRESENT_SBOX)["differential_uniformity"]   # 4
    Bn, trail = best_trail_bnb(PRESENT_SBOX, ToySPN(16).perm, rounds=3)
"""
from .gf2n import (GF2n, DEFAULT_MODULI, is_irreducible_gf2, power_map, inverse_map,
                   cyclotomic_class, is_gold_exponent, is_kasami_exponent, gold_is_apn,
                   kasami_is_apn, is_permutation_exponent)
from .boolean import (mobius, tt_to_anf, anf_to_tt, anf_string, fwht, walsh, is_balanced,
                      is_bent, correlation_immunity, resiliency, algebraic_immunity,
                      autocorrelation, boolean_from_callable, majority)
from .boolean import algebraic_degree as boolean_degree
from .boolean import nonlinearity as boolean_nonlinearity
from .sbox import (PRESENT_SBOX, GIFT_SBOX, ddt, lat, bct, walsh_spectrum, inverse_sbox,
                   is_permutation, differential_uniformity, is_apn, linearity, nonlinearity,
                   boomerang_uniformity, algebraic_degree, min_component_degree,
                   differential_branch_number, linear_branch_number, coordinate, component,
                   fixed_points, sbox_report)
from .aes import AES128, SBOX as AES_SBOX, INV_SBOX as AES_INV_SBOX, encrypt_block as aes_encrypt, \
    decrypt_block as aes_decrypt, key_expansion as aes_key_expansion, self_test as aes_self_test
from .spn import ToySPN, ToyFeistel, present_permutation, apply_bit_perm
from .stream import LFSR, NLFSR, ToyGrain, berlekamp_massey
from .trails import (weight_table, allowed_patterns, best_trail_bnb, best_trail_exhaustive,
                     min_active_sboxes_exhaustive, Trail, CNF, spn_active_sbox_cnf,
                     trail_to_assignment, run_sat_solver, MILPModel, spn_active_sbox_milp)
from .integral import (integral_sum, balanced_bits, square_distinguisher, exact_output_degrees,
                       cube_sum_degree_lower_bound, bcd_gamma, degree_upper_bounds)
from .afcost import (CipherCost, power_mult_cost, mimc_rounds, mimc_cost, hades_cost, rasta_cost,
                     lowmc_cost, trivium_like_cost, aes128_boolean_cost, compare as compare_costs)

__all__ = [n for n in dir() if not n.startswith("_")]
