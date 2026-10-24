"""Regression tests for blind review A of 2026-10-24 on src/q3_rescore.py and the shard pooling,
written after the findings and before the fixes were relied on (research-flow: majors get tests).

 A1 the verdict must not call a winner between two EXACT arms that differ only in noise level
    (the mean |O - O_ref| has a noise floor ~ sqrt(2/pi) sigma; the msd verdict removes it);
 A2 the Gauss-conditioned modes use their own Kish ESS, below the raw one when per-trajectory
    in-sector weights vary;
 A3 a jackknife over fewer than `min_batches` batches is no estimate; so is a point where one
    batch carries all the weight;
 A6 a window that starts before the bare or ideal grid raises instead of extrapolating flat.

Synthetic arrays only; nothing here is an H2 result.
"""
import numpy as np
import pytest

from src.noisy_q3 import NoisyRun
from src.q3_rescore import rescore_cell

OBS = "flippable_density"


def _arm(t, v, *, se=0.0, acceptance=None, p_in=1.0):
    t = np.asarray(t, dtype=float)
    v = np.asarray(v, dtype=float) * np.ones(len(t))
    a = {"times": t, "raw": {OBS: (v, np.full(len(t), se))}, "cond": {OBS: (v, np.full(len(t), se))},
         "p_in": np.full(len(t), p_in)}
    if acceptance is not None:
        a["acceptance"] = np.asarray(acceptance, dtype=float)
    return a


def _with_batches(arm, rows, weights):
    rows = np.asarray(rows, dtype=float)
    w = np.asarray(weights, dtype=float)
    arm["per_batch"] = {"raw": {OBS: list(rows)}, "cond": {OBS: list(rows)},
                        "wsum": list(w), "p_in": list(np.ones_like(w))}
    tot = (rows * w).sum(0) / w.sum(0)
    arm["raw"][OBS] = (tot, arm["raw"][OBS][1])
    arm["cond"][OBS] = (tot, arm["cond"][OBS][1])
    return arm


def test_a1_two_exact_arms_with_different_noise_are_not_ranked():
    """Both arms are unbiased around the reference; the encoded one is 5x noisier per batch. The
    old |.| ranking calls the quiet arm better; the msd verdict must say "unresolved"."""
    rng = np.random.default_rng(2026)
    t = np.linspace(0, 3, 13)
    ref = 0.3 + 0.0 * t
    calls = abs_ranked = 0
    for _ in range(40):
        bare = _with_batches(_arm(t, ref), ref + 0.002 * rng.standard_normal((20, 13)),
                             np.full((20, 13), 6.0))
        ice = _with_batches(_arm(t, ref, acceptance=np.ones(13)),
                            ref + 0.010 * rng.standard_normal((20, 13)), np.full((20, 13), 1.0))
        s = rescore_cell(_arm(t, ref), bare, ice, ess_floor=10, n_traj_bare=120, n_traj_ice=20,
                         min_batches=10)
        p = next(p for p in s.pairs if p.ref == "raw" and p.b == "Iceberg")
        calls += p.verdict != "unresolved"
        abs_ranked += s.residual[("Iceberg", "raw")] > s.residual[("bare + Gauss", "raw")]
    assert abs_ranked >= 36, "the |.| residual should show the noise-floor bias this test is about"
    # one-sigma convention: about a third of null pairs may still cross; a biased metric calls
    # the quiet arm the winner essentially always
    assert calls < 24, calls


def test_a2_conditioned_mode_uses_its_own_ess():
    run = NoisyRun("iceberg", np.array([0, 1]), 1.0, np.zeros((1, 2, 4)),
                   wsum=np.array([[20.0, 20.0]]), n_traj=20, w2sum=np.array([[20.0, 20.0]]),
                   wpsum=np.array([[10.0, 10.0]]), wp2sum=np.array([[10.0, 10.0]]))
    assert np.allclose(run.ess(), 20.0)
    assert np.allclose(run.ess_cond(), 10.0)
    t = [0.0, 1.0]
    ice = _arm(t, 0.3, acceptance=[1.0, 1.0])
    ice["ess"], ice["ess_cond"] = np.array([20.0, 20.0]), np.array([20.0, 8.0])
    s = rescore_cell(_arm(t, 0.3), _arm(t, 0.3), ice, ess_floor=10, n_traj_bare=100,
                     n_traj_ice=20)
    assert s.estimate["Iceberg"] and not s.estimate["Iceberg + Gauss"]


def test_a2_conditioned_lower_bound_without_kish():
    t = [0.0, 1.0]
    bare = _arm(t, 0.3, p_in=0.05)                 # 100 trajectories x p_in 0.05 = 5 < 10
    s = rescore_cell(_arm(t, 0.3), bare, None, ess_floor=10, n_traj_bare=100, n_traj_ice=0)
    assert s.estimate["bare raw"] and not s.estimate["bare + Gauss"]


def test_a3_too_few_batches_is_no_estimate():
    t = np.linspace(0, 1, 3)
    ice = _with_batches(_arm(t, 0.3, acceptance=np.ones(3)), 0.3 + np.zeros((5, 3)),
                        np.full((5, 3), 10.0))
    s = rescore_cell(_arm(t, 0.3), _arm(t, 0.3), ice, ess_floor=10, n_traj_bare=100,
                     n_traj_ice=50, min_batches=10)
    assert not s.estimate["Iceberg"] and "min_batches" in s.reason["Iceberg"]


def test_a3_one_batch_holding_all_the_weight_is_no_estimate():
    t = np.linspace(0, 1, 3)
    w = np.full((12, 3), 2.0)
    w[1:, -1] = 0.0                                 # only batch 0 survives to the last point
    ice = _with_batches(_arm(t, 0.3, acceptance=np.ones(3)), 0.3 + np.zeros((12, 3)), w)
    ice["ess"] = np.full(3, 50.0)
    s = rescore_cell(_arm(t, 0.3), _arm(t, 0.3), ice, ess_floor=10, n_traj_bare=100,
                     n_traj_ice=50, min_batches=10)
    assert not s.estimate["Iceberg"] and "one batch" in s.reason["Iceberg"]


def test_a6_window_before_the_bare_grid_raises():
    with pytest.raises(ValueError):
        rescore_cell(_arm([0.0, 1.0, 2.0], 0.3), _arm([0.5, 1.0, 2.0], 0.3),
                     _arm([0.0, 1.0], 0.3, acceptance=[1.0, 1.0]), ess_floor=1,
                     n_traj_bare=10, n_traj_ice=10)


def test_a2_shards_pool_the_conditioned_ess_exactly():
    from src.noisy_q3_sweep import run_noisy_sweep
    from src.q3_shards import merge_arms
    out = run_noisy_sweep([(3, 4, "flippable")], [0.5], [1.0], n_traj_bare=8, n_traj_ice=8,
                          n_batches=4, seed=7, steps=2, ice_steps=2, record_every=1, mem_gb=4.0)
    arm = out[next(iter(out))]["ice"]
    pb = arm["per_batch"]
    parts = [{"times": arm["times"],
              "per_batch": {k: ({o: np.asarray(v)[sl] for o, v in pb[k].items()}
                                if isinstance(pb[k], dict) else np.asarray(pb[k])[sl])
                            for k in pb}} for sl in (slice(0, 1), slice(1, 4))]
    merged = merge_arms(parts, n_traj=[2, 6])
    assert np.allclose(merged["ess_cond"], arm["ess_cond"], rtol=1e-12)
    assert np.allclose(merged["ess"], arm["ess"], rtol=1e-12)


def test_b2_rotation_gadget_cx_sit_in_the_preparation_only():
    """Review B: of the 196 two-qubit locations of the one-step N = 12 program, the 72 rot-cx are
    the state preparation (once); each further step adds 60 ZZPhase + 32 syndrome CX."""
    import collections

    import src.encoded_codes as ec
    from config import CONFIG
    from src.dimers import TriangularDimers
    from src.encoded_codes import NoiseRates
    from src.mcmc_baseline import initial_spins
    from src.noisy_q3 import make_iceberg

    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable", CONFIG.ceilings.ed_max_spins)
    prog = make_iceberg(d, s0, CONFIG.q3.J, CONFIG.q3.noisy_h, CONFIG.q3.dt)
    noise = NoiseRates(p2=1e-3, zz_bias=0.3)

    def counts(n):
        c = collections.Counter()
        for ins in ec.to_stim(prog.schedule(n, "Z"), noise).flattened():
            if ins.tag and ins.tag.split(":")[0].endswith(("-cx", "-zz")):
                c[ins.tag.split(":")[0]] += len(ins.targets_copy()) // 2
        return c

    one, two = counts(1), counts(2)
    assert one == {"rot-cx": 72, "rot-zz": 60, "syn-cx": 64}
    step = {k: two[k] - one[k] for k in two}
    assert step == {"rot-cx": 0, "rot-zz": 60, "syn-cx": 32}, step


def test_b4_merging_the_same_shard_twice_is_refused():
    from src.q3_shards import merge_cells
    c = {"cell": {"N": 20, "h": 0.5, "lam": 3.0, "ice_steps": 12}, "noise": {"p2": 1e-3},
         "settings": {"traj_bare": 6, "traj_ice": 23, "batches": 1, "seed_extra": [3]},
         "bare": None, "ice": None, "ideal": None}
    with pytest.raises(ValueError):
        merge_cells([c, c])
