# Lattice cryptanalysis and concrete security estimation

The goal is to be able to *re-derive* a claimed security level: reduction (LLL/BKZ), cost models (core-SVP, sieving exponents, dimensions-for-free), attack families (primal uSVP/BDD, dual incl. FFT/MATZOV-style, hybrid MitM), and structural attacks (overstretched NTRU, subfields). Always state which cost model a number comes from.

Suggested order: LLL82 -> Regev09 -> LPR10 -> LS15 -> Pei16 (foundations); GN08 -> CN11 -> APS15 -> ADPS16 -> ACDDPPVW18 (estimation); BDGL16 -> Duc18 -> ADHKPS19 (sieving); HG07 -> ABD16 -> KF17 -> DDGR20 -> MATZOV22 -> DP23 (attack variants and their caveats).

BibTeX: [`lattice-cryptanalysis.bib`](lattice-cryptanalysis.bib) — 19 entries, all resolved against ePrint / Crossref / DataCite with `skills/bib-verify/scripts/verify_bib.py` (status VERIFIED: title, authors, year). The venue column is informational and was not machine-checked. Re-run the verifier before copying entries into a paper.

| key | ePrint / DOI | year | title | venue | why read |
|---|---|---|---|---|---|
| `LLL82` | [doi](https://doi.org/10.1007/BF01457454) | 1982 | Factoring Polynomials with Rational Coefficients | Math. Ann. 1982 | LLL |
| `Regev09` | [doi](https://doi.org/10.1145/1568318.1568324) | 2009 | On Lattices, Learning with Errors, Random Linear Codes, and Cryptography | J. ACM 2009 | LWE |
| `HG07` | [doi](https://doi.org/10.1007/978-3-540-74143-5_9) | 2007 | A Hybrid Lattice-Reduction and Meet-in-the-Middle Attack Against NTRU | CRYPTO 2007 | hybrid attack |
| `GN08` | [doi](https://doi.org/10.1007/978-3-540-78967-3_3) | 2008 | Predicting Lattice Reduction | EUROCRYPT 2008 | root-Hermite factor |
| `CN11` | [doi](https://doi.org/10.1007/978-3-642-25385-0_1) | 2011 | BKZ 2.0: Better Lattice Security Estimates | ASIACRYPT 2011 | BKZ simulator |
| `LPR10` | [2012/230](https://eprint.iacr.org/2012/230) | 2012 | On Ideal Lattices and Learning with Errors Over Rings | EUROCRYPT 2010 / J. ACM 2013 | Ring-LWE |
| `LS15` | [2012/090](https://eprint.iacr.org/2012/090) | 2012 | Worst-Case to Average-Case Reductions for Module Lattices | DCC 2015 | Module-LWE |
| `APS15` | [2015/046](https://eprint.iacr.org/2015/046) | 2015 | On the Concrete Hardness of Learning with Errors | J. Math. Cryptol. 2015 | estimator survey |
| `Pei16` | [2015/939](https://eprint.iacr.org/2015/939) | 2015 | A Decade of Lattice Cryptography | FnT TCS 2016 | survey |
| `ADPS16` | [2015/1092](https://eprint.iacr.org/2015/1092) | 2015 | Post-quantum Key Exchange -- a New Hope | USENIX Security 2016 | core-SVP methodology |
| `BDGL16` | [2015/1128](https://eprint.iacr.org/2015/1128) | 2015 | New Directions in Nearest Neighbor Searching with Applications to Lattice Sieving | SODA 2016 | 0.292 sieving exponent |
| `ABD16` | [2016/127](https://eprint.iacr.org/2016/127) | 2016 | A Subfield Lattice Attack on Overstretched NTRU Assumptions | CRYPTO 2016 | overstretched NTRU |
| `KF17` | [doi](https://doi.org/10.1007/978-3-319-56620-7_1) | 2017 | Revisiting Lattice Attacks on Overstretched NTRU Parameters | EUROCRYPT 2017 | dense sublattice |
| `Duc18` | [2017/999](https://eprint.iacr.org/2017/999) | 2017 | Shortest Vector from Lattice Sieving: a Few Dimensions for Free | EUROCRYPT 2018 | dimensions for free |
| `ACDDPPVW18` | [2018/331](https://eprint.iacr.org/2018/331) | 2018 | Estimate all the LWE, NTRU schemes! | SCN 2018 | estimator comparison |
| `ADHKPS19` | [2019/089](https://eprint.iacr.org/2019/089) | 2019 | The General Sieve Kernel and New Records in Lattice Reduction | EUROCRYPT 2019 | G6K |
| `DDGR20` | [2020/292](https://eprint.iacr.org/2020/292) | 2020 | LWE with Side Information: Attacks and Concrete Security Estimation | CRYPTO 2020 | leaky-LWE estimator |
| `MATZOV22` | [doi](https://doi.org/10.5281/zenodo.6412487) | 2022 | Report on the Security of LWE: Improved Dual Lattice Attack | Zenodo | dual + FFT |
| `DP23` | [2023/302](https://eprint.iacr.org/2023/302) | 2023 | Does the Dual-Sieve Attack on Learning with Errors even Work? | CRYPTO 2023 | dual attack heuristics questioned |
