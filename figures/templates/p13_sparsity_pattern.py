#!/usr/bin/env python3
"""P13 -- matrix sparsity patterns of a factorised linear transform.

Pattern: small multiples of equal-size square panels, one per factor, filled
cells = non-zero; each panel labelled underneath with its symbol and number of
non-zero diagonals (the quantity that drives rotation count); an "=" / "x"
between panels shows the factorisation.  Toy: radix-2 FFT factors for n = 16.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np
from matplotlib.colors import ListedColormap


def butterfly(n, span):
    M = np.zeros((n, n), dtype=int)
    for i in range(n):
        M[i, i] = 1
        M[i, i ^ span] = 1
    return M


def diagonals(M):
    n = len(M)
    return sum(1 for k in range(n) if any(M[i, (i + k) % n] for i in range(n)))


def make(venue="lncs", outdir=ROOT / "examples"):
    n = 16
    Ms = [butterfly(n, s) for s in (8, 4, 2, 1)]
    prod = np.linalg.multi_dot(Ms) != 0
    panels = Ms + [prod.astype(int)]
    names = [f"$B_{i + 1}$" for i in range(4)] + [r"$B_1B_2B_3B_4$"]
    fig, axs = P.figure(venue, width="full", aspect=0.27, ncols=5)
    cmap = ListedColormap(["white", P.OURS_DARK])
    for ax, M, nm in zip(axs, panels, names):
        ax.imshow(M, cmap=cmap, vmin=0, vmax=1, interpolation="nearest")
        ax.set_xticks(np.arange(-.5, n), minor=True)
        ax.set_yticks(np.arange(-.5, n), minor=True)
        ax.grid(which="minor", color=P.GRID, lw=0.25)
        ax.grid(which="major", visible=False)
        ax.tick_params(which="both", length=0, labelbottom=False, labelleft=False)
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_color(P.INK_2)
            sp.set_linewidth(0.5)
        ax.set_xlabel(f"{nm}\n{diagonals(M)} diagonals", fontsize="small")
    return P.save(fig, "p13_sparsity_pattern", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
