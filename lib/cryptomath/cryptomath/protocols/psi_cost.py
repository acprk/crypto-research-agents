"""Approximate communication / computation formulas for PSI protocols.

These are *screening* formulas (leading terms only) meant for comparing
design options before implementing anything.  Constants (code width, OKVS
expansion, cuckoo parameters, stash) change between papers and versions:
set them explicitly and re-derive from the paper you compare against.
Before quoting numbers in a paper, measure the real implementation.

References
----------
* V. Kolesnikov, R. Kumaresan, M. Rosulek, N. Trieu, "Efficient batched
  oblivious PRF with applications to private set intersection", CCS 2016
  (KKRT; BaRK-OPRF, pseudorandom code width w ~ 424-448 bits).
* B. Pinkas, T. Schneider, M. Zohner, "Scalable private set intersection
  based on OT extension", ACM TOPS 2018 (cuckoo hashing analysis for PSI).
* B. Pinkas, T. Schneider, O. Tkachenko, A. Yanai, "Efficient circuit-based
  PSI with linear communication", EUROCRYPT 2019 (OPPRF-based circuit-PSI).
* P. Rindal, P. Schoppmann, "VOLE-PSI: fast OPRF and circuit-PSI from
  vector-OLE", EUROCRYPT 2021.
* P. Rindal, S. Raghuraman, "Blazing fast PSI from improved OKVS and
  subfield VOLE", CCS 2022.
* C. Meadows, IEEE S&P 1986; Huberman–Franklin–Hogg, EC 1999 (DH-PSI).
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass


@dataclass
class PSICost:
    protocol: str
    comm_bits: float
    comm_rounds: int
    public_key_ops: float
    symmetric_ops: float
    notes: str = ""

    @property
    def comm_MiB(self) -> float:
        return self.comm_bits / 8 / 2 ** 20

    def as_dict(self) -> dict:
        d = asdict(self)
        d["comm_MiB"] = self.comm_MiB
        return d


def psi_output_len(n_x: int, n_y: int, stat: int = 40) -> int:
    """Tag length ell = stat + log2(n_x n_y) bits (false-positive prob <= 2^-stat)."""
    return stat + math.ceil(math.log2(max(2, n_x * n_y)))


def naive_hash_psi(n_x: int, n_y: int, stat: int = 40) -> PSICost:
    """Insecure baseline: server sends truncated hashes of its set."""
    ell = psi_output_len(n_x, n_y, stat)
    return PSICost("naive-hash (insecure)", n_y * ell, 1, 0, n_x + n_y)


def dh_psi_cost(n_c: int, n_s: int, group_bits: int = 256, stat: int = 40) -> PSICost:
    """Semi-honest DH-PSI: client sends n_c blinded elements, server returns
    n_c re-exponentiated elements plus n_s tags of ell bits.  Exps: 2n_c (client) + n_c + n_s (server).
    """
    ell = psi_output_len(n_c, n_s, stat)
    return PSICost("DH-PSI", 2 * n_c * group_bits + n_s * ell, 2, 3 * n_c + n_s, n_c + n_s)


def kkrt_cost(n_r: int, n_s: int, code_width: int = 448, hashes: int = 3,
              bin_factor: float = 1.2, stash: int = 0, stat: int = 40, kappa: int = 128) -> PSICost:
    """KKRT16 (semi-honest): cuckoo-hash receiver set into m = bin_factor * n_r bins,
    one BaRK-OPRF instance per bin (m x code_width bit OT-extension matrix),
    sender sends (hashes + stash) * n_s tags of ell bits.
    """
    m = math.ceil(bin_factor * n_r) + stash
    ell = psi_output_len(n_r, n_s, stat)
    comm = m * code_width + (hashes + stash) * n_s * ell + kappa * 2 * code_width  # + base OTs
    sym = m * 2 + (hashes + stash) * n_s
    return PSICost("KKRT16", comm, 3, code_width, sym,
                   f"m={m} bins, ell={ell}, base OTs counted as 2*kappa*w bits")


def vole_psi_cost(n_r: int, n_s: int, okvs_expansion: float = 1.3, field_bits: int = 128,
                  vole_comm_bits: float | None = None, stat: int = 40) -> PSICost:
    """VOLE-based PSI (RS21 / RR22 style): receiver sends an OKVS of
    okvs_expansion * n_r field elements; sender sends n_s tags of ell bits;
    plus the (silent) VOLE generation, sublinear in n (pass measured bits, or a
    placeholder of 2^17 bits per 2^20 VOLEs scaled -- a rough guess, label it so).
    """
    m = math.ceil(okvs_expansion * n_r)
    ell = psi_output_len(n_r, n_s, stat)
    if vole_comm_bits is None:
        vole_comm_bits = 2 ** 17 * max(1.0, m / 2 ** 20)   # placeholder, NOT from a paper
    comm = m * field_bits + n_s * ell + vole_comm_bits
    return PSICost("VOLE-PSI", comm, 2, 0, m + n_s + n_r,
                   f"OKVS size m={m}; silent-VOLE term is a placeholder unless supplied")


def circuit_psi_cost(n_r: int, n_s: int, item_bits: int | None = None, bin_factor: float = 1.27,
                     comm_per_and_bits: float = 256, oppf_bits_per_bin: float = 448,
                     stat: int = 40) -> PSICost:
    """Circuit-PSI (PSTY19-style): OPPRF per bin + one sigma-bit equality circuit per bin.

    sigma = stat + log2(m) bit comparisons -> (sigma - 1) AND gates per bin.
    comm_per_and_bits: 2*kappa for half-gates garbling, ~2 ROTs for GMW, etc.
    """
    m = math.ceil(bin_factor * n_r)
    sigma = item_bits if item_bits is not None else stat + math.ceil(math.log2(max(2, m)))
    ands = m * (sigma - 1)
    comm = m * oppf_bits_per_bin + 3 * n_s * sigma + ands * comm_per_and_bits
    return PSICost("circuit-PSI", comm, 4, 0, m + 3 * n_s,
                   f"m={m} bins, sigma={sigma}, AND gates={ands} (output stays secret-shared)")


def compare_psi(n: int, **kw) -> list[dict]:
    """Balanced-set comparison table (n = |X| = |Y|)."""
    rows = [naive_hash_psi(n, n), dh_psi_cost(n, n), kkrt_cost(n, n), vole_psi_cost(n, n),
            circuit_psi_cost(n, n)]
    return [r.as_dict() for r in rows]
