"""Explanatory schematics for the Q3 write-ups: figures/schem_triangular_dimers.png,
figures/schem_iceberg.png, figures/schem_pipeline.png.

The lattice panel is computed, not drawn by hand: the spin state is src/dimers.TriangularDimers'
three-sublattice state on the 6 x 6 torus, the bonds follow src/lattice.triangular_bonds
(d1 = (1, 0), d2 = (0, 1), d3 = (1, 1)), a bond is frustrated when its two spins are aligned
(J < 0 in this repo's H = -J sum ZZ - h sum X), its dimer is the dual honeycomb edge joining the
centroids of the two triangles that share it, and a site is marked flippable when its six bonds
alternate frustrated / satisfied around it (its hexagon holds three alternating dimers). The Iceberg panel follows research/02-stage2-iceberg.md (2211.06703 Fig. 1).
No noisy number appears in these figures. Usage: python -I scripts/plot_q3_schematics.py [--out DIR]
"""

from __future__ import annotations

import argparse
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

from config import CONFIG
from src.dimers import TriangularDimers

SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
                     "savefig.facecolor": SURFACE, "font.size": 8, "text.color": INK})
A1, A2 = np.array([1.0, 0.0]), np.array([-0.5, np.sqrt(3) / 2])


def _pos(x, y):
    return x * A1 + y * A2


def fig_lattice(out):
    L = 6
    d = TriangularDimers(L, L)
    s = np.asarray(d.three_sublattice_spins()).reshape(L, L)          # (Ly, Lx)
    # Flippable, locally: going round the site, its six bonds alternate frustrated / satisfied
    # (so its hexagon holds 3 alternating dimers). Neighbours in angular order: +d1, +d3, +d2,
    # -d1, -d3, -d2 (d3 = d1 + d2). Computed on the periodic torus.
    ring = ((1, 0), (1, 1), (0, 1), (-1, 0), (-1, -1), (0, -1))
    flip = set()
    for y in range(L):
        for x in range(L):
            fr = [s[y, x] == s[(y + dy) % L, (x + dx) % L] for dx, dy in ring]
            if all(fr[i] != fr[(i + 1) % 6] for i in range(6)):
                flip.add(y * L + x)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    tris = []
    for y in range(L - 1):
        for x in range(L - 1):
            tris.append(((x, y), (x + 1, y), (x + 1, y + 1)))
            tris.append(((x, y), (x, y + 1), (x + 1, y + 1)))
    cent = {t: sum(_pos(*p) for p in t) / 3 for t in tris}
    edges = {}
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[0], t[2])):
            edges.setdefault(tuple(sorted((a, b))), []).append(t)
    for k, ax in enumerate(axes):
        for (a, b), ts in edges.items():
            pa, pb = _pos(*a), _pos(*b)
            frustrated = s[a[1], a[0]] == s[b[1], b[0]]
            if k == 0:
                ax.plot(*zip(pa, pb), color=SERIES[1] if frustrated else GRID,
                        lw=2.6 if frustrated else 1.0, zorder=1)
            else:
                ax.plot(*zip(pa, pb), color=GRID, lw=0.8, zorder=1)
                if frustrated and len(ts) == 2:
                    ax.plot(*zip(cent[ts[0]], cent[ts[1]]), color=SERIES[0], lw=3.2,
                            solid_capstyle="round", zorder=3)
        if k == 1:
            c = np.array(list(cent.values()))
            ax.plot(c[:, 0], c[:, 1], "o", ms=2.2, color=INK2, zorder=2)
        for y in range(L):
            for x in range(L):
                p = _pos(x, y)
                up = s[y, x] > 0
                ax.plot(*p, "o", ms=9, color=SURFACE, mec=INK, mew=0.8, zorder=4)
                ax.text(*p, "↑" if up else "↓", ha="center", va="center", fontsize=8, zorder=5)
                if k == 1 and (y * L + x) in flip and 0 < x < L - 1 and 0 < y < L - 1:
                    ax.add_patch(mpatches.Circle(p, 0.33, fill=False, ec=SERIES[2], lw=1.6,
                                                 zorder=5))
        ax.set_aspect("equal")
        ax.axis("off")
    axes[0].set_title("(a) spins on the triangular lattice; orange = frustrated bond\n"
                      "(aligned spins, J < 0): exactly one per triangle in a ground state")
    axes[1].set_title("(b) dimers on the dual honeycomb lattice (blue) cross frustrated bonds;\n"
                      "green ring = flippable site (its hexagon holds 3 alternating dimers)")
    fig.text(0.01, 0.01, "Three-sublattice state on a 6x6 patch (open drawing of the periodic "
             "torus). Schematic; no noisy data.", fontsize=6.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(os.path.join(out, "schem_triangular_dimers.png"), dpi=170)
    plt.close(fig)


def _box(ax, x, y, w, h, text, color, fs=7.5):
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                         fc=color, ec=INK, lw=0.8, alpha=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def _arrow(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                arrowprops={"arrowstyle": "->", "color": INK2, "lw": 1.0})


def fig_iceberg(out):
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4)
    ax.axis("off")
    rows = ["qubit 1", "qubit 2", "...", "qubit k", "top t", "bottom b", "ancilla a1",
            "ancilla a2"]
    for i, r in enumerate(rows):
        y = 3.6 - i * 0.42
        ax.text(0.05, y, r, fontsize=7, va="center")
        ax.plot([0.9, 9.8], [y, y], color=GRID if "ancilla" not in r else "#c9c8c3", lw=1)
    _box(ax, 1.0, 1.0, 1.3, 2.75, "encode\n(prep)\n\nstabilizers\nS_X = X...X\nS_Z = Z...Z",
         "#dbe8f7")
    _box(ax, 2.6, 1.0, 2.0, 2.75, "one Trotter step\n\nlogical X_i = X_t X_i\nlogical Z_i = "
         "Z_b Z_i\n\nZZ rotations +\nrotation-gadget CX", "#fbe0d4")
    _box(ax, 4.9, 0.45, 1.8, 3.3, "syndrome round\n\n2 ancillas read\nS_X and S_Z\nvia CX\n\n"
         "any -1  ->\nshot discarded", "#d6f0e6")
    _box(ax, 7.0, 1.0, 1.0, 2.75, "repeat\nsteps +\nrounds", "#f3f3f1")
    _box(ax, 8.3, 1.0, 1.4, 2.75, "final Z readout\n+ parity check\n\nkeep only if\nno detector\n"
         "fired", "#fdeec2")
    for x0, x1 in ((2.3, 2.6), (4.6, 4.9), (6.7, 7.0), (8.0, 8.3)):
        _arrow(ax, x0, 2.4, x1, 2.4)
    ax.text(0.05, 0.12, "Iceberg [[k+2, k, 2]] (2211.06703): k logical qubits in k+2 physical "
            "plus 2 syndrome ancillas = k+4 physical qubits (N = 20 logical -> 24, the "
            "state-vector ceiling). Distance 2: every single-qubit error is DETECTED, none is "
            "corrected.", fontsize=6.8, color=INK2)
    fig.savefig(os.path.join(out, "schem_iceberg.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_pipeline(out):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.4)
    ax.axis("off")
    _box(ax, 0.1, 3.3, 1.9, 0.8, "initial dimer state\n(defect-free, W0)", "#f3f3f1")
    _box(ax, 2.4, 3.3, 2.3, 0.8, "ideal circuit\n(zero noise)", "#e9e9e6")
    _box(ax, 2.4, 1.95, 2.3, 0.8, "bare circuit\n+ noise (lambda)", "#fbe0d4")
    _box(ax, 2.4, 0.6, 2.3, 0.8, "Iceberg-encoded circuit\n+ noise (lambda)", "#d6f0e6")
    _box(ax, 5.1, 1.95, 1.9, 0.8, "raw readout\nor Gauss-law\npost-selection", "#dbe8f7", 7)
    _box(ax, 5.1, 0.6, 1.9, 0.8, "detector\npost-selection\n(+ Gauss)", "#dbe8f7", 7)
    _box(ax, 7.4, 1.0, 2.5, 2.9, "score (v2)\n\n4 modes x 2 references\ncommon window\nESS "
         ">= floor or 'no estimate'\njackknife over batches\ncost = mean(1/acceptance)",
         "#fdeec2", 7)
    for (x0, y0, x1, y1) in ((2.0, 3.7, 2.4, 3.7), (2.0, 3.6, 2.4, 2.35), (2.0, 3.5, 2.4, 1.0),
                             (4.7, 2.35, 5.1, 2.35), (4.7, 1.0, 5.1, 1.0),
                             (7.0, 2.35, 7.4, 2.35), (7.0, 1.0, 7.4, 1.6),
                             (4.7, 3.7, 7.4, 3.5)):
        _arrow(ax, x0, y0, x1, y1)
    ax.text(0.1, 0.1, "Every noisy arm: Pauli-trajectory Monte Carlo with exact readout "
            "distributions, under an ASSUMED noise model. Classical prediction, NOT an H2 result.",
            fontsize=6.8, color=INK2)
    fig.savefig(os.path.join(out, "schem_pipeline.png"), dpi=170, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(REPO, CONFIG.figures_dir))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for fn in (fig_lattice, fig_iceberg, fig_pipeline):
        fn(a.out)
        print("wrote", fn.__name__)


if __name__ == "__main__":
    main()
