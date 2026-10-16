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

from src.encoded_tfim import (IcebergTFIM, ShotRecord, TwirledProgram, check_physical_ceiling,
                              twirl_program)

BACKENDS = ("local-sim", "selene", "nexus")
NEXUS_MSG = ("Nexus backend: requires Quantinuum credentials/credits; flip toggle when access "
             "is granted")

# The per-run approval token a caller must pass to reach hardware, alongside allow_hardware=True
# (SCOPE §5's double gate). It is deliberately a sentence a human has to type, not a boolean, so
# it cannot be satisfied by a default argument, a stray True, or an automated retry.
NEXUS_APPROVAL = "I approve spending HQC on this run"
# H2's qubit count, read from pytket-quantinuum's own device data (QuantinuumBackendData for H2),
# not hardcoded from a doc: the encoded program must fit (DECISIONS.md OPEN-2).
H2_N_QUBITS = 56


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
            elif typ in (OpType.X, OpType.Y, OpType.Z):
                # explicit twirl Pauli (src/twirl.py). Deliberately noiseless in THIS classical
                # model [assumed, modeling choice]: Noise.p1 represents the SAME rate this
                # project already uses for every other 1-qubit gate, and charging it here too
                # would make a twirled run strictly noisier than an untwirled one even though
                # both see the same stochastic Pauli channel -- breaking the no-op property this
                # module exists to preserve (tests/test_twirl.py). On real/native hardware this
                # gate is NOT free -- see scripts/twirl_gate_count.py's measured native 1q-gate
                # cost (DECISIONS.md OPEN-3); that cost is accounted there, not as extra p1 here.
                sv.apply1(_PAULI[typ.name], qs[0])
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
# Randomized compiling (DECISIONS.md OPEN-3, D-RC; src/twirl.py). ADDITIVE, OFF by default
# (EncodedConfig.rc): this swaps in a TwirledProgram's circuits in place of _segments()'
# "prep"/"trotter", applying the classical frame corrections to the raw sz/fz/sx/fx and final
# bits. "synZ"/"synX" are reused UNCHANGED from `segs` -- they have no ZZPhase gates, so
# twirling never modifies them; only the Pauli frame passes through.
# --------------------------------------------------------------------------- #
def _local_shot_twirled(spec: IcebergTFIM, prog: TwirledProgram, sim: LocalSim,
                        segs: Dict[str, Circuit], sync: set) -> ShotRecord:
    sv = StateVector(spec.n_phys, sim.rng)
    for q in range(spec.n_phys):
        if sim.noise.p_init and sim.rng.random() < sim.noise.p_init:
            sv.apply1(_PAULI["X"], q)
    rounds = []

    def syndrome_round(flip: tuple) -> None:
        out = []
        for kind in ("Z", "X"):
            sim.run_segment(sv, segs["syn" + kind])
            out += [sim.measure(sv, spec.A), sim.measure(sv, spec.F)]
            sim.reset(sv, spec.A)
            sim.reset(sv, spec.F)
        sim.idle(sv, spec.data)
        sz, fz, sx, fx = out
        fza, ffz, fsx, ffx = flip
        rounds.append((sz ^ fza, fz ^ ffz, sx ^ fsx, fx ^ ffx))

    syndrome_round(prog.round0_flip)
    sim.run_segment(sv, prog.prep)
    for s in range(1, len(prog.trotter_layers) + 1):
        sim.run_segment(sv, prog.trotter_layers[s - 1])
        sim.idle(sv, spec.data)
        if s in sync:
            syndrome_round(prog.round_flip[s])
    final = np.array([sim.measure(sv, q) for q in spec.data], dtype=np.int8)
    final = final ^ prog.final_flip
    return ShotRecord(rounds, final)


def run_twirled(spec: IcebergTFIM, n_steps: int, shots: int, noise: Noise, noise_seed: int,
                max_spins: int, rc_seed: int, n_instances: int,
                extra_shots: int = 0) -> List[List[ShotRecord]]:
    """local-sim execution of `n_instances` independent, reproducible randomized-compiling
    instances (src.encoded_tfim.twirl_program, seeded from `rc_seed`), `shots` local-sim shots
    each. At zero noise every instance reproduces the untwirled program's ShotRecords exactly
    (tests/test_twirl.py); under this project's Pauli noise model the per-instance results
    differ shot-by-shot but their ensemble average reproduces the untwirled prediction -- see
    the module docstring of src/twirl.py. Returns one list of ShotRecords per instance."""
    check_physical_ceiling(spec.n_phys, max_spins)
    segs = _segments(spec)
    sync = set(spec.syndrome_steps(n_steps))
    children = np.random.SeedSequence(rc_seed).spawn(n_instances)
    # Spawn the per-instance NOISE seeds too, rather than noise_seed + i: adjacent calls with
    # noise seeds differing by less than n_instances would otherwise share noise streams.
    noise_children = np.random.SeedSequence(noise_seed).spawn(n_instances)
    out: List[List[ShotRecord]] = []
    for i, (child, noise_child) in enumerate(zip(children, noise_children)):
        shots_i = shots + (1 if i < extra_shots else 0)
        prog = twirl_program(spec, n_steps, child)
        sim = LocalSim(noise, int(noise_child.generate_state(1, dtype=np.uint32)[0]))
        out.append([_local_shot_twirled(spec, prog, sim, segs, sync) for _ in range(shots_i)])
    return out


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


_RC_REG: Dict[str, Dict] = {}


def build_guppy_program_twirled(spec: IcebergTFIM, prog: TwirledProgram):
    """Guppy program for ONE randomized-compiling instance (`prog`, from
    src.encoded_tfim.twirl_program; DECISIONS.md OPEN-3). Same wire protocol as
    build_guppy_program (sz/fz/sx/fx per round, d per final bit, then accepted), so
    _parse_selene needs no change. Each Trotter layer gets its OWN loaded pytket function
    (the layers generally differ, since the Pauli frame -- and so the sign of each gate's
    angle -- evolves step to step), and every classical XOR correction from `prog` is baked in
    as a Python-level `not` at SOURCE-GENERATION time (the frame is deterministic given the
    instance's seed, so this is ordinary dead-code elimination, not a runtime branch); the
    final per-qubit corrections differ qubit to qubit, so that loop is unrolled explicitly,
    following the same code-generation pattern as src.encoded_codes.guppy_program."""
    import importlib.util
    import os
    import tempfile

    _selene_counter[0] += 1
    tag = f"rc{_selene_counter[0]}"
    n_steps = len(prog.trotter_layers)
    ND = spec.k + 2
    sync = set(spec.syndrome_steps(n_steps))
    _RC_REG[tag] = {"prep": prog.prep, "synZ": spec.syndrome_segment("Z"),
                    "synX": spec.syndrome_segment("X"), "trotter": prog.trotter_layers}
    N, A, F = spec.n_phys, spec.A, spec.F

    L = ["from guppylang import guppy",
         "from guppylang.std.builtins import array, comptime, result",
         "from guppylang.std.quantum import discard_array, project_z, qubit, reset",
         "from src.backends_qc import _RC_REG",
         f"_C = _RC_REG[{tag!r}]",
         f"prep_fn = guppy.load_pytket('prep_{tag}', _C['prep'])",
         f"synz_fn = guppy.load_pytket('synz_{tag}', _C['synZ'])",
         f"synx_fn = guppy.load_pytket('synx_{tag}', _C['synX'])"]
    for i in range(n_steps):
        L.append(f"trot_fn_{i} = guppy.load_pytket('trot_{tag}_{i}', _C['trotter'][{i}])")

    def maybe_not(var: str, flip: int) -> None:
        if flip:
            L.append(f"    {var} = not {var}")

    L += ["", "@guppy", "def main() -> None:",
          f"    q = array(qubit() for _ in range(comptime({N})))",
          "    synz_fn(q)", f"    sz = project_z(q[comptime({A})]).read()"]
    maybe_not("sz", prog.round0_flip[0])
    L.append(f"    fz = project_z(q[comptime({F})]).read()")
    maybe_not("fz", prog.round0_flip[1])
    L += [f"    reset(q[comptime({A})])", f"    reset(q[comptime({F})])", "    synx_fn(q)",
          f"    sx_ref = project_z(q[comptime({A})]).read()"]
    maybe_not("sx_ref", prog.round0_flip[2])
    L.append(f"    fx = project_z(q[comptime({F})]).read()")
    maybe_not("fx", prog.round0_flip[3])
    L += [f"    reset(q[comptime({A})])", f"    reset(q[comptime({F})])",
          "    result('sz', sz)", "    result('fz', fz)",
          "    result('sx', sx_ref)", "    result('fx', fx)",
          "    ok = not (sz or fz or fx)", "    sz_prev = sz",
          "    if ok:", "        prep_fn(q)"]
    for s in range(1, n_steps + 1):
        L += ["    if ok:", f"        trot_fn_{s - 1}(q)"]
        if s in sync:
            fza, ffz, fsx, ffx = prog.round_flip[s]
            L += ["        synz_fn(q)", f"        sz2 = project_z(q[comptime({A})]).read()"]
            if fza:
                L.append("        sz2 = not sz2")
            L.append(f"        fz2 = project_z(q[comptime({F})]).read()")
            if ffz:
                L.append("        fz2 = not fz2")
            L += [f"        reset(q[comptime({A})])", f"        reset(q[comptime({F})])",
                  "        synx_fn(q)", f"        sx2 = project_z(q[comptime({A})]).read()"]
            if fsx:
                L.append("        sx2 = not sx2")
            L.append(f"        fx2 = project_z(q[comptime({F})]).read()")
            if ffx:
                L.append("        fx2 = not fx2")
            L += [f"        reset(q[comptime({A})])", f"        reset(q[comptime({F})])",
                  "        result('sz', sz2)", "        result('fz', fz2)",
                  "        result('sx', sx2)", "        result('fx', fx2)",
                  "        if fz2 or fx2 or sz2 != sz_prev or sx2 != sx_ref:",
                  "            ok = False", "        sz_prev = sz2"]
    L.append("    par = False")
    for i in range(ND):
        L.append(f"    bit{i} = project_z(q[{i}]).read()")
        if prog.final_flip[i]:
            L.append(f"    bit{i} = not bit{i}")
        L.append(f"    result('d', bit{i})")
        L.append(f"    par = par != bit{i}")
    L += ["    result('accepted', ok and par == sz_prev)", "    discard_array(q)", ""]

    d = tempfile.mkdtemp(prefix="guppy_rc_")
    path = os.path.join(d, f"prog_{tag}.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    modspec = importlib.util.spec_from_file_location(f"prog_{tag}", path)
    mod = importlib.util.module_from_spec(modspec)
    modspec.loader.exec_module(mod)
    return mod.main


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
def _nexus_preflight(spec: IcebergTFIM, n_steps: int, shots: int, *, allow_hardware: bool,
                     approval: Optional[str], max_cost_hqc: float,
                     device: Optional[str]) -> None:
    """Enforce SCOPE §5's double gate and the spending cap BEFORE anything could be submitted.

    Raises on the first unmet condition, so a caller can never reach a submission by accident.
    This runs even though `run()` then raises NotImplementedError, because the gate is the part
    that must be correct and tested now: the submission call itself needs a Nexus login, a device
    identifier and the Guppy/HUGR submission route confirmed against live documentation
    (docs/nexus_toggle.md items 3-5, all still [unverified]), none of which can be exercised here.

    On success it PRINTS the cost ceiling and job shape it would submit under, so the number is on
    the record before the spend, not after it (docs/nexus_toggle.md item 6).
    """
    if not allow_hardware:
        raise PermissionError(
            "nexus backend refused: HardwareConfig.allow_hardware is False. Nothing will be "
            "submitted. Set it consciously (SCOPE §5) -- it is not a default.")
    if approval != NEXUS_APPROVAL:
        raise PermissionError(
            "nexus backend refused: missing the per-run approval token. Pass "
            f"approval={NEXUS_APPROVAL!r} for THIS run. allow_hardware alone is not enough: "
            "SCOPE §5 requires both, so that no loop or retry can spend credits unattended.")
    if not max_cost_hqc or max_cost_hqc <= 0:
        raise ValueError(
            "nexus backend refused: HardwareConfig.max_cost_hqc must be a positive HQC ceiling. "
            "It is passed to pytket-quantinuum as `max_cost`, which the backend enforces "
            "server-side. There is no 'unlimited' value by design.")
    if not device:
        raise ValueError("nexus backend refused: no device name given (HardwareConfig.device).")
    n_phys = spec.n_phys
    if n_phys > H2_N_QUBITS:
        raise ValueError(
            f"nexus backend refused: the encoded program needs {n_phys} physical qubits, but H2 "
            f"has {H2_N_QUBITS}. Choose a smaller lattice (DECISIONS.md OPEN-2).")
    print(f"[nexus preflight] device={device!r} qubits={n_phys}/{H2_N_QUBITS} steps={n_steps} "
          f"shots={shots} max_cost={max_cost_hqc} HQC (server-enforced ceiling); "
          "approval token accepted.")


def run(spec: IcebergTFIM, n_steps: int, shots: int, noise: Noise, backend: str, seed: int,
        max_spins: int, rc: bool = False, rc_instances: int = 1,
        rc_seed: Optional[int] = None, allow_hardware: bool = False,
        approval: Optional[str] = None, max_cost_hqc: float = 0.0,
        device: Optional[str] = None) -> List[ShotRecord]:
    """Execute the encoded program for `n_steps` Trotter steps and return per-shot records.

    `rc` is the randomized-compiling switch (EncodedConfig.rc, DECISIONS.md OPEN-3), OFF by
    default; with it off this function behaves exactly as before. With it on, the `shots`
    budget is DIVIDED over `rc_instances` independent twirled instances and their records are
    pooled into the single returned list -- randomized compiling spreads a fixed shot budget
    over randomizations, it does not grant extra shots. Under this project's Pauli noise models
    the pooled result reproduces the untwirled prediction (tests/test_twirl.py); the switch
    exists so the H2 emulator can be driven with randomized-compiled circuits, which is where
    it actually does something, since real hardware noise is not already Pauli.
    """
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; choose one of {BACKENDS}")
    if backend == "nexus":
        # CLAUDE.md promises `nexus` is "a stub that raises NotImplementedError", so a plain call
        # keeps doing exactly that. The gate's specific refusals are for a caller who is actually
        # reaching for hardware -- i.e. who supplied any hardware argument. Either way nothing is
        # submitted; this only decides which refusal is the more informative one.
        if allow_hardware or approval is not None or max_cost_hqc or device is not None:
            _nexus_preflight(spec, n_steps, shots, allow_hardware=allow_hardware,
                             approval=approval, max_cost_hqc=max_cost_hqc, device=device)
        raise NotImplementedError(NEXUS_MSG)
    if rc and rc_instances < 1:
        raise ValueError(f"rc_instances must be >= 1, got {rc_instances}")
    check_physical_ceiling(spec.n_phys, max_spins)        # before any allocation
    if rc:
        if rc_instances > shots:
            raise ValueError(f"rc_instances ({rc_instances}) exceeds shots ({shots}): each "
                             "instance would get zero shots")
        per = shots // rc_instances
        extra = shots - per * rc_instances                # hand out the remainder, lose nothing
        rcs = seed if rc_seed is None else rc_seed
        if backend == "local-sim":
            batches = run_twirled(spec, n_steps, per, noise, seed, max_spins, rcs, rc_instances,
                                  extra_shots=extra)
            return [r for batch in batches for r in batch]
        return _run_selene_twirled(spec, n_steps, per, extra, noise, seed, max_spins, rcs,
                                   rc_instances)
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


def _run_selene_twirled(spec: IcebergTFIM, n_steps: int, per: int, extra: int, noise: Noise,
                        seed: int, max_spins: int, rc_seed: int,
                        n_instances: int) -> List[ShotRecord]:
    """Selene emulator execution of `n_instances` twirled instances, records pooled."""
    from selene_sim import DepolarizingErrorModel, Quest
    if noise.p_idle:
        raise ValueError("selene's DepolarizingErrorModel has no idle term; set p_idle = 0")
    rc_children = np.random.SeedSequence(rc_seed).spawn(n_instances)
    noise_children = np.random.SeedSequence(seed).spawn(n_instances)
    out: List[ShotRecord] = []
    for i, (rc_child, noise_child) in enumerate(zip(rc_children, noise_children)):
        shots_i = per + (1 if i < extra else 0)
        if shots_i == 0:
            continue
        prog = twirl_program(spec, n_steps, rc_child)
        main_fn = build_guppy_program_twirled(spec, prog)
        ns = int(noise_child.generate_state(1, dtype=np.uint32)[0])
        em = DepolarizingErrorModel(random_seed=ns, p_1q=noise.p1, p_2q=noise.p2,
                                    p_meas=noise.pm, p_init=noise.p_init)
        res = (main_fn.emulator(n_qubits=spec.n_phys).with_shots(shots_i)
               .with_simulator(Quest()).with_seed(ns).with_error_model(em).run())
        out.extend(_parse_selene(s.entries) for s in res.results)
    return out


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
