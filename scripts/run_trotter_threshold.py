"""Trotter-threshold / dt-convergence study (handoff/08 Part A1, K2) -> data/trotter_threshold.txt.

Fixed physical time T, dt scanned; the repo's 2nd-order Strang Trotter evolution (the step behind
every Q3 curve) against exact evolution (Chebyshev, src/trotter_threshold.ExactPropagator), from
the Q3 defect-free starts of the frustrated triangular TFIM (J = -1). Reports the convergence order,
the located threshold, the first-order Floquet resonances, and where the working dt = 0.25 sits,
including the Trotter bias of the Q3 late-window verdict quantities.
All settings from config.CONFIG.q3 (thr_* fields). Design and tags: src/trotter_threshold.py,
docs/q3_thermalization.md §8. Classical simulation only; NOT quantum hardware, NOT an H2 result.
Usage: python -I scripts/run_trotter_threshold.py
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.dimers import TriangularDimers  # noqa: E402
from src.mcmc_baseline import (  # noqa: E402
    ConfigEvaluator, Shells, dimer_pattern, ensemble_values, exact_references, initial_spins,
    qdm_diagonal_ensemble,
)
from src.trotter_threshold import (  # noqa: E402
    OBS, late_window_bias, locate_threshold, loglog_slope, trotter_error_scan,
)

Q = CONFIG.q3
C = CONFIG.ceilings
CAVEAT = ("# CLASSICAL noiseless simulation only (exact Chebyshev evolution vs 2nd-order Strang Trotter); "
          "NOT quantum hardware, NOT an H2 result. No noise model.")


def signal_of(d, s0):
    """|f(c0) - f_DE|: the start's own flippable-density relaxation signal (None if frozen)."""
    sh = Shells.build(d, 1)
    ex = exact_references(d, s0, sh, Q.J, Q.dt, C.ed_max_spins)
    if ex.component.dim == 1:
        return None
    de = ensemble_values(d, qdm_diagonal_ensemble(d, s0, ex.masks["component"]), dimer_pattern(d, s0), sh, Q.J, Q.dt)
    f0 = float(ConfigEvaluator(d).flippable(np.asarray(s0, dtype=np.int8).reshape(1, -1)).mean())
    return abs(f0 - de.scalars["flippable_density"])


def summarize(log, scan, signal):
    dts = np.array([p.dt for p in scan.points])
    inf = np.array([p.infidelity for p in scan.points])
    slopes = {o: loglog_slope(*scan.series(o), Q.thr_fit_dt_max) for o in OBS}
    s_inf = loglog_slope(dts, inf, Q.thr_fit_dt_max)
    log(f"  convergence order [measured, log-log fit on dt <= {Q.thr_fit_dt_max}]: "
        + ", ".join(f"{o} {v:.2f}" for o, v in slopes.items())
        + f"; infidelity {s_inf:.2f}   (expected 2 for local observables, 4 for infidelity)")
    below, above = locate_threshold(*scan.series("flippable_density"), Q.thr_eps)
    res = ", ".join(f"n_s={k}: pi/(|J| n_s)={v:.3f}" for k, v in scan.resonances)
    log(f"  first-order Floquet resonances of c0 [derived]: {res}")
    if above is None:
        log(f"  threshold (absolute): time-max flippable-density error never reaches eps={Q.thr_eps} in this scan")
    else:
        log(f"  threshold (absolute) [measured, eps={Q.thr_eps} on the time-max flippable-density error]: "
            f"in ({below:.3g}, {above:.3g}]")
    rel = (None, None)
    if signal is None:
        log("  threshold (relative): n/a — frozen start, no in-sector relaxation signal")
    else:
        eps_r = Q.thr_eps_rel * signal
        rel = locate_threshold(*scan.series("flippable_density"), eps_r)
        log(f"  threshold (relative) [measured, error >= {Q.thr_eps_rel:g} x signal |f(c0) - f_DE| = "
            f"{eps_r:.2e}]: in ({rel[0]}, {rel[1]}]")
    k = int(np.argmin(np.abs(dts - Q.dt)))
    if abs(dts[k] - Q.dt) < 1e-9:
        e = scan.points[k].max_err["flippable_density"]
        m = "n/a" if above is None else (f"{below / Q.dt:.2f}-{above / Q.dt:.2f}x dt" if below else f"<= {above / Q.dt:.2f}x dt")
        mr = "n/a" if rel[1] is None else (f"{rel[0] / Q.dt:.2f}-{rel[1] / Q.dt:.2f}x dt" if rel[0] else f"<= {rel[1] / Q.dt:.2f}x dt")
        sig = "" if signal is None else f" = {e / signal:.3f} of the signal"
        log(f"  working dt={Q.dt}: time-max flippable-density error {e:.2e} = {e / Q.thr_eps:.2f} eps{sig}; "
            f"infidelity at the last compared time {scan.points[k].infidelity:.2e}; absolute threshold at {m}; "
            f"relative threshold at {mr}")
    return below, above, rel


def table(log, scan):
    log(f"  {'dt':>7s} {'steps':>6s} " + " ".join(f"{o + '_max':>19s}" for o in OBS) + f" {'infid(T)':>10s}")
    for p in scan.points:
        log(f"  {p.dt:7.4f} {p.n_steps:6d} " + " ".join(f"{p.max_err[o]:19.3e}" for o in OBS)
            + f" {p.infidelity:10.3e}")


def main():
    out = []

    def log(line=""):
        out.append(line)
        print(line, flush=True)

    log(f"# generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/run_trotter_threshold.py (handoff/08 Part A1, K2)")
    log(CAVEAT)
    log(f"# Frustrated triangular TFIM, J={Q.J}; fixed physical time T={Q.thr_T}/|J|; start = Q3 defect-free product "
        "state c0. Error = |O_Trotter(t) - O_exact(t)| maximised over the comparison times; observables = "
        "src/dimers.py definitions as in src/mcmc_baseline.relaxation_curve (C1 = per-pair connected dimer "
        "correlation in shell r = 0.866). infid(T) = 1 - |<exact|Trotter>|^2 at the last compared time "
        "(floor(T/dt) dt <= T when dt does not divide T).")
    log("# Threshold theory [established, no numbers imported]: Heyl-Hauke-Zoller, Sci. Adv. 5, eaau8342; "
        "Yang et al., PRX Quantum 4, 030320. Resonance prediction [derived]: dt = pi/(|J| n_s) for the n_s "
        "present in c0 (src/trotter_threshold.py docstring).")
    summary = []

    start, stop, step = Q.thr_dense
    dense = np.unique(np.round(np.append(np.arange(start, stop + step / 2, step), Q.dt), 10))  # + the working dt
    log(f"\n## 1. Dense scans (every Trotter time compared; dt = {start}..{stop} step {step}; floor(T/dt) steps)")
    for Lx, Ly, kind in Q.thr_dense_cases:
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        sh = Shells.build(d, Q.n_shells)
        signal = signal_of(d, s0)
        for h in Q.thr_h:
            t0 = time.time()
            scan = trotter_error_scan(d, s0, sh, J=Q.J, h=h, T=Q.thr_T, dts=dense, max_spins=C.ed_max_spins, kind=kind)
            log(f"\n### {Lx}x{Ly} {kind} h={h} ({time.time() - t0:.0f}s)")
            b, a, rel = summarize(log, scan, signal)
            summary.append((f"{Lx}x{Ly} {kind}", h, b, a, rel, scan))
            table(log, scan)

    log(f"\n## 2. Coarse scans on the largest exact cluster (compared at multiples of {Q.thr_cmp_every}; "
        "exact states shared by all dt)")
    for Lx, Ly, kind in Q.thr_coarse_cases:
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        sh = Shells.build(d, Q.n_shells)
        signal = signal_of(d, s0)
        for h in Q.thr_coarse_h:
            t0 = time.time()
            scan = trotter_error_scan(d, s0, sh, J=Q.J, h=h, T=Q.thr_T, dts=Q.thr_coarse_dts,
                                      max_spins=C.ed_max_spins, cmp_every=Q.thr_cmp_every, kind=kind)
            log(f"\n### {Lx}x{Ly} {kind} h={h} ({time.time() - t0:.0f}s)")
            b, a, rel = summarize(log, scan, signal)
            summary.append((f"{Lx}x{Ly} {kind}", h, b, a, rel, scan))
            table(log, scan)

    log(f"\n## 3. Trotter bias of the Q3 late-window means at the working dt={Q.dt} "
        f"(late window = last {Q.late_fraction:.0%} of total time {Q.qdm_times}/h, same snapshot grid as "
        "data/q3_relaxation.txt; C1 from window-averaged moments). RAW = full state (carries the leakage); "
        "COND = sector-conditioned, the quantity the Q3 verdicts use; p_out = weight outside the defect-free W0 sector.")
    log(f"  {'case':24s} {'h':>4s} {'observable':18s} {'raw exact':>10s} {'raw bias':>10s} {'/std':>6s} "
        f"{'cond exact':>10s} {'cond bias':>10s} {'/std':>6s}")
    for Lx, Ly, kind in Q.curve_cases:
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        sh = Shells.build(d, Q.n_shells)
        for h in Q.h_curves:
            t0 = time.time()
            rows = late_window_bias(d, s0, sh, J=Q.J, h=h, dt=Q.dt, total_time=Q.qdm_times / h,
                                    max_snapshots=Q.max_snapshots, late_fraction=Q.late_fraction,
                                    max_spins=C.ed_max_spins)
            for r in rows:
                q = abs(r.trotter - r.exact) / r.late_std if r.late_std > 1e-12 else float("nan")
                qc = abs(r.cond_trotter - r.cond_exact) / r.cond_std if r.cond_std > 1e-12 else float("nan")
                log(f"  {Lx}x{Ly} {kind:18s} {h:4.2f} {r.obs:18s} {r.exact:+10.5f} {r.trotter - r.exact:+10.2e} "
                    f"{q:6.2f} {r.cond_exact:+10.5f} {r.cond_trotter - r.cond_exact:+10.2e} {qc:6.2f}")
            print(f"    ({Lx}x{Ly} h={h}: {time.time() - t0:.0f}s)", flush=True)

    log("\n## Summary: threshold brackets (absolute eps / relative to the start's signal) and where dt = 0.25 sits")
    for name, h, b, a, rel, scan in summary:
        e = {round(p.dt, 6): p.max_err["flippable_density"] for p in scan.points}.get(round(Q.dt, 6))
        res = min((v for _, v in scan.resonances), default=float("nan"))
        err = f"; error at dt=0.25 {e:.2e}" if e is not None else ""
        log(f"  {name:20s} h={h:4.2f}: absolute in ({b}, {a}]; relative in ({rel[0]}, {rel[1]}]; "
            f"lowest c0 resonance {res:.3f}{err}")
    with open(os.path.join(REPO, CONFIG.data_dir, "trotter_threshold.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote data/trotter_threshold.txt")


if __name__ == "__main__":
    main()
