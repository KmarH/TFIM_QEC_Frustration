"""Noisy and Iceberg-encoded Q3 relaxation curves (handoff/08 Part B1) + the Stim size story (B2).

Write-up: docs/q3_thermalization.md §9. EVERY noisy number produced here is a CLASSICAL
PREDICTION UNDER AN ASSUMED NOISE MODEL (the research/06 H2 prior, config SensitivityConfig);
none is an H2 / hardware result.

Circuit (both arms identical up to encoding). The encoded pipeline's circuit-order Strang step
(src/encoded_codes.EncodedTFIM: X half, ZZ, X half; exp(+i h dt/2 X), exp(+i J dt ZZ)) on the
periodic triangular torus (bonds in src/lattice.triangular_bonds order). The Q3 ideal curves use
src/trotter.py's ZZ-outside splitting instead; both are 2nd-order Strang, and the difference is
measured and reported (tests, data file), not assumed away.

Noise model [assumed, research/06 prior]: after every 2-qubit gate a 2-qubit Pauli error with
probability p2, of which a fraction eta is Z(x)Z on top of a uniform 1/15 share (exactly the
Stim channel of src/encoded_codes.to_stim); after every 1-qubit gate a uniform X/Y/Z error with
probability p1; each readout bit flips with probability pm; each mid-circuit reset suffers an X
with probability p_init. Pauli-trajectory Monte Carlo (one random fault pattern per trajectory).

What is recorded. At every step boundary, without disturbing the trajectory, the EXACT readout
distribution a Z measurement of the (logical) register would produce there, including readout
flips: no shot sampling, so the only statistical error is over fault patterns (trajectories,
batch-means SE). For the Iceberg arm a trajectory carries weight 0 once any detector has fired
(post-selection), and the snapshot keeps only data patterns that pass the final pure-Z
detectors; the logical bits are the parities of the pure-Z readout representatives. The
observables are evaluated on the mixture distribution with the src/dimers.py definitions
(src/trotter_threshold.observable_function), raw and sector-conditioned, so bare / encoded /
ideal / handoff-07 curves are like-for-like.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from pytket import OpType

from src.backends import MemoryCeilingError
from src.backends_qc import _CX, _H, _PAULI, StateVector
from src.dimers import TriangularDimers
from src.encoded_codes import (
    BareTFIM, EncodedTFIM, NoiseRates, _support, detected_rate_per_step, iceberg_code,
    undetected_rate_per_step,
)
from src.encoded_tfim import check_physical_ceiling
from src.lattice import triangular_bonds
from src.mcmc_baseline import SCALARS, Shells, check_exact_ceiling, shell_correlations
from src.trotter_threshold import observable_function

_S = np.diag([1, 1j])
_PAULIS2 = [(a, b) for a in "IXYZ" for b in "IXYZ" if (a, b) != ("I", "I")]   # 15; ZZ is last


# --------------------------------------------------------------------------- #
# Noise sampling: the Stim channel of encoded_codes.to_stim, gate by gate
# --------------------------------------------------------------------------- #
def _fault_2q(rng, noise: NoiseRates) -> Optional[Tuple[str, str]]:
    """2q fault after a 2q gate: prob p2*(1-eta)/15 each of the 15 Paulis, + p2*eta on ZZ.

    Sampling must reproduce the exact PAULI_CHANNEL_2 weights of encoded_codes.to_stim so the
    Monte-Carlo arm and the Stim size story (B2) share one noise model: the ZZ bias is the
    dominant correlated error of the native 2q gate (research/06 H2 prior), so trajectory
    predictions and first-order accounting cannot drift apart.
    """
    if not noise.p2 or rng.random() >= noise.p2:
        return None
    # Draw the biased ZZ share first, then split the remaining weight uniformly over the 15 Paulis;
    # this nested draw gives marginals (1-eta)/15 + eta on ZZ, matching the to_stim channel exactly.
    if noise.zz_bias and rng.random() < noise.zz_bias:
        return ("Z", "Z")
    return _PAULIS2[rng.integers(15)]


def _fault_1q(rng, noise: NoiseRates) -> Optional[str]:
    if not noise.p1 or rng.random() >= noise.p1:
        return None
    return "XYZ"[rng.integers(3)]


def apply_segment_biased(sv: StateVector, seg, rng, noise: NoiseRates) -> None:
    """src/encoded_codes._apply_segment with the ZZ-biased 2q channel (local-sim there is uniform)."""
    for cmd in seg.get_commands():
        typ = cmd.op.type
        qs = [q.index[0] for q in cmd.qubits]
        if typ == OpType.H:
            sv.apply1(_H, qs[0])
        elif typ == OpType.S:
            sv.apply1(_S, qs[0])
        elif typ == OpType.Sdg:
            sv.apply1(_S.conj(), qs[0])
        elif typ == OpType.Rz:
            a = np.pi * float(cmd.op.params[0]) / 2
            sv.apply1(np.diag([np.exp(-1j * a), np.exp(1j * a)]), qs[0])
        elif typ == OpType.CX:
            sv.apply2(_CX, qs[0], qs[1])
        elif typ == OpType.ZZPhase:
            a = np.pi * float(cmd.op.params[0]) / 2
            sv.apply2(np.diag(np.exp(-1j * a * np.array([1, -1, -1, 1]))), qs[0], qs[1])
        else:
            raise ValueError(f"unsupported op {typ}")
        if len(qs) == 2:
            f = _fault_2q(rng, noise)
            if f:
                for q, x in zip(qs, f):
                    if x != "I":
                        sv.apply1(_PAULI[x], q)
        else:
            f = _fault_1q(rng, noise)
            if f:
                sv.apply1(_PAULI[f], qs[0])


def _check_supported(noise: NoiseRates) -> None:
    """The runners model p2 (+ zz_bias), p1, pm, p_init only; refuse the rest rather than silently
    dropping them (so 'assumed absent' can never become silently wrong)."""
    if noise.p_idle or noise.overrot:
        raise NotImplementedError("noisy_q3 runners do not model p_idle / overrot; set them to 0")


def check_memory(n_bytes: float, budget_gb: float, what: str) -> None:
    """Refuse an allocation whose estimated size exceeds the budget, before allocating (review M5:
    the 2^N ceiling alone does not bound batches x snapshots x 2^N accumulators)."""
    if n_bytes > budget_gb * 2 ** 30:
        raise MemoryCeilingError(f"{what}: estimated {n_bytes / 2 ** 30:.1f} GiB > budget {budget_gb} GiB "
                                 "(reduce batches / record_every / size)")


def readout_flip(p: np.ndarray, qubits: Sequence[int], n: int, pm: float) -> np.ndarray:
    """Exact readout bit-flip channel (prob pm per listed qubit) on a 2^n probability vector.

    Applied as a linear map on the full distribution, not sampled per shot: the measurement is
    the exact Z-readout distribution at the step boundary, so the ONLY statistical error in a
    curve is over fault patterns (trajectories, batch-means SE). Mixing in shot noise would add a
    second, avoidable error source and blur the ~2 sigma Stim-vs-sim comparison. The per-qubit
    flips commute, so the channel factorises axis by axis.
    """
    if not pm:
        return p
    t = p.reshape((2,) * n)
    for q in qubits:
        t = (1 - pm) * t + pm * np.flip(t, axis=q)
    return t.reshape(-1)


# --------------------------------------------------------------------------- #
# The two programs
# --------------------------------------------------------------------------- #
@dataclass
class TriangularIcebergTFIM(EncodedTFIM):
    """EncodedTFIM (Iceberg) on the periodic triangular torus, prepared in a Z-basis product state.

    Additive subclass: the bonds become triangular, and the uniform ry(theta) prep is replaced by
    ry(pi) (= logical Y up to phase, a |0> -> |1> flip) on the down-spin sites, ry(0) elsewhere,
    so the gate/noise-location structure of the prep is unchanged. This is CONSERVATIVE against
    Iceberg: it runs k weight-3 parity gadgets (including the no-op ry(0) ones), where a frame-only
    logical-X prep would need no 2-qubit gate; the bare arm charges one 1q location per down spin
    (review M6). It costs ~6% survival at t = 0 on 3x4 [measured]."""

    spins0: tuple = ()

    def __post_init__(self) -> None:
        super().__post_init__()
        self.bonds = triangular_bonds(self.Lx, self.Ly, "periodic")
        if len(self.spins0) != self.k:
            raise ValueError("spins0 must give one +-1 per logical site (row-major)")

    def schedule(self, n_steps: int, basis: str = "Z"):
        sch = super().schedule(n_steps, basis)          # built with this program's theta (= 0)
        if self.theta != 0.0:
            raise ValueError("TriangularIcebergTFIM uses theta = 0; the prep comes from spins0")
        # The first k "rot" unitaries are the prep rotations, in logical order (each may be followed
        # by its parity-gadget ancilla measure/detect/reset, which is left untouched: only the
        # rotation angle changes, so the gadget structure is identical).
        pos = [i for i, it in enumerate(sch.items) if it[0] == "U" and it[2] == "rot"][: self.k]
        for l, i in enumerate(pos):
            _, anc_old = self.rotation(self.rep_y(l), 0.0)
            seg, anc = self.rotation(self.rep_y(l), np.pi / 2 if self.spins0[l] < 0 else 0.0)
            if anc != anc_old:
                raise RuntimeError("prep gadget structure changed")
            sch.items[i] = ("U", seg, "rot")
        return sch


def make_iceberg(d: TriangularDimers, spins0: np.ndarray, J: float, h: float, dt: float) -> TriangularIcebergTFIM:
    return TriangularIcebergTFIM(iceberg_code(d.N), d.Lx, d.Ly, "periodic", J, h, dt, 0.0,
                                 spins0=tuple(int(s) for s in np.asarray(spins0).reshape(-1)))


@dataclass
class TriangularBareTFIM(BareTFIM):
    """encoded_codes.BareTFIM (Stim accounting image of the unencoded circuit) on the triangular torus."""

    def __post_init__(self):
        super().__post_init__()
        self.bonds = triangular_bonds(self.Lx, self.Ly, "periodic")


# --------------------------------------------------------------------------- #
# Trajectory runners with exact per-step readout snapshots
# --------------------------------------------------------------------------- #
@dataclass
class NoisyRun:
    """Weighted mixture readout distributions at the recorded steps, per trajectory batch."""

    arm: str                         # "ideal" | "bare" | "iceberg"
    steps: np.ndarray                # recorded Trotter steps (0 = after prep)
    dt: float
    acc: np.ndarray                  # (B, T, 2^N): sum over the batch of weight * logical distribution
    wsum: np.ndarray                 # (B, T): sum of weights (post-selection survival) per batch
    n_traj: int

    @property
    def times(self) -> np.ndarray:
        return self.steps * self.dt

    def acceptance(self) -> np.ndarray:
        """Fraction of trajectories surviving post-selection (1 for unencoded arms)."""
        return self.wsum.sum(0) / self.n_traj

    def mixture(self, batch: Optional[int] = None) -> np.ndarray:
        """(T, 2^N) normalised mixture distribution (pooled, or one batch); NaN where no weight."""
        a, w = (self.acc.sum(0), self.wsum.sum(0)) if batch is None else (self.acc[batch], self.wsum[batch])
        with np.errstate(invalid="ignore", divide="ignore"):
            return a / w[:, None]


def _record_steps(n_steps: int, every: int) -> List[int]:
    return list(range(0, n_steps + 1, every)) if n_steps % every == 0 else list(range(0, n_steps + 1, every)) + [n_steps]


def run_bare(d: TriangularDimers, spins0: np.ndarray, *, J: float, h: float, dt: float, n_steps: int,
             noise: NoiseRates, n_traj: int, n_batches: int, record_every: int, rng: np.random.Generator,
             max_spins: int, mem_gb: float = 2.0) -> NoisyRun:
    """Unencoded circuit-order Strang trajectories with gate-level noise (the bare H2-style arm).

    Prep: X on the down-spin sites (a 1q gate each). Step: Rx half on every site (1q), ZZ on every
    bond in triangular_bonds order (2q, biased channel), Rx half (1q). Snapshot readout with pm."""
    check_exact_ceiling(d.N, max_spins)
    _check_supported(noise)
    N = d.N
    rec = _record_steps(n_steps, record_every)
    check_memory(n_batches * len(rec) * (1 << N) * 8 + 2 * (1 << N) * 16, mem_gb, "run_bare accumulators")
    a = h * dt / 2
    RX = np.array([[math.cos(a), 1j * math.sin(a)], [1j * math.sin(a), math.cos(a)]])   # exp(+i a X)
    ZZ = np.diag(np.exp(1j * J * dt * np.array([1, -1, -1, 1])))                         # exp(+i J dt ZZ)
    down = [s for s, v in enumerate(np.asarray(spins0).reshape(-1)) if v < 0]
    acc = np.zeros((n_batches, len(rec), 1 << N))
    wsum = np.zeros((n_batches, len(rec)))
    noiseless = not (noise.p1 or noise.p2 or noise.pm)
    for tr in range(n_traj):
        b = tr % n_batches
        sv = StateVector(N, rng)
        for q in down:
            sv.apply1(_PAULI["X"], q)
            f = _fault_1q(rng, noise)
            if f:
                sv.apply1(_PAULI[f], q)

        def snap(k):
            p = readout_flip(np.abs(sv.flat()) ** 2, range(N), N, noise.pm)
            acc[b, k] += p
            wsum[b, k] += 1.0

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
                        sv.apply2(ZZ, i, j)
                        f = _fault_2q(rng, noise)
                        if f:
                            for q, x in zip((i, j), f):
                                if x != "I":
                                    sv.apply1(_PAULI[x], q)
            if ki < len(rec) and rec[ki] == s:
                snap(ki)
                ki += 1
        if noiseless:            # deterministic: one trajectory is the exact answer
            acc[:] = acc[b]
            wsum[:] = wsum[b]
            return NoisyRun("ideal", np.array(rec), dt, acc[:1], wsum[:1], 1)
    return NoisyRun("bare", np.array(rec), dt, acc, wsum, n_traj)


def _boundaries(prog: TriangularIcebergTFIM) -> Tuple[int, int]:
    """(item index right after syndrome round 1, items per Trotter step) of prog.schedule(n):
    a step = Trotter body + syndrome round, each ending with an "I" item."""
    def last_idle(n):
        items = prog.schedule(n).items
        return max(i for i, it in enumerate(items) if it[0] == "I") + 1
    b1, b2, b3 = last_idle(1), last_idle(2), last_idle(3)
    if b3 - b2 != b2 - b1:
        raise RuntimeError("schedule is not periodic in the step")
    return b1, b2 - b1


def run_iceberg(d: TriangularDimers, spins0: np.ndarray, *, J: float, h: float, dt: float, n_steps: int,
                noise: NoiseRates, n_traj: int, n_batches: int, record_every: int, rng: np.random.Generator,
                max_spins: int, mem_gb: float = 2.0,
                apply_u: Callable[..., None] | None = None,
                ) -> NoisyRun:
    """Iceberg-encoded trajectories (src/encoded_codes schedule, syndrome round every step) with
    post-selection on every detector, and exact logical readout snapshots at step boundaries.

    `apply_u` is an additive hook (default `apply_segment_biased`, i.e. behaviour unchanged) for
    applying one unitary segment with its faults. It exists so a noise-SCALED runner can insert
    amplifying Paulis without duplicating this trajectory loop; see
    src/noise_scaling.run_iceberg_scaled (decision D6, 2026-10-22)."""
    prog = make_iceberg(d, spins0, J, h, dt)
    check_physical_ceiling(prog.n_phys, max_spins)
    check_exact_ceiling(d.N, max_spins)                 # logical 2^N observable tables
    _check_supported(noise)
    n_rec = len(_record_steps(n_steps, record_every))
    check_memory(n_batches * n_rec * (1 << d.N) * 8                      # accumulators
                 + (1 << prog.n_phys) * (8 * 3 + 16 * 2),                # lidx, parity work, zdet, state, probs
                 mem_gb, "run_iceberg tables")
    apply_seg = apply_segment_biased if apply_u is None else apply_u
    sch = prog.schedule(n_steps)
    b1, stride = _boundaries(prog)
    rec = _record_steps(n_steps, record_every)
    n, nd = prog.n_phys, prog.n_data
    idx = np.arange(1 << n)

    def bit(q):
        return (idx >> (n - 1 - q)) & 1

    lidx = np.zeros(1 << n, dtype=np.int64)              # logical basis index of each physical index
    for l in range(prog.k):
        par = np.zeros(1 << n, dtype=np.int64)
        for q in _support(prog.readout_z(l)):
            par ^= bit(q)
        lidx |= par << (prog.k - 1 - l)                   # logical site 0 = MSB, as dimers.py
    zdet = np.ones(1 << n, dtype=bool)                   # final pure-Z detectors (readout parity)
    for i, P in enumerate(prog.stabs):
        if all(P[q] in (0, 3) for q in range(nd)):
            par = np.zeros(1 << n, dtype=np.int64)
            for q in _support(P):
                par ^= bit(q)
            zdet &= par == 0
    at = {b1 + (s - 1) * stride: s for s in rec}     # s = 0: right after the prep (start of step 1)
    acc = np.zeros((n_batches, len(rec), 1 << d.N))
    wsum = np.zeros((n_batches, len(rec)))
    for tr in range(n_traj):
        b = tr % n_batches
        sv = StateVector(n, rng)
        meas: Dict[str, int] = {}
        ok = True

        def snap(k):
            # Post-selection is absorbing: once any detector has fired (ok=False) the whole
            # trajectory is discarded for the rest of time, so its weight is carried as 0 at this
            # and every later boundary rather than renormalised. A detector click flags a *known*
            # error syndrome; keeping that trajectory would readmit a state Iceberg has already
            # rejected, biasing the surviving mixture. Dropping it is what makes 'acceptance' the
            # true code survival and the conditioned curve a clean post-selected estimate.
            if not ok:
                return
            p = readout_flip(np.abs(sv.flat()) ** 2, range(nd), n, noise.pm)
            # Also drop final pure-Z detector violations (zdet): readout-parity failures are part
            # of the same post-selection, enforced on the snapshot distribution itself.
            p = np.where(zdet, p, 0.0)
            w = float(p.sum())
            if w > 0:
                acc[b, k] += np.bincount(lidx, weights=p, minlength=1 << d.N)
                wsum[b, k] += w

        for i, it in enumerate(sch.items):
            if i in at:
                snap(rec.index(at[i]))
                if not ok:
                    break
            kind = it[0]
            if kind == "U":
                apply_seg(sv, it[1], rng, noise)
            elif kind == "M":
                _, q, key, rb = it
                if key.startswith("d"):
                    break                                  # the destructive readout is emulated by snap
                bit = sv.measure(q)
                if noise.pm and rng.random() < noise.pm:
                    bit ^= 1
                meas[key] = bit
            elif kind == "R":
                sv.reset(it[1])
                if noise.p_init and rng.random() < noise.p_init:
                    sv.apply1(_PAULI["X"], it[1])
            elif kind == "C":
                if meas[it[1]]:
                    P = it[2]
                    for q in _support(P):
                        sv.apply1(_PAULI["IXYZ"[P[q]]], q)
            elif kind == "D":
                if sum(meas[k] for k in it[1]) % 2:
                    ok = False
    return NoisyRun("iceberg", np.array(rec), dt, acc, wsum, n_traj)


# --------------------------------------------------------------------------- #
# Observables of a run (identical definitions to the Q3 arm)
# --------------------------------------------------------------------------- #
OBS_N = ("flippable_density", "defect_density", "memory", "C1")


@dataclass
class RunObservables:
    times: np.ndarray
    acceptance: np.ndarray                    # code post-selection survival (1 for unencoded)
    p_in: np.ndarray                          # weight in the defect-free W0 sector (Gauss-law post-selection acceptance)
    raw: Dict[str, Tuple[np.ndarray, np.ndarray]]    # obs -> (value, batch SE)
    cond: Dict[str, Tuple[np.ndarray, np.ndarray]]   # sector-conditioned


def run_observables(d: TriangularDimers, spins0: np.ndarray, shells: Shells, run: NoisyRun,
                    max_spins: int) -> RunObservables:
    obs = observable_function(d, spins0, shells, max_spins=max_spins)
    i0 = d.product_state_index(spins0)
    wx, wy = d.winding_x(0), d.winding_y(0)
    mask = (d.total_defects() == 0) & (wx == wx[i0]) & (wy == wy[i0])

    def evaluate(P):                     # P: (T, 2^N) -> raw, cond dicts of (T,) arrays, p_in
        # raw vs cond is the T-17 caveat made operational. 'raw' is the full noisy mixture; 'cond'
        # restricts to the defect-free W0 winding sector (Gauss-law post-selection) and renormalises.
        # Noise LEAKS weight out of W0 toward the uniform/thermal distribution, so a raw noisy curve
        # can drift onto the thermal reference B_W0 for a reason that is pure decoherence, not
        # physical thermalization. Reporting both lets a reader separate "the sector is relaxing"
        # (visible in cond) from "the state is leaving the sector" (the raw-vs-cond gap); landing on
        # B_W0 in the raw curve alone is therefore not evidence of thermalization.
        raw = {o: np.full(len(P), np.nan) for o in OBS_N}
        cond = {o: np.full(len(P), np.nan) for o in OBS_N}
        pin = np.full(len(P), np.nan)
        for t, p in enumerate(P):
            if not np.all(np.isfinite(p)):
                continue
            pin[t] = float(p[mask].sum())
            r = obs(p)
            for o in OBS_N:
                raw[o][t] = r[o]
            if pin[t] > 0:
                c = obs(np.where(mask, p, 0.0) / pin[t])
                for o in OBS_N:
                    cond[o][t] = c[o]
        return raw, cond, pin

    raw, cond, pin = evaluate(run.mixture())
    nb = run.acc.shape[0]
    if nb > 1:
        per = [evaluate(run.mixture(b)) for b in range(nb)]
        def se(vals):
            # batches with no surviving weight are NaN: the SE uses only the finite ones (review M3)
            v = np.array(vals)
            k = np.isfinite(v).sum(axis=0)
            with np.errstate(invalid="ignore", divide="ignore"):
                return np.where(k > 1, np.nanstd(v, axis=0, ddof=1) / np.sqrt(np.maximum(k, 1)), np.nan)
        se_raw = {o: se([x[0][o] for x in per]) for o in OBS_N}
        se_cond = {o: se([x[1][o] for x in per]) for o in OBS_N}
    else:
        se_raw = {o: np.zeros(len(run.steps)) for o in OBS_N}
        se_cond = {o: np.zeros(len(run.steps)) for o in OBS_N}
    return RunObservables(run.times, run.acceptance(), pin,
                          {o: (raw[o], se_raw[o]) for o in OBS_N}, {o: (cond[o], se_cond[o]) for o in OBS_N})


# --------------------------------------------------------------------------- #
# B2: first-order (Stim) accounting toward larger N
# --------------------------------------------------------------------------- #
@dataclass
class SizeRow:
    Lx: int
    Ly: int
    n_logical: int
    n_phys_iceberg: int
    bare_unprotected: float          # bare: prob. per step that any fault occurs (all undetected)
    ice_detected: float              # Iceberg: per-step detected (discarded) probability
    ice_undetected: float            # Iceberg: per-step undetected logical-fault probability


def size_row(Lx: int, Ly: int, spins0: np.ndarray, *, J: float, h: float, dt: float, noise: NoiseRates) -> SizeRow:
    """Stim first-order fault accounting (src/encoded_codes) for the triangular programs: no
    state vector, so it runs at any N (Stim is unbounded; SCOPE §5). First order in the fault
    rates [derived accounting], under the ASSUMED noise model."""
    d = TriangularDimers(Lx, Ly)
    prog = make_iceberg(d, spins0, J, h, dt)
    bare = TriangularBareTFIM(Lx, Ly, "periodic", J, h, dt, 0.0)
    ub = undetected_rate_per_step(bare, noise)
    ui = undetected_rate_per_step(prog, noise)
    return SizeRow(Lx, Ly, d.N, prog.n_phys, float(ub["total"]), float(detected_rate_per_step(prog, noise)),
                   float(ui["total"]))
