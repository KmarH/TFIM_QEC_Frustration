"""Regression tests for src/noisy_q3_sweep.score_cell, the scorer every number in
docs/q3_scaling.md §4 flows through.

HONEST LABEL: unlike the four frozen spec files of this study, these tests were written AFTER the
function (they are regression tests, not a blind spec). They exist because `score_cell` carries the
§9.2 metric for the whole generalization and the frozen specs predate it: the frozen
tests/test_noisy_q3_sweep.py pins only the RAW curves the sweep returns, not how they are scored.

The arms here are synthetic arrays with residuals known by construction, so each assertion has a
closed-form expected value. No physics is claimed; nothing is an H2 result.
"""

import numpy as np

from src.noisy_q3_sweep import OBSERVABLE, score_cell

OBS = OBSERVABLE               # "flippable_density"
DT = 0.25


def _arm(times, raw, cond, se=0.001, p_in=1.0, acceptance=1.0):
    """One arm in the dict shape run_noisy_sweep returns (src/noisy_q3_sweep._arm)."""
    times = np.asarray(times, dtype=float)
    raw = np.full_like(times, raw) if np.isscalar(raw) else np.asarray(raw, dtype=float)
    cond = np.full_like(times, cond) if np.isscalar(cond) else np.asarray(cond, dtype=float)
    ses = np.full_like(times, se)
    return {"times": times,
            OBS: raw,
            f"{OBS}_se": ses,
            "acceptance": np.full_like(times, acceptance),
            "p_in": np.full_like(times, p_in),
            "raw": {OBS: (raw, ses)},
            "cond": {OBS: (cond, ses)}}


def _by(scores):
    return {(s.mode, s.window): s for s in scores}


def test_residuals_equal_the_constructed_offsets():
    """A constant offset from the ideal curve must come back as exactly that residual, and the
    Gauss mode must be scored against the ideal CONDITIONED curve with the raw score alongside."""
    t = np.arange(0, 9) * DT
    ideal = _arm(t, raw=0.30, cond=0.28)
    bare = _arm(t, raw=0.31, cond=0.282, se=0.0005, p_in=0.5)
    scores = _by(score_cell(ideal, bare, None, early_t=float(t[-1])))

    raw_early = scores[("bare raw", "early")]
    assert np.isclose(raw_early.residual, 0.01), raw_early.residual
    assert not np.isfinite(raw_early.residual_vs_raw), "a raw mode has no conditioned counterpart"
    assert np.isclose(raw_early.cost, 1.0), "the unencoded raw arm pays no post-selection"

    gauss = scores[("bare + Gauss", "early")]
    assert np.isclose(gauss.residual, 0.002), "Gauss is scored against the ideal conditioned curve"
    assert np.isclose(gauss.residual_vs_raw, 0.018), "and against the raw curve in brackets"
    assert np.isclose(gauss.cost, 2.0), "shot cost is 1 / mean(p_in)"


def test_resolved_requires_the_residual_to_exceed_its_own_se():
    """The §9.2 reading rule: a residual at or below the mode's SE is NOT resolved. An SE of
    exactly 0 (a single batch, no spread to estimate from) is also not resolved."""
    t = np.arange(0, 5) * DT
    ideal = _arm(t, raw=0.30, cond=0.30)
    big_se = _by(score_cell(ideal, _arm(t, raw=0.301, cond=0.30, se=0.01), None))
    assert big_se[("bare raw", "early")].resolved is False, "0.001 residual vs 0.01 SE is the floor"
    small_se = _by(score_cell(ideal, _arm(t, raw=0.301, cond=0.30, se=0.0001), None))
    assert small_se[("bare raw", "early")].resolved is True
    zero_se = _by(score_cell(ideal, _arm(t, raw=0.301, cond=0.30, se=0.0), None))
    assert zero_se[("bare raw", "early")].resolved is False, "SE = 0 must not read as resolved"


def test_encoded_arm_is_scored_on_its_own_shorter_grid():
    """The encoded arm runs a survival-matched (shorter) window, so it must be scored against the
    ideal curve INTERPOLATED onto its own times, and its cost must include detector survival."""
    t_long = np.arange(0, 17) * DT
    ideal = _arm(t_long, raw=np.linspace(0.30, 0.22, 17), cond=np.linspace(0.28, 0.20, 17))
    t_ice = np.arange(0, 5) * DT                      # a quarter of the window
    ice = _arm(t_ice, raw=np.linspace(0.30, 0.28, 5) + 0.005,
               cond=np.linspace(0.28, 0.26, 5), se=0.0002, p_in=0.8, acceptance=0.25)
    bare = _arm(t_long, raw=0.30, cond=0.28)
    scores = _by(score_cell(ideal, bare, ice))

    ice_raw = scores[("Iceberg", "early")]
    assert ice_raw.n_points == len(t_ice), "scored on its own grid, not the bare one"
    expected = float(np.mean(np.abs((np.linspace(0.30, 0.28, 5) + 0.005)
                                    - np.interp(t_ice, t_long, ideal["raw"][OBS][0]))))
    assert np.isclose(ice_raw.residual, expected), (ice_raw.residual, expected)
    assert np.isclose(ice_raw.cost, 4.0), "1 / 0.25 detector survival"
    ice_gauss = scores[("Iceberg + Gauss", "early")]
    assert np.isclose(ice_gauss.cost, 5.0), "Iceberg + Gauss pays survival TIMES Gauss acceptance"


def test_early_window_defaults_to_the_encoded_reach_and_late_is_the_second_half():
    """early_t defaults to the encoded arm's last time (matched survival); the late window is the
    second half of the bare times. Both windows must select the right number of points."""
    t_long = np.arange(0, 21) * DT                    # 0 .. 5.0
    ideal = _arm(t_long, raw=0.30, cond=0.28)
    bare = _arm(t_long, raw=0.31, cond=0.282)
    ice = _arm(np.arange(0, 9) * DT, raw=0.30, cond=0.28)   # 0 .. 2.0
    scores = _by(score_cell(ideal, bare, ice))
    assert scores[("bare raw", "early")].n_points == 9, "early = bare points within t <= 2.0"
    assert scores[("bare raw", "late")].n_points == 11, "late = bare points with t >= 2.5"
    # an explicit early_t overrides the encoded reach
    wide = _by(score_cell(ideal, bare, ice, early_t=float(t_long[-1])))
    assert wide[("bare raw", "early")].n_points == len(t_long)


def test_nonfinite_points_are_skipped_not_propagated():
    """A post-selected arm can lose all weight at late times (NaN). Those points must drop out of
    the mean instead of poisoning it."""
    t = np.arange(0, 9) * DT
    ideal = _arm(t, raw=0.30, cond=0.28)
    raw = np.full(9, 0.31)
    raw[-3:] = np.nan
    bare = _arm(t, raw=raw, cond=0.282)
    s = _by(score_cell(ideal, bare, None, early_t=float(t[-1])))[("bare raw", "early")]
    assert s.n_points == 6, "the three NaN points are excluded"
    assert np.isclose(s.residual, 0.01), "and the surviving residual is unchanged"
