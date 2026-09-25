#!/usr/bin/env python3
"""P14 -- parameter-sweep heatmap with the optimum outlined.

Pattern: two discrete tuning knobs on the axes, cost in each cell (value
printed, one decimal), a single-hue sequential ramp where darker = worse (or
better -- say which in the colour-bar label), infeasible cells hatched grey
rather than coloured, and the optimum cell outlined.  SYNTHETIC COSTS.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Rectangle


def make(venue="lncs", outdir=ROOT / "examples"):
    ells = np.arange(1, 9)          # gadget digits
    ks = np.arange(1, 7)            # key-switching keys
    L, K = np.meshgrid(ells, ks)
    cost = 3.0 * L + 18.0 / L + 1.4 * K + 10.0 / K + 0.3 * L * K
    infeasible = (L * K > 30)
    fig, ax = P.figure(venue, width=0.75 if venue == "lncs" else "column", aspect=0.62)
    cmap = LinearSegmentedColormap.from_list("seq", P.SEQ_BLUE[:10])
    data = np.ma.masked_where(infeasible, cost)
    im = ax.imshow(data, cmap=cmap, origin="lower", aspect="auto")
    for (i, j), v in np.ndenumerate(cost):
        if infeasible[i, j]:
            ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, facecolor=P.NEUTRAL_MID, hatch="////",
                                   edgecolor=P.BASELINE_GREYS[2], lw=0))
            continue
        dark = (v - data.min()) / (data.max() - data.min()) > 0.6
        ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6, color="white" if dark else P.INK)
    i, j = np.unravel_index(np.ma.argmin(data), cost.shape)
    ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False, edgecolor=P.ACCENT, lw=1.6))
    ax.set_xticks(range(len(ells)), ells)
    ax.set_yticks(range(len(ks)), ks)
    ax.set_xlabel(r"number of gadget digits $\ell$")
    ax.set_ylabel("number of keys $k$")
    ax.grid(False)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    cb = fig.colorbar(im, ax=ax, pad=0.02, shrink=0.9)
    cb.set_label("latency (ms), lower is better", fontsize="small")
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize="small", length=2)
    return P.save(fig, "p14_param_sweep_heatmap", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
