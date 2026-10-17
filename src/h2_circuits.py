"""Authoring the encoded and bare TFIM programs as ONE pytket circuit each, for H2 (handoff/13).

H2 and its Nexus emulators accept pytket circuits / QIR, not Guppy/HUGR (HUGR is Helios-only in
qnexus 0.51.1, docs/quantinuum_issues.md QI-3). So the Guppy program's feedforward discard cannot
run on H2; instead every shot runs to the end, the syndrome bits are measured MID-CIRCUIT into
classical registers (measure + reset on the ancilla and flag, supported on H2), and the discard is
applied classically afterwards by the same `accepted()` predicate every other backend uses. HQC is
charged on static gate counts, so skipping work after a detection would not have saved credits.

Layout of one encoded circuit (H2Layout):
  registers r0, r1, ... of 4 bits each, in program order, holding (sz, fz, sx, fx) of every
  syndrome round (round 0, then one per spec.syndrome_steps), then register "d" with the k+2
  final data bits. A twirled instance's classical frame corrections are NOT in the circuit; they
  are applied to the raw bits in `shot_records`, exactly as backends_qc._local_shot_twirled does.

Everything here is additive. Nothing contacts Quantinuum.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pytket import Bit, Circuit, OpType

from src.backends_qc import _segments, bare_segments
from src.encoded_codes import EncodedTFIM, _support
from src.encoded_tfim import IcebergTFIM, ShotRecord, TwirledProgram
from src.noise_scaling import hqc_cost


@dataclass
class H2Layout:
    """Where each classical result lives in the circuit's registers."""

    round_steps: list[int]  # 0 for the round-0 syndrome, then each Trotter step with a round
    n_final: int  # k + 2 data bits, register "d"

    @property
    def round_regs(self) -> list[str]:
        return [f"r{i}" for i in range(len(self.round_steps))]

    @property
    def cbits(self) -> list[Bit]:
        """All result bits in the order `shot_records` expects."""
        out = [Bit(r, j) for r in self.round_regs for j in range(4)]
        return out + [Bit("d", j) for j in range(self.n_final)]


def encoded_h2_circuit(
    spec: IcebergTFIM, n_steps: int, prog: TwirledProgram | None = None
) -> tuple[Circuit, H2Layout]:
    """The whole encoded program as one circuit. `prog` swaps in a randomized-compiling instance's
    prep/trotter circuits (src.encoded_tfim.twirl_program); the syndrome segments are shared."""
    segs = _segments(spec)
    sync = set(spec.syndrome_steps(n_steps))
    steps = [0] + [s for s in range(1, n_steps + 1) if s in sync]
    c = Circuit(spec.n_phys)
    A, F = spec.A, spec.F

    def syndrome_round(idx: int) -> None:
        reg = c.add_c_register(f"r{idx}", 4)
        for j, kind in enumerate(("Z", "X")):
            c.append(segs["syn" + kind])
            c.Measure(c.qubits[A], reg[2 * j])
            c.Measure(c.qubits[F], reg[2 * j + 1])
            c.Reset(c.qubits[A])
            c.Reset(c.qubits[F])

    syndrome_round(0)
    c.append(prog.prep if prog is not None else segs["prep"])
    ridx = 0
    for s in range(1, n_steps + 1):
        c.append(prog.trotter_layers[s - 1] if prog is not None else segs["trotter"])
        if s in sync:
            ridx += 1
            syndrome_round(ridx)
    d = c.add_c_register("d", len(spec.data))
    for i, q in enumerate(spec.data):
        c.Measure(c.qubits[q], d[i])
    return c, H2Layout(steps, len(spec.data))


def shot_records(
    shots: np.ndarray, layout: H2Layout, prog: TwirledProgram | None = None
) -> list[ShotRecord]:
    """(n_shots, len(layout.cbits)) raw bits -> ShotRecords, with a twirled instance's classical
    frame corrections applied (the same XORs as backends_qc._local_shot_twirled)."""
    shots = np.asarray(shots, dtype=np.int8)
    n_round = len(layout.round_steps)
    if shots.ndim != 2 or shots.shape[1] != 4 * n_round + layout.n_final:
        raise ValueError(
            f"expected (n_shots, {4 * n_round + layout.n_final}) bits, got {shots.shape}"
        )
    out: list[ShotRecord] = []
    for row in shots:
        rounds = []
        for i, step in enumerate(layout.round_steps):
            raw = [int(b) for b in row[4 * i : 4 * i + 4]]
            if prog is not None:
                flip = prog.round0_flip if step == 0 else prog.round_flip[step]
                raw = [b ^ int(f) for b, f in zip(raw, flip, strict=True)]
            rounds.append(tuple(raw))
        final = row[4 * n_round :].astype(np.int8)
        if prog is not None:
            final = final ^ np.asarray(prog.final_flip, dtype=np.int8)
        out.append(ShotRecord(rounds, final))
    return out


def bare_h2_circuit(spec: IcebergTFIM, n_steps: int) -> tuple[Circuit, list[Bit]]:
    """The bare (unencoded) reference on k qubits: same logical evolution, Z readout into "m"."""
    segs = bare_segments(spec)
    c = Circuit(spec.k)
    c.append(segs["prep"])
    for _ in range(n_steps):
        c.append(segs["trotter"])
    m = c.add_c_register("m", spec.k)
    for i in range(spec.k):
        c.Measure(c.qubits[i], m[i])
    return c, [Bit("m", i) for i in range(spec.k)]


def bare_z(shots: np.ndarray) -> np.ndarray:
    """Raw bare readout bits -> +-1 Z eigenvalues, (n_shots, k), as run_bare_local returns."""
    return (1 - 2 * np.asarray(shots, dtype=np.int8)).astype(np.int8)


# --------------------------------------------------------------------------- #
# The other codes (Steane, 5-qubit, concatenated Iceberg; src/encoded_codes.py)
# --------------------------------------------------------------------------- #
# Their program is a Schedule (unitary segments, measurements, resets, feedforward Pauli
# corrections, detectors). Round 0 of a code with mixed-type stabilizers FEEDS FORWARD the
# stabilizer's pure error when it reads -1, before the non-Clifford rotations (the frame would
# otherwise flip rotation signs), so here it is emitted as REAL conditional X/Y/Z gates -- pytket
# conditional gates, which H2 supports and the local emulator executes. Detectors stay classical.
_CHUNK = 32  # result bits per classical register, to stay far below any width limit


@dataclass
class CodesLayout:
    keys: list[str]  # measurement keys in program order
    detectors: list[list[int]]  # each: indices into keys whose XOR must be 0
    logicals: list[list[int]]  # per logical qubit: key indices whose parity is its Z

    @property
    def cbits(self) -> list[Bit]:
        return [Bit(f"m{i // _CHUNK}", i % _CHUNK) for i in range(len(self.keys))]


def codes_h2_circuit(prog: EncodedTFIM, n_steps: int) -> tuple[Circuit, CodesLayout]:
    """The whole Z-prep program of `prog` (steps `n_steps`) as ONE circuit plus its layout."""
    sch = prog.schedule(n_steps, "Z")
    if sch.basis_prep:
        raise ValueError("only the executed Z-prep program is authored for H2")
    c = Circuit(sch.n)
    keys = [it[2] for it in sch.items if it[0] == "M"]
    idx = {k: i for i, k in enumerate(keys)}
    regs = [
        c.add_c_register(f"m{r}", min(_CHUNK, len(keys) - r * _CHUNK))
        for r in range((len(keys) + _CHUNK - 1) // _CHUNK)
    ]
    bit = lambda i: regs[i // _CHUNK][i % _CHUNK]  # noqa: E731
    detectors: list[list[int]] = []
    for it in sch.items:
        kind = it[0]
        if kind == "U":
            c.append(it[1])
        elif kind == "M":
            c.Measure(c.qubits[it[1]], bit(idx[it[2]]))
        elif kind == "R":
            c.Reset(c.qubits[it[1]])
        elif kind == "C":
            P = it[2]
            for q in _support(P):
                gate = (c.X, c.Y, c.Z)[P[q] - 1]
                gate(q, condition_bits=[bit(idx[it[1]])], condition_value=1)
        elif kind == "D":
            detectors.append([idx[k] for k in it[1]])
        # "I" (idle-noise points) carry no operation
    return c, CodesLayout(keys, detectors, [[idx[k] for k in ks] for ks in sch.logicals])


def codes_records(bits: np.ndarray, layout: CodesLayout) -> list[tuple[bool, np.ndarray]]:
    """Raw bits -> (accepted, logical +-1 array) per shot, as src.encoded_codes.run_local returns:
    accepted iff every detector parity is 0."""
    bits = np.asarray(bits, dtype=np.int8)
    if bits.ndim != 2 or bits.shape[1] != len(layout.keys):
        raise ValueError(f"expected (n_shots, {len(layout.keys)}) bits, got {bits.shape}")
    out = []
    for row in bits:
        ok = all(int(row[d].sum()) % 2 == 0 for d in layout.detectors)
        vals = np.array([1 - 2 * (int(row[ks].sum()) % 2) for ks in layout.logicals], dtype=np.int8)
        out.append((ok, vals))
    return out


# --------------------------------------------------------------------------- #
# Compilation and cost (offline)
# --------------------------------------------------------------------------- #
_NON_GATE = (
    OpType.Measure,
    OpType.Reset,
    OpType.Barrier,
    OpType.ClassicalTransform,
    OpType.SetBits,
    OpType.CopyBits,
    OpType.RangePredicate,
    OpType.ExplicitPredicate,
    OpType.ExplicitModifier,
    OpType.MultiBit,
)


def two_qubit_count(c: Circuit) -> int:
    return sum(
        1 for cmd in c.get_commands() if len(cmd.qubits) == 2 and cmd.op.type not in _NON_GATE
    )


def compile_for_h2(c: Circuit, backend) -> Circuit:
    """Compile to H2's native gates at TKET level 0 (D-NS6: levels 1-2 cancel folded gates), and
    assert the two-qubit count did not change -- twirling and folding exist to change the noise,
    so a compiler that silently removed entanglers would make the run something else."""
    before = two_qubit_count(c)
    out = backend.get_compiled_circuit(c, optimisation_level=0)
    after = two_qubit_count(out)
    if after != before:
        raise RuntimeError(f"compilation changed the two-qubit count {before} -> {after}")
    return out


def native_counts(c: Circuit) -> dict[str, int]:
    """Gate/measurement counts of a COMPILED circuit, for the HQC formula."""
    n1 = nrz = n2 = nm = nr = 0
    for cmd in c.get_commands():
        t = cmd.op.type
        if t == OpType.Conditional:  # a conditional gate is the gate it wraps (cmd.qubits excludes the bits)
            t = cmd.op.op.type
        if t == OpType.Measure:
            nm += 1
        elif t == OpType.Reset:
            nr += 1
        elif t in _NON_GATE:
            continue
        elif len(cmd.qubits) == 2:
            n2 += 1
        elif len(cmd.qubits) == 1:
            n1 += 1
            nrz += int(t == OpType.Rz)
    return {"n1q": n1, "nrz": nrz, "n2q": n2, "nmeas": nm, "nreset": nr, "nqubits": c.n_qubits}


def hqc_estimate(counts: dict[str, int], shots: int, count_rz: bool = False) -> float:
    """Offline HQC estimate, HQC = 5 + C (N1q + 10 N2q + 5 Nm)/5000 [established, research/07],
    with Nm = state preparations (one per qubit) + mid-circuit and final measurements + resets.
    Rz is NOT charged by default: the free H2-1SC quoted 42 circuits and the Rz-free estimate equals
    the quote to the cent for Iceberg and bare circuits [measured, data/h2_sc_quotes*.txt; DECISIONS
    D-HQC]. `count_rz=True` charges the virtual Rz gates as one-qubit gates (the older, conservative
    upper bound, 15-20% too high)."""
    n1 = counts["n1q"] - (0 if count_rz else counts["nrz"])
    nm = counts["nqubits"] + counts["nmeas"] + counts["nreset"]
    return hqc_cost(n1, counts["n2q"], nm, shots)
