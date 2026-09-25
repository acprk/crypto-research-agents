"""Adapter recipes: how to benchmark each public baseline with crbench.

These are *recipes*, not vendored code.  Each entry tells you which parser to use
and a typical command template (run from the baseline's build directory, see
``references/baselines/MANIFEST.md`` for fetch/pin/build).  ``{target}`` and
``{threads}`` are placeholders you fill in.

Fairness reminders printed by ``crbench adapters NAME`` come from the manifest's
fairness checklist: same parameters, same thread count, same compiler and flags,
same machine, interleaved rounds.
"""
from __future__ import annotations

ADAPTERS: dict[str, dict] = {
    "openfhe": {"parser": "openfhe", "cmd": "./bin/examples/pke/{target}",
                "notes": "Build with -DCMAKE_BUILD_TYPE=Release; WITH_NATIVEOPT only if the other arm is also -march=native. Library preset parameter sets may differ from those printed in papers -- print and record them."},
    "openfhe-gbench": {"parser": "gbench", "cmd": "./bin/benchmark/{target} --benchmark_repetitions=5 --benchmark_report_aggregates_only=true",
                       "notes": "Google-benchmark binaries; set OMP_NUM_THREADS explicitly."},
    "helib": {"parser": "helib", "cmd": "./bin/{target}",
              "notes": "Enable timers (setTimersOn) and printAllTimers; single-thread unless NTL threads are matched."},
    "seal": {"parser": "generic", "cmd": "./bin/sealbench --benchmark_filter={target}",
             "notes": "sealbench uses google-benchmark: use parser gbench if output is console table."},
    "lattigo": {"parser": "gobench", "cmd": "go test -run=^$ -bench={target} -benchtime=10x -count=5 ./...",
                "notes": "Set GOMAXPROCS to match the other arm."},
    "tfhe-rs": {"parser": "criterion", "cmd": "cargo bench --bench {target} -- --noplot",
                "notes": "RAYON_NUM_THREADS controls parallelism; compare single-thread vs single-thread first."},
    "tfhe-cpp": {"parser": "generic", "cmd": "./build/test/{target}", "notes": "Wrap in your own timing loop if no timer is printed."},
    "concrete": {"parser": "generic", "cmd": "python {target}.py", "notes": "Record compiler (optimizer) version; circuits are re-parameterised per program."},
    "lattice-estimator": {"parser": "lattice-estimator", "cmd": "sage -python {target}.py",
                          "notes": "Record estimator commit, cost model (e.g. MATZOV / ADPS16) and secret/error distributions."},
    "mp-spdz": {"parser": "mpspdz", "cmd": "Scripts/{target}.sh", "notes": "Report both time and communication; LAN vs WAN simulated with tc netem."},
    "emp-toolkit": {"parser": "generic", "cmd": "./bin/{target} 1 12345 & ./bin/{target} 2 12345", "notes": "Two-party: run both parties; measure on the slower one."},
    "apsi": {"parser": "generic", "cmd": "./bin/receiver_cli ...", "notes": "Server preprocessing vs online time must be reported separately."},
    "sat": {"parser": "sat", "cmd": "cadical {target}.cnf", "notes": "Fix the random seed; report solver version and the CNF hash."},
    "gnu-time": {"parser": "gnu-time", "cmd": "/usr/bin/time -v {target}", "notes": "Peak memory (max RSS)."},
}


def describe(name: str) -> str:
    a = ADAPTERS[name]
    return f"{name}: parser={a['parser']}\n  cmd:   {a['cmd']}\n  notes: {a['notes']}"


if __name__ == "__main__":
    for n in ADAPTERS:
        assert ADAPTERS[n]["parser"]
        print(describe(n))
