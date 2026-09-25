#!/usr/bin/env python3
"""P07 -- ciphertext / modulus bit-layout diagram ("where do the bits live").

Pattern (very common in FHE bootstrapping papers): each row is one ciphertext
state drawn as a horizontal bar of width log q; coloured segments show message
bits, gap and noise; braces give the moduli (q, Delta, t); the operation that
maps one state to the next is written on the arrow between rows.  Keep 2-4
rows, a single accent for the message, grey for noise.  SYNTHETIC LAYOUT.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
from matplotlib.patches import Rectangle
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch


def brace(ax, x0, x1, y, h=0.12, up=True, label="", **kw):
    """Curly brace from x0 to x1 at height y (opening upwards if up)."""
    s = 1 if up else -1
    xm = (x0 + x1) / 2
    verts = [(x0, y), (x0, y + s * h), (xm, y), (xm, y + s * h),
             (xm, y + s * h), (xm, y), (x1, y + s * h), (x1, y)]
    codes = [MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4,
             MPath.MOVETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4]
    ax.add_patch(PathPatch(MPath(verts, codes), fill=False, lw=0.7, color=P.INK_2))
    ax.text(xm, y + s * (h + 0.04), label, ha="center", va="bottom" if up else "top", fontsize="small", **kw)


def row(ax, y, segs, name):
    x = 0.0
    for w, c, lab in segs:
        ax.add_patch(Rectangle((x, y), w, 0.35, facecolor=c, edgecolor=P.INK_2, lw=0.6))
        if lab:
            ax.text(x + w / 2, y + 0.175, lab, ha="center", va="center", fontsize="small")
        x += w
    ax.text(-0.3, y + 0.175, name, ha="right", va="center", fontsize="small")
    return x


def make(venue="lncs", outdir=ROOT / "examples"):
    fig, ax = P.figure(venue, width=0.8 if venue == "lncs" else "column", aspect=0.8)
    msg, noise, gap = P.SEQ_BLUE[1], "#d3d2cc", "white"
    rows = [
        (3.0, [(1.5, msg, "$m$"), (1.5, gap, ""), (3.0, noise, "$e$")], r"$\mathrm{ct}$", r"$q$"),
        (1.6, [(1.5, gap, ""), (4.5, noise, "$e + qI$")], r"$\mathrm{ct}'$", r"$Q \gg q$"),
        (0.2, [(1.5, msg, "$m$"), (3.3, gap, ""), (1.2, noise, "$e'$")], r"$\mathrm{ct}''$", r"$q$"),
    ]
    for y, segs, name, top in rows:
        x1 = row(ax, y, segs, name)
        brace(ax, 0, x1, y + 0.42, label=top)
    brace(ax, 0, 1.5, 2.93, up=False, label="$t$")
    brace(ax, 0, 1.5, 0.13, up=False, label="$t$")
    for (ya, yb, op) in [(3.0, 1.6, "ModRaise"), (1.6, 0.2, "EvalMod (toy)")]:
        ax.annotate("", xy=(3.0, yb + 0.78), xytext=(3.0, ya - 0.08),
                    arrowprops=dict(arrowstyle="-|>", color=P.INK_2, lw=0.7, mutation_scale=7))
        ax.text(3.12, (ya - 0.08 + yb + 0.78) / 2, op, fontsize="small", va="center")
    ax.set_xlim(-1.4, 6.3)
    ax.set_ylim(-0.3, 3.8)
    ax.axis("off")
    return P.save(fig, "p07_modulus_layout", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
