"""Backend toggle for the encoded TFIM program (handoff/04): local-sim | selene | nexus.

All three consume the SAME authored pytket segments from src/encoded_tfim.IcebergTFIM.

local-sim  pytket core (2.18.4) ships no shot simulator: Circuit.get_statevector() refuses
           mid-circuit Measure/Reset. So local-sim executes the pytket Circuit objects command by
           command in an in-repo state-vector engine that adds measurement, reset and stochastic
           Pauli noise. Its unitary action is cross-checked against pytket's own
           get_statevector() in tests. Discard is applied classically per shot.
selene     the segments are loaded into a Guppy program with guppy.load_pytket; syndrome
           ancillas are measured MID-CIRCUIT (project_z + reset), and the discard decision is
           computed in-program and FED FORWARD: once a detector fires, every later quantum block
           is skipped. Runs on the Selene emulator (Quest state vector) with Selene's
           DepolarizingErrorModel. Selene applies its rates to ITS OWN compiled native gates,
           so its gate-level exposure can differ from local-sim's [stated, not hidden].
nexus      stub only: raises NotImplementedError (see docs/nexus_toggle.md).

A noisy curve from local-sim or selene is a classical prediction under a stated, assumed noise
model, never an H2 result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
from pytket import Circuit, OpType

from src.encoded_tfim import IcebergTFIM, ShotRecord, check_physical_ceiling

BACKENDS = ("local-sim", "selene", "nexus")
NEXUS_MSG = ("Nexus backend: requires Quantinuum credentials/credits; flip toggle when access "
             "is granted")


@dataclass
class Noise:
    """Generic depolarizing rates [ASSUMPTIONS, not measurements, not H2-calibrated]."""

    p2: float = 0.0       # after every 2-qubit gate: uniform over the 15 non-identity Paulis
    p1: float = 0.0       # after every 1-qubit gate: uniform over X, Y, Z
    pm: float = 0.0       # classical flip of every measurement outcome
    p_init: float = 0.0   # X after every reset / initialisation
    p_idle: float = 0.0   # local-sim only: depolarizing on code qubits once per Trotter step and
                          # per syndrome round (Selene's model has no idle term)

    @property
    def zero(self) -> bool:
        return not (self.p2 or self.p1 or self.pm or self.p_init or self.p_idle)


# --------------------------------------------------------------------------- #
# local-sim: state-vector interpreter for pytket commands
# --------------------------------------------------------------------------- #
_H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
_PAULI = {"I": np.eye(2, dtype=complex), "X": np.array([[0, 1], [1, 0]], dtype=complex),
          "Y": np.array([[0, -1j], [1j, 0]]), "Z": np.diag([1.0, -1.0]).astype(complex)}
_CX = np.eye(4, dtype=complex)[[0, 1, 3, 2]]


def _pp_matrix(typ: OpType, alpha: float) -> np.ndarray:
    """PhasePP(alpha) = exp(-i pi alpha/2 P(x)P) (pytket half-turn convention)."""
    P = _PAULI["Z"] if typ == OpType.ZZPhase else _PAULI["X"]
    a = np.pi * alpha / 2
    return np.cos(a) * np.eye(4) - 1j * np.sin(a) * np.kron(P, P)


class StateVector:
    """|psi> on n qubits, qubit 0 = most significant bit (repo convention)."""

    def __init__(self, n: int, rng: np.random.Generator):
        self.n = n
        self.rng = rng
        self.psi = np.zeros((2,) * n, dtype=complex)
        self.psi[(0,) * n] = 1.0

    def apply1(self, U: np.ndarray, q: int) -> None:
        self.psi = np.moveaxis(np.tensordot(U, self.psi, axes=([1], [q])), 0, q)

    def apply2(self, U: np.ndarray, a: int, b: int) -> None:
        t = np.tensordot(U.reshape(2, 2, 2, 2), self.psi, axes=([2, 3], [a, b]))
        self.psi = np.moveaxis(t, [0, 1], [a, b])

    def measure(self, q: int) -> int:
        p1 = float(np.sum(np.abs(np.take(self.psi, 1, axis=q)) ** 2))
        bit = int(self.rng.random() < p1)
        keep = np.take(self.psi, bit, axis=q)
        norm = np.sqrt(p1 if bit else 1 - p1)
        new = np.zeros_like(self.psi)
        idx = [slice(None)] * self.n
        idx[q] = bit
        new[tuple(idx)] = keep / norm
        self.psi = new
        return bit

    def reset(self, q: int) -> None:
        if self.measure(q):
            self.apply1(_PAULI["X"], q)

    def flat(self) -> np.ndarray:
        return self.psi.reshape(-1)


class LocalSim:
    """Executes the authored pytket segments with noise; one instance per shot stream."""

    def __init__(self, noise: Noise, seed: int):
        self.noise = noise
        self.rng = np.random.default_rng(seed)

    def _pauli_noise(self, sv: StateVector, qs: List[int], p: float) -> None:
        if p and self.rng.random() < p:
            labels = "IXYZ"
            while True:
                draw = [labels[self.rng.integers(4)] for _ in qs]
                if any(x != "I" for x in draw):
                    break
            for q, x in zip(qs, draw):
                if x != "I":
                    sv.apply1(_PAULI[x], q)

    def run_segment(self, sv: StateVector, seg: Circuit) -> None:
        for cmd in seg.get_commands():
            typ = cmd.op.type
            qs = [q.index[0] for q in cmd.qubits]
            if typ == OpType.H:
                sv.apply1(_H, qs[0])
                self._pauli_noise(sv, qs, self.noise.p1)
            elif typ == OpType.CX:
                sv.apply2(_CX, qs[0], qs[1])
                self._pauli_noise(sv, qs, self.noise.p2)
            elif typ in (OpType.ZZPhase, OpType.XXPhase):
                sv.apply2(_pp_matrix(typ, float(cmd.op.params[0])), qs[0], qs[1])
                self._pauli_noise(sv, qs, self.noise.p2)
            else:
                raise ValueError(f"local-sim: unsupported op {typ}")

    def measure(self, sv: StateVector, q: int) -> int:
        bit = sv.measure(q)
        if self.noise.pm and self.rng.random() < self.noise.pm:
            bit ^= 1
        return bit

    def reset(self, sv: StateVector, q: int) -> None:
        sv.reset(q)
        if self.noise.p_init and self.rng.random() < self.noise.p_init:
            sv.apply1(_PAULI["X"], q)

    def idle(self, sv: StateVector, qs: List[int]) -> None:
        for q in qs:
            self._pauli_noise(sv, [q], self.noise.p_idle)


def _local_shot(spec: IcebergTFIM, n_steps: int, sim: LocalSim, segs: Dict[str, Circuit],
                sync: set) -> ShotRecord:
    sv = StateVector(spec.n_phys, sim.rng)
    for q in range(spec.n_phys):                 # initialisation errors on |0^n>
        if sim.noise.p_init and sim.rng.random() < sim.noise.p_init:
            sv.apply1(_PAULI["X"], q)
    rounds = []

    def syndrome_round():
        out = []
        for kind in ("Z", "X"):
            sim.run_segment(sv, segs["syn" + kind])
            out += [sim.measure(sv, spec.A), sim.measure(sv, spec.F)]
            sim.reset(sv, spec.A)
            sim.reset(sv, spec.F)
        sim.idle(sv, spec.data)
        sz, fz, sx, fx = out
        rounds.append((sz, fz, sx, fx))

    syndrome_round()
    sim.run_segment(sv, segs["prep"])
    for s in range(1, n_steps + 1):
        sim.run_segment(sv, segs["trotter"])
        sim.idle(sv, spec.data)
        if s in sync:
            syndrome_round()
    final = np.array([sim.measure(sv, q) for q in spec.data], dtype=np.int8)
    return ShotRecord(rounds, final)


def local_exact_logical_z2(spec: IcebergTFIM, n_steps: int) -> float:
    """Noiseless local-sim, exact (no sampling) logical Z2 at the end of the program.
    Random mid-circuit outcomes (only round-0 S_X) are resolved by a fixed branch; the logical
    distribution does not depend on that branch (S_X sign is a pure frame)."""
    rng = np.random.default_rng(0)
    sim = LocalSim(Noise(), 0)
    segs = _segments(spec)
    sv = StateVector(spec.n_phys, rng)
    sync = set(spec.syndrome_steps(n_steps))

    def syndrome_round():
        for kind in ("Z", "X"):
            sim.run_segment(sv, segs["syn" + kind])
            for q in (spec.A, spec.F):
                sv.reset(q)

    syndrome_round()
    sim.run_segment(sv, segs["prep"])
    for s in range(1, n_steps + 1):
        sim.run_segment(sv, segs["trotter"])
        if s in sync:
            syndrome_round()
    probs = np.abs(sv.flat()) ** 2
    n, k = spec.n_phys, spec.k
    idx = np.arange(1 << n)
    bit = lambda q: (idx >> (n - 1 - q)) & 1          # noqa: E731
    zb = bit(spec.b)
    M = sum(1 - 2 * (bit(i) ^ zb) for i in range(k)).astype(float)
    return float(np.sum(probs * M ** 2)) / k ** 2


def _segments(spec: IcebergTFIM) -> Dict[str, Circuit]:
    return {"prep": spec.prep_segment(), "trotter": spec.trotter_segment(),
            "synZ": spec.syndrome_segment("Z"), "synX": spec.syndrome_segment("X")}


# --------------------------------------------------------------------------- #
# selene: Guppy program with mid-circuit measurement + feedforward discard
# --------------------------------------------------------------------------- #
_selene_counter = [0]


def build_guppy_program(spec: IcebergTFIM, n_steps: int):
    """Guppy program for one (spec, n_steps). Returns the @guppy main function."""
    from guppylang import guppy
    from guppylang.std.builtins import array, comptime, result
    from guppylang.std.quantum import discard_array, project_z, qubit, reset

    _selene_counter[0] += 1
    tag = f"{_selene_counter[0]}"
    segs = _segments(spec)
    prep_fn = guppy.load_pytket(f"prep_{tag}", segs["prep"])
    trot_fn = guppy.load_pytket(f"trot_{tag}", segs["trotter"])
    synz_fn = guppy.load_pytket(f"synz_{tag}", segs["synZ"])
    synx_fn = guppy.load_pytket(f"synx_{tag}", segs["synX"])
    N, A, F, NS = spec.n_phys, spec.A, spec.F, n_steps
    ND, E = spec.k + 2, spec.syndrome_every

    @guppy
    def main() -> None:
        q = array(qubit() for _ in range(comptime(N)))
        # round 0: S_Z must read 0; S_X sets the reference frame
        synz_fn(q)
        sz = project_z(q[comptime(A)]).read()
        fz = project_z(q[comptime(F)]).read()
        reset(q[comptime(A)])
        reset(q[comptime(F)])
        synx_fn(q)
        sx_ref = project_z(q[comptime(A)]).read()
        fx = project_z(q[comptime(F)]).read()
        reset(q[comptime(A)])
        reset(q[comptime(F)])
        result("sz", sz)
        result("fz", fz)
        result("sx", sx_ref)
        result("fx", fx)
        ok = not (sz or fz or fx)
        sz_prev = sz
        if ok:
            prep_fn(q)
        for s in range(comptime(NS)):
            if ok:                                   # feedforward: skip all work once discarded
                trot_fn(q)
                if (s + 1) % comptime(E) == 0 or s + 1 == comptime(NS):
                    synz_fn(q)
                    sz2 = project_z(q[comptime(A)]).read()
                    fz2 = project_z(q[comptime(F)]).read()
                    reset(q[comptime(A)])
                    reset(q[comptime(F)])
                    synx_fn(q)
                    sx2 = project_z(q[comptime(A)]).read()
                    fx2 = project_z(q[comptime(F)]).read()
                    reset(q[comptime(A)])
                    reset(q[comptime(F)])
                    result("sz", sz2)
                    result("fz", fz2)
                    result("sx", sx2)
                    result("fx", fx2)
                    if fz2 or fx2 or sz2 != sz_prev or sx2 != sx_ref:
                        ok = False
                    sz_prev = sz2
        par = False
        for i in range(comptime(ND)):
            bit = project_z(q[i]).read()
            result("d", bit)
            par = par != bit
        result("accepted", ok and par == sz_prev)
        discard_array(q)

    return main


def _parse_selene(entries) -> ShotRecord:
    rounds, cur, final, acc = [], [], [], None
    for key, val in entries:
        if key in ("sz", "fz", "sx", "fx"):
            cur.append(int(val))
            if len(cur) == 4:
                rounds.append(tuple(cur))
                cur = []
        elif key == "d":
            final.append(int(val))
        elif key == "accepted":
            acc = bool(val)
    rec = ShotRecord(rounds, np.array(final, dtype=np.int8))
    rec.in_program_accepted = acc        # type: ignore[attr-defined]
    return rec


# --------------------------------------------------------------------------- #
# Toggle
# --------------------------------------------------------------------------- #
def run(spec: IcebergTFIM, n_steps: int, shots: int, noise: Noise, backend: str, seed: int,
        max_spins: int) -> List[ShotRecord]:
    """Execute the encoded program for `n_steps` Trotter steps and return per-shot records."""
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; choose one of {BACKENDS}")
    if backend == "nexus":
        raise NotImplementedError(NEXUS_MSG)
    check_physical_ceiling(spec.n_phys, max_spins)        # before any allocation
    if backend == "local-sim":
        sim = LocalSim(noise, seed)
        segs = _segments(spec)
        sync = set(spec.syndrome_steps(n_steps))
        return [_local_shot(spec, n_steps, sim, segs, sync) for _ in range(shots)]
    # selene
    from selene_sim import DepolarizingErrorModel, Quest
    if noise.p_idle:
        raise ValueError("selene's DepolarizingErrorModel has no idle term; set p_idle = 0")
    prog = build_guppy_program(spec, n_steps)
    em = DepolarizingErrorModel(random_seed=seed, p_1q=noise.p1, p_2q=noise.p2,
                                p_meas=noise.pm, p_init=noise.p_init)
    res = (prog.emulator(n_qubits=spec.n_phys).with_shots(shots).with_simulator(Quest())
           .with_seed(seed).with_error_model(em).run())
    return [_parse_selene(s.entries) for s in res.results]


# --------------------------------------------------------------------------- #
# Bare (unencoded) reference at matched gate-level noise, for the limits assessment
# --------------------------------------------------------------------------- #
def bare_segments(spec: IcebergTFIM) -> Dict[str, Circuit]:
    """The same logical evolution on k bare qubits: ry(theta) as Rz(-1/2) Rx Rz(1/2)-free form:
    pytket Ry, Rx field half-layers and ZZPhase bonds (1q gates carry p1, 2q gates p2)."""
    prep = Circuit(spec.k)
    for i in range(spec.k):
        prep.Ry(spec.theta / np.pi, i)
    trot = Circuit(spec.k)
    ax = 2 * (-spec.h * spec.dt / 2) / np.pi         # exp(-i phi X) = Rx(2 phi/pi)
    az = 2 * (-spec.J * spec.dt) / np.pi
    for i in range(spec.k):
        trot.Rx(ax, i)
    for i, j in spec.bonds:
        trot.ZZPhase(az, i, j)
    for i in range(spec.k):
        trot.Rx(ax, i)
    return {"prep": prep, "trotter": trot}


def run_bare_local(spec: IcebergTFIM, n_steps: int, shots: int, noise: Noise, seed: int,
                   max_spins: int) -> np.ndarray:
    """Bare logical lattice under the same per-gate rates; returns (shots, k) Z eigenvalues."""
    check_physical_ceiling(spec.k, max_spins)
    sim = LocalSim(noise, seed)
    segs = bare_segments(spec)
    rot = {OpType.Rx: _PAULI["X"], OpType.Ry: _PAULI["Y"]}
    out = np.empty((shots, spec.k), dtype=np.int8)
    for s_ in range(shots):
        sv = StateVector(spec.k, sim.rng)
        for q in range(spec.k):
            if noise.p_init and sim.rng.random() < noise.p_init:
                sv.apply1(_PAULI["X"], q)
        for name, reps in (("prep", 1), ("trotter", n_steps)):
            for _ in range(reps):
                for cmd in segs[name].get_commands():
                    typ = cmd.op.type
                    qs = [q.index[0] for q in cmd.qubits]
                    if typ in rot:
                        a = np.pi * float(cmd.op.params[0]) / 2
                        sv.apply1(np.cos(a) * np.eye(2) - 1j * np.sin(a) * rot[typ], qs[0])
                        sim._pauli_noise(sv, qs, noise.p1)
                    else:
                        sv.apply2(_pp_matrix(typ, float(cmd.op.params[0])), qs[0], qs[1])
                        sim._pauli_noise(sv, qs, noise.p2)
                if name == "trotter":
                    sim.idle(sv, list(range(spec.k)))
        out[s_] = [1 - 2 * sim.measure(sv, q) for q in range(spec.k)]
    return out
