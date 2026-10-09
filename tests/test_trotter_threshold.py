"""Trotter-threshold / dt-convergence study (handoff/08 Part A1, K2; src/trotter_threshold.py).

Checked against independent references: the Chebyshev propagator against scipy expm_multiply and
dense diagonalization; the observable function against src/mcmc_baseline.relaxation_curve (the
Q3 arm); the Strang convergence order (local errors x4 per dt halving, infidelity x16); the
threshold against the first-order Floquet resonance pi/(|J| n_s), including a discriminating start
(the stripe, n_s = 2 only) whose resonance lies 3x higher.
"""

import math

import numpy as np
import pytest
import scipy.sparse.linalg as spla

from config import RunConfig
from src.backends import MemoryCeilingError
from src.dimers import TriangularDimers
from src.mcmc_baseline import Shells, initial_spins, relaxation_curve
from src.operators import tfim_hamiltonian
from src.trotter import ising_diagonal, trotter2_step
from src.trotter_threshold import (
    ExactPropagator, floquet_resonances, late_window_bias, locate_threshold, loglog_slope,
    observable_function, trotter_error_scan,
)

J, H = -1.0, 0.3
CEIL = RunConfig().ceilings


@pytest.fixture(scope="module")
def d33():
    d = TriangularDimers(3, 3)
    return d, initial_spins(d, "3-sublattice"), Shells.build(d, 3)


def test_chebyshev_propagator_matches_expm_multiply_and_eigh(d33):
    d, s0, _ = d33
    U = ExactPropagator(d, J, H)
    Hm = tfim_hamiltonian(d.N, d.bonds, J, H)
    E, V = np.linalg.eigh(Hm.toarray())
    rng = np.random.default_rng(1)
    psi = rng.normal(size=1 << d.N) + 1j * rng.normal(size=1 << d.N)
    psi /= np.linalg.norm(psi)
    for t in (0.07, 0.7, 3.0):
        ours = U(psi, t)
        assert np.linalg.norm(ours - spla.expm_multiply(-1j * t * Hm.tocsc(), psi)) < 1e-10
        assert np.linalg.norm(ours - V @ (np.exp(-1j * E * t) * (V.conj().T @ psi))) < 1e-10


def test_observables_identical_to_the_q3_relaxation_curve(d33):
    d, s0, sh = d33
    c = relaxation_curve(d, s0, sh, J=J, h=H, dt=0.25, total_time=2.0, max_snapshots=8,
                         max_spins=CEIL.ed_max_spins)
    obs = observable_function(d, s0, sh)
    psi = np.zeros(1 << d.N, complex)
    psi[d.product_state_index(s0)] = 1
    diag = ising_diagonal(d.N, d.bonds, J)
    for k, t in enumerate(c.times):
        if k:
            psi = trotter2_step(psi, d.N, diag, H, 0.25)
        o = obs(np.abs(psi) ** 2)
        for key in ("flippable_density", "defect_density", "memory"):
            assert o[key] == pytest.approx(c.raw[key][k], abs=1e-12)
        assert o["C1"] == pytest.approx(c.raw_shells[k, 1], abs=1e-12)


def test_strang_is_second_order(d33):
    """Local errors x4 per dt halving, infidelity x16 (O(dt^4))."""
    d, s0, sh = d33
    scan = trotter_error_scan(d, s0, sh, J=J, h=H, T=5.0, dts=[0.025, 0.05, 0.1],
                              max_spins=CEIL.ed_max_spins)
    for o in ("flippable_density", "memory", "defect_density"):
        dts, e = scan.series(o)
        assert 3.6 < e[1] / e[0] < 4.4 and 3.6 < e[2] / e[1] < 4.4, o
        assert loglog_slope(dts, e, 0.1) == pytest.approx(2.0, abs=0.1)
    inf = [p.infidelity for p in scan.points]
    assert 14 < inf[1] / inf[0] < 18


def test_threshold_sits_at_or_below_the_floquet_resonance(d33):
    """3-sublattice c0 has n_s = 6 spins -> resonance pi/6 = 0.524 [derived]. The error stays
    small at the working dt = 0.25 and blows up approaching the resonance."""
    d, s0, sh = d33
    assert floquet_resonances(d, s0, J) == [(6, pytest.approx(math.pi / 6))]
    dts = [0.25, 0.3, 0.4, 0.45, 0.5]
    scan = trotter_error_scan(d, s0, sh, J=J, h=H, T=10.0, dts=dts, max_spins=CEIL.ed_max_spins)
    x, e = scan.series("flippable_density")
    below, above = locate_threshold(x, e, 0.05)
    assert e[0] < 0.05 and above is not None and above <= math.pi / 6
    assert e[-1] / e[0] > 10


def test_threshold_moves_with_n_s_stripe_is_discriminating():
    """The stripe has only n_s = 2 spins: c0 resonance pi/2 = 1.571 [derived].
    At weak field (h = 0.1, first order) its local error stays controlled at dt = 0.5 — where the
    3-sublattice start (n_s = 6, resonance 0.524) has already broken down — and breaks only near
    its own resonance. At h = 0.3 the configurations admixed at higher order bring their n_s = 6
    gaps, and the stripe feels the pi/6 resonance too [measured]: the c0 rule is a weak-field rule."""
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "stripe")
    sh = Shells.build(d, 3)
    assert floquet_resonances(d, s0, J) == [(2, pytest.approx(math.pi / 2))]
    weak = trotter_error_scan(d, s0, sh, J=J, h=0.1, T=10.0, dts=[0.25, 0.5, 1.5], max_spins=CEIL.ed_max_spins)
    _, e = weak.series("defect_density")
    assert e[1] < 2e-3 and e[2] > 50 * e[1]
    d3 = TriangularDimers(3, 3)
    s3 = initial_spins(d3, "3-sublattice")
    e3 = trotter_error_scan(d3, s3, Shells.build(d3, 3), J=J, h=0.1, T=10.0, dts=[0.5],
                            max_spins=CEIL.ed_max_spins).series("defect_density")[1]
    assert e3[0] > 10 * e[1]
    strong = trotter_error_scan(d, s0, sh, J=J, h=0.3, T=10.0, dts=[0.45, 0.5], max_spins=CEIL.ed_max_spins)
    _, es = strong.series("defect_density")
    assert es[1] > 5 * es[0]


def test_shared_comparison_mode_agrees_with_every_step_mode(d33):
    d, s0, sh = d33
    a = trotter_error_scan(d, s0, sh, J=J, h=H, T=4.0, dts=[0.1, 0.25, 0.5], max_spins=CEIL.ed_max_spins,
                           cmp_every=1.0)
    b = trotter_error_scan(d, s0, sh, J=J, h=H, T=4.0, dts=[0.1, 0.25, 0.5], max_spins=CEIL.ed_max_spins)
    for pa, pb in zip(a.points, b.points):
        assert pa.infidelity == pytest.approx(pb.infidelity, rel=1e-6)
        assert pa.max_err["flippable_density"] <= pb.max_err["flippable_density"] + 1e-12
    with pytest.raises(ValueError):
        trotter_error_scan(d, s0, sh, J=J, h=H, T=4.0, dts=[0.3], max_spins=CEIL.ed_max_spins, cmp_every=1.0)


def test_late_window_bias_shrinks_as_dt_squared(d33):
    d, s0, sh = d33
    kw = dict(J=J, h=H, total_time=10.0, max_snapshots=40, late_fraction=0.5, max_spins=CEIL.ed_max_spins)
    big = {r.obs: abs(r.trotter - r.exact) for r in late_window_bias(d, s0, sh, dt=0.25, **kw)}
    small = {r.obs: abs(r.trotter - r.exact) for r in late_window_bias(d, s0, sh, dt=0.125, **kw)}
    for o in ("flippable_density", "defect_density"):
        assert 2.5 < big[o] / small[o] < 6.0, o


def test_ceilings_refuse_before_allocating():
    d = TriangularDimers(3, 7)              # N = 21 > ED ceiling
    s = np.ones((7, 3))
    with pytest.raises(MemoryCeilingError):
        trotter_error_scan(d, s, Shells.build(d, 1), J=J, h=H, T=1.0, dts=[0.5], max_spins=CEIL.ed_max_spins)
    with pytest.raises(MemoryCeilingError):
        late_window_bias(d, s, Shells.build(d, 1), J=J, h=H, dt=0.5, total_time=1.0, max_snapshots=2,
                         late_fraction=0.5, max_spins=CEIL.ed_max_spins)


def test_bias_table_conditioned_value_is_the_verdict_quantity(d33):
    """Review fix M2: the COND columns of the bias table must be exactly what
    src/mcmc_baseline.classify compares with the baseline (late window, conditioned curve,
    C1 from window-averaged moments)."""
    from src.mcmc_baseline import classify
    d, s0, sh = d33
    kw = dict(J=J, h=0.5, dt=0.25, total_time=12.0, max_snapshots=40, max_spins=CEIL.ed_max_spins)
    c = relaxation_curve(d, s0, sh, **kw)
    rows = {r.obs: r for r in late_window_bias(d, s0, sh, late_fraction=0.5, **kw)}
    assert rows["flippable_density"].cond_trotter == pytest.approx(
        classify(c, "flippable_density", 0.0, 0.0).late_cond, abs=1e-12)
    assert rows["flippable_density"].trotter == pytest.approx(
        classify(c, "flippable_density", 0.0, 0.0).late_raw, abs=1e-12)
    assert rows["C1"].cond_trotter == pytest.approx(classify(c, "C", 0.0, 0.0, shell=1).late_cond, abs=1e-12)
    late = c.times >= c.times[-1] / 2
    assert rows["p_out"].trotter == pytest.approx(c.p_out[late].mean(), abs=1e-12)


def test_public_builders_guard_the_ceiling():
    d = TriangularDimers(3, 7)              # N = 21
    with pytest.raises(MemoryCeilingError):
        ExactPropagator(d, J, H, max_spins=CEIL.ed_max_spins)
    with pytest.raises(MemoryCeilingError):
        observable_function(d, np.ones((7, 3)), Shells.build(d, 1), max_spins=CEIL.ed_max_spins)
