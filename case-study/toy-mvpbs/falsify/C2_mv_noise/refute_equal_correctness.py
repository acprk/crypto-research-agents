# TOY: not secure
"""Falsifier attack on C2 ("MV-PBS gives the 4 output bits with ONE blind rotation and the
same correctness as per-bit PBS").  Kill switch: at some admissible toy parameter set the
S-box failure rate of MV-PBS is significantly higher than that of per-bit PBS.

Reads the raw logs of results/noise_T2 (produced by code/run_experiments.py; the noise
experiment itself is the constructive part of this attack) and compares failure counts
with Wilson 95% intervals.  Also checks the model (THEORY T1) against the measured std.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import math

from _common import result_kv, verdict


def wilson(c, n, z=1.96):
    p = c / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


pb, mv = result_kv("noise_T2", "perbit"), result_kv("noise_T2", "mvpbs")
rows = []
for k in range(1, 5):
    a, b = pb[f"perbit_k{k}"], mv[f"mvpbs_k{k}"]
    ca, cb, n = int(a["sbox_fails"]), int(b["sbox_fails"]), int(a["n"])
    la, ha = wilson(ca, n)
    lb, hb = wilson(cb, n)
    rows.append((k, ca, cb, n, ha, lb))
    print(f"k={k}: per-bit {ca}/{n} [{la:.3f},{ha:.3f}]   MV-PBS {cb}/{n} [{lb:.3f},{hb:.3f}]")
for i in range(4):
    b = mv[f"mvpbs_bit{i}"]
    print(f"bit {i}: norm2={b['norm2']} measured std 2^{b['std_log2']} vs model 2^{b['pred_std_log2']}")
sep = [k for k, ca, cb, n, ha, lb in rows if lb > ha]
if sep:
    verdict("C2", "weakened", f"MV-PBS failure CI above per-bit CI for k in {sep} at T2; "
            "same-correctness holds only when ||d_i||^2 * Var_BR + Var_KS fits the margin")
else:
    verdict("C2", "survived", "no significant difference at T2")
