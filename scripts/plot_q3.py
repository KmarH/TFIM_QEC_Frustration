"""Q3 figures (handoff/08 Part B3, FLAG C): read the saved data/*.txt files, write figures/*.png.

Nothing is recomputed here except the a + b/N fit line drawn on the size figure (a weighted
least-squares refit of the plotted MCMC points, the same fit run_q3_size.py prints): every plotted
number is parsed from a data file written by a reproducible script (run_q3_baseline.py, run_trotter_threshold.py, run_q3_noisy.py,
run_q3_size.py), so the figures can be regenerated from the data alone. figures/*.png is
gitignored (local outputs). Every figure carries its status line in the caption: classical
simulation / statistics, and for noisy panels "classical prediction under an ASSUMED noise model,
NOT an H2 result".
Palette: the dataviz skill's validated categorical light palette (slots 1-5 pass the CVD and
normal-vision checks; slots 3-5 sit below 3:1 contrast, so series also differ by line style and
the data files are the table view). Usage: python -I scripts/plot_q3.py
"""

from __future__ import annotations

import math
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401
import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402

DATA = os.path.join(REPO, CONFIG.data_dir)
FIG = os.path.join(REPO, CONFIG.figures_dir)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]     # categorical slots 1-5 (light)
STYLES = ["-", "--", "-.", ":", (0, (5, 1, 1, 1))]
SURFACE, INK, INK2, GRID, REF = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#8a8984"
CLASSICAL = "Classical simulation / statistics only. Not an H2 or hardware result."
ASSUMED = "Noisy curves: classical prediction under an ASSUMED noise model (research/06 H2 prior). NOT an H2 result."

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 1.8,
    "font.size": 9, "axes.titlesize": 10, "legend.frameon": False, "legend.fontsize": 8,
})


def _read(name):
    with open(os.path.join(DATA, name)) as fh:
        return fh.read().splitlines()


def _caption(fig, *lines):
    fig.text(0.01, 0.005, "\n".join(lines), fontsize=7, color=INK2, va="bottom", ha="left")


def _save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    print("wrote", os.path.relpath(path, REPO))


def _ref_line(ax, y, label, style):
    """Reference level; identified in the legend (labels on the line collide with the curves)."""
    ax.axhline(y, color=REF, lw=1.1, ls=style, zorder=1, label=label)


# --------------------------------------------------------------------------- #
# data/q3_relaxation.txt
# --------------------------------------------------------------------------- #
def parse_relaxation():
    lines = _read("q3_relaxation.txt")
    curves, refs, tables = {}, {}, {}
    cur = None
    for l in lines:
        m = re.match(r"^# (\d+x\d+ \S+ h=[\d.]+): B_W0 flippable ([\d.]+), memory ([\d.]+), C\(r1\) ([-+\d.]+); "
                     r"DE ([\d.]+), ([\d.]+), ([-+\d.]+)", l)
        if m:
            refs[m.group(1)] = dict(B_f=float(m.group(2)), B_c=float(m.group(4)), DE_f=float(m.group(5)), DE_c=float(m.group(7)))
            continue
        m = re.match(r"^(\d+x\d+ \S+ h=[\d.]+)\s+([-+\d.e\s]+)$", l)
        if m and len(m.group(2).split()) == 9:
            curves.setdefault(m.group(1), []).append([float(v) for v in m.group(2).split()])
            continue
        m = re.match(r"^## (\d+x\d+) start=(\S+) W0=.* h=([\d.]+) ", l)
        if m:
            cur = (m.group(1), m.group(2), float(m.group(3)))
            continue
        m = re.match(r"^  (flippable_density|memory|C\(r=0\.866025\))\s+([-+\d.]+)\s+([-+\d.]+)\s+([-+\d.]+)\s+"
                     r"([-+\d.]+)\s+([-+\d.]+)\s+([\d.]+)", l)
        if m and cur:
            tables.setdefault(cur, {})[m.group(1)] = dict(B=float(m.group(2)), DE=float(m.group(3)), late_raw=float(m.group(5)),
                                                         late_cond=float(m.group(6)), std=float(m.group(7)))
        m = re.match(r"^  leakage \[measured\]: late P_out ([\d.e+-]+)", l)
        if m and cur:
            tables.setdefault(cur, {})["p_out"] = float(m.group(1))
    return {k: np.array(v) for k, v in curves.items()}, refs, tables


def fig_relaxation(curves, refs):
    keys = [k for k in ("3x6 3-sublattice h=0.1", "3x6 3-sublattice h=0.3") if k in curves]
    fig, axes = plt.subplots(len(keys), 2, figsize=(9, 3.0 * len(keys) + 0.6), squeeze=False)
    for row, key in enumerate(keys):
        c, r = curves[key], refs[key]
        t, raw_f, cond_f, raw_c, cond_c, pout = c[:, 0], c[:, 1], c[:, 2], c[:, 5], c[:, 6], c[:, 7]
        for col, (raw, cond, B, DE, name) in enumerate(((raw_f, cond_f, r["B_f"], r["DE_f"], "flippable density"),
                                                          (raw_c, cond_c, r["B_c"], r["DE_c"], "C(r = 0.866)"))):
            ax = axes[row, col]
            if col == 0:     # exact leakage envelope |raw - cond| <= P_out (range 1) for the linear observable
                ax.fill_between(t, cond - pout, cond + pout, color=SERIES[0], alpha=0.12, lw=0,
                                label="leakage envelope ±P_out (exact bound)")
            ax.plot(t, cond, color=SERIES[0], ls=STYLES[0], label="sector-conditioned")
            ax.plot(t, raw, color=SERIES[1], ls=STYLES[1], label="raw (incl. leakage)")
            _ref_line(ax, B, "B_W0 (infinite-T sector, MCMC = exact)", (0, (4, 3)))
            _ref_line(ax, DE, "DE (finite-cluster H_QDM long-time)", ":")
            ax.set_title(f"{key.replace(' h=', ', h = ')}: {name}", loc="left")
            ax.set_xlabel("t |J|")
            if col == 0:
                ax.set_ylim(0.2, 0.7)
            if row == 0 and col == 0:
                ax.legend(loc="upper right")
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    _caption(fig, "Ideal (noiseless, unencoded) 2nd-order Trotter relaxation from the 3-sublattice state, dt = 0.25 "
                  "(data/q3_relaxation.txt).", CLASSICAL)
    _save(fig, "q3_relaxation.png")


def fig_field_scan(tables):
    hs = sorted({k[2] for k in tables if k[0] == "3x6"})
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, obs, name in ((axes[0], "flippable_density", "flippable density"), (axes[1], "C(r=0.866025)", "C(r = 0.866)")):
        for i, (case, lab) in enumerate(((("3x6", "3-sublattice"), "3x6, 3-sublattice"), (("3x4", "flippable"), "3x4, flippable"))):
            pts = [(h, tables[(case[0], case[1], h)][obs]) for h in hs if (case[0], case[1], h) in tables]
            if not pts:
                continue
            x = np.array([p[0] for p in pts])
            y = np.array([p[1]["late_cond"] for p in pts])
            e = np.array([p[1]["std"] for p in pts])
            ax.errorbar(x, y, yerr=e, color=SERIES[i], ls=STYLES[i], marker="o", ms=4, capsize=2, label=lab + " (cond, late)")
            ax.plot(x, [p[1]["B"] for p in pts], color=SERIES[i], lw=1, ls=(0, (4, 3)), alpha=0.7)
            ax.plot(x, [p[1]["DE"] for p in pts], color=SERIES[i], lw=1, ls=":", alpha=0.9)
        ax.set_title(f"late sector-conditioned {name} vs h", loc="left")
        ax.set_xlabel("h / |J|")
        ax.axvspan(0.4, max(hs) + 0.05, color=GRID, alpha=0.5, lw=0)
        ax.text(0.45, ax.get_ylim()[1], "stress point", fontsize=7, color=INK2, va="top", ha="center")
    axes[0].legend(loc="center left", bbox_to_anchor=(0.0, 0.55))
    axes[0].text(0.02, 0.98, "dashed: B_W0   dotted: DE", transform=axes[0].transAxes, fontsize=7, color=INK2, va="top")
    ax = axes[2]
    for i, case in enumerate((("3x6", "3-sublattice"), ("3x4", "flippable"), ("3x4", "stripe"))):
        pts = [(h, tables[(case[0], case[1], h)]["p_out"]) for h in hs if (case[0], case[1], h) in tables]
        if pts:
            ax.plot([p[0] for p in pts], [p[1] for p in pts], color=SERIES[i], ls=STYLES[i], marker="o", ms=4,
                    label=f"{case[0]}, {case[1]}")
    ax.set_yscale("log")
    ax.set_title("late weight outside the W0 sector, P_out", loc="left")
    ax.set_xlabel("h / |J|")
    ax.legend(loc="lower right")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _caption(fig, "Error bars: temporal std over the late window (not a statistical error). Ideal noiseless curves, dt = 0.25 "
                  "(data/q3_relaxation.txt).", CLASSICAL)
    _save(fig, "q3_field_scan.png")


# --------------------------------------------------------------------------- #
# data/trotter_threshold.txt
# --------------------------------------------------------------------------- #
def parse_threshold():
    scans, cur = {}, None
    for l in _read("trotter_threshold.txt"):
        m = re.match(r"^### (\d+x\d+) (\S+) h=([\d.]+)", l)
        if m:
            cur = (m.group(1), m.group(2), float(m.group(3)))
            continue
        if l.startswith("##"):
            cur = None if not l.startswith("###") else cur
        m = re.match(r"^\s+([\d.]+)\s+(\d+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)$", l)
        if m and cur:
            scans.setdefault(cur, []).append([float(m.group(i)) for i in (1, 3, 4, 5, 6, 7)])
    return {k: np.array(v) for k, v in scans.items()}


def fig_threshold(scans):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, case, title in ((axes[0], ("3x4", "flippable"), "3x4 flippable start"),
                            (axes[1], ("3x3", "3-sublattice"), "3x3 3-sublattice start")):
        for i, h in enumerate((0.1, 0.3, 0.5)):
            s = scans.get((case[0], case[1], h))
            if s is None:
                continue
            ax.plot(s[:, 0], s[:, 1], color=SERIES[i], ls=STYLES[i], label=f"h = {h}")
        ref = scans.get((case[0], case[1], 0.3))
        if ref is not None:
            k = np.argmin(np.abs(ref[:, 0] - 0.1))
            x = np.array([0.02, 0.3])
            ax.plot(x, ref[k, 1] * (x / ref[k, 0]) ** 2, color=REF, lw=1, ls=(0, (4, 3)))
            ax.text(0.05, ref[k, 1] * (0.05 / ref[k, 0]) ** 2 * 1.6, "∝ dt²", fontsize=7, color=INK2)
        for x, lab in ((math.pi / 6, "π/6"), (math.pi / 4, "π/4")):
            ax.axvline(x, color=REF, lw=1, ls=":")
            ax.text(x, 2e-6, lab, fontsize=7, color=INK2, ha="left")
        ax.axvline(CONFIG.q3.dt, color=INK2, lw=1.2)
        ax.text(CONFIG.q3.dt, 0.6, " working dt = 0.25", fontsize=7, color=INK, va="top")
        ax.axhline(CONFIG.q3.thr_eps, color=REF, lw=1)
        ax.text(0.021, CONFIG.q3.thr_eps * 1.15, "ε = 0.05 (absolute criterion)", fontsize=7, color=INK2)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(1e-6, 1.0)
        ax.set_xlabel("Trotter step dt |J|")
        ax.set_ylabel("time-max |flippable density error|")
        ax.set_title(f"Trotter error vs exact, T = 20/|J|: {title}", loc="left")
        ax.legend(loc="lower right", bbox_to_anchor=(1.0, 0.1))
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _caption(fig, "2nd-order Strang vs exact (Chebyshev) evolution; resonances π/(|J| n_s) from first-order Floquet theory "
                  "(data/trotter_threshold.txt).", CLASSICAL)
    _save(fig, "trotter_threshold.png")


# --------------------------------------------------------------------------- #
# data/q3_noisy.txt
# --------------------------------------------------------------------------- #
_NUM = r"([-+]?[\d.]+(?:e[-+]?\d+)?|nan|n/a)"


def parse_noisy():
    out, cur = {}, None
    for l in _read("q3_noisy.txt"):
        m = re.match(r"^## (\d+x\d+) start=(\S+)", l)
        if m:
            cur = (m.group(1), m.group(2))
            out[cur] = []
            continue
        if l.startswith("## "):
            cur = None
            continue
        if cur and re.match(r"^\s+[\d.]+\s+(nan|[\d.]+)\s+[\d.]+ \|", l):
            vals = re.findall(r"[-+]?\d+\.\d+(?:e[-+]?\d+)?(?:±\d+\.\d+)?|nan|n/a", l)

            def v(x):
                if x in ("nan", "n/a"):
                    return (np.nan, np.nan)
                a, _, b = x.partition("±")
                return (float(a), float(b) if b else np.nan)
            row = [v(x) for x in vals]
            out[cur].append(row)
    return out


def fig_noisy(noisy):
    case = ("3x4", "flippable")
    rows = noisy.get(case)
    if not rows:
        print("skip q3_noisy.png (no data)")
        return
    t = np.array([r[0][0] for r in rows])
    acc = np.array([r[1][0] for r in rows])
    pin = np.array([r[2][0] for r in rows])
    ideal = np.array([r[3][0] for r in rows])
    ideal_cond = np.array([r[4][0] for r in rows])
    series = [("bare, raw", 5), ("bare + Gauss-law post-selection", 6), ("Iceberg, post-selected", 7),
              ("Iceberg + Gauss-law post-selection", 8)]
    fig, axes = plt.subplots(2, 1, figsize=(8.5, 6.4), sharex=True, gridspec_kw=dict(height_ratios=(2.2, 1)))
    ax = axes[0]
    ax.plot(t, ideal, color=INK, lw=1.4, label="ideal circuit (no noise), raw")
    ax.plot(t, ideal_cond, color=REF, lw=1.2, ls=(0, (2, 1)),
            label="ideal, sector-conditioned (target of the Gauss modes)")
    for i, (lab, j) in enumerate(series):
        y = np.array([r[j][0] for r in rows])
        e = np.array([r[j][1] for r in rows])
        ax.plot(t, y, color=SERIES[i], ls=STYLES[i + 1], label=lab)
        ax.fill_between(t, y - e, y + e, color=SERIES[i], alpha=0.15, lw=0)
    ax.set_ylabel("flippable density")
    ax.set_title("3x4 triangular TFIM, flippable start, h = 0.3: bare vs Iceberg under the assumed H2-prior noise",
                 loc="left")
    ax.legend(loc="lower left", ncol=1)
    ax = axes[1]
    ax.plot(t, pin, color=SERIES[1], ls=STYLES[2], label="bare: Gauss-law acceptance (p_in)")
    ax.plot(t, acc, color=SERIES[2], ls=STYLES[3], label="Iceberg: detector survival")
    ax.set_yscale("log")
    ax.set_ylim(1e-3, 1.5)
    ax.set_ylabel("post-selection acceptance")
    ax.set_xlabel("t |J|")
    ax.legend(loc="lower left")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    _caption(fig, "Bands: batch-means SE over fault patterns (exact readout distributions, no shot noise). Same circuit-order "
                  "Strang circuit on both arms (data/q3_noisy.txt).", ASSUMED)
    _save(fig, "q3_noisy.png")


# --------------------------------------------------------------------------- #
# data/q3_size.txt
# --------------------------------------------------------------------------- #
def parse_size():
    base, budget = [], []
    for l in _read("q3_size.txt"):
        m = re.match(r"^\s+(\d+)x(\d+)\s+(\d+)\s+([\d.]+) ± ([\d.]+)\s+([-+\d.]+) ± ([\d.]+)", l)
        if m:
            base.append([float(m.group(i)) for i in (3, 4, 5, 6, 7)])
            continue
        m = re.match(r"^\s+(\d+)x(\d+)\s+(\d+)\s+(\d+)\s+(yes|NO)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)"
                     r"\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", l)
        if m:
            budget.append(dict(N=int(m.group(3)), phys=int(m.group(4)), fits=m.group(5) == "yes",
                               t_ice=[float(m.group(i)) for i in (10, 11, 12)], t_bare=[float(m.group(i)) for i in (13, 14, 15)]))
    return np.array(base), budget


def fig_size(base, budget):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    ax = axes[0]
    N, f, fe = base[:, 0], base[:, 1], base[:, 2]
    ax.errorbar(1 / N, f, yerr=fe, color=SERIES[0], marker="o", ms=4, ls="none", capsize=2, label="MCMC, W0 = (0,0)")
    for n, y in zip(N, f):
        ax.annotate(f"N={int(n)}", (1 / n, y), xytext=(4, -10), textcoords="offset points", fontsize=7, color=INK2)
    big = N >= 36
    b, a = np.polyfit(1 / N[big], f[big], 1, w=1 / fe[big])
    x = np.linspace(0, 1 / 36, 20)
    ax.plot(x, a + b * x, color=REF, lw=1, ls=(0, (4, 3)), label=f"a + b/N fit (N ≥ 36): a = {a:.3f} [inferred]")
    ax.set_xlim(left=0)
    ax.set_xlabel("1 / N")
    ax.set_ylabel("sector-baseline flippable density")
    ax.set_title("ergodic (infinite-T) sector baseline vs size", loc="left")
    ax.legend(loc="lower right")
    ax = axes[1]
    Nb = np.array([r["N"] for r in budget])
    # matched thresholds (review M4): the same survival level for both quantities
    for k, (lvl, st) in enumerate(((0, "50%"), (2, "1%"))):
        ax.plot(Nb, [r["t_ice"][lvl] for r in budget], color=SERIES[2], ls=STYLES[k], marker="o", ms=4,
                label=f"Iceberg: detector survival falls to {st}")
        ax.plot(Nb, [r["t_bare"][lvl] for r in budget], color=SERIES[1], ls=STYLES[k], marker="s", ms=4,
                label=f"bare: fault-free fraction falls to {st}")
    for r in budget:
        if not r["fits"]:
            ax.annotate(f"Iceberg needs {r['phys']} > {CONFIG.compare.n_data} H2 qubits", (r["N"], r["t_ice"][0]),
                        xytext=(-250, -2), textcoords="offset points", fontsize=7, color=INK2,
                        arrowprops=dict(arrowstyle="-", color=REF, lw=0.8))
    ax.axhline(CONFIG.q3.qdm_times / CONFIG.q3.noisy_h, color=REF, lw=1, ls=":", label="Q3 relaxation window (h = 0.3)")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_yticks([1, 2, 5, 10, 20, 40])
    ax.set_xlabel("number of spins N")
    ax.set_ylabel("t |J|")
    ax.set_title("noise budget vs size (Stim first-order accounting)", loc="left")
    ax.set_ylim(0.5, 120)
    ax.legend(loc="upper right", fontsize=6.5, ncol=2)
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    _caption(fig, "Left: MCMC statistics (data/q3_size.txt §1). Right: first-order fault accounting under the ASSUMED research/06 "
                  "H2-prior noise model (§2), NOT an H2 result.",
                  "Right-panel curves are different quantities: Iceberg = post-selection cost, bare = fault-free shot fraction.", "No thermodynamic-limit claim; the quantum curve itself stops "
                  "at N = 18 (state-vector / ED ceilings).")
    _save(fig, "q3_size.png")


def main():
    curves, refs, tables = parse_relaxation()
    fig_relaxation(curves, refs)
    fig_field_scan(tables)
    fig_threshold(parse_threshold())
    if os.path.exists(os.path.join(DATA, "q3_noisy.txt")):
        fig_noisy(parse_noisy())
    fig_size(*parse_size())


if __name__ == "__main__":
    main()
