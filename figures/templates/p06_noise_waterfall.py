#!/usr/bin/env python3
"""P06 -- noise-budget waterfall across a homomorphic circuit.

Pattern: x = operations in execution order; each floating bar shows the bits
of budget one operation consumes (length = cost); a thin connector joins the
running total; the zero line is labelled "decryption fails"; a refresh step
(bootstrapping) is the only bar going up and uses the accent colour.
SYNTHETIC DATA.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def make(venue="lncs", outdir=ROOT / "examples"):
    ops = ["fresh", "Mult", "Rot", "Mult", "Add", "Mult", "Boot", "Mult", "Mult", "Rot"]
    delta = [0, -22, -3, -21, -1, -22, +52, -22, -21, -3]
    start = 80.0
    fig, ax = P.figure(venue, width="full", aspect=0.40)
    level = start
    xs = np.arange(len(ops))
    tops = []
    for i, (op, d) in enumerate(zip(ops, delta)):
        if i == 0:
            ax.bar(i, start, 0.6, color=P.BASELINE_GREYS[1])
            new = start
        else:
            new = level + d
            lo, hi = sorted((level, new))
            c = P.ACCENT if d > 0 else P.OURS
            ax.bar(i, hi - lo, 0.6, bottom=lo, color=c)
            ax.plot([i - 1 + 0.3, i - 0.3], [level, level], color=P.INK_MUTED, lw=0.6)
            ax.text(i, hi + 1.5, f"${d:+d}$", ha="center", va="bottom", fontsize="x-small", color=P.INK_2)
        level = new
        tops.append(level)
    ax.axhline(0, color=P.CATEGORICAL[7], lw=0.9)
    ax.text(len(ops) - 0.5, 0, "decryption fails below 0 ", ha="right", va="bottom", fontsize="small")
    ax.set_xticks(xs, ops)
    ax.tick_params(axis="x", length=0)
    ax.set_ylabel("noise budget (bits)")
    ax.set_ylim(-5, start + 12)
    ax.set_xlim(-0.6, len(ops) - 0.4)
    return P.save(fig, "p06_noise_waterfall", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
