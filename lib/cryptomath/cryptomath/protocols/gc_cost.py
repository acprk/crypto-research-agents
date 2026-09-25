"""Garbled-circuit size / cost counter.

Count gates of a Boolean circuit (Bristol-fashion text or a gate list) and
convert to garbled-table size under different garbling schemes.

Bits per gate (kappa = label length):

=====================  ==========  ============
scheme                 AND gate    XOR gate
=====================  ==========  ============
classical (Yao)        4 kappa     4 kappa
point-and-permute      4 kappa     4 kappa
GRR3                   3 kappa     3 kappa
free-XOR + GRR3        3 kappa     0
half-gates             2 kappa     0
three-halves           1.5 kappa + 5   0
=====================  ==========  ============

References
----------
* A. C. Yao, "How to generate and exchange secrets", FOCS 1986.
* D. Beaver, S. Micali, P. Rogaway, "The round complexity of secure
  protocols", STOC 1990 (point-and-permute).
* M. Naor, B. Pinkas, R. Sumner, "Privacy preserving auctions and mechanism
  design", EC 1999 (GRR3 row reduction).
* V. Kolesnikov, T. Schneider, "Improved garbled circuit: free XOR gates and
  applications", ICALP 2008.
* S. Zahur, M. Rosulek, D. Evans, "Two halves make a whole: reducing data
  transfer in garbled circuits using half gates", EUROCRYPT 2015.
* M. Rosulek, L. Roy, "Three halves make a whole? Beating the half-gates
  lower bound for garbled circuits", CRYPTO 2021.
* "Bristol Fashion" MPC circuits, N. Smart et al. (circuit file format).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

SCHEMES = {
    "classical": (4.0, 4.0, 0),
    "point-and-permute": (4.0, 4.0, 0),
    "grr3": (3.0, 3.0, 0),
    "free-xor-grr3": (3.0, 0.0, 0),
    "half-gates": (2.0, 0.0, 0),
    "three-halves": (1.5, 0.0, 5),
}


@dataclass
class GateCount:
    AND: int = 0
    XOR: int = 0
    INV: int = 0
    OTHER: int = 0
    and_depth: int = 0
    inputs: int = 0
    outputs: int = 0

    def garbled_bits(self, scheme: str = "half-gates", kappa: int = 128) -> float:
        a, x, extra = SCHEMES[scheme]
        nonfree = self.OTHER  # OR/NAND etc. cost as AND
        return (self.AND + nonfree) * (a * kappa + extra) + self.XOR * x * kappa

    def garbled_MiB(self, scheme: str = "half-gates", kappa: int = 128) -> float:
        return self.garbled_bits(scheme, kappa) / 8 / 2 ** 20

    def total_comm_bits(self, scheme: str = "half-gates", kappa: int = 128,
                        evaluator_inputs: int | None = None, ot_bits_per_input: float | None = None) -> float:
        """Garbled tables + garbler input labels + OT for evaluator inputs (IKNP ~ kappa + 2 kappa)."""
        ev = self.inputs // 2 if evaluator_inputs is None else evaluator_inputs
        ot = 3 * kappa if ot_bits_per_input is None else ot_bits_per_input
        return self.garbled_bits(scheme, kappa) + (self.inputs - ev) * kappa + ev * ot + self.outputs


def parse_bristol(text: str) -> GateCount:
    """Count gates (and AND-depth) of a Bristol-fashion circuit."""
    lines = [l.split() for l in text.strip().splitlines() if l.strip()]
    ngates, nwires = int(lines[0][0]), int(lines[0][1])
    ins = [int(v) for v in lines[1]]
    outs = [int(v) for v in lines[2]]
    n_in = sum(ins[1:]) if len(ins) > 1 else 0
    n_out = sum(outs[1:]) if len(outs) > 1 else 0
    depth = [0] * nwires
    gc = GateCount(inputs=n_in, outputs=n_out)
    for g in lines[3:3 + ngates]:
        nin, nout = int(g[0]), int(g[1])
        wi = [int(w) for w in g[2:2 + nin]]
        wo = [int(w) for w in g[2 + nin:2 + nin + nout]]
        op = g[-1].upper()
        d = max((depth[w] for w in wi), default=0)
        if op == "AND":
            gc.AND += 1
            d += 1
        elif op == "XOR":
            gc.XOR += 1
        elif op in ("INV", "NOT", "EQW", "EQ", "MAND"):
            if op == "MAND":
                gc.AND += nout
                d += 1
            else:
                gc.INV += 1
        else:
            gc.OTHER += 1
            d += 1
        for w in wo:
            depth[w] = d
    gc.and_depth = max(depth) if depth else 0
    return gc


def count_gates(gates) -> GateCount:
    """Count a list of (op, ...) tuples, e.g. [('AND', a, b, c), ('XOR', ...)]."""
    c = Counter(g[0].upper() for g in gates)
    return GateCount(AND=c["AND"], XOR=c["XOR"], INV=c["INV"] + c["NOT"],
                     OTHER=sum(v for k, v in c.items() if k not in ("AND", "XOR", "INV", "NOT")))


# Standard gate counts of common building blocks (free-XOR friendly designs).
def adder_cost(n: int) -> GateCount:
    """n-bit ripple-carry adder: n - 1 ANDs (carry-out dropped), ~4n XORs."""
    return GateCount(AND=n - 1, XOR=4 * n, and_depth=n - 1, inputs=2 * n, outputs=n)


def comparator_cost(n: int) -> GateCount:
    """x > y on n bits: n ANDs (Kolesnikov–Sadeghi–Schneider 2009 style), depth n."""
    return GateCount(AND=n, XOR=3 * n, and_depth=n, inputs=2 * n, outputs=1)


def equality_cost(n: int) -> GateCount:
    """x == y on n bits: n XNORs + (n - 1)-AND tree, depth ceil(log2 n)."""
    import math
    return GateCount(AND=n - 1, XOR=n, INV=n, and_depth=math.ceil(math.log2(max(n, 1))),
                     inputs=2 * n, outputs=1)


def multiplier_cost(n: int) -> GateCount:
    """School-book n x n -> n-bit (truncated) multiplier: ~n^2 - n ANDs."""
    return GateCount(AND=n * n - n, XOR=2 * n * n, and_depth=2 * n, inputs=2 * n, outputs=n)


def hamming_threshold_cost(n: int, t: int) -> GateCount:
    """HD(x, y) <= t: n XORs, popcount (~n ANDs via full-adder tree), compare on log n bits."""
    import math
    L = max(1, math.ceil(math.log2(n + 1)))
    return GateCount(AND=n + L, XOR=3 * n + 3 * L, and_depth=L + L, inputs=2 * n, outputs=1)
