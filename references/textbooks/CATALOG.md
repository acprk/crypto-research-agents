# Textbook catalog

Bibliographic entries + topic tags + the crypto areas that typically need each book.
**No PDFs are stored in this repository.** Each row links to a `toc/<slug>.md` file that holds only the
table of contents (extracted from a locally owned copy with
`skills/textbook-index/scripts/extract_toc.py`, or recalled from the publisher's public TOC and then
marked `TOC from public source`).

TOC source legend: **bm** = embedded PDF bookmarks (pages = PDF physical pages) · **txt** = parsed from the
printed contents pages (pages = printed page numbers; OCR noise possible) · **pub** = chapter-level TOC from a
public source (verify before citing chapter numbers) · **stub** = bibliographic entry only (scanned / DjVu
without outline; fill from the publisher page).

Area codes: FHE · LAT (lattice crypto & cryptanalysis) · SYM (symmetric crypto) · MPC (MPC/PSI/OT) ·
ZK · PQC (post-quantum signatures/KEM, incl. codes, multivariate, isogenies) · ALL.

## A. Algebra, Galois theory, number theory

| slug | book | TOC | topic tags | areas |
|---|---|---|---|---|
| [dummit-abstract-algebra](toc/dummit-abstract-algebra.md) | D. S. Dummit, R. M. Foote, *Abstract Algebra* (3rd ed., Wiley) | txt | groups, rings, modules, fields, Galois theory, finite fields, cyclotomic extensions, Dedekind domains, representation & character theory | ALL |
| [artin-algebra](toc/artin-algebra.md) | M. Artin, *Algebra* (2nd ed., Pearson) | bm | linear algebra, groups, symmetry, bilinear forms, representations, rings, factoring, quadratic number fields, Galois theory | ALL |
| [hungerford-algebra](toc/hungerford-algebra.md) | T. W. Hungerford, *Algebra* (GTM 73) | pub | groups, rings, modules, Galois theory, structure of fields, commutative rings, categories | FHE, LAT |
| [carstensen-opitz-abstract-algebra-applications](toc/carstensen-opitz-abstract-algebra-applications.md) | C. Carstensen-Opitz, B. Fine, G. Rosenberger, *Abstract Algebra: Applications to Galois Theory, Algebraic Geometry, Representation Theory and Cryptography* (2nd ed., De Gruyter) | bm | field extensions, Galois theory, modules, group-based crypto | FHE, PQC |
| [howie-fields-and-galois-theory](toc/howie-fields-and-galois-theory.md) | J. M. Howie, *Fields and Galois Theory* (Springer SUMS) | txt | field extensions, splitting fields, finite fields, Galois correspondence, cyclotomic polynomials | FHE, SYM |
| [jacobson-lectures-in-abstract-algebra-iii](toc/jacobson-lectures-in-abstract-algebra-iii.md) | N. Jacobson, *Lectures in Abstract Algebra III: Theory of Fields and Galois Theory* (GTM 32) | pub | Galois theory, abelian (Kummer) extensions, valuations, Artin–Schreier | FHE |
| [ireland-a-classical-introduction-to-modern-number-theory](toc/ireland-a-classical-introduction-to-modern-number-theory.md) | K. Ireland, M. Rosen, *A Classical Introduction to Modern Number Theory* (GTM 84) | txt | congruences, primitive roots, quadratic reciprocity, Gauss/Jacobi sums, finite fields, cyclotomic fields, Stickelberger, elliptic curves | FHE, SYM, PQC |
| [washington-introduction-to-cyclotomic-fields](toc/washington-introduction-to-cyclotomic-fields.md) | L. C. Washington, *Introduction to Cyclotomic Fields* (GTM 83, 2nd ed.) | pub | cyclotomic fields, Dirichlet characters, cyclotomic units, class groups, Stickelberger, Kronecker–Weber | FHE, LAT |
| [milne-algebraic-number-theory](toc/milne-algebraic-number-theory.md) | J. S. Milne, *Algebraic Number Theory* (course notes v3.x, freely available) | bm | rings of integers, Dedekind domains, discriminants, Minkowski/geometry of numbers, class group, units, cyclotomic & local fields | LAT, FHE |
| [chahal-algebraic-number-theory-a-brief-introduction](toc/chahal-algebraic-number-theory-a-brief-introduction.md) | J. S. Chahal, *Algebraic Number Theory: A Brief Introduction* (CRC) | bm | relative extensions, geometry of numbers, decomposition/inertia groups, cyclotomic fields, Kronecker–Weber | LAT, FHE |
| [kurzweil-the-theory-of-finite-groups-an-introduction](toc/kurzweil-the-theory-of-finite-groups-an-introduction.md) | H. Kurzweil, B. Stellmacher, *The Theory of Finite Groups* (Universitext) | txt | group actions, permutation groups, p-groups, transfer, linear groups | SYM, PQC |
| [serre-linear-representations-of-finite-groups](toc/serre-linear-representations-of-finite-groups.md) | J.-P. Serre, *Linear Representations of Finite Groups* (GTM 42) | txt | characters, orthogonality, Schur's lemma, induced representations, group algebra | FHE, SYM, LAT |
| [ford-rings-and-modules-lecture-notes](toc/ford-rings-and-modules-lecture-notes.md) | T. J. Ford, *Rings and Modules* (lecture notes) | txt | modules over PIDs, canonical forms, Galois theory, tensor products, projective modules, CRT | FHE, LAT |
| [matsumura-commutative-algebra](toc/matsumura-commutative-algebra.md) | H. Matsumura, *Commutative Algebra* (2nd ed.) | bm | primary decomposition, dimension, depth, flatness, completion, regular rings | FHE |
| [popescu-abelian-categories](toc/popescu-abelian-categories.md) | N. Popescu, *Abelian Categories with Applications to Rings and Modules* | stub | category theory, module categories | (background) |
| [faith-algebra-i-rings-modules-and-categories](toc/faith-algebra-i-rings-modules-and-categories.md) | C. Faith, *Algebra I: Rings, Modules, and Categories* | stub | ring & module theory | (background) |
| [faticoni-categories-of-modules-over-endomorphism-rings](toc/faticoni-categories-of-modules-over-endomorphism-rings.md) | T. G. Faticoni, *Categories of Modules over Endomorphism Rings* (Mem. AMS) | stub | endomorphism rings | (background) |
| [lidl-niederreiter-finite-fields](toc/lidl-niederreiter-finite-fields.md) | R. Lidl, H. Niederreiter, *Finite Fields* (Encyclopedia Math. Appl. 20) | pub | finite field structure, polynomials, factorisation, exponential sums, permutation polynomials, LFSRs | SYM, PQC, FHE, ZK |
| [schmidt-combinatorics-and-finite-fields](toc/schmidt-combinatorics-and-finite-fields.md) | K.-U. Schmidt, A. Winterhof (eds.), *Combinatorics and Finite Fields* (Radon Series 23) | bm | difference sets, bent functions, permutation polynomials, Weil sums, cyclotomy, pseudorandomness | SYM |

## B. p-adic analysis

| slug | book | TOC | topic tags | areas |
|---|---|---|---|---|
| [koblitz-p-adic-numbers-analysis-zeta-functions](toc/koblitz-p-adic-numbers-analysis-zeta-functions.md) | N. Koblitz, *p-adic Numbers, p-adic Analysis, and Zeta-Functions* (GTM 58) | txt | Q_p, Hensel, Teichmüller, Newton polygons, p-adic zeta | FHE (Z/p^e plaintexts), PQC (isogenies background) |
| [robert-a-course-in-p-adic-analysis](toc/robert-a-course-in-p-adic-analysis.md) | A. M. Robert, *A Course in p-adic Analysis* (GTM 198) | pub | p-adic fields, Mahler series, continuous functions on Z_p, ramification | FHE |
| [galindo-p-adic-analysis-arithmetic-and-singularities](toc/galindo-p-adic-analysis-arithmetic-and-singularities.md) | C. Galindo et al. (eds.), *p-Adic Analysis, Arithmetic and Singularities* (Contemp. Math.) | bm | p-adic/motivic integration, Igusa zeta functions | (background) |

## C. Linear algebra, matrix analysis, harmonic analysis, optimisation

| slug | book | TOC | topic tags | areas |
|---|---|---|---|---|
| [meyer-matrix-analysis-and-applied-linear-algebra](toc/meyer-matrix-analysis-and-applied-linear-algebra.md) | C. D. Meyer, *Matrix Analysis and Applied Linear Algebra* (SIAM) | bm | norms, orthogonality, DFT/FFT, circulants, SVD, eigenvalues, Perron–Frobenius | FHE, LAT, ALL |
| [hiai-introduction-to-matrix-analysis-and-applications](toc/hiai-introduction-to-matrix-analysis-and-applications.md) | F. Hiai, D. Petz, *Introduction to Matrix Analysis and Applications* (Universitext) | bm | tensor products, positivity, matrix monotone/convex functions, majorization, singular values | FHE (noise bounds), LAT |
| [petersen-pedersen-matrix-cookbook](toc/petersen-pedersen-matrix-cookbook.md) | K. B. Petersen, M. S. Pedersen, *The Matrix Cookbook* (free) | bm | identities, derivatives, inverses, Gaussians | ALL (quick reference) |
| [folland-a-course-in-abstract-harmonic-analysis](toc/folland-a-course-in-abstract-harmonic-analysis.md) | G. B. Folland, *A Course in Abstract Harmonic Analysis* (CRC) | pub | LCA groups, Pontryagin duality, Fourier on groups, induced representations | FHE, LAT (Gaussians/smoothing) |
| [grafakos-classical-and-modern-fourier-analysis](toc/grafakos-classical-and-modern-fourier-analysis.md) | L. Grafakos, *Classical and Modern Fourier Analysis* (Pearson) | txt | L^p, interpolation, Fourier transform, torus, singular integrals | LAT, FHE (approximation) |
| [grafakos-modern-fourier-analysis](toc/grafakos-modern-fourier-analysis.md) | L. Grafakos, *Modern Fourier Analysis* (GTM 250, 2nd ed.) | pub | function spaces, BMO, weighted inequalities, time–frequency | (background) |
| [boyd-vandenberghe-convex-optimization](toc/boyd-vandenberghe-convex-optimization.md) | S. Boyd, L. Vandenberghe, *Convex Optimization* (CUP; free) | bm | convex sets/functions, duality, LP/SDP, approximation (minimax), interior-point | FHE (polynomial approx.), SYM (MILP), ALL |
| [brondsted-introduction-to-convex-polytopes](toc/brondsted-introduction-to-convex-polytopes.md) | A. Brøndsted, *An Introduction to Convex Polytopes* (GTM 90) | bm | polytopes, faces, Euler relation | LAT, SYM (MILP convex hulls) |

## D. Combinatorics, graphs, geometry

| slug | book | TOC | topic tags | areas |
|---|---|---|---|---|
| [merris-combinatorics](toc/merris-combinatorics.md) | R. Merris, *Combinatorics* (2nd ed., Wiley) | bm | counting, Pólya/Burnside enumeration, generating functions, codes and designs | ALL |
| [west-introduction-to-graph-theory-with-solution-manual](toc/west-introduction-to-graph-theory-with-solution-manual.md) | D. B. West, *Introduction to Graph Theory* (2nd ed.) | bm | matchings, connectivity, colouring, planarity, expanders-adjacent basics | MPC (cuckoo hashing/OKVS graphs), ZK |
| [sauer-finite-and-infinite-combinatorics-in-sets-and-logic](toc/sauer-finite-and-infinite-combinatorics-in-sets-and-logic.md) | N. W. Sauer et al. (eds.), *Finite and Infinite Combinatorics in Sets and Logic* (NATO ASI) | txt | Ramsey theory, partition calculus | (background) |
| [kollar-algebraic-geometry-santa-cruz-1995](toc/kollar-algebraic-geometry-santa-cruz-1995.md) | J. Kollár, R. Lazarsfeld, D. R. Morrison (eds.), *Algebraic Geometry — Santa Cruz 1995* | txt | surfaces, higher-dimensional geometry | (background) |
| [zelobenko-compact-lie-groups-and-their-representations](toc/zelobenko-compact-lie-groups-and-their-representations.md) | D. P. Želobenko, *Compact Lie Groups and Their Representations* (AMS Transl.) | stub | Lie groups, representations | (background) |

## E. Cryptography textbooks and surveys (not in the local corpus; TOC from public source)

| slug | book | TOC | topic tags | areas |
|---|---|---|---|---|
| [katz-lindell-introduction-to-modern-cryptography](toc/katz-lindell-introduction-to-modern-cryptography.md) | J. Katz, Y. Lindell, *Introduction to Modern Cryptography* (3rd ed.) | pub | definitions, reductions, symmetric & public-key primitives, PQC intro | ALL |
| [boneh-shoup-graduate-course-in-applied-cryptography](toc/boneh-shoup-graduate-course-in-applied-cryptography.md) | D. Boneh, V. Shoup, *A Graduate Course in Applied Cryptography* (free draft) | pub | proofs for symmetric/public-key crypto, Sigma protocols, ZK, key exchange, lattices | ALL |
| [micciancio-goldwasser-complexity-of-lattice-problems](toc/micciancio-goldwasser-complexity-of-lattice-problems.md) | D. Micciancio, S. Goldwasser, *Complexity of Lattice Problems* | pub | SVP/CVP hardness, basis reduction, lattice-based functions | LAT, PQC, FHE |
| [peikert-a-decade-of-lattice-cryptography](toc/peikert-a-decade-of-lattice-cryptography.md) | C. Peikert, *A Decade of Lattice Cryptography* (ePrint 2015/939) | pub | SIS/LWE, ring/module variants, trapdoors, FHE | LAT, PQC, FHE |
| [knudsen-robshaw-block-cipher-companion](toc/knudsen-robshaw-block-cipher-companion.md) | L. R. Knudsen, M. J. B. Robshaw, *The Block Cipher Companion* | pub | DES/AES, modes, differential/linear cryptanalysis | SYM |
| [carlet-boolean-functions-for-cryptography-and-coding-theory](toc/carlet-boolean-functions-for-cryptography-and-coding-theory.md) | C. Carlet, *Boolean Functions for Cryptography and Coding Theory* (CUP 2021) | pub (topics) | Walsh spectrum, nonlinearity, APN, bent, algebraic immunity, Reed–Muller | SYM |
| [thaler-proofs-arguments-and-zero-knowledge](toc/thaler-proofs-arguments-and-zero-knowledge.md) | J. Thaler, *Proofs, Arguments, and Zero-Knowledge* (free) | pub | sum-check, GKR, PCP/IOP, polynomial commitments, SNARK recursion | ZK |
| [evans-kolesnikov-rosulek-pragmatic-introduction-to-secure-mpc](toc/evans-kolesnikov-rosulek-pragmatic-introduction-to-secure-mpc.md) | D. Evans, V. Kolesnikov, M. Rosulek, *A Pragmatic Introduction to Secure MPC* (free) | pub | GC, GMW, OT, ORAM, malicious security | MPC |

Also useful, catalogued without a TOC file: F. J. MacWilliams, N. J. A. Sloane, *The Theory of
Error-Correcting Codes* (coding theory: PQC codes, SYM MDS matrices, ZK Reed–Solomon); S. D. Galbraith,
*Mathematics of Public Key Cryptography* (CUP, free author version: DLP, pairings, lattices, isogeny
background); H. Cohen, *A Course in Computational Algebraic Number Theory* (GTM 138: algorithms for
number fields, LLL, class groups).

## Adding a book

```bash
python3 skills/textbook-index/scripts/extract_toc.py /path/to/my/books --out-dir references/textbooks/toc --summary /tmp/toc.json
```

Then add one row here (slug, bibliographic entry, TOC code, tags, areas) and, if the book fills a gap,
a line in [TOPIC-MAP.md](TOPIC-MAP.md). Never commit the PDF; never paste body text.
