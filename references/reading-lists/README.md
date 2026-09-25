# Reading lists

Curated, public-only starting points per area. Each list is a `.md` (reading order + one-line
"why read") and a `.bib` (drop-in BibTeX). Every entry was resolved on 2026-09-25 against the IACR
ePrint OAI record, Crossref or DataCite by `skills/bib-verify/scripts/verify_bib.py`; the lists are
deliberately short (16-25 entries) — they are a seed for `lit-scout`, not a survey.

| list | scope |
|---|---|
| [fhe-bootstrapping](fhe-bootstrapping.md) | BGV/BFV/CKKS/GSW/FHEW/TFHE and their bootstrapping lines |
| [lattice-cryptanalysis](lattice-cryptanalysis.md) | reduction, estimators, primal/dual/hybrid attacks, NTRU structure |
| [symmetric-cryptanalysis](symmetric-cryptanalysis.md) | differential/linear/boomerang/integral, MILP/SAT automation, MPC/FHE/ZK-friendly ciphers |
| [mpc-psi](mpc-psi.md) | GC/GMW/SPDZ, OT extension, PCGs, PSI lineage, secure sketches |
| [zk-proofs](zk-proofs.md) | commitments, PIOPs, SNARK/STARK lines, folding, MPC-in-the-head |
| [pqc-signatures-kem](pqc-signatures-kem.md) | lattice/hash/multivariate/isogeny designs and landmark breaks |

Rules for extending a list:

1. Public references only; prefer the ePrint id, else a DOI.
2. Anything you are not sure exists goes in with a `% UNVERIFIED` comment line directly above it.
3. Run `python3 skills/bib-verify/scripts/verify_bib.py <list>.bib` and fix every non-VERIFIED row
   (when this repo was built the verifier caught three wrong ePrint numbers/titles written from memory,
   which is exactly why the gate exists).
4. Keep a list under ~25 entries; spin off a new list rather than growing one.
