"""FROZEN test spec (test-first, written 2026-10-24 BEFORE src/q3_shards.py and the provenance /
budget-guard code existed) for review/18 F13 and the sharded, pre-declared re-run (DECIDED-10).

SPEC
 S1 `src.noisy_q3_sweep.run_noisy_sweep(..., seed_extra=())` is bitwise identical to omitting the
    argument; a non-empty `seed_extra` changes the stream.
 S2 Each arm's `per_batch` carries "raw", "cond" (obs -> B rows), "wsum" and "p_in" (B rows) - also
    when n_batches == 1 - and arms carry "n_eff" (sum of weights) and "ess" (Kish (sum w)^2 /
    sum w^2, from a w^2 accumulator) per recorded step.
 S3 `src.q3_shards.merge_arms(arms, n_traj)` pools any split of one run's batches back into exactly
    the single run's pooled curves for the LINEAR observables (flippable_density, defect_density,
    memory; raw and cond), its acceptance and n_eff; C1 (a connected correlator, non-linear) is
    NaN in the merge and listed in `merged["unmergeable"]`.
 S4 `src.q3_shards.merge_cells(cells)` refuses cells that differ in (N, h, lam), window
    (ice_steps) or noise model, and sums the trajectory counts.
 S5 `scripts/run_q3_sweep.resolve_settings(n_logical, h, lam, cli, allow_reduced)` returns
    (settings, sources): every setting comes from config unless given on the CLI; sources[k] is
    "config" or "cli". A CLI trajectory/batch count BELOW config, or an ice_steps different from
    config's pre-declared window, raises ValueError unless `allow_reduced` gives a reason.
 S6 `scripts/run_q3_sweep.build_provenance(argv, sources, allow_reduced)` records argv, the git
    commit and dirty flag, the setting sources and the allow_reduced reason.

Tiny synthetic runs only (3x4 bare / 16-qubit Iceberg, 2 steps); nothing here is an H2 result.
"""
import os
import sys

import numpy as np
import pytest
from src.q3_shards import merge_arms, merge_cells

from src.noisy_q3_sweep import OBSERVABLE, run_noisy_sweep

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))
import run_q3_sweep as rqs

LINEAR = ("flippable_density", "defect_density", "memory")
TINY = {"n_traj_bare": 8, "n_traj_ice": 8, "n_batches": 4, "seed": 1234, "steps": 2,
        "ice_steps": 2, "record_every": 1, "mem_gb": 4.0}


@pytest.fixture(scope="module")
def tiny():
    return run_noisy_sweep([(3, 4, "flippable")], [0.5], [1.0], **TINY)


def _cell(out):
    return out[next(iter(out))]


def test_s1_empty_seed_extra_is_bitwise_identical(tiny):
    again = run_noisy_sweep([(3, 4, "flippable")], [0.5], [1.0], seed_extra=(), **TINY)
    a, b = _cell(tiny), _cell(again)
    for arm in ("bare", "ice"):
        assert np.array_equal(a[arm][OBSERVABLE], b[arm][OBSERVABLE])
    other = run_noisy_sweep([(3, 4, "flippable")], [0.5], [1.0], seed_extra=(7,), **TINY)
    assert not np.array_equal(_cell(other)["ice"]["acceptance"], a["ice"]["acceptance"]) or \
        not np.array_equal(_cell(other)["bare"][OBSERVABLE], a["bare"][OBSERVABLE])


def test_s2_per_batch_carries_weights_and_kish_ess(tiny):
    for arm in ("bare", "ice"):
        a = _cell(tiny)[arm]
        pb = a["per_batch"]
        T = len(a["times"])
        for k in ("raw", "cond"):
            assert np.asarray(pb[k][OBSERVABLE]).shape == (4, T)
        assert np.asarray(pb["wsum"]).shape == (4, T) and np.asarray(pb["p_in"]).shape == (4, T)
        assert np.allclose(np.asarray(pb["wsum"]).sum(0), a["n_eff"])
        ess = np.asarray(a["ess"])
        assert np.all(ess <= TINY["n_traj_ice"] + 1e-9), "Kish ESS <= number of trajectories"
        assert np.all(ess >= np.asarray(a["n_eff"]) - 1e-9), "Kish ESS >= sum w for w in [0, 1]"
    one = run_noisy_sweep([(3, 4, "flippable")], [0.5], [1.0], **{**TINY, "n_batches": 1})
    assert np.asarray(_cell(one)["ice"]["per_batch"]["wsum"]).shape[0] == 1


@pytest.mark.parametrize("split", [(2, 2), (1, 3), (1, 1, 1, 1)])
def test_s3_merging_a_split_reproduces_the_pooled_run(tiny, split):
    for arm_name in ("bare", "ice"):
        arm = _cell(tiny)[arm_name]
        pb = arm["per_batch"]
        parts, start = [], 0
        for n in split:
            sl = slice(start, start + n)
            part = {"times": arm["times"],
                    "per_batch": {"raw": {o: np.asarray(v)[sl] for o, v in pb["raw"].items()},
                                  "cond": {o: np.asarray(v)[sl] for o, v in pb["cond"].items()},
                                  "wsum": np.asarray(pb["wsum"])[sl],
                                  "p_in": np.asarray(pb["p_in"])[sl]}}
            if "w2sum" in pb:
                part["per_batch"]["w2sum"] = np.asarray(pb["w2sum"])[sl]
            parts.append(part)
            start += n
        merged = merge_arms(parts, n_traj=[2 * n for n in split])
        for o in LINEAR:
            for k in ("raw", "cond"):
                assert np.allclose(merged[k][o][0], arm[k][o][0], rtol=1e-12, atol=1e-14), (arm_name, k, o)
        assert np.allclose(merged["acceptance"], arm["acceptance"], rtol=1e-12)
        assert np.allclose(merged["n_eff"], arm["n_eff"], rtol=1e-12)
        assert "C1" in merged["unmergeable"] and np.all(np.isnan(merged["raw"]["C1"][0]))


def test_s4_merge_cells_refuses_mismatched_cells():
    base = {"cell": {"N": 20, "h": 0.5, "lam": 3.0, "ice_steps": 12}, "noise": {"p2": 1e-3},
            "settings": {"traj_bare": 15, "traj_ice": 25, "batches": 1},
            "bare": None, "ice": None, "ideal": None}
    other = {**base, "cell": {**base["cell"], "ice_steps": 13}}
    with pytest.raises(ValueError):
        merge_cells([base, other])
    noisy = {**base, "noise": {"p2": 2e-3}}
    with pytest.raises(ValueError):
        merge_cells([base, noisy])


def test_s5_settings_come_from_config_and_reductions_need_a_reason():
    s, src = rqs.resolve_settings(20, 0.5, 3.0, cli={}, allow_reduced=None)
    assert all(v == "config" for v in src.values())
    with pytest.raises(ValueError):
        rqs.resolve_settings(20, 0.5, 3.0, cli={"traj_ice": 24}, allow_reduced=None)
    s2, src2 = rqs.resolve_settings(20, 0.5, 3.0, cli={"traj_ice": 24},
                                    allow_reduced="test: deliberately reduced")
    assert s2["traj_ice"] == 24 and src2["traj_ice"] == "cli"
    with pytest.raises(ValueError):
        rqs.resolve_settings(20, 0.5, 3.0, cli={"ice_steps": s["ice_steps"] + 1},
                             allow_reduced=None)


def test_s6_provenance_records_how_the_run_was_made():
    _, src = rqs.resolve_settings(20, 0.5, 3.0, cli={}, allow_reduced=None)
    p = rqs.build_provenance(["run_q3_sweep.py", "--cell", "20:0.5:3"], src, None)
    for k in ("argv", "git_commit", "git_dirty", "setting_sources", "allow_reduced"):
        assert k in p, k
    assert p["argv"][1:] == ["--cell", "20:0.5:3"]
