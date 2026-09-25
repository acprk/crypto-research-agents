# TOY: not secure (Pedersen over a small default group; h derived by naive hash-to-group)
"""Commitment schemes: hash-based and Pedersen.

References
----------
* T. P. Pedersen, "Non-interactive and information-theoretic secure
  verifiable secret sharing", CRYPTO 1991.
* S. Halevi, S. Micali, "Practical and provably-secure commitment schemes
  from collision-free hashing", CRYPTO 1996 (hash commitments).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from ..ec.groups import ModPGroup


def hash_commit(message: bytes, opening: bytes | None = None) -> tuple[bytes, bytes]:
    """C = SHA-256("commit" || r || m) with 32-byte random r.  Returns (C, r).

    Hiding in the random-oracle model, binding by collision resistance.
    """
    r = opening if opening is not None else secrets.token_bytes(32)
    return hashlib.sha256(b"commit" + r + message).digest(), r


def hash_verify(commitment: bytes, message: bytes, opening: bytes) -> bool:
    return hmac.compare_digest(hash_commit(message, opening)[0], commitment)


class Pedersen:
    """C = g^m h^r in a prime-order group with log_g(h) unknown.

    Perfectly hiding, computationally binding (DLOG); additively homomorphic:
    commit(m1, r1) * commit(m2, r2) = commit(m1 + m2, r1 + r2).
    """

    def __init__(self, group=None, h=None):
        self.G = group or ModPGroup()
        self.g = self.G.generator
        self.h = h if h is not None else self.G.hash_to_group(b"Pedersen-h")

    def commit(self, m: int, r: int | None = None, rng=None):
        r = r if r is not None else self.G.random_scalar(rng)
        C = self.G.op(self.G.exp(self.g, m), self.G.exp(self.h, r))
        return C, r

    def verify(self, C, m: int, r: int) -> bool:
        return self.G.eq(C, self.commit(m, r)[0])

    def add(self, C1, C2):
        return self.G.op(C1, C2)
