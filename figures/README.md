# figures/ -- house style, templates, harvester

```
style/        crypto.mplstyle + lncs/acm/ieee.mplstyle, palette.py (colours, sizes, save, CVD check)
templates/    p01..p16 matplotlib templates (synthetic data) + run_all.py
templates/tikz/  protocol_flow, pipeline, spn_round, lattice_basis, commutative_diagram
              + crypto-tikz.sty + Makefile
examples/     rendered outputs of every template (PDF + PNG), committed; all ours
harvester/    harvest.py (PDF corpus -> figure crops + index), gallery.py (HTML contact sheet)
PATTERNS.md   pattern catalog in words: when to use, anatomy, pitfalls, template
tests/        pytest smoke tests
gallery/      DEFAULT HARVEST OUTPUT -- gitignored, never commit
```

Requirements: Python >= 3.10 with numpy and matplotlib. The harvester also
needs PyMuPDF (`pip install pymupdf`). The TikZ templates and the table
preview need TeX Live (`latexmk`, `pdflatex`, `tikz-cd`, `booktabs`) and
`pdftoppm` (poppler).

## 1. Use the house style in a paper

```python
import sys; sys.path.insert(0, "figures/style")
import palette as P

fig, ax = P.figure("lncs", width="full", aspect=0.45)   # 4.80 in wide = LNCS \textwidth
ax.plot(x, t_ours, **P.line_style(0), label="ours")     # blue + marker + solid
ax.plot(x, t_base, **P.baseline_style(0), label="prior")  # grey + other marker/dash
P.save(fig, "fig_speedup", outdir="paper/figs")          # fig_speedup.pdf + .png
```

In LaTeX, include the figure at the size it was made:
`\includegraphics[width=\textwidth]{figs/fig_speedup}` for LNCS, or
`\columnwidth` for a `width="column"` ACM/IEEE figure. Do not rescale, or the
7-8 pt figure text will no longer match the caption.

| venue | column | full width | font in figures |
|---|---|---|---|
| `lncs` (llncs) | 4.80 in (12.2 cm), single column | 4.80 in | Computer Modern (bundled `cmr10` + cm mathtext) |
| `acm` (acmart sigconf) | 3.33 in | 7.00 in | Libertine if installed, else STIX (Times-like) |
| `ieee` (IEEEtran) | 3.50 in | 7.16 in | TeX Gyre Termes / Times if installed, else STIX |

Pure style-sheet use: `plt.style.use(["figures/style/crypto.mplstyle", "figures/style/lncs.mplstyle"])`.

The colours are a validated 8-slot categorical order. Adjacent pairs keep an
OKLab dE of at least 9 under simulated protan/deutan vision. Ours = slot 1
(blue), and baselines use `BASELINE_GREYS`. Sequential data uses `SEQ_BLUE`,
and diverging data uses `DIVERGING` (blue-grey-red). Run `python3
figures/style/palette.py` to re-check the palette after any change.

## 2. Templates

```bash
python3 figures/templates/run_all.py               # all p*.py -> figures/examples/
python3 figures/templates/p04_param_feasibility.py --venue ieee --out /tmp/x
make -C figures/templates/tikz                     # TikZ -> figures/examples/tikz_*.{pdf,png}
```

Copy a template into your project and replace the synthetic arrays with data
loaded from `results/` (every number needs an EVIDENCE row). Pattern-to-
template mapping and design notes are in `PATTERNS.md`.

| id | template | pattern |
|---|---|---|
| C1 | p01_speedup_bars | speed-up bars, baseline = 1 line |
| C2 | p02_breakdown_stacked | stacked stage breakdown (not pies) |
| C3 | p03_scaling_loglog | log-log scaling with O(.) guides |
| C4 | p04_param_feasibility | parameter-plane feasibility region |
| C5 | p05_pareto_tradeoff | Pareto front |
| C6 | p06_noise_waterfall | noise-budget waterfall |
| C7 | p07_modulus_layout | ciphertext / modulus bit layout |
| C8 | p08_sbox_ddt_heatmap | DDT/LAT heatmap |
| C9 | p09_trail_bounds | trail bound vs rounds, security margin |
| C10 | p10_error_distribution | error histogram, log tails, failure prob. |
| C11 | p11_approx_error | approximation + log error |
| C12 | p12_crossover_cost | cost-model crossover |
| C13 | p13_sparsity_pattern | matrix sparsity small multiples |
| C14 | p14_param_sweep_heatmap | parameter sweep heatmap |
| C15 | p15_bench_distribution | repeated-run A/B distributions |
| C16 | p16_results_table | booktabs table, best bold |
| D1-D5 | tikz/*.tex | protocol flow, pipeline, SPN round, lattice, commutative diagram |

## 3. Harvester (learn from published figures, locally)

```bash
python3 figures/harvester/harvest.py PAPERS_DIR [MORE_DIRS_OR_PDFS ...] \
    --out /tmp/crypto_gallery --exclude drafts --exclude 're:[Oo]urs' --jobs 8 --timeout 90
python3 figures/harvester/gallery.py /tmp/crypto_gallery   # -> /tmp/crypto_gallery/index.html
python3 figures/harvester/harvest.py --selftest
```

For each PDF, the harvester does the following:

1. It finds caption blocks ("Fig. 3.", "Figure 3:", "图 3").
2. It grows a clip rectangle from the vector drawings (`page.get_drawings()`)
   and embedded images adjacent to the caption, above it first and then
   below. Growth stops at running-text paragraphs and other captions, and
   the clip then absorbs nearby label text.
3. It renders the clip at 200 dpi.
4. It records drawing statistics: lines, curves, rects, filled rects, axis
   ticks, arrowheads, colours, text density, whitespace and effective
   raster dpi.
5. It classifies the figure into one of: plot-bar, plot-line,
   plot-scaling, table-like, protocol-flow, architecture-pipeline,
   circuit-cipher, lattice-geometric, heatmap-matrix, tree-graph,
   pseudocode-box or other. Classification combines caption keywords with
   these statistics.
6. It scores quality from 0 to 100, favouring vector content, 300+ dpi
   rasters, 2-7 colours, balanced whitespace and a reasonable size.

Outputs are `index.json` (full stats), `index.csv` and `img/*.png`. Each PDF
runs in its own process with a timeout, and broken PDFs are logged under
`errors`. Duplicates are skipped by file hash and by a first-page text
fingerprint.

The classifier is a heuristic. Expect roughly 70% correct labels. Glyphs
drawn as outlines and raster-only figures fall back to caption keywords.
Use the gallery to browse, not as ground truth.

**Copyright:** harvested crops belong to their authors. Keep the gallery
local (`figures/gallery/` is gitignored; `/tmp/...` is better). Only commit
patterns described in your own words (`PATTERNS.md`,
`gallery_index.template.md`), citing public ePrint IDs.

## 4. Tests

```bash
python3 -m pytest figures/tests -q    # palette check, harvester/gallery self-tests, all templates render
```
