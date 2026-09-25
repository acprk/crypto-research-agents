# Local figure gallery -- index template

The harvested gallery (`figures/gallery/` by default, or any `--out` directory)
is **never committed**: the images belong to their authors.  Commit only notes
written in your own words, e.g. in `figures/PATTERNS.md` or in a project's
`paper/figs/NOTES.md`, using this template.

| # | pattern (see PATTERNS.md) | source (public ePrint ID, fig.) | what works | what to avoid | template |
|---|---|---|---|---|---|
| 1 | C1 speed-up bars | e.g. 20XX/NNNN Fig. 3 | baseline is a line, not a bar | value on every bar | p01 |

Regenerate the gallery:

    python3 figures/harvester/harvest.py CORPUS_DIR --out /tmp/crypto_gallery
    python3 figures/harvester/gallery.py /tmp/crypto_gallery   # open index.html
