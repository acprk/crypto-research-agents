# REVIEWS — mock and real reviews (owner: `reviewer-sim`) — TEACHING EXAMPLE

All reviews below are **simulated** by `reviewer-sim` (skills `venue-calibration`, `mock-review`,
workflow `workflows/mock-review-panel.js`) on `paper/main.pdf`. No real reviewer was involved.

## Round 1 — 2026-09-25 — venue profile: mock "LNCS short paper" (applied-crypto workshop)

| persona | score | confidence | top-3 weaknesses | action item → agent |
|---|---|---|---|---|
| expert-skeptic (FHE implementer) | weak accept | 4/5 | (1) "3.86× is close to 4 — is the extra work per LUT really negligible, or only at k = 4?" (2) Python timings on a shared machine: wall or CPU? (3) no novelty over CIM19 | R1-1 → writer: add the k = 64 saturation sentence with E9 (Section 4, "Speed"). R1-2 → writer: state CPU time + reason in Setup (DECISIONS D-4). R1-3: none — the paper already disclaims novelty (intro, last line). |
| generalist (symmetric-crypto reader) | accept | 3/5 | (1) why not a single PBS returning the nibble? (2) what is ‖d_f‖ intuitively? (3) figure (b) legend: which curve is the model? | R1-4 → writer: add the "nibble output ⇒ one PBS suffices" sentence to the intro (DECISIONS D-1). R1-5 → figure-artist: say "dotted: model" in panel title and caption. Item (2) answered by Lemma 2 wording ("number of value changes"); no change. |
| data / desk-reject auditor | accept | 4/5 | (1) every number traceable? (2) is the CMux-tree comparison fair? (3) page budget | Checked `paper/audit-tex.log` (0 errors) and `gate-check.log`; C5 refuted → vpack appears only as a remark without a number (confirmed in Section 4). 5 pages incl. references and appendix: OK. No action. |

### Meta-review (reviewer-sim)
Consensus: accept as a teaching note. The only substantive risk was an implied linear speed-up;
the falsifier's C3 → C6 replacement already fixes it once R1-1 is applied. Routed items:
R1-1, R1-2, R1-4 → `writer`; R1-5 → `figure-artist`. PI decision: DECISIONS D-6 (one loop to P7).

### Closure (2026-09-25)
| item | closed by | where | verified |
|---|---|---|---|
| R1-1 | writer | paper/sections/experiments.tex, "Speed" paragraph (43.67×, E9) | audit-tex 0 errors |
| R1-2 | writer | paper/sections/experiments.tex, "Setup" paragraph | – |
| R1-3 | – | no change (novelty disclaimer present) | – |
| R1-4 | writer | paper/sections/intro.tex, 2nd paragraph | – |
| R1-5 | figure-artist | code/make_figures.py panel (b) title; figure caption | figure re-rendered |
