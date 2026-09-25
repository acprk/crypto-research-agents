# Post-quantum signatures and KEMs (design and cryptanalysis)

Lattice KEM/signature designs (Kyber, Dilithium, Falcon's sampler, Hawk), trapdoors (GPV, MP12), Fiat-Shamir with aborts, the FO transform, hash-based signatures, isogenies, and multivariate schemes, together with the landmark breaks (Rainbow, SIDH) and the leakage/failure attacks that shape parameter choices. Rule of thumb from the breaks: adding algebraic structure to a security-bearing object (public map, trapdoor distribution, torsion information) is where attacks come from.

Suggested order: GPV08 -> MP12 -> Lyu12 -> DP16 -> BDKLLSSS18 -> DKLLSSS18 -> DPPW22 (lattice); HHK17 -> DVV19 (KEM transform, failures); BHKNRS19 (hash-based); KPG99 -> Beu21 -> Beu22 (multivariate); DKLPW20 -> CD23 -> MMPPW23 -> Rob23 (isogenies); NR06 -> BCLV17 (leakage, ring choice).

BibTeX: [`pqc-signatures-kem.bib`](pqc-signatures-kem.bib) — 19 entries, all resolved against ePrint / Crossref / DataCite with `skills/bib-verify/scripts/verify_bib.py` (status VERIFIED: title, authors, year). The venue column is informational and was not machine-checked. Re-run the verifier before copying entries into a paper.

| key | ePrint / DOI | year | title | venue | why read |
|---|---|---|---|---|---|
| `KPG99` | [doi](https://doi.org/10.1007/3-540-48910-X_15) | 1999 | Unbalanced Oil and Vinegar Signature Schemes | EUROCRYPT 1999 | UOV |
| `NR06` | [doi](https://doi.org/10.1007/11761679_17) | 2006 | Learning a Parallelepiped: Cryptanalysis of GGH and NTRU Signatures | EUROCRYPT 2006 | leakage of trapdoor |
| `GPV08` | [2007/432](https://eprint.iacr.org/2007/432) | 2007 | Trapdoors for Hard Lattices and New Cryptographic Constructions | STOC 2008 | hash-and-sign |
| `MP12` | [2011/501](https://eprint.iacr.org/2011/501) | 2011 | Trapdoors for Lattices: Simpler, Tighter, Faster, Smaller | EUROCRYPT 2012 | gadget trapdoors |
| `Lyu12` | [2011/537](https://eprint.iacr.org/2011/537) | 2011 | Lattice Signatures Without Trapdoors | EUROCRYPT 2012 | Fiat-Shamir with aborts |
| `DP16` | [2015/1014](https://eprint.iacr.org/2015/1014) | 2015 | Fast Fourier Orthogonalization | ISSAC 2016 | Falcon sampler |
| `BCLV17` | [2016/461](https://eprint.iacr.org/2016/461) | 2016 | NTRU Prime: Reducing Attack Surface at Low Cost | SAC 2017 | ring choice |
| `BDKLLSSS18` | [2017/634](https://eprint.iacr.org/2017/634) | 2017 | CRYSTALS -- Kyber: a CCA-secure module-lattice-based KEM | EuroS&P 2018 | ML-KEM ancestor |
| `DKLLSSS18` | [2017/633](https://eprint.iacr.org/2017/633) | 2017 | CRYSTALS -- Dilithium: Digital Signatures from Module Lattices | ePrint version | ML-DSA ancestor |
| `HHK17` | [2017/604](https://eprint.iacr.org/2017/604) | 2017 | A Modular Analysis of the Fujisaki-Okamoto Transformation | TCC 2017 | FO variants |
| `DVV19` | [2018/1089](https://eprint.iacr.org/2018/1089) | 2018 | On the impact of decryption failures on the security of LWE/LWR based schemes | ePrint | decryption-failure impact on LWE/LWR KEMs |
| `BHKNRS19` | [2019/1086](https://eprint.iacr.org/2019/1086) | 2019 | The SPHINCS+ Signature Framework | CCS 2019 | SLH-DSA ancestor |
| `DKLPW20` | [2020/1240](https://eprint.iacr.org/2020/1240) | 2020 | SQISign: compact post-quantum signatures from quaternions and isogenies | ASIACRYPT 2020 | isogeny signature |
| `Beu21` | [2020/1343](https://eprint.iacr.org/2020/1343) | 2020 | Improved Cryptanalysis of UOV and Rainbow | EUROCRYPT 2021 | intersection attack |
| `Beu22` | [2022/214](https://eprint.iacr.org/2022/214) | 2022 | Breaking Rainbow Takes a Weekend on a Laptop | CRYPTO 2022 | Rainbow key recovery |
| `CD23` | [2022/975](https://eprint.iacr.org/2022/975) | 2022 | An Efficient Key Recovery Attack on SIDH | EUROCRYPT 2023 | SIDH break |
| `MMPPW23` | [2023/640](https://eprint.iacr.org/2023/640) | 2023 | A Direct Key Recovery Attack on SIDH | EUROCRYPT 2023 | SIDH break |
| `Rob23` | [2022/1038](https://eprint.iacr.org/2022/1038) | 2022 | Breaking SIDH in Polynomial Time | EUROCRYPT 2023 | SIDH break, any start curve |
| `DPPW22` | [2022/1155](https://eprint.iacr.org/2022/1155) | 2022 | Hawk: Module LIP makes Lattice Signatures Fast, Compact and Simple | ASIACRYPT 2022 | lattice isomorphism |
