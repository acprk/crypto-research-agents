# Zero-knowledge proofs and SNARKs

Definitions (GMR), Fiat-Shamir, polynomial commitments (KZG, FRI, inner-product), the PIOP/compiler view (Marlin, PLONK, Spartan, HyperPlonk), transparent/linear-time provers (STARK, Aurora, Brakedown, Ligero), folding (Nova), and MPC-in-the-head (ZKBoo, KKW), which also underlies several post-quantum signatures.

Suggested order: GMR89 -> FS86 -> KZG10 -> Gro16 -> GWC19 -> CHMMVW20 -> CBBZ23 (pairing/PIOP line); BBHR18fri -> BBHR18 -> BCRSVW19 -> AHIV17 -> GLSTW23 -> Set20 (transparent line); BBBPWM18 (IPA); KST22 (folding); GMO16 -> KKW18 (MPCitH).

BibTeX: [`zk-proofs.bib`](zk-proofs.bib) — 17 entries, all resolved against ePrint / Crossref / DataCite with `skills/bib-verify/scripts/verify_bib.py` (status VERIFIED: title, authors, year). The venue column is informational and was not machine-checked. Re-run the verifier before copying entries into a paper.

| key | ePrint / DOI | year | title | venue | why read |
|---|---|---|---|---|---|
| `FS86` | [doi](https://doi.org/10.1007/3-540-47721-7_12) | 1986 | How To Prove Yourself: Practical Solutions to Identification and Signature Problems | CRYPTO 1986 | Fiat-Shamir |
| `GMR89` | [doi](https://doi.org/10.1137/0218012) | 1989 | The Knowledge Complexity of Interactive Proof Systems | SIAM J. Comput. 1989 | ZK definition |
| `KZG10` | [doi](https://doi.org/10.1007/978-3-642-17373-8_11) | 2010 | Constant-Size Commitments to Polynomials and Their Applications | ASIACRYPT 2010 | KZG |
| `Gro16` | [2016/260](https://eprint.iacr.org/2016/260) | 2016 | On the Size of Pairing-based Non-interactive Arguments | EUROCRYPT 2016 | Groth16 |
| `GMO16` | [2016/163](https://eprint.iacr.org/2016/163) | 2016 | ZKBoo: Faster Zero-Knowledge for Boolean Circuits | USENIX Security 2016 | MPC-in-the-head |
| `BBBPWM18` | [2017/1066](https://eprint.iacr.org/2017/1066) | 2017 | Bulletproofs: Short Proofs for Confidential Transactions and More | IEEE S&P 2018 | inner-product arguments |
| `BBHR18` | [2018/046](https://eprint.iacr.org/2018/046) | 2018 | Scalable, Transparent, and Post-Quantum Secure Computational Integrity | ePrint | STARK |
| `BBHR18fri` | [doi](https://doi.org/10.4230/LIPIcs.ICALP.2018.14) | 2018 | Fast Reed-Solomon Interactive Oracle Proofs of Proximity | ICALP 2018 | FRI |
| `KKW18` | [2018/475](https://eprint.iacr.org/2018/475) | 2018 | Improved Non-Interactive Zero Knowledge with Applications to Post-Quantum Signatures | CCS 2018 | MPCitH with preprocessing |
| `BCRSVW19` | [2018/828](https://eprint.iacr.org/2018/828) | 2018 | Aurora: Transparent Succinct Arguments for R1CS | EUROCRYPT 2019 | IOP-based |
| `Set20` | [2019/550](https://eprint.iacr.org/2019/550) | 2019 | Spartan: Efficient and general-purpose zkSNARKs without trusted setup | CRYPTO 2020 | sum-check SNARK |
| `GWC19` | [2019/953](https://eprint.iacr.org/2019/953) | 2019 | PLONK: Permutations over Lagrange-bases for Oecumenical Noninteractive arguments of Knowledge | ePrint | PLONK |
| `CHMMVW20` | [2019/1047](https://eprint.iacr.org/2019/1047) | 2019 | Marlin: Preprocessing zkSNARKs with Universal and Updatable SRS | EUROCRYPT 2020 | AHP compiler |
| `KST22` | [2021/370](https://eprint.iacr.org/2021/370) | 2021 | Nova: Recursive Zero-Knowledge Arguments from Folding Schemes | CRYPTO 2022 | folding |
| `GLSTW23` | [2021/1043](https://eprint.iacr.org/2021/1043) | 2021 | Brakedown: Linear-time and field-agnostic SNARKs for R1CS | CRYPTO 2023 | linear-time prover |
| `CBBZ23` | [2022/1355](https://eprint.iacr.org/2022/1355) | 2022 | HyperPlonk: Plonk with Linear-Time Prover and High-Degree Custom Gates | EUROCRYPT 2023 | multilinear PLONK |
| `AHIV17` | [2022/1608](https://eprint.iacr.org/2022/1608) | 2022 | Ligero: Lightweight Sublinear Arguments Without a Trusted Setup | CCS 2017 / DCC 2023 | Ligero full version |
