#!/usr/bin/env python3
"""P05 -- trade-off scatter with Pareto front.

Pattern: two costs that are both "lower is better" (latency vs. key material);
every configuration is a dot; the Pareto front is a step line through the
non-dominated ones (coloured), dominated ones are grey; an arrow/inset text
says which corner is better; only a handful of named points are labelled.
SYNTHETIC DATA.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def pareto(xy):
    idx = np.argsort(xy[:, 0])
    front, best = [], np.inf
    for i in idx:
        if xy[i, 1] < best:
            front.append(i)
            best = xy[i, 1]
    return np.array(front)


def make(venue="lncs", outdir=ROOT / "examples"):
    rng = np.random.default_rng(7)
    k = rng.uniform(0.05, 1.0, 40)
    key = 2 ** (4 + 6 * k)                                # MB
    lat = 2 ** (7 - 5 * k + rng.normal(0, 0.6, k.size))   # ms
    xy = np.c_[key, lat]
    f = pareto(xy)
    dom = np.setdiff1d(np.arange(len(xy)), f)
    fig, ax = P.figure(venue, width="full", aspect=0.5)
    ax.scatter(key[dom], lat[dom], s=10, color=P.BASELINE_GREYS[2], label="dominated", zorder=2)
    fx, fy = key[f], lat[f]
    ax.step(fx, fy, where="post", color=P.OURS, lw=1.0, zorder=3)
    ax.scatter(fx, fy, s=18, color=P.OURS, edgecolor="white", linewidth=0.6, zorder=4, label="Pareto-optimal")
    for i, name in [(f[0], "small-key"), (f[len(f) // 2], "balanced"), (f[-1], "low-latency")]:
        ax.annotate(name, (key[i], lat[i]), xytext=(5, 5), textcoords="offset points", fontsize="small")
    ax.set_xscale("log", base=2)
    ax.set_yscale("log", base=2)
    ax.set_xlabel("evaluation-key size (MB)")
    ax.set_ylabel("latency (ms)")
    ax.annotate("better", xy=(0.04, 0.06), xytext=(0.16, 0.24), xycoords="axes fraction",
                arrowprops=dict(arrowstyle="->", color=P.INK_MUTED, lw=0.7), color=P.INK_MUTED, fontsize="small")
    ax.grid(axis="both")
    ax.legend(loc="upper right")
    return P.save(fig, "p05_pareto_tradeoff", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
