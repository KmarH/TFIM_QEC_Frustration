"""Expensive stage of the Q3 generalization study: one (N, h, lam) cell per process.

The study generalizes the single-cell Iceberg-vs-Gauss-law result of docs/q3_thermalization.md
§9.2 (N = 12, h = 0.3, lam = 1) over size (D1), field (D2) and noise scale (D3). Each cell is an
independent Pauli-trajectory Monte-Carlo run, so cells are run as separate processes - locally and
on the project's other two machines - and merged afterwards. A cell that dies costs one cell.

EVERY number produced here is a CLASSICAL PREDICTION under the ASSUMED research/06 H2 prior
(Pauli-trajectory simulation), NEVER an H2 / hardware result. Nothing touches hardware; no HQC.

Reuse only: src/noisy_q3_sweep.run_noisy_sweep (arms) and .score_cell (the §9.2 metric, lifted
from scripts/run_q3_noisy.py so generalized cells stay comparable to the published one).

Usage
  one cell:   .venv/Scripts/python.exe -I scripts/run_q3_sweep.py --cell 12:0.3:1 [--ice-steps 48]
  bare only:  ... --cell 20:0.5:3 --arms bare
  merge all:  .venv/Scripts/python.exe -I scripts/run_q3_sweep.py --merge
Per-cell JSON lands in runs/q3_sweep/ (gitignored); --merge writes data/q3_sweep.txt.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import socket
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from config import CONFIG
from src.encoded_codes import NoiseRates
from src.noisy_q3_sweep import (
    iceberg_physical_qubits,
    prior_noise,
    run_noisy_sweep,
    score_cell,
)
from src.q3_scaling import SIZE_TO_CASE

WORK_DIR = os.path.join(REPO, "runs", "q3_sweep")
CAVEAT = ("CLASSICAL PREDICTION under an ASSUMED noise model (research/06 H2 prior, "
          "Pauli-trajectory MC). NOT an H2 / hardware result.")


def _jsonable(obj):
    if isinstance(obj, np.ndarray):
        return [None if not np.isfinite(x) else float(x) for x in obj.ravel()]
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not np.isfinite(float(obj)) else float(obj)
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    return obj


def _arm_payload(arm: dict | None) -> dict | None:
    if arm is None:
        return None
    return {k: _jsonable(v) for k, v in arm.items()}


def run_one(n_logical: int, h: float, lam: float, *, ice_steps: int | None, arms: str,
            traj_bare: int | None = None, traj_ice: int | None = None,
            batches: int | None = None, record_every: int | None = None,
            mem_gb: float | None = None) -> dict:
    """Run one cell (its noisy arms plus the matching ideal reference) and score it."""
    q3, qs = CONFIG.q3, CONFIG.q3_scaling
    case = SIZE_TO_CASE[n_logical]
    ps = qs.per_size.get(n_logical, {})
    traj_bare = int(ps.get("traj_bare", q3.noisy_traj_bare) if traj_bare is None else traj_bare)
    traj_ice = int(ps.get("traj_ice", q3.noisy_traj_ice) if traj_ice is None else traj_ice)
    batches = int(ps.get("batches", q3.noisy_batches) if batches is None else batches)
    record_every = int(ps.get("record_every", q3.noisy_record_every)
                       if record_every is None else record_every)
    mem_gb = float(ps.get("mem_gb", q3.noisy_mem_gb) if mem_gb is None else mem_gb)
    common = {"ice_steps": ice_steps, "record_every": record_every, "mem_gb": mem_gb}

    t0 = time.perf_counter()
    # The ideal reference is the SAME circuit with every rate 0. One zero-noise bare run is enough:
    # the encoded arm is transparent at zero noise (tested, docs/q3_thermalization.md §9.1), and its
    # curve is read off this one by interpolation, as scripts/run_q3_noisy.py does.
    ideal = run_noisy_sweep([case], [h], [1], n_traj_bare=1, n_traj_ice=1, n_batches=1,
                            seed=CONFIG.seed, noise=NoiseRates(), arms="bare", **common)
    t_ideal = time.perf_counter() - t0

    # Phase markers: a cell otherwise prints nothing until it finishes, which made a 10-hour run
    # indistinguishable from a hung one (2026-10-23). Cheap, and the only progress signal there is.
    print(f"[{time.strftime('%H:%M:%S')}] ideal done in {t_ideal:.0f} s; starting noisy arms "
          f"(N={n_logical}, h={h:g}, lam={lam:g}, traj {traj_bare}/{traj_ice}, arms={arms})",
          flush=True)
    t0 = time.perf_counter()
    noisy = run_noisy_sweep([case], [h], [lam], n_traj_bare=traj_bare, n_traj_ice=traj_ice,
                            n_batches=batches, seed=CONFIG.seed, noise=prior_noise(),
                            return_meta=True, arms=arms, **common)
    t_noisy = time.perf_counter() - t0
    print(f"[{time.strftime('%H:%M:%S')}] noisy arms done in {t_noisy:.0f} s", flush=True)

    ideal_arm = ideal[(*case, h, 1)]["bare"]
    cell = noisy[(*case, h, lam)]
    scores = score_cell(ideal_arm, cell["bare"], cell["ice"])
    noise = prior_noise()
    return {
        "caveat": CAVEAT,
        "cell": {"N": n_logical, "case": list(case), "h": h, "lam": lam,
                 "physical_qubits": iceberg_physical_qubits(n_logical) if n_logical % 2 == 0 else 0,
                 "ice_steps": ice_steps if ice_steps is not None else CONFIG.q3.noisy_ice_steps,
                 "arms": arms},
        "settings": {"traj_bare": traj_bare, "traj_ice": traj_ice, "batches": batches,
                     "record_every": record_every, "mem_gb": mem_gb, "seed": CONFIG.seed,
                     "J": CONFIG.q3.J, "dt": CONFIG.q3.dt},
        "noise": {"p2": noise.p2, "p1": noise.p1, "pm": noise.pm, "p_init": noise.p_init,
                  "zz_bias": noise.zz_bias, "status": "assumed (research/06 H2 prior)"},
        "provenance": {"host": socket.gethostname(), "platform": platform.platform(),
                       "python": platform.python_version(),
                       "seconds_ideal": round(t_ideal, 1), "seconds_noisy": round(t_noisy, 1)},
        "ideal": _arm_payload(ideal_arm),
        "bare": _arm_payload(cell["bare"]),
        "ice": _arm_payload(cell["ice"]),
        "scores": [vars(s) | {"resolved": s.resolved} for s in scores],
    }


def _cell_name(n: int, h: float, lam: float) -> str:
    return f"cell_N{n}_h{h:g}_lam{lam:g}.json"


def merge() -> None:
    """Merge every per-cell JSON in runs/q3_sweep/ into data/q3_sweep.txt."""
    q3 = CONFIG.q3
    files = sorted(f for f in os.listdir(WORK_DIR) if f.startswith("cell_") and f.endswith(".json"))
    if not files:
        raise SystemExit(f"no per-cell results in {WORK_DIR}")
    cells = []
    for f in files:
        with open(os.path.join(WORK_DIR, f), encoding="utf-8") as fh:
            cells.append(json.load(fh))
    cells.sort(key=lambda c: (c["cell"]["N"], c["cell"]["h"], c["cell"]["lam"]))

    out: list[str] = []

    def log(line: str = "") -> None:
        out.append(line)

    log("# Q3 generalization study - noisy sweep over (N, h, lam). data/q3_sweep.txt")
    log(f"# {CAVEAT}")
    log("# Decision cards D1-D6 (project lead, 2026-10-22). Generalizes the single cell of")
    log("#   docs/q3_thermalization.md §9.2 (N = 12, h = 0.3, lam = 1; data/q3_noisy.txt).")
    log(f"# Model: J = {q3.J:g}, dt = {q3.dt:g}; bare window = qdm_times / h; encoded window is")
    log("#   SURVIVAL-MATCHED per size (the largest window whose predicted detector survival")
    log("#   clears the floor; data/q3_scaling.txt), so encoded cells are compared at matched")
    log("#   survival, NOT at a matched window. Each cell states its own window.")
    log("# lam > 1 amplifies the 2q channel by Pauli insertion on BOTH arms (D6:")
    log("#   src/noise_scaling.run_bare_scaled / run_iceberg_scaled); 1q and SPAM stay at lam = 1.")
    log("# 'resolved' = the residual exceeds the mode's own mean batch SE. A residual at or below")
    log("#   the SE is NOT resolved: it is the statistical floor, not a win for either arm.")

    log("\n## 1. Cells run [measured]")
    log(f"  {'N':>4s} {'case':>18s} {'h':>5s} {'lam':>4s} {'phys':>5s} {'ice steps':>10s} "
        f"{'traj b/i':>10s} {'batches':>8s} {'host':>16s} {'py':>8s} {'s noisy':>9s}")
    for c in cells:
        cc, st, pr = c["cell"], c["settings"], c["provenance"]
        log(f"  {cc['N']:>4d} {'x'.join(map(str, cc['case'][:2])) + ' ' + cc['case'][2]:>18s} "
            f"{cc['h']:>5g} {cc['lam']:>4g} {cc['physical_qubits']:>5d} {cc['ice_steps']:>10d} "
            f"{f"{st['traj_bare']}/{st['traj_ice']}":>10s} {st['batches']:>8d} "
            f"{pr['host'][:16]:>16s} {pr['python']:>8s} {pr['seconds_noisy']:>9.0f}")

    log("\n## 2. Accuracy vs the ideal circuit and shot cost, per mode "
        "[measured; classical prediction]")
    log("#  residual = mean |O_noisy - O_ideal| over the window. Raw modes are scored against the")
    log("#  ideal RAW curve; Gauss modes against the ideal SECTOR-CONDITIONED curve (what they")
    log("#  estimate), with [vs raw] alongside. cost = 1/mean(acceptance); final = at the last point.")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'window':>7s} {'mode':>16s} {'residual':>9s} "
        f"{'[vs raw]':>9s} {'SE':>8s} {'resolved':>9s} {'cost':>7s} {'final':>7s} {'pts':>4s}")
    for c in cells:
        cc = c["cell"]
        for s in c["scores"]:
            # raw modes have no "vs conditioned ideal" counterpart: print "-", never a bare nan
            v_raw = s["residual_vs_raw"]
            vr = f"{v_raw:.4f}" if v_raw is not None and math.isfinite(v_raw) else "-"
            log(f"  {cc['N']:>4d} {cc['h']:>5g} {cc['lam']:>4g} {s['window']:>7s} "
                f"{s['mode']:>16s} {s['residual']:>9.4f} {vr:>9s} {s['se']:>8.4f} "
                f"{s['resolved']!s:>9s} {s['cost']:>7.2f} {s['cost_final']:>7.1f} "
                f"{s['n_points']:>4d}")

    log("\n## 3. Iceberg vs bare + Gauss, head to head (the §9.2 question) "
        "[measured; classical prediction]")
    log("#  The published N = 12, h = 0.3, lam = 1 cell: bare + Gauss 0.0017 +- 0.0004 at x1.43")
    log("#  shots vs Iceberg 0.019 +- 0.008 at x3.1. 'verdict' compares the early-window residuals")
    log("#  with both SEs: a gap smaller than the combined SE is reported as unresolved.")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'bare+Gauss':>22s} {'Iceberg':>22s} "
        f"{'Ice+Gauss':>22s} {'verdict':>28s}")
    for c in cells:
        cc = c["cell"]
        by = {(s["mode"], s["window"]): s for s in c["scores"]}
        g = by.get(("bare + Gauss", "early"))
        i = by.get(("Iceberg", "early"))
        ig = by.get(("Iceberg + Gauss", "early"))

        def fmt(s):
            if s is None:
                return "-"
            return f"{s['residual']:.4f}+-{s['se']:.4f} x{s['cost']:.2f}"

        if g is None or i is None:
            verdict = "no encoded arm" if i is None else "incomplete"
        else:
            gap = i["residual"] - g["residual"]
            comb = (g["se"] ** 2 + i["se"] ** 2) ** 0.5
            if abs(gap) <= comb:
                verdict = "unresolved (within combined SE)"
            elif gap > 0:
                verdict = f"bare+Gauss better by {gap:.4f}"
            else:
                verdict = f"Iceberg better by {-gap:.4f}"
        log(f"  {cc['N']:>4d} {cc['h']:>5g} {cc['lam']:>4g} {fmt(g):>22s} {fmt(i):>22s} "
            f"{fmt(ig):>22s} {verdict:>28s}")

    log("\n## 4. Measured Iceberg survival vs the Stim first-order prediction "
        "[independent cross-check]")
    log("#  Stim's exp(-detected_total) is a different code path (fault propagation, not")
    log("#  trajectories); data/q3_scaling.txt holds the predictions. Reported here: measured only.")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'t_end':>6s} {'survival(end)':>14s} {'traj':>6s}")
    for c in cells:
        cc, ice = c["cell"], c["ice"]
        if not ice:
            continue
        log(f"  {cc['N']:>4d} {cc['h']:>5g} {cc['lam']:>4g} {ice['times'][-1]:>6.2f} "
            f"{ice['acceptance'][-1]:>14.4f} {c['settings']['traj_ice']:>6d}")

    path = os.path.join(REPO, CONFIG.data_dir, "q3_sweep.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {os.path.relpath(path, REPO)} from {len(cells)} cells")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cell", help="N:h:lam, e.g. 12:0.3:1")
    ap.add_argument("--ice-steps", type=int, default=None,
                    help="survival-matched encoded window in Trotter steps (data/q3_scaling.txt)")
    ap.add_argument("--arms", choices=("both", "bare"), default="both")
    ap.add_argument("--traj-bare", type=int, default=None)
    ap.add_argument("--traj-ice", type=int, default=None)
    ap.add_argument("--batches", type=int, default=None)
    ap.add_argument("--record-every", type=int, default=None)
    ap.add_argument("--mem-gb", type=float, default=None)
    ap.add_argument("--merge", action="store_true", help="merge runs/q3_sweep/*.json -> data/")
    args = ap.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    if args.merge:
        merge()
        return
    if not args.cell:
        ap.error("--cell N:h:lam (or --merge)")
    n_s, h_s, lam_s = args.cell.split(":")
    n, h, lam = int(n_s), float(h_s), float(lam_s)
    res = run_one(n, h, lam, ice_steps=args.ice_steps, arms=args.arms, traj_bare=args.traj_bare,
                  traj_ice=args.traj_ice, batches=args.batches, record_every=args.record_every,
                  mem_gb=args.mem_gb)
    path = os.path.join(WORK_DIR, _cell_name(n, h, lam))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(res, fh)
    print(f"cell N={n} h={h:g} lam={lam:g} done in "
          f"{res['provenance']['seconds_noisy']:.0f} s -> {os.path.relpath(path, REPO)}")
    for s in res["scores"]:
        if s["window"] == "early":
            print(f"  {s['mode']:>16s} residual {s['residual']:.4f} +- {s['se']:.4f} "
                  f"cost x{s['cost']:.2f} resolved={s['resolved']}")


if __name__ == "__main__":
    main()
