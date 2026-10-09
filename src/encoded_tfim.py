"""Iceberg-encoded square-TFIM Trotter circuit (handoff/04 Part A).

One logical square lattice (Lx x Ly, k = Lx*Ly logical qubits, k even) lives in ONE Iceberg
[[k+2, k, 2]] block (arXiv:2211.06703; src/qec/iceberg.py layout: data 0..k-1, top t = k,
bottom b = k+1), plus one syndrome ancilla A = k+2 and one flag F = k+3:
    n_phys = k + 4.

Authored form = pytket segment circuits (the single source of truth). The same segments are
  - executed by `backends_qc` (local-sim interprets them command by command; selene loads them
    into a Guppy program with mid-circuit measurement / reset / feedforward discard), and
  - translated to Stim here for VERIFICATION (fault injection), never for execution.

Logical gates [derived; transparency is checked in tests against the bare simulate_z2]:
  exp(-i phi Zbar_i Zbar_j) = exp(-i phi Z_i Z_j)          (Zbar_i Zbar_j = Z_b Z_i Z_b Z_j)
  exp(-i phi Xbar_i)        = exp(-i phi X_t X_i)
  logical ry(theta) on i    = Sbar Rxbar(theta) Sbar^dag, Sbar = exp(-i pi/4 Z_b Z_i)
All are single two-qubit Pauli rotations commuting with S_X = X^n and S_Z = Z^n; each is ONE
ZZPhase (XX rotations conjugated by H on both qubits; see _pp).
The Trotter step is the Q1 harness's circuit-order Strang step (src/compare.py):
  field half-layer exp(+i h dt/2 Xbar_i) -> bonds exp(+i J dt Zbar_i Zbar_j) -> field half-layer.

Syndrome round = flagged S_Z then flagged S_X (Chao-Reichardt single flag, same pattern as
src/qec/concatenated_gadget.py, rebuilt here as pytket segments). Discard rule (QED): a shot is
kept iff every flag reads 0, every S_Z equals the previous S_Z (round 0 reference = 0 because
|0^n> is +1 for S_Z), every S_X equals the round-0 S_X (random, used as the reference), and
the final data parity equals the last S_Z.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import stim
from pytket import Circuit, OpType

from src.backends import MemoryCeilingError
from src.lattice import square_bonds


# --------------------------------------------------------------------------- #
# Spec and authored segments
# --------------------------------------------------------------------------- #
@dataclass
class IcebergTFIM:
    Lx: int
    Ly: int
    boundary: str
    J: float
    h: float
    dt: float
    theta: float
    syndrome_every: int = 1

    def __post_init__(self) -> None:
        self.k = self.Lx * self.Ly
        if self.k < 2 or self.k % 2:
            raise ValueError(f"Iceberg needs an even number of logical qubits (got {self.k})")
        if self.syndrome_every < 1:
            raise ValueError("syndrome_every >= 1")
        self.bonds = square_bonds(self.Lx, self.Ly, self.boundary)
        self.t, self.b = self.k, self.k + 1
        self.A, self.F = self.k + 2, self.k + 3
        self.data = list(range(self.k + 2))          # all code qubits (S_X / S_Z support)

    @property
    def n_phys(self) -> int:
        return self.k + 4

    # -- rotation helper: exp(-i phi P P) in pytket half-turns -------------------
    @staticmethod
    def _pp(c: Circuit, pauli: str, a: int, b: int, phi: float) -> None:
        """exp(-i phi P_a P_b). ZZPhase(alpha) = exp(-i pi alpha/2 ZZ); an XX rotation is
        authored as H.H ZZPhase H.H because the Selene HUGR-QIS compiler (selene-sim 0.3.4)
        rejects pytket XXPhase; ZZ is also H2's native entangler. Same operator, 4 extra H."""
        alpha = 2.0 * phi / np.pi
        if pauli == "Z":
            c.ZZPhase(alpha, a, b)
        else:
            c.H(a); c.H(b)
            c.ZZPhase(alpha, a, b)
            c.H(a); c.H(b)

    def prep_segment(self) -> Circuit:
        """Logical ry(theta) on every logical qubit (applied after the round-0 syndrome)."""
        c = Circuit(self.n_phys)
        for i in range(self.k):
            self._pp(c, "Z", self.b, i, -np.pi / 4)   # Sbar^dag
            self._pp(c, "X", self.t, i, self.theta / 2)   # Rxbar(theta) = exp(-i theta/2 Xbar)
            self._pp(c, "Z", self.b, i, +np.pi / 4)   # Sbar
        return c

    def trotter_segment(self) -> Circuit:
        """One circuit-order Strang step on the logical lattice."""
        c = Circuit(self.n_phys)
        phx = -self.h * self.dt / 2                    # exp(-i B dt/2), B = -h sum Xbar
        phz = -self.J * self.dt                        # exp(-i A dt),   A = -J sum ZbarZbar
        for i in range(self.k):
            self._pp(c, "X", self.t, i, phx)
        for i, j in self.bonds:
            self._pp(c, "Z", i, j, phz)
        for i in range(self.k):
            self._pp(c, "X", self.t, i, phx)
        return c

    def syndrome_segment(self, kind: str) -> Circuit:
        """Flagged measurement of S_Z ("Z") or S_X ("X"); measure A then F in Z afterwards."""
        c = Circuit(self.n_phys)
        A, F, d = self.A, self.F, self.data
        w = len(d)
        if kind == "Z":
            c.H(F)
            for idx, q in enumerate(d):
                c.CX(q, A)
                if idx in (0, w - 2):
                    c.CX(F, A)
            c.H(F)
        else:
            c.H(A)
            for idx, q in enumerate(d):
                c.CX(A, q)
                if idx in (0, w - 2):
                    c.CX(A, F)
            c.H(A)
        return c

    def syndrome_steps(self, n_steps: int) -> List[int]:
        """Steps after which a syndrome round runs: every `syndrome_every`, and always the last."""
        s = [x for x in range(1, n_steps + 1) if x % self.syndrome_every == 0]
        if n_steps >= 1 and (not s or s[-1] != n_steps):
            s.append(n_steps)
        return s

    def logical_from_bits(self, bits: np.ndarray) -> np.ndarray:
        """Zbar_i = Z_b Z_i eigenvalue (+-1) per shot from final data bits (shots, k+2)."""
        bits = np.asarray(bits, dtype=np.int8)
        return 1 - 2 * (bits[:, :self.k] ^ bits[:, [self.b]])


def check_physical_ceiling(n_phys: int, max_spins: int) -> None:
    """Refuse a state-vector execution whose PHYSICAL register (code + ancilla + flag) is over
    the SCOPE §5 ceiling, before anything is allocated."""
    if n_phys > max_spins:
        raise MemoryCeilingError(
            f"encoded run needs {n_phys} physical qubits (code + syndrome ancillas); the "
            f"state-vector ceiling is {max_spins} (SCOPE §5). Use a smaller logical lattice."
        )


# --------------------------------------------------------------------------- #
# Classical post-processing shared by every backend
# --------------------------------------------------------------------------- #
@dataclass
class ShotRecord:
    """Raw per-shot outcomes in program order: rounds = [(sz, fz, sx, fx), ...]; final bits."""

    rounds: List[Tuple[int, int, int, int]]
    final: np.ndarray            # (k+2,) data bits


def accepted(rec: ShotRecord) -> bool:
    """The QED discard predicate (module docstring)."""
    sz_prev, sx_ref = 0, None
    for sz, fz, sx, fx in rec.rounds:
        if fz or fx:
            return False
        if sz != sz_prev:
            return False
        if sx_ref is None:
            sx_ref = sx
        elif sx != sx_ref:
            return False
        sz_prev = sz
    return int(np.bitwise_xor.reduce(rec.final)) == sz_prev


def z2_from_logical(zbar: np.ndarray) -> Tuple[float, float]:
    """Z2 = <(sum_i Zbar_i)^2>/k^2 over shots, with its standard error."""
    k = zbar.shape[1]
    m2 = (zbar.sum(axis=1).astype(float) ** 2) / k ** 2
    if len(m2) == 0:
        return float("nan"), float("nan")
    se = m2.std(ddof=1) / np.sqrt(len(m2)) if len(m2) > 1 else float("nan")
    return float(m2.mean()), float(se)


# --------------------------------------------------------------------------- #
# Stim translation (VERIFICATION only)
# --------------------------------------------------------------------------- #
@dataclass
class StimNoise:
    """Generic circuit-level depolarizing model (assumed rates, never H2-calibrated).
    `classes` selects which fault locations are noisy (for per-class FT accounting)."""

    p2: float = 0.0
    p1: float = 0.0
    pm: float = 0.0
    p_init: float = 0.0
    p_idle: float = 0.0
    classes: Tuple[str, ...] = ("rot", "cx", "h", "meas", "reset", "idle")


def _rot_to_stim(c: stim.Circuit, typ: OpType, alpha: float, a: int, b: int, mode: str) -> None:
    """PhasePP(alpha): 'identity' (exact for Pauli-fault propagation: a Pauli passes through
    exp(-i phi P) unchanged up to the sign of phi) or 'clifford' (alpha multiple of 1/2)."""
    if mode == "identity":
        return
    r = alpha % 4.0
    q = round(r * 2) / 2
    if abs(r - q) > 1e-9:
        raise ValueError(f"non-Clifford angle {alpha} half-turns in clifford mode")
    p = "ZZ" if typ == OpType.ZZPhase else "XX"
    # PhasePP(alpha) = exp(-i pi alpha/2 PP) equals SQRT_PP^(alpha/0.5) up to global phase
    seq = {0.0: [], 0.5: [f"SQRT_{p}"], 1.0: [f"SQRT_{p}"] * 2, 1.5: [f"SQRT_{p}_DAG"],
           2.0: [], 2.5: [f"SQRT_{p}"], 3.0: [f"SQRT_{p}"] * 2, 3.5: [f"SQRT_{p}_DAG"]}[q]
    for g in seq:
        c.append(g, [a, b])


def _segment_to_stim(c: stim.Circuit, seg: Circuit, noise: StimNoise, mode: str) -> None:
    on = set(noise.classes)
    for cmd in seg.get_commands():
        typ = cmd.op.type
        qs = [q.index[0] for q in cmd.qubits]
        if typ == OpType.H:
            c.append("H", qs)
            if noise.p1 and "h" in on:
                c.append("DEPOLARIZE1", qs, noise.p1)
        elif typ == OpType.CX:
            c.append("CX", qs)
            if noise.p2 and "cx" in on:
                c.append("DEPOLARIZE2", qs, noise.p2)
        elif typ in (OpType.ZZPhase, OpType.XXPhase):
            _rot_to_stim(c, typ, float(cmd.op.params[0]), qs[0], qs[1], mode)
            if noise.p2 and "rot" in on:
                c.append("DEPOLARIZE2", qs, noise.p2)
        else:
            raise ValueError(f"unexpected op {typ} in authored segment")


def build_stim(spec: IcebergTFIM, n_steps: int, basis: str = "Z", mode: str = "identity",
               noise: Optional[StimNoise] = None, readout: bool = True,
               inject: Optional[List[Tuple[int, str, int]]] = None) -> stim.Circuit:
    """Stim image of the encoded program.

    basis "Z": prep |0^n> (logical |0..0> after the round-0 S_X projection), Z readout,
               observables Zbar_i.  basis "X": prep |+^n>, X readout, observables Xbar_i
               (needed so Z-type logical faults are visible). In 'identity' mode the logical
               state stays a Zbar (resp. Xbar) eigenstate, so observables are deterministic.
    inject: [(after_step, pauli, qubit)] probability-1 errors after a Trotter segment.
    """
    noise = noise or StimNoise()
    on = set(noise.classes)
    c = stim.Circuit()
    n, A, F, d = spec.n_phys, spec.A, spec.F, spec.data
    meas = 0
    dets: List[Tuple[int, ...]] = []

    def m(q):
        nonlocal meas
        if noise.pm and "meas" in on:
            c.append("X_ERROR", [q], noise.pm)
        c.append("M", [q])
        meas += 1
        return meas - 1

    def reset(qs):
        c.append("R", qs)
        if noise.p_init and "reset" in on:
            c.append("X_ERROR", qs, noise.p_init)

    def idle():
        if noise.p_idle and "idle" in on:
            c.append("DEPOLARIZE1", d, noise.p_idle)

    def det(ms):
        c.append("DETECTOR", [stim.target_rec(x - meas) for x in ms])

    reset(list(range(n)))
    if basis == "X":
        c.append("H", d)                                  # |+^n>: S_X = +1 deterministic
    prev = {"Z": None, "X": None}

    def round_():
        for kind in ("Z", "X"):
            _segment_to_stim(c, spec.syndrome_segment(kind), noise, mode)
            ma, mf = m(A), m(F)
            det([mf])
            deterministic = (kind == "Z") if basis == "Z" else (kind == "X")
            if prev[kind] is not None:
                det([prev[kind], ma])
            elif deterministic:
                det([ma])
            prev[kind] = ma
            reset([A, F])
        idle()

    round_()
    # logical ry(theta) prep: its gates carry noise in every mode; in 'identity' mode they act
    # as identity (logical state stays an eigenstate of the readout-basis logicals)
    _segment_to_stim(c, spec.prep_segment(), noise, mode)
    sync = set(spec.syndrome_steps(n_steps))
    for s in range(1, n_steps + 1):
        _segment_to_stim(c, spec.trotter_segment(), noise, mode)
        idle()
        for (after, p, q) in inject or []:
            if after == s:
                c.append({"X": "X_ERROR", "Y": "Y_ERROR", "Z": "Z_ERROR"}[p], [q], 1.0)
        if s in sync:
            round_()
    if not readout:
        return c
    if basis == "X":
        c.append("H", d)
    fin = [m(q) for q in d]
    det(fin + [prev[basis]])                                # final parity vs last S_basis
    for i in range(spec.k):
        anchor = spec.b if basis == "Z" else spec.t
        c.append("OBSERVABLE_INCLUDE", [stim.target_rec(fin[i] - meas),
                                        stim.target_rec(fin[anchor] - meas)], i)
    return c


def stim_exact_logical_z2(spec: IcebergTFIM, n_steps: int, seed: int = 0) -> float:
    """Exact clean-run logical Z2 of the CLIFFORD-angle instance via Stim's tableau simulator
    (consistency check only). Requires every rotation angle to be a multiple of 1/2 half-turn."""
    c = build_stim(spec, n_steps, basis="Z", mode="clifford", readout=False)
    sim = stim.TableauSimulator(seed=seed)
    sim.do(c)
    k = spec.k
    tot = float(k)
    for i in range(k):
        for j in range(k):
            if i != j:
                ps = stim.PauliString(spec.n_phys)
                ps[i] = "Z"
                ps[j] = "Z"                         # Zbar_i Zbar_j = Z_i Z_j
                tot += sim.peek_observable_expectation(ps)
    return tot / k ** 2


def single_fault_report(spec: IcebergTFIM, n_steps: int, p: float = 1e-3) -> Dict[str, dict]:
    """Per fault class: number of single-fault mechanisms that flip a logical observable while
    firing no detector, in both readout bases, plus the Pauli products responsible (Stim DEM +
    explain). Rotation gates are identity for propagation (exact; see _rot_to_stim)."""
    out: Dict[str, dict] = {}
    for cls in ("rot", "cx", "h", "meas", "reset", "idle"):
        noise = StimNoise(p2=p, p1=p, pm=p, p_init=p, p_idle=p, classes=(cls,))
        n_bad, paulis, n_mech = 0, set(), 0
        for basis in ("Z", "X"):
            circ = build_stim(spec, n_steps, basis=basis, noise=noise)
            dem = circ.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
            bad = stim.DetectorErrorModel()
            for inst in dem.flattened():
                if inst.type != "error":
                    continue
                n_mech += 1
                tg = inst.targets_copy()
                if not any(t.is_relative_detector_id() for t in tg) and any(t.is_logical_observable_id() for t in tg):
                    bad.append(inst)
            n_bad += len(bad)
            if len(bad):
                for e in circ.explain_detector_error_model_errors(dem_filter=bad, reduce_to_one_representative_error=False):
                    for loc in e.circuit_error_locations:
                        paulis.add("".join(f"{t.gate_target.pauli_type}{t.gate_target.value}" for t in loc.flipped_pauli_product))
        out[cls] = {"mechanisms": n_mech, "undetected_logical": n_bad, "paulis": sorted(paulis)}
    return out


def weight1_injection_all_detected(spec: IcebergTFIM, n_steps: int) -> Tuple[bool, List[str]]:
    """Every single-qubit X/Y/Z on every code qubit after every Trotter segment must fire a
    detector in the clean circuit (checked in both readout bases; Z-basis alone is blind to
    nothing here because S_X is measured every round)."""
    missed = []
    for s in range(1, n_steps + 1):
        for q in spec.data:
            for p in "XYZ":
                fired = False
                for basis in ("Z", "X"):
                    circ = build_stim(spec, n_steps, basis=basis, inject=[(s, p, q)])
                    dets = circ.compile_detector_sampler(seed=1).sample(4)
                    fired |= bool(dets.any(axis=1).all())
                if not fired:
                    missed.append(f"{p}{q}@step{s}")
    return len(missed) == 0, missed
