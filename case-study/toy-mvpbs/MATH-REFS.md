# MATH-REFS — where each mathematical fact comes from (owner: `math-librarian`) — TEACHING EXAMPLE

Looked up in `references/textbooks/CATALOG.md` / `TOPIC-MAP.md` (TOCs only; no PDFs in the repo).
Page numbers are those printed in the catalog's TOC files; chapter-level entries marked *pub*
in the catalog must be checked against the book before citing a section number in a real paper.

| fact used in paper | book / paper | chapter.section / theorem no. | verified by (sage/lean/hand) |
|---|---|---|---|
| Quotient ring R = Z[X]/(X^N+1), units of a quotient ring, (1 − X)·Σ_{j<N} X^j = 1 − X^N = 2 in R | Dummit–Foote, *Abstract Algebra* (toc/dummit-abstract-algebra.md) | Ch. 7 "Ring Homomorphisms and Quotient Rings" (p. 239); Ch. 9 §9.1–9.2 "Polynomial Rings" (pp. 295–299) | hand + L1 exhaustive check (theory/check_mvpbs_noise.log) |
| X^N + 1 = Φ_{2N}(X) for N a power of two (so R is the 2N-th cyclotomic ring) | Dummit–Foote | "Cyclotomic Polynomials and Extensions" (p. 552, §13.6 in TOPIC-MAP) | hand |
| Negacyclic convolution = multiplication by an anti-circulant matrix; variance of a fixed linear combination of independent centred variables = Σ c_i² Var | Meyer, *Matrix Analysis and Applied Linear Algebra* (toc/meyer-matrix-analysis-and-applied-linear-algebra.md) for circulant/structured matrices; the variance identity is elementary probability — **no catalog book covers it** (gap reported to the PI, harmless here) | Meyer: Ch. 5 "Norms, Inner Products, and Orthogonality" (p. 273; the catalog tags it with DFT/circulants — check the exact section before citing) | Monte Carlo T1a (ratio 0.955–1.029) |
| Discrete Gaussians / sub-Gaussian tails used by the TFHE noise heuristic | Peikert, *A Decade of Lattice Cryptography* (toc/peikert-a-decade-of-lattice-cryptography.md) | §2 "Background (lattices, Gaussians, hard problems)" — *pub* TOC | not needed beyond the erfc tail used in T1b |
| Boolean-function view of S-box output bits (coordinate functions) | Carlet, *Boolean Functions for Cryptography and Coding Theory* (toc/carlet-boolean-functions-for-cryptography-and-coding-theory.md) | "Generalities on Boolean and vectorial functions" (chapter-level *pub* TOC) | L2 exhaustive |
