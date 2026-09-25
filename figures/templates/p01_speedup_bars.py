#!/usr/bin/env python3
"""P01 -- speed-up bar chart with a baseline = 1 reference line.

Pattern: grouped bars of *ratios* (baseline time / method time) per parameter
set; the reference method is the horizontal line y = 1 (not a bar); ours is the
only saturated colour, other methods are greys; only our bars carry value labels;
the geometric mean is reported once.  SYNTHETIC DATA.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def make(venue="lncs", outdir=ROOT / "examples"):
    sets = ["Set I", "Set II", "Set III", "Set IV", "Set V"]
    rng = np.random.default_rng(1)
    prior_b = np.array([1.3, 1.1, 1.6, 1.4, 1.2])            # ratio vs. baseline A
    ours = np.array([2.1, 2.8, 3.4, 2.6, 4.1]) + rng.normal(0, 0.05, 5)
    fig, ax = P.figure(venue, width="full", aspect=0.42)
    x = np.arange(len(sets))
    w = 0.36
    ax.bar(x - w / 2, prior_b, w * 0.94, color=P.BASELINE_GREYS[2], label="Baseline B")
    bars = ax.bar(x + w / 2, ours, w * 0.94, color=P.OURS, label="Ours")
    ax.axhline(1.0, color=P.INK_2, lw=0.8, zorder=3)
    ax.text(len(sets) - 0.4, 1.03, "Baseline A", va="bottom", ha="left", color=P.INK_2, fontsize="small")
    for b, v in zip(bars, ours):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}" + r"$\times$", ha="center", va="bottom",
                fontsize="small", color=P.INK)
    gm = float(np.exp(np.log(ours).mean()))
    ax.set_title(f"geometric mean speed-up of ours: {gm:.2f}" + r"$\times$", loc="left", fontsize="small",
                 color=P.INK_2)
    ax.set_xticks(x, sets)
    ax.set_ylabel(r"speed-up over Baseline A ($\times$)")
    ax.set_ylim(0, ours.max() * 1.18)
    ax.set_xlim(-0.6, len(sets) + 0.15)
    ax.tick_params(axis="x", length=0)
    ax.legend(loc="upper left", ncols=2)
    return P.save(fig, "p01_speedup_bars", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
