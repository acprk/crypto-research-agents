#!/usr/bin/env python3
"""P10 -- empirical error distribution with Gaussian fit and failure threshold.

Pattern: histogram of measured decryption noise on a LOG y-axis (so the tails
are visible), fitted Gaussian as a thin line, the correctness bound +-B as
vertical lines, and the extrapolated failure probability stated as 2^-k.
Always report sample count.  SYNTHETIC SAMPLES.
"""
import sys, pathlib, math
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def make(venue="lncs", outdir=ROOT / "examples"):
    rng = np.random.default_rng(11)
    N = 200_000
    e = rng.normal(0, 3.2, N) + rng.uniform(-4, 4, N) + rng.integers(-1, 2, N)
    sigma = e.std()
    B = 40.0
    fig, ax = P.figure(venue, width="full", aspect=0.42)
    bins = np.arange(-45.5, 46.5, 1.0)
    h, _ = np.histogram(e, bins)
    c = (bins[:-1] + bins[1:]) / 2
    ax.bar(c, h / N, width=1.0, color=P.SEQ_BLUE[4], lw=0, label=f"empirical ($N=2^{{{math.log2(N):.1f}}}$)")
    xs = np.linspace(-45, 45, 400)
    ax.plot(xs, np.exp(-xs ** 2 / (2 * sigma ** 2)) / (sigma * math.sqrt(2 * math.pi)), color=P.INK, lw=0.9,
            label=rf"Gaussian fit, $\sigma={sigma:.2f}$")
    for s in (-B, B):
        ax.axvline(s, color=P.CATEGORICAL[7], lw=0.9)
    pfail = math.erfc(B / (sigma * math.sqrt(2)))
    ax.text(B - 1, 1e-2, rf"$\pm B$: $\Pr[|e|>B]\approx 2^{{{math.log2(pfail):.0f}}}$", ha="right",
            fontsize="small")
    ax.set_yscale("log")
    ax.set_ylim(1e-7, 0.2)
    ax.set_xlabel("decryption error $e$")
    ax.set_ylabel("frequency")
    ax.legend(loc="upper left")
    return P.save(fig, "p10_error_distribution", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
