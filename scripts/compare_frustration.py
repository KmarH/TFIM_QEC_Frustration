"""Q2 (SCOPE §2): frustration — triangular vs square — on shared observables.

Compares the square and triangular TFIM at matched size and field, using only the
geometry-agnostic Stage-1 machinery (ED ground state via src.backends) and the Stage-3
dimer observables (src.dimers), within the SCOPE §5 ceilings. Local ED only; no hardware.

What it reports (ground state of H = -J sum ZZ - h sum X, AFM frustrated sign J<0 to match
arXiv:2503.20870 §V; periodic BC both lattices for a fair torus-vs-torus comparison):
  - ground-state energy per site,
  - total |M_z| (Z-magnetization; frustration suppresses order),
  - mean nearest-neighbour <Z_i Z_j> over the bond list (bond-energy density proxy),
  - (triangular only) Gauss-law defect density per triangle — the frustration-specific
    observable, which has no square-lattice analogue.

CAVEAT (T-19, docs/q2_frustration.md A.2): the 3x4 square torus used here has an odd periodic
length, so it is NOT bipartite and its antiferromagnet is itself frustrated (h=0 E/bond -2/3,
vs -1 on the bipartite 4x4). It is not a clean unfrustrated reference; within ED <= 20 only the
4x4 square torus is. The clean matched contrast is data/frustration_correlations.txt (4x4).

The contrast this script was written for: on the square (unfrustrated) lattice the AFM ground state
orders and nearest-neighbour <ZZ> is strongly negative with little field-sensitivity at
small h; on the triangular (frustrated) lattice the three bonds of every triangle cannot
all be satisfied, so the ground-state bond correlations are weaker/degenerate and the
dimer/defect language (not available for the square lattice) becomes the right description.
Numbers are MEASURED; interpretation is cross-checked against src/dimers.py identities.
"""

from __future__ import annotations

import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import RunConfig  # noqa: E402
from src.backends import run_ed  # noqa: E402
from src.dimers import TriangularDimers  # noqa: E402
from src.observables import total_magnetization_z, two_point_correlations_z  # noqa: E402
from src.operators import tfim_hamiltonian  # noqa: E402


def _ground_state(geometry: str, Lx: int, Ly: int, J: float, h: float):
    cfg = RunConfig()
    cfg.backend = "ed"
    cfg.lattice.geometry = geometry
    cfg.lattice.boundary = "periodic"
    cfg.lattice.Lx, cfg.lattice.Ly = Lx, Ly
    cfg.model.J, cfg.model.h = J, h
    res = run_ed(cfg, k=1)
    return res.eigenvalues[0], res.eigenvectors[:, 0], res.bonds


def _mean_nn_zz(psi, n, bonds):
    """Mean raw <Z_i Z_j> over the bond list (bond-energy density proxy)."""
    # reuse the connected-correlation helper's raw cousin via expval on dimer parity
    from src.observables import expval_zz
    return float(np.mean([expval_zz(psi, n, i, j) for (i, j) in bonds]))


def main() -> None:
    J = -1.0  # frustrated AFM sign in our H = -J sum ZZ - h sum X convention
    Lx, Ly = 3, 4  # 12 spins; periodic; >=3x4 so the triangular torus has >1 winding sector
    n = Lx * Ly
    fields = [0.0, 0.1, 0.3, 0.6, 1.0]

    out = []
    log = lambda s="": (print(s), out.append(s))  # noqa: E731
    log(f"# Q2 frustration comparison — triangular vs square, {Lx}x{Ly}={n} spins, periodic, J={J} (AFM)")
    log("# H = -J sum ZZ - h sum X; ground state by Lanczos ED. Numbers are measured.")
    log(f"# {'geom':<11} {'h':>5} {'E/site':>10} {'|M_z|':>8} {'mean<ZZ>':>10} {'defect_dens':>12}")

    dimers = TriangularDimers(Lx, Ly)
    for h in fields:
        for geom in ("square", "triangular"):
            e0, psi, bonds = _ground_state(geom, Lx, Ly, J, h)
            mz = abs(total_magnetization_z(psi, n))
            nnzz = _mean_nn_zz(psi, n, bonds)
            if geom == "triangular":
                dens = dimers.defect_density(psi)
                dstr = f"{dens:12.4e}"
            else:
                dstr = f"{'n/a':>12}"
            log(f"  {geom:<11} {h:5.2f} {e0/n:10.5f} {mz:8.4f} {nnzz:10.5f} {dstr}")
        log()

    # Headline contrast at h=0 (classical frustrated limit): energy per bond is the
    # basis-independent frustration measure (the h=0 ground state is degenerate, so a single
    # Lanczos vector's <ZZ> and M_z are basis-dependent artifacts and are NOT interpreted).
    log("# Interpretation (h=0, classical limit) — energy per bond is basis-independent:")
    e_sq, _, bsq = _ground_state("square", Lx, Ly, J, 0.0)
    e_tri, _, btri = _ground_state("triangular", Lx, Ly, J, 0.0)
    log(f"#   square     E/bond at h=0 = {e_sq/len(bsq):+.4f} over {len(bsq)} bonds")
    log(f"#   triangular E/bond at h=0 = {e_tri/len(btri):+.4f} over {len(btri)} bonds "
        f"(less negative -> more frustrated: a triangle satisfies only 1 of 3 bonds)")
    log("#   The h=0 ground state is degenerate on both lattices, so the per-vector |M_z| and")
    log("#   mean<ZZ> columns above are basis-dependent and not interpreted; energy/bond is the")
    log("#   honest frustration signature. The triangular defect density is ~0 in the ground")
    log("#   manifold (= defect-free Gauss-law subspace) and grows as (h/|J|)^2 off it")
    log("#   (data/gauss_law_scaling.txt). The square lattice has no dimer/defect description;")
    log("#   that observable is frustration-specific.")
    log("# CAVEAT (T-19): this 3x4 square torus has an odd periodic length (3), so it is NOT bipartite")
    log("#   and its AFM is itself frustrated (h=0 E/bond -2/3, vs -1 on the bipartite 4x4). It is not a")
    log("#   clean unfrustrated reference; part of the -0.667 vs -0.333 contrast is odd-length frustration.")
    log("#   Within ED <= 20 only the 4x4 square torus is clean: see docs/q2_frustration.md A.2 and")
    log("#   data/frustration_correlations.txt (scripts/compare_frustration_correlations.py).")

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    path = os.path.join(ROOT, "data", "frustration_compare.txt")
    with open(path, "w") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"\nwritten to {path}")


if __name__ == "__main__":
    main()
