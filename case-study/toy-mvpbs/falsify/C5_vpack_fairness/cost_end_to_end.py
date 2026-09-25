# TOY: not secure
"""Falsifier attack on C5 ("the CMux-tree / vertical-packing S-box is >= 5x faster than
MV-PBS") -- attack step 3 of skills/falsify: baseline fairness.

The measured vpack arm starts from GGSW encryptions of the 4 input bits, whereas perbit and
mvpbs start from ONE LWE encryption of the nibble.  In an LWE-in/LWE-out pipeline the vpack
arm must first (a) extract the 4 input bits (>= 1 blind rotation, e.g. by MV-PBS) and (b) turn
each bit LWE into a GGSW (circuit bootstrapping, CGGI: l_cb >= 1 PBS per bit).  We price that
LOWER BOUND with measured medians from the same run: bit extraction = one MV-PBS (t_mv),
one circuit bootstrap >= l_cb full PBS, one PBS = t_perbit / 4.  Also prints exact operation counts via
cryptomath.costmodel.Counter.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from _common import raw_samples, verdict
from crbench import stats
from cryptomath.costmodel.counter import CMUX, KS, PBS, Counter
from sbox_fhe import PARAMS, TFHE, evaluate

tf = TFHE(PARAMS["T1"], seed=5)
for method in ("perbit", "mvpbs", "vpack"):
    with Counter() as c:
        evaluate(method, tf, 7)
    print(f"{method:7s} op counts per S-box (as measured, LWE vs GGSW input): {dict(c.counts)}")

t_mv = stats.median(raw_samples("bench_T1_k4", "mvpbs"))
t_vp = stats.median(raw_samples("bench_T1_k4", "vpack"))
t_pbs = stats.median(raw_samples("bench_T1_k4", "perbit")) / 4
print(f"measured medians: mvpbs {1e3 * t_mv:.1f} ms, vpack {1e3 * t_vp:.1f} ms, raw ratio {t_mv / t_vp:.1f}x")
for l_cb in (1, 2, 3):
    t_e2e = t_mv + 4 * l_cb * t_pbs + t_vp   # extract bits + 4 circuit bootstraps + CMux tree
    print(f"l_cb={l_cb}: end-to-end vpack >= {1e3 * t_e2e:.0f} ms  => ratio vs mvpbs <= {t_mv / t_e2e:.2f}x")
verdict("C5", "refuted", "raw ratio compares different input formats; with even the cheapest "
        "LWE->GGSW conversion (l_cb=1) vpack is slower than MV-PBS end-to-end")
