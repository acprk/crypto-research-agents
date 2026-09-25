# crbench — benchmark harness for crypto research

Dependency-light (numpy only). Python >= 3.10.

```bash
pip install -e lib/bench          # or: PYTHONPATH=lib/bench python3 -m crbench ...
crbench run -a base='./bench_old --toy' -a new='./bench_new --toy' \
            -n 7 -w 1 --parser generic --threads 1 --cpus 2 --log-dir results/toy-ab --target ./build
crbench table results/toy-ab/run.json --latex --evidence new:speedup=E3
crbench evidence add EVIDENCE.md --printed '2.02×' --command 'derived: E1/E2' --log -
crbench evidence check EVIDENCE.md --root .
crbench audit-tex paper/main.tex EVIDENCE.md      # exit 1 if any number is untraced
crbench stale build/bench src/                    # exit 1 if a source is newer than the binary
crbench parsers ; crbench adapters
```

| module | purpose |
|---|---|
| `stats` | median, IQR, bootstrap CI, speed-up of medians with (paired) bootstrap CI |
| `runner` | interleaved rounds (alternate / shuffle / fixed), warm-up, repeats, timeout, thread vars, `taskset` pinning, per-execution logs + `run.json`, failures kept in the ledger |
| `envcapture` | CPU / governor / load / compilers / git commit+dirty of target / perf env vars; warnings |
| `lock` | advisory `flock` so benches never overlap |
| `parsers` | registry: generic, criterion, gobench, gbench, helib, openfhe, lattice-estimator, sat, mpspdz, gnu-time; `register_parser`, `regex_parser` |
| `tables` | Markdown + LaTeX booktabs; cells carry EVIDENCE IDs (`\evid{E3}`) |
| `evidence` | EVIDENCE.md reader/writer/validator; `audit_tex` |
| `adapters` | per-library recipe: parser + typical command + fairness note |

## audit-tex rules

A number is *measurement-like* if it has a decimal point, a thousands separator, a
unit right after it (`s ms µs MB KiB bits × % cycles rounds` ...), or is an exponent
(`2^{128}`). Each such number in the document body must appear in the printed column
of some EVIDENCE.md row (numeric match after normalisation: `1{,}536` = `1,536` =
`1536`; `2.50` = `2.5`). `\evid{ID}` tags additionally check the preceding number
against that specific row. Escape hatches: `% crbench:ignore` on a line, or a
`% crbench:ignore-begin` / `% crbench:ignore-end` block — each use should be
justified in the ledger or DECISIONS.md. `--strict` audits bare integers too.

Tests: `python3 -m pytest -q lib/bench/tests` (or `python3 -m unittest discover -s lib/bench/tests`).
