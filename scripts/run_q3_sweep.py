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
  one cell:   .venv/Scripts/python.exe -I scripts/run_q3_sweep.py --cell 12:0.3:1
  one shard:  ... --cell 20:0.5:3 --shard 7 [--skip-ideal]          (DECIDED-10 re-runs)
  pool:       ... --merge-shards 20:0.5:3     (runs/q3_sweep/shards/* -> runs/q3_sweep/cell_*)
  bare only:  ... --cell 20:0.5:3 --arms bare
  merge all:  .venv/Scripts/python.exe -I scripts/run_q3_sweep.py --merge
Per-cell JSON lands in runs/q3_sweep/ (gitignored); --merge writes data/q3_sweep.txt.

Settings (review/18 F13, 2026-10-24). Every count, the encoded window and the record density come
from config (`Q3ScalingConfig.per_size`, `.cell_windows`, `.rerun`) unless given on the command
line, and each cell file records which (`provenance.setting_sources`), with the argv and the git
commit. A command-line count BELOW config, or a window / record density that differs from the
pre-declared one, is refused unless `--allow-reduced "<reason>"` gives a reason, which is then
recorded. This is what was missing when both N = 20 cells silently ran at half budget.
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
from src.q3_rescore import rescore_cell
from src.q3_scaling import (
    CANONICAL_2Q_SCOPE,
    SIZE_TO_CASE,
    stim_rate_table,
    survival_curve,
)
from src.q3_shards import merge_cells

WORK_DIR = os.path.join(REPO, "runs", "q3_sweep")
CAVEAT = ("CLASSICAL PREDICTION under an ASSUMED noise model (research/06 H2 prior, "
          "Pauli-trajectory MC). NOT an H2 / hardware result.")


def _jsonable(obj):
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
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


def _key(n: int, h: float, lam: float) -> tuple:
    return (int(n), float(h), int(lam) if float(lam).is_integer() else float(lam))


_GUARDED_COUNTS = ("traj_bare", "traj_ice", "batches")
_GUARDED_EXACT = ("ice_steps", "record_every")


def resolve_settings(n_logical: int, h: float, lam: float, cli: dict,
                     allow_reduced: str | None, shard: int | None = None) -> tuple[dict, dict]:
    """(settings, sources) for one cell or one shard of it (review/18 F13).

    Config gives every value: `per_size` for counts and record density, `cell_windows` for the
    encoded window, and `rerun` (DECIDED-10) for the re-budgeted cells, where a full run uses
    `rerun_shards` batches and a SHARD runs one batch of each arm. A CLI count below config, or a
    window / record density different from config, raises ValueError unless `allow_reduced`
    states a reason."""
    q3, qs = CONFIG.q3, CONFIG.q3_scaling
    key = _key(n_logical, h, lam)
    ps = qs.per_size.get(n_logical, {})
    base = {"traj_bare": int(ps.get("traj_bare", q3.noisy_traj_bare)),
            "traj_ice": int(ps.get("traj_ice", q3.noisy_traj_ice)),
            "batches": int(ps.get("batches", q3.noisy_batches)),
            "record_every": int(ps.get("record_every", q3.noisy_record_every)),
            "mem_gb": float(ps.get("mem_gb", q3.noisy_mem_gb)),
            "ice_steps": qs.cell_windows.get(key)}
    rr = qs.rerun.get(key)
    if rr is not None:
        if shard is None:
            base.update(traj_bare=rr["traj_bare"], traj_ice=rr["traj_ice"],
                        batches=qs.rerun_shards)
        else:
            if not 0 <= shard < qs.rerun_shards:
                raise ValueError(f"shard {shard} outside 0..{qs.rerun_shards - 1}")
            base.update(traj_bare=rr["batch_bare"], traj_ice=rr["batch_ice"], batches=1)
        base["ice_steps"] = rr["ice_steps"]
    elif shard is not None:
        raise ValueError(f"cell {key} has no pre-declared shard budget (config.q3_scaling.rerun)")
    settings, sources = dict(base), {k: "config" for k in base}
    problems = []
    for k, v in cli.items():
        if v is None:
            continue
        settings[k], sources[k] = v, "cli"
        if base.get(k) is None:
            problems.append(f"{k} = {v} has no pre-declared value")
        elif k in _GUARDED_COUNTS and v < base[k]:
            problems.append(f"{k} = {v} is below the declared {base[k]}")
        elif k in _GUARDED_EXACT and v != base[k]:
            problems.append(f"{k} = {v} differs from the declared {base[k]}")
    if settings["ice_steps"] is None:
        problems.append("no encoded window: cell not in config.q3_scaling.cell_windows")
    if problems and not allow_reduced:
        raise ValueError("refusing undeclared settings (pass --allow-reduced '<reason>'): "
                         + "; ".join(problems))
    return settings, sources


def _git(*args: str) -> str | None:
    import subprocess
    try:
        r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True,
                           timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def build_provenance(argv: list[str], sources: dict, allow_reduced: str | None) -> dict:
    """Everything needed to say later how a cell file was made (review/18 F13)."""
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {"host": socket.gethostname(), "platform": platform.platform(),
            "python": platform.python_version(), "argv": list(argv),
            "git_commit": _git("rev-parse", "HEAD"),
            "git_dirty": None if status is None else bool(status),
            "setting_sources": dict(sources), "allow_reduced": allow_reduced,
            "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}


def run_one(n_logical: int, h: float, lam: float, *, arms: str, cli: dict | None = None,
            allow_reduced: str | None = None, shard: int | None = None,
            skip_ideal: bool = False, argv: list[str] | None = None) -> dict:
    """Run one cell, or one shard of it (its own seed stream, one batch per arm), with the
    matching ideal reference (skipped on shards other than the one that carries it), and
    score it with the legacy metric when the ideal is present."""
    st, sources = resolve_settings(n_logical, h, lam, cli or {}, allow_reduced, shard)
    case = SIZE_TO_CASE[n_logical]
    common = {"ice_steps": st["ice_steps"], "record_every": st["record_every"],
              "mem_gb": st["mem_gb"]}
    seed_extra = () if shard is None else (int(shard),)
    prov = build_provenance(argv if argv is not None else sys.argv, sources, allow_reduced)

    t0 = time.perf_counter()
    ideal_arm = None
    if not skip_ideal:
        # The ideal reference is the SAME circuit with every rate 0. One zero-noise bare run is
        # enough: the encoded arm is transparent at zero noise (tested, docs/q3_thermalization.md
        # §9.1), and its curve is read off this one by interpolation, as scripts/run_q3_noisy.py
        # does. Deterministic, so a shard set needs it once (src/q3_shards.merge_cells checks).
        ideal = run_noisy_sweep([case], [h], [1], n_traj_bare=1, n_traj_ice=1, n_batches=1,
                                seed=CONFIG.seed, noise=NoiseRates(), arms="bare", **common)
        ideal_arm = ideal[(*case, h, 1)]["bare"]
    t_ideal = time.perf_counter() - t0

    # Phase markers: a cell otherwise prints nothing until it finishes, which made a 10-hour run
    # indistinguishable from a hung one (2026-10-23). Cheap, and the only progress signal there is.
    print(f"[{time.strftime('%H:%M:%S')}] ideal done in {t_ideal:.0f} s; starting noisy arms "
          f"(N={n_logical}, h={h:g}, lam={lam:g}, traj {st['traj_bare']}/{st['traj_ice']}, "
          f"batches {st['batches']}, shard {shard}, arms={arms})", flush=True)
    t0 = time.perf_counter()
    noisy = run_noisy_sweep([case], [h], [lam], n_traj_bare=st["traj_bare"],
                            n_traj_ice=st["traj_ice"], n_batches=st["batches"],
                            seed=CONFIG.seed, noise=prior_noise(), return_meta=True, arms=arms,
                            seed_extra=seed_extra, **common)
    t_noisy = time.perf_counter() - t0
    print(f"[{time.strftime('%H:%M:%S')}] noisy arms done in {t_noisy:.0f} s", flush=True)

    cell = noisy[(*case, h, lam)]
    scores = score_cell(ideal_arm, cell["bare"], cell["ice"]) if ideal_arm is not None else []
    noise = prior_noise()
    prov.update(seconds_ideal=round(t_ideal, 1), seconds_noisy=round(t_noisy, 1))
    return {
        "caveat": CAVEAT,
        "cell": {"N": n_logical, "case": list(case), "h": h, "lam": lam,
                 "physical_qubits": iceberg_physical_qubits(n_logical) if n_logical % 2 == 0 else 0,
                 "ice_steps": st["ice_steps"], "arms": arms},
        "settings": {"traj_bare": st["traj_bare"], "traj_ice": st["traj_ice"],
                     "batches": st["batches"], "record_every": st["record_every"],
                     "mem_gb": st["mem_gb"], "seed": CONFIG.seed, "seed_extra": list(seed_extra),
                     "shard": shard, "J": CONFIG.q3.J, "dt": CONFIG.q3.dt,
                     "lambda_scope": list(CANONICAL_2Q_SCOPE)},
        "noise": {"p2": noise.p2, "p1": noise.p1, "pm": noise.pm, "p_init": noise.p_init,
                  "zz_bias": noise.zz_bias, "status": "assumed (research/06 H2 prior)"},
        "provenance": prov,
        "ideal": _arm_payload(ideal_arm),
        "bare": _arm_payload(cell["bare"]),
        "ice": _arm_payload(cell["ice"]),
        "scores": [vars(s) | {"resolved": s.resolved} for s in scores],
    }


def _write_atomic(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh)
    os.replace(tmp, path)


def _shard_name(n: int, h: float, lam: float, shard: int) -> str:
    return f"cell_N{n}_h{h:g}_lam{lam:g}_shard{shard:02d}.json"


def merge_shards(n: int, h: float, lam: float, partial: bool = False) -> str:
    """Pool runs/q3_sweep/shards/<cell>_shardNN.json into runs/q3_sweep/<cell>.json. A cell file
    already there is MOVED to runs/q3_sweep/superseded/ first (never overwritten in place)."""
    qs = CONFIG.q3_scaling
    sdir = os.path.join(WORK_DIR, "shards")
    names = [_shard_name(n, h, lam, i) for i in range(qs.rerun_shards)]
    have = [x for x in names if os.path.exists(os.path.join(sdir, x))]
    if len(have) < len(names) and not partial:
        raise SystemExit(f"{len(have)} of {len(names)} shards present; pass --partial to pool them")
    cells = []
    for x in have:
        with open(os.path.join(sdir, x), encoding="utf-8") as fh:
            cells.append(json.load(fh))
    cells.sort(key=lambda c: c["ideal"] is None)          # the ideal-carrying shard first
    if cells[0]["ideal"] is None:
        raise SystemExit("no shard carries the ideal reference (shard 00 missing): the pooled "
                         "cell could not be scored; wait for shard 00")
    merged = merge_cells(cells)
    ideal = merged["ideal"]
    merged["scores"] = ([vars(s) | {"resolved": s.resolved}
                         for s in score_cell(ideal, merged["bare"], merged["ice"])]
                        if ideal is not None else [])
    merged["provenance"].update(host=socket.gethostname(), platform=platform.platform(),
                                python=platform.python_version(),
                                seconds_ideal=sum(c["provenance"]["seconds_ideal"] for c in cells),
                                seconds_noisy=sum(c["provenance"]["seconds_noisy"] for c in cells),
                                partial=len(have) < len(names))
    target = os.path.join(WORK_DIR, _cell_name(n, h, lam))
    if os.path.exists(target):
        old = os.path.join(WORK_DIR, "superseded", time.strftime("%Y-%m-%d"),
                           _cell_name(n, h, lam))
        os.makedirs(os.path.dirname(old), exist_ok=True)
        os.replace(target, old)
    _write_atomic(target, _jsonable(merged))
    return target


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
    log("#  Stim's exp(-(offset + detect rate * steps)) is a different code path (fault")
    log("#  propagation, not trajectories), at the cell's window under the lambda scope")
    log(f"#  {CANONICAL_2Q_SCOPE} (DECIDED-9; review/18 F12: this column used to be promised and")
    log("#  never printed). dev = (measured - predicted) / sqrt(p (1 - p) / traj), a binomial")
    log("#  yardstick that treats the fractional trajectory weights as 0/1 [inferred].")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'t_end':>6s} {'survival(end)':>14s} {'traj':>6s} "
        f"{'Stim':>8s} {'dev':>7s}")
    for c in cells:
        cc, ice = c["cell"], c["ice"]
        if not ice:
            continue
        meas, ntr = ice["acceptance"][-1], c["settings"]["traj_ice"]
        pred = float(survival_curve(stim_rate_table(cc["N"], cc["lam"], prior_noise(),
                                                    scope="2q"),
                                    np.array([cc["ice_steps"]]))[0])
        dev = (meas - pred) / math.sqrt(pred * (1 - pred) / ntr)
        log(f"  {cc['N']:>4d} {cc['h']:>5g} {cc['lam']:>4g} {ice['times'][-1]:>6.2f} "
            f"{meas:>14.4f} {ntr:>6d} {pred:>8.4f} {dev:>+6.1f}s")

    qs = CONFIG.q3_scaling
    log("\n## 5. v2 scores: 4 modes x 2 references, pre-declared rules (DECIDED-8, DECIDED-10) "
        "[measured; classical prediction]")
    log("#  Every mode against BOTH ideal curves (raw | Gauss-conditioned), on ONE window (the")
    log("#  encoded arm's times, bare interpolated onto them). A mode has an estimate only if its")
    log(f"#  effective sample size is >= {qs.ess_floor:g} at EVERY window point (ESS = Kish, or the")
    log("#  surviving weight, a lower bound, for cells without it). SE = delete-one-batch")
    log("#  jackknife of the window average where per-batch data exist (jk), else the legacy mean")
    log("#  per-point SE (lg). cost = mean(1/acceptance) over the window (shots), final = at the")
    log("#  end. ESS / SE are over fault trajectories; cost is in hardware shots: two currencies.")
    log("#  |res| = mean |O - O_ref| (descriptive, continuous with section 9.2; it carries a noise")
    log("#  floor ~ sqrt(2/pi) sigma). rms = sign(msd) sqrt|msd| with msd = mean[(O - O_ref)^2 -")
    log("#  Var O], the bias-corrected mean square on which verdicts are called (section 6).")
    log("#  Gauss modes use their own Kish ESS (sum w p_in)^2 / sum (w p_in)^2, or the lower bound")
    log("#  acceptance x p_in x trajectories. 'no estimate' is a result, not a missing row.")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'mode':>16s} {'|res| vs raw':>16s} "
        f"{'|res| vs cond':>16s} {'rms raw':>8s} {'rms cond':>8s} {'SE':>3s} {'B':>3s} "
        f"{'ESSmin':>8s} {'cost':>7s} {'final':>7s} {'pts':>4s}  note")
    v2 = []
    for c in cells:
        cc, st = c["cell"], c["settings"]
        sc = rescore_cell(c["ideal"], c["bare"], c["ice"], ess_floor=qs.ess_floor,
                          n_traj_bare=st["traj_bare"], n_traj_ice=st["traj_ice"],
                          verdict_k=qs.verdict_k, min_batches=qs.min_batches)
        v2.append((cc, sc))
        for m in ("bare raw", "bare + Gauss", "Iceberg", "Iceberg + Gauss"):
            def rs(ref, sc=sc, m=m):
                r, e = sc.residual[(m, ref)], sc.se[(m, ref)]
                return "no estimate" if not math.isfinite(r) else f"{r:.4f}+-{e:.4f}"
            def rm(ref, sc=sc, m=m):
                x = sc.rms[(m, ref)]
                return "-" if not math.isfinite(x) else f"{x:.4f}"
            log(f"  {cc['N']:>4d} {cc['h']:>5g} {cc['lam']:>4g} {m:>16s} {rs('raw'):>16s} "
                f"{rs('cond'):>16s} {rm('raw'):>8s} {rm('cond'):>8s} "
                f"{('jk' if sc.se_method[m] == 'jackknife' else 'lg'):>3s} "
                f"{sc.n_batches[m]:>3d} {sc.ess_min[m]:>8.1f} {sc.cost[m]:>7.2f} "
                f"{sc.cost_final[m]:>7.1f} {sc.n_points[m]:>4d}  {sc.reason[m]}")

    log("\n## 6. v2 head to head, within each reference [measured; classical prediction]")
    log("#  gap = msd(second) - msd(first) (bias-corrected mean squares); sigma = combined SE.")
    log(f"#  Winner only when |gap| > {qs.verdict_k:g} sigma (DECIDED-8). Under the null about 32 %")
    log("#  of pairs cross 1 sigma by chance; read every verdict with its gap/s.")
    log(f"  {'N':>4s} {'h':>5s} {'lam':>4s} {'ref':>4s} {'pair':>34s} {'gap':>9s} {'sigma':>8s} "
        f"{'gap/s':>6s}  verdict")
    for cc, sc in v2:
        for p in sc.pairs:
            z = p.gap / p.sigma if math.isfinite(p.gap) and p.sigma > 0 else float("nan")
            gs = f"{p.gap:+.2e}" if math.isfinite(p.gap) else "-"
            ss = f"{p.sigma:.2e}" if math.isfinite(p.sigma) else "-"
            zs = f"{z:+.1f}" if math.isfinite(z) else "-"
            log(f"  {cc['N']:>4d} {cc['h']:>5g} {cc['lam']:>4g} {p.ref:>4s} "
                f"{(p.a + ' vs ' + p.b):>34s} {gs:>9s} {ss:>8s} {zs:>6s}  {p.verdict}")

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
    ap.add_argument("--shard", type=int, default=None,
                    help="run shard i of a pre-declared re-run (config.q3_scaling.rerun)")
    ap.add_argument("--skip-ideal", action="store_true",
                    help="omit the ideal reference (shards other than the one carrying it)")
    ap.add_argument("--merge-shards", metavar="N:h:lam", default=None)
    ap.add_argument("--partial", action="store_true", help="--merge-shards with missing shards")
    ap.add_argument("--out-dir", default=None, help="write the cell JSON here instead")
    ap.add_argument("--allow-reduced", metavar="REASON", default=None,
                    help="accept settings below / different from config, recording REASON")
    args = ap.parse_args()

    os.makedirs(WORK_DIR, exist_ok=True)
    if args.merge:
        merge()
        return
    if args.merge_shards:
        n_s, h_s, lam_s = args.merge_shards.split(":")
        print("wrote", merge_shards(int(n_s), float(h_s), float(lam_s), partial=args.partial))
        return
    if not args.cell:
        ap.error("--cell N:h:lam (or --merge)")
    n_s, h_s, lam_s = args.cell.split(":")
    n, h, lam = int(n_s), float(h_s), float(lam_s)
    cli = {"ice_steps": args.ice_steps, "traj_bare": args.traj_bare, "traj_ice": args.traj_ice,
           "batches": args.batches, "record_every": args.record_every, "mem_gb": args.mem_gb}
    res = run_one(n, h, lam, arms=args.arms, cli=cli, allow_reduced=args.allow_reduced,
                  shard=args.shard, skip_ideal=args.skip_ideal, argv=sys.argv)
    if args.shard is not None:
        path = os.path.join(args.out_dir or os.path.join(WORK_DIR, "shards"),
                            _shard_name(n, h, lam, args.shard))
    else:
        path = os.path.join(args.out_dir or WORK_DIR, _cell_name(n, h, lam))
    _write_atomic(path, res)
    print(f"cell N={n} h={h:g} lam={lam:g} done in "
          f"{res['provenance']['seconds_noisy']:.0f} s -> {os.path.relpath(path, REPO)}")
    for s in res["scores"]:
        if s["window"] == "early":
            print(f"  {s['mode']:>16s} residual {s['residual']:.4f} +- {s['se']:.4f} "
                  f"cost x{s['cost']:.2f} resolved={s['resolved']}")


if __name__ == "__main__":
    main()
