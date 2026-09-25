#!/usr/bin/env python3
"""P09 -- trail-probability bound vs. number of rounds (security margin).

Pattern: step plot of the proven lower bound on -log2(best trail probability)
(= weight) per round count for differential and linear trails; horizontal
line at the security level (key/state size); the first round that crosses it is
marked; the gap to the full cipher round count is the "security margin" bracket.
SYNTHETIC BOUNDS (shape only).
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def make(venue="lncs", outdir=ROOT / "examples"):
    r = np.arange(1, 17)
    active_d = np.array([1, 2, 5, 9, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56])
    active_l = np.array([1, 2, 4, 8, 11, 14, 18, 21, 25, 28, 32, 35, 39, 42, 46, 49])
    wd, wl = 2 * active_d, 2 * active_l        # toy: each active S-box costs >= 2 bits
    sec, full = 64, 16
    fig, ax = P.figure(venue, width="full", aspect=0.42)
    ax.step(r, wd, where="mid", color=P.OURS, marker="o", ms=3, label="differential")
    ax.step(r, wl, where="mid", color=P.ACCENT, marker="s", ms=3, linestyle="--", label="linear")
    ax.axhline(sec, color=P.INK_2, lw=0.8)
    ax.text(0.7, sec + 2, f"security level $2^{{-{sec}}}$", fontsize="small", color=P.INK_2)
    first = int(r[np.argmax(np.minimum(wd, wl) >= sec)])
    ax.axvline(first, color=P.INK_MUTED, lw=0.6, linestyle=(0, (1, 1.5)))
    ax.annotate("", xy=(full, 108), xytext=(first, 108),
                arrowprops=dict(arrowstyle="<->", lw=0.7, color=P.INK, shrinkA=0, shrinkB=0))
    ax.text((first + full) / 2, 111, f"margin: {full - first} rounds", ha="center", fontsize="small")
    ax.set_xlabel("rounds $r$")
    ax.set_ylabel(r"$-\log_2 p$ (lower bound)")
    ax.set_xticks(r)
    ax.set_ylim(0, 125)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 0.93))
    return P.save(fig, "p09_trail_bounds", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
