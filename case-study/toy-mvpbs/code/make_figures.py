# TOY: not secure
"""P7 figures (owner: figure-artist).  Reads ONLY results/ logs; never hand-typed numbers.

    /usr/bin/python3 code/make_figures.py     -> paper/figs/fig_speedup_failure.{pdf,png}

Panel (a): speed-up of MV-PBS over per-bit PBS vs number of LUTs k (bars, paired-bootstrap
95% CI), per-bit PBS = reference line at 1, ideal "k x" as a dashed guide (pattern P01).
Panel (b): S-box failure rate vs k at the noisy set T2 with Wilson 95% intervals, measured
(markers) and model (THEORY T1, lines).
Built from figures/templates/p01_speedup_bars.py + figures/style/palette.py (house style).
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(PROJ, "..", ".."))
sys.path[:0] = [HERE, os.path.join(PROJ, "falsify"), os.path.join(REPO, "figures", "style")]

import numpy as np  # noqa: E402
import palette as P  # noqa: E402
from _common import raw_samples, result_kv  # noqa: E402
from crbench import stats  # noqa: E402


def wilson(c, n, z=1.96):
    p = c / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, mid - half), min(1.0, mid + half)


def model_fail(norm2s, std_br2, std_ks2, margin=1 / 64):
    """P[any of the bits wrong], independence approximation."""
    ps = [math.erfc(margin / math.sqrt(2 * (n2 * std_br2 + std_ks2))) for n2 in norm2s]
    return 1 - float(np.prod([1 - p for p in ps]))


def main():
    ks = [1, 2, 3, 4]
    sp = [stats.speedup(raw_samples("bench_T1_kscan", f"perbit_k{k}"),
                        raw_samples("bench_T1_kscan", f"mvpbs_k{k}"), paired=True) for k in ks]
    pb, mv = result_kv("noise_T2", "perbit"), result_kv("noise_T2", "mvpbs")

    fig, (a, b) = P.figure("lncs", width="full", aspect=0.36, ncols=2)
    x = np.arange(len(ks))
    r = np.array([s.ratio for s in sp])
    err = np.array([[s.ratio - s.ci_low for s in sp], [s.ci_high - s.ratio for s in sp]])
    bars = a.bar(x, r, 0.6, color=P.OURS, yerr=err, capsize=2, ecolor=P.INK, label="MV-PBS (measured)")
    a.plot(x, ks, ls="--", color=P.BASELINE_GREYS[1], marker="", lw=0.9, label=r"ideal $k\times$")
    a.axhline(1.0, color=P.INK_2 if hasattr(P, "INK_2") else P.INK, lw=0.8)
    for bb, v in zip(bars, r):
        inside = v > 1.5
        a.text(bb.get_x() + bb.get_width() / 2, v - 0.35 if inside else v + 0.3, f"{v:.2f}" + r"$\times$",
               ha="center", va="center", fontsize="x-small", color="white" if inside else P.INK)
    a.set_xticks(x, [str(k) for k in ks])
    a.set_xlabel("number of LUTs $k$ (output bits)")
    a.set_ylabel("speed-up over per-bit PBS")
    a.set_ylim(0, 4.6)
    a.legend(loc="upper left", fontsize="x-small")
    a.set_title("(a) toy timing, set T1", loc="left", fontsize="small")

    for name, kv, style, col in (("per-bit PBS", pb, "s", P.BASELINE_GREYS[0]), ("MV-PBS", mv, "o", P.OURS)):
        tag = "perbit" if name.startswith("per") else "mvpbs"
        c = np.array([int(kv[f"{tag}_k{k}"]["sbox_fails"]) for k in ks])
        n = int(kv[f"{tag}_k1"]["n"])
        lo, hi = zip(*[wilson(ci, n) for ci in c])
        rate = c / n
        b.errorbar(np.array(ks) + (0.06 if tag == "mvpbs" else -0.06), rate,
                   yerr=[rate - np.array(lo), np.array(hi) - rate], fmt=style, color=col, ms=3.5,
                   capsize=2, lw=0.9, label=f"{name} (measured)")
        # model line from the same log (pred_std of each bit = sqrt(norm2 Var_BR + Var_KS))
        var = [2 ** (2 * float(kv[f"{tag}_bit{i}"]["pred_std_log2"])) for i in range(4)]
        mod = [1 - np.prod([1 - math.erfc((1 / 64) / math.sqrt(2 * v)) for v in var[:k]]) for k in ks]
        b.plot(ks, mod, ls=":", color=col, lw=0.9)
    b.set_xticks(ks)
    b.set_xlabel("number of LUTs $k$ (output bits)")
    b.set_ylabel("S-box failure rate")
    b.set_ylim(-0.02, 0.5)
    b.legend(loc="upper left", fontsize="x-small")
    b.set_title("(b) noisy toy set T2 (dotted: model)", loc="left", fontsize="small")
    for p in P.save(fig, "fig_speedup_failure", os.path.join(PROJ, "paper", "figs")):
        print("wrote", os.path.relpath(p, PROJ))


if __name__ == "__main__":
    main()
