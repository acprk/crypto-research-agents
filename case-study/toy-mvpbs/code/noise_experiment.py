# TOY: not secure
"""Noise / failure-rate experiment (one execution; called by crbench, see run_experiments.py).

    python3 code/noise_experiment.py --method mvpbs --params T2 --trials 192

For `trials` S-box evaluations (inputs cycle through 0..15) it records the signed
phase error of each of the 4 output-bit ciphertexts, then prints

    ERR <trial> <m> <bit> <error as a fraction of the torus>      (raw data)
    RESULT name=<method>_bit<i> std_log2=<empirical> pred_std_log2=<model> fails=<c> n=<t>
    RESULT name=<method>_k<k> sbox_fails=<c> n=<t>                 (any of the first k bits wrong)

Decoding margin for a bit encoded in Z_16 with one padding bit: 1/(4*16) = 2^-6.
Model (THEORY.md, Theorem T1): Var_out = ||d_i||^2 * Var_BR + Var_KS  for MV-PBS and
Var_BR + Var_KS for per-bit PBS; Var_BR, Var_KS from cryptomath.fhe.noise.
"""
from __future__ import annotations

import argparse
import math
import sys

import numpy as np

from sbox_fhe import (PARAMS, P_IN, PRESENT_SBOX, Q, TFHE, bit_luts, d_norm2, mv_pbs,
                      per_bit_pbs, phase_error)
from cryptomath.fhe import noise as NZ


def predicted_std(P, norm2: int) -> float:
    br = NZ.tfhe_blind_rotate(P.n, P.N, P.k, P.bg_bits, P.l, P.glwe_sigma ** 2).var
    ks = NZ.tfhe_keyswitch(P.k * P.N, P.ks_bits, P.ks_l, P.lwe_sigma ** 2).var
    return math.sqrt(norm2 * br + ks)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True, choices=["perbit", "mvpbs"])
    ap.add_argument("--params", default="T2", choices=sorted(PARAMS))
    ap.add_argument("--trials", type=int, default=192)
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args(argv)

    P = PARAMS[a.params]
    tf = TFHE(P, seed=a.seed)
    fs = bit_luts(PRESENT_SBOX, 4)
    fn = mv_pbs if a.method == "mvpbs" else per_bit_pbs
    margin = 1.0 / (4 * P_IN)
    errs = np.zeros((a.trials, 4))
    for t in range(a.trials):
        m = t % 16
        outs = fn(tf, tf.encrypt(m, P_IN), fs)
        for i, o in enumerate(outs):
            e = phase_error(tf, o, fs[i](m)) / Q
            errs[t, i] = e
            print(f"ERR {t} {m} {i} {e:+.6e}")
    wrong = np.abs(errs) >= margin
    print(f"# params={a.params} glwe_sigma=2^{math.log2(P.glwe_sigma):.2f} margin=2^{math.log2(margin):.0f}")
    for i in range(4):
        n2 = d_norm2(fs[i], P.N, P_IN) if a.method == "mvpbs" else 1
        print(f"RESULT name={a.method}_bit{i} std_log2={math.log2(errs[:, i].std()):.3f} "
              f"pred_std_log2={math.log2(predicted_std(P, n2)):.3f} norm2={n2} "
              f"fails={int(wrong[:, i].sum())} n={a.trials}")
    for k in range(1, 5):
        print(f"RESULT name={a.method}_k{k} sbox_fails={int(wrong[:, :k].any(axis=1).sum())} n={a.trials}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
