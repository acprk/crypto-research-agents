#!/usr/bin/env python3
# TOY: not secure
"""sage-check style numeric checks for THEORY.md (owner: theorist).  Pure Python + numpy.

    /usr/bin/python3 theory/check_mvpbs_noise.py      # ~10 s, one JSON line per statement

Statements (IDs match THEORY.md):
  L1  factorisation  T_f = v0 * d_f  (mod X^N+1, mod 2^32)  -- exhaustive over all Boolean f
      for p in {2,4,8} (N in {32,64,512}) and all 2^16 Boolean f for p = 16 (N = 64); random
      non-Boolean f for p = 16, N = 512.
  L2  max over Boolean f : Z_p -> {0,1} of ||d_f||_2^2 equals p + 2           (exhaustive)
  T1a if the accumulator noise has i.i.d. centred coefficients of variance V, then coefficient 0
      of d_f * e has variance ||d_f||^2 V                                       (Monte Carlo, 5%)
  T1b model prediction at T1/T2 for the PRESENT output bits (printed, used by THEORY.md)
Exit status 1 if any statement has a counterexample (so agents / CI notice).
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))
from sbox_fhe import PARAMS, P_IN, Q, bit_luts, d_norm2, d_poly, encode, negacyclic_mul_int, torus_mod, v0_poly  # noqa: E402
from cryptomath.fhe import noise as NZ  # noqa: E402


def test_poly(f, N, p):
    return torus_mod(np.array([encode(f(j * p // N), p) for j in range(N)], dtype=np.int64))


def check_L1():
    cases = 0
    for p, Ns in ((2, (32, 64, 512)), (4, (32, 64, 512)), (8, (32, 64, 512)), (16, (64,))):
        for N in Ns:
            v0 = v0_poly(N, p)
            for b in range(1 << p):
                f = lambda m, b=b: (b >> m) & 1  # noqa: E731
                if not np.array_equal(test_poly(f, N, p), negacyclic_mul_int(d_poly(f, N, p), v0)):
                    return {"id": "L1", "ok": False, "counterexample": {"p": p, "N": N, "f": b}}
                cases += 1
    rng = np.random.default_rng(1)
    for _ in range(200):
        t = rng.integers(0, 16, 16)
        f = lambda m, t=t: int(t[m])  # noqa: E731
        if not np.array_equal(test_poly(f, 512, 16), negacyclic_mul_int(d_poly(f, 512, 16), v0_poly(512, 16))):
            return {"id": "L1", "ok": False, "counterexample": {"table": t.tolist()}}
        cases += 1
    return {"id": "L1", "ok": True, "cases": cases}


def check_L2():
    res = {}
    for p in (2, 4, 8, 16):
        N = 4 * p
        res[p] = max(d_norm2(lambda m, b=b: (b >> m) & 1, N, p) for b in range(1 << p))
    ok = all(v == p + 2 for p, v in res.items())
    return {"id": "L2", "ok": ok, "max_norm2_by_p": res}


def check_T1a(trials=4000):
    rng = np.random.default_rng(2)
    N, out = 512, []
    for f in bit_luts():
        d = d_poly(f, N, P_IN)
        e = rng.normal(0, 1000.0, size=(trials, N)).round().astype(np.int64)
        c0 = np.array([negacyclic_mul_int(d, row)[0] for row in e])
        c0 = np.where(c0 >= Q // 2, c0 - Q, c0).astype(float)
        ratio = c0.var() / (np.dot(d, d) * 1000.0 ** 2)
        out.append(round(float(ratio), 3))
    return {"id": "T1a", "ok": all(abs(r - 1) < 0.05 for r in out), "empirical/predicted": out}


def check_T1b():
    rows = {}
    for name, P in PARAMS.items():
        br = NZ.tfhe_blind_rotate(P.n, P.N, P.k, P.bg_bits, P.l, P.glwe_sigma ** 2).var
        ks = NZ.tfhe_keyswitch(P.k * P.N, P.ks_bits, P.ks_l, P.lwe_sigma ** 2).var
        margin = 1.0 / (4 * P_IN)
        r = {"std_BR_log2": round(0.5 * math.log2(br), 2), "std_KS_log2": round(0.5 * math.log2(ks), 2)}
        for tag, n2s in (("perbit", [1] * 4), ("mvpbs", [d_norm2(f, P.N, P_IN) for f in bit_luts()])):
            fails = [math.erfc(margin / math.sqrt(2 * (n2 * br + ks))) for n2 in n2s]
            r[tag] = {"norm2": n2s,
                      "std_log2": [round(0.5 * math.log2(n2 * br + ks), 2) for n2 in n2s],
                      "p_fail_bit": [float(f"{x:.3g}") for x in fails],
                      "p_fail_sbox_indep": float(f"{1 - np.prod([1 - x for x in fails]):.3g}")}
        rows[name] = r
    return {"id": "T1b", "ok": True, "prediction": rows}


if __name__ == "__main__":
    results = [check_L1(), check_L2(), check_T1a(), check_T1b()]
    for r in results:
        print(json.dumps(r))
    sys.exit(0 if all(r["ok"] for r in results) else 1)
