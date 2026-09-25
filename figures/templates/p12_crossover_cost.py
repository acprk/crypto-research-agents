#!/usr/bin/env python3
"""P12 -- cost-model crossover: which algorithm wins where.

Pattern: two (or three) analytic cost curves over a parameter, the crossover
point marked and its x value printed, the background of each regime tinted
very lightly and labelled with the winner; optional measured points overlaid
as markers to show the model is calibrated.  SYNTHETIC MODEL.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def make(venue="lncs", outdir=ROOT / "examples"):
    d = np.linspace(2, 64, 400)
    cost_a = 2.0 * d + 6                    # e.g. linear number of key-switches
    cost_b = 4 * np.sqrt(d) * 2 + 9         # e.g. baby-step giant-step
    xc = d[np.argmin(np.abs(cost_a - cost_b))]
    fig, ax = P.figure(venue, width="full", aspect=0.42)
    ax.axvspan(d[0], xc, color=P.SEQ_ORANGE[0], lw=0, alpha=0.6)
    ax.axvspan(xc, d[-1], color=P.SEQ_BLUE[0], lw=0, alpha=0.6)
    ax.plot(d, cost_a, color=P.ACCENT, label="direct")
    ax.plot(d, cost_b, color=P.OURS, linestyle="--", label="BSGS")
    rng = np.random.default_rng(5)
    dm = np.array([4, 8, 16, 32, 48, 64])
    ax.plot(dm, 4 * np.sqrt(dm) * 2 + 9 + rng.normal(0, 1.0, dm.size), "o", color=P.OURS, ms=3.5,
            mec="white", mew=0.5, label="BSGS measured")
    ax.axvline(xc, color=P.INK_2, lw=0.6)
    ax.text(xc, ax.get_ylim()[1] * 0.97, f" crossover $d\\approx{xc:.0f}$", va="top", fontsize="small")
    ax.text((d[0] + xc) / 2, 6, "direct wins", ha="center", fontsize="small", color=P.INK_2)
    ax.text((xc + d[-1]) / 2, 6, "BSGS wins", ha="center", fontsize="small", color=P.INK_2)
    ax.set_xlabel("polynomial degree $d$")
    ax.set_ylabel("# key-switchings")
    ax.set_xlim(d[0], d[-1])
    ax.set_ylim(0, 140)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.9))
    return P.save(fig, "p12_crossover_cost", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
