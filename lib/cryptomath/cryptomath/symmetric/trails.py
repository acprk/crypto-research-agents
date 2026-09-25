"""Differential / linear trail search for small bit-permutation SPNs.

Three independent tools, deliberately cross-checkable on toy sizes:

1. ``best_trail_bnb``        Matsui-style branch-and-bound (pure Python).
2. ``best_trail_exhaustive`` exact min-plus dynamic programming over all
                              2^B states (numpy; B <= 16 or so).
3. Model exporters: ``spn_active_sbox_cnf`` (DIMACS CNF, optional native XOR
   lines, sequential-counter cardinality) and ``spn_active_sbox_milp`` (CPLEX
   LP format, or matrices for ``scipy.optimize.milp``).

Weights
-------
Differential: w = -log2(DDT[a, b] / 2^n)            (trail prob. 2^-W)
Linear:       w = -log2(|2 LAT[a, b]| / 2^n)        (|trail correlation| 2^-W)
Trails are *characteristics*; the probability of a differential may be larger
(clustering) -- always validate experimentally on the toy cipher.

References
----------
* M. Matsui, "On correlation between the order of S-boxes and the strength of
  DES", EUROCRYPT 1994 (branch-and-bound trail search).
* N. Mouha, Q. Wang, D. Gu, B. Preneel, "Differential and linear
  cryptanalysis using mixed-integer linear programming", Inscrypt 2011.
* S. Sun, L. Hu, P. Wang, K. Qiao, X. Ma, L. Song, "Automatic security
  evaluation and (related-key) differential characteristic search",
  ASIACRYPT 2014 (bit-oriented MILP with S-box constraints).
* C. Sinz, "Towards an optimal CNF encoding of Boolean cardinality
  constraints", CP 2005 (sequential counter).
* M. Soos, K. Nohl, C. Castelluccia, "Extending SAT solvers to cryptographic
  problems", SAT 2009 (native XOR clauses in CryptoMiniSat).
* G. S. Tseitin, "On the complexity of derivation in propositional
  calculus", 1968.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

import numpy as np

from .sbox import ddt, lat

INF = float("inf")


# ---------------------------------------------------------------------------
# weight tables
# ---------------------------------------------------------------------------
def weight_table(sbox, kind: str = "diff") -> np.ndarray:
    """Matrix T[a, b] of transition weights (inf = impossible, T[0,0] = 0)."""
    n = (len(sbox) - 1).bit_length()
    if kind == "diff":
        D = ddt(sbox).astype(float)
        with np.errstate(divide="ignore"):
            T = -np.log2(D / (1 << n))
    elif kind == "linear":
        C = np.abs(2.0 * lat(sbox)) / (1 << n)
        with np.errstate(divide="ignore"):
            T = -np.log2(C)
    else:
        raise ValueError("kind must be 'diff' or 'linear'")
    T[np.isinf(T)] = INF
    T = T + 0.0  # drop -0.0
    return T


def allowed_patterns(sbox, kind: str = "diff") -> set[tuple[int, int]]:
    T = weight_table(sbox, kind)
    return {(a, b) for a in range(T.shape[0]) for b in range(T.shape[1]) if T[a, b] < INF}


def _perm_array(perm: list[int], B: int) -> np.ndarray:
    x = np.arange(1 << B, dtype=np.int64)
    y = np.zeros_like(x)
    for i, p in enumerate(perm):
        y |= ((x >> i) & 1) << p
    return y


def _apply_perm(x: int, perm: list[int]) -> int:
    y = 0
    for i, p in enumerate(perm):
        y |= ((x >> i) & 1) << p
    return y


# ---------------------------------------------------------------------------
# exhaustive DP (ground truth for tiny blocks)
# ---------------------------------------------------------------------------
def best_trail_exhaustive(sbox, perm, rounds: int, kind: str = "diff", table=None) -> list[float]:
    """Exact minimum trail weight for 1..rounds rounds (returns list, index r-1).

    ``table`` overrides the weight table, e.g. ``(T < inf).astype(float)``
    with T[0,0] = 0 gives the minimum number of active S-boxes.
    """
    T = weight_table(sbox, kind) if table is None else np.asarray(table, dtype=float)
    w = (len(sbox) - 1).bit_length()
    B = len(perm)
    nsb = B // w
    if B > 20:
        raise ValueError("exhaustive DP only for tiny blocks (B <= 20)")
    P = _perm_array(perm, B)
    W = np.zeros(1 << B)
    W[0] = INF
    out = []
    for _ in range(rounds):
        A = W.reshape((1 << w,) * nsb)
        for ax in range(nsb):
            A = np.moveaxis(A, ax, -1)
            A = (A[..., :, None] + T).min(axis=-2)
            A = np.moveaxis(A, -1, ax)
        Wy = A.reshape(-1)
        out.append(float(Wy[1:].min()))
        W = np.full(1 << B, INF)
        W[P] = Wy
    return out


def min_active_sboxes_exhaustive(sbox, perm, rounds: int, kind: str = "diff") -> list[int]:
    T = weight_table(sbox, kind)
    A = np.where(T < INF, 1.0, INF)
    A[0, 0] = 0.0
    return [int(v) for v in best_trail_exhaustive(sbox, perm, rounds, kind, table=A)]


# ---------------------------------------------------------------------------
# Matsui branch-and-bound
# ---------------------------------------------------------------------------
@dataclass
class Trail:
    weight: float
    rounds: list = field(default_factory=list)   # [(input, output) of S-layer per round]

    def __repr__(self):
        body = ", ".join(f"({a:#x}->{b:#x})" for a, b in self.rounds)
        return f"Trail(w={self.weight:g}, {body})"


def best_trail_bnb(sbox, perm, rounds: int, kind: str = "diff", step: float = 1.0,
                   max_iterations: int = 10 ** 7) -> tuple[list[float], Trail]:
    """Matsui's algorithm: returns ([B_1, ..., B_R], best R-round trail)."""
    T = weight_table(sbox, kind)
    w = (len(sbox) - 1).bit_length()
    B = len(perm)
    nsb = B // w
    msk = (1 << w) - 1
    trans = {a: sorted(((T[a, b], b) for b in range(1 << w) if T[a, b] < INF))
             for a in range(1, 1 << w)}
    minw = {a: trans[a][0][0] for a in trans}
    minw[0] = 0.0
    wmin = min(minw[a] for a in trans)
    pairs_by_weight = sorted((T[a, b], a, b) for a in range(1, 1 << w) for b in range(1 << w) if T[a, b] < INF)
    Bn = [0.0]
    best_tr = None
    counter = [0]

    for R in range(1, rounds + 1):
        bound = Bn[R - 1] + wmin
        while True:
            best = [INF, None]

            def later_rounds(i, x, acc, path):
                # round i >= 1 with fixed input x
                counter[0] += 1
                if counter[0] > max_iterations:
                    raise RuntimeError("branch-and-bound iteration limit hit")
                nibs = [(x >> (w * j)) & msk for j in range(nsb)]
                act = [j for j in range(nsb) if nibs[j]]
                lb = sum(minw[nibs[j]] for j in act)
                if acc + lb + Bn[R - 1 - i] > min(bound, best[0]):
                    return
                if i == R - 1:
                    y = 0
                    for j in act:
                        y |= trans[nibs[j]][0][1] << (w * j)
                    tot = acc + lb
                    if tot < best[0]:
                        best[0], best[1] = tot, path + [(x, y)]
                    return

                def rec(k, acc2, y, rem):
                    if acc2 + rem + Bn[R - 1 - i] > min(bound, best[0]):
                        return
                    if k == len(act):
                        later_rounds(i + 1, _apply_perm(y, perm), acc2, path + [(x, y)])
                        return
                    j = act[k]
                    a = nibs[j]
                    for wt, b in trans[a]:
                        if acc2 + wt + rem - minw[a] + Bn[R - 1 - i] > min(bound, best[0]):
                            break
                        rec(k + 1, acc2 + wt, y | (b << (w * j)), rem - minw[a])

                rec(0, acc, 0, lb)

            def first_round(j, acc, x, y):
                if acc + Bn[R - 1] > min(bound, best[0]):
                    return
                if j == nsb:
                    if x == 0:
                        return
                    if R == 1:
                        if acc < best[0]:
                            best[0], best[1] = acc, [(x, y)]
                    else:
                        later_rounds(1, _apply_perm(y, perm), acc, [(x, y)])
                    return
                first_round(j + 1, acc, x, y)            # S-box j inactive
                for wt, a, b in pairs_by_weight:
                    if acc + wt + Bn[R - 1] > min(bound, best[0]):
                        break
                    first_round(j + 1, acc + wt, x | (a << (w * j)), y | (b << (w * j)))

            first_round(0, 0.0, 0, 0)
            if best[1] is not None:
                Bn.append(float(best[0]))
                best_tr = Trail(float(best[0]), best[1])
                break
            bound += step
    return Bn[1:], best_tr


# ---------------------------------------------------------------------------
# CNF
# ---------------------------------------------------------------------------
class CNF:
    """Tiny DIMACS CNF builder with XOR support and cardinality encodings."""

    def __init__(self):
        self.nvars = 0
        self.clauses: list[list[int]] = []
        self.xors: list[tuple[list[int], int]] = []   # native XOR (CryptoMiniSat 'x' lines)

    def new_var(self) -> int:
        self.nvars += 1
        return self.nvars

    def new_vars(self, k: int) -> list[int]:
        return [self.new_var() for _ in range(k)]

    def add(self, clause):
        self.clauses.append([int(l) for l in clause])

    # --- XOR ---------------------------------------------------------------
    def add_xor(self, vs, rhs: int = 0, native: bool = False, chunk: int = 4):
        """Constrain XOR(vs) == rhs.

        native=True  -> emit a CryptoMiniSat XOR line.
        native=False -> Tseitin chain: split into pieces of <= ``chunk``
                        variables joined by auxiliary variables, each piece
                        expanded into 2^(k-1) clauses.
        """
        vs = list(vs)
        if native:
            self.xors.append((vs, rhs & 1))
            return
        while len(vs) > chunk:
            t = self.new_var()
            self._xor_direct(vs[:chunk - 1] + [t], 0)   # t = XOR(first chunk-1)
            vs = [t] + vs[chunk - 1:]
        self._xor_direct(vs, rhs & 1)

    def _xor_direct(self, vs, rhs):
        k = len(vs)
        if k == 0:
            if rhs:
                self.add([])
            return
        for m in range(1 << k):
            # forbid assignments whose parity != rhs; assignment bit i = value of vs[i]
            if bin(m).count("1") % 2 != rhs:
                self.add([(-v if (m >> i) & 1 else v) for i, v in enumerate(vs)])

    # --- cardinality -------------------------------------------------------
    def at_most_k(self, xs, k: int):
        """Sinz sequential counter: sum(xs) <= k."""
        xs = list(xs)
        n = len(xs)
        if k >= n:
            return
        if k == 0:
            for x in xs:
                self.add([-x])
            return
        s = [[self.new_var() for _ in range(k)] for _ in range(n - 1)]
        self.add([-xs[0], s[0][0]])
        for j in range(1, k):
            self.add([-s[0][j]])
        for i in range(1, n - 1):
            self.add([-xs[i], s[i][0]])
            self.add([-s[i - 1][0], s[i][0]])
            for j in range(1, k):
                self.add([-xs[i], -s[i - 1][j - 1], s[i][j]])
                self.add([-s[i - 1][j], s[i][j]])
            self.add([-xs[i], -s[i - 1][k - 1]])
        self.add([-xs[n - 1], -s[n - 2][k - 1]])

    def at_least_one(self, xs):
        self.add(list(xs))

    def or_equiv(self, out: int, xs):
        """out <-> OR(xs)."""
        for x in xs:
            self.add([-x, out])
        self.add([-out] + list(xs))

    # --- output / checking -------------------------------------------------
    def to_dimacs(self) -> str:
        lines = [f"p cnf {self.nvars} {len(self.clauses) + len(self.xors)}"]
        lines += [" ".join(map(str, c)) + " 0" for c in self.clauses]
        for vs, rhs in self.xors:
            lits = list(vs)
            if rhs == 0:          # CMS 'x' line means XOR = 1; negate one literal for 0
                lits[0] = -lits[0]
            lines.append("x" + " ".join(map(str, lits)) + " 0")
        return "\n".join(lines) + "\n"

    def write(self, path: str):
        with open(path, "w") as f:
            f.write(self.to_dimacs())

    def evaluate(self, assignment: dict[int, int]) -> bool:
        """Check a (full) assignment {var: 0/1}; used for tests."""
        val = lambda l: assignment.get(abs(l), 0) ^ (l < 0)
        if not all(any(val(l) for l in c) for c in self.clauses):
            return False
        return all(sum(assignment.get(v, 0) for v in vs) % 2 == rhs for vs, rhs in self.xors)


def sbox_pattern_clauses(cnf: CNF, xin, xout, allowed: set[tuple[int, int]]):
    """Forbid every (in, out) bit pattern not in ``allowed`` (one clause each)."""
    w, v = len(xin), len(xout)
    bits = list(xin) + list(xout)
    for a in range(1 << w):
        for b in range(1 << v):
            if (a, b) in allowed:
                continue
            pat = a | (b << w)
            cnf.add([(-x if (pat >> i) & 1 else x) for i, x in enumerate(bits)])


@dataclass
class SPNModelVars:
    x: list          # x[r][i]: S-layer input bit i in round r
    y: list          # y[r][i]: S-layer output bit i
    active: list     # active[r][j]


def spn_active_sbox_cnf(sbox, perm, rounds: int, max_active: int, kind: str = "diff"):
    """CNF satisfiable iff an R-round trail with <= max_active active S-boxes exists."""
    w = (len(sbox) - 1).bit_length()
    B = len(perm)
    nsb = B // w
    allowed = allowed_patterns(sbox, kind)
    cnf = CNF()
    X = [cnf.new_vars(B)]
    Y, Act = [], []
    for r in range(rounds):
        y = cnf.new_vars(B)
        acts = []
        for j in range(nsb):
            xi, yi = X[r][w * j:w * j + w], y[w * j:w * j + w]
            sbox_pattern_clauses(cnf, xi, yi, allowed)
            a = cnf.new_var()
            cnf.or_equiv(a, xi)
            acts.append(a)
        Y.append(y)
        Act.append(acts)
        if r + 1 < rounds:
            nx = [0] * B
            for i, p in enumerate(perm):
                nx[p] = y[i]
            X.append(nx)
    cnf.at_least_one(X[0])
    cnf.at_most_k([a for acts in Act for a in acts], max_active)
    return cnf, SPNModelVars(X, Y, Act)


def trail_to_assignment(model: SPNModelVars, trail: Trail, sbits: int) -> dict[int, int]:
    """Map a trail (from best_trail_bnb) onto CNF variables (aux counter vars not set)."""
    asg = {}
    for r, (a, b) in enumerate(trail.rounds):
        for i, v in enumerate(model.x[r]):
            asg[v] = (a >> i) & 1
        for i, v in enumerate(model.y[r]):
            asg[v] = (b >> i) & 1
        for j, v in enumerate(model.active[r]):
            asg[v] = int(((a >> (sbits * j)) & ((1 << sbits) - 1)) != 0)
    return asg


def run_sat_solver(cnf: CNF, solver: str | None = None, timeout: int = 60):
    """Run an external solver (cryptominisat5/cadical/kissat/minisat) if installed.

    Returns (sat: bool, model: dict | None), or None if no solver is found.
    """
    cands = [solver] if solver else ["cryptominisat5", "cadical", "kissat", "minisat"]
    exe = next((c for c in cands if c and shutil.which(c)), None)
    if exe is None:
        return None
    if cnf.xors and "cryptominisat" not in exe:
        raise ValueError("native XOR lines need cryptominisat5")
    with tempfile.TemporaryDirectory() as d:
        fin, fout = f"{d}/in.cnf", f"{d}/out.txt"
        cnf.write(fin)
        if "minisat" in exe and "crypto" not in exe:
            subprocess.run([exe, fin, fout], capture_output=True, timeout=timeout)
            txt = open(fout).read().split()
            if not txt or txt[0] != "SAT":
                return (False, None)
            lits = [int(t) for t in txt[1:]]
        else:
            res = subprocess.run([exe, fin], capture_output=True, text=True, timeout=timeout)
            out = res.stdout
            if "s UNSATISFIABLE" in out:
                return (False, None)
            lits = [int(t) for line in out.splitlines() if line.startswith("v") for t in line[1:].split()]
    return (True, {abs(l): int(l > 0) for l in lits if l})


# ---------------------------------------------------------------------------
# MILP
# ---------------------------------------------------------------------------
@dataclass
class MILPModel:
    names: list = field(default_factory=list)
    objective: dict = field(default_factory=dict)          # var index -> coeff (minimise)
    rows: list = field(default_factory=list)               # (dict idx->coeff, sense, rhs)

    def var(self, name: str) -> int:
        self.names.append(name)
        return len(self.names) - 1

    def add(self, coeffs: dict, sense: str, rhs: float):
        assert sense in (">=", "<=", "=")
        self.rows.append((dict(coeffs), sense, rhs))

    def to_lp(self) -> str:
        """CPLEX LP format (readable by Gurobi, CPLEX, HiGHS, glpsol --lp)."""
        def expr(d):
            s = []
            for i, c in d.items():
                if c == 0:
                    continue
                sign = "-" if c < 0 else "+"
                mag = abs(c)
                s.append(f"{sign} {'' if mag == 1 else f'{mag:g} '}{self.names[i]}")
            txt = " ".join(s) if s else "0 " + self.names[0]
            return txt[2:] if txt.startswith("+ ") else txt
        out = ["Minimize", " obj: " + expr(self.objective), "Subject To"]
        for k, (d, sense, rhs) in enumerate(self.rows):
            out.append(f" c{k}: {expr(d)} {sense} {rhs:g}")
        out += ["Binary"] + [" " + n for n in self.names] + ["End"]
        return "\n".join(out) + "\n"

    def write(self, path: str):
        with open(path, "w") as f:
            f.write(self.to_lp())

    def to_matrices(self):
        """(c, A, lb, ub) dense arrays for scipy.optimize.milp (all binary)."""
        n = len(self.names)
        c = np.zeros(n)
        for i, v in self.objective.items():
            c[i] = v
        A = np.zeros((len(self.rows), n))
        lb = np.full(len(self.rows), -np.inf)
        ub = np.full(len(self.rows), np.inf)
        for k, (d, sense, rhs) in enumerate(self.rows):
            for i, v in d.items():
                A[k, i] += v
            if sense in (">=", "="):
                lb[k] = rhs
            if sense in ("<=", "="):
                ub[k] = rhs
        return c, A, lb, ub

    def solve_scipy(self):
        """Solve with scipy's HiGHS MILP if scipy is installed; returns (obj, x) or None."""
        try:
            from scipy.optimize import Bounds, LinearConstraint, milp
        except ImportError:
            return None
        c, A, lb, ub = self.to_matrices()
        res = milp(c, constraints=LinearConstraint(A, lb, ub),
                   integrality=np.ones(len(c)), bounds=Bounds(0, 1))
        if res.status != 0:
            return (math.inf, None)
        return (float(round(res.fun)), np.round(res.x).astype(int))


def spn_active_sbox_milp(sbox, perm, rounds: int, kind: str = "diff") -> MILPModel:
    """Minimise #active S-boxes over R rounds (exact via impossible-pattern cuts)."""
    w = (len(sbox) - 1).bit_length()
    B = len(perm)
    nsb = B // w
    allowed = allowed_patterns(sbox, kind)
    bijective = sorted(sbox) == list(range(len(sbox)))
    br = min(bin(a).count("1") + bin(b).count("1") for a, b in allowed if a)
    M = MILPModel()
    X = [[M.var(f"x_0_{i}") for i in range(B)]]
    for r in range(rounds):
        y = [M.var(f"y_{r}_{i}") for i in range(B)]
        for j in range(nsb):
            xi, yi = X[r][w * j:w * j + w], y[w * j:w * j + w]
            a = M.var(f"A_{r}_{j}")
            M.objective[a] = 1.0
            for v in xi:
                M.add({a: 1, v: -1}, ">=", 0)
            M.add({**{v: 1 for v in xi}, a: -1}, ">=", 0)
            if bijective:   # nonzero in <=> nonzero out; also a branch-number cut
                for v in yi:
                    M.add({a: 1, v: -1}, ">=", 0)
                M.add({**{v: 1 for v in yi}, a: -1}, ">=", 0)
                M.add({**{v: 1 for v in xi + yi}, a: -br}, ">=", 0)
            bits = xi + yi
            for pa in range(1 << w):
                for pb in range(1 << w):
                    if (pa, pb) in allowed:
                        continue
                    pat = pa | (pb << w)
                    d, ones = {}, 0
                    for i, v in enumerate(bits):
                        if (pat >> i) & 1:
                            d[v] = d.get(v, 0) - 1
                            ones += 1
                        else:
                            d[v] = d.get(v, 0) + 1
                    M.add(d, ">=", 1 - ones)
        if r + 1 < rounds:
            nx = [0] * B
            for i, p in enumerate(perm):
                nx[p] = y[i]
            X.append(nx)
    M.add({v: 1 for v in X[0]}, ">=", 1)
    return M
