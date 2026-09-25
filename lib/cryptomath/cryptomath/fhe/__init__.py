# TOY: not secure
"""TOY fully homomorphic encryption schemes, noise models and bootstrapping
building blocks.  Insecure parameters, no side-channel care -- for learning,
for checking noise formulas and for screening algorithmic ideas only.

Module map
----------
rlwe       shared Ciphertext, base-w decomposition, key switching
bgv        BGV: keygen/enc/dec, add, mul, relin, modswitch, Galois, slots
bfv        BFV: scale-invariant variant, invariant noise budget
ckks       CKKS: canonical embedding encoder, rescale, rotations, error tracking
tfhe       TFHE: LWE/GLWE/GGSW, gadget decomposition, external product, CMux,
           blind rotation, sample extract, key switch, programmable bootstrapping
noise      analytic variance formulas for all of the above
polyeval   Horner, Paterson-Stockmeyer, BSGS (power & Chebyshev basis) + counts
bootstrap  Chebyshev mod-reduction approximations, BSGS linear transforms,
           CoeffToSlot cost, BGV digit-extraction cost
"""
from .rlwe import Ciphertext  # noqa: F401
from .bgv import BGV  # noqa: F401
from .bfv import BFV  # noqa: F401
from .ckks import CKKS, CKKSEncoder  # noqa: F401
from .tfhe import TFHE, TFHEParams  # noqa: F401
from . import noise, polyeval, bootstrap  # noqa: F401
