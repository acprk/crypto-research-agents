# TOY: not secure
"""Analytic noise estimators (coefficient-variance heuristic).

All functions return a :class:`Noise` (variance of one noise coefficient,
in absolute units of the ciphertext modulus) and helpers convert it to
"bits of budget" or failure probability.  Model: noise coefficients are
independent, zero-mean, and a product of polynomials of length N with
independent coefficients has coefficient variance N * Var(a) * Var(b).
This is the standard average-case heuristic (e.g. Costache--Smart,
ePrint 2015/889; Costache et al., "On the precision loss in approximate
homomorphic encryption", ePrint 2022/162); the canonical-embedding
worst-case bounds of the original papers are larger by ~sqrt(N) factors.

Symbols: N ring dim, sigma error std dev, Vs / Vu secret / ephemeral
per-coefficient variance (2/3 for uniform ternary, h/N for sparse), t plain
modulus, w key-switch digit base, L number of digits.

For TFHE the unit is the torus (variance of phase as a fraction of 1),
following CGGI (ePrint 2018/421, Thm. 3.x / 4.x) and the TFHE-rs noise
formulas (average case, binary keys, Var(s) = E[s^2] = 1/2).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["Noise", "budget_bits", "tail_bound", "failure_prob_log2",
           "bgv_fresh", "bgv_add", "bgv_mul", "bgv_keyswitch", "bgv_modswitch",
           "bfv_fresh", "bfv_mul", "bfv_keyswitch",
           "ckks_fresh", "ckks_mul", "ckks_rescale", "ckks_keyswitch", "ckks_precision_bits",
           "tfhe_ms", "tfhe_external_product_add", "tfhe_blind_rotate", "tfhe_keyswitch",
           "tfhe_pbs", "tfhe_failure_prob_log2"]

TERNARY_VAR = 2.0 / 3.0


@dataclass
class Noise:
    var: float

    @property
    def std(self) -> float:
        return math.sqrt(self.var)

    def __add__(self, o: "Noise") -> "Noise":
        return Noise(self.var + o.var)

    def scale(self, c: float) -> "Noise":
        return Noise(self.var * c * c)


def tail_bound(noise: Noise, sigmas: float = 6.0) -> float:
    """High-probability bound on one coefficient (sigmas * std)."""
    return sigmas * noise.std


def budget_bits(noise: Noise, modulus: float, sigmas: float = 6.0) -> float:
    """log2(modulus / (2 * bound)): decryption fails when this reaches 0."""
    return math.log2(modulus / (2 * tail_bound(noise, sigmas)))


def failure_prob_log2(noise: Noise, margin: float, coeffs: int = 1) -> float:
    """log2 of P[|X| > margin] for X ~ N(0, var), union bound over ``coeffs``."""
    z = margin / (math.sqrt(2) * noise.std)
    p = math.erfc(z)
    if p == 0.0:  # asymptotic erfc(z) ~ exp(-z^2)/(z sqrt(pi))
        lp = (-z * z - math.log(z * math.sqrt(math.pi))) / math.log(2)
    else:
        lp = math.log2(p)
    return lp + math.log2(coeffs)


# ------------------------------------------------------------------- BGV
def bgv_fresh(N: int, t: int, sigma: float, Vs: float = TERNARY_VAR, Vu: float = TERNARY_VAR) -> Noise:
    """v = t (e u + e0 + e1 s) + m (public-key encryption); message term ignored."""
    return Noise(t * t * sigma * sigma * (1 + N * (Vu + Vs)))


def bgv_add(a: Noise, b: Noise) -> Noise:
    return a + b


def bgv_mul(a: Noise, b: Noise, N: int) -> Noise:
    """Product of the two noises (before relinearisation)."""
    return Noise(N * a.var * b.var)


def bgv_keyswitch(N: int, t: int, sigma: float, Q: float, w: float) -> Noise:
    """t * sum_i D_i e_i, D_i uniform digits in [0, w)."""
    L = max(1, math.ceil(math.log(Q, w)))
    return Noise(t * t * L * N * (w * w / 3.0) * sigma * sigma)


def bgv_modswitch(a: Noise, q_drop: float, N: int, t: int, Vs: float = TERNARY_VAR) -> Noise:
    """v -> v/q + rounding term (delta0 + delta1 s)/q, |delta/q| <= t/2 uniform."""
    return Noise(a.var / q_drop ** 2 + t * t / 12.0 * (1 + N * Vs))


# ------------------------------------------------------------------- BFV
def bfv_fresh(N: int, sigma: float, Vs: float = TERNARY_VAR, Vu: float = TERNARY_VAR) -> Noise:
    return Noise(sigma * sigma * (1 + N * (Vu + Vs)))


def bfv_mul(a: Noise, b: Noise, N: int, t: int, Vs: float = TERNARY_VAR) -> Noise:
    """Tensor + scale by t/Q (coefficient heuristic).

    Terms: t(v1 k2 + v2 k1) with Var(k) ~ N Vs/12, (v1 m2 + v2 m1) with
    Var(m) ~ t^2/12, and rounding (1 + N Vs + N^2 Vs^2)/12.
    """
    kvar = N * Vs / 12.0
    return Noise(t * t * N * (a.var + b.var) * kvar
                 + N * (a.var + b.var) * t * t / 12.0
                 + (1 + N * Vs + N * N * Vs * Vs) / 12.0)


def bfv_keyswitch(N: int, sigma: float, Q: float, w: float) -> Noise:
    L = max(1, math.ceil(math.log(Q, w)))
    return Noise(L * N * (w * w / 3.0) * sigma * sigma)


# ------------------------------------------------------------------ CKKS
def ckks_fresh(N: int, sigma: float, Vs: float = TERNARY_VAR, Vu: float = TERNARY_VAR) -> Noise:
    return Noise(sigma * sigma * (1 + N * (Vu + Vs)))


def ckks_mul(a: Noise, b: Noise, N: int, msg_a: float, msg_b: float) -> Noise:
    """(m1 + e1)(m2 + e2) - m1 m2 ~ m1 e2 + m2 e1 (+ e1 e2), m = scaled coefficient RMS."""
    return Noise(N * (msg_a ** 2 * b.var + msg_b ** 2 * a.var + a.var * b.var))


def ckks_rescale(a: Noise, q_drop: float, N: int, Vs: float = TERNARY_VAR) -> Noise:
    return Noise(a.var / q_drop ** 2 + (1 + N * Vs) / 12.0)


def ckks_keyswitch(N: int, sigma: float, Q: float, w: float) -> Noise:
    return bfv_keyswitch(N, sigma, Q, w)


def ckks_precision_bits(noise: Noise, scale: float, N: int) -> float:
    """Approximate bits of precision per slot: log2(scale / (std * sqrt(N)))."""
    return math.log2(scale / (noise.std * math.sqrt(N)))


# ------------------------------------------------------------------ TFHE
def tfhe_ms(n: int, N: int, Vs: float = 0.5) -> Noise:
    """Mod switch q -> 2N: rounding error on b and each a_i (uniform, var 1/(12 (2N)^2))."""
    return Noise((1 + n * Vs) / (12.0 * (2 * N) ** 2))


def tfhe_external_product_add(N: int, k: int, bg_bits: int, l: int, var_bsk: float,
                              Vs: float = 0.5) -> Noise:
    """Noise added by one CMux / external product with a binary GGSW."""
    B = 2.0 ** bg_bits
    digit_var = (B * B + 2) / 12.0
    dec_err_var = 1.0 / (12.0 * B ** (2 * l))
    return Noise((k + 1) * l * N * digit_var * var_bsk + (1 + k * N * Vs) * dec_err_var * 0.5)


def tfhe_blind_rotate(n: int, N: int, k: int, bg_bits: int, l: int, var_bsk: float) -> Noise:
    return tfhe_external_product_add(N, k, bg_bits, l, var_bsk).scale(math.sqrt(n))


def tfhe_keyswitch(kN: int, ks_bits: int, ks_l: int, var_ksk: float, Vs: float = 0.5) -> Noise:
    B = 2.0 ** ks_bits
    digit_var = (B * B + 2) / 12.0
    dec_err_var = 1.0 / (12.0 * B ** (2 * ks_l))
    return Noise(kN * ks_l * digit_var * var_ksk + kN * Vs * dec_err_var)


def tfhe_pbs(n: int, N: int, k: int, bg_bits: int, l: int, var_bsk: float,
             ks_bits: int, ks_l: int, var_ksk: float, keyswitch: bool = True) -> Noise:
    """Output noise of PBS (blind rotation + sample extract [+ key switch])."""
    out = tfhe_blind_rotate(n, N, k, bg_bits, l, var_bsk)
    if keyswitch:
        out = out + tfhe_keyswitch(k * N, ks_bits, ks_l, var_ksk)
    return out


def tfhe_failure_prob_log2(var_in: float, n: int, N: int, p: int) -> float:
    """log2 P[PBS decodes the wrong box] for input phase variance var_in (torus units).

    Error before blind rotation = input noise + mod-switch noise; the margin
    is half a box, 1/(4p) with one padding bit.
    """
    tot = Noise(var_in) + tfhe_ms(n, N)
    return failure_prob_log2(tot, 1.0 / (4 * p))
