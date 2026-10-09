"""Flagged fault-tolerant syndrome gadget for the concatenated Iceberg code (handoff/01).

[derived construction — verified numerically below, see docs/concatenated_iceberg_d4.md]

Memory experiment on any CSS code given as ordered stabilizer supports (here the
ConcatenatedIceberg [[16,4,4]] by default):

  prep      all data in |0> (basis "Z") or |+> (basis "X")
  rounds    each round measures, in order: inner S_Z, inner S_X, outer S_Z, outer S_X
            Each stabilizer uses ONE syndrome ancilla + ONE flag qubit
            (Chao & Reichardt, "Quantum error correction with only two extra
            qubits", Phys. Rev. Lett. 121, 050502 (2018), arXiv:1705.02329; the
            syndrome ancilla + flag ARE those "two extra qubits", and §V applies
            the technique to the [[n,n-2,2]] Iceberg family itself):
              Z-type: anc |0>, flag |+>;  CX(d0->anc) CX(flag->anc) CX(d1..d_{w-2}->anc)
                      CX(flag->anc) CX(d_{w-1}->anc); measure anc in Z, flag in X.
              X-type: anc |+>, flag |0>;  CX(anc->d0) CX(anc->flag) CX(anc->d1..)
                      CX(anc->flag) CX(anc->d_{w-1}); measure anc in X, flag in Z.
            Physical meaning of the flag: a single fault on the shared ancilla in
            the middle of the CNOT ladder would copy onto several data qubits at
            once (a "hook" error of weight > 1 from just one fault), which could
            masquerade as a logical fault and defeat the distance. The flag qubit
            is entangled with the ancilla by the two bracketing flag CNOTs so that
            exactly those dangerous mid-ladder ancilla faults also flip the flag;
            the flag detector then marks the shot for discard. The CNOT ORDER
            above is therefore load-bearing, not cosmetic.
            An ancilla fault between the two flag CNOTs (the only place it can spread
            to >= 2 data qubits) also flips the flag.
  readout   transversal data measurement in the memory basis; stabilizers of that
            type and the logicals of that type are rebuilt from it.

Detectors (all deterministic on a clean run):
  - every flag outcome;
  - stabilizer outcome XOR its previous-round outcome (round 0: only stabilizers
    of the memory-basis type, which are deterministic after prep);
  - final data parity on each memory-basis stabilizer XOR its last-round outcome.
Observables: every memory-basis logical (k of them).

DISCARD PREDICATE (cross-level): a shot is kept iff NO detector fires — inner
syndrome change, outer syndrome change, or any flag. This is pure error
detection at both levels; no decoding/correction is attempted. Rationale for
"any detector": with detection-only (no correction) a code of distance d
guarantees that every undetectable residual error has weight >= d; the moment
ANY level signals (inner stabilizer, outer stabilizer, or a flag catching a hook)
we can no longer certify that bound, so the only safe move is to throw the shot
away. Keeping a shot that fired an inner detector but not an outer one would
reintroduce exactly the correlated/hook errors the two-level scheme is built to
reject. The price is a nonzero discard rate; the payoff is a post-selected
logical error rate set by the full d=4 distance.

`fault_distance` measures the minimum number of circuit faults (DEM error
mechanisms) that flip a logical observable while firing no detector, by exact
search up to 3 faults. Nothing here touches hardware.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import stim

from src.qec.concatenated import ConcatenatedIceberg


@dataclass
class NoiseModel:
    """Uniform circuit-level depolarizing model (QECConfig docstring). p=0 -> noiseless."""

    p: float = 0.0
    p1_ratio: float = 0.1
    pm_ratio: float = 1.0
    idle_ratio: float = 0.1
    p2_ratio: float = 1.0   # 0 + idle_ratio=1 gives a code-capacity (data-only) model

    @property
    def p2(self) -> float:
        return self.p * self.p2_ratio

    @property
    def p1(self) -> float:
        return self.p * self.p1_ratio

    @property
    def pm(self) -> float:
        return self.p * self.pm_ratio

    @property
    def pidle(self) -> float:
        return self.p * self.idle_ratio

    @classmethod
    def from_config(cls, qec, p: float) -> "NoiseModel":
        return cls(p=p, p1_ratio=qec.p1_ratio, pm_ratio=qec.pm_ratio, idle_ratio=qec.idle_ratio)


@dataclass
class CSSSpec:
    """CSS code as ORDERED supports; order = CNOT schedule of each measurement."""

    n: int
    x_stabs: List[List[int]]
    z_stabs: List[List[int]]
    x_logicals: List[List[int]]
    z_logicals: List[List[int]]
    # stabilizer groups measured in sequence each round: (label, type, indices)
    groups: List[Tuple[str, str, List[int]]] = field(default_factory=list)

    @classmethod
    def from_concatenated(cls, code: ConcatenatedIceberg) -> "CSSSpec":
        no, ki = code.n_outer, code.k_inner
        inner, outer = list(range(no)), list(range(no, no + ki))
        return cls(
            n=code.n,
            x_stabs=code.x_stabilizer_supports(),
            z_stabs=code.z_stabilizer_supports(),
            x_logicals=[code.logical_support("X", a, i)
                        for a in range(ki) for i in range(code.k_outer)],
            z_logicals=[code.logical_support("Z", a, i)
                        for a in range(ki) for i in range(code.k_outer)],
            groups=[("inner", "Z", inner), ("inner", "X", inner),
                    ("outer", "Z", outer), ("outer", "X", outer)],
        )


@dataclass
class GadgetCircuit:
    circuit: stim.Circuit
    detector_labels: List[str]   # "flag" | "inner" | "outer" per detector index


class _Builder:
    """Appends noisy operations and tracks the measurement record index."""

    def __init__(self, n_data: int, noise: NoiseModel):
        self.c = stim.Circuit()
        self.noise = noise
        self.n_data = n_data
        self.anc, self.flag = n_data, n_data + 1
        self.n_meas = 0
        self.labels: List[str] = []

    # --- noisy primitives ---
    def reset(self, qs):
        self.c.append("R", qs)
        if self.noise.pm:
            self.c.append("X_ERROR", qs, self.noise.pm)

    def h(self, qs):
        self.c.append("H", qs)
        if self.noise.p1:
            self.c.append("DEPOLARIZE1", qs, self.noise.p1)

    def cx(self, ctrl, tgt):
        self.c.append("CX", [ctrl, tgt])
        if self.noise.p2:
            self.c.append("DEPOLARIZE2", [ctrl, tgt], self.noise.p2)

    def measure(self, q) -> int:
        if self.noise.pm:
            self.c.append("X_ERROR", [q], self.noise.pm)
        self.c.append("M", [q])
        self.n_meas += 1
        return self.n_meas - 1

    def idle(self):
        if self.noise.pidle:
            self.c.append("DEPOLARIZE1", list(range(self.n_data)), self.noise.pidle)

    def detector(self, meas: Sequence[int], label: str):
        self.c.append("DETECTOR", [stim.target_rec(m - self.n_meas) for m in meas])
        self.labels.append(label)

    # --- flagged stabilizer measurement ---
    def measure_stabilizer(self, ptype: str, support: List[int], use_flag: bool) -> Tuple[int, Optional[int]]:
        a, f = self.anc, self.flag
        w = len(support)
        flagged = use_flag and w >= 3   # weight <= 2 hooks are single-qubit up to the stabilizer
        self.reset([a, f] if flagged else [a])
        if ptype == "X":
            self.h([a])
        elif flagged:
            self.h([f])

        def data_cx(q):
            self.cx(a, q) if ptype == "X" else self.cx(q, a)

        def flag_cx():
            self.cx(a, f) if ptype == "X" else self.cx(f, a)

        for idx, q in enumerate(support):
            data_cx(q)
            if flagged and idx in (0, w - 2):
                flag_cx()
        if ptype == "X":
            self.h([a])
        elif flagged:
            self.h([f])
        m_a = self.measure(a)
        m_f = self.measure(f) if flagged else None
        return m_a, m_f


def build_memory_circuit(
    spec: CSSSpec,
    basis: str = "Z",
    rounds: int = 2,
    noise: Optional[NoiseModel] = None,
    use_flags: bool = True,
    inject: Optional[List[Tuple[str, int]]] = None,
    inject_after_round: int = 0,
) -> GadgetCircuit:
    """Memory experiment circuit (see module docstring).

    `inject` = list of (pauli, data_qubit) probability-1 errors applied after round
    `inject_after_round` (code-capacity checks on an otherwise noiseless circuit).
    """
    if basis not in ("X", "Z"):
        raise ValueError("basis must be 'X' or 'Z'")
    if rounds < 1:
        raise ValueError("rounds >= 1")
    noise = noise or NoiseModel()
    b = _Builder(spec.n, noise)
    data = list(range(spec.n))

    b.reset(data)
    if basis == "X":
        b.h(data)

    stabs = {"X": spec.x_stabs, "Z": spec.z_stabs}
    prev: Dict[Tuple[str, int], int] = {}
    for r in range(rounds):
        for label, ptype, idxs in spec.groups:
            b.idle()
            for s in idxs:
                m_a, m_f = b.measure_stabilizer(ptype, stabs[ptype][s], use_flags)
                if m_f is not None:
                    b.detector([m_f], "flag")
                key = (ptype, s)
                if key in prev:
                    b.detector([prev[key], m_a], label)
                elif ptype == basis:
                    b.detector([m_a], label)
                prev[key] = m_a
        if inject and r == inject_after_round:
            chan = {"X": "X_ERROR", "Y": "Y_ERROR", "Z": "Z_ERROR"}
            for pauli, q in inject:
                b.c.append(chan[pauli], [q], 1.0)

    # transversal readout in the memory basis
    if basis == "X":
        b.h(data)
    m_data = [b.measure(q) for q in data]
    for label, ptype, idxs in spec.groups:
        if ptype != basis:
            continue
        for s in idxs:
            b.detector([m_data[q] for q in stabs[ptype][s]] + [prev[(ptype, s)]], label)
    logicals = spec.z_logicals if basis == "Z" else spec.x_logicals
    for L, supp in enumerate(logicals):
        b.c.append("OBSERVABLE_INCLUDE", [stim.target_rec(m_data[q] - b.n_meas) for q in supp], L)
    return GadgetCircuit(b.c, b.labels)


def discard(detection_events: np.ndarray) -> np.ndarray:
    """Cross-level discard predicate: discard a shot iff ANY detector fired."""
    return np.asarray(detection_events).any(axis=-1)


# --------------------------------------------------------------------------- #
# Code-capacity check through the actual circuit
# --------------------------------------------------------------------------- #
def injected_signature(spec: CSSSpec, basis: str, errors: List[Tuple[str, int]], rounds: int = 2):
    """(detectors, observables) bit arrays for a deterministic injected data error."""
    gc = build_memory_circuit(spec, basis, rounds, inject=errors)
    det, obs = gc.circuit.compile_detector_sampler().sample(1, separate_observables=True)
    return det[0], obs[0]


def undetected_low_weight_errors(spec: CSSSpec, max_weight: int = 3, rounds: int = 2):
    """All nonidentity data Paulis of weight <= max_weight that fire NO detector in
    either memory basis. Signatures of single-qubit X/Z errors are taken from the
    real Stim circuits; multi-qubit signatures follow by XOR (Pauli-frame linearity).
    Returns a list of offending Pauli strings (empty == all detected)."""
    sig: Dict[Tuple[str, int], int] = {}
    for q in range(spec.n):
        for p in ("X", "Z"):
            acc = 0
            for basis in ("Z", "X"):
                det, _ = injected_signature(spec, basis, [(p, q)], rounds)
                acc = (acc << len(det)) | int("".join("1" if v else "0" for v in det) or "0", 2)
            sig[(p, q)] = acc
    single = {}
    for q in range(spec.n):
        single[(q, "X")] = sig[("X", q)]
        single[(q, "Z")] = sig[("Z", q)]
        single[(q, "Y")] = sig[("X", q)] ^ sig[("Z", q)]
    bad = []
    for w in range(1, max_weight + 1):
        for qs in combinations(range(spec.n), w):
            for ps in np.ndindex(*(3,) * w):
                s = 0
                for q, pi in zip(qs, ps):
                    s ^= single[(q, "XYZ"[pi])]
                if s == 0:
                    bad.append("".join(f"{'XYZ'[pi]}{q} " for q, pi in zip(qs, ps)).strip())
    return bad


# --------------------------------------------------------------------------- #
# Circuit-level fault distance (exact search on the detector error model)
# --------------------------------------------------------------------------- #
def _dem_mechanisms(circuit: stim.Circuit) -> List[Tuple[int, int]]:
    dem = circuit.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
    mechs = []
    for inst in dem.flattened():
        if inst.type != "error":
            continue
        d = o = 0
        for t in inst.targets_copy():
            if t.is_relative_detector_id():
                d ^= 1 << t.val
            elif t.is_logical_observable_id():
                o ^= 1 << t.val
        mechs.append((d, o))
    return mechs


def fault_distance(circuit: stim.Circuit, max_faults: int = 3) -> Optional[int]:
    """Least number of DEM error mechanisms whose combined effect fires no detector
    but flips >= 1 logical observable. Exact for 1..max_faults (max 3); returns
    None if no such combination exists up to max_faults (fault distance > max_faults).

    Physical meaning: this is the CIRCUIT fault distance (minimum number of faulty
    physical operations that cause an undetected logical error), as opposed to the
    noiseless CODE distance in concatenated.code_distance (minimum WEIGHT of an
    undetected logical Pauli on the data). Fault tolerance to t faults needs fault
    distance >= 2t+1 for correction, or >= t+1 for detection-only post-selection.
    With flags the gadget reaches None up to 3 (fault distance > 3, matching the
    d=4 code); WITHOUT flags it collapses to 2, because a single mid-ladder ancilla
    fault spreads into a weight-2 hook that escapes detection — the quantitative
    statement of why the flag qubits are required, not optional.
    """
    if max_faults > 3:
        raise ValueError("exact search implemented up to 3 faults")
    mechs = _dem_mechanisms(circuit)
    if any(d == 0 and o for d, o in mechs):
        return 1
    if max_faults < 2:
        return None
    by_det: Dict[int, List[Tuple[int, int]]] = {}
    for i, (d, o) in enumerate(mechs):
        by_det.setdefault(d, []).append((i, o))
    for lst in by_det.values():
        obs = {o for _, o in lst}
        if len(obs) > 1:
            return 2
    if max_faults < 3:
        return None
    M = len(mechs)
    for i in range(M):
        di, oi = mechs[i]
        for j in range(i + 1, M):
            dj, oj = mechs[j]
            for k, ok in by_det.get(di ^ dj, ()):
                if k != i and k != j and (oi ^ oj ^ ok):
                    return 3
    return None


# --------------------------------------------------------------------------- #
# Sampling: discard (post-selection) rate and post-selected logical error rate
# --------------------------------------------------------------------------- #
def _wilson(k: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    ph = k / n
    den = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / den
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


@dataclass
class SampleResult:
    basis: str
    p: float
    shots: int
    kept: int
    logical_errors: int          # among kept shots, any observable flipped
    discard_by_label: Dict[str, int]

    @property
    def discard_rate(self) -> float:
        return 1 - self.kept / self.shots

    @property
    def discard_ci(self) -> Tuple[float, float]:
        return _wilson(self.shots - self.kept, self.shots)

    @property
    def logical_rate(self) -> float:
        return self.logical_errors / self.kept if self.kept else float("nan")

    @property
    def logical_ci(self) -> Tuple[float, float]:
        return _wilson(self.logical_errors, self.kept)


def sample(gc: GadgetCircuit, basis: str, p: float, shots: int, seed: int) -> SampleResult:
    sampler = gc.circuit.compile_detector_sampler(seed=seed)
    det, obs = sampler.sample(shots, separate_observables=True)
    drop = discard(det)
    keep = ~drop
    labels = np.array(gc.detector_labels)
    by_label = {lab: int(det[:, labels == lab].any(axis=1).sum()) for lab in sorted(set(labels))}
    return SampleResult(
        basis=basis, p=p, shots=shots, kept=int(keep.sum()),
        logical_errors=int(obs[keep].any(axis=1).sum()), discard_by_label=by_label,
    )
