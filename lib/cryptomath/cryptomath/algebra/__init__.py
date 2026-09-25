"""Algebra for lattice / FHE research: number theory, finite fields,
cyclotomic rings, Galois automorphisms, slots, NTT, Z_{p^e} helpers and
Dirichlet characters.  Pure Python + numpy; exact integer arithmetic.

Module map
----------
ntheory        phi, lambda, mult_order, primitive roots, (Z/m)^* subgroups/cosets, NTT primes
poly           list-polynomial arithmetic, cyclotomic_poly, PolyRing (Z_q[X]/Phi_m), automorphisms
finite_field   GF(p^k) with irreducibility test (Rabin)
slots          decomposition of p in Q(zeta_m), factor Phi_m mod p, Hensel lift, SlotEncoder
ntt            radix-2 cyclic/negacyclic NTT, Bluestein DFT, CyclotomicNTT for any m
padic          Hensel roots, digits, polynomial functions / null polys mod n,
               Halevi-Shoup lifting + digit extraction, lowest-digit-retain polynomial
characters     Dirichlet characters, Gauss / character / exponential sums
"""
from .ntheory import *  # noqa: F401,F403
from .poly import *  # noqa: F401,F403
from .finite_field import *  # noqa: F401,F403
from .slots import *  # noqa: F401,F403
from .ntt import *  # noqa: F401,F403
from .padic import *  # noqa: F401,F403
from .characters import *  # noqa: F401,F403
