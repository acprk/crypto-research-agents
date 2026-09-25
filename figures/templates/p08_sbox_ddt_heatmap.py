#!/usr/bin/env python3
"""P08 -- difference distribution table (DDT) heatmap of a 4-bit S-box.

Pattern: 16x16 grid, rows = input difference, columns = output difference,
hex tick labels; one-hue sequential ramp (0 = white); cell counts printed only
when non-zero, in dark or white ink by background lightness; the maximal entry
(differential uniformity) is called out in the caption/title.  Works the same
for LAT (use a diverging map centred at 0) and BCT.  The S-box used is the
public PRESENT S-box.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np
from matplotlib.colors import ListedColormap, BoundaryNorm

SBOX = [0xC, 0x5, 0x6, 0xB, 0x9, 0x0, 0xA, 0xD, 0x3, 0xE, 0xF, 0x8, 0x4, 0x7, 0x1, 0x2]


def ddt(s):
    n = len(s)
    t = np.zeros((n, n), dtype=int)
    for x in range(n):
        for a in range(n):
            t[a, s[x] ^ s[x ^ a]] += 1
    return t


def make(venue="lncs", outdir=ROOT / "examples"):
    T = ddt(SBOX)
    assert T[0, 0] == 16 and T.sum() == 256
    du = T[1:].max()
    fig, ax = P.figure(venue, width=0.62 if venue == "lncs" else "column", aspect=0.92)
    levels = [0, 2, 4, 6, 8, 16]
    cmap = ListedColormap(["#ffffff", P.SEQ_BLUE[2], P.SEQ_BLUE[5], P.SEQ_BLUE[8], P.SEQ_BLUE[11]])
    norm = BoundaryNorm([0, 1, 3, 5, 7, 17], cmap.N)
    im = ax.imshow(T, cmap=cmap, norm=norm)
    for a in range(16):
        for b in range(16):
            v = T[a, b]
            if v:
                ax.text(b, a, str(v), ha="center", va="center", fontsize=5.5,
                        color="white" if v >= 6 else P.INK)
    ax.set_xticks(range(16), [f"{i:x}" for i in range(16)], fontsize=6)
    ax.set_yticks(range(16), [f"{i:x}" for i in range(16)], fontsize=6)
    ax.set_xlabel(r"output difference $\beta$")
    ax.set_ylabel(r"input difference $\alpha$")
    ax.xaxis.set_label_position("top")
    ax.xaxis.tick_top()
    ax.grid(False)
    ax.set_xticks(np.arange(-.5, 16), minor=True)
    ax.set_yticks(np.arange(-.5, 16), minor=True)
    ax.grid(which="minor", color=P.GRID, lw=0.3)
    ax.tick_params(which="both", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_title(f"differential uniformity = {du}", fontsize="small", color=P.INK_2, loc="left", pad=2, y=-0.08)
    return P.save(fig, "p08_sbox_ddt_heatmap", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
