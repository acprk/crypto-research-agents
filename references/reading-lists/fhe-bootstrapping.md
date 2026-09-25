# FHE: BGV / BFV / CKKS / TFHE and bootstrapping

Read the scheme papers first (BGV, BFV, CKKS, GSW, FHEW/TFHE), then the bootstrapping line of each family. For any bootstrapping idea, the questions a reviewer will ask are: which step dominates (linear transform vs. non-linear step / blind rotation), what is the multiplicative depth and key-switch count, what noise/precision is left, and at what security level (check against the HE standard tables and a lattice estimator).

Suggested order: SV11 -> BGV12 -> FV12 -> GHS12 -> HS14 -> HS18 -> CH18 -> GIKV23 (BGV/BFV track); CKKS17 -> CHKKS18 -> CCS19 -> HK20 -> BMTH21 -> LM21 (CKKS track); GSW13 -> DM15 -> CGGI16/CGGI20 -> MP21 -> CJP21 -> LMKCDEY22 (FHEW/TFHE track).

BibTeX: [`fhe-bootstrapping.bib`](fhe-bootstrapping.bib) — 25 entries, all resolved against ePrint / Crossref / DataCite with `skills/bib-verify/scripts/verify_bib.py` (status VERIFIED: title, authors, year). The venue column is informational and was not machine-checked. Re-run the verifier before copying entries into a paper.

| key | ePrint / DOI | year | title | venue | why read |
|---|---|---|---|---|---|
| `Gentry09` | [doi](https://doi.org/10.1145/1536414.1536440) | 2009 | Fully Homomorphic Encryption Using Ideal Lattices | STOC 2009 | first FHE; bootstrapping + squashing |
| `SV11` | [2011/133](https://eprint.iacr.org/2011/133) | 2011 | Fully Homomorphic SIMD Operations | DCC 2014 | CRT slot packing |
| `BGV12` | [2011/277](https://eprint.iacr.org/2011/277) | 2011 | Fully Homomorphic Encryption without Bootstrapping | ITCS 2012 | BGV; modulus switching |
| `Bra12` | [2012/078](https://eprint.iacr.org/2012/078) | 2012 | Fully Homomorphic Encryption without Modulus Switching from Classical GapSVP | CRYPTO 2012 | scale-invariant |
| `FV12` | [2012/144](https://eprint.iacr.org/2012/144) | 2012 | Somewhat Practical Fully Homomorphic Encryption | ePrint | BFV |
| `GHS12` | [2012/099](https://eprint.iacr.org/2012/099) | 2012 | Homomorphic Evaluation of the AES Circuit | CRYPTO 2012 | slot permutations, Frobenius |
| `GSW13` | [2013/340](https://eprint.iacr.org/2013/340) | 2013 | Homomorphic Encryption from Learning with Errors: Conceptually-Simpler, Asymptotically-Faster, Attribute-Based | CRYPTO 2013 | GSW; gadget matrices |
| `HS14` | [2014/873](https://eprint.iacr.org/2014/873) | 2014 | Bootstrapping for HElib | EUROCRYPT 2015 | BGV thin/general bootstrapping |
| `DM15` | [2014/816](https://eprint.iacr.org/2014/816) | 2014 | FHEW: Bootstrapping Homomorphic Encryption in less than a second | EUROCRYPT 2015 | FHEW; blind rotation |
| `CKKS17` | [2016/421](https://eprint.iacr.org/2016/421) | 2016 | Homomorphic Encryption for Arithmetic of Approximate Numbers | ASIACRYPT 2017 | CKKS |
| `CGGI16` | [2016/870](https://eprint.iacr.org/2016/870) | 2016 | Faster Fully Homomorphic Encryption: Bootstrapping in less than 0.1 Seconds | ASIACRYPT 2016 | TFHE conference version |
| `CGGI20` | [2018/421](https://eprint.iacr.org/2018/421) | 2018 | TFHE: Fast Fully Homomorphic Encryption over the Torus | J. Cryptology 2020 | TFHE journal version |
| `CH18` | [2018/067](https://eprint.iacr.org/2018/067) | 2018 | Homomorphic Lower Digits Removal and Improved FHE Bootstrapping | EUROCRYPT 2018 | BGV/BFV digit extraction |
| `HS18` | [2018/244](https://eprint.iacr.org/2018/244) | 2018 | Faster Homomorphic Linear Transformations in HElib | CRYPTO 2018 | BSGS, hoisting |
| `CHKKS18` | [2018/153](https://eprint.iacr.org/2018/153) | 2018 | Bootstrapping for Approximate Homomorphic Encryption | EUROCRYPT 2018 | first CKKS bootstrapping |
| `CCS19` | [2018/1043](https://eprint.iacr.org/2018/1043) | 2018 | Improved Bootstrapping for Approximate Homomorphic Encryption | EUROCRYPT 2019 | FFT-like CoeffToSlot |
| `HK20` | [2019/688](https://eprint.iacr.org/2019/688) | 2019 | Better Bootstrapping for Approximate Homomorphic Encryption | CT-RSA 2020 | cosine + double angle |
| `MP21` | [2020/086](https://eprint.iacr.org/2020/086) | 2020 | Bootstrapping in FHEW-like Cryptosystems | WAHC 2021 | AP vs GINX blind rotation |
| `BMTH21` | [2020/1203](https://eprint.iacr.org/2020/1203) | 2020 | Efficient Bootstrapping for Approximate Homomorphic Encryption with Non-Sparse Keys | EUROCRYPT 2021 | dense-key CKKS bootstrapping |
| `LM21` | [2020/1533](https://eprint.iacr.org/2020/1533) | 2020 | On the Security of Homomorphic Encryption on Approximate Numbers | EUROCRYPT 2021 | IND-CPA-D |
| `CJP21` | [2021/091](https://eprint.iacr.org/2021/091) | 2021 | Programmable Bootstrapping Enables Efficient Homomorphic Inference of Deep Neural Networks | CSCML 2021 | PBS / LUT |
| `HES19` | [2019/939](https://eprint.iacr.org/2019/939) | 2019 | Homomorphic Encryption Standard | Protecting Privacy through HE (Springer) | parameter tables |
| `LMKCDEY22` | [2022/198](https://eprint.iacr.org/2022/198) | 2022 | Efficient FHEW Bootstrapping with Small Evaluation Keys, and Applications to Threshold Homomorphic Encryption | EUROCRYPT 2023 | automorphism-based blind rotation |
| `GIKV23` | [2022/1364](https://eprint.iacr.org/2022/1364) | 2022 | On Polynomial Functions Modulo   and Faster Bootstrapping for Homomorphic Encryption | EUROCRYPT 2023 | null polynomials mod p^e |
| `OpenFHE22` | [2022/915](https://eprint.iacr.org/2022/915) | 2022 | OpenFHE: Open-Source Fully Homomorphic Encryption Library | WAHC 2022 | library baseline |
