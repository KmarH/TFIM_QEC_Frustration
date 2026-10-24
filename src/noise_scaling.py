"""Noise scaling for the 6x6 Q3 arm (T-17 / R-14): Pauli insertion, gate folding, the lambda-slope
diagnostic and the fixed-asymptote exponential extrapolation, with the HQC cost formula.

Derivation and decisions: research/derivations/01-noise-scaling-arm.md (D1-D5, 2026-10-16);
sources: research/07-noise-scaling.md. Write-up: docs/q3_noise_scaling.md.

EVERY noisy number produced with this module is a CLASSICAL PREDICTION UNDER AN ASSUMED NOISE
MODEL (the research/06 H2 prior); none is an H2 / hardware result. This module only builds and
simulates circuits; it has no submission path.

- Insertion [derived; the 2503.20870 method]: before every ZZPhase, with probability
  (lam - 1) * q_P insert the 2q Pauli P of the model (one draw per gate). To first order the 2q
  error becomes lam * q_P per component. It scales exactly what the model contains and nothing
  else: not 1q, SPAM or idle noise.
  **Scope caveat [review/18 F6, 2026-10-23].** research/07-noise-scaling.md supports this method
  only before the 2q ROTATIONS (2503.20870 S1.4, "before each U_ZZ ... probability (alpha-1)p_j"),
  and its PEA row records that such a model "is valid only when combined with random Pauli
  twirls". `insert_paulis` below stays inside that support (ZZPhase only). `run_iceberg_scaled`
  does NOT: it inserts before every 2q gate of the encoded circuit - syndrome-extraction CX and
  rotation-gadget CX included - using the rotation-learned channel, in an UNTWIRLED trajectory
  simulation. That extension is **[inferred], not [derived]**, and the KB does not cover it. It is
  also only first-order-faithful for ZZPhase: inserting before the gate while the intrinsic fault
  lands after is exact for ZZPhase (depolarizing is unitarily covariant and ZZ commutes with the
  rotation) but not for CX, where CX (Z x Z) CX = I x Z moves the eta-biased excess into a
  different Iceberg detection class (review/18 F7).
  **Three lambda scopes coexist in this repository and they are NOT the same set of gates**
  (review/18 F3): the trajectory simulator and `run_*_scaled` amplify EVERY 2q gate (correct for
  the model, which charges `_fault_2q` at every 2q location, src/noisy_q3.py:103);
  `q3_scaling._NAMED_SCOPES["2q"]` is ("rot-zz", "syn-cx") and sets the survival-matched encoded
  windows; `insert_paulis` and `config.q3_scaling.fold_scope` are rot-zz only and govern the
  pytket circuit that is compiled, HQC-costed and would be submitted. **Which is canonical is an
  open decision for the project lead; do not send a lambda point to the emulator before it is
  settled.**
- Folding [derived; 2005.10921]: ZZPhase(a) -> ZZPhase(a) [ZZPhase(-a) ZZPhase(a)]^k, lam = 2k+1.
  The twirled total error is x lam to first order for any Pauli channel. The Pauli composition is
  x lam only for channels with q_P = q_{P.ZZ} on anticommuting P (true of the prior, not in
  general).
- Fit [D5]: O(lam) = B + (O0 - B) exp(-g lam) with B FIXED (infinite-T value), so three lam
  points leave one degree of freedom and the chi2 test can reject the form.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace

import numpy as np
import stim
from pytket import Circuit, OpType
from scipy.optimize import least_squares
from scipy.stats import chi2 as chi2_dist

import src.encoded_codes as ec
from config import CONFIG
from src.backends_qc import _PAULI, StateVector
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates
from src.mcmc_baseline import check_exact_ceiling
from src.noisy_q3 import (
    NoisyRun,
    _check_supported,
    _fault_1q,
    _fault_2q,
    _record_steps,
    apply_segment_biased,
    check_memory,
    readout_flip,
    run_iceberg,
)

PauliModel = dict[str, float]
LABELS15 = [a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II"]
_OP1 = {"X": OpType.X, "Y": OpType.Y, "Z": OpType.Z}


# --------------------------------------------------------------------------- #
# Models and amplification
# --------------------------------------------------------------------------- #
def prior_model(noise: NoiseRates) -> PauliModel:
    """The 2q Pauli channel of encoded_codes.to_stim: p2(1-eta)/15 on each of 15 Paulis, plus
    p2*eta on ZZ."""
    u = noise.p2 * (1 - noise.zz_bias) / 15
    return {k: u + (noise.p2 * noise.zz_bias if k == "ZZ" else 0.0) for k in LABELS15}


def _draw(model: PauliModel, scale: float, rng: np.random.Generator) -> str | None:
    """One draw: label P with probability scale * model[P], else None."""
    if not model or scale <= 0:
        return None
    total = scale * sum(model.values())
    if total > 1 + 1e-12:
        raise ValueError(f"insertion probability {total:.3g} > 1: lam too large for this model")
    u = rng.random()
    if u >= total:
        return None
    acc = 0.0
    for k, q in model.items():
        acc += scale * q
        if u < acc:
            return k
    return k                       # round-off at the upper edge


def insert_paulis(circuit: Circuit, lam: float, model: PauliModel,
                  rng: np.random.Generator) -> Circuit:
    """Copy of `circuit` with, before every ZZPhase, the 2q Pauli P inserted with probability
    (lam-1)*model[P] (one draw per gate). label[0] acts on the gate's first qubit. The Paulis are
    emitted as 1q X/Y/Z gates, so the 2q count is unchanged. lam >= 1."""
    if lam < 1:
        raise ValueError(f"lam must be >= 1, got {lam}")
    out = Circuit(circuit.n_qubits, circuit.n_bits)
    for cmd in circuit.get_commands():
        if cmd.op.type == OpType.ZZPhase:
            lab = _draw(model, lam - 1, rng)
            if lab:
                for q, x in zip(cmd.qubits, lab, strict=True):
                    if x != "I":
                        out.add_gate(_OP1[x], [q])
        out.add_gate(cmd.op, cmd.args)
    return out


def fold_circuit(circuit: Circuit, lam: int) -> Circuit:
    """Every ZZPhase(a) -> ZZPhase(a) [ZZPhase(-a) ZZPhase(a)]^((lam-1)/2); other gates untouched.
    lam must be an odd integer >= 1."""
    if int(lam) != lam or lam < 1 or int(lam) % 2 == 0:
        raise ValueError(f"folding needs an odd integer lam >= 1, got {lam}")
    k = (int(lam) - 1) // 2
    out = Circuit(circuit.n_qubits, circuit.n_bits)
    for cmd in circuit.get_commands():
        out.add_gate(cmd.op, cmd.args)
        if cmd.op.type == OpType.ZZPhase:
            a = cmd.op.params[0]
            for _ in range(k):
                out.add_gate(OpType.ZZPhase, [-a], cmd.args)
                out.add_gate(OpType.ZZPhase, [a], cmd.args)
    return out


# --------------------------------------------------------------------------- #
# First-order (Stim) accounting at scale lam
# --------------------------------------------------------------------------- #
@contextmanager
def _scaled_stim(lam: float, scope: Sequence[str]):
    """Within the block, encoded_codes.to_stim returns its usual image with the probabilities of
    every noise instruction whose tag class is in `scope` multiplied by lam. To first order this is
    folding or insertion on those locations (Stim treats rotations as identity). It reuses the
    verified rate functions unchanged. Not thread-safe."""
    orig = ec.to_stim

    def scaled(sch, noise, mode="identity"):
        out = stim.Circuit()
        for ins in orig(sch, noise, mode).flattened():
            if ins.tag and ins.tag.split(":")[0] in scope:
                args = [a * lam for a in ins.gate_args_copy()]
                ins = stim.CircuitInstruction(ins.name, ins.targets_copy(), args, tag=ins.tag)
            out.append(ins)
        return out

    ec.to_stim = scaled
    try:
        yield
    finally:
        ec.to_stim = orig


def scaled_stim_rates(prog, noise: NoiseRates, lam: float,
                      scope: Sequence[str] = ("rot-zz", "syn-cx")) -> dict[str, float]:
    """First-order per-step rates with the `scope` noise classes x lam: 'bare_or_undetected' (the
    bare program's fault rate, or the code's undetected-logical rate) and 'detected' (0 for a
    program without detectors). [derived accounting, ASSUMED noise]

    Refuses noise classes the scope cannot scale (over-rotation, idle), rather than silently
    leaving them at lam = 1 (review B, 2026-10-16)."""
    if noise.overrot or noise.p_idle:
        raise NotImplementedError("scaled_stim_rates scales gate classes only; overrot / p_idle "
                                  "would stay unscaled: set them to 0")
    with _scaled_stim(lam, tuple(scope)):
        und = ec.undetected_rate_per_step(prog, noise)["total"]
        det = ec.detected_rate_per_step(prog, noise)
    return {"bare_or_undetected": float(und), "detected": float(det) if abs(det) > 1e-15 else 0.0}


# --------------------------------------------------------------------------- #
# Trajectories at scale lam (the bare arm of noisy_q3.run_bare, gate for gate)
# --------------------------------------------------------------------------- #
def run_bare_scaled(d: TriangularDimers, spins0: np.ndarray, *, lam: float, method: str,
                    J: float, h: float, dt: float, n_steps: int, noise: NoiseRates, n_traj: int,
                    n_batches: int, record_every: int, rng: np.random.Generator, max_spins: int,
                    mem_gb: float = 2.0, model: PauliModel | None = None) -> NoisyRun:
    """noisy_q3.run_bare at noise scale lam. Identical prep, step, faults and snapshots; only each
    ZZ gate changes:
      'insert': a Pauli drawn from `model` (default: the prior channel of `noise`) with probability
                (lam-1)*q_P before the gate, then the gate and its usual fault;
      'fold':   the gate and its fault, then (lam-1)/2 times [ZZ^-1, fault, ZZ, fault].
    Classical prediction under the ASSUMED noise model."""
    if method not in ("insert", "fold"):
        raise ValueError(f"method must be 'insert' or 'fold', got {method!r}")
    if method == "fold" and (int(lam) != lam or lam < 1 or int(lam) % 2 == 0):
        raise ValueError(f"folding needs an odd integer lam >= 1, got {lam}")
    if method == "insert" and lam < 1:
        raise ValueError(f"lam must be >= 1, got {lam}")
    check_exact_ceiling(d.N, max_spins)
    _check_supported(noise)
    model = prior_model(noise) if model is None else model
    k_fold = (int(lam) - 1) // 2 if method == "fold" else 0
    N = d.N
    rec = _record_steps(n_steps, record_every)
    check_memory(n_batches * len(rec) * (1 << N) * 8 + 2 * (1 << N) * 16, mem_gb,
                 "run_bare_scaled accumulators")
    a = h * dt / 2
    c, sn = math.cos(a), math.sin(a)
    RX = np.array([[c, 1j * sn], [1j * sn, c]])                       # exp(+i a X)
    phase = np.array([1, -1, -1, 1])
    ZZ = np.diag(np.exp(1j * J * dt * phase))                         # exp(+i J dt ZZ)
    ZZi = ZZ.conj()
    down = [s for s, v in enumerate(np.asarray(spins0).reshape(-1)) if v < 0]
    acc = np.zeros((n_batches, len(rec), 1 << N))
    wsum = np.zeros((n_batches, len(rec)))
    noiseless = not (noise.p1 or noise.p2 or noise.pm)

    def fault2(sv, i, j):
        f = _fault_2q(rng, noise)
        if f:
            for q, x in zip((i, j), f, strict=True):
                if x != "I":
                    sv.apply1(_PAULI[x], q)

    for tr in range(n_traj):
        b = tr % n_batches
        sv = StateVector(N, rng)
        for q in down:
            sv.apply1(_PAULI["X"], q)
            f = _fault_1q(rng, noise)
            if f:
                sv.apply1(_PAULI[f], q)

        def snap(kk, sv=sv, b=b):
            p = readout_flip(np.abs(sv.flat()) ** 2, range(N), N, noise.pm)
            acc[b, kk] += p
            wsum[b, kk] += 1.0

        ki = 0
        if rec[0] == 0:
            snap(0)
            ki = 1
        for s in range(1, n_steps + 1):
            for half in (0, 1):
                for q in range(N):
                    sv.apply1(RX, q)
                    f = _fault_1q(rng, noise)
                    if f:
                        sv.apply1(_PAULI[f], q)
                if half == 0:
                    for (i, j) in d.bonds:
                        if method == "insert":
                            lab = _draw(model, lam - 1, rng)
                            if lab:
                                for q, x in zip((i, j), lab, strict=True):
                                    if x != "I":
                                        sv.apply1(_PAULI[x], q)
                        sv.apply2(ZZ, i, j)
                        fault2(sv, i, j)
                        for _ in range(k_fold):
                            sv.apply2(ZZi, i, j)
                            fault2(sv, i, j)
                            sv.apply2(ZZ, i, j)
                            fault2(sv, i, j)
            if ki < len(rec) and rec[ki] == s:
                snap(ki)
                ki += 1
        if noiseless:            # deterministic: one trajectory is the exact answer (as run_bare)
            return NoisyRun("ideal", np.array(rec), dt, acc[b:b + 1], wsum[b:b + 1], 1)
    return NoisyRun("bare", np.array(rec), dt, acc, wsum, n_traj)


# --------------------------------------------------------------------------- #
# Trajectories at scale lam, ENCODED arm (decision D6, 2026-10-22)
# --------------------------------------------------------------------------- #
class _OneCommand:
    """One-command stand-in for a pytket segment.

    It lets `run_iceberg_scaled` reuse noisy_q3.apply_segment_biased — the verified gate dispatch
    and ZZ-biased fault sampling — command by command, so the amplifying Pauli can go in front of
    each 2-qubit gate without duplicating either the gate dispatch or the trajectory loop.
    """

    __slots__ = ("_cmd",)

    def __init__(self, cmd):
        self._cmd = cmd

    def get_commands(self):
        return (self._cmd,)


def run_iceberg_scaled(d: TriangularDimers, spins0: np.ndarray, *, lam: float, method: str,
                       J: float, h: float, dt: float, n_steps: int, noise: NoiseRates, n_traj: int,
                       n_batches: int, record_every: int, rng: np.random.Generator, max_spins: int,
                       mem_gb: float = 2.0, model: PauliModel | None = None) -> NoisyRun:
    """noisy_q3.run_iceberg at noise scale lam, by Pauli insertion on the two-qubit gates.

    Before every 2-qubit gate of the encoded circuit — the logical ZZ rotations AND the
    syndrome-extraction CX gates, i.e. the ("rot-zz", "syn-cx") scope of `scaled_stim_rates` — a
    Pauli P drawn from `model` (default: the prior channel of `noise`) is inserted with
    probability (lam-1)*q_P, one draw per gate; then the gate and its usual fault follow. This is
    the same mechanism and the same channel as `run_bare_scaled(method="insert")`, so the two arms
    of the lambda ladder are amplified alike: the 2q channel scales, while 1q, SPAM and idle noise
    stay at lam = 1.

    At lam = 1 no randomness is drawn, so the run is bitwise identical to `run_iceberg` at the
    same seed and the lam = 1 rung stays comparable to data/q3_noisy.txt.

    `method="fold"` is refused: folding the encoded circuit would also fold the syndrome CX gates,
    which changes the code's detection structure rather than only its error rate (a separate
    design question, not an assumption this function may make silently).

    Classical prediction under the ASSUMED noise model; never an H2 result.
    """
    if method == "fold":
        raise NotImplementedError(
            "folding is not defined for the encoded arm: it would fold the syndrome-extraction "
            "CX gates too, changing the code's detection structure and not only its error rate. "
            "Use method='insert' (decision D6, 2026-10-22)."
        )
    if method != "insert":
        raise ValueError(f"method must be 'insert' for the encoded arm, got {method!r}")
    if lam < 1:
        raise ValueError(f"lam must be >= 1, got {lam}")
    model = prior_model(noise) if model is None else model

    def apply_u(sv, seg, rng_, noise_):
        for cmd in seg.get_commands():
            qs = [q.index[0] for q in cmd.qubits]
            if len(qs) == 2:
                lab = _draw(model, lam - 1, rng_)
                if lab:
                    for q, x in zip(qs, lab, strict=True):
                        if x != "I":
                            sv.apply1(_PAULI[x], q)
            apply_segment_biased(sv, _OneCommand(cmd), rng_, noise_)

    return run_iceberg(d, spins0, J=J, h=h, dt=dt, n_steps=n_steps, noise=noise, n_traj=n_traj,
                       n_batches=n_batches, record_every=record_every, rng=rng,
                       max_spins=max_spins, mem_gb=mem_gb, apply_u=apply_u)


# --------------------------------------------------------------------------- #
# The diagnostic and the extrapolation
# --------------------------------------------------------------------------- #
@dataclass
class SlopeResult:
    slope: float
    se: float           # unscaled weighted-LSQ standard error
    z: float
    resolved: bool      # |z| >= z_min


def slope_test(lams, values, ses, z_min: float | None = None) -> SlopeResult:
    """Weighted least-squares slope of O against lam, with weights 1/se^2 and the UNSCALED se
    (no reduced-chi2 rescaling). Resolved when |z| >= z_min (default CONFIG.noise_scaling.z_min)."""
    z_min = CONFIG.noise_scaling.z_min if z_min is None else z_min
    lam = np.asarray(lams, dtype=float)
    y = np.asarray(values, dtype=float)
    w = 1 / np.asarray(ses, dtype=float) ** 2
    lb, yb = (w * lam).sum() / w.sum(), (w * y).sum() / w.sum()
    sxx = (w * (lam - lb) ** 2).sum()
    slope = float((w * (lam - lb) * (y - yb)).sum() / sxx)
    se = float(1 / math.sqrt(sxx))
    z = slope / se
    return SlopeResult(slope, se, z, bool(abs(z) >= z_min))


@dataclass
class ExtrapResult:
    O0: float           # extrapolated lam = 0 value
    se: float           # unscaled se of O0, from (J^T W J)^-1
    g: float            # decay rate per unit lam
    B: float            # asymptote (fixed, or fitted when asymptote=None)
    chi2: float
    dof: int
    p_value: float
    consistent: bool    # p_value >= CONFIG.noise_scaling.p_consistent (False when dof == 0)


def extrapolate_exp(lams, values, ses, asymptote: float | None) -> ExtrapResult:
    """Fit O(lam) = B + (O0 - B) exp(-g lam) by weighted least squares. With `asymptote` given, B is
    fixed (D5): params (O0, g), dof = n - 2. With None, B is fitted too (dof = n - 3). The fit is
    reported as `consistent` only when the chi2 p-value clears CONFIG.noise_scaling.p_consistent."""
    lam = np.asarray(lams, dtype=float)
    y = np.asarray(values, dtype=float)
    s = np.asarray(ses, dtype=float)
    fixed = asymptote is not None

    def unpack(p):
        return (p[0], p[1], float(asymptote)) if fixed else (p[0], p[1], p[2])

    def resid(p):
        O0, g, B = unpack(p)
        return (B + (O0 - B) * np.exp(-g * lam) - y) / s

    # start: closed-form two-point exponential through the end points (fallback g = 0.1)
    B0 = float(asymptote) if fixed else float(y[-1] - 0.5 * (y[0] - y[-1]))
    i0, i1 = int(np.argmin(lam)), int(np.argmax(lam))
    ratio = (y[i1] - B0) / (y[i0] - B0) if y[i0] != B0 else -1.0
    g0 = -math.log(ratio) / (lam[i1] - lam[i0]) if ratio > 0 else 0.1
    O00 = B0 + (y[i0] - B0) * math.exp(g0 * lam[i0])
    p0 = [O00, g0] if fixed else [O00, g0, B0]
    fit = least_squares(resid, p0, xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=10000)
    O0, g, B = unpack(fit.x)
    Jm = fit.jac
    cov = np.linalg.pinv(Jm.T @ Jm)
    chi2 = float(np.sum(fit.fun ** 2))
    dof = len(lam) - len(p0)
    p_value = float(chi2_dist.sf(chi2, dof)) if dof > 0 else float("nan")
    consistent = bool(dof > 0 and p_value >= CONFIG.noise_scaling.p_consistent)
    return ExtrapResult(float(O0), float(math.sqrt(max(cov[0, 0], 0.0))), float(g), float(B),
                        chi2, dof, p_value, consistent)


# --------------------------------------------------------------------------- #
# Cost
# --------------------------------------------------------------------------- #
def hqc_cost(n1q: int, n2q: int, nm: int, shots: int) -> float:
    """Quantinuum H-series credits for one circuit [established, Quantinuum docs via research/07]:
    HQC = 5 + C (N1q + 10 N2q + 5 Nm) / 5000, C = shots; Nm counts prep, mid-circuit and final
    measurements and resets. An ESTIMATE for planning; nothing here submits anything."""
    return 5.0 + shots * (n1q + 10 * n2q + 5 * nm) / 5000.0


def replace_noise(noise: NoiseRates, **kw) -> NoiseRates:
    """dataclasses.replace for NoiseRates (convenience for scripts)."""
    return replace(noise, **kw)
