# TOY: not secure
"""P5 driver (owner: experimenter).  Runs every experiment through crbench and writes logs.

    cd case-study/toy-mvpbs && /usr/bin/python3 code/run_experiments.py          # ~2.5 min
    /usr/bin/python3 code/run_experiments.py --only bench_T1_k4                   # one experiment
    /usr/bin/python3 code/run_experiments.py --quick     # smoke test (~1 min) -> results-quick/, not results/

Experiments (each -> results/<name>/{run.json, <arm>/r*.log, summary.log}):

  bench_T1_k4     perbit vs mvpbs vs vpack, all 16 inputs, k=4, 5 interleaved rounds (+1 warm-up)
  bench_T1_kscan  perbit vs mvpbs for k=1..4 output bits, 4 inputs, 5 interleaved rounds (+1)
  noise_T1        phase errors of all 4 outputs, 48 trials per method (correctness at T1)
  noise_T2        same at the noisy set T2, 128 trials per method (failure rates)

Timing metric: process CPU time of the homomorphic evaluation only (the machine is shared;
see DECISIONS.md D3); wall time is in every per-execution log as `sbox_wall elapsed`.

Protocol (skills/bench-protocol): interleaved rounds with rotating arm order, medians,
bootstrap CIs from crbench.stats, OMP/BLAS threads = 1, env captured in run.json.
Afterwards every file under results/ is sanitised (home dir -> ~, hostname -> host).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import sbox_fhe  # noqa: E402,F401  (puts lib/ on sys.path)
from crbench import stats  # noqa: E402
from crbench.runner import run_interleaved  # noqa: E402

PY = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
RES = os.path.join(PROJ, "results")

# keep the environment capture free of unrelated private paths
os.environ.pop("LD_LIBRARY_PATH", None)


def fresh_dir(d):
    """Move a previous run of the same experiment out of the way (to a temp dir, not deleted)."""
    if os.path.exists(d):
        shutil.move(d, tempfile.mkdtemp(prefix="old_" + os.path.basename(d) + "_"))


def bench(name, arms, repeats, warmup, quick):
    if quick:
        repeats, warmup = 3, 0
    d = os.path.join(RES, name)
    fresh_dir(d)
    r = run_interleaved(arms, repeats=repeats, warmup=warmup, order="alternate", parser="generic",
                        metric="time", label="sbox_eval", log_dir=os.path.relpath(d, PROJ),
                        threads=1, cwd=PROJ, target_dir=PROJ, verbose=True)
    return r, d


def write_summary(d, lines):
    with open(os.path.join(d, "summary.log"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def exp_bench_k4(quick):
    arms = {m: f"{PY} code/bench_sbox.py --method {m} --k 4 --params T1 --inputs 16"
            for m in ("perbit", "mvpbs", "vpack")}
    r, d = bench("bench_T1_k4", arms, 5, 1, quick)
    s = r.summary()
    out = ["# bench_T1_k4: time of ONE 4-bit S-box evaluation (4 output-bit ciphertexts), toy Python, T1",
           f"# rounds={r.repeats} warmup={r.warmup} order={r.order} threads=1 started={r.started}"]
    for a in arms:
        x = s[a]
        out.append(f"{a:7s} median_ms={1e3 * x['median']:.1f} iqr_ms={1e3 * x['iqr']:.1f} "
                   f"ci95_ms=[{1e3 * x['ci_low']:.1f},{1e3 * x['ci_high']:.1f}] n={x['n']} failures={x['failures']}")
    for base, cand in (("perbit", "mvpbs"), ("perbit", "vpack"), ("mvpbs", "vpack")):
        sp = stats.speedup(r.samples(base), r.samples(cand), paired=True)
        out.append(f"speedup {cand}_vs_{base} = {sp.fmt(2)}  (median ratio, paired bootstrap 95% CI)")
    write_summary(d, out)


def exp_kscan(quick):
    arms = {}
    for k in range(1, 5):
        arms[f"perbit_k{k}"] = f"{PY} code/bench_sbox.py --method perbit --k {k} --params T1 --inputs 4"
        arms[f"mvpbs_k{k}"] = f"{PY} code/bench_sbox.py --method mvpbs --k {k} --params T1 --inputs 4"
    r, d = bench("bench_T1_kscan", arms, 5, 1, quick)
    s = r.summary()
    out = ["# bench_T1_kscan: per-bit PBS vs MV-PBS for k = 1..4 output bits, toy Python, T1, 4 inputs, CPU time",
           f"# rounds={r.repeats} warmup={r.warmup} order={r.order} threads=1 started={r.started}"]
    for k in range(1, 5):
        pb, mv = f"perbit_k{k}", f"mvpbs_k{k}"
        sp = stats.speedup(r.samples(pb), r.samples(mv), paired=True)
        out.append(f"k={k} perbit_median_ms={1e3 * s[pb]['median']:.1f} mvpbs_median_ms={1e3 * s[mv]['median']:.1f} "
                   f"speedup={sp.fmt(2)} ideal={k}")
    write_summary(d, out)


def exp_noise(params, trials, quick):
    if quick:
        trials = 16
    name = f"noise_{params}"
    d = os.path.join(RES, name)
    fresh_dir(d)
    arms = {m: f"{PY} code/noise_experiment.py --method {m} --params {params} --trials {trials}"
            for m in ("perbit", "mvpbs")}
    r = run_interleaved(arms, repeats=1, warmup=0, log_dir=os.path.relpath(d, PROJ), threads=1,
                        cwd=PROJ, target_dir=PROJ, verbose=True)
    out = [f"# {name}: phase error of each output-bit ciphertext; margin 2^-6; trials={trials} per method"]
    for a in arms:
        ex = [e for e in r.executions if e.arm == a][0]
        text = open(os.path.join(PROJ, ex.log)).read()
        for line in text.splitlines():
            if line.startswith("RESULT"):
                body = line[len("RESULT "):]
                m = re.search(r"sbox_fails=(\d+) n=(\d+)", body)
                if m:
                    c, n = int(m.group(1)), int(m.group(2))
                    lo, hi = wilson(c, n)
                    body += f" rate={c / n:.3f} wilson95=[{lo:.3f},{hi:.3f}]"
                out.append(body)
    write_summary(d, out)


def wilson(c, n, z=1.96):
    p = c / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def sanitise(root):
    home = os.path.expanduser("~")
    host = platform.node()
    user = os.path.basename(home)
    for dp, _dn, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                t = open(p).read()
            except UnicodeDecodeError:
                continue
            u = t.replace(home, "~")
            if host:
                u = u.replace(host, "host")
            u = re.sub(rf"\b{re.escape(user)}@", "user@", u)
            if u != t:
                open(p, "w").write(u)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--sanitise-only", action="store_true", help="only scrub results/ (after falsify runs)")
    a = ap.parse_args()
    global RES
    if a.quick:  # smoke test: never overwrite the evidence in results/
        RES = os.path.join(PROJ, "results-quick")
    if a.sanitise_only:
        sanitise(RES)
        return
    os.chdir(PROJ)  # log paths in run.json are relative to the project
    os.makedirs(RES, exist_ok=True)
    todo = {"bench_T1_k4": lambda: exp_bench_k4(a.quick),
            "bench_T1_kscan": lambda: exp_kscan(a.quick),
            "noise_T1": lambda: exp_noise("T1", 48, a.quick),
            "noise_T2": lambda: exp_noise("T2", 128, a.quick)}
    for name, fn in todo.items():
        if a.only and name != a.only:
            continue
        fn()
    sanitise(RES)


if __name__ == "__main__":
    main()
