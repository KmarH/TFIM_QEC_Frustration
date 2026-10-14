"""Q2 Part A (handoff/09): distance-resolved connected <ZZ>_c, square vs triangular -> data/frustration_correlations.txt.

Exact ground states (ED in the global-spin-flip-even sector, checked against src.backends.run_ed) of
H = -J sum ZZ - h sum X, J < 0 (AFM), periodic square and triangular tori at matched size and field.
C(r) = mean connected <Z_i Z_j> - <Z_i><Z_j> (src.observables.two_point_correlations_z) over the
pairs at minimal-image Euclidean distance r (src/frustration.py). Settings: config.CONFIG.q2.
Classical ED only; every number [measured]; NOT an H2 result. Usage: python -I scripts/compare_frustration_correlations.py
"""

from __future__ import annotations

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config import CONFIG, RunConfig  # noqa: E402
from src.backends import run_ed  # noqa: E402
from src.frustration import (  # noqa: E402
    correlation_by_distance, even_sector_ground_state, is_bipartite_torus, max_abs_magnetization,
    spectral_gaps,
)

Q = CONFIG.q2
C = CONFIG.ceilings


def run_ed_energy(geometry, Lx, Ly, J, h):
    cfg = RunConfig()
    cfg.backend = "ed"
    cfg.lattice.geometry, cfg.lattice.boundary = geometry, "periodic"
    cfg.lattice.Lx, cfg.lattice.Ly = Lx, Ly
    cfg.model.J, cfg.model.h = J, h
    return float(run_ed(cfg, k=1).eigenvalues[0])


def main():
    out = []

    def log(line=""):
        out.append(line)
        print(line, flush=True)

    log(f"# generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/compare_frustration_correlations.py (handoff/09 Part A)")
    log("# CLASSICAL exact diagonalization only; every number [measured]; NOT an H2 / hardware result.")
    log(f"# H = -J sum ZZ - h sum X, J={Q.J} (AFM), periodic tori. Ground state: exact, in the global-spin-flip-EVEN sector "
        "(unique and P-even for h > 0 by Perron-Frobenius [derived]; avoids the symmetry-broken Lanczos mixtures a "
        "near-degenerate torus produces). dE_ED = E_even - E(src.backends.run_ed) (must be ~0).")
    log("# C(r) = mean over pairs at distance r of the CONNECTED <Z_i Z_j> - <Z_i><Z_j>; [lo, hi] = spread inside the "
        "shell (inequivalent directions). Distance = minimal-image EUCLIDEAN site distance, nearest neighbours at 1: "
        "square (x,y); triangular x e1 + y e2 with e1=(1,0), e2=(-1/2, sqrt3/2) (the src/dimers.py embedding).")
    log("# h = 0: degenerate ground state on both lattices (massively on the triangular one) -> single-vector C(r) is "
        "recorded but NOT interpreted. gaps = E1-E0, E2-E0 in the full space.")
    log("# CAVEAT 1 [measured]: a square torus with an ODD periodic length is not bipartite, so its AFM is itself "
        "frustrated (h=0 E/bond -2/3 on 3x4 vs -1 on 4x4): only even x even square tori are the unfrustrated reference. "
        "The 3x4 pair (data/frustration_compare.txt) is kept for continuity, flagged.")
    log("# CAVEAT 2 [established]: the repo's triangular embedding (square + one diagonal) sits at the J'=J point of "
        "Iglovikov et al., PRB 87, 214415 (arXiv:1303.0883), near a Stephenson disorder line / incommensurate floating "
        "phase: triangular C(r) on small tori may be incommensurate, non-monotonic and torus-shape dependent. No "
        "'frustration monotonically weakens order' story is read into it.")

    summary = []
    for Lx, Ly in Q.partA_clusters:
        for geom in ("square", "triangular"):
            bip = is_bipartite_torus(geom, Lx, Ly)
            tag = ("square, bipartite = UNFRUSTRATED reference" if bip else
                   "square, odd periodic length = itself FRUSTRATED" if geom == "square" else "triangular, frustrated")
            log(f"\n## {geom} {Lx}x{Ly} (N={Lx * Ly}; {tag})")
            for h in Q.fields:
                t0 = time.time()
                gs = even_sector_ground_state(geom, Lx, Ly, Q.J, h, C.ed_max_spins)
                de = gs.energy - run_ed_energy(geom, Lx, Ly, Q.J, h)
                gaps = spectral_gaps(geom, Lx, Ly, Q.J, h, C.ed_max_spins)
                shells = correlation_by_distance(gs.psi, geom, Lx, Ly, Q.distance_decimals)
                note = "   [h=0: degenerate, NOT interpreted]" if h == 0 else ""
                log(f"  h={h:<4} E/site={gs.energy / gs.n:+.5f} E/bond={gs.energy / len(gs.bonds):+.5f} dE_ED={de:+.1e} "
                    f"gaps={gaps[0]:.2e},{gaps[1]:.2e} max|<Z_i>|={max_abs_magnetization(gs.psi, gs.n):.1e} "
                    f"({time.time() - t0:.1f}s){note}")
                for s in shells:
                    log(f"      r={s.r:<9.6f} pairs={s.n_pairs:<4d} C(r)={s.mean:+.5f}  [{s.lo:+.5f}, {s.hi:+.5f}]")
                summary.append((Lx, Ly, geom, h, shells))

    log("\n## Summary at h > 0: nearest-neighbour C(1) and the farthest shell C(r_max) [measured]. r_max differs between "
        "the geometries (it is the largest minimal-image distance of each torus), so the C(r_max) columns are a "
        "long-distance indicator per lattice, not a like-for-like distance.")
    log(f"  {'cluster':>7s} {'h':>4s} | {'square C(1)':>11s} {'C(r_max)':>9s} {'r_max':>6s} | {'triang C(1)':>11s} {'C(r_max)':>9s} "
        f"{'r_max':>6s} | square more AFM-correlated at r=1?")
    for Lx, Ly in Q.partA_clusters:
        for h in Q.fields:
            if h == 0:
                continue
            sq = next(s for (a, b, g, hh, s) in summary if (a, b, g, hh) == (Lx, Ly, "square", h))
            tr = next(s for (a, b, g, hh, s) in summary if (a, b, g, hh) == (Lx, Ly, "triangular", h))
            log(f"  {Lx}x{Ly:<5d} {h:4.1f} | {sq[0].mean:+11.4f} {sq[-1].mean:+9.4f} {sq[-1].r:6.3f} | {tr[0].mean:+11.4f} "
                f"{tr[-1].mean:+9.4f} {tr[-1].r:6.3f} | "
                f"{'yes' if sq[0].mean < tr[0].mean else 'NO'}")
    with open(os.path.join(ROOT, CONFIG.data_dir, "frustration_correlations.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote data/frustration_correlations.txt")


if __name__ == "__main__":
    main()
