"""Environment capture: record everything needed to judge whether two numbers are comparable.

Captured: hostname hash (not the raw hostname, to keep ledgers shareable), OS/kernel,
CPU model/cores/flags summary (``lscpu``), memory, CPU governor, load average,
compiler versions, Python version, git commit + dirty flag of the target directory,
and a whitelist of performance-relevant environment variables.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time

PERF_ENV_VARS = (
    "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS",
    "GOMAXPROCS", "CC", "CXX", "CFLAGS", "CXXFLAGS", "LDFLAGS", "RUSTFLAGS",
    "LD_LIBRARY_PATH", "CARGO_PROFILE_RELEASE_LTO", "GOAMD64", "CRBENCH_LOCK",
)

COMPILERS = (
    ("gcc", ["gcc", "--version"]),
    ("g++", ["g++", "--version"]),
    ("clang", ["clang", "--version"]),
    ("rustc", ["rustc", "--version"]),
    ("cargo", ["cargo", "--version"]),
    ("go", ["go", "version"]),
    ("cmake", ["cmake", "--version"]),
    ("sage", ["sage", "--version"]),
    ("lean", ["lean", "--version"]),
)


def _run(cmd: list[str], cwd: str | None = None, timeout: float = 10.0) -> str | None:
    if shutil.which(cmd[0]) is None:
        return None
    try:
        out = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _first_line(s: str | None) -> str | None:
    return s.splitlines()[0].strip() if s else None


def cpu_info() -> dict:
    info: dict = {"machine": platform.machine(), "logical_cpus": os.cpu_count()}
    ls = _run(["lscpu"])
    if ls:
        for line in ls.splitlines():
            if ":" not in line:
                continue
            k, v = (t.strip() for t in line.split(":", 1))
            if k in ("Model name", "Socket(s)", "Core(s) per socket", "Thread(s) per core",
                     "CPU max MHz", "L3 cache", "NUMA node(s)"):
                info[k] = v
            if k == "Flags":
                flags = set(v.split())
                info["simd"] = sorted(f for f in flags if f.startswith(("avx", "sse4", "bmi", "adx", "sha", "aes", "vpclmul", "neon")))
    gov = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    if os.path.exists(gov):
        try:
            info["governor"] = open(gov).read().strip()
        except OSError:
            pass
    try:
        info["loadavg"] = list(os.getloadavg())
    except OSError:
        pass
    return info


def mem_info() -> dict:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return {"mem_total_kb": int(line.split()[1])}
    except OSError:
        pass
    return {}


def git_info(path: str | None) -> dict:
    if not path or not os.path.isdir(path):
        return {}
    commit = _run(["git", "rev-parse", "HEAD"], cwd=path)
    if commit is None:
        return {"git": None}
    dirty = _run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=path)
    describe = _run(["git", "describe", "--tags", "--always"], cwd=path)
    return {"git_commit": commit, "git_dirty": bool(dirty), "git_describe": describe}


def capture_env(target_dir: str | None = None, extra_vars: tuple[str, ...] = ()) -> dict:
    host = platform.node()
    env = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host_id": hashlib.sha256(host.encode()).hexdigest()[:12],
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "cpu": cpu_info(),
        **mem_info(),
        "compilers": {name: _first_line(_run(cmd)) for name, cmd in COMPILERS},
        "env": {k: os.environ[k] for k in PERF_ENV_VARS + tuple(extra_vars) if k in os.environ},
    }
    env["compilers"] = {k: v for k, v in env["compilers"].items() if v}
    if target_dir:
        env["target"] = {"dir_name": os.path.basename(os.path.abspath(target_dir)), **git_info(target_dir)}
    return env


def warn_env(env: dict) -> list[str]:
    """Human-readable warnings about conditions that make timings untrustworthy."""
    w = []
    cpu = env.get("cpu", {})
    if cpu.get("governor") not in (None, "performance"):
        w.append(f"CPU governor is '{cpu.get('governor')}', not 'performance' (frequency scaling adds noise)")
    la = cpu.get("loadavg")
    n = cpu.get("logical_cpus") or 1
    if la and la[0] > 0.25 * n:
        w.append(f"1-min load average {la[0]:.1f} > 25% of {n} CPUs: machine is busy")
    if env.get("target", {}).get("git_dirty"):
        w.append("target working tree is dirty: record the diff or commit before benchmarking")
    return w


if __name__ == "__main__":
    e = capture_env(os.getcwd())
    print(json.dumps(e, indent=2))
    for msg in warn_env(e):
        print("WARNING:", msg)
