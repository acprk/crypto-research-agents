#!/usr/bin/env python3
"""P03 -- log-log scaling curve with asymptotic guide lines.

Pattern: measured cost vs. problem size on log2/log10 axes, markers at measured
points only; thin grey guide lines O(n log n), O(n^2) anchored at the first
point and labelled at their right end; series are direct-labelled so no legend
lookup is needed; the slope is what the reader should see.  SYNTHETIC DATA.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np
from matplotlib.ticker import FixedLocator, FuncFormatter


def make(venue="lncs", outdir=ROOT / "examples"):
    rng = np.random.default_rng(3)
    logn = np.arange(8, 17)
    n = 2.0 ** logn
    fast = 2e-5 * n * np.log2(n) * (1 + rng.normal(0, 0.04, n.size)) + 0.01
    slow = 6e-8 * n ** 2 * (1 + rng.normal(0, 0.04, n.size)) + 0.01
    fig, ax = P.figure(venue, width="column" if venue != "lncs" else 0.62, aspect=0.75)
    for i, (y, name) in enumerate([(slow, "schoolbook"), (fast, "NTT-based")]):
        c = P.BASELINE_GREYS[0] if i == 0 else P.OURS
        ax.loglog(n, y, color=c, marker=P.MARKERS[i], linestyle="-", base=2)
        P.direct_label(ax, n[-1], y[-1], name, dx=5)
    for f, lab in [(lambda m: m * np.log2(m), r"$O(n\log n)$"), (lambda m: m ** 2, r"$O(n^2)$")]:
        g = f(n) / f(n[0]) * (fast[0] if "log" in lab else slow[0])
        ax.loglog(n, g, color=P.INK_MUTED, lw=0.6, linestyle=(0, (4, 2)), base=2, zorder=1)
        below = "log" in lab   # put each guide label on the side away from the other guide
        ax.annotate(lab, (n[-3], g[-3]), xytext=(4, -6) if below else (-4, 6), textcoords="offset points",
                    color=P.INK_MUTED, fontsize="small", ha="left" if below else "right",
                    va="top" if below else "bottom")
    ax.xaxis.set_major_locator(FixedLocator(n[::2]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: rf"$2^{{{int(round(np.log2(v)))}}}$"))
    ax.set_xlabel(r"ring dimension $n$")
    ax.set_ylabel("time (ms)")
    ax.set_xlim(n[0] / 1.3, n[-1] * 6)
    ax.grid(axis="both", which="major")
    return P.save(fig, "p03_scaling_loglog", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
