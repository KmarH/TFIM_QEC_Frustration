"""Stim-based verification of stabilizer error-detection codes (SCOPE §6).

These checks confirm a code's defining algebra and its single-qubit-error
detection property WITHOUT assuming the construction is correct — they are the
independent numerical confirmation the reviewer asks for on QEC claims.

For a [[n, k, d]] stabilizer code we verify:
  1. All stabilizer generators mutually commute (a valid stabilizer group).
  2. Each logical operator commutes with every stabilizer (logicals preserve the
     code space).
  3. The symplectic pairing of logicals: Xbar_i anticommutes with Zbar_i and
     commutes with Zbar_j (j != i) and with all other logicals of the same type.
  4. Distance-2 detection: every weight-1 Pauli error (X, Y, Z on each qubit)
     anticommutes with at least one stabilizer, i.e. is DETECTED. This is the
     operational meaning of distance >= 2.

Commutation uses stim.PauliString.commutes. All functions are pure algebra on
Pauli strings; no circuit execution, no hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import stim


@dataclass
class VerificationReport:
    name: str
    stabilizers_commute: bool
    logicals_commute_with_stabilizers: bool
    logical_symplectic_ok: bool
    all_weight1_detected: bool
    undetected_weight1: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return (
            self.stabilizers_commute
            and self.logicals_commute_with_stabilizers
            and self.logical_symplectic_ok
            and self.all_weight1_detected
        )

    def summary(self) -> str:
        status = "PASS" if self.ok else "FAIL"
        lines = [
            f"[{status}] {self.name}",
            f"    stabilizers mutually commute      : {self.stabilizers_commute}",
            f"    logicals commute w/ stabilizers   : {self.logicals_commute_with_stabilizers}",
            f"    logical symplectic algebra ok     : {self.logical_symplectic_ok}",
            f"    all weight-1 errors detected      : {self.all_weight1_detected}",
        ]
        if self.undetected_weight1:
            lines.append(f"    UNDETECTED weight-1 errors        : {self.undetected_weight1}")
        return "\n".join(lines)


def _weight1_errors(n: int) -> List[stim.PauliString]:
    """All single-qubit X, Y, Z errors on an n-qubit register."""
    errs: List[stim.PauliString] = []
    for q in range(n):
        for pauli in ("X", "Y", "Z"):
            p = stim.PauliString(n)
            p[q] = pauli
            errs.append(p)
    return errs


def verify_code(
    name: str,
    n: int,
    stabilizers: List[stim.PauliString],
    logical_x: List[stim.PauliString],
    logical_z: List[stim.PauliString],
) -> VerificationReport:
    """Run checks 1–4 above on a stabilizer code. Returns a VerificationReport."""
    # 1. Stabilizers mutually commute.
    stab_commute = all(
        stabilizers[a].commutes(stabilizers[b])
        for a in range(len(stabilizers))
        for b in range(a + 1, len(stabilizers))
    )

    # 2. Each logical commutes with every stabilizer.
    log_stab = all(
        L.commutes(S) for S in stabilizers for L in (logical_x + logical_z)
    )

    # 3. Symplectic pairing: Xbar_i anticommutes Zbar_i; commutes with Zbar_j (i!=j);
    #    like-type logicals commute. This is the algebra of independent logical
    #    qubits: each conjugate pair (Xbar_i, Zbar_i) behaves like a single qubit's
    #    X/Z, and distinct logical qubits are mutually independent (all commute).
    sympl = True
    k = len(logical_x)
    for i in range(k):
        for j in range(k):
            want_anticommute = i == j
            commutes = logical_x[i].commutes(logical_z[j])
            # Physics: Xbar_i and Zbar_i MUST anticommute (same qubit). So on the
            # diagonal (i==j) seeing `commutes == True` is a failure, and
            # off-diagonal (i!=j) seeing `commutes == False` is a failure — both
            # captured by `commutes == want_anticommute`.
            if commutes == want_anticommute:  # expected anticommute when i==j
                sympl = False
    for i in range(k):
        for j in range(i + 1, k):
            if not logical_x[i].commutes(logical_x[j]):
                sympl = False
            if not logical_z[i].commutes(logical_z[j]):
                sympl = False

    # 4. Distance-2 detection: every weight-1 error anticommutes with some stabilizer.
    #    NOTE (scope): this confirms detection distance >= 2 only (no weight-1 error
    #    is undetected). It does not by itself establish the full code distance,
    #    since an undetected error could in principle be a stabilizer element rather
    #    than a logical; for the Iceberg code the stabilizers are weight-n (>=4) so
    #    this cannot happen here. See concatenated.py / review M2 for why the
    #    stronger "anticommutes with a logical" test matters for higher-distance codes.
    undetected: List[str] = []
    for err in _weight1_errors(n):
        detected = any(not err.commutes(S) for S in stabilizers)
        if not detected:
            undetected.append(str(err))
    all_detected = len(undetected) == 0

    return VerificationReport(
        name=name,
        stabilizers_commute=stab_commute,
        logicals_commute_with_stabilizers=log_stab,
        logical_symplectic_ok=sympl,
        all_weight1_detected=all_detected,
        undetected_weight1=undetected,
    )
