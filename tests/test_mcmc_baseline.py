"""Q3 sector-restricted MCMC ergodic baseline (handoff/07, src/mcmc_baseline.py).

What is checked, and against what INDEPENDENT reference:
  * per-configuration observables == the src/dimers.py 2^N operators on every basis state;
  * the shared correlation function == TriangularDimers.dimer_correlation_by_distance;
  * the chain never leaves the defect-free W0 sector (every visited state checked against the
    dimers.py arrays) and samples it UNIFORMLY (chi^2 on independent final states);
  * MCMC averages == brute-force exact enumeration within the autocorrelation-aware SE;
  * ceilings refuse before allocating; the quantum arm uses identical observables;
  * the dressed defect prediction and the H_QDM diagonal ensemble against direct dynamics.
"""

import math

import numpy as np
import pytest
import scipy.linalg as sla
from scipy import stats

from config import RunConfig
from src.backends import MemoryCeilingError
from src import mcmc_baseline
from src.dimers import TriangularDimers
from src.mcmc_baseline import (
    SCALARS, ConfigEvaluator, Shells, classify, dimer_pattern, ensemble_values, exact_references,
    index_from_spins, initial_spins, leak_scaling, qdm_diagonal_ensemble, relaxation_curve,
    sample_sector, sector_census, shell_correlations, moments_from_probabilities, spins_from_index,
)

J, DT = -1.0, 0.25
CEIL = RunConfig().ceilings


@pytest.fixture(scope="module", params=[(3, 3), (3, 4), (4, 3)])
def d(request):
    return TriangularDimers(*request.param)


# --------------------------------------------------------------- identical definitions
def test_config_evaluator_equals_dimers_operators_on_every_basis_state(d):
    z = spins_from_index(np.arange(1 << d.N), d.N)
    assert np.array_equal(index_from_spins(z), np.arange(1 << d.N))
    ev = ConfigEvaluator(d)
    n = ev.dimers(z)
    for k, b in enumerate(d.bonds):
        assert np.array_equal(n[:, k], d.dimer(b))
    assert np.array_equal(ev.defects(z), d.total_defects())
    fl = ev.flippable(z)
    for s in range(d.N):
        assert np.array_equal(fl[:, s], d.flippable(s))
    for y in range(d.Ly):
        assert np.array_equal(ev.winding_x(n, y), d.winding_x(y))
    for x in range(d.Lx):
        assert np.array_equal(ev.winding_y(n, x), d.winding_y(x))


def test_shell_correlations_equal_dimer_correlation_by_distance(d):
    rng = np.random.default_rng(3)
    shells = Shells.build(d)                      # all shells
    for p in (rng.random(1 << d.N), (d.total_defects() == 0).astype(float)):
        p = p / p.sum()
        ref = d.dimer_correlation_by_distance(p)
        mine = shell_correlations(shells, *moments_from_probabilities(d, p))
        assert list(ref) == shells.r
        for r, c in zip(shells.r, mine):
            npairs, csum = ref[r]
            assert c * npairs == pytest.approx(csum, abs=1e-12)


def test_flip_creates_exactly_n_s_defects():
    """The dressing's premise [derived]: on a defect-free configuration, flipping a
    non-flippable spin s creates n_s = #equal consecutive hexagon pairs defects."""
    d = TriangularDimers(3, 4)
    ev = ConfigEvaluator(d)
    free = np.nonzero(d.total_defects() == 0)[0]
    z = spins_from_index(free, d.N)
    ns = ev.equal_hex_pairs(z)
    for s in range(d.N):
        zf = z.copy()
        zf[:, s] *= -1
        assert np.array_equal(ev.defects(zf), ns[:, s])
    assert set(np.unique(ns)) <= {0, 2, 4, 6}


# --------------------------------------------------------------- sector structure
def test_orientation_densities_fixed_by_winding_in_sector():
    """[derived] On the defect-free sector rho_h = (W_x + Lx)/(3 Lx), rho_v = (W_y + Ly)/(3 Ly),
    rho_d = 1 - rho_h - rho_v (N dimers on 3N bonds)."""
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable")
    ex = exact_references(d, s0, Shells.build(d, 1), J, DT, CEIL.ed_max_spins)
    (wx, wy), sc = ex.W0, ex.sector.scalars
    assert sc["rho_h"] == pytest.approx((wx + d.Lx) / (3 * d.Lx))
    assert sc["rho_v"] == pytest.approx((wy + d.Ly) / (3 * d.Ly))
    assert sc["rho_h"] + sc["rho_v"] + sc["rho_d"] == pytest.approx(1.0)
    assert sc["defect_density"] == 0.0


def test_sector_restriction_is_necessary_global_average_differs():
    """A winding-blind average mixes sectors the dynamics cannot connect (1706.02601): on 3x4 it
    differs from the W0 = (0, 2) sector value in discriminating observables."""
    d = TriangularDimers(3, 4)
    ex = exact_references(d, initial_spins(d, "flippable"), Shells.build(d, 3), J, DT, CEIL.ed_max_spins)
    assert ex.sector.dim == 60 and ex.global_.dim == 68
    assert abs(ex.global_.scalars["flippable_density"] - ex.sector.scalars["flippable_density"]) > 0.03
    assert abs(ex.global_.scalars["rho_v"] - ex.sector.scalars["rho_v"]) > 0.05


def test_sector_census_each_sector_is_one_component_or_frozen():
    for L in [(3, 3), (3, 4), (4, 4)]:
        for W, size, ncomp, largest in sector_census(TriangularDimers(*L), CEIL.ed_max_spins):
            assert ncomp == 1 or largest == 1, (L, W, size, ncomp, largest)


# --------------------------------------------------------------- the sampler
def test_sampler_never_leaves_the_sector_checked_against_dimers_arrays():
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable")
    ex = exact_references(d, s0, Shells.build(d, 1), J, DT, CEIL.ed_max_spins)
    res = sample_sector(d, s0, Shells.build(d, 1), J=J, dt=DT, n_chains=8, n_sweeps=300,
                        burn_in=20, rng=np.random.default_rng(5), record_visits=True)
    v = np.unique(res.visits)
    assert np.all(ex.masks["sector"][v])
    assert np.all(d.total_defects()[v] == 0)
    for y in range(d.Ly):
        assert np.all(d.winding_x(y)[v] == ex.W0[0])
    for x in range(d.Lx):
        assert np.all(d.winding_y(x)[v] == ex.W0[1])
    assert len(v) == ex.sector.dim          # and it reaches all 60 states


def test_sampler_raises_on_a_bad_INITIAL_state_only():
    """The guard's initial-state branch: s0 = all up on 3x3 has all 18 triangles defective and
    ZERO flippable sites, so the sampler performs no flips at all and the RuntimeError comes
    from the state it was handed, not from the mover. (Review: this test alone passes even if
    the flip-application code is a complete no-op — see the mover test below for the real
    regression.) A configuration with defects also has cut-dependent winding."""
    d = TriangularDimers(3, 3)
    ev = ConfigEvaluator(d)
    z = np.ones((1, d.N), dtype=np.int8)
    assert ev.defects(z)[0] == 2 * d.N            # every triangle defective
    assert ev.flippable(z).sum() == 0             # nothing can move
    with pytest.raises(RuntimeError, match="left the defect-free"):
        sample_sector(d, np.ones((3, 3), dtype=int), Shells.build(d, 1), J=J, dt=DT, n_chains=2,
                      n_sweeps=2, burn_in=0, rng=np.random.default_rng(0))


def test_sampler_guard_catches_a_mover_caused_escape(monkeypatch):
    """The real regression (review): start IN the sector (3x4 'flippable', 0 defects) and make
    the mover itself propose an invalid move, so the guard has to catch an escape caused by the
    flip-application code — the path the bad-initial-state test above never reaches.

    Injection: the flip condition reads the hexagon-neighbour table `ev.hex[s]`. Site BAD is
    genuinely NOT flippable in this configuration (n_s = 2, flipping it creates 2 defects),
    while site DONOR is. Giving BAD the DONOR's hexagon row makes BAD *look* flippable, so the
    mover flips it and leaves the defect-free W0 sector. Everything the guard itself uses
    (triangles for the defect count, row/column cuts for the windings) is untouched.
    """
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable")
    ev = ConfigEvaluator(d)
    z0 = np.asarray(s0, dtype=np.int8).reshape(1, -1)
    ns = ev.equal_hex_pairs(z0)[0]
    BAD, DONOR = 0, 1
    assert ev.defects(z0)[0] == 0                 # the start really is in the sector
    assert ns[BAD] == 2 and ns[DONOR] == 0        # BAD is not flippable, DONOR is

    class HexCorrupted(ConfigEvaluator):
        def __init__(self, dd):
            super().__init__(dd)
            self.hex = self.hex.copy()
            self.hex[BAD] = self.hex[DONOR]

    monkeypatch.setattr(mcmc_baseline, "ConfigEvaluator", HexCorrupted)
    with pytest.raises(RuntimeError, match="left the defect-free W0 sector"):
        sample_sector(d, s0, Shells.build(d, 1), J=J, dt=DT, n_chains=2, n_sweeps=3,
                      burn_in=0, rng=np.random.default_rng(0))
    # ... and without the injection the very same run is clean (the guard is not trigger-happy).
    monkeypatch.undo()
    res = sample_sector(d, s0, Shells.build(d, 1), J=J, dt=DT, n_chains=2, n_sweeps=3,
                        burn_in=0, rng=np.random.default_rng(0))
    assert res.accept_rate > 0


def test_sampler_is_uniform_on_the_component_chi2():
    """Independent samples (final state of many chains) are uniform over the 42 states."""
    d = TriangularDimers(3, 3)
    s0 = initial_spins(d, "3-sublattice")
    res = sample_sector(d, s0, Shells.build(d, 1), J=J, dt=DT, n_chains=2000, n_sweeps=1,
                        burn_in=60, rng=np.random.default_rng(11), record_visits=True)
    comp = np.nonzero(exact_references(d, s0, Shells.build(d, 1), J, DT, CEIL.ed_max_spins).masks["component"])[0]
    counts = np.array([np.sum(res.visits[-1] == i) for i in comp])
    assert counts.sum() == 2000
    assert stats.chisquare(counts).pvalue > 1e-3


@pytest.mark.parametrize("L,kind", [((3, 3), "3-sublattice"), ((3, 4), "flippable")])
def test_mcmc_matches_exact_enumeration_within_se(L, kind):
    d = TriangularDimers(*L)
    s0 = initial_spins(d, kind)
    sh = Shells.build(d, 3)
    ex = exact_references(d, s0, sh, J, DT, CEIL.ed_max_spins)
    res = sample_sector(d, s0, sh, J=J, dt=DT, n_chains=24, n_sweeps=1500, burn_in=100,
                        rng=np.random.default_rng(17))
    for k in SCALARS:
        e = res.scalars[k]
        assert abs(e.value - ex.sector.scalars[k]) <= 4 * e.se + 1e-9, k
    assert abs(res.dressing.value - ex.sector.dressing) <= 4 * res.dressing.se + 1e-9
    for (v, se), x in zip(res.shells, ex.sector.shells):
        assert abs(v - x) <= 4 * se + 1e-9
    # discriminating: the chain started at c0 must have forgotten it (memory(c0) = 1)
    assert res.scalars["memory"].value < 0.5
    # autocorrelation is visible and accounted for
    assert res.scalars["memory"].tau_int > 0.5


def test_frozen_start_never_moves():
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "stripe")
    res = sample_sector(d, s0, Shells.build(d, 1), J=J, dt=DT, n_chains=4, n_sweeps=20,
                        burn_in=0, rng=np.random.default_rng(1), record_visits=True)
    assert res.accept_rate == 0.0
    assert np.all(res.visits == d.product_state_index(s0))
    assert res.scalars["memory"].value == 1.0


# --------------------------------------------------------------- ceilings
def test_ceilings_refuse_before_allocating():
    big = TriangularDimers(5, 5)            # N = 25: above both ceilings
    with pytest.raises(MemoryCeilingError):
        exact_references(big, np.ones((5, 5)), Shells.build(big, 1), J, DT, CEIL.ed_max_spins)
    with pytest.raises(MemoryCeilingError):
        sector_census(big, CEIL.ed_max_spins)
    with pytest.raises(MemoryCeilingError):
        relaxation_curve(big, np.ones((5, 5)), Shells.build(big, 1), J=J, h=0.3, dt=DT,
                         total_time=1.0, max_snapshots=2, max_spins=CEIL.statevector_max_spins)
    with pytest.raises(MemoryCeilingError):
        initial_spins(TriangularDimers(4, 6), "flippable", CEIL.ed_max_spins)   # N = 24 > 20
    n21 = TriangularDimers(3, 7)            # N = 21: under the state-vector ceiling, over ED
    with pytest.raises(MemoryCeilingError):   # 2^N x 3N tables: guarded at the ED ceiling (review m2)
        relaxation_curve(n21, np.ones((7, 3)), Shells.build(n21, 1), J=J, h=0.3, dt=DT,
                         total_time=1.0, max_snapshots=2, max_spins=CEIL.ed_max_spins)
    with pytest.raises(MemoryCeilingError):
        qdm_diagonal_ensemble(n21, np.ones((7, 3)), np.zeros(1, dtype=bool), max_spins=CEIL.ed_max_spins)


def test_mcmc_runs_beyond_the_exact_ceiling():
    d = TriangularDimers(9, 6)              # the reference Sec. V lattice size, N = 54
    res = sample_sector(d, initial_spins(d, "3-sublattice"), Shells.build(d, 2), J=J, dt=DT,
                        n_chains=4, n_sweeps=20, burn_in=5, rng=np.random.default_rng(2))
    assert res.W0 == (0, 0) and res.accept_rate > 0


# --------------------------------------------------------------- quantum arm
@pytest.fixture(scope="module")
def curve34():
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable")
    sh = Shells.build(d, 3)
    return d, s0, sh, relaxation_curve(d, s0, sh, J=J, h=0.3, dt=DT, total_time=40.0,
                                       max_snapshots=80, max_spins=CEIL.ed_max_spins)


def test_quantum_arm_uses_identical_observables(curve34):
    d, s0, sh, c = curve34
    ev = ConfigEvaluator(d)
    z0 = np.asarray(s0, dtype=np.int8).reshape(1, -1)
    sc0 = ev.scalars(z0, dimer_pattern(d, s0))
    for k in SCALARS:
        assert c.raw[k][0] == pytest.approx(float(sc0[k][0]))
    p0 = np.zeros(1 << d.N)
    p0[d.product_state_index(s0)] = 1
    assert np.allclose(c.raw_shells[0], shell_correlations(sh, *moments_from_probabilities(d, p0)))


def test_leakage_decomposition_bound_holds(curve34):
    """[derived] |<O> - <O>_in| <= P_out for every [0,1]-valued diagonal observable, at all t."""
    _, _, _, c = curve34
    for k in SCALARS:
        assert np.all(np.abs(c.raw[k] - c.cond[k]) <= c.p_out + 1e-12)
    assert np.all(c.cond["defect_density"] == 0.0)
    assert np.all(c.p_wleak <= c.p_out + 1e-12)
    assert c.p_out.max() < 0.25 and c.p_out[1:].mean() > 1e-3


def test_dressed_defect_density_matches_dynamics_small_h():
    """rho_D ~= h^2 [<g>_DE + g(c0)] [derived, first order] against direct Trotter dynamics.
    (The DE, not the infinite-T sector average, is what this finite cluster visits.)"""
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable")
    sh = Shells.build(d, 1)
    h = 0.05
    c = relaxation_curve(d, s0, sh, J=J, h=h, dt=DT, total_time=12 / h, max_snapshots=120,
                         max_spins=CEIL.ed_max_spins)
    ex = exact_references(d, s0, sh, J, DT, CEIL.ed_max_spins)
    de = ensemble_values(d, qdm_diagonal_ensemble(d, s0, ex.masks["component"]),
                         dimer_pattern(d, s0), sh, J, DT)
    g0 = ConfigEvaluator(d).dressing(np.asarray(s0, dtype=np.int8).reshape(1, -1), J, DT)[0]
    late = c.times >= c.times[-1] / 2
    assert c.raw["defect_density"][late].mean() == pytest.approx(h * h * (de.dressing + g0), rel=0.03)


def test_dressing_stripe_limit_is_one_over_sixteen():
    """Stripe: n_s = 2 everywhere -> g = 1/16 at dt -> 0, so rho_D = (h/|J|)^2/8 (gauss_law_dimers §4)."""
    d = TriangularDimers(3, 4)
    z = np.asarray(d.stripe_spins(), dtype=np.int8).reshape(1, -1)
    assert ConfigEvaluator(d).dressing(z, J, 0.0)[0] == pytest.approx(1 / 16)


def test_diagonal_ensemble_equals_long_time_average_of_h_qdm():
    d = TriangularDimers(3, 3)
    s0 = initial_spins(d, "3-sublattice")
    ex = exact_references(d, s0, Shells.build(d, 1), J, DT, CEIL.ed_max_spins)
    comp = np.nonzero(ex.masks["component"])[0]
    pde = qdm_diagonal_ensemble(d, s0, ex.masks["component"])
    assert pde.sum() == pytest.approx(1.0)
    H = d.qdm_hamiltonian(1.0).tocsr()[comp][:, comp].toarray()
    w, v = np.linalg.eigh(H)
    psi0 = np.zeros(len(comp))
    psi0[np.searchsorted(comp, d.product_state_index(s0))] = 1
    ts = np.random.default_rng(4).uniform(0, 5000, 4000)
    avg = np.mean([np.abs(v @ (np.exp(-1j * w * t) * (v.T @ psi0))) ** 2 for t in ts], axis=0)
    assert np.allclose(avg, pde[comp], atol=0.01)


def test_classify_labels(curve34):
    d, s0, sh, c = curve34
    v = classify(c, "defect_density", 0.0, 0.0, frozen=True)
    assert v.label == "frozen"
    assert abs(v.shift) <= v.envelope + 1e-12
    late_cond = c.cond["flippable_density"][c.times >= c.times[-1] / 2].mean()
    assert classify(c, "flippable_density", late_cond, 0.0).label == "thermalized-in-sector"
    assert classify(c, "flippable_density", late_cond + 1.0, 0.0,
                    de_value=late_cond).label == "finite-size-DE-offset"
    assert classify(c, "flippable_density", late_cond + 1.0, 0.0).label == "not-relaxed-in-window"
    assert classify(c, "flippable_density", late_cond, 0.0, de_value=late_cond + 1e-6).label == "indistinguishable"


def test_shell_verdict_uses_window_averaged_moments(curve34):
    """Review fix M1: the window value of C(r) is C of the window-averaged moments (the window's
    mixed state), NOT the mean of the instantaneous C(r; t), which adds the temporal covariance
    of <n_a>(t). On 3x4 the corrected C(0.5) lands on the DE / sector value."""
    d, s0, sh, c = curve34
    late = c.times >= c.times[-1] / 2
    v = classify(c, "C", -0.1, 0.0, shell=0)
    m1, m2 = c.cond_mom
    assert v.late_cond == pytest.approx(shell_correlations(sh, m1[late].mean(0), m2[late].mean(0))[0])
    ex = exact_references(d, s0, sh, J, DT, CEIL.ed_max_spins)
    de = ensemble_values(d, qdm_diagonal_ensemble(d, s0, ex.masks["component"]), dimer_pattern(d, s0), sh, J, DT)
    naive = c.cond_shells[late, 0].mean()
    assert abs(v.late_cond - de.shells[0]) < abs(naive - de.shells[0])
    assert abs(v.late_cond - de.shells[0]) <= v.late_std


def test_leak_scaling_reads_the_measured_slope():
    A, s = leak_scaling("data/gauss_law_scaling.txt", "3x6 3-sublattice", 0.25)
    assert round(s, 2) == 2.08          # the file's printed slope
    assert A * 0.3 ** s == pytest.approx(1.66e-2, rel=0.1)
    assert leak_scaling("data/gauss_law_scaling.txt", "9x6 nothing", 0.25) is None
