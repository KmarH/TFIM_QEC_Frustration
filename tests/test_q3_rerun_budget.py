"""FROZEN test spec (test-first, written 2026-10-24 BEFORE config.q3_scaling.rerun existed) for the
pre-declared re-run budget of DECIDED-10 (step 4) and the pre-declared windows. It makes the
pre-registration tamper-evident: the counts in config must be what the stated rule gives, and the
rule uses only design-time quantities (Stim survival), never a measured outcome.

SPEC
 B1 `CONFIG.q3_scaling.ess_floor` is a positive number and `CONFIG.q3_scaling.cell_windows` maps
    every sweep cell (N, h, lam) to the encoded window (ice_steps) it was run with.
 B2 For every cell in `CONFIG.q3_scaling.rerun`, with K = rerun_shards (>= min_batches >= 10):
      batch_ice = max(ceil(ess_margin * ess_floor / (K * s_pred)), ceil(per_size traj_ice / K)),
      traj_ice = K * batch_ice,  batch_bare = ceil(per_size traj_bare / K),  traj_bare = K *
    batch_bare, with s_pred = survival_curve(stim_rate_table(N, lam, PRIOR, scope="2q"),
    ice_steps) under the canonical (every-2q-gate) scope.
    (Revised 2026-10-24 from the research/08 sweep BEFORE this file was frozen: one batch per
    shard, at least 10 batches - Schmeiser 1982, S10 - and a margin >= 1.5 so the realised ESS,
    about Poisson around its mean, clears the floor with high probability.)
 B3 Every re-run cell keeps its pre-declared window: rerun[cell]["ice_steps"] == cell_windows[cell].

Stim only, no state vector; nothing here is an H2 result.
"""
import math

import numpy as np
import pytest

from config import CONFIG
from src.noisy_q3_sweep import prior_noise
from src.q3_scaling import stim_rate_table, survival_curve

QS = CONFIG.q3_scaling


def test_b1_floor_and_windows_are_declared():
    assert QS.ess_floor > 0
    assert len(QS.cell_windows) == 11
    for (n, _h, _lam), steps in QS.cell_windows.items():
        assert n in (12, 18, 20) and steps > 0


@pytest.mark.parametrize("cell", sorted(CONFIG.q3_scaling.rerun))
def test_b2_counts_follow_the_rule(cell):
    n, _h, lam = cell
    r = QS.rerun[cell]
    s_pred = float(survival_curve(stim_rate_table(n, lam, prior_noise(), scope="2q"),
                                  np.array([r["ice_steps"]]))[0])
    K = QS.rerun_shards
    assert K >= QS.min_batches >= 10
    assert QS.ess_margin >= 1.5
    want = max(math.ceil(QS.ess_margin * QS.ess_floor / (K * s_pred)),
               math.ceil(QS.per_size[n]["traj_ice"] / K))
    assert r["batch_ice"] == want, (cell, r["batch_ice"], want, s_pred)
    assert r["traj_ice"] == K * r["batch_ice"]
    assert r["batch_bare"] == math.ceil(QS.per_size[n]["traj_bare"] / K)
    assert r["traj_bare"] == K * r["batch_bare"]


@pytest.mark.parametrize("cell", sorted(CONFIG.q3_scaling.rerun))
def test_b3_windows_stay_as_declared(cell):
    assert QS.rerun[cell]["ice_steps"] == QS.cell_windows[cell]
