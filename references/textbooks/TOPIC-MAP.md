# Topic map: "which book / chapter proves X?"

Used by the `math-librarian` agent. Columns: **topic → first place to look → second opinion → typical
crypto use**. Chapter numbers come from the TOC files in [`toc/`](toc/) (see [CATALOG.md](CATALOG.md) for
bibliographic data). Chapter numbers taken from public-source TOCs are marked (pub) — confirm them before
putting them in a paper. Short slugs: DF = Dummit–Foote, IR = Ireland–Rosen, W = Washington, M = Milne ANT,
LN = Lidl–Niederreiter, S = Serre, MG = Micciancio–Goldwasser, BV = Boyd–Vandenberghe.

Lookup protocol (also in `skills/textbook-index`): (1) find the topic row; (2) open the TOC file and pick the
section; (3) read the section in your own copy; (4) record in `MATH-REFS.md` the exact statement you rely on,
book + section + (printed) page, and whether you checked its hypotheses against your setting. A citation
without a checked hypothesis is a hazard, not a reference.

## Cyclotomic fields and rings (FHE, Ring-/Module-LWE)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| Cyclotomic polynomials Φ_m, irreducibility over Q | DF §13.6 | Howie ch. on cyclotomic polynomials; Artin ch.15 | ring R = Z[X]/Φ_m(X) |
| Gal(Q(ζ_m)/Q) ≅ (Z/mZ)^*; automorphisms X ↦ X^k | DF §14.5 | W ch.2 (pub); M ch.6 | rotations / key-switching automorphisms, slot permutations |
| Splitting of primes p in Q(ζ_m): order of p mod m, decomposition field | IR ch.13 | M ch.3 ("factorization in extensions"), ch.6; Chahal ch.7–8 | number and size of plaintext slots (CRT/SIMD packing) |
| Decomposition / inertia groups, Frobenius element | Chahal ch.7 | M ch.3, ch.8; Jacobson III (pub) | Frobenius action on slots, "thin" vs "full" packing |
| Ring of integers Z[ζ_m], discriminant, dual (codifferent) | M ch.2, ch.6 | W ch.2 (pub) | RLWE error in the dual/canonical embedding |
| Canonical embedding, Minkowski space | M ch.4 | Chahal ch.5 (geometry of numbers) | CKKS encoding, noise in the canonical norm |
| Trace and norm maps, tower of subfields | M ch.2 ("norms and traces") | DF §14.2; IR ch.12 | ring switching, trace-based packing / unpacking |
| Normal bases | Jacobson III (pub); LN ch.2–3 (pub) | DF (Galois ch.14 exercises) | slot ↔ coefficient transforms |
| Units, cyclotomic units | M ch.5 | W ch.8 (pub) | short generators, ideal-lattice attacks |
| Class groups, ideal lattices | M ch.3–4 | W ch.10 (pub) | ideal-SVP, principal-ideal problems |
| Stickelberger's theorem | IR ch.14 | W ch.6 (pub) | ideal-lattice attacks (log-unit / class-group methods) |

## Galois theory and finite fields (SYM, FHE, PQC, ZK)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| Fundamental theorem of Galois theory | DF §14.2 | Howie ch. on Galois correspondence; Artin ch.16; Carstensen-Opitz ch.15 | subfield structure, towers |
| Finite fields F_{p^n}: existence, uniqueness, subfields | DF §14.3 | LN ch.2 (pub); IR ch.7 | S-boxes over F_{2^n}, extension-field arithmetic in ZK/PQC |
| Multiplicative group cyclic; primitive roots; element orders | IR ch.4 | DF §9.5, §14.3; LN ch.2 (pub) | NTT-friendly primes (2N \| p−1), roots of unity, order-r elements |
| Frobenius automorphism x ↦ x^p | DF §14.3 | Carstensen-Opitz ch.15–16 | slot rotations, trace functions, linearised polynomials |
| Factorisation of polynomials over F_q | LN ch.4 (pub) | DF §9.4–9.6 | splitting of Φ_m mod p, SIMD structure |
| Permutation polynomials | LN ch.7 (pub) | Schmidt (eds.) ch.5 | S-box design, APN permutations |
| Linear recurring sequences, LFSRs | LN ch.8 (pub) | — | stream ciphers, Grain/Trivium-style analysis |
| Gauss and Jacobi sums | IR ch.6, ch.8 | Schmidt (eds.) ch.9 | character-sum bounds, exponential sums in cryptanalysis |
| Exponential / character sums, Weil bound | LN ch.5 (pub) | Schmidt (eds.) ch.7, ch.10 | nonlinearity bounds, pseudorandomness |
| Kummer / Artin–Schreier extensions | Jacobson III ch.III, VI (pub) | DF §14.7, exercises | algebraic attacks, extension towers |

## p-adic numbers and Z/p^e (FHE plaintext moduli, digit extraction)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| Q_p, Z_p, valuations | Koblitz ch.I | Robert ch.1 (pub); M ch.7 | reasoning about Z/p^e plaintext spaces |
| Hensel lifting | Koblitz ch.I | Robert ch.1–2 (pub); Ford (Hensel) | lifting roots/idempotents from mod p to mod p^e |
| Teichmüller representatives | Koblitz ch.I, III | Robert ch.2 (pub) | digit / lowest-digit structure |
| Mahler expansion, binomial-coefficient basis of functions Z_p → Z_p | Robert ch.4 (pub) | Merris ch.1–2 (binomial identities) | polynomial functions mod p^e, null polynomials |
| Newton polygons | Koblitz ch.IV | Robert ch.6 (pub) | valuations of roots, degree bounds |
| Ramification in local fields | M ch.7 | Robert ch.2 (pub) | local structure of cyclotomic rings |

## Representation theory and characters (FHE linear transforms, symmetric-key, lattices)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| Characters, orthogonality relations | S ch.2 | DF §18.3 / ch.19 | filtering by characters, Fourier on (Z/mZ)^* |
| Schur's lemma | S §2.2 | DF ch.18; Artin ch.10 | commutant arguments (what linear maps commute with the Galois action) |
| Decomposition of the regular representation / group algebra C[G] | S §2.4, ch.6 | DF ch.18 | block-diagonalising Galois-equivariant linear maps (DFT-like decompositions) |
| Induced representations, Frobenius reciprocity, Mackey | S ch.3, ch.7 | DF ch.19 | subgroup/coset decompositions of transforms |
| Burnside's lemma, Pólya enumeration | Merris ch.4 | DF §4.1 exercises; Kurzweil ch.3 | counting orbits: distinct rotation classes, S-box equivalence classes |
| Harmonic analysis on finite / LCA groups | Folland ch.4 (pub) | S ch.2; Grafakos (classical) ch.3 | Walsh–Hadamard transform, discrete Gaussians, smoothing parameter |

## Lattices and geometry of numbers (LAT, PQC, FHE security)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| Lattices, bases, determinant, successive minima | MG ch.1 (pub) | Chahal ch.5; Artin (lattices in ch.6) | all lattice crypto |
| Minkowski's theorems | M ch.4 | Chahal ch.5; MG ch.1 (pub) | lower bounds on λ_1, Gaussian heuristic sanity checks |
| SVP/CVP hardness and approximation | MG ch.3–4 (pub) | Peikert survey §2–3 (pub) | assumptions, reductions |
| Basis reduction (LLL, BKZ) | MG ch.2, ch.7 (pub) | LLL82 & CN11 in the lattice reading list | attacks, estimators |
| Gram–Schmidt, orthogonal projections, QR | Meyer ch.5 | Hiai–Petz ch.2 | GSA / BKZ simulation, Babai rounding |
| Sphere packings, Gaussian heuristic | MG ch.5 (pub) | — | expected shortest vector length |
| SIS/LWE, ring/module variants, trapdoors | Peikert survey §4–5 (pub) | Katz–Lindell ch.14 (pub); Boneh–Shoup ch.17 (pub) | construction and reduction statements |

## Linear algebra, DFT and matrix analysis (FHE transforms, noise, ZK)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| DFT/FFT as matrix factorisation, convolution theorem | Meyer ch.5 (DFT sections) | Artin ch.1, ch.10 | NTT, CoeffToSlot/SlotToCoeff factorisations |
| Circulant / structured matrices, diagonalisation by DFT | Meyer ch.5, ch.7 | Hiai–Petz ch.1–2 | diagonal method, BSGS matrix–vector products |
| Vandermonde matrices, Lagrange interpolation | Meyer ch.4–5 (see its index) | Artin ch.1 | encoding maps, polynomial IOPs |
| Kronecker / tensor products | Hiai–Petz §1.7 | DF §10.4, §11.5; Petersen–Pedersen | tensored gadget decompositions, multidimensional packing |
| Singular values, operator norms, condition numbers | Hiai–Petz ch.6 | Meyer ch.5 | noise growth bounds through linear maps |
| Majorisation | Hiai–Petz ch.6 | Merris (partitions) | worst-case vs average noise, cost-balancing arguments |
| CRT / idempotent decompositions | DF §7.6 | Ford (CRT sections); M ch.1 | RNS representation, slot decomposition |
| Modules over PIDs, Smith normal form | DF ch.12 | Ford ch.2; Artin ch.14 | lattice bases over Z, module-lattice structure |

## Boolean functions and coding theory (SYM, PQC codes, ZK)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| ANF, algebraic degree, Walsh spectrum | Carlet (topics) (pub) | Schmidt (eds.) ch.3 | S-box and filter-function analysis |
| Nonlinearity, bent functions | Carlet (pub) | Schmidt (eds.) ch.3–4 | linear cryptanalysis resistance |
| Differential uniformity, APN, boomerang uniformity | Carlet (pub) | Nyb93, CHPSS18 in the symmetric reading list | DDT/BCT-based bounds |
| Linear codes, weight enumerators, MDS | MacWilliams–Sloane (catalogued, no TOC) | Merris ch.6 | branch number, code-based PQC, Reed–Solomon proximity in ZK |
| Reed–Muller codes and Boolean functions | Carlet (pub) | MacWilliams–Sloane | algebraic degree ↔ code distance |

## Probability, combinatorics, graphs (MPC/PSI, ZK, cryptanalysis)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| Elementary probability, binomial/multinomial | Merris §1.3, §1.7 | Katz–Lindell appendix (pub) | collision/union bounds, failure probabilities |
| Generating functions, partitions | Merris ch.5 | — | counting sparse polynomials, enumerating parameter sets |
| Matchings, Hall's theorem | West ch.3 | — | cuckoo hashing / OKVS peeling success |
| Graph connectivity, cycles in random graphs | West ch.1–4 | — | cuckoo-graph failure analysis |
| Designs, difference sets | Schmidt (eds.) ch.1–2, ch.9 | Merris ch.6 | combinatorial constructions (hash families, sequences) |

## Optimisation and approximation (FHE polynomial approximation, SYM MILP/SAT)

| topic | first look | second opinion | crypto use |
|---|---|---|---|
| Convex sets/functions, duality | BV ch.2–5 | Brøndsted (polytopes) | LP relaxations, bounding arguments |
| Minimax / Chebyshev-style approximation, fitting | BV ch.6 | Grafakos (classical) ch.3 | CKKS polynomial approximation of non-linear functions |
| LP/MILP modelling, polytope facets, convex hulls | BV ch.4 | Brøndsted | MILP/SAT models of S-box transitions, active S-box bounds |
| Interior-point methods | BV ch.11 | — | solving large LP relaxations |

## Gaps (topics the local corpus does not cover well)

- **Rader / Bluestein / prime-factor FFT**: not in the corpus; use FFT literature directly.
- **Discrete Gaussians, smoothing parameter**: use the lattice reading list (Peikert survey, GPV08, MP12) rather than
  harmonic-analysis books.
- **Isogenies / elliptic curves beyond basics**: IR ch.18–19 is introductory only; use the PQC reading list.
- **Scanned books without a text layer** (Washington, Folland, Hungerford, one Grafakos volume, Jacobson III):
  an agent cannot full-text search them; either OCR your own copy locally or rely on the (pub) chapter TOCs.
