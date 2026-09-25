# cryptomath

Readable, toy-scale cryptography mathematics for **screening research ideas**:
check an algebraic fact, count the operations of a candidate algorithm, or run
a small homomorphic computation end to end. It is built for correctness and
readability, not speed.

> **Everything in `fhe/`, `lattice/`, `protocols/`, `ec/` and the toy ciphers is
> insecure** (tiny parameters, non-cryptographic RNG, no constant-time code).
> These files start with `# TOY: not secure`. Never use them to protect data.
> Before a number from here goes into a paper, re-derive it with a real tool
> (lattice-estimator, OpenFHE, TFHE-rs, Sage) and give it an EVIDENCE row.

## Install / test

```bash
cd lib/cryptomath
pip install -e .                 # optional; tests also run without installing
python3 -m unittest discover -s tests      # or: python3 -m pytest -q tests
```

Dependencies: Python ≥ 3.10, numpy, sympy (matplotlib optional). Sage and the
`lattice-estimator` are optional; imports of them are guarded.

`import cryptomath` loads subpackages lazily. If a subpackage is missing or
broken, the rest still works. `cryptomath.available()` reports which
subpackages import cleanly.

## Module map

| subpackage | modules | what you get |
|---|---|---|
| `algebra` | `ntheory` | factorisation, φ, λ, multiplicative order, primitive roots, (Z/m)^* generators / subgroups / cosets, NTT-friendly primes |
| | `poly` | list-polynomial arithmetic over Z and Z_q, Φ_m, `PolyRing` = Z_q[X]/Φ_m (negacyclic fast path), Galois automorphisms X→X^k, Newton inversion mod p^e |
| | `finite_field` | GF(p^k) (Rabin irreducibility test), minimal polynomials, roots of unity |
| | `slots` | how p splits in Q(ζ_m) (e, f, g), Φ_m factored mod p, Hensel lifting to p^e, `SlotEncoder` (CRT packing), hypercube generators of (Z/m)^*/⟨p⟩ |
| | `ntt` | radix-2 cyclic and negacyclic NTT, Bluestein DFT for any length, `CyclotomicNTT` for any m |
| | `padic` | Hensel roots, base-p digits, polynomial functions and null polynomials mod n (Kempner), Halevi–Shoup lifting polynomial and digit extraction, lowest-digit-retain polynomial (Chen–Han bound) |
| | `characters` | Dirichlet characters, conductors, annihilators of subgroups, Gauss / character / exponential sums |
| `lattice` | `distributions` | discrete Gaussian, CBD, ternary, binary, sparse ternary, with variances |
| | `samplers` | LWE / RLWE / MLWE instances and NTRU keys, returned together with the secret |
| | `estimate` | δ(β), GSA, core-SVP (0.292β / 0.265β / 0.2075β), primal uSVP, a simple dual attack, and a `lattice-estimator` wrapper |
| | `bkz_sim` | GSA profile and a Chen–Nguyen-style BKZ simulator |
| | `lll` | exact rational LLL (dimension ≤ ~30), Gram–Schmidt, Kannan embedding |
| | `params` | HE-standard (2018) maximum log q tables (**approximate**) |
| `fhe` | `bgv`, `bfv`, `ckks` | toy RLWE schemes: keygen, encryption, add, mul, relinearisation, modswitch / rescale, Galois rotations, slots, measured noise budget |
| | `tfhe` | LWE / GLWE / GGSW, gadget decomposition, external product, CMux, blind rotation, sample extraction, key switching, PBS with any LUT |
| | `noise` | analytic noise-variance formulas for every operation above, converted to budget bits or failure probability |
| | `polyeval` | Horner, Paterson–Stockmeyer, BSGS in the power and Chebyshev bases, with closed-form counts |
| | `bootstrap` | Chebyshev mod-reduction (sine and double-angle), BSGS linear transforms, CoeffToSlot cost, BGV digit-extraction cost |
| `costmodel` | `counter`, `traced`, `formulas` | `Counter` context, `count` / `counted` hooks, `Traced` values (nonscalar-mult and depth counting), sympy `CostFormula`, `compare()` report |
| `symmetric` | see its README | S-box / Boolean analysis, toy ciphers, trail search, cost formulas for arithmetisation-friendly ciphers |
| `protocols` | see its README | secret sharing, OT, OPRF, PSI and garbled-circuit cost models |
| `ec` | see its README | small elliptic curves, toy groups, BSGS / rho / Pohlig–Hellman |

(`README_symmetric_protocols_ec.md` documents the last three.)

## Quick examples

```python
from cryptomath.algebra import decomposition, SlotEncoder, cyclotomic_poly, lowest_digit_retain_poly
decomposition(2, 31)            # {'e': 1, 'f': 5, 'g': 6, ...}: 6 slots of GF(2^5)
enc = SlotEncoder(m=15, p=2, e=3)   # slots over the Galois ring GR(8, 4)
len(lowest_digit_retain_poly(5, 3)) - 1   # 9 = (e-1)(p-1)+1

from cryptomath.lattice import estimate_lwe
estimate_lwe(1024, 2**27, 3.19, sigma_s=(2/3)**0.5)["primal_usvp"]["beta"]

from cryptomath.fhe import BGV, CKKS, TFHE
bgv = BGV(N=16, t=257, levels=2, seed=1)
ct = bgv.mul(bgv.encrypt([1, 2]), bgv.encrypt([3]))
bgv.decrypt(ct)[:2], bgv.noise_budget(ct)       # ([3, 6], ~60 bits)

tf = TFHE(seed=1)
tf.decrypt(tf.pbs(tf.encrypt(5, 8), lambda m: m * m % 8, 8), 8)   # 1

# count operations before implementing anything
from cryptomath.costmodel import Counter, Traced
from cryptomath.fhe.polyeval import paterson_stockmeyer, bsgs_eval
coeffs = list(range(1, 65))
with Counter() as ps:  y = paterson_stockmeyer(coeffs, Traced(0.5))
with Counter() as bs:  z = bsgs_eval(coeffs, Traced(0.5))
ps["ctxt_mult"], y.depth, bs["ctxt_mult"], z.depth   # fewer mults vs. lower depth
```

Screening workflow: write the new idea and the baseline as plain Python
functions over abstract operations or `Traced` values. Then
`compare(new, baseline, *args)` checks that the outputs agree and prints a
Markdown table of op counts and weighted cost. Only implement ideas that
pass this screen for real.

## Conventions

* Polynomials are coefficient lists, lowest degree first. Ring elements are
  numpy `object` arrays of Python ints, so arithmetic is exact at any modulus size.
* σ always means the standard deviation. The width s = σ√(2π).
* TFHE uses the discretised torus Z_{2^32}. Noise variances are given as fractions of the torus.
* Each module docstring cites its public sources (author, year, and ePrint
  number where available).
