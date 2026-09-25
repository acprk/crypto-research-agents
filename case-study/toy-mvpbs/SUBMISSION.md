# SUBMISSION — mock LNCS short paper 2026 (owner: `submission-rebuttal`) — TEACHING EXAMPLE

> Full checklist template: `templates/handoff/SUBMISSION.md`. **Nothing is submitted**: this is a
> teaching example, and per AGENTS.md anything that leaves the machine needs the human's approval.

## Venue rules (mock)
- CFP: none (mock profile "LNCS short paper, ≤ 5 pages including references") · read on: n/a
- Template/class: Springer `llncs` from the TeX tree · paper size: letter (A4 if a CFP asks)
- Anonymity: double-blind assumed

## A. Format (desk-reject items)
- [x] correct class, no geometry/font/spacing changes (`pdf_checks.py`: text width ≈ 12.2 cm = LNCS default)
- [x] within limit: 5 pages; body ends p. 4, references start p. 4 (`paper/pdf-checks.log`)
- [x] no overprinting (overlap scan: none); title + abstract on page 1
- [x] all fonts embedded (30 fonts, none missing, no Type 3)

## B. Anonymity
- [x] `anon_check.py` on sections, refs.bib, macros, main.tex, main.pdf, code/, results/ with a private deny-list: **HIGH=0 MEDIUM=0 LOW=3** (3 informational: PDF creator/producer strings, and a template comment mentioning the de-anonymised build) — `paper/anon-check.log`
- [x] PDF metadata empty (title/author/subject/keywords blank)
- [x] no acknowledgements in the anonymous build
- [x] results/ sanitised: home directory → `~`, hostname → `host`; crbench stores only a hashed host id
- [~] anonymous artifact mirror — not applicable (no submission)

## C. Content consistency
- [x] 0 undefined references / citations; no `<<` placeholders; no `\todo`
- [x] every printed number matched to EVIDENCE: `crbench audit-tex` on main.tex + 7 section files, 0 errors (`paper/audit-tex.log`); `gate_check.py --phase P7/P8 --paper paper` PASS (`gate-check.log`)
- [x] abstract ↔ contributions ↔ evaluation use identical numbers (75.4 ms, 291.2 ms, 3.86×, 43.67×, 0/128 → 32/128); the conclusion carries no numbers
- [x] every contribution maps to a CLAIMS row with status survived/weakened (C1, C2, C4, C6); refuted C3/C5 not claimed
- [x] body self-contained without the appendix (appendix = reproduction commands only)

## D. References
- [x] every entry verified by `bib-verify` (8/8 VERIFIED, `bib-verify-report.md`, newer than refs.bib)
- [x] page ranges cross-checked on Crossref; unverified LNCS volume numbers removed rather than guessed

## E. Submission form
- [~] not applicable (mock)

## F. Upload verification
- [~] not applicable (mock). Local PDF sha256 prefix at the time of the check: `d1187f7d580b8c5a`

## Log
| time (UTC) | action | result |
|---|---|---|
| 2026-09-25 | `crbench evidence check EVIDENCE.md --root .` | 22 rows, 0 errors, 0 warnings |
| 2026-09-25 | `crbench audit-tex` (8 files) | 0 errors each |
| 2026-09-25 | `anon_check.py … --deny-file <private>` | HIGH=0 MEDIUM=0 LOW=3 |
| 2026-09-25 | `pdf_checks.py main.pdf --limit 5` | RESULT: OK |
| 2026-09-25 | `gate_check.py --phase P0…P8` | all PASS |
