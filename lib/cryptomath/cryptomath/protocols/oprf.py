# TOY: not secure (small default group, naive hash-to-group, no verifiability)
"""Diffie–Hellman OPRF F_k(x) = H(H_G(x)^k) and the DH-PSI built from it.

References
----------
* M. J. Freedman, Y. Ishai, B. Pinkas, O. Reingold, "Keyword search and
  oblivious pseudorandom functions", TCC 2005 (OPRF notion).
* S. Jarecki, A. Kiayias, H. Krawczyk, "Round-optimal password-protected
  secret sharing and T-PAKE in the password-only model", ASIACRYPT 2014
  (2HashDH OPRF).
* C. Meadows, "A more efficient cryptographic matchmaking protocol",
  IEEE S&P 1986; B. A. Huberman, M. Franklin, T. Hogg, "Enhancing privacy
  and trust in electronic communities", EC 1999 (DH-based PSI).
* RFC 9497, "Oblivious Pseudorandom Functions (OPRFs) Using Prime-Order
  Groups", 2023 (production-grade construction).
"""
from __future__ import annotations

import hashlib

from ..ec.groups import ModPGroup


class DHOPRFServer:
    def __init__(self, group=None, key: int | None = None, rng=None):
        self.G = group or ModPGroup()
        self.k = key if key is not None else self.G.random_scalar(rng)

    def evaluate_blinded(self, B):
        return self.G.exp(B, self.k)

    def evaluate(self, x: bytes) -> bytes:
        """Direct (non-oblivious) evaluation with the key, for testing."""
        return _finalize(self.G, x, self.G.exp(self.G.hash_to_group(x), self.k))


def _finalize(G, x: bytes, elem) -> bytes:
    return hashlib.sha256(b"OPRF" + len(x).to_bytes(4, "big") + x + G.encode(elem)).digest()


class DHOPRFClient:
    def __init__(self, group=None, rng=None):
        self.G = group or ModPGroup()
        self.rng = rng

    def blind(self, x: bytes):
        r = self.G.random_scalar(self.rng)
        return r, self.G.exp(self.G.hash_to_group(x), r)

    def unblind(self, x: bytes, r: int, Z) -> bytes:
        rinv = pow(r, -1, self.G.order)
        return _finalize(self.G, x, self.G.exp(Z, rinv))


def oprf_eval(server: DHOPRFServer, x: bytes, rng=None) -> bytes:
    """Run the 2-message OPRF locally; returns F_k(x)."""
    c = DHOPRFClient(server.G, rng)
    r, B = c.blind(x)
    return c.unblind(x, r, server.evaluate_blinded(B))


def dh_psi(client_set, server_set, group=None, rng=None) -> set:
    """Toy semi-honest DH-PSI via the OPRF: client learns X ∩ Y.

    Server sends {F_k(y)}; client obliviously gets {F_k(x)} and intersects.
    """
    S = DHOPRFServer(group, rng=rng)
    server_tags = {S.evaluate(y) for y in server_set}
    return {x for x in client_set if oprf_eval(S, x, rng) in server_tags}
