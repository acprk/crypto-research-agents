# TOY: not secure
"""Falsifier attack on C1 (MV-PBS correctness at T1).

Attack order (skills/falsify): definitions -> quantifiers -> edge parameters -> numerics.
  * 3 independent key seeds x all 16 inputs x 4 output bits (exhaustive over inputs);
  * edge LUTs: constant 0, constant 1, and the alternating Boolean LUT that maximises
    ||d_f||^2 = 18 (Lemma L2), plus f(0)=f(15)=1 (d_0 = 2, the only coefficient of size 2);
  * the largest-norm LUT set evaluated together in one MV-PBS call.
Prints one line per attack and a JSON verdict.  Runtime ~15 s.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _common import verdict
from sbox_fhe import PARAMS, P_IN, PRESENT_SBOX, TFHE, bit_luts, d_norm2, mv_pbs

bad = total = 0
for seed in (101, 202, 303):
    tf = TFHE(PARAMS["T1"], seed=seed)
    fs = bit_luts()
    for m in range(16):
        outs = mv_pbs(tf, tf.encrypt(m, P_IN), fs)
        for i, o in enumerate(outs):
            total += 1
            bad += tf.decrypt(o, P_IN) != fs[i](m)
print(f"exhaustive inputs x 3 key seeds: {total - bad}/{total} output bits correct")

edge = {"const0": lambda m: 0, "const1": lambda m: 1,
        "max_norm(norm2=18)": lambda m: 1 if m in (0, 15) else int(m % 2 == 0),
        "alt_0101": lambda m: m % 2}
tf = TFHE(PARAMS["T1"], seed=404)
names, fs = list(edge), list(edge.values())
print("edge LUT norms:", {n: d_norm2(f, tf.P.N, P_IN) for n, f in edge.items()})
ebad = etot = 0
for m in range(16):
    outs = mv_pbs(tf, tf.encrypt(m, P_IN), fs)
    for n, f, o in zip(names, fs, outs):
        etot += 1
        ebad += tf.decrypt(o, P_IN) != int(f(m))
print(f"edge LUTs in one MV-PBS call: {etot - ebad}/{etot} correct")
if bad or ebad:
    verdict("C1", "refuted", f"{bad + ebad} wrong outputs")
else:
    verdict("C1", "survived", f"could not refute: {total + etot} outputs correct incl. max-norm edge LUTs")
