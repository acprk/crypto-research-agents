# TOY: not secure
"""LFSR / NLFSR and a small Grain-like stream cipher, plus Berlekamp–Massey.

References
----------
* S. W. Golomb, *Shift Register Sequences*, 1967.
* J. L. Massey, "Shift-register synthesis and BCH decoding", IEEE Trans. IT,
  1969 (Berlekamp–Massey algorithm).
* M. Hell, T. Johansson, W. Meier, "Grain: a stream cipher for constrained
  environments", IJWMC 2007 / eSTREAM (structure of the toy Grain below).
"""
from __future__ import annotations


class LFSR:
    """Fibonacci LFSR over GF(2).

    ``taps`` are the indices i such that s_{t+L} = XOR_i s_{t+i}.
    Output bit at each clock is s_t (state bit 0).
    """

    def __init__(self, length: int, taps, state: int):
        self.L = length
        self.taps = list(taps)
        self.state = state & ((1 << length) - 1)

    def clock(self) -> int:
        out = self.state & 1
        fb = 0
        for t in self.taps:
            fb ^= (self.state >> t) & 1
        self.state = (self.state >> 1) | (fb << (self.L - 1))
        return out

    def keystream(self, nbits: int) -> list[int]:
        return [self.clock() for _ in range(nbits)]

    def period(self, limit: int | None = None) -> int:
        start = self.state
        limit = limit or (1 << self.L) + 1
        for i in range(1, limit + 1):
            self.clock()
            if self.state == start:
                return i
        return -1


class NLFSR:
    """Fibonacci NLFSR: new bit = feedback(state_bits_list)."""

    def __init__(self, length: int, feedback, state: int):
        self.L = length
        self.f = feedback
        self.state = state & ((1 << length) - 1)

    def bits(self) -> list[int]:
        return [(self.state >> i) & 1 for i in range(self.L)]

    def clock(self, extra: int = 0) -> int:
        out = self.state & 1
        fb = (self.f(self.bits()) ^ extra) & 1
        self.state = (self.state >> 1) | (fb << (self.L - 1))
        return out


def berlekamp_massey(bits) -> tuple[int, list[int]]:
    """Linear complexity L and connection polynomial C (C[0] = 1) over GF(2)."""
    s = [int(b) & 1 for b in bits]
    C, B = [1], [1]
    L, m = 0, 1
    for n in range(len(s)):
        d = s[n]
        for i in range(1, L + 1):
            if i < len(C):
                d ^= C[i] & s[n - i]
        if d == 0:
            m += 1
            continue
        T = C[:]
        need = len(B) + m
        if len(C) < need:
            C = C + [0] * (need - len(C))
        for i, b in enumerate(B):
            C[i + m] ^= b
        if 2 * L <= n:
            L, B, m = n + 1 - L, T, 1
        else:
            m += 1
    return L, C[: L + 1]


class ToyGrain:
    """Grain-like toy: 16-bit LFSR + 16-bit NLFSR + nonlinear filter.  # TOY: not secure

    Init: NLFSR <- key (16 bits), LFSR <- iv (12 bits) || 1111; clock
    ``init_rounds`` times feeding the output back into both registers;
    then output z_t = h(s, b) ^ b_0 ^ b_4 ^ s_6 (Grain-style masked filter).
    """

    LFSR_TAPS = [0, 2, 3, 5]          # x^16 + x^5 + x^3 + x^2 + 1 (primitive)

    def __init__(self, key: int, iv: int, init_rounds: int = 64):
        self.l = LFSR(16, self.LFSR_TAPS, (iv & 0xFFF) | (0xF << 12))
        self.n = NLFSR(16, self._g, key & 0xFFFF)
        for _ in range(init_rounds):
            z = self._z()
            lb = self.l.state & 1
            self.l.clock()
            self.l.state ^= z << 15
            self.n.clock(extra=lb ^ z)

    @staticmethod
    def _g(b):
        return b[0] ^ b[3] ^ b[7] ^ b[11] ^ (b[2] & b[9]) ^ (b[5] & b[13]) ^ (b[1] & b[6] & b[12])

    def _z(self) -> int:
        s = [(self.l.state >> i) & 1 for i in range(16)]
        b = [(self.n.state >> i) & 1 for i in range(16)]
        h = (s[1] & s[8]) ^ (s[4] & b[10]) ^ (s[12] & b[14]) ^ (s[1] & s[4] & s[12]) ^ b[15]
        return h ^ b[0] ^ b[4] ^ s[6]

    def clock(self) -> int:
        z = self._z()
        lb = self.l.state & 1
        self.l.clock()
        self.n.clock(extra=lb)
        return z

    def keystream(self, nbits: int) -> list[int]:
        return [self.clock() for _ in range(nbits)]
