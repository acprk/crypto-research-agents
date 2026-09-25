"""cryptomath.protocols -- MPC / PSI building blocks and cost models.

# TOY: not secure -- every interactive protocol here is a local, semi-honest,
# small-parameter simulation for checking correctness and counting costs.

Modules
-------
secret_sharing  Shamir over GF(p), additive, replicated 3-party, Beaver triples
ot              Chou–Orlandi-style toy 1-out-of-2 OT; IKNP / KOS cost models
oprf            DH-based OPRF (blind/evaluate/unblind), toy DH-PSI
psi_cost        DH-PSI, KKRT16, VOLE-PSI, circuit-PSI leading-term formulas
matching        Hamming / L2 / L_inf distances, threshold & fuzzy matching, ball sizes
gc_cost         Bristol-fashion gate counter, garbling size (Yao .. half-gates .. three-halves)
commitments     hash commitment, Pedersen commitment
fiat_shamir     Transcript, Schnorr sigma protocol (+ NIZK, simulator, extractor)

Quick start::

    from cryptomath.protocols import shamir_share, shamir_reconstruct
    sh = shamir_share(42, t=3, n=5, p=2**61 - 1)
    shamir_reconstruct(sh[:3], 2**61 - 1)     # 42
"""
from .secret_sharing import (shamir_share, shamir_reconstruct, shamir_add, lagrange_at,
                             additive_share, additive_reconstruct, replicated_share,
                             replicated_reconstruct, replicated_mul_to_additive,
                             beaver_triple, beaver_multiply)
from .ot import (SimplestOTSender, SimplestOTReceiver, run_simplest_ot, OTExtensionCost,
                 iknp_cost, kos_cost)
from .oprf import DHOPRFServer, DHOPRFClient, oprf_eval, dh_psi
from .psi_cost import (PSICost, psi_output_len, naive_hash_psi, dh_psi_cost, kkrt_cost,
                       vole_psi_cost, circuit_psi_cost, compare_psi)
from .matching import (hamming, l2, l2_squared, linf, cosine_similarity, threshold_match,
                       fuzzy_intersection, hamming_ball_size, linf_ball_size, random_close_pair)
from .gc_cost import (GateCount, SCHEMES as GC_SCHEMES, parse_bristol, count_gates, adder_cost,
                      comparator_cost, equality_cost, multiplier_cost, hamming_threshold_cost)
from .commitments import hash_commit, hash_verify, Pedersen
from .fiat_shamir import (Transcript, SchnorrProver, schnorr_verify, schnorr_simulate,
                          schnorr_nizk_prove, schnorr_nizk_verify, schnorr_extract)

__all__ = [n for n in dir() if not n.startswith("_")]
