"""Noisy + Iceberg-encoded Q3 relaxation curves (handoff/08 Part B1) -> data/q3_noisy.txt.

Bare (unencoded) and Iceberg-encoded circuit-order Strang trajectories of the frustrated triangular
TFIM under the research/06 H2 PRIOR noise model (config SensitivityConfig), with exact readout
snapshots (src/noisy_q3.py). Compared with the ideal circuit and with the handoff/07 sector
baseline. All settings from config.CONFIG.q3 (noisy_* fields) and CONFIG.sensitivity.
EVERY noisy number is a CLASSICAL PREDICTION UNDER AN ASSUMED NOISE MODEL, NOT an H2 result.
Usage: python -I scripts/run_q3_noisy.py
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
from src.encoded_codes import NoiseRates, detected_total  # noqa: E402
from src.mcmc_baseline import (  # noqa: E402
    Shells, dimer_pattern, ensemble_values, exact_references, initial_spins, qdm_diagonal_ensemble,
    relaxation_curve,
)
from src.noisy_q3 import make_iceberg, run_bare, run_iceberg, run_observables  # noqa: E402

Q = CONFIG.q3
S = CONFIG.sensitivity
C = CONFIG.ceilings
P1 = S.p2_prior * S.p1_ratio
NOISE = NoiseRates(p2=S.p2_prior, p1=P1, pm=P1, p_init=P1, zz_bias=S.zz_bias_prior)
CAVEAT = ("# CLASSICAL PREDICTION UNDER AN ASSUMED NOISE MODEL (research/06 H2 prior, Pauli-trajectory "
          "simulation) — NOT an H2 / hardware result.")
OBS = ("flippable_density", "C1", "defect_density", "memory")  # "C1" = the r = 0.866 dimer shell, labelled C(0.866) in q3_relaxation/q3_size (review/11 m2)


def fmt(v, se=None):
    if not np.isfinite(v):
        return f"{'n/a':>9s}"
    return f"{v:+.4f}" + (f"±{se:.4f}" if se is not None and np.isfinite(se) else "")


def main():
    out = []

    def log(line=""):
        out.append(line)
        print(line, flush=True)

    h, dt = Q.noisy_h, Q.dt
    n_bare = int(round(Q.qdm_times / h / dt))
    log(f"# generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/run_q3_noisy.py (handoff/08 Part B1)")
    log(CAVEAT)
    log(f"# Noise model [assumed]: p2={NOISE.p2:g} after every 2q gate (fraction eta={NOISE.zz_bias:g} extra Z(x)Z on top "
        f"of a uniform 1/15 share), p1={NOISE.p1:g} uniform X/Y/Z after every 1q gate, readout flip pm={NOISE.pm:g}, "
        f"reset error p_init={NOISE.p_init:g}. No idle noise, no coherent error, no leakage, no crosstalk [assumed absent].")
    log(f"# Circuit: circuit-order Strang (X half, ZZ, X half) as src/encoded_codes; J={Q.J}, h={h}, dt={dt}. "
        "Iceberg: syndrome round (flagged X^n, Z^n) after every step; post-selection on every detector "
        "(mid-circuit and final). Snapshots = exact readout distribution at the step boundary (no shot noise); "
        f"errors are batch-means SE over {Q.noisy_batches} batches of fault patterns.")
    log("# Arms: ideal = same circuit, no noise | bare = unencoded noisy | ice = Iceberg-encoded noisy, post-selected. "
        "Modes: raw = full readout distribution | cond = additionally post-selected on the defect-free W0 sector "
        "(Gauss-law + winding detection, the handoff/02 'detection only' mitigation). acc = Iceberg survival; "
        "p_in = weight in the sector (the Gauss post-selection acceptance).")

    rng = np.random.default_rng(CONFIG.seed)
    summary = []
    for Lx, Ly, kind in Q.noisy_bare_cases:
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        sh = Shells.build(d, Q.n_shells)
        ex = exact_references(d, s0, sh, Q.J, dt, C.ed_max_spins)
        de = ensemble_values(d, qdm_diagonal_ensemble(d, s0, ex.masks["component"]), dimer_pattern(d, s0), sh, Q.J, dt)
        kw = dict(J=Q.J, h=h, dt=dt, record_every=Q.noisy_record_every, max_spins=C.ed_max_spins, mem_gb=Q.noisy_mem_gb)
        t0 = time.time()
        ideal = run_observables(d, s0, sh, run_bare(d, s0, n_steps=n_bare, noise=NoiseRates(), n_traj=1, n_batches=1,
                                                     rng=rng, **kw), C.ed_max_spins)
        bare = run_observables(d, s0, sh, run_bare(d, s0, n_steps=n_bare, noise=NOISE, n_traj=Q.noisy_traj_bare,
                                                    n_batches=Q.noisy_batches, rng=rng, **kw), C.ed_max_spins)
        tb = time.time() - t0
        ice = None
        if (Lx, Ly, kind) in Q.noisy_ice_cases:
            t0 = time.time()
            ice = run_observables(d, s0, sh, run_iceberg(d, s0, n_steps=Q.noisy_ice_steps, noise=NOISE,
                                                         n_traj=Q.noisy_traj_ice, n_batches=Q.noisy_batches,
                                                         rng=rng, **dict(kw, max_spins=C.statevector_max_spins)),
                                  C.ed_max_spins)
            ti = time.time() - t0
        # circuit-order vs the Q3 ideal (src/trotter.py ZZ-outside) curve on the same snapshot grid
        q3 = relaxation_curve(d, s0, sh, J=Q.J, h=h, dt=dt, total_time=n_bare * dt,
                              max_snapshots=n_bare // Q.noisy_record_every, max_spins=C.ed_max_spins)
        dq = {o: float(np.max(np.abs(np.interp(ideal.times, q3.times, q3.raw[o] if o != "C1" else q3.raw_shells[:, 1])
                                     - ideal.raw[o][0]))) for o in ("flippable_density", "C1", "defect_density")}
        log(f"\n## {Lx}x{Ly} start={kind} W0={ex.W0}, h={h}: bare window {n_bare} steps (t={n_bare * dt:g}), "
            f"{Q.noisy_traj_bare} trajectories ({tb:.0f}s)"
            + (f"; Iceberg [[{d.N + 2},{d.N},2]] ({d.N + 4} physical) window {Q.noisy_ice_steps} steps "
               f"(t={Q.noisy_ice_steps * dt:g}), {Q.noisy_traj_ice} trajectories ({ti:.0f}s)" if ice else
               "; no Iceberg arm (Iceberg needs an even number of logical qubits)" if d.N % 2 else ""))
        log(f"  sector baseline B_W0 / DE (handoff/07): flippable {ex.sector.scalars['flippable_density']:.4f} / "
            f"{de.scalars['flippable_density']:.4f}; C1 {ex.sector.shells[1]:+.4f} / {de.shells[1]:+.4f}")
        log("  ideal circuit-order vs src/trotter.py-order ideal (both 2nd-order Strang) [measured]: max |diff| over the window "
            + ", ".join(f"{o} {v:.1e}" for o, v in dq.items()))
        if ice:
            prog = make_iceberg(d, s0, Q.J, h, dt)
            pred = [float(np.exp(-detected_total(prog, NOISE, int(s)))) if s > 0 else float("nan")
                    for s in np.round(ice.times / dt).astype(int)]
            ks = [k for k in range(len(ice.times)) if ice.times[k] in (dt * 8, dt * 16, dt * 32, dt * 48)]
            log("  Iceberg acceptance, local-sim [measured, ± binomial SE; points share trajectories] vs Stim "
                "first-order exp(-detected_total) [derived]: "
                + "; ".join(f"t={ice.times[k]:g}: {ice.acceptance[k]:.3f}±{np.sqrt(ice.acceptance[k] * (1 - ice.acceptance[k]) / Q.noisy_traj_ice):.3f}"
                            f" vs {pred[k]:.3f}" for k in ks))
        log(f"  {'t':>5s} {'acc':>6s} {'p_in':>6s} | flippable: {'ideal':>8s} {'ideal cond':>10s} {'bare raw':>15s} {'bare cond':>15s} "
            f"{'ice raw':>15s} {'ice cond':>15s} | C1: {'ideal':>8s} {'bare raw':>8s} {'bare cond':>9s} {'ice cond':>9s} "
            f"| defect: {'ideal':>8s} {'bare':>8s} {'ice':>8s}")
        for k in range(0, len(bare.times), 2):
            t = bare.times[k]
            j = int(np.searchsorted(ice.times, t)) if ice is not None else -1
            has_i = ice is not None and j < len(ice.times) and abs(ice.times[j] - t) < 1e-9
            def g(run, mode, o, idx):
                v, se = getattr(run, mode)[o]
                return v[idx], se[idx]
            ir = g(ice, "raw", "flippable_density", j) if has_i else (np.nan, np.nan)
            ic = g(ice, "cond", "flippable_density", j) if has_i else (np.nan, np.nan)
            icc = g(ice, "cond", "C1", j) if has_i else (np.nan, np.nan)
            idf = g(ice, "raw", "defect_density", j) if has_i else (np.nan, np.nan)
            log(f"  {t:5.1f} {ice.acceptance[j] if has_i else np.nan:6.3f} {bare.p_in[k]:6.3f} | "
                f"{'':11s}{ideal.raw['flippable_density'][0][k]:+.4f} {ideal.cond['flippable_density'][0][k]:+10.4f} "
                f"{fmt(*g(bare, 'raw', 'flippable_density', k)):>15s} "
                f"{fmt(*g(bare, 'cond', 'flippable_density', k)):>15s} {fmt(*ir):>15s} {fmt(*ic):>15s} | "
                f"{ideal.raw['C1'][0][k]:+.4f} {fmt(g(bare, 'raw', 'C1', k)[0]):>8s} {fmt(g(bare, 'cond', 'C1', k)[0]):>9s} "
                f"{fmt(icc[0]):>9s} | {ideal.raw['defect_density'][0][k]:+.4f} {fmt(g(bare, 'raw', 'defect_density', k)[0]):>8s} "
                f"{fmt(idf[0]):>8s}")
        summary.append((Lx, Ly, kind, ex, de, ideal, bare, ice))

    log("\n## Accuracy vs the ideal circuit: mean |O_noisy - O_ideal| over a window, with the shot-cost factor "
        "(1/acceptance) of each mode [measured; classical prediction under the assumed model]")
    log("#   Reference: raw modes vs the ideal RAW curve; Gauss-post-selected modes vs the ideal SECTOR-CONDITIONED curve "
        "(the quantity they estimate) AND, in brackets, vs the ideal raw curve. 'SE' = mean per-point batch SE of the "
        "mode: a residual comparable to it is at the statistical floor, not resolved.")
    for Lx, Ly, kind, ex, de, ideal, bare, ice in summary:
        windows = [("early t<=%g" % (Q.noisy_ice_steps * dt), bare.times <= Q.noisy_ice_steps * dt + 1e-9),
                   ("late (last half of %g)" % bare.times[-1], bare.times >= bare.times[-1] / 2)]
        for wname, wb in windows:
            for o in ("flippable_density", "C1"):
                ref = ideal.raw[o][0]
                rows = [("bare raw", bare.raw[o][0], bare.raw[o][1], np.ones_like(bare.times)),
                        ("bare + Gauss post-sel", bare.cond[o][0], bare.cond[o][1], bare.p_in)]
                line = []
                for name, v, se, a in rows:
                    m = wb & np.isfinite(v)
                    if "Gauss" in name:
                        line.append(f"{name}: {np.mean(np.abs(v[m] - ideal.cond[o][0][m])):.4f} "
                                    f"[vs raw {np.mean(np.abs(v[m] - ref[m])):.4f}] (SE {np.nanmean(se[m]):.4f}; "
                                    f"cost x{1 / np.mean(a[m]):.2f})")
                    else:
                        line.append(f"{name}: {np.mean(np.abs(v[m] - ref[m])):.4f} (SE {np.nanmean(se[m]):.4f}; "
                                    f"cost x{1 / np.mean(a[m]):.2f})")
                if ice is not None and wname.startswith("early"):
                    for name, v, se, a in (("Iceberg", ice.raw[o][0], ice.raw[o][1], ice.acceptance),
                                           ("Iceberg + Gauss", ice.cond[o][0], ice.cond[o][1], ice.acceptance * ice.p_in)):
                        ti = ice.times
                        refr = np.interp(ti, ideal.times, ref)
                        refi = np.interp(ti, ideal.times, ideal.cond[o][0]) if "Gauss" in name else refr
                        m = np.isfinite(v) & (a > 0)
                        extra = f" [vs raw {np.mean(np.abs(v[m] - refr[m])):.4f}]" if "Gauss" in name else ""
                        line.append(f"{name}: {np.mean(np.abs(v[m] - refi[m])):.4f}{extra} (SE {np.nanmean(se[m]):.4f}; "
                                    f"cost x{1 / np.mean(a[m]):.1f}, final x{1 / a[m][-1]:.0f})")
                log(f"  {Lx}x{Ly} {kind:12s} {wname:22s} {o:18s} " + "; ".join(line))

    log("\n## Late-window Q3 comparison for the noisy bare arm (sector-conditioned, as the handoff/07 verdict) "
        "[measured; classical prediction]")
    for Lx, Ly, kind, ex, de, ideal, bare, ice in summary:
        late = bare.times >= bare.times[-1] / 2
        for o, b, dv in (("flippable_density", ex.sector.scalars["flippable_density"], de.scalars["flippable_density"]),
                         ("C1", ex.sector.shells[1], de.shells[1])):
            v = bare.cond[o][0][late]
            vi = ideal.cond[o][0][late]
            log(f"  {Lx}x{Ly} {kind:12s} {o:18s} noisy cond late mean {np.mean(v):+.4f} (std {np.std(v):.4f}); "
                f"ideal cond {np.mean(vi):+.4f}; B_W0 {b:+.4f}; DE {dv:+.4f}; Gauss acceptance late {np.mean(bare.p_in[late]):.3f}")
    with open(os.path.join(REPO, CONFIG.data_dir, "q3_noisy.txt"), "w") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote data/q3_noisy.txt")


if __name__ == "__main__":
    main()
