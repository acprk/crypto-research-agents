# MPC, OT and private set intersection

Generic MPC (garbled circuits, GMW, SPDZ), OT extension and silent correlations, then the PSI lineage: polynomial/HE-based, OT/OPRF-based, circuit-PSI, VOLE+OKVS. For fuzzy/threshold variants, read secure sketches (DORS08) before designing anything. Always report communication and computation separately, in the same network model as the baselines.

Suggested order: Yao86 -> GMW87 -> IKNP03 -> ZRE15 -> DPSZ12 -> BCGIKS19 (MPC building blocks); FNP04 -> PSZ14 -> KKRT16 -> CLR17 -> PSTY19 -> RS21 -> GPRTY21 -> RR22 (PSI); DORS08 (noisy data); Kel20 (framework baseline).

BibTeX: [`mpc-psi.bib`](mpc-psi.bib) — 16 entries, all resolved against ePrint / Crossref / DataCite with `skills/bib-verify/scripts/verify_bib.py` (status VERIFIED: title, authors, year). The venue column is informational and was not machine-checked. Re-run the verifier before copying entries into a paper.

| key | ePrint / DOI | year | title | venue | why read |
|---|---|---|---|---|---|
| `Yao86` | [doi](https://doi.org/10.1109/SFCS.1986.25) | 1986 | How to Generate and Exchange Secrets | FOCS 1986 | garbled circuits |
| `GMW87` | [doi](https://doi.org/10.1145/28395.28420) | 1987 | How to Play ANY Mental Game | STOC 1987 | GMW |
| `IKNP03` | [doi](https://doi.org/10.1007/978-3-540-45146-4_9) | 2003 | Extending Oblivious Transfers Efficiently | CRYPTO 2003 | OT extension |
| `DORS08` | [2003/235](https://eprint.iacr.org/2003/235) | 2003 | Fuzzy Extractors: How to Generate Strong Keys from Biometrics and Other Noisy Data | SIAM J. Comput. 2008 | secure sketches |
| `FNP04` | [doi](https://doi.org/10.1007/978-3-540-24676-3_1) | 2004 | Efficient Private Matching and Set Intersection | EUROCRYPT 2004 | polynomial-based PSI |
| `DPSZ12` | [2011/535](https://eprint.iacr.org/2011/535) | 2011 | Multiparty Computation from Somewhat Homomorphic Encryption | CRYPTO 2012 | SPDZ |
| `PSZ14` | [2014/447](https://eprint.iacr.org/2014/447) | 2014 | Faster Private Set Intersection Based on OT Extension | USENIX Security 2014 | OT-based PSI |
| `ZRE15` | [2014/756](https://eprint.iacr.org/2014/756) | 2014 | Two Halves Make a Whole: Reducing Data Transfer in Garbled Circuits Using Half Gates | EUROCRYPT 2015 | half gates |
| `KKRT16` | [2016/799](https://eprint.iacr.org/2016/799) | 2016 | Efficient Batched Oblivious PRF with Applications to Private Set Intersection | CCS 2016 | BaRK-OPRF |
| `CLR17` | [2017/299](https://eprint.iacr.org/2017/299) | 2017 | Fast Private Set Intersection from Homomorphic Encryption | CCS 2017 | unbalanced HE-PSI |
| `PSTY19` | [2019/241](https://eprint.iacr.org/2019/241) | 2019 | Efficient Circuit-Based PSI with Linear Communication | EUROCRYPT 2019 | circuit-PSI |
| `BCGIKS19` | [2019/448](https://eprint.iacr.org/2019/448) | 2019 | Efficient Pseudorandom Correlation Generators: Silent OT Extension and More | CRYPTO 2019 | silent OT / PCG |
| `Kel20` | [2020/521](https://eprint.iacr.org/2020/521) | 2020 | MP-SPDZ: A Versatile Framework for Multi-Party Computation | CCS 2020 | framework baseline |
| `RS21` | [2021/266](https://eprint.iacr.org/2021/266) | 2021 | VOLE-PSI: Fast OPRF and Circuit-PSI from Vector-OLE | EUROCRYPT 2021 | VOLE-PSI |
| `GPRTY21` | [2021/883](https://eprint.iacr.org/2021/883) | 2021 | Oblivious Key-Value Stores and Amplification for Private Set Intersection | CRYPTO 2021 | OKVS |
| `RR22` | [2022/320](https://eprint.iacr.org/2022/320) | 2022 | Blazing Fast PSI from Improved OKVS and Subfield VOLE | CCS 2022 | RB-OKVS |
