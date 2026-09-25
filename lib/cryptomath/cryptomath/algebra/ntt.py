"""Number-theoretic transforms (readable reference implementations).

* :func:`ntt_cyclic` / :func:`intt_cyclic` -- radix-2 iterative Cooley--Tukey
  DFT over Z_q of power-of-two length n (needs n | q-1).
* :func:`ntt_negacyclic` / :func:`intt_negacyclic` -- evaluation of
  a in Z_q[X]/(X^n+1) at the odd powers psi^{2i+1} of a primitive 2n-th root
  psi (twist + cyclic NTT).  Needs 2n | q-1.
* :func:`dft_bluestein` -- DFT of *arbitrary* length n via Bluestein's chirp-z
  trick (convolution done by a power-of-two NTT if available, else schoolbook).
* :class:`CyclotomicNTT` -- CRT map Z_q[X]/Phi_m -> Z_q^{phi(m)} for arbitrary
  m with q = 1 mod m: evaluation at zeta^i, i in (Z/m)^*, and its inverse.
* :func:`negacyclic_mul_ntt` -- fast product in Z_q[X]/(X^n+1).

All functions work on Python-int lists (exact for any q size).

References
----------
* J. W. Cooley, J. W. Tukey, Math. Comp. 19, 1965.
* L. I. Bluestein, "A linear filtering approach to the computation of the
  discrete Fourier transform", IEEE Trans. Audio Electroacoust. 18, 1970.
* P. Longa, M. Naehrig, "Speeding up the Number Theoretic Transform for
  Faster Ideal Lattice-Based Cryptography", CANS 2016, ePrint 2016/504.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List, Sequence

from .ntheory import euler_phi, root_of_unity, units
from .poly import is_power_of_two

__all__ = ["bit_reverse", "ntt_cyclic", "intt_cyclic", "ntt_negacyclic",
           "intt_negacyclic", "negacyclic_mul_ntt", "dft_naive", "dft_bluestein",
           "CyclotomicNTT", "solve_mod"]


def bit_reverse(a: Sequence[int]) -> List[int]:
    n = len(a)
    bits = n.bit_length() - 1
    return [a[int(format(i, f"0{bits}b")[::-1], 2)] if bits else a[i] for i in range(n)]


def ntt_cyclic(a: Sequence[int], q: int, omega: int | None = None) -> List[int]:
    """A_k = sum_j a_j omega^{jk} mod q, n = len(a) a power of two."""
    n = len(a)
    if not is_power_of_two(n):
        raise ValueError("length must be a power of two (use dft_bluestein)")
    if omega is None:
        omega = root_of_unity(n, q)
    A = bit_reverse([x % q for x in a])
    length = 2
    while length <= n:
        w_len = pow(omega, n // length, q)
        for start in range(0, n, length):
            w = 1
            half = length // 2
            for j in range(half):
                u = A[start + j]
                v = A[start + j + half] * w % q
                A[start + j] = (u + v) % q
                A[start + j + half] = (u - v) % q
                w = w * w_len % q
        length <<= 1
    return A


def intt_cyclic(A: Sequence[int], q: int, omega: int | None = None) -> List[int]:
    n = len(A)
    if omega is None:
        omega = root_of_unity(n, q)
    a = ntt_cyclic(A, q, pow(omega, -1, q))
    ninv = pow(n, -1, q)
    return [x * ninv % q for x in a]


def ntt_negacyclic(a: Sequence[int], q: int, psi: int | None = None) -> List[int]:
    """Values a(psi^{2i+1}), i = 0..n-1, with psi a primitive 2n-th root mod q."""
    n = len(a)
    if psi is None:
        psi = root_of_unity(2 * n, q)
    tw = [a[i] * pow(psi, i, q) % q for i in range(n)]
    return ntt_cyclic(tw, q, psi * psi % q)


def intt_negacyclic(A: Sequence[int], q: int, psi: int | None = None) -> List[int]:
    n = len(A)
    if psi is None:
        psi = root_of_unity(2 * n, q)
    tw = intt_cyclic(A, q, psi * psi % q)
    pinv = pow(psi, -1, q)
    return [tw[i] * pow(pinv, i, q) % q for i in range(n)]


def negacyclic_mul_ntt(a: Sequence[int], b: Sequence[int], q: int) -> List[int]:
    """a*b in Z_q[X]/(X^n+1) via NTT (q prime, 2n | q-1)."""
    n = len(a)
    psi = root_of_unity(2 * n, q)
    A = ntt_negacyclic(a, q, psi)
    B = ntt_negacyclic(b, q, psi)
    return intt_negacyclic([x * y % q for x, y in zip(A, B)], q, psi)


def dft_naive(a: Sequence[int], q: int, omega: int) -> List[int]:
    n = len(a)
    return [sum(a[j] * pow(omega, j * k, q) for j in range(n)) % q for k in range(n)]


def _convolve(x: List[int], y: List[int], q: int) -> List[int]:
    """Linear convolution mod q; radix-2 NTT when q admits it, else schoolbook."""
    L = len(x) + len(y) - 1
    N = 1
    while N < L:
        N <<= 1
    if (q - 1) % N == 0:
        try:
            w = root_of_unity(N, q)
            X = ntt_cyclic(x + [0] * (N - len(x)), q, w)
            Y = ntt_cyclic(y + [0] * (N - len(y)), q, w)
            return intt_cyclic([u * v % q for u, v in zip(X, Y)], q, w)[:L]
        except ValueError:
            pass
    out = [0] * L
    for i, u in enumerate(x):
        for j, v in enumerate(y):
            out[i + j] += u * v
    return [c % q for c in out]


def dft_bluestein(a: Sequence[int], q: int, omega: int, psi: int | None = None) -> List[int]:
    """Length-n DFT for arbitrary n via Bluestein.

    Needs psi with psi^2 = omega and psi of order 2n (i.e. 2n | q-1) so that
    omega^{jk} = psi^{k^2} psi^{j^2} psi^{-(k-j)^2}.
    """
    n = len(a)
    if psi is None:
        psi = root_of_unity(2 * n, q)
        # align psi with the requested omega: choose the square root of omega
        for t in range(2 * n):
            cand = pow(psi, t, q)
            if cand * cand % q == omega % q:
                psi = cand
                break
        else:
            raise ValueError("omega has no square root among 2n-th roots")
    chirp = [pow(psi, k * k, q) for k in range(n)]
    ichirp = [pow(c, -1, q) for c in chirp]
    x = [a[j] * chirp[j] % q for j in range(n)]
    # y_t = psi^{-t^2} for t in -(n-1)..(n-1)
    y = [ichirp[abs(t)] for t in range(-(n - 1), n)]
    conv = _convolve(x, y, q)
    return [chirp[k] * conv[k + n - 1] % q for k in range(n)]


def solve_mod(A: List[List[int]], b: List[int], q: int) -> List[int]:
    """Solve A x = b over F_q (q prime) by Gaussian elimination."""
    n = len(A)
    M = [list(row) + [bb] for row, bb in zip(A, b)]
    for col in range(n):
        piv = next(r for r in range(col, n) if M[r][col] % q)
        M[col], M[piv] = M[piv], M[col]
        inv = pow(M[col][col], -1, q)
        M[col] = [x * inv % q for x in M[col]]
        for r in range(n):
            if r != col and M[r][col] % q:
                f = M[r][col]
                M[r] = [(x - f * y) % q for x, y in zip(M[r], M[col])]
    return [M[r][n] for r in range(n)]


def _inverse_matrix(A: List[List[int]], q: int) -> List[List[int]]:
    n = len(A)
    M = [list(row) + [1 if i == j else 0 for j in range(n)] for i, row in enumerate(A)]
    for col in range(n):
        piv = next(r for r in range(col, n) if M[r][col] % q)
        M[col], M[piv] = M[piv], M[col]
        inv = pow(M[col][col], -1, q)
        M[col] = [x * inv % q for x in M[col]]
        for r in range(n):
            if r != col and M[r][col] % q:
                f = M[r][col]
                M[r] = [(x - f * y) % q for x, y in zip(M[r], M[col])]
    return [row[n:] for row in M]


class CyclotomicNTT:
    """CRT isomorphism Z_q[X]/Phi_m ~= Z_q^{phi(m)} for q prime, q = 1 mod m.

    forward(a)[i] = a(zeta^{u_i}) where u_0 < u_1 < ... are the units mod m.
    Forward uses a length-m DFT (radix-2 if m is a power of two, else
    Bluestein); inverse uses a cached inverse Vandermonde matrix (O(phi^2)
    per call, O(phi^3) once) -- fine for toy sizes.
    """

    def __init__(self, m: int, q: int):
        if (q - 1) % m:
            raise ValueError("need q = 1 mod m")
        self.m, self.q = m, q
        self.n = euler_phi(m)
        self.units = units(m)
        self.zeta = root_of_unity(m, q)
        self._psi = None
        if not is_power_of_two(m) and (q - 1) % (2 * m) == 0:
            psi = root_of_unity(2 * m, q)
            for t in range(2 * m):
                c = pow(psi, t, q)
                if c * c % q == self.zeta:
                    self._psi = c
                    break

    def forward(self, a: Sequence[int]) -> List[int]:
        q, m = self.q, self.m
        full = list(a) + [0] * (m - len(a))
        if is_power_of_two(m):
            vals = ntt_cyclic(full, q, self.zeta)
        elif self._psi is not None:
            vals = dft_bluestein(full, q, self.zeta, self._psi)
        else:
            vals = dft_naive(full, q, self.zeta)
        return [vals[u] for u in self.units]

    @property
    def _vinv(self):
        return _vandermonde_inverse(self.m, self.q, self.zeta)

    def inverse(self, vals: Sequence[int]) -> List[int]:
        V = self._vinv
        q = self.q
        return [sum(r * v for r, v in zip(row, vals)) % q for row in V]


@lru_cache(maxsize=16)
def _vandermonde_inverse(m: int, q: int, zeta: int):
    us = units(m)
    n = len(us)
    V = [[pow(zeta, u * j, q) for j in range(n)] for u in us]
    return _inverse_matrix(V, q)
