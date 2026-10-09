"""Iceberg [[k+2, k, 2]] quantum error-detection code (arXiv:2211.06703).

Physics (research/02-stage2-iceberg.md): k (even) logical qubits are encoded into
n = k + 2 physical qubits. Physical layout: numbered data qubits 0..k-1, plus a
top qubit `t` and a bottom qubit `b`. The code has exactly two stabilizers and
distance 2, so it DETECTS any single-qubit error but cannot correct — a flagged
syndrome means the shot is discarded (post-selection).

Qubit index convention used here (0-based, concrete for Stim):
    data qubits : 0, 1, ..., k-1
    top    (t)  : index k
    bottom (b)  : index k + 1
so the full register has n = k + 2 qubits with indices 0..k+1.

Stabilizers (arXiv:2211.06703v2, Fig. 1a):
    S_X = X on all n qubits
    S_Z = Z on all n qubits
S_X and S_Z commute because they overlap on all n qubits and n = k + 2 is even
(k even): each qubit contributes one anticommuting X/Z pair, and an even number
of such pairs commutes overall. This parity is exactly why the code requires
even k. Measuring S_X enforces even X-parity and S_Z even Z-parity over the whole
block, so ANY single-qubit X or Z flips one parity and is detected (distance 2).

Logical operators (i = 0..k-1), Fig. 1a:
    Xbar_i = X_t X_i   -> X on {k, i}
    Zbar_i = Z_b Z_i   -> Z on {k+1, i}
Each logical has even support on the block, so it commutes with both stabilizers
(stays in the code space). The shared top/bottom qubits give the correct
symplectic algebra: Xbar_i and Zbar_i overlap only on data qubit i (t != b), so
they anticommute (a conjugate logical pair), while Xbar_i and Zbar_j (i != j)
share no qubit and commute (independent logical qubits). The weight-2 operator
X_i X_j = Xbar_i · Xbar_j is a genuine logical of weight 2, confirming d = 2 is
exact: distance 2 DETECTS any single-qubit error but cannot CORRECT, so a flagged
syndrome means the shot is discarded (post-selection), not repaired.

This module provides the code's Pauli data as stim.PauliString objects and a
verifier that checks the defining algebra and the distance-2 detection property.
Nothing here touches hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import stim


@dataclass
class IcebergCode:
    """The Iceberg [[k+2, k, 2]] code for an even number k of logical qubits."""

    k: int

    def __post_init__(self) -> None:
        # Even k (=> even n) is required: S_X and S_Z overlap on all n qubits, so
        # they commute only when n is even. Odd k would make the two stabilizers
        # anticommute and the code ill-defined.
        if self.k < 2 or self.k % 2 != 0:
            raise ValueError(
                f"Iceberg code requires an even k >= 2 (got k={self.k}); "
                "n=k+2 physical qubits, k logical."
            )

    # --- register geometry ---
    @property
    def n(self) -> int:
        """Number of physical qubits, n = k + 2."""
        return self.k + 2

    @property
    def top(self) -> int:
        """Index of the top qubit t."""
        return self.k

    @property
    def bottom(self) -> int:
        """Index of the bottom qubit b."""
        return self.k + 1

    # --- stabilizers ---
    def stabilizers(self) -> List[stim.PauliString]:
        """[S_X, S_Z] = [X on all n qubits, Z on all n qubits]."""
        sx = stim.PauliString(self.n)
        sz = stim.PauliString(self.n)
        for q in range(self.n):
            sx[q] = "X"
            sz[q] = "Z"
        return [sx, sz]

    # --- logical operators ---
    def logical_x(self, i: int) -> stim.PauliString:
        """Xbar_i = X_t X_i (X on the top qubit and numbered data qubit i)."""
        self._check_logical_index(i)
        p = stim.PauliString(self.n)
        p[self.top] = "X"
        p[i] = "X"
        return p

    def logical_z(self, i: int) -> stim.PauliString:
        """Zbar_i = Z_b Z_i (Z on the bottom qubit and numbered data qubit i)."""
        self._check_logical_index(i)
        p = stim.PauliString(self.n)
        p[self.bottom] = "Z"
        p[i] = "Z"
        return p

    def _check_logical_index(self, i: int) -> None:
        if not (0 <= i < self.k):
            raise ValueError(f"logical index {i} out of range [0, {self.k})")
