"""cryptomath.ec -- small prime-field elliptic curves, toy groups and generic DLP attacks.

# TOY: not secure -- nothing here is constant time; parameters are tiny.

Modules
-------
curve   EllipticCurve (affine + Jacobian arithmetic, double-and-add, ladder),
        Tonelli–Shanks, naive point counting, prime-order curve search, secp256k1
        constants (for arithmetic self-tests only)
groups  uniform group interface: ModPGroup (QR subgroup of Z_p^*, safe prime),
        ZpStarGroup (full Z_p^*), ECGroup (prime-order subgroup of a curve)
dlp     baby-step giant-step, Pollard rho (r-adding walk), Pohlig–Hellman,
        generic cost estimates

Quick start::

    from cryptomath.ec import ECGroup, bsgs
    G = ECGroup.small(10007)
    h = G.exp(G.generator, 1234)
    bsgs(G, G.generator, h)          # -> 1234
"""
from .curve import (EllipticCurve, legendre, sqrt_mod, find_prime_order_curve,
                    SECP256K1, secp256k1)
from .groups import (ModPGroup, ZpStarGroup, ECGroup, safe_prime, SAFE_PRIME_64,
                     SAFE_PRIME_128)
from .dlp import bsgs, pollard_rho, pohlig_hellman, expected_generic_cost

__all__ = [n for n in dir() if not n.startswith("_")]
