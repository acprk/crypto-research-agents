"""palette.py -- colours, venue sizes and save helpers for house-style figures.

Typical use (from a template or a paper's figure script)::

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "style"))
    import palette as P

    P.use("lncs")                                   # or "acm", "ieee"
    fig, ax = P.figure("lncs", width="full", aspect=0.45)
    ax.plot(x, y, color=P.OURS, **P.line_style(0))
    P.save(fig, "speedup", outdir="figures/examples")   # -> speedup.pdf + speedup.png

Design rules encoded here (see skills/paper-figures/SKILL.md):

* categorical colours are assigned in a fixed order (``CATEGORICAL``) and never
  cycled past 8 -- fold the tail into "Other" or use small multiples;
* "ours vs. baselines" figures use emphasis: ``OURS`` (slot-1 blue) plus
  neutral greys for baselines, instead of 6 competing hues;
* every series also gets a marker / dash / hatch so the figure survives
  greyscale printing and colour-vision deficiency;
* sequential data uses one hue light->dark (``SEQ_BLUE``); diverging data uses
  blue <-> red with a grey midpoint (``DIVERGING``).

``python3 palette.py`` runs a self-check (CVD separation of the categorical
order under simulated protan/deutan/tritan vision, and a save round-trip).
"""
from __future__ import annotations

import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# colours
# ---------------------------------------------------------------------------
CATEGORICAL = [
    "#2a78d6",  # 1 blue
    "#eb6834",  # 2 orange
    "#1baf7a",  # 3 aqua
    "#eda100",  # 4 yellow  (low contrast on white: pair with marker/label)
    "#e87ba4",  # 5 magenta (low contrast on white)
    "#008300",  # 6 green
    "#4a3aa7",  # 7 violet
    "#e34948",  # 8 red
]
OURS = CATEGORICAL[0]
OURS_DARK = "#1c5cab"
ACCENT = CATEGORICAL[1]           # second emphasis colour (e.g. "ours, variant")
BASELINE_GREYS = ["#52514e", "#8a8984", "#b5b4ae", "#d3d2cc"]
INK = "#0b0b0b"
INK_2 = "#52514e"
INK_MUTED = "#8a8984"
GRID = "#e4e3df"
SURFACE = "#ffffff"
NEUTRAL_MID = "#f0efec"

SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
            "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
SEQ_ORANGE = ["#fde3d6", "#fbc7ad", "#f7a784", "#f2885c", "#eb6834", "#c9531f", "#a44117", "#7e3010"]
DIVERGING = ["#104281", "#2a78d6", "#86b6ef", "#cde2fb", NEUTRAL_MID,
             "#f8d0cf", "#f09392", "#e34948", "#9e2322"]

# region fills for feasibility plots (light tints, never saturated blocks)
FEASIBLE = "#cde2fb"
INFEASIBLE = "#f0efec"
DANGER = "#f8d0cf"

MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
DASHES = ["-", "--", "-.", ":", (0, (5, 1, 1, 1)), (0, (1, 1)), (0, (3, 1, 1, 1, 1, 1)), (0, (4, 2))]
HATCHES = ["", "////", "\\\\\\\\", "xxxx", "....", "++++", "oo", "--"]

# ---------------------------------------------------------------------------
# venue geometry (inches)
# ---------------------------------------------------------------------------
VENUES = {
    #          column   full     style file
    "lncs": {"column": 4.80, "full": 4.80, "style": "lncs.mplstyle"},   # single column, 12.2 cm
    "acm":  {"column": 3.33, "full": 7.00, "style": "acm.mplstyle"},
    "ieee": {"column": 3.50, "full": 7.16, "style": "ieee.mplstyle"},
}
GOLDEN = (math.sqrt(5) - 1) / 2


def use(venue: str = "lncs") -> None:
    """Activate crypto.mplstyle + the venue sheet."""
    import matplotlib.pyplot as plt
    import logging
    for name in ("matplotlib.font_manager", "fontTools", "matplotlib.backends.backend_pdf"):
        logging.getLogger(name).setLevel(logging.ERROR)
    v = VENUES[venue]
    plt.style.use([str(HERE / "crypto.mplstyle"), str(HERE / v["style"])])


def size(venue: str = "lncs", width: str | float = "full", aspect: float = GOLDEN) -> tuple[float, float]:
    """(w, h) in inches. width = 'column' | 'full' | fraction of full width."""
    v = VENUES[venue]
    w = v[width] if isinstance(width, str) else v["full"] * float(width)
    return (w, w * aspect)


def figure(venue: str = "lncs", width: str | float = "full", aspect: float = GOLDEN, nrows=1, ncols=1, **kw):
    import matplotlib.pyplot as plt
    use(venue)
    return plt.subplots(nrows, ncols, figsize=size(venue, width, aspect), **kw)


def line_style(i: int, color: str | None = None) -> dict:
    """Colour + marker + dash for series i (redundant encoding)."""
    return {"color": color or CATEGORICAL[i % 8], "marker": MARKERS[i % 8], "linestyle": DASHES[i % 8]}


def baseline_style(i: int) -> dict:
    """Grey, distinct marker/dash -- for baselines in an 'ours vs. prior' plot."""
    return {"color": BASELINE_GREYS[i % 4], "marker": MARKERS[(i + 1) % 8], "linestyle": DASHES[(i + 1) % 8]}


def direct_label(ax, x, y, text, color=INK, dx=4, dy=0, **kw):
    """Label a series at a point (usually its end) in text ink, offset in points."""
    ax.annotate(text, (x, y), xytext=(dx, dy), textcoords="offset points",
                va="center", ha="left" if dx >= 0 else "right", color=color, **kw)


def save(fig, stem: str, outdir: str | Path = ".", png_dpi: int = 300) -> list[Path]:
    """Write <stem>.pdf (vector) and <stem>.png; return the paths."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    paths = [outdir / f"{stem}.pdf", outdir / f"{stem}.png"]
    fig.savefig(paths[0], metadata={"Creator": "crypto-research-agents", "CreationDate": None})
    fig.savefig(paths[1], dpi=png_dpi)
    return paths


def cli(make, doc: str = "") -> None:
    """Standard command line for templates: --venue, --out, --width."""
    import argparse
    import matplotlib
    matplotlib.use("Agg")
    ap = argparse.ArgumentParser(description=doc)
    ap.add_argument("--venue", default="lncs", choices=sorted(VENUES))
    ap.add_argument("--out", default=str(HERE.parent / "examples"), help="output directory")
    a = ap.parse_args()
    paths = make(venue=a.venue, outdir=a.out)
    for p in paths:
        assert Path(p).exists() and Path(p).stat().st_size > 0, p
        print(p)


# ---------------------------------------------------------------------------
# colour-vision check (OKLab distance under Machado et al. 2009 simulation)
# ---------------------------------------------------------------------------
_MACHADO = {  # severity 1.0, linear RGB
    "protan": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def _hex2lin(h: str):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def _oklab(lin):
    r, g, b = lin
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _sim(lin, kind):
    if kind == "normal":
        return lin
    M = _MACHADO[kind]
    return [min(1.0, max(0.0, sum(M[i][j] * lin[j] for j in range(3)))) for i in range(3)]


def delta_e(a: str, b: str, kind: str = "normal") -> float:
    """OKLab distance x100 between two hex colours under simulated vision."""
    pa, pb = _oklab(_sim(_hex2lin(a), kind)), _oklab(_sim(_hex2lin(b), kind))
    return 100 * math.dist(pa, pb)


def check_palette(colors=None, pairs: str = "adjacent") -> dict:
    """Worst-pair distance per vision type. Target: >= 8 (CVD), >= 15 (normal)."""
    colors = colors or CATEGORICAL
    idx = ([(i, i + 1) for i in range(len(colors) - 1)] if pairs == "adjacent"
           else [(i, j) for i in range(len(colors)) for j in range(i + 1, len(colors))])
    out = {}
    for kind in ("normal", "protan", "deutan", "tritan"):
        worst = min(idx, key=lambda p: delta_e(colors[p[0]], colors[p[1]], kind))
        out[kind] = (round(delta_e(colors[worst[0]], colors[worst[1]], kind), 1), colors[worst[0]], colors[worst[1]])
    return out


if __name__ == "__main__":
    import tempfile
    rep = check_palette()
    for k, v in rep.items():
        print(f"{k:7s} worst adjacent dE = {v[0]:5.1f}  ({v[1]} vs {v[2]})")
    assert rep["normal"][0] >= 15, rep
    assert min(rep["protan"][0], rep["deutan"][0]) >= 8, rep
    for venue in VENUES:
        import matplotlib
        matplotlib.use("Agg")
        fig, ax = figure(venue, width="column")
        for i in range(3):
            ax.plot([0, 1, 2], [i, i + 1, i + 0.5], **line_style(i), label=f"s{i}")
        ax.set_xlabel(r"$\log_2 q$")
        ax.legend()
        with tempfile.TemporaryDirectory() as d:
            pdf, png = save(fig, "t", d)
            assert pdf.stat().st_size > 1000 and png.stat().st_size > 1000
        w, h = fig.get_size_inches()
        assert abs(w - VENUES[venue]["column"]) < 1e-6
    print("palette self-check OK")
