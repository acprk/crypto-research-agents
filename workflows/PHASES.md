# Phases P0–P8 — the research pipeline

Each phase has an **owner**, **inputs**, **outputs** and a **gate**. The `pi-orchestrator`
only advances `STATE.md` when every gate box is ticked. Any agent can send work *back*.

| Phase | Owner (helpers) | Output | Gate (all must hold) |
|---|---|---|---|
| **P0 Scoping** | pi-orchestrator | `STATE.md` thesis, venue, deadline | thesis is one falsifiable sentence; venue CFP read; kill date set |
| **P1 Literature** | lit-scout (math-librarian) | `LITERATURE.md`, `refs.bib`, `MATH-REFS.md` | matrix ≥ 15 verified works; strongest baseline named; pre-emption search < 7 days old; `bib-verify` passes |
| **P2 Ideation** | idea-miner (falsifier screens) | `IDEAS.md`, first `CLAIMS.md` rows | ≥ 1 idea with cost-model gain and kill criterion; top idea registered as claims |
| **P3 Theory** | theorist (math-librarian) | `THEORY.md`, `lean/` | every lemma numerically checked on small params (`sage-check`); main theorem proof complete; security parameters estimated (`param-estimation`) |
| **P4 Baselines** | baseline-engineer | `baselines/MANIFEST.md` | strongest baseline builds at pinned commit; its published numbers reproduced within tolerance OR discrepancy documented |
| **P5 Experiments** | experimenter | `results/`, `EVIDENCE.md` | interleaved runs, ≥ 3 repeats, medians; env captured; every candidate paper number has an EVIDENCE row |
| **P6 Falsification gate** | falsifier | `CLAIMS.md` verdicts | no `open` claims; refuted claims removed from narrative; weakened wording adopted |
| **P7 Writing + figures** | writer, figure-artist | `paper/` | playbook sections complete; `crbench audit-tex` passes; 0 undefined refs; figures in house style |
| **P8 Review → submit → rebuttal → camera-ready** | reviewer-sim, submission-rebuttal | `REVIEWS.md`, `SUBMISSION.md` | mock-review action items closed; `anon_check` clean; checklist done; artifact packaged |

## Feedback loops
- P6 refutes a core claim → back to **P2** (new idea) or **P3** (weaker theorem).
- P6 finds an unfair or unreproduced baseline → back to **P4/P5**.
- P8 mock review finds a missing experiment → **P5**; a presentation problem → **P7**.
- Pre-emption found at any time → **P1** threat assessment → PI decides pivot/position/kill in `DECISIONS.md`.

## Multi-agent workflows (run with Claude Code's Workflow tool, `scriptPath`)
| script | phase | pattern |
|---|---|---|
| `lit-sweep.js` | P1 | multi-modal sweep → per-item existence verification → synthesis |
| `idea-tournament.js` | P2 | 5 mining angles → falsifier screening pipeline → 3-criterion judge panel |
| `falsify-round.js` | P6 | per claim: 3 diverse-lens falsifiers, majority vote → ledger |
| `mock-review-panel.js` | P8 | 3 reviewer personas → meta-review with routed action items |

Example: `Workflow({scriptPath: "workflows/falsify-round.js", args: {project: "/abs/path/my-paper"}})`.
Without the Workflow tool, ask the orchestrator: "run P6 using agents/falsifier.md on every open claim".
