# TOY: not secure
"""Small PRESENT-like SPN and a toy Feistel network, for attack experiments.

ToySPN: block of B in {8, 16, 32, 64} bits made of B/4 copies of a 4-bit
S-box followed by the PRESENT-style bit permutation
    P(i) = i * B/4 mod (B - 1),  P(B - 1) = B - 1,
with independent round keys (key-alternating: k_0, S, P, k_1, ..., S, P, k_r).

References
----------
* A. Bogdanov, L. R. Knudsen, G. Leander, C. Paar, A. Poschmann, M. J. B.
  Robshaw, Y. Seurin, C. Vikkelsoe, "PRESENT: an ultra-lightweight block
  cipher", CHES 2007.
* H. M. Heys, "A tutorial on linear and differential cryptanalysis",
  Cryptologia 2002 (toy 16-bit SPN used for teaching).
* H. Feistel, "Cryptography and computer privacy", Sci. Am. 1973.
"""
from __future__ import annotations

import random

from .sbox import PRESENT_SBOX, inverse_sbox


def present_permutation(block_bits: int) -> list[int]:
    """PRESENT-like bit permutation: bit i moves to position P[i]."""
    B = block_bits
    if B % 4 or B < 8:
        raise ValueError("block_bits must be a multiple of 4, >= 8")
    return [(i * (B // 4)) % (B - 1) if i != B - 1 else B - 1 for i in range(B)]


def apply_bit_perm(x: int, perm: list[int]) -> int:
    y = 0
    for i, p in enumerate(perm):
        y |= ((x >> i) & 1) << p
    return y


def invert_perm(perm: list[int]) -> list[int]:
    inv = [0] * len(perm)
    for i, p in enumerate(perm):
        inv[p] = i
    return inv


class ToySPN:
    """PRESENT-like key-alternating SPN.

    Parameters
    ----------
    block_bits : 8, 16, 32 or 64.
    rounds     : number of S-layer + P-layer rounds (last round keeps P).
    sbox       : 4-bit S-box (default PRESENT).
    round_keys : list of rounds + 1 ints; if None, drawn from ``seed``.
    """

    def __init__(self, block_bits: int = 16, rounds: int = 4, sbox=None, perm=None,
                 round_keys=None, seed: int | None = None):
        self.B = block_bits
        self.rounds = rounds
        self.sbox = list(sbox if sbox is not None else PRESENT_SBOX)
        self.sbits = (len(self.sbox) - 1).bit_length()
        if self.B % self.sbits:
            raise ValueError("block size must be a multiple of the S-box size")
        self.nsb = self.B // self.sbits
        self.inv_sbox = inverse_sbox(self.sbox)
        self.perm = list(perm) if perm is not None else present_permutation(block_bits)
        self.inv_perm = invert_perm(self.perm)
        self.mask = (1 << self.B) - 1
        if round_keys is None:
            rng = random.Random(seed)
            round_keys = [rng.getrandbits(self.B) for _ in range(rounds + 1)]
        if len(round_keys) != rounds + 1:
            raise ValueError("need rounds + 1 round keys")
        self.round_keys = [k & self.mask for k in round_keys]

    # --- layers ----------------------------------------------------------
    def s_layer(self, x: int, inverse: bool = False) -> int:
        tab = self.inv_sbox if inverse else self.sbox
        w, m = self.sbits, (1 << self.sbits) - 1
        y = 0
        for j in range(self.nsb):
            y |= tab[(x >> (w * j)) & m] << (w * j)
        return y

    def p_layer(self, x: int, inverse: bool = False) -> int:
        return apply_bit_perm(x, self.inv_perm if inverse else self.perm)

    # --- cipher ----------------------------------------------------------
    def encrypt(self, x: int, rounds: int | None = None) -> int:
        r = self.rounds if rounds is None else rounds
        for i in range(r):
            x = self.p_layer(self.s_layer(x ^ self.round_keys[i]))
        return x ^ self.round_keys[r]

    def decrypt(self, y: int, rounds: int | None = None) -> int:
        r = self.rounds if rounds is None else rounds
        y ^= self.round_keys[r]
        for i in reversed(range(r)):
            y = self.s_layer(self.p_layer(y, inverse=True), inverse=True) ^ self.round_keys[i]
        return y

    def codebook(self, rounds: int | None = None):
        """Full codebook as numpy array (block_bits <= 20 only)."""
        import numpy as np
        if self.B > 20:
            raise ValueError("codebook only for tiny blocks")
        return np.array([self.encrypt(x, rounds) for x in range(1 << self.B)], dtype=np.int64)


class ToyFeistel:
    """Balanced Feistel network on 2*half_bits bits.

    F(x, k) = rotl(S-layer(x ^ k), 1) using the given 4-bit S-box.  # TOY: not secure
    """

    def __init__(self, half_bits: int = 8, rounds: int = 8, sbox=None,
                 round_keys=None, seed: int | None = None):
        if half_bits % 4:
            raise ValueError("half_bits must be a multiple of 4")
        self.h = half_bits
        self.rounds = rounds
        self.sbox = list(sbox if sbox is not None else PRESENT_SBOX)
        self.mask = (1 << half_bits) - 1
        if round_keys is None:
            rng = random.Random(seed)
            round_keys = [rng.getrandbits(half_bits) for _ in range(rounds)]
        self.round_keys = [k & self.mask for k in round_keys]

    def F(self, x: int, k: int) -> int:
        x ^= k
        y = 0
        for j in range(self.h // 4):
            y |= self.sbox[(x >> (4 * j)) & 0xF] << (4 * j)
        return ((y << 1) | (y >> (self.h - 1))) & self.mask

    def encrypt(self, x: int) -> int:
        L, R = x >> self.h, x & self.mask
        for k in self.round_keys:
            L, R = R, L ^ self.F(R, k)
        return (L << self.h) | R

    def decrypt(self, y: int) -> int:
        L, R = y >> self.h, y & self.mask
        for k in reversed(self.round_keys):
            L, R = R ^ self.F(L, k), L
        return (L << self.h) | R
