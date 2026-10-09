"""Noisy + Iceberg-encoded Q3 curves and the Stim size story (handoff/08 Part B; src/noisy_q3.py).

Independent references: the Iceberg arm at zero noise must equal the bare circuit exactly
(transparency); the circuit-order ideal must differ from the Q3 (trotter.py-order) ideal only at
O(dt^2); the readout channel against brute force; the sampled 2q fault distribution against the
Stim channel it mirrors; the first-order Stim rates must grow linearly with N.
"""

import math

import numpy as np
import pytest

from config import RunConfig
from src.backends import MemoryCeilingError
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates
from src.encoded_tfim import check_physical_ceiling  # noqa: F401  (guard used by run_iceberg)
from src.mcmc_baseline import Shells, initial_spins, relaxation_curve
from src.noisy_q3 import (
    _fault_2q, make_iceberg, readout_flip, run_bare, run_iceberg, run_observables, size_row,
)

J, H, DT = -1.0, 0.3, 0.25
CEIL = RunConfig().ceilings
PRIOR = NoiseRates(p2=6e-4, p1=6e-5, pm=6e-5, p_init=6e-5, zz_bias=0.05)


@pytest.fixture(scope="module")
def d34():
    d = TriangularDimers(3, 4)
    return d, initial_spins(d, "flippable"), Shells.build(d, 3)


def _bare(d, s0, n, noise=NoiseRates(), n_traj=1, nb=1, dt=DT, seed=0):
    return run_bare(d, s0, J=J, h=H, dt=dt, n_steps=n, noise=noise, n_traj=n_traj, n_batches=nb,
                    record_every=1, rng=np.random.default_rng(seed), max_spins=CEIL.ed_max_spins)


def test_iceberg_is_transparent_at_zero_noise(d34):
    """Encoded at zero noise == bare circuit, at every step boundary (and the t=0 snapshot is c0)."""
    d, s0, _ = d34
    ice = run_iceberg(d, s0, J=J, h=H, dt=DT, n_steps=6, noise=NoiseRates(), n_traj=1, n_batches=1,
                      record_every=1, rng=np.random.default_rng(0), max_spins=CEIL.statevector_max_spins)
    bare = _bare(d, s0, 6)
    assert np.allclose(ice.acceptance(), 1.0)
    assert np.abs(ice.mixture() - bare.mixture()).max() < 1e-12
    assert bare.mixture()[0][d.product_state_index(s0)] == pytest.approx(1.0)


def test_circuit_order_differs_from_trotter_order_only_at_second_order():
    d = TriangularDimers(3, 3)
    s0 = initial_spins(d, "3-sublattice")
    sh = Shells.build(d, 3)
    diffs = []
    for dt in (0.25, 0.125):
        n = int(round(4.0 / dt))
        ob = run_observables(d, s0, sh, _bare(d, s0, n, dt=dt), CEIL.ed_max_spins)
        c = relaxation_curve(d, s0, sh, J=J, h=H, dt=dt, total_time=4.0, max_snapshots=n, max_spins=CEIL.ed_max_spins)
        diffs.append(np.max(np.abs(ob.raw["flippable_density"][0] - c.raw["flippable_density"])))
    assert 3.0 < diffs[0] / diffs[1] < 5.0


def test_readout_flip_matches_brute_force():
    rng = np.random.default_rng(3)
    n, pm = 3, 0.1
    p = rng.random(1 << n)
    p /= p.sum()
    ref = np.zeros_like(p)
    for i in range(1 << n):
        for j in range(1 << n):
            k = bin(i ^ j).count("1")
            ref[j] += p[i] * pm ** k * (1 - pm) ** (n - k)
    assert np.allclose(readout_flip(p, range(n), n, pm), ref)
    assert np.allclose(readout_flip(p, [0], n, 0.0), p)


def test_two_qubit_fault_distribution_mirrors_the_stim_channel():
    """P(ZZ) = p2 (eta + (1-eta)/15), each other Pauli p2 (1-eta)/15 (encoded_codes.to_stim)."""
    rng = np.random.default_rng(7)
    noise = NoiseRates(p2=1.0, zz_bias=0.3)
    draws = [_fault_2q(rng, noise) for _ in range(60000)]
    zz = sum(d == ("Z", "Z") for d in draws) / len(draws)
    xi = sum(d == ("X", "I") for d in draws) / len(draws)
    assert zz == pytest.approx(0.3 + 0.7 / 15, abs=0.01)
    assert xi == pytest.approx(0.7 / 15, abs=0.005)
    assert _fault_2q(rng, NoiseRates(p2=0.0)) is None


def test_noisy_runs_are_sane(d34):
    """Noise lowers Iceberg survival monotonically; the bare noisy curve stays a probability mixture;
    Gauss post-selection acceptance (p_in) falls below 1."""
    d, s0, sh = d34
    ice = run_iceberg(d, s0, J=J, h=H, dt=DT, n_steps=4, noise=NoiseRates(p2=5e-3, p1=5e-4), n_traj=12,
                      n_batches=3, record_every=1, rng=np.random.default_rng(1), max_spins=CEIL.statevector_max_spins)
    a = ice.acceptance()
    assert np.all(np.diff(a) <= 1e-12) and a[-1] < 1.0
    ob = run_observables(d, s0, sh, _bare(d, s0, 8, noise=NoiseRates(p2=5e-3, p1=5e-4), n_traj=12, nb=3), CEIL.ed_max_spins)
    assert np.all(ob.p_in <= 1 + 1e-12) and ob.p_in[-1] < 1.0
    assert np.all(np.isfinite(ob.raw["flippable_density"][1]))


def test_stim_rates_grow_linearly_with_n():
    """First-order per-step rates per site are size-independent (3x4 vs 6x6) [derived accounting]."""
    a = size_row(3, 4, initial_spins(TriangularDimers(3, 4), "stripe"), J=J, h=H, dt=DT, noise=PRIOR)
    b = size_row(6, 6, initial_spins(TriangularDimers(6, 6), "3-sublattice"), J=J, h=H, dt=DT, noise=PRIOR)
    assert b.n_phys_iceberg == 40
    for f in ("bare_unprotected", "ice_detected", "ice_undetected"):
        assert getattr(b, f) / 36 == pytest.approx(getattr(a, f) / 12, rel=0.1), f
    assert b.ice_undetected < b.bare_unprotected


def test_ceilings_refuse_before_allocating():
    d = TriangularDimers(3, 7)              # N = 21: bare 2^N tables over the ED ceiling
    with pytest.raises(MemoryCeilingError):
        _bare(d, np.ones((7, 3)), 1)
    d = TriangularDimers(4, 6)              # k = 24 -> 28 physical > state-vector ceiling
    with pytest.raises(MemoryCeilingError):
        run_iceberg(d, d.stripe_spins(), J=J, h=H, dt=DT, n_steps=1, noise=NoiseRates(), n_traj=1, n_batches=1,
                    record_every=1, rng=np.random.default_rng(0), max_spins=CEIL.statevector_max_spins)
    assert make_iceberg(TriangularDimers(3, 4), initial_spins(TriangularDimers(3, 4), "stripe"), J, H, DT).n_phys == 16


def test_unsupported_noise_and_memory_are_refused(d34):
    """Review fixes: p_idle / overrot are not modelled, so they must raise rather than be dropped;
    the accumulator estimate is checked before allocating."""
    d, s0, _ = d34
    for bad in (NoiseRates(p2=1e-3, p_idle=1e-3), NoiseRates(p2=1e-3, overrot=1e-4)):
        with pytest.raises(NotImplementedError):
            _bare(d, s0, 1, noise=bad)
        with pytest.raises(NotImplementedError):
            run_iceberg(d, s0, J=J, h=H, dt=DT, n_steps=1, noise=bad, n_traj=1, n_batches=1, record_every=1,
                        rng=np.random.default_rng(0), max_spins=CEIL.statevector_max_spins)
    with pytest.raises(MemoryCeilingError):
        run_bare(d, s0, J=J, h=H, dt=DT, n_steps=100, noise=NoiseRates(), n_traj=1, n_batches=1000, record_every=1,
                 rng=np.random.default_rng(0), max_spins=CEIL.ed_max_spins, mem_gb=0.5)
