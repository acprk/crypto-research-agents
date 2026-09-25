# paper/ — toy-mvpbs write-up (TEACHING EXAMPLE)

Generated from `templates/paper/` (LNCS). Owners: `writer` (sections), `figure-artist` (`figs/`).

| file | what |
|---|---|
| `main.tex`, `sections/*.tex` | 5-page LNCS write-up; only survived/weakened claims (C1, C2, C4, C6) |
| `main.pdf` | compiled anonymous build (kept in git: our own output) |
| `figs/fig_speedup_failure.{pdf,png}` | made by `../code/make_figures.py` from `../results/` only |
| `audit-tex.log` | `crbench audit-tex` on main.tex and every section: 0 errors |
| `anon-check.log`, `pdf-checks.log`, `build.log` | anonymisation, PDF checks, LaTeX build |

Build: `make` (uses the TeX tree's `llncs.cls`, else `fetch_llncs.sh`), `make check`, `make anon`.
Bibliography: `\bibliography{../refs}` — single source `../refs.bib` owned by `lit-scout`.
