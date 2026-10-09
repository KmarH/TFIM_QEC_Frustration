"""Stage 3 triangular-lattice tests (SCOPE §4 stage 3, the frustrated main focus).

Covers only the solid, checkable part built so far: the triangular GEOMETRY and the
fact that the Stage-1 TFIM machinery (operators / Trotter / ED) is geometry-agnostic
and runs unchanged on a triangular bond list. The dimer / Gauss-law observables are
deliberately NOT here — they are flagged for a Claude Code hand-off
(research/03-stage3-triangular.md), not invented.
"""

import numpy as np
import scipy.sparse.linalg as sla
import pytest

from config import RunConfig
from src.backends import product_state, run_ed, run_statevector
from src.lattice import triangular_bonds
from src.operators import tfim_hamiltonian


def test_triangular_periodic_bond_count_is_3N():
    # Fully periodic triangular lattice (Lx,Ly >= 3): coordination 6 -> 3N bonds.
    for (Lx, Ly) in [(3, 3), (4, 3), (4, 4)]:
        bonds = triangular_bonds(Lx, Ly, "periodic")
        N = Lx * Ly
        assert len(bonds) == 3 * N
        assert len(set(bonds)) == len(bonds)          # unique
        assert all(i < j for (i, j) in bonds)          # ordered
        assert all(i != j for (i, j) in bonds)         # no self-loops


def test_triangular_interior_coordination_is_six():
    # On a periodic lattice every site has exactly 6 neighbours.
    Lx, Ly = 4, 4
    bonds = triangular_bonds(Lx, Ly, "periodic")
    deg = {s: 0 for s in range(Lx * Ly)}
    for (i, j) in bonds:
        deg[i] += 1
        deg[j] += 1
    assert set(deg.values()) == {6}


def test_triangular_open_has_frustrated_triangle():
    # Smallest open triangular patch (2x2 grid + diagonal) must contain a 3-cycle,
    # the elementary frustrated unit. Check a triangle exists among the bonds.
    bonds = set(triangular_bonds(2, 2, "open"))
    # candidate triangle: sites 0,1,3 (x,y)=(0,0),(1,0),(1,1); 0-1 (d1), 1-3 (d2), 0-3 (d3)
    def edge(a, b):
        return (min(a, b), max(a, b)) in bonds
    assert edge(0, 1) and edge(1, 3) and edge(0, 3)


def test_triangular_hamiltonian_hermitian():
    bonds = triangular_bonds(3, 3, "periodic")
    H = tfim_hamiltonian(9, bonds, J=1.0, h=0.6)
    diff = (H - H.getH())
    assert abs(diff).max() < 1e-12


def test_tfim_machinery_is_geometry_agnostic_ed_vs_dense():
    # ED on a small triangular cluster must match dense diagonalization: proves the
    # Stage-1 operator/backend code runs unchanged on triangular geometry.
    cfg = RunConfig()
    cfg.backend = "ed"
    cfg.lattice.geometry = "triangular"
    cfg.lattice.Lx, cfg.lattice.Ly = 3, 2   # 6 spins
    cfg.lattice.boundary = "open"
    cfg.model.J, cfg.model.h = 1.0, 0.5
    res = run_ed(cfg, k=1)
    H = tfim_hamiltonian(6, res.bonds, cfg.model.J, cfg.model.h).toarray()
    w = np.linalg.eigvalsh(H)
    assert abs(res.eigenvalues[0] - w[0]) < 1e-8


def test_triangular_statevector_matches_exact_expm():
    # 2nd-order Trotter on triangular geometry converges to exact expm on a small cluster.
    cfg = RunConfig()
    cfg.backend = "statevector"
    cfg.lattice.geometry = "triangular"
    cfg.lattice.Lx, cfg.lattice.Ly = 3, 2
    cfg.lattice.boundary = "open"
    cfg.model.J, cfg.model.h = 1.0, 0.8
    cfg.trotter.total_time, cfg.trotter.n_steps = 1.0, 200

    out = run_statevector(cfg, init_spec="all_up")
    H = tfim_hamiltonian(6, out.bonds, 1.0, 0.8)
    psi0 = product_state(6, "all_up")
    exact = sla.expm_multiply(-1j * 1.0 * H, psi0)
    assert np.linalg.norm(out.final_state - exact) < 1e-3


def test_q2_frustration_signature_triangular_vs_square():
    # Q2 (SCOPE §2): geometric frustration via the basis-independent ground-state energy
    # per bond at h=0 (classical AFM limit, J<0 in our H = -J sum ZZ sign). The square 3x4
    # periodic torus still satisfies its bonds better than the triangular one: each triangle
    # of the frustrated lattice can satisfy only 1 of 3 bonds, so its energy per bond is
    # higher (less negative). Energy is used, not <ZZ> on one Lanczos vector, because the
    # h=0 ground state is degenerate (4-fold here) and single-vector correlators are
    # basis-dependent; the energy is not.
    from config import RunConfig
    from src.backends import run_ed

    J = -1.0
    Lx, Ly = 3, 4

    def e_per_bond(geom):
        cfg = RunConfig()
        cfg.backend = "ed"
        cfg.lattice.geometry = geom
        cfg.lattice.boundary = "periodic"
        cfg.lattice.Lx, cfg.lattice.Ly = Lx, Ly
        cfg.model.J, cfg.model.h = J, 0.0
        res = run_ed(cfg, k=1)
        return res.eigenvalues[0] / len(res.bonds)

    sq = e_per_bond("square")        # -16 / 24 bonds
    tri = e_per_bond("triangular")   # -12 / 36 bonds
    assert sq == pytest.approx(-2.0 / 3.0, abs=1e-6)
    assert tri == pytest.approx(-1.0 / 3.0, abs=1e-6)   # frustrated: 1 of 3 bonds per triangle
    assert tri > sq                                     # less bond energy -> more frustration
