# TOY: not secure (reference implementation, not constant time; for analysis only)
"""AES-128 reference implementation with round-reduced variants.

Validated against the FIPS-197 test vectors (Appendix B and C.1).

References
----------
* NIST FIPS-197, "Advanced Encryption Standard (AES)", 2001.
* J. Daemen, V. Rijmen, *The Design of Rijndael*, Springer 2002.

Round-reduced convention: ``rounds=r`` applies the initial AddRoundKey,
r-1 full rounds and a final round without MixColumns (as the full cipher
does for r = 10).  Pass ``final_mixcolumns=True`` to keep MixColumns in the
last round (common in some distinguisher papers).
"""
from __future__ import annotations

from .gf2n import GF2n

_F = GF2n(8)


def _build_sbox() -> list[int]:
    sb = []
    for x in range(256):
        b = _F.inv(x)
        y = 0
        for i in range(8):
            bit = ((b >> i) ^ (b >> ((i + 4) % 8)) ^ (b >> ((i + 5) % 8))
                   ^ (b >> ((i + 6) % 8)) ^ (b >> ((i + 7) % 8)) ^ (0x63 >> i)) & 1
            y |= bit << i
        sb.append(y)
    return sb


SBOX = _build_sbox()
INV_SBOX = [0] * 256
for _x, _y in enumerate(SBOX):
    INV_SBOX[_y] = _x
RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def xtime(a: int) -> int:
    a <<= 1
    return (a ^ 0x11B) if a & 0x100 else a


def _gmul(a: int, b: int) -> int:
    return _F.mul(a, b)


# State: list of 16 bytes, column-major as in FIPS-197 (s[r + 4c] = in[r + 4c]).
def sub_bytes(s):
    return [SBOX[v] for v in s]


def inv_sub_bytes(s):
    return [INV_SBOX[v] for v in s]


def shift_rows(s):
    return [s[r + 4 * ((c + r) % 4)] for c in range(4) for r in range(4)]


def inv_shift_rows(s):
    return [s[r + 4 * ((c - r) % 4)] for c in range(4) for r in range(4)]


def _mix_col(col, m):
    return [
        _gmul(m[0], col[0]) ^ _gmul(m[1], col[1]) ^ _gmul(m[2], col[2]) ^ _gmul(m[3], col[3]),
        _gmul(m[3], col[0]) ^ _gmul(m[0], col[1]) ^ _gmul(m[1], col[2]) ^ _gmul(m[2], col[3]),
        _gmul(m[2], col[0]) ^ _gmul(m[3], col[1]) ^ _gmul(m[0], col[2]) ^ _gmul(m[1], col[3]),
        _gmul(m[1], col[0]) ^ _gmul(m[2], col[1]) ^ _gmul(m[3], col[2]) ^ _gmul(m[0], col[3]),
    ]


def mix_columns(s):
    out = []
    for c in range(4):
        out += _mix_col(s[4 * c:4 * c + 4], (2, 3, 1, 1))
    return out


def inv_mix_columns(s):
    out = []
    for c in range(4):
        out += _mix_col(s[4 * c:4 * c + 4], (14, 11, 13, 9))
    return out


def add_round_key(s, k):
    return [a ^ b for a, b in zip(s, k)]


def key_expansion(key: bytes, rounds: int = 10) -> list[list[int]]:
    """AES-128 key schedule -> list of rounds+1 round keys (16 bytes each)."""
    if len(key) != 16:
        raise ValueError("AES-128 key must be 16 bytes")
    w = [list(key[4 * i:4 * i + 4]) for i in range(4)]
    for i in range(4, 4 * (rounds + 1)):
        t = list(w[i - 1])
        if i % 4 == 0:
            t = t[1:] + t[:1]
            t = [SBOX[v] for v in t]
            t[0] ^= RCON[i // 4 - 1]
        w.append([a ^ b for a, b in zip(w[i - 4], t)])
    return [sum(w[4 * r:4 * r + 4], []) for r in range(rounds + 1)]


def encrypt_block(pt: bytes, key: bytes, rounds: int = 10, final_mixcolumns: bool = False) -> bytes:
    if len(pt) != 16:
        raise ValueError("block must be 16 bytes")
    if not 1 <= rounds <= 10:
        raise ValueError("1 <= rounds <= 10")
    rk = key_expansion(key, rounds)
    s = add_round_key(list(pt), rk[0])
    for r in range(1, rounds + 1):
        s = shift_rows(sub_bytes(s))
        if r < rounds or final_mixcolumns:
            s = mix_columns(s)
        s = add_round_key(s, rk[r])
    return bytes(s)


def decrypt_block(ct: bytes, key: bytes, rounds: int = 10, final_mixcolumns: bool = False) -> bytes:
    rk = key_expansion(key, rounds)
    s = list(ct)
    for r in range(rounds, 0, -1):
        s = add_round_key(s, rk[r])
        if r < rounds or final_mixcolumns:
            s = inv_mix_columns(s)
        s = inv_sub_bytes(inv_shift_rows(s))
    return bytes(add_round_key(s, rk[0]))


class AES128:
    """Object wrapper: ``AES128(key, rounds).encrypt(block)``."""

    def __init__(self, key: bytes, rounds: int = 10, final_mixcolumns: bool = False):
        self.key, self.rounds, self.fmc = bytes(key), rounds, final_mixcolumns

    def encrypt(self, block: bytes) -> bytes:
        return encrypt_block(block, self.key, self.rounds, self.fmc)

    def decrypt(self, block: bytes) -> bytes:
        return decrypt_block(block, self.key, self.rounds, self.fmc)


FIPS197_VECTORS = [
    # (key, plaintext, ciphertext) -- FIPS-197 Appendix B and Appendix C.1
    ("2b7e151628aed2a6abf7158809cf4f3c", "3243f6a8885a308d313198a2e0370734", "3925841d02dc09fbdc118597196a0b32"),
    ("000102030405060708090a0b0c0d0e0f", "00112233445566778899aabbccddeeff", "69c4e0d86a7b0430d8cdb78070b4c55a"),
]


def self_test() -> bool:
    for k, p, c in FIPS197_VECTORS:
        k, p, c = bytes.fromhex(k), bytes.fromhex(p), bytes.fromhex(c)
        if encrypt_block(p, k) != c or decrypt_block(c, k) != p:
            return False
    return True


if __name__ == "__main__":
    print("AES-128 FIPS-197 self-test:", "OK" if self_test() else "FAIL")
