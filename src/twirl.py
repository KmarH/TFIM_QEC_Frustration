"""Randomized compiling (Pauli twirling) of pytket circuits (DECISIONS.md OPEN-3, D-RC).

This is a HARDWARE-READINESS module, not a physics change. Twirling conjugates each entangling
gate with a random Pauli so a device's real (partly coherent) error channel is converted into a
stochastic Pauli channel. This project's noise models (src/backends_qc.Noise,
src/encoded_tfim.StimNoise) are ALREADY Pauli channels, so twirling is EXACTLY a no-op for every
existing prediction in this repo [derived] -- see tests/test_twirl.py's no-op test, which is the
property this module exists to make available for later H2 use, not a new result.

Convention [established, pytket]: ZZPhase(alpha) = exp(-i*pi*alpha/2 * Z#Z) (half-turns); XXPhase
analogously for X#X. A single-qubit Pauli P in {I,X,Y,Z} commutes with Z iff P in {I,Z}, and with
X iff P in {I,X}. A two-qubit Pauli pair P = P1#P2 commutes with the generator G#G (G in {X,Z})
iff BOTH or NEITHER of P1, P2 anticommutes with G individually; otherwise it anticommutes
[established, Pauli algebra]. Conjugating R(alpha) = exp(-i*pi*alpha/2 * G#G) by such a pair P
gives, EXACTLY: P R(alpha) P^-1 = R(alpha) if P commutes with G#G, R(-alpha) if it anticommutes
[derived; this is the only identity used below].

Implementation (the "Pauli frame" scheme) [derived]: walk the circuit in program order, carrying
a Pauli-frame label per qubit (frame[q] in {I,X,Y,Z}, meaning "the physically-realized circuit's
state equals this Pauli applied to the IDEAL circuit's state at this point"). A 1-qubit Clifford
gate (H) and a 2-qubit Clifford gate (CX) are emitted UNCHANGED; the frame propagates through them
by ordinary Pauli conjugation (H swaps X<->Z; CX follows the standard CNOT stabilizer-update
rule). At every ZZPhase/XXPhase gate (the twirl targets -- these are the only non-Clifford
entanglers the project's circuits use, authored in src/encoded_tfim.py/src/encoded_codes.py), the
INCOMING frame on the gate's two qubits determines whether it commutes or anticommutes with the
gate's generator; the PHYSICALLY EMITTED gate has its angle sign-flipped accordingly (this is the
only way to keep an EXACT Pauli-frame algebra through an arbitrary, non-Clifford rotation angle --
conjugating an arbitrary-angle rotation BY a Pauli stays a rotation of the same type; conjugating a
Pauli THROUGH an arbitrary-angle rotation does not generally stay a Pauli). A FRESH, independently
random Pauli pair is then drawn for the two qubits and PHYSICALLY EMITTED as an explicit X/Y/Z gate
immediately after the (sign-adjusted) rotation, on whichever qubit drew a non-identity Pauli; the
outgoing frame is set to this fresh draw XORed with the incoming frame (same bit-level composition
as any other Pauli-after-Pauli product).

[CORRECTNESS NOTE, found in audit 2026-10-15]: an earlier version of this function tried to make
the fresh draw free by only updating the frame dict, never emitting a gate for it, reasoning that
"it rides along for free until it flips a later gate's sign or a final readout". That reasoning is
WRONG: the incoming frame can be absorbed for free into the gate's sign because P in P R(alpha) P^-1
= +-R(alpha) is an identity about THIS SAME, already-present P; a FRESH, independently-drawn P has
no such relationship to establish -- it is a NEW Pauli that must be physically realized by SOME
gate for the frame bookkeeping to remain true, exactly as a real device twirl physically inserts a
random Pauli layer between two-qubit gates. Omitting that gate made the twirled circuit's actual
output differ from the untwirled one by more than a Pauli frame (confirmed both analytically for a
2-gate chain and numerically via exact statevector comparison -- see the "must fail without the
explicit emission" check in tests/test_twirl.py). Emitting the fresh draw explicitly, as this
version does, is NOT free: it costs up to two extra 1-qubit gates per twirled 2-qubit gate (see
scripts/twirl_gate_count.py, Step 3 of the randomized-compiling brief, DECISIONS.md OPEN-3). This
also means EVERY ZZPhase/XXPhase touch -- including the very first one on a given qubit -- is now
varied across twirl instances (the earlier "known limitation" about first touches no longer
applies, since the fresh gate is emitted regardless of whether the incoming frame was trivial).

A fresh Pauli, once emitted, still needs to be tracked forward exactly like any other Pauli: it
rides in the frame until it either changes the sign of a LATER ZZPhase/XXPhase gate it is carried
into, or reaches a Z-basis measurement, where an X or Y component must flip the recorded classical
bit (frame_readout_flips below). This is also why mid-circuit Reset matters: a reset forces the
physical qubit to a KNOWN state (|0>) regardless of any pending frame, so frame on a reset qubit
always clears to I with no correction needed for the reset itself (only for whatever measurement
preceded it).

Status tags: the Pauli-algebra identities above are [established]; the frame-propagation scheme
built from them is [derived]; nothing here is [measured] or [assumed] -- there is no noise model
in this module, only exact circuit transformation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from pytket import Circuit, OpType

PauliLabel = str   # one of "I", "X", "Y", "Z"

_TO_BITS: Dict[str, Tuple[int, int]] = {"I": (0, 0), "X": (1, 0), "Z": (0, 1), "Y": (1, 1)}
_FROM_BITS: Dict[Tuple[int, int], str] = {v: k for k, v in _TO_BITS.items()}
_TWIRLED_TYPES = (OpType.ZZPhase, OpType.XXPhase)


@dataclass
class TwirlResult:
    """One randomized-compiling instance: the twirled circuit and the Pauli frame it leaves
    on every qubit touched by a twirl (qubits never involved in a ZZPhase/XXPhase gate, or
    whose frame happened to return to "I", are simply absent -- treat missing as "I")."""

    circuit: Circuit
    frame: Dict[int, PauliLabel]


def _get(frame: Dict[int, PauliLabel], q: int) -> PauliLabel:
    return frame.get(q, "I")


_EMIT_PAULI = {"X": lambda c, q: c.X(q), "Y": lambda c, q: c.Y(q), "Z": lambda c, q: c.Z(q)}


def twirl_circuit(circuit: Circuit, rng: np.random.Generator,
                   frame_in: Optional[Dict[int, PauliLabel]] = None) -> TwirlResult:
    """Twirl every ZZPhase/XXPhase gate in `circuit`, threading an optional incoming Pauli
    frame (default: identity on every qubit). H and CX are emitted unchanged (frame propagates
    through them); any other gate type raises, matching the strict op-set this project's
    authored segments use (src/encoded_tfim.py, src/encoded_codes.py: only H, CX, ZZPhase,
    XXPhase appear). Reproducible: the only randomness drawn is from `rng`, one 4-bit uniform
    choice per twirled gate, in program order. The fresh draw at each twirled gate is emitted as
    an explicit X/Y/Z gate on whichever qubit(s) drew a non-identity Pauli (see the module
    docstring's correctness note) -- NOT free; up to two extra 1-qubit gates per twirled gate.
    """
    n = circuit.n_qubits
    frame: Dict[int, PauliLabel] = dict(frame_in) if frame_in else {}
    new_c = Circuit(n)
    for cmd in circuit.get_commands():
        typ = cmd.op.type
        qs = [q.index[0] for q in cmd.qubits]
        if typ == OpType.H:
            q = qs[0]
            new_c.H(q)
            x, z = _TO_BITS[_get(frame, q)]
            frame[q] = _FROM_BITS[(z, x)]
        elif typ == OpType.CX:
            c, t = qs
            new_c.CX(c, t)
            xc, zc = _TO_BITS[_get(frame, c)]
            xt, zt = _TO_BITS[_get(frame, t)]
            frame[c] = _FROM_BITS[(xc, zc ^ zt)]
            frame[t] = _FROM_BITS[(xt ^ xc, zt)]
        elif typ in _TWIRLED_TYPES:
            a, b = qs
            alpha = float(cmd.op.params[0])
            xa, za = _TO_BITS[_get(frame, a)]
            xb, zb = _TO_BITS[_get(frame, b)]
            # commute bit: x-component for a Z#Z generator (ZZPhase), z-component for X#X (XXPhase)
            comp = 0 if typ == OpType.ZZPhase else 1
            ca = (xa, za)[comp]
            cb = (xb, zb)[comp]
            s_in = 1.0 if ca == cb else -1.0
            if typ == OpType.ZZPhase:
                new_c.ZZPhase(alpha * s_in, a, b)
            else:
                new_c.XXPhase(alpha * s_in, a, b)
            draw = rng.integers(0, 2, size=4)
            lbl_a = _FROM_BITS[(int(draw[0]), int(draw[1]))]
            lbl_b = _FROM_BITS[(int(draw[2]), int(draw[3]))]
            if lbl_a != "I":
                _EMIT_PAULI[lbl_a](new_c, a)
            if lbl_b != "I":
                _EMIT_PAULI[lbl_b](new_c, b)
            frame[a] = _FROM_BITS[(xa ^ int(draw[0]), za ^ int(draw[1]))]
            frame[b] = _FROM_BITS[(xb ^ int(draw[2]), zb ^ int(draw[3]))]
        else:
            raise ValueError(f"twirl_circuit: unsupported op {typ}")
    return TwirlResult(new_c, frame)


def frame_readout_flips(frame: Dict[int, PauliLabel], qubits: Sequence[int],
                        basis: str = "Z") -> np.ndarray:
    """Classical bit-flip mask (int8, same length/order as `qubits`) a measurement of each
    listed qubit must be XORed with to recover the untwirled/ideal outcome: 1 iff the frame
    on that qubit anticommutes with the observable actually measured.

    `basis` selects which component of the frame matters. Getting it wrong is silent, which is
    why it is a named argument rather than an assumption:
      "Z" (default) -- flip iff the frame is X or Y (the frame's X-component).
      "X"           -- flip iff the frame is Z or Y (the frame's Z-component). Use this when the
                       readout conjugates the data by H before measuring, as
                       `encoded_tfim.build_stim(..., basis="X")` does: after that H the
                       computational-basis measurement reads the original X observable, so it is
                       the frame's Z-component that flips the bit, not its X-component.
    """
    if basis not in ("Z", "X"):
        raise ValueError(f"basis must be 'Z' or 'X', got {basis!r}")
    bit = 0 if basis == "Z" else 1          # _TO_BITS values are (x_bit, z_bit)
    return np.array([_TO_BITS[_get(frame, q)][bit] for q in qubits], dtype=np.int8)


def clear_frame(frame: Dict[int, PauliLabel], qubits: Sequence[int]) -> None:
    """A physical Reset forces a qubit to the known state |0>, regardless of any pending
    frame; call this on the qubits a caller resets, after using frame_readout_flips on the
    measurement that preceded the reset (src/backends_qc.LocalSim.reset pattern)."""
    for q in qubits:
        frame[q] = "I"


def twirl_ensemble(circuit: Circuit, n: int, seed: int,
                    frame_in: Optional[Dict[int, PauliLabel]] = None) -> List[TwirlResult]:
    """`n` independent, reproducible randomized-compiling instances of `circuit` from one
    `seed` (numpy SeedSequence spawning -- re-running with the same seed and n reproduces the
    same ensemble exactly; a larger n only appends further-spawned streams, it does not
    perturb the first n' < n instances)."""
    children = np.random.SeedSequence(seed).spawn(n)
    return [twirl_circuit(circuit, np.random.default_rng(c), frame_in) for c in children]
