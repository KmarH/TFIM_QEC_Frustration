"""Q3 thermalization: sector-restricted MCMC ergodic baseline + Trotter relaxation overlay (handoff/07).

Writes
  data/mcmc_baseline.txt  — sector census, MCMC vs brute-force exact per-sector averages, MCMC-only
                            baselines beyond the exact ceiling (incl. the reference 9x6 torus);
  data/q3_relaxation.txt  — Trotter relaxation curves (raw and sector-conditioned) overlaid on the
                            W0 baseline, the measured O((h/|J|)^2) leakage band, and the verdicts.
All settings from config.CONFIG.q3. Design and tags: docs/q3_thermalization.md.
Every number is a CLASSICAL statistical reference or a classical simulation of the ideal circuit,
not quantum hardware, not an H2 result. No noise model is involved anywhere.
Usage: python -I scripts/run_q3_baseline.py
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.dimers import TriangularDimers  # noqa: E402
from src.mcmc_baseline import (  # noqa: E402
    SCALARS, ConfigEvaluator, Shells, classify, dimer_pattern, ensemble_values, exact_references,
    initial_spins, leak_scaling, qdm_diagonal_ensemble, relaxation_curve, sample_sector,
    sector_census,
)

Q = CONFIG.q3
C = CONFIG.ceilings
CAVEAT = ("# CLASSICAL statistical reference (uniform ensemble over a winding sector) and classical "
          "noiseless state-vector simulation only; NOT quantum hardware, NOT an H2 result.")
with open(os.path.join(REPO, Q.leak_table), encoding="utf-8") as _fh:   # h range of the measured leak table
    TABLE_HMAX = max(float(v) for v in next(l for l in _fh if l.startswith("h_scan")).split("=")[1].split())
DISCRIMINATING = ("flippable_density", "memory")   # rho_* are fixed by W0 and defect density is 0 in-sector


def mcmc(d, s0, sh, seed):
    return sample_sector(d, s0, sh, J=Q.J, dt=Q.dt, n_chains=Q.n_chains, n_sweeps=Q.n_sweeps,
                         burn_in=Q.burn_in, rng=np.random.default_rng(seed))


def fmt_est(e):
    return f"{e.value:.5f} ± {e.se:.5f} (naive {e.se_naive:.5f}, tau_int {e.tau_int:.2f})"


def _numeric(lines):
    """File content minus what legitimately changes between identical reruns (timestamp, wall
    times, this provenance line)."""
    return [re.sub(r"; \d+s$", "", l) for l in lines
            if not l.startswith("# generated") and not l.startswith("# provenance")
            and not l.startswith("# content-sha256")]


def content_hash(lines):
    """sha256 of the numeric content (review/11 m3), so 'identical rerun' is checkable without git:
    hashlib.sha256("\n".join(_numeric(lines)).encode()).hexdigest() on the file's lines."""
    return hashlib.sha256("\n".join(_numeric(lines)).encode()).hexdigest()


def provenance(path, new_lines):
    """Header line saying whether the numbers match the file being replaced (review/10 m3): the
    MCMC is seeded (CONFIG.seed), so a rerun must reproduce them exactly."""
    if not os.path.exists(path):
        return "# provenance: first generation of this file"
    with open(path, encoding="utf-8") as fh:
        old = fh.read().splitlines()
    stamp = next((l for l in old if l.startswith("# generated")), "# generated ?")[2:]
    same = _numeric(old) == _numeric("\n".join(new_lines).splitlines())   # entries may hold "\n"
    return ("# provenance: numeric content IDENTICAL to the file it replaced (" + stamp + "); only timestamp/timings differ"
            if same else "# provenance: numeric content CHANGED vs the file it replaced (" + stamp + ")")


def baseline_file(path, seed):
    out = []
    log = out.append
    log(f"# generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/run_q3_baseline.py (handoff/07)")
    log(CAVEAT)
    log(f"# Frustrated triangular TFIM, J={Q.J} (AFM in our sign), dt={Q.dt}. Ensemble: UNIFORM over the "
        "flip-connected component of c0 in its defect-free winding sector W0 [derived].")
    log(f"# MCMC: {Q.n_chains} independent chains from c0, {Q.burn_in} burn-in + {Q.n_sweeps} measured sweeps "
        "(1 sweep = N single-site flippable-flip attempts). SE = std(chain means)/sqrt(chains) [autocorrelation-aware]; "
        "naive SE and tau_int = (SE/naive)^2/2 shown beside it. Shell correlations: jackknife over chains.")
    log("# Observables (src/dimers.py definitions): defect_density = <sum_t D_t>/2N; flippable_density = <sum_s Pi_s>/N; "
        "rho_h/v/d = orientation-mean <n_b>; memory = sum_b n_b(c0)<n_b>/N; C(r) = per-pair connected <n_a n_b> "
        "in bond-midpoint distance shell r (Euclidean, as dimer_correlation_by_distance); "
        "dressing <g> = O(h^2) dressed-defect coefficient (src/mcmc_baseline.py docstring).")

    log("\n## 1. Sector census (exact enumeration, N <= ED ceiling): W, sector size, #flip components, largest")
    for Lx, Ly, _ in Q.exact_cases:
        d = TriangularDimers(Lx, Ly)
        cen = sector_census(d, C.ed_max_spins)
        log(f"{Lx}x{Ly} (N={d.N}): " + "; ".join(f"W={W} size {s} comps {n} largest {m}" for W, s, n, m in cen))

    log("\n## 2. MCMC vs brute-force exact per-sector average [measured]; z = (MCMC - exact)/SE")
    log("##    'global' = uniform over ALL defect-free configurations (winding-blind) — shown to expose the "
        "spurious value a whole-space ergodic average would give")
    for k, (Lx, Ly, kind) in enumerate(Q.exact_cases):
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        sh = Shells.build(d, Q.n_shells)
        t0 = time.time()
        ex = exact_references(d, s0, sh, Q.J, Q.dt, C.ed_max_spins)
        res = mcmc(d, s0, sh, seed + k)
        log(f"\n{Lx}x{Ly} start={kind} W0={ex.W0}: component {ex.component.dim} = sector {ex.sector.dim} "
            f"(components in sector: {ex.n_components_in_sector}), defect-free total {ex.global_.dim}; "
            f"acceptance {res.accept_rate:.3f}; {time.time() - t0:.0f}s")
        for o in SCALARS:
            e, x, g = res.scalars[o], ex.sector.scalars[o], ex.global_.scalars[o]
            z = (e.value - x) / e.se if e.se > 1e-12 else 0.0
            tag = "" if o in DISCRIMINATING else "   (fixed by W0 in-sector [derived]; not discriminating)"
            log(f"  {o:18s} exact {x:.5f}  MCMC {fmt_est(e)}  z={z:+.2f}  global {g:.5f}{tag}")
        e, x, g = res.dressing, ex.sector.dressing, ex.global_.dressing
        log(f"  {'dressing <g>':18s} exact {x:.5f}  MCMC {fmt_est(e)}  z={(e.value - x) / e.se:+.2f}  global {g:.5f}")
        for i, r in enumerate(sh.r):
            (v, se), x, g = res.shells[i], ex.sector.shells[i], ex.global_.shells[i]
            z = (v - x) / se if se > 1e-12 else 0.0
            tag = "   (near-fixed: one dimer per triangle; not discriminating)" if i == 0 else ""
            log(f"  C(r={r:<8g})       exact {x:+.5f}  MCMC {v:+.5f} ± {se:.5f}  z={z:+.2f}  global {g:+.5f}{tag}")

    log("\n## 3. MCMC-only per-sector baselines beyond the exact ceiling [measured, MCMC; no exact check possible]")
    log("##    Sector = component of c0 by construction; whether it is the whole W0 sector at this size is "
        "[unverified] (true on every torus enumerated, N <= 20).")
    for k, (Lx, Ly, kind) in enumerate(Q.mcmc_only_cases):
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        sh = Shells.build(d, Q.n_shells)
        t0 = time.time()
        res = mcmc(d, s0, sh, seed + 100 + k)
        log(f"\n{Lx}x{Ly} (N={d.N}) start={kind} W0={res.W0}: acceptance {res.accept_rate:.3f}; {time.time() - t0:.0f}s")
        for o in SCALARS:
            log(f"  {o:18s} MCMC {fmt_est(res.scalars[o])}")
        log(f"  {'dressing <g>':18s} MCMC {fmt_est(res.dressing)}")
        for i, r in enumerate(sh.r):
            v, se = res.shells[i]
            log(f"  C(r={r:<8g})       MCMC {v:+.5f} ± {se:.5f}")
    out.insert(2, provenance(path, out))
    lines = "\n".join(out).splitlines()   # entries may hold "\n"
    out.insert(3, "# content-sha256 (numeric lines, i.e. minus generated/provenance/this line and "
               "trailing wall times): " + content_hash(lines))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def relaxation_file(path, seed):
    out = []
    log = out.append
    log(f"# generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/run_q3_baseline.py (handoff/07)")
    log(CAVEAT)
    log(f"# Noiseless 2nd-order Trotter (src/trotter.evolve, record_every) from a defect-free product state; "
        f"J={Q.J}, dt={Q.dt}, total time = {Q.qdm_times}/h (H_QDM time unit 1/h); late window = last "
        f"{Q.late_fraction:.0%} of the curve.")
    log("# raw = <O>(t); cond = <O> conditioned on the defect-free W0 sector; P_out = 1 - P(defect-free and W=W0); "
        "P_wleak = P(W(cut 0) != W0) (the data/gauss_law_scaling.txt quantity).")
    log("# Baseline B_W0 = exact uniform sector average (= MCMC within SE, data/mcmc_baseline.txt). "
        "DE = exact H_QDM diagonal ensemble from c0 on this cluster (finite-size diagnostic, quantum, first order).")
    log("# Leakage band: |raw - cond| <= P_out * range(O) EXACTLY [derived]; 'toward_global' = P_out*(global - B_W0) "
        "is the shift IF the leaked weight looked like the winding-blind average [inferred].")
    log("# Verdict tolerance = late temporal std of cond + 2*SE(B_W0) (finite cluster; operational, docs/q3_thermalization.md §5). "
        "'indistinguishable' = within tolerance of BOTH B_W0 and DE.")
    log("# C(r) late values = C(r) of the late-window-AVERAGED moments <n_a>, <n_a n_b> (not the average of C(r;t)); "
        "std = temporal std of C(r;t). The leak-scaling table is time-averaged over T=20/|J| from t=0, the runs over "
        "the late half of 12/h, so the prediction is a cross-check, not a like-for-like fit.")
    curves = []
    for Lx, Ly, kind in Q.curve_cases:
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        sh = Shells.build(d, Q.n_shells)
        ex = exact_references(d, s0, sh, Q.J, Q.dt, C.ed_max_spins)
        n0 = dimer_pattern(d, s0)
        de = ensemble_values(d, qdm_diagonal_ensemble(d, s0, ex.masks["component"]), n0, sh, Q.J, Q.dt)
        frozen = ex.component.dim == 1
        g0 = float(ConfigEvaluator(d).dressing(np.asarray(s0, dtype=np.int8).reshape(1, -1), Q.J, Q.dt)[0])
        fit = leak_scaling(os.path.join(REPO, Q.leak_table), f"{Lx}x{Ly} {kind}", Q.dt)
        for h in Q.h_curves:
            t0 = time.time()
            c = relaxation_curve(d, s0, sh, J=Q.J, h=h, dt=Q.dt, total_time=Q.qdm_times / h,
                                 max_snapshots=Q.max_snapshots, max_spins=C.ed_max_spins)
            late = c.times >= (1 - Q.late_fraction) * c.times[-1]
            log(f"\n## {Lx}x{Ly} start={kind} W0={ex.W0} h={h} (component {ex.component.dim}"
                f"{', FROZEN: no H_QDM dynamics' if frozen else ''}); {time.time() - t0:.0f}s")
            pw = float(c.p_wleak[late].mean())
            li = np.nonzero(late)[0]
            p1, p2 = float(c.p_out[li[: len(li) // 2]].mean()), float(c.p_out[li[len(li) // 2:]].mean())
            drift = (f"; NON-STATIONARY leak: P_out rises {p1:.3f} -> {p2:.3f} across the late window"
                     if p2 > 1.2 * p1 else "")
            pred = f"{fit[0] * h ** fit[1]:.3e} (A h^s, s={fit[1]:.2f}, gauss_law_scaling.txt)" if fit else "n/a (no row in the scaling table)"
            if fit and h > TABLE_HMAX + 1e-12:
                pred += f" — EXTRAPOLATED beyond the table's h <= {TABLE_HMAX:g}"
            log(f"  leakage [measured]: late P_out {float(c.p_out[late].mean()):.3e}; late P_wleak {pw:.3e}; "
                f"scaling-table prediction of P_wleak {pred}{drift}")
            rd = float(c.raw['defect_density'][late].mean())
            ps, pd = h * h * (ex.sector.dressing + g0), h * h * (de.dressing + g0)
            log(f"  defect density [measured] late raw {rd:.3e}; dressed prediction h^2(<g>+g(c0)) "
                f"[derived, 1st order]: {ps:.3e} with <g>_W0 (ratio {rd / ps:.3f}), {pd:.3e} with <g>_DE (ratio {rd / pd:.3f}); "
                "in-sector baseline 0 exactly")
            log(f"  {'observable':18s} {'B_W0':>9s} {'DE':>9s} {'global':>9s} {'late_raw':>9s} {'late_cond':>9s} "
                f"{'std':>7s} {'shift':>10s} {'bound':>9s} {'tow_glob':>10s}  verdict")
            rows = [(o, None, ex.sector.scalars[o], de.scalars[o], ex.global_.scalars[o]) for o in SCALARS if o != "defect_density"]
            rows += [(f"C(r={r:g})", i, ex.sector.shells[i], de.shells[i], ex.global_.shells[i]) for i, r in enumerate(sh.r)]
            for name, shell, b, dev, gl in rows:
                v = classify(c, name, b, 0.0, global_value=gl, de_value=dev, late_fraction=Q.late_fraction,
                             frozen=frozen, shell=shell)
                note = ("  (fixed by W0 in-sector; not discriminating)" if name.startswith("rho_") else
                        "  (near-fixed: one dimer per triangle; not discriminating)" if shell == 0 else "")
                log(f"  {name:18s} {b:+9.5f} {dev:+9.5f} {gl:+9.5f} {v.late_raw:+9.5f} {v.late_cond:+9.5f} "
                    f"{v.late_std:7.4f} {v.shift:+10.2e} {v.envelope:9.2e} {v.toward_global:+10.2e}  {v.label}{note}")
            curves.append((f"{Lx}x{Ly} {kind} h={h}", ex, de, c))
    log("\n## Curves (every 4th snapshot): t, raw/cond flippable_density, raw/cond memory, raw/cond C(r1), P_out, P_wleak")
    for name, ex, de, c in curves:
        log(f"# {name}: B_W0 flippable {ex.sector.scalars['flippable_density']:.5f}, memory "
            f"{ex.sector.scalars['memory']:.5f}, C(r1) {ex.sector.shells[1]:+.5f}; DE {de.scalars['flippable_density']:.5f}, "
            f"{de.scalars['memory']:.5f}, {de.shells[1]:+.5f}")
        for j in range(0, len(c.times), 4):
            log(f"{name:24s} {c.times[j]:7.2f} {c.raw['flippable_density'][j]:.5f} {c.cond['flippable_density'][j]:.5f} "
                f"{c.raw['memory'][j]:.5f} {c.cond['memory'][j]:.5f} {c.raw_shells[j, 1]:+.5f} {c.cond_shells[j, 1]:+.5f} "
                f"{c.p_out[j]:.3e} {c.p_wleak[j]:.3e}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


def main():
    seed = CONFIG.seed
    data = os.path.join(REPO, CONFIG.data_dir)
    t0 = time.time()
    baseline_file(os.path.join(data, "mcmc_baseline.txt"), seed)
    print(f"wrote data/mcmc_baseline.txt ({time.time() - t0:.0f}s)")
    t0 = time.time()
    relaxation_file(os.path.join(data, "q3_relaxation.txt"), seed)
    print(f"wrote data/q3_relaxation.txt ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
