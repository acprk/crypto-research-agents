"""Render docs/bigmap/bigmap.{png,svg,pdf}: the one-page map of crypto-research-agents.

Layout = six horizontal bands, one column per agent, columns grouped under phases:
phases -> agents -> blackboard files -> skills -> library -> external tools.
Run:  python3 docs/bigmap/make_bigmap.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

OUT = Path(__file__).resolve().parent
W, GAP = 1.0, 0.18           # column width, gap between columns
COLS = 12
X = [i * (W + GAP) for i in range(COLS)]
XMAX = X[-1] + W

C = dict(phase="#3b6ea5", agent="#ffe0a3", agent_e="#c98a1a", pi="#f5b041", fal="#f5b7b1", fal_e="#c0392b",
         bb="#d5f0d5", bb_e="#2e7d32", sk="#dbe4f6", sk_e="#5c7cbf", lib="#ead5ee", lib_e="#8e44ad",
         tool="#f6d6d5", tool_e="#b0413e", red="#c0392b", green="#2e7d32", band="#f7f7f7")

# (agent, one-line capability, blackboard files, skills) — one column each
AGENTS = [
    ("pi-orchestrator", "gates · dispatch\narbitration", "STATE.md\nDECISIONS.md", "phase-gate\nworkflows/*.js"),
    ("lit-scout", "ePrint · DBLP\nrelated-work matrix", "LITERATURE.md\nrefs.bib", "eprint-search\nlit-matrix\nbib-verify\nreading-notes"),
    ("math-librarian", "textbook TOC index\n'which book, which §'", "MATH-REFS.md", "textbook-index"),
    ("idea-miner", "8-step mining loop\ncost-model screen", "IDEAS.md\n→ CLAIMS rows", "idea-mining-loop"),
    ("theorist", "proofs · Sage\nLean4 · parameters", "THEORY.md\nlean/", "sage-check\nlean-bridge\nparam-estimation"),
    ("baseline-engineer", "fetch · pin · build\nfairness checklist", "baselines/\nMANIFEST.md", "baseline-pin"),
    ("experimenter", "interleaved bench\nmedians · env", "EVIDENCE.md\nresults/", "bench-protocol\nlog-to-evidence"),
    ("falsifier", "red team\nVETO power", "CLAIMS.md\n(verdicts)", "falsify"),
    ("writer", "section playbook\nonly survived claims", "paper/", "paper-playbook\nabstract-craft\ntechnique-overview\nexperiments-writing"),
    ("figure-artist", "house style\nharvest patterns", "paper/figs/", "paper-figures\nfigure-harvest"),
    ("reviewer-sim", "venue-calibrated\n3 personas", "REVIEWS.md", "venue-calibration\nmock-review"),
    ("submission-rebuttal", "anon · artifact\nrebuttal · camera-ready", "SUBMISSION.md", "rebuttal\nanonymize-check\ncamera-ready\nartifact-pack"),
]
# phase -> column span
PHASES = [("P0\nScoping", 0, 0), ("P1 Literature", 1, 2), ("P2\nIdeation", 3, 3), ("P3\nTheory", 4, 4),
          ("P4\nBaselines", 5, 5), ("P5\nExperiments", 6, 6), ("P6\nFalsify gate", 7, 7),
          ("P7 Write + Figures", 8, 9), ("P8 Review → Submit\n→ Rebuttal → CR", 10, 11)]
# library boxes: (label, first col, last col)
LIB = [("cryptomath.algebra\nGF(p^k) · Φ_m · Galois · CRT slots · NTT\nZ_{p^e} · digit extraction · characters", 0, 3),
       ("cryptomath.lattice\nLWE/RLWE/NTRU · estimator\ncore-SVP · BKZ/GSA · LLL", 4, 5),
       ("cryptomath.fhe (toy)\nBGV · BFV · CKKS · TFHE/PBS\nnoise · PS/BSGS · Chebyshev", 6, 7),
       ("cryptomath.symmetric · protocols · ec\nDDT/LAT/BCT · Boolean · APN · AES/SPN\nSAT/MILP · SS/OT/PSI/GC · DLP", 8, 9),
       ("crbench · costmodel · figures · lean\ninterleaved A/B · audit-tex · op count\nmplstyle · 12+ templates · harvester", 10, 11)]
TOOLS = [("WebSearch / WebFetch\nePrint · DBLP · Crossref", 0, 2), ("SageMath · Mathematica MCP\nLean LSP MCP", 3, 5),
         ("baseline libraries\nOpenFHE · HElib · SEAL · Lattigo · TFHE-rs\nMP-SPDZ · emp · APSI · CryptoSMT · liboqs", 6, 8),
         ("LaTeX · latexmk · TikZ\npdffonts · matplotlib", 9, 11)]

# band y-ranges (top, height)
# band label, y-bottom, y-top
BANDS = [("Phases", 10.35, 11.2), ("Agents\nagents/*.md", 8.2, 9.6), ("Blackboard\n(project files)", 6.45, 8.1),
         ("Skills\nskills/*/SKILL.md", 4.55, 6.2), ("Library\nlib/", 3.4, 4.45), ("Tools / MCP", 2.35, 3.3)]


def box(ax, x, y, w, h, text, fc, ec, fs=8.5, bold=False, lw=1.0, r=0.06):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc, ec=ec, lw=lw))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", linespacing=1.25)


def arrow(ax, p, q, color="#777777", lw=1.0, ls="-", rad=0.0, text=None, tcolor=None, fs=7.5):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=10, color=color, lw=lw, ls=ls,
                                 connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 0.12 + abs(rad) * 0.9, text, ha="center", fontsize=fs,
                color=tcolor or color, style="italic")


def span(a, b):
    return X[a], X[b] + W - X[a]


def main():
    fig, ax = plt.subplots(figsize=(22, 10.4))
    ax.set_xlim(-2.0, XMAX + 0.3)
    ax.set_ylim(2.2, 13.35)
    ax.axis("off")
    ax.text(XMAX / 2 - 0.9, 13.05, "crypto-research-agents — BIGMAP", ha="center", fontsize=20, fontweight="bold")
    ax.text(XMAX / 2 - 0.9, 12.62, "12 agents · shared blackboard · falsify-first gate · skills · algorithm library · tools",
            ha="center", fontsize=12, color="#444444")

    for label, lo, hi in BANDS:
        ax.add_patch(FancyBboxPatch((-1.9, lo), XMAX + 2.1, hi - lo, boxstyle="round,pad=0,rounding_size=0.1",
                                    fc=C["band"], ec="#dddddd", lw=0.8, zorder=0))
        ax.text(-1.8, (lo + hi) / 2, label, ha="left", va="center", fontsize=10.5, fontweight="bold", color="#333333")

    # phases (chevrons)
    ytop, h = 11.2, 0.62
    for name, a, b in PHASES:
        x0, w = span(a, b)
        y0 = ytop - 0.75
        t = 0.16
        ax.add_patch(Polygon([(x0, y0), (x0 + w - t, y0), (x0 + w, y0 + h / 2), (x0 + w - t, y0 + h), (x0, y0 + h),
                              (x0 + t, y0 + h / 2)], closed=True, fc=C["phase"], ec=C["phase"]))
        ax.text(x0 + w / 2, y0 + h / 2, name, ha="center", va="center", color="white", fontsize=8.6, fontweight="bold", linespacing=1.05)
    pc = {n.split()[0]: (span(a, b)[0] + span(a, b)[1] / 2) for n, a, b in PHASES}
    yb = ytop - 0.75 + h
    arrow(ax, (pc["P6"], yb), (pc["P2"], yb), C["red"], 1.3, "--", 0.25, "core claim refuted → new idea / weaker theorem")
    arrow(ax, (pc["P6"] - 0.15, yb), (pc["P5"] + 0.15, yb), C["red"], 1.3, "--", 0.6, "unfair baseline")
    arrow(ax, (pc["P8"], yb), (pc["P7"], yb), C["red"], 1.3, "--", 0.5, "mock-review items")
    arrow(ax, (pc["P1"] + 0.3, yb), (pc["P0"], yb), C["red"], 1.0, ":", 0.5, "pre-emption → pivot?", fs=7)

    # agents
    for i, (name, cap, bbf, sk) in enumerate(AGENTS):
        fc, ec, lw = C["agent"], C["agent_e"], 1.0
        if name == "pi-orchestrator":
            fc, lw = C["pi"], 1.8
        if name == "falsifier":
            fc, ec, lw = C["fal"], C["fal_e"], 1.8
        box(ax, X[i], 8.3, W, 1.2, f"\n{cap}", fc, ec, fs=7.6, lw=lw)
        ax.text(X[i] + W / 2, 9.37, name, ha="center", va="center", fontsize=7.9, fontweight="bold", color="#222222",
                bbox=dict(fc=fc, ec="none", pad=0.5))
        # blackboard
        strong = bbf.startswith(("CLAIMS", "EVIDENCE"))
        box(ax, X[i], 7.05, W, 0.95, bbf, C["bb"], C["bb_e"], fs=7.6, lw=2.0 if strong else 1.0)
        # skills
        box(ax, X[i], 4.65, W, 1.45, sk, C["sk"], C["sk_e"], fs=7.2)
        arrow(ax, (X[i] + W / 2, 8.3), (X[i] + W / 2, 8.0), "#8a8a8a", 0.9)
    # key gates into paper
    paper_x = X[8] + W / 2
    arrow(ax, (X[7] + W, 7.35), (X[8], 7.35), C["green"], 2.0, "-", 0.0)
    ax.text(X[7] + W + GAP / 2, 7.95, "only survived\nclaims", ha="center", fontsize=6.8, color=C["green"], style="italic")
    arrow(ax, (X[6] + W / 2, 7.05), (paper_x - 0.2, 7.05), C["green"], 1.8, "-", 0.28)
    ax.text((X[6] + paper_x) / 2, 6.62, "only logged numbers (crbench audit-tex)", ha="center", fontsize=6.8,
            color=C["green"], style="italic")
    arrow(ax, (X[7] + W / 2, 8.3), (X[6] + W / 2 + 0.25, 8.0), C["red"], 1.4, "-", 0.0)
    ax.text(X[7] - 0.05, 8.12, "audit", fontsize=6.8, color=C["red"], style="italic", ha="right")

    # library + tools
    for label, a, b in LIB:
        x0, w = span(a, b)
        box(ax, x0, 3.5, w, 0.85, label, C["lib"], C["lib_e"], fs=7.6)
    for label, a, b in TOOLS:
        x0, w = span(a, b)
        box(ax, x0, 2.42, w, 0.8, label, C["tool"], C["tool_e"], fs=7.6)
    fig.savefig(OUT / "bigmap.png", dpi=170, bbox_inches="tight")
    fig.savefig(OUT / "bigmap.svg", bbox_inches="tight")
    fig.savefig(OUT / "bigmap.pdf", bbox_inches="tight")


if __name__ == "__main__":
    main()
