# TOY: not secure
"""Falsifier check of C4 (measured speed-up of MV-PBS over per-bit PBS for the full 4-bit
S-box at T1 lies in [3, 4)).  Numeric recomputation from raw logs (attack step 4):
same configuration for both arms, interleaved, correct outputs, CI inside the stated range.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import glob
import os
import re

from _common import PROJ, raw_samples, verdict
from crbench import stats

pb, mv = raw_samples("bench_T1_k4", "perbit"), raw_samples("bench_T1_k4", "mvpbs")
cfg = {a: re.sub(r"--method \w+", "", open(os.path.join(PROJ, "results/bench_T1_k4", a, "r001.log")).read().split("\n")[1])
       for a in ("perbit", "mvpbs")}
same_cfg = cfg["perbit"] == cfg["mvpbs"]
ok_out = all("correct=64 total=64" in open(p).read()
             for p in glob.glob(os.path.join(PROJ, "results/bench_T1_k4", "*", "r*.log")) if "vpack" not in p)
sp = stats.speedup(pb, mv, paired=len(pb) == len(mv))
print(f"n={len(pb)}/{len(mv)} same_config={same_cfg} all_outputs_correct={ok_out} speedup={sp.fmt(2)}")
if same_cfg and ok_out and 3 <= sp.ci_low and sp.ci_high < 4:
    verdict("C4", "survived", f"recomputed {sp.fmt(2)} from raw logs; inside [3,4)")
else:
    verdict("C4", "weakened" if same_cfg and ok_out else "refuted", f"recomputed {sp.fmt(2)}")
