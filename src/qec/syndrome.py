"""Stim circuit-level syndrome extraction for the Iceberg code (SCOPE §6).

Builds explicit stabilizer-measurement circuits and uses Stim DETECTOR
annotations to confirm the code's operational behavior under injected Pauli
errors — the circuit-level counterpart to the pure-algebra checks in verify.py.

Stabilizer measurement here uses the standard ancilla scheme:
  - To measure S_Z = Z_0 Z_1 ... Z_{n-1}: prepare an ancilla in |0>, apply
    CX(data_q -> ancilla) for every data qubit, then measure the ancilla in Z.
    The ancilla records the parity of the Z-eigenvalues, i.e. the S_Z syndrome.
  - To measure S_X = X_0 ... X_{n-1}: prepare an ancilla in |+> (H), apply
    CX(ancilla -> data_q) for every data qubit, then H and measure. The ancilla
    records the S_X syndrome.

Why two rounds: resetting all qubits to |0> gives a +1 eigenstate of S_Z but NOT
of S_X, so a single S_X measurement is random even with no error. We therefore
measure each stabilizer in TWO consecutive rounds and place each DETECTOR on the
PARITY of the two rounds. On a clean run the second round reproduces the first
(the state is stabilized after the first measurement), so each detector is
deterministically 0; a single-qubit error inserted between the rounds flips the
affected stabilizer parity and fires its detector. This is the standard
difference-of-rounds detector construction and is what makes the clean run silent.

A fired DETECTOR means the stabilizer was violated — the error was detected and
the shot would be discarded (post-selection). This is error DETECTION, not
correction (distance 2). No hardware; stabilizer sim only.

Qubit indices: data 0..n-1 are the code qubits (IcebergCode layout); ancillas use
indices n (for S_Z) and n+1 (for S_X). No hardware; stabilizer sim only.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import stim

from src.qec.iceberg import IcebergCode


def _measure_sz(c: stim.Circuit, n: int, anc: int) -> None:
    """Append an S_Z = Z_0...Z_{n-1} measurement using ancilla `anc`."""
    c.append("R", [anc])
    for q in range(n):
        c.append("CX", [q, anc])
    c.append("M", [anc])


def _measure_sx(c: stim.Circuit, n: int, anc: int) -> None:
    """Append an S_X = X_0...X_{n-1} measurement using ancilla `anc`."""
    c.append("R", [anc])
    c.append("H", [anc])
    for q in range(n):
        c.append("CX", [anc, q])
    c.append("H", [anc])
    c.append("M", [anc])


def syndrome_circuit(
    code: IcebergCode,
    errors: Optional[List[Tuple[str, int]]] = None,
) -> stim.Circuit:
    """Build a two-round S_Z/S_X syndrome-extraction circuit for `code`.

    `errors` is an optional list of (pauli, qubit) single-qubit errors inserted
    on the data qubits BETWEEN the two syndrome rounds, e.g. [("X", 0)]. Two
    DETECTORs are emitted, one per stabilizer, each on the PARITY of that
    stabilizer's two rounds. On a clean run both detectors are deterministically
    0; a weight-1 error flips the parity of the stabilizer(s) it anticommutes
    with, firing the corresponding detector.

    Measurement record order per round is [S_Z, S_X]. With two rounds the four
    records are, most-recent-last: round1 S_Z (-4), round1 S_X (-3),
    round2 S_Z (-2), round2 S_X (-1).
    """
    n = code.n
    anc_z = n       # ancilla for S_Z
    anc_x = n + 1   # ancilla for S_X
    c = stim.Circuit()

    # Reset data qubits to |0...0>. This is a +1 eigenstate of S_Z (every Z_q|0>=+|0>)
    # but NOT of S_X (X flips |0>), so the first S_X measurement outcome is random.
    # The two-round / parity-detector scheme below makes that initial randomness
    # cancel so the clean run is deterministically silent.
    for q in range(n):
        c.append("R", [q])

    # Round 1: project onto the stabilizer eigenspaces.
    _measure_sz(c, n, anc_z)
    _measure_sx(c, n, anc_x)

    # Inject the requested single-qubit error(s) between the rounds. These are
    # inserted as probability-1 Pauli error CHANNELS (X_ERROR/Y_ERROR/Z_ERROR),
    # not deterministic gates: Stim's detector sampler measures detectors relative
    # to the error-free frame, so a deterministic gate would be absorbed into that
    # frame and never fire a detector. A certain error channel is the correct way
    # to model "an error occurred here" for detection.
    if errors:
        _ERR = {"X": "X_ERROR", "Y": "Y_ERROR", "Z": "Z_ERROR"}
        for (pauli, q) in errors:
            if pauli not in _ERR:
                raise ValueError(f"bad error Pauli {pauli!r}")
            if not (0 <= q < n):
                raise ValueError(f"error qubit {q} out of data range [0,{n})")
            c.append(_ERR[pauli], [q], 1.0)

    # Round 2: re-measure the stabilizers.
    _measure_sz(c, n, anc_z)
    _measure_sx(c, n, anc_x)

    # DETECTORs on the parity of each stabilizer across the two rounds.
    #   S_Z: records -4 (round1) and -2 (round2)
    #   S_X: records -3 (round1) and -1 (round2)
    c.append("DETECTOR", [stim.target_rec(-4), stim.target_rec(-2)])  # S_Z parity
    c.append("DETECTOR", [stim.target_rec(-3), stim.target_rec(-1)])  # S_X parity
    return c


def detects_error(code: IcebergCode, pauli: str, qubit: int, shots: int = 64) -> bool:
    """Return True iff a single `pauli` error on `qubit` trips a detector.

    Physical meaning: a tripped detector is a violated stabilizer parity, i.e. the
    error landed outside the code space and the shot is DISCARDED (post-selection).
    For a distance-2 code every weight-1 error must trip a detector; a weight-1
    error that stayed silent would be an undetectable fault and break detection.

    Deterministic for a single Pauli error (no stochastic noise), so a small shot
    count suffices; we sample a few to confirm reproducibility.
    """
    circ = syndrome_circuit(code, errors=[(pauli, qubit)])
    sampler = circ.compile_detector_sampler()
    dets = sampler.sample(shots=shots)
    # dets shape (shots, 2); error is detected if any detector fires on all shots.
    return bool(dets.any(axis=1).all())


def clean_run_is_silent(code: IcebergCode, shots: int = 64) -> bool:
    """Return True iff an error-free syndrome extraction fires no detector."""
    circ = syndrome_circuit(code, errors=None)
    dets = circ.compile_detector_sampler().sample(shots=shots)
    return bool((~dets.any(axis=1)).all())
