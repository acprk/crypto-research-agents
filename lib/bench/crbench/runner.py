"""Interleaved A/B/... subprocess runner.

Why interleave?  Machine state drifts (thermal, co-tenants, page cache, turbo).
Running all A then all B lets drift masquerade as a speed-up.  We therefore run
*rounds*; each round runs every arm once, and the arm order rotates between rounds
(``alternate``: A B C / B C A / C A B ...) or is shuffled with a fixed seed.

Every single execution writes its full stdout/stderr to ``log_dir/<arm>/r<k>.log``
with a header (command, round, time, return code), and the whole run is saved as
``log_dir/run.json`` -- these are the files EVIDENCE.md rows point at.
"""
from __future__ import annotations

import json
import os
import random
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Sequence

from . import stats
from .envcapture import capture_env, warn_env
from .lock import BenchLock
from .parsers import parse_text

THREAD_VARS = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS", "GOMAXPROCS")


@dataclass
class Execution:
    arm: str
    round: int
    warmup: bool
    returncode: int
    wall: float
    value: float | None
    log: str | None
    error: str = ""


@dataclass
class RunResult:
    arms: dict[str, str]
    order: str
    repeats: int
    warmup: int
    metric: str
    executions: list[Execution] = field(default_factory=list)
    env: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    started: str = ""
    finished: str = ""

    def samples(self, arm: str) -> list[float]:
        return [e.value for e in self.executions if e.arm == arm and not e.warmup and e.value is not None and e.returncode == 0]

    def failures(self, arm: str | None = None) -> list[Execution]:
        return [e for e in self.executions if (arm is None or e.arm == arm) and (e.returncode != 0 or e.value is None)]

    def summary(self) -> dict:
        out = {}
        for a in self.arms:
            s = self.samples(a)
            out[a] = stats.summarize(s).to_dict() if s else {"n": 0}
            out[a]["failures"] = len(self.failures(a))
        return out

    def speedups(self, baseline: str) -> dict:
        base = self.samples(baseline)
        res = {}
        for a in self.arms:
            if a == baseline:
                continue
            s = self.samples(a)
            if base and s:
                paired = len(base) == len(s)
                res[a] = stats.speedup(base, s, paired=paired).to_dict()
        return res

    def to_dict(self) -> dict:
        d = asdict(self)
        d["summary"] = self.summary()
        return d

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


def round_order(arms: Sequence[str], r: int, order: str, rng: random.Random) -> list[str]:
    arms = list(arms)
    if order == "fixed":
        return arms
    if order == "alternate":
        k = r % len(arms)
        return arms[k:] + arms[:k]
    if order == "shuffle":
        rng.shuffle(arms)
        return arms
    raise ValueError(f"unknown order {order!r} (fixed|alternate|shuffle)")


def _prefix(cpus: str | None) -> list[str]:
    if not cpus:
        return []
    if sys.platform.startswith("linux"):
        return ["taskset", "-c", cpus]
    return []  # pragma: no cover - pinning unsupported, recorded as warning by caller


def stale_build_check(binary: str, sources: Sequence[str], exts=(".c", ".cc", ".cpp", ".h", ".hpp", ".rs", ".go", ".toml", ".txt")) -> list[str]:
    """Return source files newer than ``binary``.  Non-empty => rebuild before benchmarking."""
    if not os.path.exists(binary):
        return [f"<missing binary {binary}>"]
    t = os.path.getmtime(binary)
    newer = []
    for src in sources:
        for root, _dirs, files in os.walk(src) if os.path.isdir(src) else [(os.path.dirname(src), [], [os.path.basename(src)])]:
            for fn in files:
                if fn.endswith(exts):
                    p = os.path.join(root, fn)
                    if os.path.getmtime(p) > t:
                        newer.append(p)
    return newer


def run_interleaved(
    arms: dict[str, str | Sequence[str]],
    repeats: int = 5,
    warmup: int = 1,
    order: str = "alternate",
    parser: str | None = None,
    metric: str = "time",
    label: str | None = None,
    reduce: str = "first",
    extract: Callable[[str], float | None] | None = None,
    log_dir: str | None = None,
    timeout: float | None = None,
    threads: int | None = None,
    cpus: str | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    use_lock: bool = True,
    lock_path: str | None = None,
    target_dir: str | None = None,
    seed: int = 0,
    shell: bool | None = None,
    verbose: bool = False,
) -> RunResult:
    """Run each arm ``warmup + repeats`` times in interleaved rounds.

    Value per execution: if ``extract`` is given, ``extract(output)``; elif ``parser`` is
    given, the ``metric`` record(s) (optionally filtered by ``label``) reduced by
    ``reduce`` in {first,last,sum,median}; else the wall-clock time of the subprocess.
    A non-zero return code or a missing metric marks the execution as failed; it is kept
    in the ledger (never silently dropped) but excluded from statistics.
    """
    if repeats < 1:
        raise ValueError("repeats must be >= 1")
    rng = random.Random(seed)
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    if threads is not None:
        for v in THREAD_VARS:
            run_env[v] = str(threads)
    res = RunResult(arms={k: (v if isinstance(v, str) else shlex.join(v)) for k, v in arms.items()},
                    order=order, repeats=repeats, warmup=warmup,
                    metric=("wall" if parser is None and extract is None else metric))
    res.env = capture_env(target_dir)
    res.env["bench"] = {"threads": threads, "cpus": cpus, "order": order, "seed": seed}
    res.warnings = warn_env(res.env)
    if cpus and not sys.platform.startswith("linux"):
        res.warnings.append("CPU pinning requested but unsupported on this platform")

    lock = BenchLock(lock_path, label=",".join(arms)) if (use_lock and lock_path) else (BenchLock(label=",".join(arms)) if use_lock else None)
    if lock:
        lock.acquire()
    res.started = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    try:
        for r in range(warmup + repeats):
            is_warm = r < warmup
            for arm in round_order(list(arms), r, order, rng):
                cmd = arms[arm]
                use_shell = isinstance(cmd, str) if shell is None else shell
                argv = cmd if use_shell else list(cmd) if not isinstance(cmd, str) else shlex.split(cmd)
                if cpus:
                    pre = _prefix(cpus)
                    argv = (shlex.join(pre) + " " + argv) if use_shell and pre else pre + list(argv)
                t0 = time.perf_counter()
                err = ""
                try:
                    p = subprocess.run(argv, shell=use_shell, capture_output=True, text=True, env=run_env, cwd=cwd, timeout=timeout)
                    rc, out = p.returncode, (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
                except subprocess.TimeoutExpired as e:
                    rc, out, err = -9, (e.stdout or "") if isinstance(e.stdout, str) else "", f"timeout after {timeout}s"
                wall = time.perf_counter() - t0
                value: float | None
                if extract is not None:
                    value = extract(out)
                elif parser is not None:
                    recs = [x for x in parse_text(out, parser) if x.metric == metric and (label is None or x.label == label)]
                    vals = [float(x.value) for x in recs]
                    if not vals:
                        value, err = None, err or f"metric {metric!r} not found in output"
                    elif reduce == "first":
                        value = vals[0]
                    elif reduce == "last":
                        value = vals[-1]
                    elif reduce == "sum":
                        value = sum(vals)
                    elif reduce == "median":
                        value = stats.median(vals)
                    else:
                        raise ValueError(f"unknown reduce {reduce!r}")
                else:
                    value = wall
                if rc != 0 and not err:
                    err = f"exit code {rc}"
                log_path = None
                if log_dir:
                    d = os.path.join(log_dir, arm)
                    os.makedirs(d, exist_ok=True)
                    log_path = os.path.join(d, f"r{r:03d}{'_warmup' if is_warm else ''}.log")
                    with open(log_path, "w") as f:
                        f.write(f"# crbench arm={arm} round={r} warmup={is_warm}\n# cmd: {res.arms[arm]}\n"
                                f"# rc={rc} wall={wall:.6f}s value={value} error={err}\n# ---\n{out}")
                res.executions.append(Execution(arm, r, is_warm, rc, wall, value, log_path, err))
                if verbose:
                    print(f"[round {r}{' warmup' if is_warm else ''}] {arm}: value={value} rc={rc} {err}", file=sys.stderr)
    finally:
        res.finished = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        if lock:
            lock.release()
    if log_dir:
        res.save(os.path.join(log_dir, "run.json"))
    return res


def load_run(path: str) -> RunResult:
    with open(path) as f:
        d = json.load(f)
    d.pop("summary", None)
    ex = [Execution(**e) for e in d.pop("executions")]
    r = RunResult(**d)
    r.executions = ex
    return r


if __name__ == "__main__":
    py = shlex.quote(sys.executable)
    r = run_interleaved({"A": f"{py} -c 'print(\"time: 2 ms\")'", "B": f"{py} -c 'print(\"time: 1 ms\")'"},
                        repeats=3, warmup=1, parser="generic", use_lock=False)
    print(json.dumps(r.summary(), indent=1))
    print(r.speedups("A"))
