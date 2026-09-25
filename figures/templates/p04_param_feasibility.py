#!/usr/bin/env python3
"""P04 -- parameter-plane feasibility region.

Pattern: x = ring dimension n (log2), y = modulus size log2 q.  Upper
constraint: security (log q must stay below the lambda-bit curve); lower
constraint: correctness (enough modulus for depth L).  The feasible set is a
light tint between them; the chosen parameter is a single marked point with a
label.  Security curves are labelled in-line.  TOY SECURITY MODEL -- replace
by lattice-estimator output before publishing.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def toy_max_logq(n, lam):
    # TOY: log q_max grows ~linearly in n and ~1/lambda (shape only, not a real estimate)
    return n * 3.5 / lam


def make(venue="lncs", outdir=ROOT / "examples"):
    logn = np.linspace(10, 16, 200)
    n = 2 ** logn
    fig, ax = P.figure(venue, width="full", aspect=0.45)
    need = 60 + 40 * 12      # toy: base + bits per level * depth
    sec128 = toy_max_logq(n, 128)
    ax.fill_between(logn, need, sec128, where=sec128 >= need, color=P.FEASIBLE, lw=0, label="feasible")
    for lam, ls in [(80, (0, (1, 1.5))), (128, "-"), (192, (0, (4, 2)))]:
        y = toy_max_logq(n, lam)
        ax.plot(logn, y, color=P.INK_2 if lam != 128 else P.OURS_DARK, lw=0.9, linestyle=ls)
        k = np.searchsorted(y, 1500)
        k = min(k, len(logn) - 1)
        ax.text(logn[k], y[k], rf" $\lambda={lam}$", color=P.INK_2, fontsize="small", va="bottom", ha="left",
                rotation=0)
    ax.axhline(need, color=P.CATEGORICAL[7], lw=0.9)
    ax.text(10.05, need, " correctness: depth $L=12$", va="bottom", fontsize="small", color=P.INK)
    ax.plot([15], [need + 180], marker="*", ms=9, color=P.ACCENT, mec="white", mew=0.6, zorder=5)
    ax.annotate("chosen set", (15, need + 180), xytext=(8, -3), textcoords="offset points", ha="left", va="top",
                fontsize="small")
    ax.text(10.4, 1800, "insecure", color=P.INK_MUTED, fontsize="small", style="italic")
    ax.text(15.3, 250, "incorrect", color=P.INK_MUTED, fontsize="small", style="italic")
    ax.set_xticks(range(10, 17), [rf"$2^{{{k}}}$" for k in range(10, 17)])
    ax.set_xlabel(r"ring dimension $n$")
    ax.set_ylabel(r"$\log_2 q$")
    ax.set_xlim(10, 16)
    ax.set_ylim(0, 2000)
    return P.save(fig, "p04_param_feasibility", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
