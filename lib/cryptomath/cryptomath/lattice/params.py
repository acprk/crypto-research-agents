"""Parameter selection helpers from the public Homomorphic Encryption
Standard tables.

Values: maximum log2(q) for ring dimension n at a given security level,
uniform *ternary* secret, error sigma ~ 3.2, as published in

  M. Albrecht et al., "Homomorphic Encryption Standard", HomomorphicEncryption.org
  technical report, Nov 2018 (also in "Protecting Privacy through Homomorphic
  Encryption", Springer 2021).  https://homomorphicencryption.org/standard/

They were produced with a 2018 version of the lattice-estimator; later
estimator versions (and newer attacks) move these numbers by a few bits.
Treat them as APPROXIMATE and re-run the estimator for any paper claim.
"""
from __future__ import annotations

from typing import Dict, Optional

__all__ = ["HE_STANDARD_TERNARY", "max_logq", "min_ring_dim", "APPROXIMATE_NOTE"]

APPROXIMATE_NOTE = ("HE-standard (2018) table values; approximate -- re-check with the "
                    "current lattice-estimator before relying on them.")

# {model: {security_bits: {n: max_log2_q}}}
HE_STANDARD_TERNARY: Dict[str, Dict[int, Dict[int, int]]] = {
    "classical": {
        128: {1024: 27, 2048: 54, 4096: 109, 8192: 218, 16384: 438, 32768: 881},
        192: {1024: 19, 2048: 37, 4096: 75, 8192: 152, 16384: 305, 32768: 611},
        256: {1024: 14, 2048: 29, 4096: 58, 8192: 118, 16384: 237, 32768: 476},
    },
    "quantum": {
        128: {1024: 25, 2048: 51, 4096: 101, 8192: 202, 16384: 411, 32768: 827},
        192: {1024: 17, 2048: 35, 4096: 70, 8192: 141, 16384: 284, 32768: 571},
        256: {1024: 13, 2048: 27, 4096: 54, 8192: 109, 16384: 220, 32768: 443},
    },
}


def max_logq(n: int, security: int = 128, model: str = "classical") -> Optional[int]:
    """Largest log2(q) allowed for ring dimension n (None if n not tabulated)."""
    return HE_STANDARD_TERNARY[model][security].get(n)


def min_ring_dim(log_q: float, security: int = 128, model: str = "classical") -> Optional[int]:
    """Smallest tabulated power-of-two n with max_logq(n) >= log_q (None if too large)."""
    for n, lq in sorted(HE_STANDARD_TERNARY[model][security].items()):
        if lq >= log_q:
            return n
    return None
