#!/usr/bin/env python3
"""P11 -- polynomial approximation: target + error on log scale (small multiples).

Pattern: top panel shows the target function and one approximation over the
evaluation interval; bottom panel (shared x) shows log10 |error| for several
degrees, direct-labelled; the precision target is a horizontal line.  Never plot
the error on a linear axis.  Toy target: sin(2 pi x)/(2 pi) on [-K, K].
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np
from numpy.polynomial import chebyshev as C


def make(venue="lncs", outdir=ROOT / "examples"):
    K = 6
    f = lambda x: np.sin(2 * np.pi * x) / (2 * np.pi)
    x = np.linspace(-K, K, 4000)
    fig, (a1, a2) = P.figure(venue, width="full", aspect=0.62, nrows=2, sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.6]})
    a1.plot(x, f(x), color=P.INK_MUTED, lw=1.6, label="target")
    degs = [31, 47, 63]
    for i, d in enumerate(degs):
        p = C.Chebyshev.interpolate(f, d, domain=[-K, K])
        err = np.abs(p(x) - f(x)) + 1e-18
        if d == degs[-1]:
            a1.plot(x, p(x), color=P.OURS, lw=0.8, linestyle="--", label=f"degree {d}")
        a2.semilogy(x, err, color=P.CATEGORICAL[i], lw=0.7)
        P.direct_label(a2, K, err[-200:].max(), f"$d={d}$", dx=3)
    a2.axhline(2 ** -20, color=P.INK_2, lw=0.7)
    a2.text(-K, 2 ** -20, r" target $2^{-20}$", va="top", fontsize="small", color=P.INK_2,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
    a1.legend(loc="upper right", ncols=2)
    a1.set_ylabel("$f(x)$")
    a2.set_ylabel(r"$|p(x)-f(x)|$")
    a2.set_xlabel("$x$")
    a2.set_xlim(-K, K * 1.13)
    return P.save(fig, "p11_approx_error", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
