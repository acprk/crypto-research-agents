# Symmetric cryptanalysis and automated trail search

Core statistical attacks (differential, linear, boomerang, integral/division property, cube), the S-box tables that drive them (DDT/LAT/BCT), solver-based automation (MILP/SAT/SMT), and arithmetization-oriented / FHE-friendly designs whose cost model is multiplicative depth or AND-count instead of cycles.

Suggested order: BS91 -> Mat93 -> Nyb93 -> Knu94 -> Wag99 -> CHPSS18 (attacks and tables); MWGP11 -> SHWQML14 -> KLT15 -> Tod15 -> XZBL16 (automation); DS09 (algebraic); ARSTZ15 -> DEGLLLMR18 -> GKRRS21 (MPC/FHE/ZK-friendly primitives); Goh19 (ML-assisted).

BibTeX: [`symmetric-cryptanalysis.bib`](symmetric-cryptanalysis.bib) — 16 entries, all resolved against ePrint / Crossref / DataCite with `skills/bib-verify/scripts/verify_bib.py` (status VERIFIED: title, authors, year). The venue column is informational and was not machine-checked. Re-run the verifier before copying entries into a paper.

| key | ePrint / DOI | year | title | venue | why read |
|---|---|---|---|---|---|
| `BS91` | [doi](https://doi.org/10.1007/BF00630563) | 1991 | Differential Cryptanalysis of DES-like Cryptosystems | J. Cryptology 1991 | differential |
| `Mat93` | [doi](https://doi.org/10.1007/3-540-48285-7_33) | 1993 | Linear Cryptanalysis Method for DES Cipher | EUROCRYPT 1993 | linear |
| `Nyb93` | [doi](https://doi.org/10.1007/3-540-48285-7_6) | 1993 | Differentially Uniform Mappings for Cryptography | EUROCRYPT 1993 | APN, differential uniformity |
| `Knu94` | [doi](https://doi.org/10.1007/3-540-60590-8_16) | 1994 | Truncated and Higher Order Differentials | FSE 1994 |  |
| `Wag99` | [doi](https://doi.org/10.1007/3-540-48519-8_12) | 1999 | The Boomerang Attack | FSE 1999 |  |
| `DS09` | [2008/385](https://eprint.iacr.org/2008/385) | 2008 | Cube Attacks on Tweakable Black Box Polynomials | EUROCRYPT 2009 | cube attacks |
| `MWGP11` | [doi](https://doi.org/10.1007/978-3-642-34704-7_5) | 2011 | Differential and Linear Cryptanalysis Using Mixed-Integer Linear Programming | Inscrypt 2011 | MILP active S-boxes |
| `SHWQML14` | [2013/676](https://eprint.iacr.org/2013/676) | 2013 | Automatic Security Evaluation and (Related-key) Differential Characteristic Search: Application to SIMON, PRESENT, LBlock, DES(L) and Other Bit-oriented Block Ciphers | ASIACRYPT 2014 | MILP trails |
| `KLT15` | [2015/145](https://eprint.iacr.org/2015/145) | 2015 | Observations on the SIMON Block Cipher Family | CRYPTO 2015 | SAT/SMT trail search (CryptoSMT) |
| `Tod15` | [2015/090](https://eprint.iacr.org/2015/090) | 2015 | Structural Evaluation by Generalized Integral Property | EUROCRYPT 2015 | division property |
| `XZBL16` | [2016/857](https://eprint.iacr.org/2016/857) | 2016 | Applying MILP Method to Searching Integral Distinguishers Based on Division Property for 6 Lightweight Block Ciphers | ASIACRYPT 2016 | MILP division property |
| `ARSTZ15` | [2016/687](https://eprint.iacr.org/2016/687) | 2016 | Ciphers for MPC and FHE | EUROCRYPT 2015 | LowMC |
| `CHPSS18` | [2018/161](https://eprint.iacr.org/2018/161) | 2018 | Boomerang Connectivity Table: A New Cryptanalysis Tool | EUROCRYPT 2018 | BCT |
| `DEGLLLMR18` | [2018/181](https://eprint.iacr.org/2018/181) | 2018 | Rasta: A Cipher with Low ANDdepth and Few ANDs per Bit | CRYPTO 2018 | FHE-friendly stream cipher |
| `Goh19` | [2019/037](https://eprint.iacr.org/2019/037) | 2019 | Improving Attacks on Round-Reduced Speck32/64 Using Deep Learning | CRYPTO 2019 | neural distinguishers |
| `GKRRS21` | [2019/458](https://eprint.iacr.org/2019/458) | 2019 | Poseidon: A New Hash Function for Zero-Knowledge Proof Systems | USENIX Security 2021 | arithmetization-oriented |
