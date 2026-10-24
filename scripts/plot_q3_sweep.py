"""Figures for the Q3 generalization sweep (DECIDED-7..10): read runs/q3_sweep/cell_*.json, write
figures/q3_sweep_*.png. Nothing is simulated here; the v2 scores are recomputed from the saved
cell files with src/q3_rescore.py (the same call scripts/run_q3_sweep.py --merge makes), and the
Stim survival predictions with src/q3_scaling (Stim only).

Every noisy panel is a CLASSICAL PREDICTION under an ASSUMED noise model (research/06 H2 prior),
NOT an H2 result; each figure says so in its caption. figures/*.png is gitignored.
Palette and style: scripts/plot_q3.py (dataviz-validated categorical slots; series also differ by
line style). Usage: python -I scripts/plot_q3_sweep.py [--out DIR]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from config import CONFIG
from src.noisy_q3_sweep import prior_noise
from src.q3_rescore import MODES, REFS, rescore_cell
from src.q3_scaling import stim_rate_table, survival_curve

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
STYLES = ["-", "--", "-.", ":", (0, (5, 1, 1, 1))]
SURFACE, INK, INK2, GRID, REF = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
ASSUMED = ("Classical prediction under an ASSUMED noise model (research/06 H2 prior), "
           "Pauli-trajectory simulation. NOT an H2 or hardware result.")
OBS = "flippable_density"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.5,
    "font.size": 8, "axes.titlesize": 8.5, "legend.frameon": False, "legend.fontsize": 7,
})
MODE_STYLE = {"bare raw": (SERIES[1], STYLES[1]), "bare + Gauss": (SERIES[0], STYLES[0]),
              "Iceberg": (SERIES[3], STYLES[3]), "Iceberg + Gauss": (SERIES[2], STYLES[2])}


def _f(x):
    return np.asarray(x, dtype=float)


def load_cells(work: str) -> list[dict]:
    cells = []
    for p in sorted(glob.glob(os.path.join(work, "cell_*.json"))):
        with open(p, encoding="utf-8") as fh:
            cells.append(json.load(fh))
    cells.sort(key=lambda c: (c["cell"]["N"], c["cell"]["h"], c["cell"]["lam"]))
    return cells


def _label(c) -> str:
    cc = c["cell"]
    return f"N={cc['N']}, h={cc['h']:g}, λ={cc['lam']:g}"


def _score(c):
    qs, st = CONFIG.q3_scaling, c["settings"]
    return rescore_cell(c["ideal"], c["bare"], c["ice"], ess_floor=qs.ess_floor,
                        n_traj_bare=st["traj_bare"], n_traj_ice=st["traj_ice"],
                        verdict_k=qs.verdict_k, min_batches=qs.min_batches)


def _caption(fig, text):
    fig.text(0.01, 0.005, text, fontsize=6.5, color=INK2, va="bottom", ha="left", wrap=True)


def fig_curves(cells, out):
    n = len(cells)
    cols = 4
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(11, 2.5 * rows + 0.6), squeeze=False)
    for ax, c in zip(axes.flat, cells):
        ideal, bare, ice = c["ideal"], c["bare"], c["ice"]
        ti = _f(ideal["times"])
        ax.plot(ti, _f(ideal["raw"][OBS][0]), color=INK, lw=1.0, label="ideal raw")
        ax.plot(ti, _f(ideal["cond"][OBS][0]), color=REF, lw=1.0, ls="--", label="ideal cond.")
        for mode, (arm, key) in {"bare raw": ("bare", "raw"), "bare + Gauss": ("bare", "cond"),
                                 "Iceberg": ("ice", "raw"),
                                 "Iceberg + Gauss": ("ice", "cond")}.items():
            a = {"bare": bare, "ice": ice}[arm]
            if a is None:
                continue
            t, v, e = _f(a["times"]), _f(a[key][OBS][0]), np.nan_to_num(_f(a[key][OBS][1]))
            col, ls = MODE_STYLE[mode]
            ax.plot(t, v, color=col, ls=ls, label=mode)
            ax.fill_between(t, v - e, v + e, color=col, alpha=0.15, lw=0)
        if ice is not None:
            ax.axvspan(0, _f(ice["times"])[-1], color=GRID, alpha=0.35, lw=0)
        ax.set_title(_label(c))
        ax.set_xlabel("t |J|")
        ax.set_ylabel("flippable density")
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    axes.flat[0].legend(loc="upper right", ncol=1)
    _caption(fig, "Shaded: the encoded window (Iceberg survival-matched). Bands: per-point batch "
             "SE (trajectories only; readout is exact). " + ASSUMED)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(os.path.join(out, "q3_sweep_curves.png"), dpi=160)
    plt.close(fig)


def fig_survival(cells, out):
    rows = []
    for c in cells:
        cc, ice = c["cell"], c["ice"]
        if ice is None:
            continue
        steps = np.array([cc["ice_steps"]])
        can = float(survival_curve(stim_rate_table(cc["N"], cc["lam"], prior_noise(),
                                                   scope="2q"), steps)[0])
        old = float(survival_curve(stim_rate_table(cc["N"], cc["lam"], prior_noise(),
                                                   scope="2q-legacy"), steps)[0])
        m, ntr = float(ice["acceptance"][-1]), c["settings"]["traj_ice"]
        rows.append((_label(c), m, np.sqrt(max(m * (1 - m), 1e-12) / ntr), can, old))
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    x = np.arange(len(rows))
    ax.errorbar(x, [r[1] for r in rows], yerr=[r[2] for r in rows], fmt="o", color=SERIES[0],
                ms=4, capsize=2, label="measured (trajectories)")
    ax.plot(x, [r[3] for r in rows], "s", color=SERIES[2], ms=4,
            label="Stim, every-2q scope (DECIDED-9)")
    ax.plot(x, [r[4] for r in rows], "x", color=SERIES[1], ms=5, label="Stim, old scope")
    ax.set_xticks(x, [r[0] for r in rows], rotation=35, ha="right")
    ax.set_ylabel("Iceberg survival at window end")
    ax.legend()
    _caption(fig, "Error bar: binomial sqrt(p(1-p)/n) on the trajectory count [inferred]. "
             + ASSUMED)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(out, "q3_sweep_survival.png"), dpi=160)
    plt.close(fig)


def fig_ess(cells, out):
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    for i, c in enumerate(c for c in cells if c["ice"] is not None):
        ice = c["ice"]
        t = _f(ice["times"])
        ess = (_f(ice["ess"]) if ice.get("ess") is not None
               else _f(ice["acceptance"]) * c["settings"]["traj_ice"])
        ax.semilogy(t, np.maximum(ess, 0.5), color=SERIES[i % 5], ls=STYLES[(i // 5) % 5],
                    marker="o", ms=2.5, label=_label(c))
    ax.axhline(CONFIG.q3_scaling.ess_floor, color=INK, lw=1.0, ls="--")
    ax.text(0.2, CONFIG.q3_scaling.ess_floor * 1.12, f"floor = {CONFIG.q3_scaling.ess_floor:g}",
            fontsize=7)
    ax.set_xlabel("t |J|")
    ax.set_ylabel("effective sample (Iceberg)")
    ax.legend(ncol=2, fontsize=6)
    _caption(fig, "ESS = Kish where stored, else surviving weight = acceptance x trajectories "
             "(a lower bound). " + ASSUMED)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(out, "q3_sweep_ess.png"), dpi=160)
    plt.close(fig)


def fig_table(cells, out):
    scores = [(c, _score(c)) for c in cells]
    fig, axes = plt.subplots(1, 2, figsize=(10, 0.36 * len(cells) + 1.6), sharey=True)
    for ax, ref in zip(axes, REFS):
        M = np.array([[s.residual[(m, ref)] for m in MODES] for _, s in scores])
        im = ax.imshow(np.where(np.isfinite(M), M, np.nan), cmap="Blues", aspect="auto",
                       vmin=0, vmax=np.nanmax(M) if np.isfinite(M).any() else 1)
        for i, (_, s) in enumerate(scores):
            for j, m in enumerate(MODES):
                r = s.residual[(m, ref)]
                txt = "no est." if not np.isfinite(r) else f"{r:.3f}\n±{s.se[(m, ref)]:.3f}"
                ax.text(j, i, txt, ha="center", va="center", fontsize=5.5,
                        color=INK if not np.isfinite(r) or r < 0.6 * np.nanmax(M) else "white")
        ax.set_xticks(range(len(MODES)), MODES, rotation=20, ha="right")
        ax.set_title(f"residual vs ideal {'raw' if ref == 'raw' else 'Gauss-conditioned'} curve")
        ax.grid(False)
        fig.colorbar(im, ax=ax, fraction=0.04)
    axes[0].set_yticks(range(len(cells)), [_label(c) for c in cells])
    _caption(fig, "v2 scores (DECIDED-8/10): mean |O - O_ref| over the common encoded window; "
             "'no est.' = effective sample below the pre-declared floor. " + ASSUMED)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(os.path.join(out, "q3_sweep_table.png"), dpi=160)
    plt.close(fig)


def fig_cost(cells, out):
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for m in MODES:
        col, _ = MODE_STYLE[m]
        xs, ys, es = [], [], []
        for c in cells:
            s = _score(c)
            ref = "cond" if "Gauss" in m else "raw"
            if np.isfinite(s.residual[(m, ref)]):
                xs.append(s.cost[m])
                ys.append(s.residual[(m, ref)])
                es.append(s.se[(m, ref)])
        ax.errorbar(xs, ys, yerr=es, fmt="o", color=col, ms=4, capsize=2, label=m)
    ax.set_xscale("log")
    ax.set_xlabel("shot-cost multiplier  mean(1/acceptance)")
    ax.set_ylabel("residual vs its own target")
    ax.legend()
    _caption(fig, "Each point is one cell with an estimate; raw modes vs the raw ideal, Gauss "
             "modes vs the conditioned ideal. " + ASSUMED)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(os.path.join(out, "q3_sweep_cost.png"), dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(REPO, CONFIG.figures_dir))
    ap.add_argument("--work", default=os.path.join(REPO, "runs", "q3_sweep"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    cells = load_cells(a.work)
    if not cells:
        raise SystemExit(f"no cell files in {a.work}")
    for fn in (fig_curves, fig_survival, fig_ess, fig_table, fig_cost):
        fn(cells, a.out)
        print("wrote", fn.__name__)


if __name__ == "__main__":
    main()
