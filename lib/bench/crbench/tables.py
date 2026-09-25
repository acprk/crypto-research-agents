"""Markdown and LaTeX (booktabs) tables whose cells carry EVIDENCE IDs.

A cell may be a plain value or a ``Cell(value, evidence="E12")``.  Rendering:

* Markdown: ``3.51×[^E12]`` plus a footnote block ``[^E12]: see EVIDENCE.md#E12``.
* LaTeX  : ``3.51$\\times$\\evid{E12}``.  ``\\evid`` is defined by
  :data:`LATEX_PREAMBLE` as an invisible marker by default (so the paper looks
  normal) but ``crbench audit-tex`` reads it to tie every cell to its ledger row.
  Pass ``visible=True`` to render IDs as superscripts in drafts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Sequence

LATEX_PREAMBLE = r"""% crbench: evidence marker. Invisible in camera-ready; switch to visible in drafts:
% \renewcommand{\evid}[1]{\textsuperscript{\tiny #1}}
\providecommand{\evid}[1]{}
"""


@dataclass
class Cell:
    value: Any
    evidence: str | None = None
    fmt: str | None = None  # python format spec, e.g. ".2f"


@dataclass
class Column:
    key: str
    header: str
    fmt: str | None = None
    align: str = "r"  # l / c / r
    suffix: str = ""  # e.g. "×" (rendered as $\times$ in LaTeX)


def _fmt(v: Any, spec: str | None) -> str:
    if v is None:
        return "--"
    if spec and isinstance(v, (int, float)):
        return format(v, spec)
    return str(v)


def _cell(row: dict, col: Column) -> tuple[str, str | None]:
    v = row.get(col.key)
    if isinstance(v, Cell):
        return _fmt(v.value, v.fmt or col.fmt) + (col.suffix if v.value is not None else ""), v.evidence
    return _fmt(v, col.fmt) + (col.suffix if v is not None else ""), None


def _latex_escape(s: str) -> str:
    rep = {"&": r"\&", "%": r"\%", "#": r"\#", "_": r"\_", "×": r"$\times$", "→": r"$\to$", "≈": r"$\approx$", "±": r"$\pm$", "µ": r"$\mu$"}
    return "".join(rep.get(ch, ch) for ch in s)


def to_markdown(rows: Sequence[dict], columns: Sequence[Column], caption: str | None = None) -> str:
    align = {"l": ":---", "c": ":---:", "r": "---:"}
    lines = []
    if caption:
        lines.append(f"**{caption}**\n")
    lines.append("| " + " | ".join(c.header for c in columns) + " |")
    lines.append("|" + "|".join(align[c.align] for c in columns) + "|")
    used: list[str] = []
    for row in rows:
        cells = []
        for c in columns:
            txt, ev = _cell(row, c)
            if ev:
                txt += f"[^{ev}]"
                if ev not in used:
                    used.append(ev)
            cells.append(txt.replace("|", r"\|"))
        lines.append("| " + " | ".join(cells) + " |")
    if used:
        lines.append("")
        lines.extend(f"[^{e}]: EVIDENCE.md row {e}" for e in used)
    return "\n".join(lines) + "\n"


def to_latex(rows: Sequence[dict], columns: Sequence[Column], caption: str | None = None, label: str | None = None,
             visible: bool = False, midrule_after: Sequence[int] = (), notes: str | None = None) -> str:
    out = []
    if visible:
        out.append(r"\providecommand{\evid}[1]{\textsuperscript{\tiny #1}}")
    out += [r"\begin{table}[t]", r"\centering"]
    if caption:
        out.append(r"\caption{" + _latex_escape(caption) + "}")
    if label:
        out.append(r"\label{" + label + "}")
    out.append(r"\begin{tabular}{" + "".join(c.align for c in columns) + "}")
    out.append(r"\toprule")
    out.append(" & ".join(_latex_escape(c.header) for c in columns) + r" \\")
    out.append(r"\midrule")
    for i, row in enumerate(rows):
        cells = []
        for c in columns:
            txt, ev = _cell(row, c)
            txt = _latex_escape(txt)
            if ev:
                txt += r"\evid{" + ev + "}"
            cells.append(txt)
        out.append(" & ".join(cells) + r" \\")
        if i in midrule_after:
            out.append(r"\midrule")
    out.append(r"\bottomrule")
    out.append(r"\end{tabular}")
    if notes:
        out.append(r"\par\smallskip{\footnotesize " + _latex_escape(notes) + "}")
    out.append(r"\end{table}")
    return "\n".join(out) + "\n"


def from_run_summary(summary: dict, speedups: dict | None = None, evidence: dict[str, str] | None = None,
                     digits: int = 3) -> tuple[list[dict], list[Column]]:
    """Turn ``RunResult.summary()`` (+ ``speedups``) into rows/columns for the renderers."""
    evidence = evidence or {}
    speedups = speedups or {}
    rows = []
    for arm, s in summary.items():
        sp = speedups.get(arm)
        rows.append({
            "arm": arm,
            "n": s.get("n"),
            "median": Cell(s.get("median"), evidence.get(arm), f".{digits}g") if s.get("n") else None,
            "iqr": s.get("iqr"),
            "speedup": Cell(sp["ratio"], evidence.get(arm + ":speedup"), ".2f") if sp else None,
            "ci": f"[{sp['ci_low']:.2f}, {sp['ci_high']:.2f}]" if sp else None,
        })
    cols = [Column("arm", "Arm", align="l"), Column("n", "n"), Column("median", "Median (s)"),
            Column("iqr", "IQR (s)", f".{digits}g"), Column("speedup", "Speed-up", suffix="×"), Column("ci", "95% CI", align="c")]
    return rows, cols


if __name__ == "__main__":
    rows = [{"scheme": "toy-A", "t": Cell(1.234, "E1"), "x": Cell(2.0, "E2")}, {"scheme": "toy-B", "t": 2.468, "x": None}]
    cols = [Column("scheme", "Scheme", align="l"), Column("t", "Time (s)", ".3f"), Column("x", "Speed-up", ".2f", suffix="×")]
    print(to_markdown(rows, cols, "Toy"))
    print(to_latex(rows, cols, "Toy", "tab:toy"))
