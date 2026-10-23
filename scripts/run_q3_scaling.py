"""Stim prefilter for the Q3 generalization study (decision cards D1-D6, 2026-10-22).

The CHEAP stage. It spends no state vector: Stim first-order fault accounting (src/q3_scaling.py)
decides which (N, h, lam) cells of the study can resolve anything at all, so the expensive
exact-circuit sweep (scripts/run_q3_sweep.py) is only paid for where it is worth paying.

It reports, per logical size N and noise scale lam:
  * the per-Trotter-step bare fault rate and the Iceberg detected / undetected-logical rates;
  * the Iceberg post-selection survival at the reference window (t = 12, 48 steps) and the
    SURVIVAL-MATCHED window (the project lead's decision, 2026-10-22): the largest window whose
    predicted survival still clears CONFIG.q3_scaling.survival_floor;
  * expected bare faults over each field's physics window (qdm_times / h), which is why the
    unmitigated bare arm is not a Q3 measurement at larger N;
  * the keep / drop verdict per cell of the D1 x D2 x D3 grid, and for the D4 extreme combos.

Two lambda scopes are printed, because they are not the same experiment:
  * "2q"  = ("rot-zz", "syn-cx"), the classes Pauli insertion actually amplifies in the
            trajectory runners (src/noise_scaling.run_bare_scaled / run_iceberg_scaled). THIS is
            the scope the keep/drop verdict uses, since it is what the expensive stage runs.
  * "all" = every noise class present, the "all gates" row of
            research/derivations/01-noise-scaling-arm.md, kept for continuity with that derivation.

EVERY number here is a CLASSICAL PREDICTION under the ASSUMED research/06 H2 prior (first-order
fault accounting), NEVER an H2 / hardware result. Nothing touches hardware; no HQC is spent.

Usage: .venv/Scripts/python.exe -I scripts/run_q3_scaling.py
"""

from __future__ import annotations

import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from config import CONFIG
from src.noisy_q3_sweep import iceberg_physical_qubits, prior_noise
from src.q3_scaling import (
    SIZE_TO_CASE,
    faults_per_window,
    prefilter_grid,
    stim_rate_table,
    survival_curve,
    time_to_survival,
    window_steps,
)

SCOPE_2Q = ("rot-zz", "syn-cx")


def matched_window(rates, floor: float, cap: int) -> int:
    """Largest number of Trotter steps whose predicted survival is still >= floor, capped.

    Survival is exp(-(prep offset + rate * steps)) (src/q3_scaling.survival_curve), so the
    threshold is at steps = (-ln(floor) - offset) / rate; 0 means the prep offset alone is
    already below the floor."""
    budget = -math.log(floor) - rates.iceberg_detect_prep_offset
    if budget <= 0:
        return 0
    return int(min(cap, math.floor(budget / rates.iceberg_detect_per_step)))


def main() -> None:
    q3, qs, ceil = CONFIG.q3, CONFIG.q3_scaling, CONFIG.ceilings
    noise = prior_noise()
    out: list[str] = []

    def log(line: str = "") -> None:
        out.append(line)
        print(line)

    log("# Q3 generalization study - Stim prefilter (D1-D6, 2026-10-22). data/q3_scaling.txt")
    log("# CLASSICAL PREDICTION under an ASSUMED noise model (research/06 H2 prior, Stim")
    log("#   first-order fault accounting). NOT an H2 / hardware result. No HQC spent.")
    log(f"# Noise: p2={noise.p2:g}, eta={noise.zz_bias:g}, p1=pm=p_init={noise.p1:g} [assumed].")
    log(f"# Model: J={q3.J:g}, dt={q3.dt:g}; windows in units of 1/|J|. Stim treats Pauli")
    log("#   rotations as identity, so the per-step RATES are h-independent; h enters only")
    log("#   through the window length (qdm_times / h).")
    log(f"# Ceilings (SCOPE §5): state vector <= {ceil.statevector_max_spins}, ED <= "
        f"{ceil.ed_max_spins}; Stim unbounded. The PHYSICAL register (N + 4) is what counts.")
    log(f"# Survival floor for the keep verdict: {qs.survival_floor:g} [assumed]; encoded window "
        f"cap {qs.ice_window_cap} steps (t = {qs.ice_window_cap * q3.dt:g}).")

    sizes = tuple(qs.sizes_exact) + tuple(qs.sizes_stim_only)
    ref_steps = window_steps(q3.qdm_times, q3.dt)

    # ---------------------------------------------------------------- 1. rate table
    log("\n## 1. First-order per-step rates and Iceberg survival [derived accounting]")
    log(f"#  lam scope '2q' = {SCOPE_2Q} (what insertion amplifies in the trajectory runners);")
    log("#  'all' = every noise class present (research/derivations/01 'all gates' row).")
    log(f"#  survival(ref) is at the reference window {ref_steps} steps (t = {q3.qdm_times:g});")
    log("#  matched window = largest window with survival >= the floor (capped).")
    log(f"  {'N':>4s} {'case':>18s} {'phys':>5s} {'lam':>4s} {'scope':>5s} {'bare/step':>10s} "
        f"{'ice det/step':>13s} {'ice undet/step':>15s} {'prep off':>9s} {'surv(ref)':>10s} "
        f"{'matched steps':>14s} {'t_matched':>10s}")
    rates_by: dict[tuple[int, float, str], object] = {}
    for n in sizes:
        Lx, Ly, kind = SIZE_TO_CASE[n]
        for lam in qs.lams:
            for label, scope in (("2q", SCOPE_2Q), ("all", "all")):
                r = stim_rate_table(n, lam, noise, scope=scope)
                rates_by[(n, float(lam), label)] = r
                surv = float(survival_curve(r, ref_steps))
                mw = matched_window(r, qs.survival_floor, qs.ice_window_cap)
                log(f"  {n:>4d} {f'{Lx}x{Ly} {kind}':>18s} {iceberg_physical_qubits(n):>5d} "
                    f"{lam:>4g} {label:>5s} {r.bare_fault_per_step:>10.3e} "
                    f"{r.iceberg_detect_per_step:>13.3e} {r.iceberg_undetected_per_step:>15.3e} "
                    f"{r.iceberg_detect_prep_offset:>9.4f} {surv:>10.4f} {mw:>14d} "
                    f"{mw * q3.dt:>10.2f}")

    # ---------------------------------------------------------------- 2. survival levels
    log("\n## 2. Physical time (1/|J|) at which Iceberg survival falls to a level "
        "[derived accounting, 2q scope]")
    log(f"  {'N':>4s} {'lam':>4s} " + " ".join(f"{f't({lv:g})':>9s}" for lv in qs.survival_levels))
    for n in sizes:
        for lam in qs.lams:
            r = rates_by[(n, float(lam), "2q")]
            cells = " ".join(f"{time_to_survival(r, lv, q3.dt):>9.2f}" for lv in qs.survival_levels)
            log(f"  {n:>4d} {lam:>4g} {cells}")

    # ---------------------------------------------------------------- 3. bare fault budget
    log("\n## 3. Expected bare faults per shot over each field's physics window "
        "(qdm_times / h) [derived accounting, 2q scope]")
    log("#  A window carrying >> 1 fault per shot is not a Q3 measurement without mitigation.")
    log(f"  {'N':>4s} {'lam':>4s} " + " ".join(f"{f'h={h:g}':>12s}" for h in q3.h_curves))
    for n in sizes:
        for lam in qs.lams:
            r = rates_by[(n, float(lam), "2q")]
            cells = []
            for h in q3.h_curves:
                steps = window_steps(q3.qdm_times / h, q3.dt)
                cells.append(f"{faults_per_window(r, steps):>12.2f}")
            log(f"  {n:>4d} {lam:>4g} " + " ".join(cells))

    # ---------------------------------------------------------------- 4. the grid verdict
    log("\n## 4. D1 x D2 x D3 prefilter verdict for the exact-circuit stage [derived]")
    log("#  keep = the encoded arm can still be resolved at the reference window; a dropped cell "
        "keeps its BARE arm (bare + Gauss post-selection needs no code survival).")
    log("#  'all'-scope survival is printed beside the deciding 2q value for comparison.")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'surv 2q':>8s} {'surv all':>9s} "
        f"{'matched steps':>14s} {'ice verdict':>12s} {'bare window':>12s}")
    grid = prefilter_grid(qs.sizes_exact, qs.lams, q3.h_curves, noise, q3.qdm_times, q3.dt,
                          survival_floor=qs.survival_floor)
    keep_cells: list[tuple[int, float, float, int]] = []
    for cell in grid:
        r2 = rates_by[(cell.N, float(cell.lam), "2q")]
        s2 = float(survival_curve(r2, ref_steps))
        mw = matched_window(r2, qs.survival_floor, qs.ice_window_cap)
        verdict = "KEEP" if s2 >= qs.survival_floor else ("matched" if mw > 0 else "DROP")
        bare_steps = window_steps(q3.qdm_times / cell.h, q3.dt)
        log(f"  {cell.N:>4d} {cell.h:>5g} {cell.lam:>4g} {s2:>8.4f} {cell.survival:>9.4f} "
            f"{mw:>14d} {verdict:>12s} {bare_steps:>12d}")
        if mw > 0:
            keep_cells.append((cell.N, cell.h, float(cell.lam), mw))

    # ---------------------------------------------------------------- 5. extreme combos
    log("\n## 5. D4 extreme combinations [derived]")
    for n, h, lam in qs.extreme_combos:
        r = rates_by[(n, float(lam), "2q")]
        mw = matched_window(r, qs.survival_floor, qs.ice_window_cap)
        bare_steps = window_steps(q3.qdm_times / h, q3.dt)
        log(f"  N={n:<3d} h={h:<4g} lam={lam:<2g} ice matched window {mw:>3d} steps "
            f"(t = {mw * q3.dt:.2f}); bare window {bare_steps} steps; "
            f"bare faults/shot {faults_per_window(r, bare_steps):.2f}")

    # ---------------------------------------------------------------- 6. what the sweep will run
    log("\n## 6. Cells handed to the expensive stage (scripts/run_q3_sweep.py)")
    log("#  Every cell runs its BARE arm; the encoded arm runs over 'ice steps' (survival-matched).")
    log("#  Per-size trajectory counts and accumulator settings: CONFIG.q3_scaling.per_size, fixed "
        "from the D5 timing probe.")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'ice steps':>10s} {'traj bare':>10s} "
        f"{'traj ice':>9s} {'batches':>8s} {'rec every':>10s}")
    for n, h, lam, mw in keep_cells:
        ps = qs.per_size[n]
        log(f"  {n:>4d} {h:>5g} {lam:>4g} {mw:>10d} {ps['traj_bare']:>10d} {ps['traj_ice']:>9d} "
            f"{ps['batches']:>8d} {ps['record_every']:>10d}")
    log(f"# {len(keep_cells)} cells with an encoded arm, out of {len(grid)} in the grid.")

    path = os.path.join(REPO, CONFIG.data_dir, "q3_scaling.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {os.path.relpath(path, REPO)}")


if __name__ == "__main__":
    main()
