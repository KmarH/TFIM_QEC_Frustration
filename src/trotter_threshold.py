"""Trotter-threshold / dt-convergence study for the frustrated triangular TFIM (handoff/08 Part A, K2).

Write-up: docs/q3_thermalization.md §8. Classical only: exact sparse time evolution
(Chebyshev expansion of exp(-iHt) on src/operators.tfim_hamiltonian, tested against scipy's
expm_multiply and dense diagonalization) against the repo's 2nd-order Strang step
(src/trotter.trotter2_step, the step every Q3 curve uses). Nothing here is an H2 result.

What is measured. From a defect-free product state c0 (the Q3 starts), at fixed physical time T,
the deviation |O_Trotter(t) - O_exact(t)| of the Q3 local observables (src/dimers.py definitions,
evaluated exactly as src/mcmc_baseline.relaxation_curve does), maximised over the comparison
times, plus the final-state infidelity 1 - |<psi_exact(T)|psi_Trotter(T)>|^2.

Expected behaviour [derived / established].
  * Small dt: local errors O(dt^2) (Strang is 2nd order); infidelity O(dt^4).
  * Threshold: above a sharp dt the local observables stop tracking the exact dynamics
    (Heyl, Hauke & Zoller, Sci. Adv. 5, eaau8342 [established]; Trotter prethermalization:
    Yang et al., PRX Quantum 4, 030320 [established]; no numbers imported from either).
  * Where, for this model [derived, first-order Floquet, src/mcmc_baseline.py docstring]: flipping
    a non-flippable spin s of a defect-free configuration costs 2|J| n_s, and its admixture
    h^2 (dt/2)^2 / sin^2(|J| n_s dt) diverges when |J| n_s dt = pi: the Ising energy folds back
    into the Floquet zone and the gap protecting the Gauss law closes. With n_s in {2, 4, 6}, the
    resonances are dt = pi/(6|J|) ~ 0.524, pi/(4|J|) ~ 0.785, pi/(2|J|) ~ 1.571; the lowest
    one present in the dynamics sets the threshold. "Present" is a weak-field statement about c0
    and its flip sector; as h grows, configurations admixed at higher order bring their own gaps
    (e.g. the stripe, n_s = 2 only, keeps a small absolute error up to dt ~ 1 at h = 0.1 and breaks
    near pi/2, but already jumps at pi/6 at h = 0.3) [measured: data/trotter_threshold.txt §1
    stripe scans; tests/test_trotter_threshold.py].

Operational threshold (stated, not borrowed): dt* = the smallest scanned dt at which the time-max
error of the flippable density reaches eps (CONFIG.q3.thr_eps) [assumed criterion].
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.special import jv

from src.dimers import TriangularDimers
from src.mcmc_baseline import (
    ConfigEvaluator, Shells, check_exact_ceiling, dimer_pattern, shell_correlations,
)
from src.operators import tfim_hamiltonian
from src.trotter import ising_diagonal, trotter2_step

# Observables compared (all [0,1]-valued or a per-pair correlation); C1 = second distance shell
# (r = sqrt(3)/2), the first discriminating one (docs/q3_thermalization.md §4).
OBS = ("flippable_density", "defect_density", "memory", "C1")


def observable_function(d: TriangularDimers, spins0: np.ndarray, shells: Shells,
                        max_spins: int = 20) -> Callable[[np.ndarray], Dict[str, float]]:
    """p (2^N probabilities) -> Q3 observables, with the src/dimers.py arrays and exactly the
    formulas of src/mcmc_baseline.relaxation_curve (tested equal). Builds 2^N x 3N tables, so it
    refuses N above the ED ceiling before allocating."""
    check_exact_ceiling(d.N, max_spins)
    n0 = dimer_pattern(d, spins0)
    flips = sum(d.flippable(s).astype(np.float64) for s in range(d.N)) / d.N
    occ = np.stack([d.dimer(b) for b in d.bonds], axis=1).astype(np.float64)   # (2^N, 3N)
    D = d.total_defects() / (2 * d.N)

    def obs(p: np.ndarray) -> Dict[str, float]:
        dens = p @ occ
        sup = np.nonzero(p > 1e-16)[0]
        second = occ[sup].T @ (occ[sup] * p[sup, None])
        c = shell_correlations(shells, dens, second)
        return {"flippable_density": float(p @ flips), "defect_density": float(p @ D),
                "memory": float(dens @ n0) / d.N, "C1": float(c[1]), "_moments": (dens, second)}

    return obs


class ExactPropagator:
    """exp(-i H t) psi by a Chebyshev expansion [established numerical method].

    H is rescaled into [-1, 1] with Gershgorin bounds (diagonal = Ising energies, off-diagonal
    row sum = |h| N), so no eigensolver is needed; exp(-iHt) = e^{-ibt} sum_k (2 - delta_k0)
    (-i)^k J_k(a t) T_k(H'), truncated at K = 1.5 a t + 50 terms, past which the Bessel
    coefficients are below ~1e-16. Accurate to ~1e-12 against expm_multiply (tests), and several
    times faster at N = 18."""

    def __init__(self, d: TriangularDimers, J: float, h: float, max_spins: int = 20):
        check_exact_ceiling(d.N, max_spins)
        self.H = tfim_hamiltonian(d.N, d.bonds, J, h).tocsr()
        diag = ising_diagonal(d.N, d.bonds, J)
        r = abs(h) * d.N
        lo, hi = float(diag.min()) - r - 1e-9, float(diag.max()) + r + 1e-9
        self.a, self.b = (hi - lo) / 2, (hi + lo) / 2

    def __call__(self, psi: np.ndarray, t: float) -> np.ndarray:
        x = self.a * t
        K = int(1.5 * x + 50)
        coef = jv(np.arange(K), x)

        def Hs(v):
            return (self.H @ v - self.b * v) / self.a

        t0, t1 = psi, Hs(psi)
        out = coef[0] * t0 + 2 * (-1j) * coef[1] * t1
        for k in range(2, K):
            t0, t1 = t1, 2 * Hs(t1) - t0
            out = out + 2 * (-1j) ** k * coef[k] * t1
        return np.exp(-1j * self.b * t) * out


def floquet_resonances(d: TriangularDimers, spins0: np.ndarray, J: float) -> List[Tuple[int, float]]:
    """[(n_s, dt_res = pi/(|J| n_s))] for the non-zero n_s values present in c0 [derived]."""
    ns = ConfigEvaluator(d).equal_hex_pairs(np.asarray(spins0, dtype=np.int8).reshape(1, -1))[0]
    return [(int(k), math.pi / (abs(J) * k)) for k in sorted(set(ns.tolist()) - {0}, reverse=True)]


@dataclass
class ScanPoint:
    dt: float
    n_steps: int
    max_err: Dict[str, float]       # max over comparison times of |O_Trotter - O_exact|
    mean_err: Dict[str, float]      # mean over comparison times
    infidelity: float               # 1 - |<exact(T)|Trotter(T)>|^2


@dataclass
class ThresholdScan:
    Lx: int
    Ly: int
    kind: str
    h: float
    T: float
    cmp_every: Optional[float]      # None: compare at every Trotter time
    points: List[ScanPoint]
    resonances: List[Tuple[int, float]] = field(default_factory=list)

    def series(self, obs: str, kind: str = "max") -> Tuple[np.ndarray, np.ndarray]:
        dts = np.array([p.dt for p in self.points])
        vals = np.array([(p.max_err if kind == "max" else p.mean_err)[obs] for p in self.points])
        return dts, vals


def _steps(T: float, dt: float) -> int:
    n = int(round(T / dt))
    if abs(n * dt - T) > 1e-9 * max(1.0, T):
        raise ValueError(f"dt = {dt} does not divide T = {T}")
    return n


def trotter_error_scan(d: TriangularDimers, spins0: np.ndarray, shells: Shells, *, J: float, h: float,
                       T: float, dts: Sequence[float], max_spins: int, cmp_every: Optional[float] = None,
                       kind: str = "") -> ThresholdScan:
    """Error of the Strang Trotter evolution against exact evolution, for each dt.

    cmp_every=None compares at every Trotter time (exact propagated alongside, one Chebyshev
    call per step: fine for N <= 12). Otherwise the comparison times are the multiples of
    cmp_every (each dt must divide it), and the exact states are computed ONCE and shared by all
    dt — the affordable mode at N = 18. Guarded at the ED ceiling (2^N observable tables and a
    sparse 2^N Hamiltonian) before allocating."""
    check_exact_ceiling(d.N, max_spins)
    obs = observable_function(d, spins0, shells)
    U = ExactPropagator(d, J, h)
    diag = ising_diagonal(d.N, d.bonds, J)
    psi0 = np.zeros(1 << d.N, dtype=np.complex128)
    psi0[d.product_state_index(spins0)] = 1.0

    shared: Dict[int, Tuple[Dict[str, float], Optional[np.ndarray]]] = {}
    if cmp_every is not None:
        n_cmp = _steps(T, cmp_every)
        psi = psi0.copy()
        for k in range(1, n_cmp + 1):
            psi = U(psi, cmp_every)
            shared[k] = (obs(np.abs(psi) ** 2), psi.copy() if k == n_cmp else None)

    points = []
    for dt in dts:
        # every-step mode: run floor(T/dt) steps (dense dt grids need not divide T)
        n = _steps(T, dt) if cmp_every is not None else int(math.floor(T / dt + 1e-9))
        psi_t = psi0.copy()
        psi_e = psi0.copy()
        errs: Dict[str, List[float]] = {o: [] for o in OBS}
        every = None if cmp_every is None else _steps(cmp_every, dt)
        for step in range(1, n + 1):
            psi_t = trotter2_step(psi_t, d.N, diag, h, dt)
            if every is None:
                psi_e = U(psi_e, dt)
                ex = obs(np.abs(psi_e) ** 2)
            elif step % every == 0:
                ex, final = shared[step // every]
                if final is not None:
                    psi_e = final
            else:
                continue
            tr = obs(np.abs(psi_t) ** 2)
            for o in OBS:
                errs[o].append(abs(tr[o] - ex[o]))
        inf = 1.0 - abs(np.vdot(psi_e, psi_t)) ** 2
        points.append(ScanPoint(float(dt), n, {o: float(max(v)) for o, v in errs.items()},
                                {o: float(np.mean(v)) for o, v in errs.items()}, float(max(inf, 0.0))))
    return ThresholdScan(d.Lx, d.Ly, kind, h, T, cmp_every, points, floquet_resonances(d, spins0, J))


def loglog_slope(dts: np.ndarray, errs: np.ndarray, dt_max: float) -> float:
    """Least-squares slope of log(err) vs log(dt) over dt <= dt_max (the convergence order)."""
    m = (dts <= dt_max + 1e-12) & (errs > 0)
    return float(np.polyfit(np.log(dts[m]), np.log(errs[m]), 1)[0])


def locate_threshold(dts: np.ndarray, errs: np.ndarray, eps: float) -> Tuple[Optional[float], Optional[float]]:
    """(last dt below eps before the first crossing, first dt with err >= eps) in a sorted scan;
    the threshold lies between them. (None, None) if the scan never reaches eps."""
    order = np.argsort(dts)
    dts, errs = dts[order], errs[order]
    hit = np.nonzero(errs >= eps)[0]
    if len(hit) == 0:
        return None, None
    k = int(hit[0])
    return (float(dts[k - 1]) if k > 0 else None), float(dts[k])


@dataclass
class LateWindowBias:
    """Trotter bias of the Q3 late-window means at the working dt. The verdicts
    (src/mcmc_baseline.classify) use the SECTOR-CONDITIONED curve; the raw curve also carries the
    leakage, so both are reported, plus P_out itself (review fix M2)."""

    obs: str
    exact: float             # raw curve
    trotter: float
    late_std: float          # temporal std of the exact raw curve over the window
    cond_exact: float        # sector-conditioned curve (the verdict quantity)
    cond_trotter: float
    cond_std: float          # temporal std of the exact conditioned curve (verdict tolerance scale)


def late_window_bias(d: TriangularDimers, spins0: np.ndarray, shells: Shells, *, J: float, h: float,
                     dt: float, total_time: float, max_snapshots: int, late_fraction: float,
                     max_spins: int) -> List[LateWindowBias]:
    """Late-window means of the raw observables, Trotter (dt) vs exact, on the same snapshot grid
    as src/mcmc_baseline.relaxation_curve (record_every = ceil(n_steps / max_snapshots))."""
    check_exact_ceiling(d.N, max_spins)
    obs = observable_function(d, spins0, shells)
    n_steps = int(round(total_time / dt))
    rec = max(1, math.ceil(n_steps / max_snapshots))
    U = ExactPropagator(d, J, h)
    diag = ising_diagonal(d.N, d.bonds, J)
    i0 = d.product_state_index(spins0)
    wx, wy = d.winding_x(0), d.winding_y(0)
    in_sector = (d.total_defects() == 0) & (wx == wx[i0]) & (wy == wy[i0])

    def both(psi):
        p = np.abs(psi) ** 2
        p_in = float(p[in_sector].sum())
        raw = obs(p)
        raw["p_out"] = 1.0 - p_in
        return raw, obs(np.where(in_sector, p, 0.0) / p_in)

    psi_t = np.zeros(1 << d.N, dtype=np.complex128)
    psi_t[i0] = 1.0
    psi_e = psi_t.copy()
    times, tr, ex = [0.0], [both(psi_t)], [both(psi_e)]
    for step in range(1, n_steps + 1):
        psi_t = trotter2_step(psi_t, d.N, diag, h, dt)
        if step % rec == 0:
            psi_e = U(psi_e, rec * dt)
            times.append(step * dt)
            tr.append(both(psi_t))
            ex.append(both(psi_e))
    times = np.array(times)
    late = np.nonzero(times >= (1.0 - late_fraction) * times[-1])[0]

    def window(series, o, arm):
        if o == "C1":   # C of the window-AVERAGED moments, as src/mcmc_baseline.classify (review/09 M1)
            dens = np.mean([series[k][arm]["_moments"][0] for k in late], axis=0)
            second = np.mean([series[k][arm]["_moments"][1] for k in late], axis=0)
            return float(shell_correlations(shells, dens, second)[1])
        return float(np.mean([series[k][arm][o] for k in late]))

    def std(series, o, arm):
        return float(np.std([series[k][arm][o] for k in late]))

    out = []
    for o in OBS:
        out.append(LateWindowBias(o, window(ex, o, 0), window(tr, o, 0), std(ex, o, 0),
                                  window(ex, o, 1), window(tr, o, 1), std(ex, o, 1)))
    out.append(LateWindowBias("p_out", window(ex, "p_out", 0), window(tr, "p_out", 0), std(ex, "p_out", 0),
                              float("nan"), float("nan"), float("nan")))
    return out
