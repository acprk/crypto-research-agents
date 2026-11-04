# CLAIMS — falsifiable statements

> Rule: every claim that may appear in the paper is registered here **before** it is written.
> The `falsifier` attacks `open` claims first. Only `survived` (or `weakened` with the
> weakened wording) claims may enter `paper/`.

> Example row (register real ones with `cra claim add` / the `claim_register` tool, which allocate IDs):
> `| C1 | For all primes p ≡ 1 (mod 4) with p < 2^20, algorithm X uses ≤ k nonscalar mults. Kill: one p with > k | idea-miner | open | | |`

| ID | claim (precise, falsifiable, with parameter range) | proposer | status | falsifier evidence / counterexample | EVIDENCE / THEORY refs |
|---|---|---|---|---|---|

Status ∈ {open, survived, weakened, refuted}. Refuted claims stay in the table (with the reason) — they are data.
