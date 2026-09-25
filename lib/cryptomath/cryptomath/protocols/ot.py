# TOY: not secure (small groups, no malicious-security checks, no constant time)
"""Oblivious transfer: a toy "simplest OT" and an IKNP OT-extension cost model.

References
----------
* T. Chou, C. Orlandi, "The simplest protocol for oblivious transfer",
  LATINCRYPT 2015 (ePrint 2015/267).  NB: later work pointed out subtleties
  in its UC proof; it is used here only as a readable toy.
* Y. Ishai, J. Kilian, K. Nissim, E. Petrank, "Extending oblivious
  transfers efficiently", CRYPTO 2003 (IKNP).
* M. Keller, E. Orsini, P. Scholl, "Actively secure OT extension with
  optimal overhead", CRYPTO 2015 (KOS).
* E. Boyle, G. Couteau, N. Gilboa, Y. Ishai, L. Kohl, P. Scholl, "Efficient
  two-round OT extension and silent non-interactive secure computation",
  CCS 2019 (silent OT; sublinear communication).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..ec.groups import ModPGroup


def _kdf(group, elem, label: bytes, nbytes: int) -> bytes:
    out, ctr = b"", 0
    while len(out) < nbytes:
        out += hashlib.sha256(label + ctr.to_bytes(4, "big") + group.encode(elem)).digest()
        ctr += 1
    return out[:nbytes]


def _xor(a: bytes, b: bytes) -> bytes:
    return bytes(x ^ y for x, y in zip(a, b))


class SimplestOTSender:
    """Sender with messages (m0, m1) of equal length."""

    def __init__(self, group=None, rng=None):
        self.G = group or ModPGroup()
        self.a = self.G.random_scalar(rng)
        self.A = self.G.exp(self.G.generator, self.a)

    def first_message(self):
        return self.A

    def respond(self, B, m0: bytes, m1: bytes):
        if len(m0) != len(m1):
            raise ValueError("messages must have equal length")
        G = self.G
        k0 = _kdf(G, G.exp(B, self.a), b"OT0", len(m0))
        BA = G.op(B, G.inv(self.A))
        k1 = _kdf(G, G.exp(BA, self.a), b"OT1", len(m1))
        return _xor(m0, k0), _xor(m1, k1)


class SimplestOTReceiver:
    def __init__(self, choice: int, group=None, rng=None):
        self.G = group or ModPGroup()
        self.c = choice & 1
        self.b = self.G.random_scalar(rng)

    def second_message(self, A):
        self.A = A
        gb = self.G.exp(self.G.generator, self.b)
        return self.G.op(A, gb) if self.c else gb

    def decrypt(self, e0: bytes, e1: bytes) -> bytes:
        k = _kdf(self.G, self.G.exp(self.A, self.b), b"OT1" if self.c else b"OT0", len(e0))
        return _xor(e1 if self.c else e0, k)


def run_simplest_ot(m0: bytes, m1: bytes, choice: int, group=None, rng=None) -> bytes:
    """Run both parties locally; returns the receiver's output m_choice."""
    S = SimplestOTSender(group, rng)
    R = SimplestOTReceiver(choice, S.G, rng)
    B = R.second_message(S.first_message())
    e0, e1 = S.respond(B, m0, m1)
    return R.decrypt(e0, e1)


@dataclass
class OTExtensionCost:
    base_ots: int
    comm_bits_receiver: int
    comm_bits_sender: int
    hash_calls: int
    prg_bits: int

    @property
    def total_comm_bits(self) -> int:
        return self.comm_bits_receiver + self.comm_bits_sender

    @property
    def total_comm_MiB(self) -> float:
        return self.total_comm_bits / 8 / 2 ** 20


def iknp_cost(m: int, ell: int, kappa: int = 128, random_ot: bool = False) -> OTExtensionCost:
    """Semi-honest IKNP: extend kappa base OTs to m OTs on ell-bit strings.

    Receiver -> sender: m x kappa bit matrix (m * kappa bits).
    Sender -> receiver: 2 m ell bits (0 for random-OT outputs).
    Hashes: 2m (sender) + m (receiver).  Base-OT cost not included.
    """
    return OTExtensionCost(
        base_ots=kappa,
        comm_bits_receiver=m * kappa,
        comm_bits_sender=0 if random_ot else 2 * m * ell,
        hash_calls=3 * m,
        prg_bits=2 * kappa * m,
    )


def kos_cost(m: int, ell: int, kappa: int = 128, stat: int = 40) -> OTExtensionCost:
    """KOS15 (malicious): IKNP plus a correlation check on kappa + stat extra rows."""
    base = iknp_cost(m, ell, kappa)
    base.comm_bits_receiver = (m + kappa + stat) * kappa + 2 * kappa  # extra rows + check values
    base.prg_bits = 2 * kappa * (m + kappa + stat)
    return base
