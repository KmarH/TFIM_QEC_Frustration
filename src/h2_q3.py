"""Q3 circuits for H2 (handoff/14, Phase 2): the frustrated triangular TFIM as ONE pytket circuit,
bare and Iceberg-encoded, the noise-scaling ladder, and the classical post-processing of the shots.

Shrunk to what the emulator can run (DECISIONS OPEN-4, decided 2026-10-17): the lambda ladder is built
at 3x4 (12 qubits bare), the size story at 3x6 (18); the 6x6 arm stays a Stim-only design. Conventions
are the repo's: H = -J sum ZZ - h sum X, circuit-order Strang step (X half, ZZ, X half) with
`src.backends_qc.bare_segments`' angles, row-major sites, qubit 0 = most significant bit, bit 1 =
spin -1. The Gauss-law post-selection is CLASSICAL, applied to the Z readout (`q3_observables`).

Everything here is offline and additive. A circuit from this module run on a classical emulator is a
prediction under whatever noise that emulator has; only a Nexus H2-1E/hardware run is an H2 result.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from pytket import Bit, Circuit, OpType

from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates, iceberg_code
from src.h2_circuits import CodesLayout, codes_h2_circuit
from src.lattice import triangular_bonds
from src.mcmc_baseline import Shells
from src.noise_scaling import fold_circuit, insert_paulis, prior_model
from src.noisy_q3 import make_iceberg
from src.trotter_threshold import observable_function

OBS_KEYS = ("flippable_density", "C1", "defect_density", "memory")


def _flat_spins(spins0, k: int) -> np.ndarray:
    s = np.asarray(spins0).reshape(-1)
    if len(s) != k or not np.all(np.abs(s) == 1):
        raise ValueError(f"spins0 must be {k} values of +-1, got shape {np.shape(spins0)}")
    return s


def triangular_bare_h2_circuit(
    Lx: int, Ly: int, spins0, n_steps: int, J: float, h: float, dt: float
) -> tuple[Circuit, list[Bit]]:
    """k = Lx*Ly qubits: X on every spin -1, `n_steps` Strang steps over the periodic triangular
    bonds, Z readout of qubit q into Bit("m", q)."""
    k = Lx * Ly
    s = _flat_spins(spins0, k)
    c = Circuit(k)
    for q in range(k):
        if s[q] < 0:
            c.X(q)
    ax = 2 * (-h * dt / 2) / np.pi  # exp(-i phi X) = Rx(2 phi / pi), as bare_segments
    az = 2 * (-J * dt) / np.pi
    bonds = triangular_bonds(Lx, Ly, "periodic")
    for _ in range(n_steps):
        for q in range(k):
            c.Rx(ax, q)
        for i, j in bonds:
            c.ZZPhase(az, i, j)
        for q in range(k):
            c.Rx(ax, q)
    m = c.add_c_register("m", k)
    for q in range(k):
        c.Measure(q, m[q])
    return c, [Bit("m", q) for q in range(k)]


def triangular_iceberg_h2_circuit(
    Lx: int, Ly: int, spins0, n_steps: int, J: float, h: float, dt: float
) -> tuple[Circuit, CodesLayout]:
    """The Iceberg-encoded program (src.noisy_q3.make_iceberg) as one circuit with mid-circuit
    syndrome measure/reset and the detectors in the layout. k must be even."""
    k = Lx * Ly
    if k % 2:
        raise ValueError(f"the Iceberg code needs an even number of logical qubits, got {k}")
    d = TriangularDimers(Lx, Ly)
    prog = make_iceberg(d, _flat_spins(spins0, k).reshape(Ly, Lx), J, h, dt)
    return codes_h2_circuit(prog, n_steps)


def bits_to_distribution(bits) -> np.ndarray:
    """(n_shots, N) 0/1 array -> the empirical probability vector of length 2**N (qubit 0 = MSB)."""
    b = np.asarray(bits)
    if b.ndim != 2 or b.shape[0] == 0:
        raise ValueError(f"expected a non-empty (n_shots, N) array, got shape {b.shape}")
    n = b.shape[1]
    idx = np.zeros(b.shape[0], dtype=np.int64)
    for j in range(n):
        idx = (idx << 1) | b[:, j].astype(np.int64)
    p = np.bincount(idx, minlength=1 << n).astype(np.float64)
    return p / p.sum()


def q3_observables(
    d: TriangularDimers, spins0, shells: Shells, p: np.ndarray, max_spins: int = 20
) -> dict:
    """{"raw": obs(p), "gauss": obs(p | defect-free initial-winding sector), "p_in": weight in the
    sector} -- the 'raw' / 'cond' / 'p_in' of src.noisy_q3.run_observables. gauss is nan if p_in = 0."""
    obs = observable_function(d, spins0, shells, max_spins=max_spins)
    i0 = d.product_state_index(np.asarray(spins0).reshape(d.Ly, d.Lx))
    wx, wy = d.winding_x(0), d.winding_y(0)
    mask = (d.total_defects() == 0) & (wx == wx[i0]) & (wy == wy[i0])
    p_in = float(p[mask].sum())

    def pick(r):
        return {k: r[k] for k in OBS_KEYS}

    raw = pick(obs(p))
    gauss = pick(obs(np.where(mask, p, 0.0) / p_in)) if p_in > 0 else {k: float("nan") for k in OBS_KEYS}
    return {"raw": raw, "gauss": gauss, "p_in": p_in}


@dataclass
class ScaledCircuit:
    lam: int
    method: str  # "none" (lam = 1), "insert" or "fold"
    instance: int
    circuit: Circuit


def default_model() -> dict:
    """The research/06 H2 prior Pauli channel (ASSUMED), as scripts/run_noise_scaling.py builds it."""
    S = CONFIG.sensitivity
    p1 = S.p2_prior * S.p1_ratio
    return prior_model(NoiseRates(p2=S.p2_prior, p1=p1, pm=p1, p_init=p1, zz_bias=S.zz_bias_prior))


def _split_measures(base: Circuit) -> tuple[Circuit, list[tuple[int, Bit]]]:
    """(measure-free body, [(qubit, bit)]) -- insert_paulis / fold_circuit rebuild a circuit with
    anonymous bits and raise on named registers, so they act on the body only."""
    body = Circuit(base.n_qubits)
    meas = []
    measured: set[int] = set()
    for cmd in base.get_commands():
        if cmd.op.type == OpType.Measure:
            meas.append((cmd.qubits[0].index[0], cmd.bits[0]))
            measured.add(cmd.qubits[0].index[0])
        else:
            if measured & {q.index[0] for q in cmd.qubits}:
                raise ValueError("noise scaling carries over only FINAL measurements; found a mid-circuit one")
            body.add_gate(cmd.op, [a.index[0] for a in cmd.args])
    return body, meas


def _with_measures(body: Circuit, base: Circuit, meas: list[tuple[int, Bit]]) -> Circuit:
    out = Circuit(base.n_qubits)
    out.append(body)
    for reg_name, size in {b.reg_name: 0 for b in base.bits}.items():
        size = max(b.index[0] for b in base.bits if b.reg_name == reg_name) + 1
        out.add_c_register(reg_name, size)
    for q, b in meas:
        out.Measure(q, b)
    return out


def noise_scaled_circuits(
    base: Circuit, lam: int, method: str, *, instances: int = 1, seed: int = 0, model=None
) -> list[ScaledCircuit]:
    """lam = 1: the base itself. "insert": `instances` independent Pauli-insertion draws
    (rng = default_rng((seed, instance))); "fold": one folded circuit. The final measurements are
    carried over untouched. The two-qubit count: x1 for insert, x lam for fold."""
    if method not in ("none", "insert", "fold"):
        raise ValueError(f"method must be 'insert' or 'fold', got {method!r}")
    if isinstance(lam, bool) or int(lam) != lam or lam < 1:
        raise ValueError(f"lam must be an integer >= 1, got {lam!r}")
    lam = int(lam)
    if lam == 1:
        return [ScaledCircuit(1, "none", 0, base.copy())]
    if method == "fold":
        if lam % 2 == 0:
            raise ValueError(f"folding needs an odd lam, got {lam}")
        body, meas = _split_measures(base)
        return [ScaledCircuit(lam, "fold", 0, _with_measures(fold_circuit(body, lam), base, meas))]
    if method != "insert":
        raise ValueError(f"method must be 'insert' or 'fold', got {method!r}")
    if instances < 1:
        raise ValueError(f"instances must be >= 1, got {instances}")
    model = default_model() if model is None else model
    body, meas = _split_measures(base)
    out = []
    for i in range(instances):
        rng = np.random.default_rng((seed, i))
        out.append(ScaledCircuit(lam, "insert", i, _with_measures(insert_paulis(body, lam, model, rng), base, meas)))
    return out


def iceberg_noise_scaled_circuits(base: Circuit, lam: int, *, instances: int = 1, seed: int = 0,
                                  model=None) -> list[ScaledCircuit]:
    """The Iceberg-encoded circuit at noise scale lam by Pauli insertion (DECIDED-9, 2026-10-24):
    before EVERY two-qubit gate (logical ZZ rotations, rotation-gadget CX, syndrome CX) a Pauli
    from `model` (default: the research/06 prior channel) with probability (lam - 1) q_P - the
    same rule, place and channel as the trajectory simulator (src/noise_scaling.run_iceberg_scaled)
    and the Stim rate table. Mid-circuit syndrome measurements, resets and conditionals are kept
    as they are. lam = 1 returns the base. Folding is not offered: it would fold the syndrome CX
    and change the code's detection structure (run_iceberg_scaled refuses it for that reason)."""
    if isinstance(lam, bool) or int(lam) != lam or lam < 1:
        raise ValueError(f"lam must be an integer >= 1, got {lam!r}")
    lam = int(lam)
    if lam == 1:
        return [ScaledCircuit(1, "none", 0, base.copy())]
    if instances < 1:
        raise ValueError(f"instances must be >= 1, got {instances}")
    model = default_model() if model is None else model
    return [ScaledCircuit(lam, "insert", i,
                          insert_paulis(base, lam, model, np.random.default_rng((seed, i))))
            for i in range(instances)]

