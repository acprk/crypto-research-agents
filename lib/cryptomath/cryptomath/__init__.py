"""cryptomath -- toy-scale cryptography mathematics for research screening.

Subpackages are imported lazily (PEP 562 ``__getattr__``), so a missing or
broken optional subpackage never breaks ``import cryptomath``::

    import cryptomath
    cryptomath.algebra.cyclotomic_poly(12)
    cryptomath.available()          # -> {'algebra': True, 'ec': False, ...}

Subpackages
-----------
algebra    finite fields, cyclotomics, Galois group of Q(zeta_m), slots, NTT,
           Z_{p^e} helpers (Hensel, digit extraction, null polynomials), characters
lattice    LWE/RLWE/MLWE/NTRU toy samplers, error distributions, security
           estimation (core-SVP, primal uSVP, dual), GSA/BKZ simulator, toy LLL
fhe        TOY BGV / BFV / CKKS / TFHE, noise estimators, bootstrapping blocks
costmodel  abstract operation counting and symbolic cost formulas
symmetric  S-box / Boolean-function analysis, toy ciphers (separate owner)
protocols  secret sharing, OT, PSI cost models (separate owner)
ec         small prime-field elliptic curves (separate owner)

Everything here is for experimentation and teaching. Nothing is constant-time
and all FHE / lattice code is insecure by construction.
"""
from __future__ import annotations

import importlib

__version__ = "0.1.0"

SUBPACKAGES = ("algebra", "lattice", "fhe", "costmodel", "symmetric", "protocols", "ec")

__all__ = list(SUBPACKAGES) + ["available", "__version__"]


def __getattr__(name: str):
    if name in SUBPACKAGES:
        mod = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def available() -> dict:
    """Return ``{subpackage: importable?}`` without raising."""
    out = {}
    for name in SUBPACKAGES:
        try:
            importlib.import_module(f"{__name__}.{name}")
            out[name] = True
        except Exception:  # pragma: no cover - depends on install state
            out[name] = False
    return out


def __dir__():
    return sorted(set(globals()) | set(SUBPACKAGES))
