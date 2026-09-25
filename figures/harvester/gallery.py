#!/usr/bin/env python3
"""gallery.py -- build a local HTML contact sheet from a harvest index.

    python3 gallery.py /tmp/crypto_gallery            # writes /tmp/crypto_gallery/index.html
    python3 gallery.py GALLERY --min-quality 60 --top 40
    python3 gallery.py --selftest

Figures are grouped by heuristic type and sorted by quality score.  The page
is fully static (no network), has a type filter and a quality slider.  The
gallery is for local study only -- never commit or publish it.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import tempfile
from pathlib import Path

TYPE_ORDER = [
    "plot-bar", "plot-line", "plot-scaling", "heatmap-matrix", "table-like",
    "protocol-flow", "architecture-pipeline", "circuit-cipher", "lattice-geometric",
    "tree-graph", "pseudocode-box", "other",
]

CSS = """
body{font:14px/1.4 system-ui,sans-serif;margin:24px;color:#0b0b0b;background:#fcfcfb}
h1{font-size:20px;margin:0 0 8px} h2{font-size:16px;margin:28px 0 8px;border-bottom:1px solid #ddd}
.controls{position:sticky;top:0;background:#fcfcfb;padding:8px 0;z-index:2;border-bottom:1px solid #eee}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}
.card{background:#fff;border:1px solid #e4e3df;border-radius:6px;padding:8px}
.card img{width:100%;max-height:260px;object-fit:contain;background:#fff;cursor:zoom-in}
.meta{font-size:12px;color:#52514e;margin-top:4px}
.cap{font-size:12px;margin-top:4px;max-height:5.6em;overflow:hidden}
.q{font-weight:600;color:#0b0b0b}
table.counts td{padding:2px 10px}
"""

JS = """
function apply(){
  const t=document.getElementById('type').value, q=+document.getElementById('q').value;
  document.getElementById('qv').textContent=q;
  document.querySelectorAll('.card').forEach(c=>{
    const ok=(t==='all'||c.dataset.type===t)&&(+c.dataset.q>=q);
    c.style.display=ok?'':'none';});
  document.querySelectorAll('section').forEach(s=>{
    s.style.display=(t==='all'||s.dataset.type===t)?'':'none';});
}
"""


def build(gallery_dir: str | os.PathLike, min_quality: float = 0.0, top: int = 0) -> Path:
    gdir = Path(gallery_dir)
    idx = json.loads((gdir / "index.json").read_text())
    figs = [f for f in idx["figures"] if f.get("quality", 0) >= min_quality]
    groups: dict[str, list] = {}
    for f in figs:
        groups.setdefault(f["type"], []).append(f)
    for g in groups.values():
        g.sort(key=lambda f: -f["quality"])
    order = [t for t in TYPE_ORDER if t in groups] + sorted(set(groups) - set(TYPE_ORDER))
    out = ["<!doctype html><html><head><meta charset='utf-8'><title>Figure gallery (local)</title>",
           f"<style>{CSS}</style><script>{JS}</script></head><body>",
           "<h1>Harvested figure gallery &mdash; LOCAL STUDY ONLY (copyright of the authors)</h1>",
           f"<div class='meta'>{len(figs)} figures, generated {html.escape(idx.get('generated', ''))}</div>",
           "<table class='counts'>" + "".join(
               f"<tr><td>{t}</td><td>{len(groups[t])}</td></tr>" for t in order) + "</table>",
           "<div class='controls'>type <select id='type' onchange='apply()'><option>all</option>" +
           "".join(f"<option>{t}</option>" for t in order) +
           "</select> &nbsp; min quality <input id='q' type='range' min='0' max='100' value='0' "
           "oninput='apply()'> <span id='qv'>0</span></div>"]
    for t in order:
        items = groups[t][:top] if top else groups[t]
        out.append(f"<section data-type='{t}'><h2>{t} ({len(groups[t])})</h2><div class='grid'>")
        for f in items:
            st = f.get("stats", {})
            src = html.escape(Path(f["source_pdf"]).name)
            vec = "vector" if st.get("n_paths", 0) and not st.get("n_images") else (
                "raster" if st.get("n_images") else "text")
            out.append(
                f"<div class='card' data-type='{t}' data-q='{f['quality']}'>"
                f"<a href='{html.escape(f['png'])}' target='_blank'><img loading='lazy' src='{html.escape(f['png'])}'></a>"
                f"<div class='meta'><span class='q'>Q {f['quality']:.0f}</span> &middot; {vec} &middot; "
                f"{src} p.{f['page']} &middot; {html.escape(f['fig_label'])}"
                f" &middot; colours {st.get('pixel_colors', '?')} &middot; ws {st.get('whitespace', 0):.2f}</div>"
                f"<div class='cap'>{html.escape(f['caption'])}</div></div>")
        out.append("</div></section>")
    if idx.get("errors"):
        out.append("<h2>errors</h2><ul>" + "".join(
            f"<li>{html.escape(Path(e.get('source_pdf', '?')).name)}: {html.escape(e.get('error', ''))}</li>"
            for e in idx["errors"]) + "</ul>")
    out.append("</body></html>")
    dest = gdir / "index.html"
    dest.write_text("\n".join(out), encoding="utf-8")
    return dest


def selftest() -> None:
    d = Path(tempfile.mkdtemp(prefix="gallery_selftest_"))
    (d / "img").mkdir()
    (d / "img" / "a.png").write_bytes(b"")
    idx = {"generated": "now", "errors": [], "figures": [
        {"type": "plot-bar", "quality": 80, "png": "img/a.png", "source_pdf": "x/y.pdf", "page": 2,
         "fig_label": "Fig. 1", "caption": "Fig. 1. <toy> & bars", "stats": {"n_paths": 3}}]}
    (d / "index.json").write_text(json.dumps(idx))
    p = build(d)
    s = p.read_text()
    assert "plot-bar (1)" in s and "&lt;toy&gt;" in s
    print("selftest OK:", p)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("gallery", nargs="?", help="directory produced by harvest.py")
    ap.add_argument("--min-quality", type=float, default=0.0)
    ap.add_argument("--top", type=int, default=0, help="max figures per type (0 = all)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return
    if not a.gallery:
        ap.error("gallery directory required")
    print(build(a.gallery, a.min_quality, a.top), file=sys.stderr)


if __name__ == "__main__":
    main()
