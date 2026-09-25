# TOY: not secure
"""Shared helpers for falsifier scripts: independent re-parsing of raw crbench logs."""
from __future__ import annotations

import glob
import json
import os
import re
import sys

PROJ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(PROJ, "..", ".."))
sys.path[:0] = [os.path.join(PROJ, "code"), os.path.join(REPO, "lib/bench"), os.path.join(REPO, "lib/cryptomath")]


def raw_samples(exp: str, arm: str) -> list[float]:
    """Re-read every non-warm-up execution log of an arm; return seconds per S-box evaluation."""
    out = []
    for p in sorted(glob.glob(os.path.join(PROJ, "results", exp, arm, "r*.log"))):
        if "warmup" in p:
            continue
        t = open(p).read()
        if not re.search(r"^# rc=0 ", t, re.M):
            continue
        m = re.search(r"^sbox_eval time: ([0-9.]+) ms", t, re.M)
        if m:
            out.append(float(m.group(1)) / 1e3)
    return out


def result_kv(exp: str, arm: str) -> dict:
    """RESULT name=... k=v lines of a single-execution experiment -> {name: {k: v}}."""
    d = {}
    for p in glob.glob(os.path.join(PROJ, "results", exp, arm, "r*.log")):
        for line in open(p):
            if line.startswith("RESULT"):
                kv = dict(re.findall(r"(\w+)=(\S+)", line))
                d[kv.pop("name")] = kv
    return d


def verdict(claim: str, status: str, reason: str) -> None:
    print(json.dumps({"claim": claim, "verdict": status, "reason": reason}))
