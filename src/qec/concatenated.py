"""Concatenated Iceberg code (target d=4) + distance probes (SCOPE §6, handoff/01).

Construction [derived; correctness argument in docs/concatenated_iceberg_d4.md]:
inner Iceberg [[k_i+2, k_i, 2]] blocks j = 0..n_o-1 (n_o = k_o+2), outer Iceberg
[[k_o+2, k_o, 2]] blocks a = 0..k_i-1. Outer qubit j of outer block a is stored as
inner logical qubit a of inner block j. Every inner block therefore feeds each
outer block exactly ONCE, so an undetected inner logical error lands on at most one
qubit per outer block (detected there) — this interleaving is what lets the
distance multiply, 2 x 2 = 4. Intuition: a logical fault must defeat BOTH levels;
the inner code already kills every weight-1 error, so to go undetected an error
must first forge an inner logical (weight >= d_inner = 2) and then, through the
one-qubit-per-outer-block interleaving, forge an outer logical as well (another
factor d_outer = 2), hence d = d_inner * d_outer = 4. (Same multi-block
interleaving pattern as Knill's C4/C6 concatenation: E. Knill, "Quantum computing
with realistically noisy devices", Nature 434, 39-44 (2005),
doi:10.1038/nature03350 — Fig. 1 "Block structure of C4/C6 concatenated codes".)

Physical index of inner-block-j local qubit q: j * n_i + q  (n_i = k_i + 2), with
the IcebergCode local layout (data 0..k_i-1, top k_i, bottom k_i+1).
Logical index of outer block a, outer logical i: a * k_o + i.

Distance probes:
  - `min_undetected_weight` (original, review/02 M2 caveat): first weight at which
    some error commutes with all stabilizers — counts stabilizer elements too.
  - `code_distance`: first weight at which some error commutes with all
    stabilizers AND anticommutes with some logical (a genuine undetected logical
    error). This is the M2-safe measurement used for the d=4 claim.
"""

from __future__ import annotations

from itertools import combinations
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
import stim

from src.qec.iceberg import IcebergCode


def min_undetected_weight(
    n: int,
    stabilizers: List[stim.PauliString],
    max_weight: int = 3,
) -> Optional[int]:
    """Smallest weight of a Pauli error that commutes with ALL stabilizers.

    Returns the detection distance proxy: the least w (1 <= w <= max_weight) for
    which some weight-w Pauli error is undetected (commutes with every
    stabilizer), or None if all errors up to max_weight are detected. A code with
    detection distance d detects every error of weight < d, so the first
    undetected weight equals d.

    REVIEWER NOTE (do-not-fix, flagged — review/02-stage2.md M2): "undetected"
    here means "commutes with all stabilizers", which includes trivial errors that
    are themselves stabilizer-group elements, not just logical operators. The claim
    "first undetected weight == d" therefore holds only when the minimum stabilizer
    weight exceeds d. It is correct for every Stage-2 code (Iceberg stabilizers are
    weight-n >= 4; all 5-qubit/Steane weight-3 commuting errors are genuine
    logicals, verified in review), but for the concatenated d=4 code the generators
    may have weight <= 4, so a low-weight stabilizer element could be miscounted as
    an undetected error and understate the true code distance. The fix for the
    concatenated check (require anticommutation with a logical) belongs to the
    Claude Code deliverable's verification, not to this probe.
    """
    paulis = ("X", "Y", "Z")
    for w in range(1, max_weight + 1):
        for qubits in combinations(range(n), w):
            # enumerate all Pauli assignments on these w qubits
            for assignment in _pauli_assignments(w, paulis):
                err = stim.PauliString(n)
                for q, p in zip(qubits, assignment):
                    err[q] = p
                if all(err.commutes(S) for S in stabilizers):
                    return w  # undetected error of this weight exists
    return None


def _pauli_assignments(w: int, paulis) -> List[Tuple[str, ...]]:
    if w == 0:
        return [()]
    smaller = _pauli_assignments(w - 1, paulis)
    out: List[Tuple[str, ...]] = []
    for s in smaller:
        for p in paulis:
            out.append(s + (p,))
    return out


def iceberg_detection_distance(k: int, max_weight: int = 3) -> int:
    """Measured detection distance of the single-level Iceberg [[k+2,k,2]].

    Expected to be 2 (detects all weight-1, misses some weight-2 logical errors).
    """
    code = IcebergCode(k)
    stabs = code.stabilizers()
    w = min_undetected_weight(code.n, stabs, max_weight=max_weight)
    return w if w is not None else max_weight + 1


# --------------------------------------------------------------------------- #
# M2-safe code distance (vectorised symplectic enumeration)
# --------------------------------------------------------------------------- #
def _symplectic(ops: Sequence[stim.PauliString], n: int) -> np.ndarray:
    """Rows [x | z] (uint8, shape (len(ops), 2n)) for a list of Pauli strings."""
    out = np.zeros((len(ops), 2 * n), dtype=np.uint8)
    for r, P in enumerate(ops):
        x, z = P.to_numpy()
        out[r, :n] = x
        out[r, n:] = z
    return out


def _errors_of_weight(n: int, w: int) -> np.ndarray:
    """All weight-w Paulis as symplectic rows [x | z], shape (C(n,w)*3^w, 2n)."""
    supports = np.array(list(combinations(range(n), w)), dtype=np.int64)
    # Pauli labels 0=X,1=Y,2=Z -> (x,z) bits (1,0),(1,1),(0,1)
    labels = np.array(np.meshgrid(*[np.arange(3)] * w, indexing="ij")).reshape(w, -1).T
    xb = (labels <= 1).astype(np.uint8)
    zb = (labels >= 1).astype(np.uint8)
    S, A = len(supports), len(labels)
    rows = np.zeros((S * A, 2 * n), dtype=np.uint8)
    idx = np.repeat(np.arange(S * A), w)
    cols = np.repeat(supports, A, axis=0).reshape(-1)
    rows[idx, cols] = np.tile(xb, (S, 1)).reshape(-1)
    rows[idx, cols + n] = np.tile(zb, (S, 1)).reshape(-1)
    return rows


def _anticommutes(errs: np.ndarray, ops: np.ndarray, n: int) -> np.ndarray:
    """Boolean (n_errs, n_ops): symplectic product <e, o> = x_e.z_o + z_e.x_o mod 2."""
    ex, ez = errs[:, :n].astype(np.int32), errs[:, n:].astype(np.int32)
    ox, oz = ops[:, :n].astype(np.int32), ops[:, n:].astype(np.int32)
    return ((ex @ oz.T + ez @ ox.T) & 1).astype(bool)


def code_distance(
    n: int,
    stabilizers: List[stim.PauliString],
    logicals: List[stim.PauliString],
    max_weight: int = 4,
) -> Tuple[Optional[int], Optional[stim.PauliString]]:
    """Measured code distance and a minimum-weight witness (review/02 M2 fix).

    Returns (d, witness): the least weight d <= max_weight of a Pauli that
    commutes with every stabilizer AND anticommutes with at least one logical
    (i.e. an undetected, non-trivial logical error), or (None, None) if none exists
    up to max_weight. `logicals` must contain a full basis (all Xbar and Zbar), so
    "commutes with all of them" is equivalent to "is in the stabilizer group".

    This is a property of the CODE alone (the noiseless Pauli-group picture): the
    smallest weight of a bare data error that is both invisible to the detectors
    and logically nontrivial. It is distinct from the circuit `fault_distance` in
    concatenated_gadget.py, which counts physical FAULT LOCATIONS in the noisy
    syndrome-extraction circuit (a single faulty gate can inject a multi-qubit
    error, so one fault can exceed weight 1); the flag qubits are what keep the
    circuit's fault distance from collapsing below this code distance.
    """
    S = _symplectic(stabilizers, n)
    L = _symplectic(logicals, n)
    for w in range(1, max_weight + 1):
        E = _errors_of_weight(n, w)
        undetected = ~_anticommutes(E, S, n).any(axis=1)
        if not undetected.any():
            continue
        E = E[undetected]
        logical = _anticommutes(E, L, n).any(axis=1)
        if logical.any():
            row = E[np.argmax(logical)]
            wit = stim.PauliString.from_numpy(
                xs=row[:n].astype(bool), zs=row[n:].astype(bool)
            )
            return w, wit
    return None, None


# --------------------------------------------------------------------------- #
# Concatenated Iceberg code
# --------------------------------------------------------------------------- #
@dataclass
class ConcatenatedIceberg:
    """Inner Iceberg(k_inner) blocks carrying k_inner outer Iceberg(k_outer) blocks.

    [[n, k, 4]] with n = (k_outer+2)(k_inner+2), k = k_inner * k_outer.
    All stabilizers and logicals are pure-X or pure-Z (CSS), so they are also
    exposed as qubit-support lists (in a deliberate measurement ORDER, see
    `outer_support`) for the syndrome gadget in concatenated_gadget.py.

    CSS consequence used downstream: X-type and Z-type errors are detected by
    disjoint stabilizer sets, so a Z-basis memory experiment probes exactly the
    bit-flip (X) logical failures and an X-basis experiment the phase-flip (Z)
    logical failures. Running one of each therefore covers BOTH logical failure
    channels; neither basis alone certifies the code.
    """

    k_inner: int = 2
    k_outer: int = 2

    def __post_init__(self) -> None:
        self.inner = IcebergCode(self.k_inner)  # validates even k
        self.outer = IcebergCode(self.k_outer)

    # --- geometry ---
    @property
    def n_inner(self) -> int:
        return self.inner.n

    @property
    def n_outer(self) -> int:
        return self.outer.n

    @property
    def n(self) -> int:
        return self.n_outer * self.n_inner

    @property
    def k(self) -> int:
        return self.k_inner * self.k_outer

    def phys(self, block: int, q: int) -> int:
        """Physical index of local qubit q of inner block `block`."""
        return block * self.n_inner + q

    def _lift(self, pauli: str, a: int, j: int) -> List[int]:
        """Support of inner logical pauli_a on inner block j (= outer qubit j of outer block a).

        Inner Xbar_a = X_t X_a, Zbar_a = Z_b Z_a; the shared t (or b) is listed
        FIRST so `outer_support` can schedule all t/b qubits before the slot qubits.
        """
        anchor = self.inner.top if pauli == "X" else self.inner.bottom
        return [self.phys(j, anchor), self.phys(j, a)]

    # --- supports (CSS) ---
    def inner_support(self, j: int) -> List[int]:
        """Inner S_X / S_Z of block j: all n_i qubits of the block."""
        return [self.phys(j, q) for q in range(self.n_inner)]

    def outer_support(self, pauli: str, a: int) -> List[int]:
        """Outer S_pauli of outer block a lifted to physical qubits, INTERLEAVED order.

        Lift = product over inner blocks j of inner logical pauli_a on block j
        (weight 2 * n_o). Order: anchor (t or b) of every block first, then slot a
        of every block. Any proper prefix then has weight <= 1 inside every inner
        block except at most one block, so an unflagged hook error is still caught
        by the inner stabilizers (belt-and-braces alongside the flag qubit).
        """
        lifted = [self._lift(pauli, a, j) for j in range(self.n_outer)]
        return [s[0] for s in lifted] + [s[1] for s in lifted]

    def logical_support(self, pauli: str, a: int, i: int) -> List[int]:
        """Logical pauli on outer block a, outer logical i (weight 4).

        Outer Xbar_i = X_{t_o} X_i -> inner Xbar_a on inner blocks t_o and i;
        outer Zbar_i = Z_{b_o} Z_i -> inner Zbar_a on inner blocks b_o and i.
        """
        anchor = self.outer.top if pauli == "X" else self.outer.bottom
        return self._lift(pauli, a, anchor) + self._lift(pauli, a, i)

    # --- stim.PauliString views (for verify_code / code_distance) ---
    def _ps(self, pauli: str, support: List[int]) -> stim.PauliString:
        p = stim.PauliString(self.n)
        for q in support:
            p[q] = pauli
        return p

    def x_stabilizer_supports(self) -> List[List[int]]:
        return [self.inner_support(j) for j in range(self.n_outer)] + [
            self.outer_support("X", a) for a in range(self.k_inner)
        ]

    def z_stabilizer_supports(self) -> List[List[int]]:
        return [self.inner_support(j) for j in range(self.n_outer)] + [
            self.outer_support("Z", a) for a in range(self.k_inner)
        ]

    def stabilizers(self) -> List[stim.PauliString]:
        """2*n_o inner generators followed by 2*k_i lifted outer generators."""
        return [self._ps("X", s) for s in self.x_stabilizer_supports()] + [
            self._ps("Z", s) for s in self.z_stabilizer_supports()
        ]

    def logical_x(self) -> List[stim.PauliString]:
        return [
            self._ps("X", self.logical_support("X", a, i))
            for a in range(self.k_inner)
            for i in range(self.k_outer)
        ]

    def logical_z(self) -> List[stim.PauliString]:
        return [
            self._ps("Z", self.logical_support("Z", a, i))
            for a in range(self.k_inner)
            for i in range(self.k_outer)
        ]
