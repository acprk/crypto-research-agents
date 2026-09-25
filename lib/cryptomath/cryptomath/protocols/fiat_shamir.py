# TOY: not secure (small default group; transcript is a simple hash chain, not a vetted design)
"""Fiat–Shamir transcript helper and the Schnorr sigma protocol.

References
----------
* A. Fiat, A. Shamir, "How to prove yourself: practical solutions to
  identification and signature problems", CRYPTO 1986.
* C. P. Schnorr, "Efficient signature generation by smart cards",
  J. Cryptology 1991.
* D. Bernhard, O. Pereira, B. Warinschi, "How not to prove yourself:
  pitfalls of the Fiat-Shamir heuristic and applications to Helios",
  ASIACRYPT 2012 (always hash the full statement: "strong" Fiat–Shamir).
"""
from __future__ import annotations

import hashlib

from ..ec.groups import ModPGroup


class Transcript:
    """Append-only transcript; challenges bind every previous message.

    Each append is length-prefixed and labelled, so different message
    splittings cannot collide.
    """

    def __init__(self, domain: bytes):
        self._h = hashlib.sha256()
        self._absorb(b"dom", domain)

    def _absorb(self, label: bytes, data: bytes):
        for part in (label, data):
            self._h.update(len(part).to_bytes(8, "big"))
            self._h.update(part)

    def append(self, label: bytes, data: bytes):
        self._absorb(b"msg:" + label, data)

    def append_int(self, label: bytes, x: int):
        self.append(label, x.to_bytes((max(x.bit_length(), 1) + 7) // 8, "big"))

    def challenge_bytes(self, label: bytes, n: int = 32) -> bytes:
        self._absorb(b"chal:" + label, n.to_bytes(4, "big"))
        out, ctr = b"", 0
        seed = self._h.copy().digest()
        while len(out) < n:
            out += hashlib.sha256(seed + ctr.to_bytes(4, "big")).digest()
            ctr += 1
        self._h.update(seed)   # ratchet: later challenges depend on this one
        return out[:n]

    def challenge_scalar(self, label: bytes, q: int) -> int:
        """Near-uniform integer mod q (128 extra bits to kill modulo bias)."""
        nbytes = (q.bit_length() + 128 + 7) // 8
        return int.from_bytes(self.challenge_bytes(label, nbytes), "big") % q


# ---------------------------------------------------------------------------
# Schnorr proof of knowledge of x with y = g^x
# ---------------------------------------------------------------------------
class SchnorrProver:
    def __init__(self, x: int, group=None, rng=None):
        self.G = group or ModPGroup()
        self.x = x % self.G.order
        self.y = self.G.exp(self.G.generator, self.x)
        self.rng = rng

    def commit(self):
        self.k = self.G.random_scalar(self.rng)
        return self.G.exp(self.G.generator, self.k)

    def respond(self, c: int) -> int:
        return (self.k + c * self.x) % self.G.order


def schnorr_verify(G, y, t, c: int, s: int) -> bool:
    """Check g^s == t * y^c."""
    return G.eq(G.exp(G.generator, s), G.op(t, G.exp(y, c)))


def schnorr_simulate(G, y, c: int, rng=None):
    """HVZK simulator: pick s, set t = g^s y^-c (transcript indistinguishable)."""
    s = G.random_scalar(rng)
    t = G.op(G.exp(G.generator, s), G.inv(G.exp(y, c)))
    return t, c, s


def _fs_challenge(G, y, t, context: bytes) -> int:
    tr = Transcript(b"schnorr-nizk")
    tr.append(b"ctx", context)
    tr.append(b"g", G.encode(G.generator))
    tr.append(b"y", G.encode(y))            # strong FS: include the statement
    tr.append(b"t", G.encode(t))
    return tr.challenge_scalar(b"c", G.order)


def schnorr_nizk_prove(x: int, group=None, context: bytes = b"", rng=None):
    """Non-interactive proof (t, s) of knowledge of log_g(y)."""
    P = SchnorrProver(x, group, rng)
    t = P.commit()
    c = _fs_challenge(P.G, P.y, t, context)
    return P.y, (t, P.respond(c))


def schnorr_nizk_verify(G, y, proof, context: bytes = b"") -> bool:
    t, s = proof
    return schnorr_verify(G, y, t, _fs_challenge(G, y, t, context), s)


def schnorr_extract(G, t, c1: int, s1: int, c2: int, s2: int) -> int:
    """Special soundness: two accepting transcripts with same t give x."""
    return (s1 - s2) * pow((c1 - c2) % G.order, -1, G.order) % G.order
