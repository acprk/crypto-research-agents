# cryptomath: `symmetric`, `protocols`, `ec`

This section covers three subpackages. All three are **toy / screening code**.
None of it is constant time, the parameters are small, and every interactive
protocol runs both parties in one process. Use it to check an idea, count
operations, or build a known-answer test. Never use it to protect data.

Run the tests (numpy and sympy required; scipy and a SAT solver are optional):

```bash
cd lib/cryptomath
python3 -m unittest discover -s tests -p "test_symmetric*.py"
python3 -m unittest discover -s tests -p "test_protocols*.py"
python3 -m unittest discover -s tests -p "test_ec*.py"
```

## `cryptomath.symmetric`

| module | contents |
|---|---|
| `gf2n` | `GF2n(n)` arithmetic, irreducibility test, `power_map(d, n)`, `inverse_map`, Gold/Kasami exponent detection with their APN criteria |
| `boolean` | Möbius transform (truth table ↔ ANF), `walsh`, `is_bent`, `nonlinearity`, `correlation_immunity`, `resiliency`, `algebraic_immunity` (for small n), autocorrelation |
| `sbox` | `ddt`, `lat`, `bct`, `differential_uniformity`, `linearity`/`nonlinearity`, `algebraic_degree`, `is_apn`, `boomerang_uniformity`, differential and linear branch numbers, `sbox_report` |
| `aes` | AES-128 reference checked against FIPS-197 (App. B, C.1). Supports round-reduced variants, with or without MixColumns in the last round |
| `spn` | `ToySPN`: PRESENT-like, 8/16/32/64-bit, independent round keys. `ToyFeistel` |
| `stream` | `LFSR`, `NLFSR`, `berlekamp_massey`, `ToyGrain` (16+16-bit Grain-like) |
| `trails` | Matsui branch-and-bound (`best_trail_bnb`), exact min-plus DP (`best_trail_exhaustive`, `min_active_sboxes_exhaustive`), DIMACS CNF export (`CNF` with Tseitin or native CryptoMiniSat XOR, Sinz cardinality), MILP export (`MILPModel.to_lp()` in CPLEX-LP format, `solve_scipy()`), optional `run_sat_solver` |
| `integral` | square/integral distinguisher on `ToySPN`, exact output degrees for tiny blocks, cube-sum degree lower bound, Boura–Canteaut–De Cannière degree upper bound |
| `afcost` | formula cost models for MiMC, HADES/Poseidon, Rasta, LowMC, Trivium-like ciphers and Boolean AES. Each reports multiplications/ANDs, depth and cost per output |

Each exact method has an independent check on toy sizes. The tests confirm
that branch-and-bound, the exhaustive DP, the MILP optimum and the SAT
threshold all agree on the 16-bit PRESENT-like SPN.

```python
from cryptomath.symmetric import PRESENT_SBOX, present_permutation, best_trail_bnb, spn_active_sbox_milp
perm = present_permutation(16)
Bn, trail = best_trail_bnb(PRESENT_SBOX, perm, rounds=4)       # weights per round count
spn_active_sbox_milp(PRESENT_SBOX, perm, 3).write("spn3.lp")    # feed to Gurobi/HiGHS/glpsol
```

Known-answer tests included:
- AES FIPS-197 vectors.
- AES S-box: differential uniformity 4, nonlinearity 112, degree 7, boomerang uniformity 6.
- PRESENT S-box: DDT maximum 4.
- x³ is APN over GF(2ⁿ) for odd n.
- A bent function has flat Walsh spectrum ±4.
- Majority has optimal algebraic immunity.

## `cryptomath.protocols`

| module | contents |
|---|---|
| `secret_sharing` | Shamir over GF(p), additive, replicated 3-party with local multiplication, Beaver triples and multiplication |
| `ot` | Chou–Orlandi-style toy 1-out-of-2 OT (works over any group from `ec.groups`); `iknp_cost`, `kos_cost` |
| `oprf` | 2HashDH-style OPRF (blind, evaluate, unblind) and a toy DH-PSI built on it |
| `psi_cost` | leading-term communication and computation formulas for naive hashing, DH-PSI, KKRT16, VOLE-PSI and circuit-PSI. Constants are parameters |
| `matching` | Hamming, L2 and L∞ distances, threshold and fuzzy matching (plaintext reference), Hamming and L∞ ball sizes |
| `gc_cost` | Bristol-fashion gate counter with AND-depth; garbled size under Yao, point-and-permute, GRR3, free-XOR, half-gates and three-halves; gate counts for adders, comparators, equality, multipliers and Hamming thresholds |
| `commitments` | hash commitment, Pedersen commitment (homomorphic) |
| `fiat_shamir` | `Transcript` (labelled, length-prefixed, ratcheting), Schnorr sigma protocol with NIZK, HVZK simulator and special-soundness extractor |

The formulas in `psi_cost` are for **screening**. They drop lower-order
terms, and the defaults for code width, OKVS expansion and bin factor come
from specific paper versions. The silent-VOLE term is a labelled placeholder
unless you supply a measured value. Before any number goes into a paper,
measure the real implementation and record it in the EVIDENCE ledger.

## `cryptomath.ec`

| module | contents |
|---|---|
| `curve` | `EllipticCurve` over GF(p): affine and Jacobian arithmetic, double-and-add, Montgomery ladder, Tonelli–Shanks, naive point counting, `find_prime_order_curve`, secp256k1 constants for arithmetic self-tests |
| `groups` | one interface over three groups: `ModPGroup` (QR subgroup of a safe prime), `ZpStarGroup`, `ECGroup` |
| `dlp` | `bsgs`, `pollard_rho` (Teske r-adding walk with Floyd cycle detection), `pohlig_hellman`, `expected_generic_cost` |

```python
from cryptomath.ec import ECGroup, bsgs, pollard_rho
G = ECGroup.small(100003, seed=5)            # prime-order toy curve
h = G.exp(G.generator, 31337)
assert bsgs(G, G.generator, h) == pollard_rho(G, G.generator, h) == 31337
```

## References (public)

Each module docstring lists its references. The main ones:
- FIPS-197; Bogdanov et al., CHES 2007 (PRESENT).
- Nyberg, EUROCRYPT 1993; Cid et al., EUROCRYPT 2018 (BCT).
- Matsui, EUROCRYPT 1994 (branch-and-bound); Mouha et al., Inscrypt 2011 and Sun et al., ASIACRYPT 2014 (MILP).
- Sinz, CP 2005 (sequential counter); Boura–Canteaut–De Cannière, FSE 2011 (degree bound).
- Albrecht et al., ASIACRYPT 2016 (MiMC); Grassi et al., USENIX Security 2021 (Poseidon); Dobraunig et al., CRYPTO 2018 (Rasta).
- Shamir, CACM 1979; Beaver, CRYPTO 1991; Araki et al., CCS 2016 (replicated sharing).
- Chou–Orlandi, LATINCRYPT 2015; Ishai–Kilian–Nissim–Petrank, CRYPTO 2003 (IKNP).
- Kolesnikov et al., CCS 2016 (KKRT); Pinkas et al., EUROCRYPT 2019 (circuit-PSI); Rindal–Schoppmann, EUROCRYPT 2021 (VOLE-PSI).
- Zahur–Rosulek–Evans, EUROCRYPT 2015 (half-gates); Rosulek–Roy, CRYPTO 2021 (three-halves).
- Pedersen, CRYPTO 1991; Schnorr, J. Cryptology 1991; Shanks 1971; Pollard 1978; Pohlig–Hellman 1978.
