"""Q2 frustration, Part A (handoff/09; src/frustration.py): distance-resolved connected correlations.

Independent references: the even-sector ground state against src.backends.run_ed's energy; the
connected form against a product state (raw <ZZ> = 1, connected = 0); the binning against the bond
lists (nearest-neighbour shell == bonds) and the pair count; the square-torus bipartiteness claim
against the exact h = 0 energy per bond; the frustration contrast as MEASURED (not assumed).
"""

import math

import numpy as np
import pytest

from config import RunConfig
from src.backends import MemoryCeilingError, run_ed
from src.frustration import (
    bonds_for, correlation_by_distance, even_sector_ground_state, is_bipartite_torus,
    max_abs_magnetization, site_distance, spectral_gaps,
)
from src.observables import expval_zz

J = -1.0
CEIL = RunConfig().ceilings


def _ed_energy(geom, Lx, Ly, h):
    cfg = RunConfig()
    cfg.backend = "ed"
    cfg.lattice.geometry, cfg.lattice.boundary = geom, "periodic"
    cfg.lattice.Lx, cfg.lattice.Ly = Lx, Ly
    cfg.model.J, cfg.model.h = J, h
    return float(run_ed(cfg, k=1).eigenvalues[0])


@pytest.mark.parametrize("geom,L,h", [("square", (4, 4), 0.3), ("triangular", (3, 4), 0.3),
                                      ("triangular", (3, 3), 0.6), ("square", (3, 4), 1.0)])
def test_even_sector_ground_state_is_the_ground_state(geom, L, h):
    gs = even_sector_ground_state(geom, *L, J, h, CEIL.ed_max_spins)
    assert gs.energy == pytest.approx(_ed_energy(geom, *L, h), abs=1e-9)
    assert np.linalg.norm(gs.psi) == pytest.approx(1.0)
    assert max_abs_magnetization(gs.psi, gs.n) < 1e-12          # P-even: <Z_i> = 0 exactly
    assert np.allclose(gs.psi, gs.psi[::-1])                     # invariant under the global flip


def test_square_neel_pair_is_quasi_degenerate():
    """On the 4x4 square at h = 0.3 the Neel pair is quasi-degenerate (gap below numerical resolution),
    which is why an unrestricted Lanczos vector is an arbitrary symmetry-broken mixture and the
    ground state is taken in the P-even sector instead."""
    gaps = spectral_gaps("square", 4, 4, J, 0.3, CEIL.ed_max_spins)
    assert gaps[0] < 1e-8 and gaps[1] > 1.0


def test_connected_form_vanishes_on_a_product_state():
    n = 9
    psi = np.zeros(1 << n)
    psi[0] = 1.0                                                  # all up: raw <ZZ> = 1, connected = 0
    shells = correlation_by_distance(psi, "triangular", 3, 3)
    assert all(abs(s.mean) < 1e-12 and abs(s.lo) < 1e-12 and abs(s.hi) < 1e-12 for s in shells)
    assert expval_zz(psi, n, 0, 1) == pytest.approx(1.0)


@pytest.mark.parametrize("geom,L", [("square", (4, 4)), ("square", (3, 4)), ("triangular", (3, 4)),
                                    ("triangular", (4, 4))])
def test_binning_nearest_shell_is_the_bond_list(geom, L):
    n = L[0] * L[1]
    bonds = bonds_for(geom, *L)
    near = {(i, j) for i in range(n) for j in range(i + 1, n) if abs(site_distance(geom, *L, i, j) - 1.0) < 1e-9}
    assert near == {tuple(sorted(b)) for b in bonds}
    psi = np.zeros(1 << n)
    psi[0] = 1.0
    shells = correlation_by_distance(psi, geom, *L)
    assert sum(s.n_pairs for s in shells) == n * (n - 1) // 2
    assert shells[0].r == pytest.approx(1.0) and shells[0].n_pairs == len(bonds)


def test_triangular_metric_matches_the_dimers_embedding():
    """sqrt(3) is the next-nearest distance (same 3-sublattice colour) in the dimers.py embedding."""
    assert site_distance("triangular", 6, 6, 0, 2 * 6 + 1) == pytest.approx(math.sqrt(3))   # (0,0)-(1,2)
    assert site_distance("square", 4, 4, 0, 5) == pytest.approx(math.sqrt(2))


def test_odd_square_torus_is_frustrated():
    """[measured] h = 0 energy per bond: -1 on the bipartite 4x4 square, -2/3 on 3x4."""
    for L, ebond, bip in (((4, 4), -1.0, True), ((3, 4), -2 / 3, False)):
        gs = even_sector_ground_state("square", *L, J, 0.0, CEIL.ed_max_spins)
        assert gs.energy / len(gs.bonds) == pytest.approx(ebond)
        assert is_bipartite_torus("square", *L) is bip
    assert not is_bipartite_torus("triangular", 4, 4)


def test_frustration_contrast_is_measured_not_assumed():
    """Matched 4x4 pair at h = 0.6 [measured, data/frustration_correlations.txt]: the square (bipartite)
    nearest-neighbour correlation is far more AFM (-0.98) than the triangular one (-0.27), and the
    square correlations do not decay across the torus (|C(r_max)| ~ 0.98) while the triangular ones do."""
    sq = correlation_by_distance(even_sector_ground_state("square", 4, 4, J, 0.6, CEIL.ed_max_spins).psi, "square", 4, 4)
    tr = correlation_by_distance(even_sector_ground_state("triangular", 4, 4, J, 0.6, CEIL.ed_max_spins).psi,
                                 "triangular", 4, 4)
    assert sq[0].mean < -0.95 and abs(sq[-1].mean) > 0.95
    assert -0.35 < tr[0].mean < -0.2 and abs(tr[-1].mean) < 0.3
    assert sq[0].mean < tr[0].mean


def test_ceiling_refused_before_allocating():
    with pytest.raises(MemoryCeilingError):
        even_sector_ground_state("square", 3, 7, J, 0.3, CEIL.ed_max_spins)
    with pytest.raises(MemoryCeilingError):
        spectral_gaps("triangular", 3, 7, J, 0.3, CEIL.ed_max_spins)
