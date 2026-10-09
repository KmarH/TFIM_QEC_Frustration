"""On-paper QEC codes: 5-qubit [[5,1,3]] and Steane [[7,1,3]] (SCOPE §6).

These are the "on-paper path": Stim-level stabilizer definitions plus a written
feasibility analysis (docs/qec_feasibility.md), NOT full lattice simulations. Both
are standard, textbook stabilizer codes with universally agreed generators, so the
definitions are [established] and checkable; the verifier confirms the stabilizer
group and that these are distance-3 (correct 1 / detect 2) codes.

Distance 3 means the minimum weight of a nontrivial logical operator is 3: the code
CORRECTS any single-qubit error (3 = 2*t+1 with t=1) or, used purely for detection,
DETECTS any error of weight <= 2. This is strictly stronger than the Iceberg d=2
detect-only code and is why the on-paper codes are the correcting-code reference
points for the Stage-2 comparison.

Perfect 5-qubit code [[5,1,3]] stabilizers (standard cyclic form):
    XZZXI, IXZZX, XIXZZ, ZXIXZ
Steane [[7,1,3]] code (CSS, from the classical [7,4,3] Hamming code):
    X-type: IIIXXXX, IXXIIXX, XIXIXIX
    Z-type: IIIZZZZ, IZZIIZZ, ZIZIZIZ
Note: the full-weight logicals below (XXXXX/ZZZZZ, XXXXXXX/ZZZZZZZ) are one valid
representative of each logical coset; lower-weight equivalents exist up to
multiplication by stabilizers, but all representatives have weight >= d = 3.
"""

from __future__ import annotations

from typing import List

import stim


def _ps(s: str) -> stim.PauliString:
    """Build a stim.PauliString from a string like 'XZZXI'."""
    return stim.PauliString(s)


def five_qubit_stabilizers() -> List[stim.PauliString]:
    """Four generators of the perfect [[5,1,3]] code (cyclic XZZXI family)."""
    return [_ps("XZZXI"), _ps("IXZZX"), _ps("XIXZZ"), _ps("ZXIXZ")]


def five_qubit_logicals():
    """Logical X and Z of the [[5,1,3]] code: both weight-5 (XXXXX, ZZZZZ)."""
    return [_ps("XXXXX")], [_ps("ZZZZZ")]


def steane_stabilizers() -> List[stim.PauliString]:
    """Six generators of the Steane [[7,1,3]] CSS code (Hamming-based)."""
    return [
        _ps("IIIXXXX"),
        _ps("IXXIIXX"),
        _ps("XIXIXIX"),
        _ps("IIIZZZZ"),
        _ps("IZZIIZZ"),
        _ps("ZIZIZIZ"),
    ]


def steane_logicals():
    """Logical X and Z of Steane: transversal weight-7 (XXXXXXX, ZZZZZZZ)."""
    return [_ps("XXXXXXX")], [_ps("ZZZZZZZ")]
