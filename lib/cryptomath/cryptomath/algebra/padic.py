"""Z_{p^e} helpers: Hensel lifting, digits, polynomial functions, null
polynomials, digit-extraction / lowest-digit-retain polynomials.

Key facts implemented and checked by the tests:

* **Polynomial functions mod n.**  Every polynomial function Z/n -> Z/n has a
  unique representation  f(x) = sum_{k < mu(n)} a_k x^(k)  (falling factorial
  x^(k) = x(x-1)...(x-k+1)) with 0 <= a_k < n / gcd(n, k!), where mu(n) is the
  Kempner number (least k with n | k!).  ``x^(mu(n))`` is a monic null
  polynomial of minimal degree.  Hence #functions = prod_k n/gcd(n, k!).
  (A. J. Kempner, "Polynomials and their residue systems", Trans. AMS 22,
  1921; D. Singmaster, "On polynomial functions (mod m)", J. Number Theory 6,
  1974.)
* **Lifting polynomial** (Halevi--Shoup): for prime p and e >= 1 there is F of
  degree p with F(z0 + p^{e'} z1) = z0 (mod p^{e'+1}) for all digits
  z0 in [0, p), 1 <= e' <= e.  Construction: F = X^p + p G with G the
  interpolant of (z - z^p)/p on {0..p-1} mod p^e.  (S. Halevi, V. Shoup,
  "Bootstrapping for HElib", EUROCRYPT 2015, ePrint 2014/873; also
  Gentry--Halevi--Smart, ePrint 2012/099, for p = 2.)
* **Digit extraction** (HS15 procedure) with depth / evaluation counts.
* **Lowest-digit-retain polynomial**: a polynomial over Z_{p^e} mapping
  x -> (x mod p) (balanced or non-negative digit) as a function on Z_{p^e};
  computed as the minimal-degree canonical representative.  (H. Chen,
  K. Han, "Homomorphic lower digits removal and improved FHE bootstrapping",
  EUROCRYPT 2018, ePrint 2018/067, bound deg <= (e-1)(p-1)+1.)
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .poly import poly_add, poly_derivative, poly_eval, poly_mul, poly_trim

__all__ = [
    "vp", "digits", "from_digits", "hensel_lift_root", "kempner", "falling_factorial_poly",
    "newton_coeffs", "is_polynomial_function", "canonical_poly_function",
    "poly_function_degree", "count_polynomial_functions", "null_poly_min",
    "is_null_poly", "hs_lift_poly", "hs_digit_extract", "hs_digit_extraction_counts",
    "lowest_digit_retain_poly", "chen_han_degree_bound", "interpolate_mod",
]


def vp(n: int, p: int) -> int:
    """p-adic valuation (vp(0) = infinity represented as a large int)."""
    if n == 0:
        return 10 ** 9
    v = 0
    while n % p == 0:
        n //= p
        v += 1
    return v


def digits(z: int, p: int, e: int, balanced: bool = False) -> List[int]:
    """Base-p digits of z mod p^e, lowest first (balanced digits if requested)."""
    z %= p ** e
    out = []
    for _ in range(e):
        d = z % p
        if balanced and d > p // 2:
            d -= p
        out.append(d)
        z = (z - d) // p
    return out


def from_digits(ds: Sequence[int], p: int) -> int:
    return sum(d * p ** i for i, d in enumerate(ds))


def hensel_lift_root(f: Sequence[int], r: int, p: int, e: int) -> int:
    """Lift a simple root r of f mod p (f'(r) != 0 mod p) to a root mod p^e (Newton)."""
    df = poly_derivative(list(f))
    if poly_eval(df, r, p) % p == 0:
        raise ValueError("root is not simple mod p")
    mod = p
    while mod < p ** e:
        mod = min(mod * mod, p ** e)
        r = (r - poly_eval(f, r, mod) * pow(poly_eval(df, r, mod), -1, mod)) % mod
    return r


def kempner(n: int) -> int:
    """Kempner number mu(n): the least k with n | k!."""
    k, f = 1, 1
    while f % n:
        k += 1
        f *= k
    return k if n > 1 else 1


def falling_factorial_poly(k: int) -> List[int]:
    """Coefficients of x(x-1)...(x-k+1)."""
    out = [1]
    for i in range(k):
        out = poly_mul(out, [-i, 1])
    return out


def interpolate_mod(xs: Sequence[int], ys: Sequence[int], n: int) -> List[int]:
    """Lagrange interpolation mod n (pairwise differences of xs must be units)."""
    res: List[int] = []
    for i, (xi, yi) in enumerate(zip(xs, ys)):
        num, den = [1], 1
        for j, xj in enumerate(xs):
            if j != i:
                num = poly_mul(num, [-xj, 1], n)
                den = den * (xi - xj) % n
        res = poly_add(res, poly_mul(num, [yi * pow(den, -1, n) % n], n), n)
    return res


def newton_coeffs(values: Sequence[int]) -> List[int]:
    """Forward differences Delta^k f(0) from f(0), f(1), ... (exact ints)."""
    d = list(values)
    out = []
    while d:
        out.append(d[0])
        d = [d[i + 1] - d[i] for i in range(len(d) - 1)]
    return out


def canonical_poly_function(func: Callable[[int], int], n: int) -> Optional[List[int]]:
    """Minimal-degree polynomial (coefficients mod n) representing ``func`` on Z/n.

    Returns None if ``func`` is not a polynomial function mod n.  The result
    is the canonical form sum a_k x^(k) with a_k reduced mod n/gcd(n, k!),
    which has the least possible degree.
    """
    mu = kempner(n)
    vals = [func(x) % n for x in range(mu)]
    d = newton_coeffs(vals)
    poly: List[int] = []
    fact = 1
    for k in range(mu):
        if k:
            fact *= k
        g = math.gcd(n, fact)
        if d[k] % g:
            return None
        nk = n // g
        a_k = (d[k] // g) * pow(fact // g, -1, nk) % nk if nk > 1 else 0
        if a_k:
            poly = poly_add(poly, [a_k * c for c in falling_factorial_poly(k)], n)
    # verify on all residues
    for x in range(n):
        if poly_eval(poly, x, n) != func(x) % n:
            return None
    return poly_trim(poly, n)


def is_polynomial_function(func: Callable[[int], int], n: int) -> bool:
    return canonical_poly_function(func, n) is not None


def poly_function_degree(func: Callable[[int], int], n: int) -> Optional[int]:
    P = canonical_poly_function(func, n)
    return None if P is None else len(P) - 1


def count_polynomial_functions(n: int) -> int:
    """Number of distinct polynomial functions Z/n -> Z/n (Kempner / Singmaster)."""
    total, fact = 1, 1
    for k in range(kempner(n)):
        if k:
            fact *= k
        total *= n // math.gcd(n, fact)
    return total


def null_poly_min(n: int) -> List[int]:
    """Monic null polynomial mod n of minimal degree: x(x-1)...(x-mu(n)+1)."""
    return [c % n for c in falling_factorial_poly(kempner(n))]


def is_null_poly(f: Sequence[int], n: int) -> bool:
    return all(poly_eval(f, x, n) == 0 for x in range(n))


# --------------------------------------------------------------------------
# Halevi--Shoup lifting polynomial and digit extraction
# --------------------------------------------------------------------------

def hs_lift_poly(p: int, e: int) -> List[int]:
    """Degree-p lifting polynomial F mod p^{e+1} (see module docstring).

    Property: for digit z0 in [0,p) and 1 <= e' <= e,
    F(z0 + p^{e'} z1) = z0 (mod p^{e'+1}).  For p = 2 this is F = X^2.
    """
    mod = p ** e
    G = interpolate_mod(list(range(p)), [((z - z ** p) // p) % mod for z in range(p)], mod)
    F = [p * c for c in G] + [0] * max(0, p + 1 - len(G))
    F = F + [0] * (p + 1 - len(F))
    F[p] += 1
    return poly_trim(F, p ** (e + 1))


def hs_digit_extract(z: int, p: int, e: int, r: int) -> Dict[str, object]:
    """Simulate HS15 digit removal on a plaintext integer.

    Input z mod p^e.  Computes the r lowest base-p digits (as integers mod the
    needed powers) using only additions, the lifting polynomial F, and exact
    division by p (which in BGV is a free plaintext-modulus switch), then
    returns floor-division result  (z - lowest r digits) / p^r  mod p^{e-r}.

    Returns a dict with ``result``, ``digits`` (w_{i,e-1-i} mod p^{e-i}),
    ``F_evals`` (number of lifting-polynomial evaluations) and ``depth``
    (multiplicative depth assuming depth(F) = ceil(log2 p)).
    """
    if not 1 <= r < e:
        raise ValueError("need 1 <= r < e")
    F = hs_lift_poly(p, e)
    dF = max(1, math.ceil(math.log2(p)))
    mod = p ** e
    z %= mod
    w: Dict[Tuple[int, int], int] = {}
    depth: Dict[Tuple[int, int], int] = {}
    evals = 0
    for k in range(r):
        # z_k = (z - sum_{i<k} p^i w_{i,k-i}) / p^k
        acc = z
        dk = 0
        for i in range(k):
            acc -= p ** i * w[(i, k - i)]
            dk = max(dk, depth[(i, k - i)])
        assert acc % p ** k == 0
        w[(k, 0)] = (acc // p ** k) % p ** (e - k)
        depth[(k, 0)] = dk
        for j in range(e - 1 - k):
            w[(k, j + 1)] = poly_eval(F, w[(k, j)], p ** (e - k))
            depth[(k, j + 1)] = depth[(k, j)] + dF
            evals += 1
    acc = z
    dres = 0
    for i in range(r):
        acc -= p ** i * w[(i, e - 1 - i)]
        dres = max(dres, depth[(i, e - 1 - i)])
    assert acc % p ** r == 0
    return {
        "result": (acc // p ** r) % p ** (e - r),
        "digits": [w[(i, e - 1 - i)] % p ** (e - i) for i in range(r)],
        "F_evals": evals,
        "depth": dres,
    }


def hs_digit_extraction_counts(p: int, e: int, r: int) -> Dict[str, int]:
    """Closed-form counts for :func:`hs_digit_extract`.

    F evaluations = sum_{k<r} (e-1-k);  depth = (e-1) * ceil(log2 p).
    Each F evaluation of degree p costs about sqrt(2p) + log2 p nonscalar
    multiplications with Paterson--Stockmeyer (see fhe.polyeval).
    """
    dF = max(1, math.ceil(math.log2(p)))
    return {"F_evals": sum(e - 1 - k for k in range(r)), "depth": (e - 1) * dF}


def lowest_digit_retain_poly(p: int, e: int, balanced: bool = True) -> List[int]:
    """Minimal-degree polynomial over Z_{p^e} with G(x) = (lowest digit of x) mod p^e.

    For odd p the balanced digit in [-(p-1)/2, (p-1)/2] is used by default.
    Raises ValueError if the map is not a polynomial function (it always is
    for these cases; the check guards the implementation).
    """
    n = p ** e

    def lowest(x):
        d = x % p
        if balanced and p > 2 and d > p // 2:
            d -= p
        return d

    P = canonical_poly_function(lowest, n)
    if P is None:
        raise ValueError("lowest-digit map is not a polynomial function mod p^e")
    return P


def chen_han_degree_bound(p: int, e: int) -> int:
    """Degree bound (e-1)(p-1)+1 for the lowest-digit-retain polynomial (CH18)."""
    return (e - 1) * (p - 1) + 1
