# TOY: not secure
"""Falsifier attack on C3: "since MV-PBS replaces k blind rotations by one, its speed-up over
per-bit PBS is at least 0.9 k for every number of LUTs k in {1, ..., 64}".

Kill switch: for some k the upper end of the paired-bootstrap 95% CI of the speed-up is below
0.9 k.  Attack step 3 (edge parameters): the proposer only measured k <= 4; the falsifier
goes to the LARGEST k in the claimed range (k = 64: the 4 S-box bits + 60 random Boolean LUTs
of the same nibble), where the per-LUT post-processing (integer polynomial product, sample
extraction, key switch) can no longer hide behind the single blind rotation.

    /usr/bin/python3 falsify/C3_linear_speedup/check_linear_speedup.py          (~35 s)
    ... --reuse    (skip the crbench run if results/falsify_C3_k64/run.json exists)
Writes results/falsify_C3_k64/{run.json, <arm>/r*.log, summary.log}.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _common import PROJ, raw_samples, verdict  # noqa: E402
from crbench import stats  # noqa: E402
from crbench.runner import run_interleaved  # noqa: E402

os.environ.pop("LD_LIBRARY_PATH", None)
os.chdir(PROJ)
PY = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
EXP = "results/falsify_C3_k64"
if not ("--reuse" in sys.argv and os.path.exists(os.path.join(EXP, "run.json"))):
    if os.path.exists(EXP):
        shutil.move(EXP, tempfile.mkdtemp(prefix="old_falsify_C3_"))
    arms = {f"{m}_k64": f"{PY} code/bench_sbox.py --method {m} --k 64 --params T1 --inputs 1"
            for m in ("perbit", "mvpbs")}
    run_interleaved(arms, repeats=5, warmup=0, order="alternate", parser="generic", metric="time",
                    label="sbox_eval", log_dir=EXP, threads=1, cwd=PROJ, target_dir=PROJ)

lines = ["# falsify_C3_k64 + bench_T1_kscan re-parsed from raw logs; claim: speedup >= 0.9 k"]
bad = []
for exp, k in [("bench_T1_kscan", 1), ("bench_T1_kscan", 2), ("bench_T1_kscan", 3), ("bench_T1_kscan", 4),
               ("falsify_C3_k64", 64)]:
    pb, mv = raw_samples(exp, f"perbit_k{k}"), raw_samples(exp, f"mvpbs_k{k}")
    sp = stats.speedup(pb, mv, paired=len(pb) == len(mv))
    flag = sp.ci_high < 0.9 * k
    bad += [k] if flag else []
    lines.append(f"k={k}: perbit_median_ms={1e3 * stats.median(pb):.1f} mvpbs_median_ms={1e3 * stats.median(mv):.1f} "
                 f"speedup={sp.fmt(2)} claimed>={0.9 * k:.1f} {'VIOLATED' if flag else 'ok'}")
with open(os.path.join(EXP, "summary.log"), "w") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
if bad:
    verdict("C3", "refuted", f"speed-up CI entirely below 0.9k for k in {bad}: per-LUT post-processing "
            "does not amortise; the speed-up saturates (Amdahl)")
else:
    verdict("C3", "survived", "could not refute")
