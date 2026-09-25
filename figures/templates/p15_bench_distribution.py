#!/usr/bin/env python3
"""P15 -- repeated-run distributions for an A/B benchmark.

Pattern: for each workload, the individual runs (jittered dots) of A and B side
by side with median and inter-quartile range; the median ratio with a
bootstrap 95% CI is printed above each pair.  This is the figure a falsifier
wants: it shows run-to-run spread, not just a single bar.  SYNTHETIC RUNS.
"""
import sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "style"))
import palette as P
import numpy as np


def boot_ci(a, b, rng, B=2000):
    r = [np.median(rng.choice(a, a.size)) / np.median(rng.choice(b, b.size)) for _ in range(B)]
    return np.percentile(r, [2.5, 97.5])


def make(venue="lncs", outdir=ROOT / "examples"):
    rng = np.random.default_rng(2)
    loads = ["KeyGen", "Encrypt", "Mult+Relin", "Bootstrap"]
    base = np.array([12.0, 3.1, 8.4, 410.0])
    gain = np.array([1.05, 1.3, 1.8, 2.3])
    fig, axs = P.figure(venue, width="full", aspect=0.36, ncols=4)
    for ax, name, m, g in zip(axs, loads, base, gain):
        a = m * rng.lognormal(0, 0.04, 31)
        b = m / g * rng.lognormal(0, 0.05, 31)
        for k, (v, c, lab) in enumerate([(a, P.BASELINE_GREYS[1], "A"), (b, P.OURS, "B")]):
            x = k + rng.uniform(-0.12, 0.12, v.size)
            ax.scatter(x, v, s=4, color=c, alpha=0.6, lw=0)
            q1, med, q3 = np.percentile(v, [25, 50, 75])
            ax.plot([k + 0.22, k + 0.22], [q1, q3], color=P.INK, lw=1.2)
            ax.plot([k + 0.16, k + 0.28], [med, med], color=P.INK, lw=1.2)
        lo, hi = boot_ci(a, b, rng, 800)
        ax.set_title(f"{name}\n{np.median(a) / np.median(b):.2f}" + r"$\times$" + f" [{lo:.2f}, {hi:.2f}]",
                     fontsize="small")
        ax.set_xticks([0, 1], ["A", "B"])
        ax.set_xlim(-0.5, 1.5)
        ax.set_ylim(0, None)
        ax.tick_params(axis="x", length=0)
    axs[0].set_ylabel("time (ms), 31 interleaved runs")
    return P.save(fig, "p15_bench_distribution", outdir)


if __name__ == "__main__":
    P.cli(make, __doc__)
