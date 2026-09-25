#!/usr/bin/env python3
"""harvest.py -- extract figures from a local corpus of (public) PDFs.

For every PDF found (recursively) under the given roots, locate figure captions
("Fig. 3.", "Figure 3:", "图 3"), compute a clip rectangle for the figure body
from the page's vector drawings, embedded images and text layout, render the
clip to PNG, measure simple statistics, classify the figure type heuristically
and give it a quality score.  Output: PNGs + ``index.json`` + ``index.csv``.

The output gallery is for LOCAL STUDY ONLY (the images are copyrighted by
their authors).  Never commit it; ``figures/.gitignore`` excludes the default
location.

Usage::

    python3 harvest.py CORPUS_DIR [CORPUS_DIR ...] --out /tmp/crypto_gallery \
        --exclude 'ours_prior' --exclude '*.zip' --timeout 90

    python3 harvest.py --selftest      # builds a synthetic PDF and checks it

Requires PyMuPDF (``import fitz``) and numpy.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import hashlib
import json
import multiprocessing as mp
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None

import numpy as np

# --------------------------------------------------------------------------
# Caption detection
# --------------------------------------------------------------------------
CAPTION_RE = re.compile(
    r"^\s*(?P<label>(?:Fig\.?|FIG\.?|Figure|FIGURE|图)\s*"
    r"(?P<num>[A-Z]?\.?\d+(?:\.\d+)?[a-z]?))\s*(?P<punct>[.:：|—–-])?\s*(?P<rest>.*)$",
    re.S,
)

# --------------------------------------------------------------------------
# Classification vocabulary (caption keywords -> type, weight)
# --------------------------------------------------------------------------
TYPES = [
    "plot-bar",
    "plot-line",
    "plot-scaling",
    "table-like",
    "protocol-flow",
    "architecture-pipeline",
    "circuit-cipher",
    "lattice-geometric",
    "heatmap-matrix",
    "tree-graph",
    "pseudocode-box",
    "other",
]

KEYWORDS: dict[str, list[tuple[str, float]]] = {
    "plot-bar": [(r"\bbar", 3), (r"\bpie\b|share of|fraction of", 2.5), (r"speed-?up", 2), (r"breakdown", 2), (r"comparison of (run|time|latenc)", 2),
                 (r"histogram", 2), (r"throughput", 1)],
    "plot-line": [(r"\bplot", 1.5), (r"\bcurve", 2), (r"as a function of", 2), (r"\bvs\.?\b|versus", 1.5),
                  (r"distribution", 1.5), (r"error", 1), (r"precision", 1), (r"approximation", 1.5),
                  (r"probabilit", 1), (r"trade-?off", 1.5)],
    "plot-scaling": [(r"scal", 2.5), (r"log[- ]?scale|log-log|logarithmic", 3), (r"asymptot", 2),
                     (r"grow", 1.5), (r"number of (slots|threads|parties|cores)", 2)],
    "table-like": [(r"\btable", 2), (r"parameter sets?", 1.5), (r"summary of", 1)],
    "protocol-flow": [(r"protocol", 3), (r"\bparty|parties", 2), (r"sender|receiver", 2.5), (r"client|server", 2),
                      (r"message", 1.5), (r"interaction", 2), (r"functionality|ideal", 1.5), (r"\bgame\b|hybrid", 1.5),
                      (r"experiment", 1)],
    "architecture-pipeline": [(r"overview", 2.5), (r"pipeline", 3), (r"architecture", 3), (r"framework", 2),
                              (r"workflow|flow of", 2), (r"procedure", 1), (r"bootstrapping", 1.5), (r"steps?\b", 1),
                              (r"illustration", 1.5), (r"diagram", 1), (r"high-level", 2),
                              (r"structure", 1.5), (r"data-?flow", 3), (r"\bblock", 1.5), (r"computation on", 1.5),
                              (r"lowering|compiler|\bir\b", 2)],
    "circuit-cipher": [(r"round", 2.5), (r"s-?box", 3), (r"cipher", 2.5), (r"circuit", 3), (r"\bgates?\b", 2),
                       (r"\bxor\b", 2), (r"permutation", 1.5), (r"key schedule", 3), (r"feistel|spn", 3),
                       (r"trail|characteristic", 2)],
    "lattice-geometric": [(r"lattice", 2.5), (r"basis", 2), (r"geometr", 2.5), (r"\bball\b|sphere", 2),
                          (r"fundamental domain|parallelepiped|voronoi", 3), (r"embedding", 1), (r"region", 1),
                          (r"\bplane\b", 1.5)],
    "heatmap-matrix": [(r"heat ?map", 3.5), (r"\bmatrix|matrices", 2), (r"\bddt\b|\blat\b|difference distribution", 3),
                       (r"correlation", 1.5), (r"diagonal", 1.5), (r"grid", 1.5), (r"sparsity", 2)],
    "tree-graph": [(r"\btree", 3), (r"\bgraph", 1), (r"\bdag\b", 3), (r"\bnodes?\b", 2), (r"recursion|recursive", 1.5),
                   (r"butterfly|ntt|fft", 1.5), (r"depth", 1)],
    "pseudocode-box": [(r"algorithm", 2.5), (r"pseudo-?code", 3), (r"\bconstruction", 2.5), (r"scheme", 1.5),
                       (r"definition", 1.5), (r"\bkeygen|encrypt|decrypt", 2), (r"procedure", 1.5)],
}
KEYWORDS_C = {t: [(re.compile(p, re.I), w) for p, w in kw] for t, kw in KEYWORDS.items()}


@dataclass
class FigRecord:
    source_pdf: str
    source_sha1: str
    page: int  # 1-based
    fig_label: str
    caption: str
    png: str
    clip: list[float]
    caption_above: bool
    type: str
    type_scores: dict = field(default_factory=dict)
    quality: float = 0.0
    stats: dict = field(default_factory=dict)
    notes: str = ""


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------
def _union(rects):
    r = fitz.Rect(rects[0])
    for x in rects[1:]:
        r |= x
    return r


def _vgap(a, b) -> float:
    """Vertical gap between rects (0 if they overlap vertically)."""
    if a.y1 < b.y0:
        return b.y0 - a.y1
    if b.y1 < a.y0:
        return a.y0 - b.y1
    return 0.0


def _hoverlap(a, b) -> bool:
    return min(a.x1, b.x1) - max(a.x0, b.x0) > 0


def _quant(c):
    if c is None:
        return None
    return tuple(int(round(v * 15)) for v in c[:3])


def page_graphics(page, drawings):
    """Return list of (rect, kind) of graphic elements: vector paths + images."""
    pr = page.rect
    out = []
    for d in drawings:
        r = fitz.Rect(d.get("rect", fitz.Rect()))
        if r.is_empty and r.width < 0.5 and r.height < 0.5:
            continue
        # full-page backgrounds / page frames are noise
        if r.width > 0.95 * pr.width and r.height > 0.9 * pr.height:
            continue
        # white fills without stroke carry no information
        fill = d.get("fill")
        if d.get("color") is None and fill is not None and min(fill[:3]) > 0.98:
            continue
        # tiny hairlines used for footnote rules etc. are still graphics; keep
        if r.width < 0.5:
            r.x1 = r.x0 + 0.5
        if r.height < 0.5:
            r.y1 = r.y0 + 0.5
        out.append((r, "vec"))
    try:
        infos = page.get_image_info()
    except Exception:
        infos = []
    for info in infos:
        r = fitz.Rect(info["bbox"])
        if r.width < 8 or r.height < 8:
            continue
        out.append((r, "img"))
    return out


def text_blocks(page):
    d = page.get_text("dict")
    blocks = []
    for b in d.get("blocks", []):
        if b.get("type", 0) != 0:
            continue
        lines = b.get("lines", [])
        txt = "\n".join("".join(s["text"] for s in ln.get("spans", [])) for ln in lines).strip()
        if not txt:
            continue
        sizes = [s["size"] for ln in lines for s in ln.get("spans", []) if s["text"].strip()]
        first_span_font = ""
        for ln in lines:
            for s in ln.get("spans", []):
                if s["text"].strip():
                    first_span_font = s.get("font", "")
                    break
            if first_span_font:
                break
        blocks.append({
            "rect": fitz.Rect(b["bbox"]),
            "text": txt,
            "nlines": len(lines),
            "size": float(np.median(sizes)) if sizes else 0.0,
            "font0": first_span_font,
        })
    return blocks


def find_captions(blocks):
    caps = []
    for i, b in enumerate(blocks):
        first = b["text"].split("\n", 1)[0]
        m = CAPTION_RE.match(first)
        if not m:
            continue
        bold = "bold" in b["font0"].lower() or ".b" in b["font0"].lower() or "cmbx" in b["font0"].lower()
        rest = (m.group("rest") or "").strip()
        # "Fig. 3 shows ..." inside running text: no punctuation, not bold -> skip
        if not m.group("punct") and not bold:
            continue
        if m.group("label").startswith("图") is False and rest[:1].islower() and not m.group("punct"):
            continue
        caps.append((i, m.group("label").strip(), b))
    return caps


def body_text_width(blocks, page):
    widths = [b["rect"].width for b in blocks if b["nlines"] >= 3]
    if not widths:
        return page.rect.width * 0.7
    return float(np.percentile(widths, 90))


def is_body_paragraph(b, tw, gfx_rects):
    """A running-text paragraph: wide, several lines, not sitting on graphics."""
    r = b["rect"]
    if b["nlines"] < 2 or r.width < 0.72 * tw:
        return False
    inter = sum((r & g).get_area() for g in gfx_rects if r.intersects(g))
    return inter < 0.15 * max(r.get_area(), 1)


def compute_clip(page, cap_block, blocks, gfx, caption_rects, tw):
    """Grow a cluster of graphics adjacent to the caption. Returns (rect, above?)."""
    cap = cap_block["rect"]
    gfx_rects = [g for g, _ in gfx]
    body = [b["rect"] for b in blocks if is_body_paragraph(b, tw, gfx_rects)]

    def try_dir(above: bool):
        if above:
            limit = page.rect.y0 + 20
            for r in body + [c for c in caption_rects if c != cap]:
                if r.y1 <= cap.y0 + 1 and r.y1 > limit:
                    limit = r.y1
            cand = [g for g in gfx_rects if g.y1 <= cap.y0 + 4 and g.y0 >= limit - 2]
            seed = [g for g in cand if cap.y0 - g.y1 < 40]
        else:
            limit = page.rect.y1 - 20
            for r in body + [c for c in caption_rects if c != cap]:
                if r.y0 >= cap.y1 - 1 and r.y0 < limit:
                    limit = r.y0
            cand = [g for g in gfx_rects if g.y0 >= cap.y1 - 4 and g.y1 <= limit + 2]
            seed = [g for g in cand if g.y0 - cap.y1 < 40]
        if not seed:
            return None
        cl = _union(seed)
        rest = [g for g in cand if g not in seed]
        changed = True
        while changed:
            changed = False
            keep = []
            for g in rest:
                if _vgap(cl, g) < 14 and (_hoverlap(cl, g) or g.width < 50 or cl.width < 50):
                    cl |= g
                    changed = True
                else:
                    keep.append(g)
            rest = keep
        return cl

    above = try_dir(True)
    below = try_dir(False)
    choice, is_above = None, True
    if above is not None and below is not None:
        choice, is_above = (above, True) if above.get_area() >= below.get_area() * 0.6 else (below, False)
    elif above is not None:
        choice = above
    elif below is not None:
        choice, is_above = below, False
    if choice is None:
        # text-only figure (e.g. an unframed algorithm listing): take the band
        # between the previous body paragraph and the caption, if non-trivial
        limit = page.rect.y0 + 30
        for r in body:
            if r.y1 <= cap.y0 and r.y1 > limit:
                limit = r.y1
        if cap.y0 - limit > 40:
            choice = fitz.Rect(page.rect.x0 + 40, limit + 2, page.rect.x1 - 40, cap.y0 - 1)
            return choice, True, "text-only"
        return None, True, "no-graphics"
    # add label text lying inside / touching the cluster (axis labels, legends)
    for b in blocks:
        r = b["rect"]
        if r == cap or is_body_paragraph(b, tw, gfx_rects):
            continue
        if CAPTION_RE.match(b["text"].split("\n", 1)[0]):
            continue
        near = (r & (choice + (-14, -18, 14, 18))).get_area() > 0.5 * r.get_area()
        if near:
            if is_above and r.y0 >= cap.y0:
                continue
            if not is_above and r.y1 <= cap.y1:
                continue
            choice |= r
    choice = (choice + (-4, -4, 4, 4)) & page.rect
    return choice, is_above, ""


# --------------------------------------------------------------------------
# Statistics, classification, quality
# --------------------------------------------------------------------------
def region_stats(page, clip, drawings, blocks, pix):
    st = {"n_line": 0, "n_curve": 0, "n_rect": 0, "n_quad": 0, "n_paths": 0,
          "n_filled_rects": 0, "n_hlines": 0, "n_vlines": 0, "n_diag": 0, "n_arrowheads": 0,
          "n_ticks": 0, "n_hticks": 0, "n_vticks": 0, "n_images": 0, "img_eff_dpi": 0.0, "vector_colors": 0, "words": 0,
          "text_density": 0.0, "whitespace": 0.0, "pixel_colors": 0, "aspect": 0.0,
          "rect_width_cv": 0.0, "grid_like": False, "xor_symbols": 0, "math_chars": 0}
    colors = set()
    fr_widths = []
    fr_x = []
    fr_y = []
    all_x, all_y = [], []
    for d in drawings:
        r = fitz.Rect(d.get("rect", fitz.Rect()))
        if not clip.intersects(r) and not clip.contains(r):
            continue
        st["n_paths"] += 1
        for c in (d.get("color"), d.get("fill")):
            q = _quant(c)
            if q is not None:
                colors.add(q)
        items = d.get("items", [])
        n_l = 0
        for it in items:
            op = it[0]
            if op == "l":
                st["n_line"] += 1
                n_l += 1
                p1, p2 = it[1], it[2]
                dx, dy = abs(p2.x - p1.x), abs(p2.y - p1.y)
                if dy < 0.5 and 1 < dx <= 5:
                    st["n_hticks"] += 1
                    st["n_ticks"] += 1
                elif dx < 0.5 and 1 < dy <= 5:
                    st["n_vticks"] += 1
                    st["n_ticks"] += 1
                if dy < 0.5 and dx > 2:
                    st["n_hlines"] += 1
                elif dx < 0.5 and dy > 2:
                    st["n_vlines"] += 1
                elif dx > 1 and dy > 1:
                    st["n_diag"] += 1
            elif op == "c":
                st["n_curve"] += 1
            elif op == "re":
                st["n_rect"] += 1
                all_x.append(round(it[1].x0, 0))
                all_y.append(round(it[1].y0, 0))
                if d.get("fill") is not None:
                    st["n_filled_rects"] += 1
                    rr = it[1]
                    fr_widths.append(rr.width)
                    fr_x.append(round(rr.x0, 0))
                    fr_y.append(round(rr.y0, 0))
            elif op == "qu":
                st["n_quad"] += 1
        # small filled triangle = arrowhead
        if d.get("fill") is not None and n_l in (2, 3) and len(items) <= 4 and r.width < 9 and r.height < 9:
            st["n_arrowheads"] += 1
    st["vector_colors"] = len(colors)
    if fr_widths:
        w = np.array(fr_widths)
        st["rect_width_cv"] = float(np.std(w) / (np.mean(w) + 1e-9))
        # grid: many distinct x and y positions, both repeated
        if len(fr_widths) >= 16 and len(set(fr_x)) >= 4 and len(set(fr_y)) >= 4:
            st["grid_like"] = len(fr_widths) >= 0.5 * len(set(fr_x)) * len(set(fr_y))
    if len(all_x) >= 25:
        nx, ny = len(set(all_x)), len(set(all_y))
        if nx >= 4 and ny >= 4 and len(all_x) >= 0.5 * nx * ny:
            st["grid_like"] = True
    dpi_list = []
    try:
        for info in page.get_image_info():
            r = fitz.Rect(info["bbox"])
            if not clip.intersects(r):
                continue
            st["n_images"] += 1
            if r.width > 1:
                dpi_list.append(info.get("width", 0) / (r.width / 72.0))
    except Exception:
        pass
    if dpi_list:
        st["img_eff_dpi"] = float(min(dpi_list))
    words = page.get_text("words", clip=clip)
    st["words"] = len(words)
    area_in2 = max(clip.get_area() / (72.0 * 72.0), 1e-3)
    st["text_density"] = len(words) / area_in2
    txt = " ".join(w[4] for w in words)
    st["xor_symbols"] = txt.count("⊕") + txt.count("⊞") + txt.count("⊗")
    st["math_chars"] = sum(1 for ch in txt if ch in "∑∏∈≤≥←→⇒∀∃λσπ⌈⌉⌊⌋·×")
    st["aspect"] = clip.width / max(clip.height, 1)
    if pix is not None:
        a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[..., :3]
        st["whitespace"] = float((a.min(axis=2) > 245).mean())
        q = (a[::3, ::3] // 32).reshape(-1, 3)
        uniq, cnt = np.unique(q, axis=0, return_counts=True)
        st["pixel_colors"] = int((cnt > 0.002 * q.shape[0]).sum())
    return st


def classify(caption: str, st: dict) -> tuple[str, dict]:
    s = {t: 0.0 for t in TYPES}
    cap = caption.lower()
    for t, pats in KEYWORDS_C.items():
        for rx, w in pats:
            if rx.search(cap):
                s[t] += 1.3 * w
    nl, nc, nr = st["n_line"], st["n_curve"], st["n_rect"]
    tot = nl + nc + nr + st["n_quad"]
    td = st["text_density"]  # words per square inch; running text is ~15-25
    # an x-axis has vertical ticks, a y-axis horizontal ones; arrowheads drawn as
    # short strokes are diagonal, so requiring both kinds filters most diagrams
    # text converted to outlines produces thousands of curves and spurious
    # "ticks"; treat such regions as non-plots
    axes = (st["n_hticks"] >= 3 and st["n_vticks"] >= 3 and st["n_ticks"] <= 200
            and nc < 800 and st["n_arrowheads"] < 3)
    if tot == 0 and st["n_images"] > 0:
        s["other"] += 1.0  # pure raster: rely on caption
    if st["grid_like"]:
        s["heatmap-matrix"] += 4.0
    elif st["n_filled_rects"] >= 5 and st["rect_width_cv"] < 0.15:
        s["plot-bar"] += 3.0 if axes else 1.5
    if axes and not st["grid_like"]:
        s["plot-line"] += 1.5
        if st["n_diag"] > 20 or nc > 30 or st["n_hlines"] > 30:
            s["plot-line"] += 1.5
    elif st["n_diag"] > 60:
        s["plot-line"] += 1.0
    if st["n_filled_rects"] >= 30 and st["vector_colors"] >= 5 and not axes:
        s["heatmap-matrix"] += 1.5
    if st["n_hlines"] >= 4 and st["n_hlines"] > 2 * max(st["n_vlines"], 1) and td > 10 and nc < 5 and not axes:
        s["table-like"] += 2.5
    if st["n_arrowheads"] >= 2 and st["n_hlines"] >= 2 and td > 6 and not axes:
        s["protocol-flow"] += 1.5
    if st["n_arrowheads"] >= 3 and 3 <= nr <= 60 and not axes:
        s["architecture-pipeline"] += 2.0
    if st["xor_symbols"] >= 2 or (nc > 20 and st["n_vlines"] > 10 and nr > 4 and "round" in cap):
        s["circuit-cipher"] += 2.5
    if nc > 20 and st["n_diag"] > 3 and td < 5 and st["n_filled_rects"] < 5 and not axes:
        s["lattice-geometric"] += 1.0
        s["tree-graph"] += 1.0
    if nr <= 3 and td > 12 and st["n_diag"] < 5 and nc < 10 and not axes:
        s["pseudocode-box"] += 2.5
    if st["math_chars"] > 15 and td > 10:
        s["pseudocode-box"] += 1.0
        s["protocol-flow"] += 0.5
    # scaling curves are line plots with log/scal words
    if s["plot-scaling"] > 0:
        s["plot-scaling"] += 0.5 * (s["plot-line"] > 0)
    best = max(s, key=lambda k: s[k])
    if s[best] < 1.0:
        best = "other"
    return best, {k: round(v, 2) for k, v in s.items() if v > 0}


def quality(st: dict, clip, page_rect, ftype: str) -> float:
    q = 50.0
    vec = st["n_paths"] > 0 and st["n_images"] == 0
    if vec:
        q += 20
    elif st["n_images"]:
        dpi = st["img_eff_dpi"]
        q += 15 if dpi >= 300 else (5 if dpi >= 150 else -15)
    pc = st["pixel_colors"]
    if ftype != "heatmap-matrix":
        if 2 <= pc <= 7:
            q += 10
        elif pc > 14:
            q -= 10
    ws = st["whitespace"]
    if 0.45 <= ws <= 0.9:
        q += 10
    elif ws > 0.96 or ws < 0.3:
        q -= 15
    frac_w = clip.width / page_rect.width
    if frac_w < 0.2 or clip.height < 50:
        q -= 20
    if st["text_density"] > 30:
        q -= 5
    return float(max(0.0, min(100.0, q)))


# --------------------------------------------------------------------------
# Per-file worker
# --------------------------------------------------------------------------
def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def text_fingerprint(path) -> str:
    """Hash of the normalised first-page text: catches the same paper saved twice
    under different names / with different metadata."""
    try:
        with fitz.open(path) as d:
            if len(d) == 0:
                return ""
            t = re.sub(r"\W+", "", d[0].get_text()[:3000]).lower()
        return "txt:" + hashlib.sha1(t.encode()).hexdigest() if len(t) > 200 else ""
    except Exception:
        return ""


def _slug(s: str, n=40) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-")
    return s[:n] or "pdf"


def process_pdf(path: str, out_dir: str, dpi: int, max_pages: int, sha: str) -> list[dict]:
    doc = fitz.open(path)
    recs: list[dict] = []
    stem = _slug(Path(path).stem) + "_" + sha[:6]
    for pno in range(min(len(doc), max_pages)):
        page = doc[pno]
        try:
            blocks = text_blocks(page)
            caps = find_captions(blocks)
            if not caps:
                continue
            drawings = page.get_drawings()
            gfx = page_graphics(page, drawings)
            tw = body_text_width(blocks, page)
            cap_rects = [b["rect"] for _, _, b in caps]
            for k, (bi, label, cb) in enumerate(caps):
                clip, above, note = compute_clip(page, cb, blocks, gfx, cap_rects, tw)
                if clip is None or clip.width < 80 or clip.height < 40:
                    continue
                pix = page.get_pixmap(clip=clip, dpi=dpi, alpha=False)
                name = f"{stem}_p{pno + 1:03d}_{k}.png"
                pix.save(os.path.join(out_dir, "img", name))
                st = region_stats(page, clip, drawings, blocks, pix)
                caption = " ".join(cb["text"].split())
                ftype, scores = classify(caption, st)
                if note == "text-only" and ftype == "other":
                    ftype = "pseudocode-box"
                qv = quality(st, clip, page.rect, ftype)
                if note == "text-only":
                    qv -= 10
                recs.append(asdict(FigRecord(
                    source_pdf=path, source_sha1=sha, page=pno + 1, fig_label=label,
                    caption=caption[:600], png=f"img/{name}", clip=[round(v, 1) for v in clip],
                    caption_above=not above, type=ftype, type_scores=scores,
                    quality=round(qv, 1), stats=st, notes=note)))
        except Exception as e:  # keep going on odd pages
            recs.append({"source_pdf": path, "page": pno + 1, "error": repr(e)[:200]})
    doc.close()
    return recs


def _child(path, out_dir, dpi, max_pages, sha, tmp_json):
    try:
        recs = process_pdf(path, out_dir, dpi, max_pages, sha)
        with open(tmp_json, "w") as f:
            json.dump(recs, f)
    except Exception as e:
        with open(tmp_json, "w") as f:
            json.dump([{"source_pdf": path, "error": repr(e)[:300]}], f)


def _excluded(sp: str, excludes) -> bool:
    for pat in excludes:
        if pat.startswith("re:"):
            if re.search(pat[3:], sp):
                return True
        elif fnmatch.fnmatch(sp, f"*{pat}*"):
            return True
    return False


def harvest(roots, out, excludes=(), dpi=200, timeout=90, max_pages=80, jobs=4, verbose=True):
    if fitz is None:
        raise SystemExit("PyMuPDF (fitz) is required: pip install pymupdf")
    out = Path(out)
    (out / "img").mkdir(parents=True, exist_ok=True)
    files = []
    seen = set()
    skipped_dupe = 0
    for root in roots:
        rp = Path(root)
        cands = [rp] if rp.is_file() else sorted(rp.rglob("*.pdf")) + sorted(rp.rglob("*.PDF"))
        for p in cands:
            if not p.is_file() or _excluded(str(p), excludes):
                continue
            try:
                sha = sha1_of(p)
            except OSError:
                continue
            fp = text_fingerprint(p)
            if sha in seen or (fp and fp in seen):
                skipped_dupe += 1
                continue
            seen.add(sha)
            if fp:
                seen.add(fp)
            files.append((str(p), sha))
    if verbose:
        print(f"[harvest] {len(files)} unique PDFs ({skipped_dupe} duplicates skipped)", file=sys.stderr)
    all_recs, errors = [], []
    tmpdir = tempfile.mkdtemp(prefix="harvest_")
    ctx = mp.get_context("fork") if hasattr(os, "fork") else mp.get_context()
    running: list[tuple] = []
    queue = list(files)
    while queue or running:
        while queue and len(running) < jobs:
            path, sha = queue.pop(0)
            tj = os.path.join(tmpdir, sha + ".json")
            pr = ctx.Process(target=_child, args=(path, str(out), dpi, max_pages, sha, tj))
            pr.start()
            running.append((pr, path, tj, time.time()))
        time.sleep(0.05)
        still = []
        for pr, path, tj, t0 in running:
            if pr.is_alive():
                if time.time() - t0 > timeout:
                    pr.kill()
                    pr.join()
                    errors.append({"source_pdf": path, "error": f"timeout>{timeout}s"})
                    if verbose:
                        print(f"[harvest] TIMEOUT {path}", file=sys.stderr)
                else:
                    still.append((pr, path, tj, t0))
                continue
            pr.join()
            if os.path.exists(tj):
                with open(tj) as f:
                    recs = json.load(f)
                good = [r for r in recs if "error" not in r]
                errors += [r for r in recs if "error" in r]
                all_recs += good
                if verbose:
                    print(f"[harvest] {len(good):3d} figs  {path}", file=sys.stderr)
            else:
                errors.append({"source_pdf": path, "error": f"worker crashed (exit {pr.exitcode})"})
        running = still
    all_recs.sort(key=lambda r: (r["type"], -r["quality"]))
    with open(out / "index.json", "w") as f:
        json.dump({"figures": all_recs, "errors": errors,
                   "generated": time.strftime("%Y-%m-%d %H:%M:%S")}, f, indent=1, ensure_ascii=False)
    with open(out / "index.csv", "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL, escapechar="\\")
        clean = lambda x: re.sub(r"[\x00-\x1f\x7f]", " ", str(x))
        w.writerow(["type", "quality", "source_pdf", "page", "fig_label", "png", "caption"])
        for r in all_recs:
            w.writerow([r["type"], r["quality"], r["source_pdf"], r["page"], r["fig_label"], r["png"], clean(r["caption"][:200])])
    counts = {}
    for r in all_recs:
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    if verbose:
        print(f"[harvest] total {len(all_recs)} figures, {len(errors)} errors", file=sys.stderr)
        for t in TYPES:
            if t in counts:
                print(f"    {t:24s} {counts[t]}", file=sys.stderr)
    return all_recs, errors, counts


# --------------------------------------------------------------------------
# Self-test: synthetic PDF with a vector bar chart + caption
# --------------------------------------------------------------------------
def selftest() -> None:
    assert fitz is not None, "PyMuPDF missing"
    tmp = Path(tempfile.mkdtemp(prefix="harvest_selftest_"))
    pdf = tmp / "synthetic.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    body = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 6).strip()
    page.insert_textbox(fitz.Rect(72, 72, 523, 160), body, fontsize=10)
    # bars
    x = 150
    for h in (60, 90, 40, 120, 75, 100):
        page.draw_rect(fitz.Rect(x, 330 - h, x + 30, 330), color=None, fill=(0.16, 0.47, 0.84))
        x += 45
    page.draw_line((140, 330), (430, 330))
    page.draw_line((140, 200), (140, 330))
    for y in range(210, 331, 30):
        page.draw_line((136, y), (140, y))
    page.insert_text((180, 350), "n=1  n=2  n=3  n=4  n=5  n=6", fontsize=8)
    page.insert_text((72, 375), "Fig. 1. Speedup of the toy scheme over the baseline (bar chart).", fontsize=9)
    page.insert_textbox(fitz.Rect(72, 400, 523, 500), body, fontsize=10)
    doc.save(pdf)
    doc.close()
    out = tmp / "gal"
    recs, errs, counts = harvest([str(tmp)], out, verbose=False, jobs=1)
    assert not errs, errs
    assert len(recs) == 1, recs
    r = recs[0]
    assert r["type"] == "plot-bar", r["type_scores"]
    assert (out / r["png"]).exists()
    assert r["clip"][1] < 230 and r["clip"][3] <= 372, r["clip"]
    print("selftest OK:", r["type"], "quality", r["quality"], "clip", r["clip"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", help="PDF files or directories (searched recursively)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "gallery"),
                    help="output gallery directory (default: figures/gallery, gitignored)")
    ap.add_argument("--exclude", action="append", default=[],
                    help="glob substring (or 're:REGEX') of paths to skip; repeatable")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--timeout", type=int, default=90, help="seconds per PDF")
    ap.add_argument("--max-pages", type=int, default=80)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return
    if not a.roots:
        ap.error("give at least one corpus directory (or --selftest)")
    harvest(a.roots, a.out, a.exclude, a.dpi, a.timeout, a.max_pages, a.jobs)


if __name__ == "__main__":
    main()
