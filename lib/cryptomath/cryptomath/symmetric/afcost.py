"""Formula-based cost models for FHE/MPC/ZK-friendly (arithmetization-oriented) ciphers.

All numbers are *formulas* evaluated on user parameters; round numbers
quoted as defaults are the designers' public recommendations at the time of
the cited paper and may have been revised after later cryptanalysis --
always re-check the latest specification before using them in a paper.

References
----------
* M. Albrecht, L. Grassi, C. Rechberger, A. Roy, T. Tiessen, "MiMC:
  efficient encryption and cryptographic hashing with minimal multiplicative
  complexity", ASIACRYPT 2016 (ePrint 2016/492).
* L. Grassi, D. Khovratovich, C. Rechberger, A. Roy, M. Schofnegger,
  "Poseidon: a new hash function for zero-knowledge proof systems",
  USENIX Security 2021 (ePrint 2019/458).
* L. Grassi, R. Lüftenegger, C. Rechberger, D. Rotaru, M. Schofnegger,
  "On a generalization of substitution-permutation networks: the HADES
  design strategy", EUROCRYPT 2020 (ePrint 2019/1107).
* C. Dobraunig, M. Eichlseder, L. Grassi, V. Lallemand, G. Leander, E. List,
  F. Mendel, C. Rechberger, "Rasta: a cipher with low ANDdepth and few ANDs
  per bit", CRYPTO 2018 (ePrint 2018/181).
* M. Albrecht, C. Rechberger, T. Schneider, T. Tiessen, M. Zohner, "Ciphers
  for MPC and FHE", EUROCRYPT 2015 (LowMC).
* A. Canteaut, S. Carpov, C. Fontaine, T. Lepoint, M. Naya-Plasencia,
  P. Paillier, R. Sirdey, "Stream ciphers: a practical solution for
  efficient homomorphic-ciphertext compression", FSE 2016 (Kreyvium).
* J. Boyar, R. Peralta, "A new combinational logic minimization technique
  with applications to cryptology", SEA 2010 (AES S-box with 32 AND gates).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass


@dataclass
class CipherCost:
    name: str
    mults: int              # field multiplications (or AND gates for binary)
    mult_depth: int         # multiplicative (AND-) depth
    nonlinear_ops: int      # S-box / chi evaluations
    output_elems: int       # field elements (or bits) produced per call
    notes: str = ""

    def per_output(self) -> float:
        return self.mults / max(1, self.output_elems)

    def as_dict(self) -> dict:
        d = asdict(self)
        d["mults_per_output"] = self.per_output()
        return d


def power_mult_cost(alpha: int) -> tuple[int, int]:
    """(#mults, depth) of x -> x^alpha by square-and-multiply.

    #mults = floor(log2 alpha) + popcount(alpha) - 1, depth = ceil(log2 alpha).
    (Optimal addition chains can be shorter for some alpha.)
    """
    if alpha < 1:
        raise ValueError("alpha >= 1")
    if alpha == 1:
        return 0, 0
    return alpha.bit_length() - 1 + bin(alpha).count("1") - 1, math.ceil(math.log2(alpha))


def mimc_rounds(field_bits: float, alpha: int = 3) -> int:
    """r = ceil(n / log2(alpha)) (MiMC-n/n; Albrecht et al. 2016)."""
    return math.ceil(field_bits / math.log2(alpha))


def mimc_cost(field_bits: float, alpha: int = 3, rounds: int | None = None,
              char2_free_squaring: bool = False) -> CipherCost:
    """MiMC-n/n: r rounds of x -> (x + k + c_i)^alpha.

    Over GF(2^n) squaring is linear; set ``char2_free_squaring`` to count only
    non-linear multiplications (for alpha = 3: one per round).
    """
    r = rounds if rounds is not None else mimc_rounds(field_bits, alpha)
    m, d = power_mult_cost(alpha)
    if char2_free_squaring:
        m = bin(alpha).count("1") - 1
    return CipherCost(f"MiMC-{field_bits:g} (alpha={alpha})", m * r, d * r, r, 1,
                      "rounds = ceil(n/log2(alpha)) unless given")


def hades_cost(t: int, R_F: int, R_P: int, alpha: int = 5, name: str = "HADES/Poseidon") -> CipherCost:
    """HADES-style permutation: R_F full rounds (t S-boxes), R_P partial rounds (1 S-box).

    #S-boxes = t*R_F + R_P; each S-box x^alpha costs ``power_mult_cost(alpha)``.
    Depth counts every round (partial rounds are still sequential).
    Designer-suggested (R_F, R_P) depend on field size, t, alpha and the
    security level: take them from the specification.
    """
    m, d = power_mult_cost(alpha)
    ns = t * R_F + R_P
    return CipherCost(f"{name}(t={t},RF={R_F},RP={R_P},a={alpha})", ns * m, (R_F + R_P) * d, ns, t,
                      "output_elems = state width t (permutation)")


def rasta_cost(n: int, rounds: int) -> CipherCost:
    """Rasta: r affine layers + chi on n bits per round -> n ANDs, AND-depth 1 per round."""
    return CipherCost(f"Rasta(n={n},r={rounds})", n * rounds, rounds, rounds, n,
                      "chi layer = n AND gates; output n keystream bits per call")


def lowmc_cost(n_sboxes: int, rounds: int, block_bits: int) -> CipherCost:
    """LowMC: m 3-bit S-boxes per round (3 ANDs each, AND-depth 1)."""
    return CipherCost(f"LowMC(m={n_sboxes},r={rounds})", 3 * n_sboxes * rounds, rounds,
                      n_sboxes * rounds, block_bits)


def trivium_like_cost(keystream_bits: int, init_rounds: int = 1152, ands_per_step: int = 3,
                      name: str = "Trivium-like") -> CipherCost:
    """Trivium/Kreyvium: 3 AND gates per clock (update of 3 registers).

    AND-depth grows with the number of clocks; the exact depth of output bit
    t depends on tap distances -- this model reports only the gate count and
    leaves depth = -1 (track it by simulating the registers symbolically).
    """
    steps = init_rounds + keystream_bits
    return CipherCost(name, ands_per_step * steps, -1, steps, keystream_bits,
                      "count includes initialisation; FHE users usually precompute it")


def aes128_boolean_cost(include_key_schedule: bool = True, and_per_sbox: int = 32) -> CipherCost:
    """AES-128 as a Boolean circuit: 160 (+40 key-schedule) S-boxes x 32 ANDs (Boyar–Peralta)."""
    ns = 160 + (40 if include_key_schedule else 0)
    return CipherCost("AES-128 (Boolean)", ns * and_per_sbox, -1, ns, 128,
                      "AND-depth depends on the S-box circuit chosen")


def compare(costs) -> list[dict]:
    """Rows sorted by mults per output element (for quick Markdown tables)."""
    return sorted((c.as_dict() for c in costs), key=lambda d: d["mults_per_output"])
