"""FROZEN test spec (test-first, written 2026-10-24 BEFORE src/q3_rescore.py existed) for the v2
scorer of the Q3 sweep: DECIDED-8 (common-estimand 4 x 2 table) and DECIDED-10 (pre-declared
estimator rules). Do not edit to fit an implementation; a failing test means the code is wrong.

SPEC
 R1 `rescore_cell(ideal, bare, ice, *, ess_floor, n_traj_bare, n_traj_ice, verdict_k=1.0,
    observable="flippable_density") -> CellScore`.
 R2 Every one of the 4 modes ("bare raw", "bare + Gauss", "Iceberg", "Iceberg + Gauss") is scored
    against BOTH references ("raw", "cond"): `residual[(mode, ref)]`, `se[(mode, ref)]` - 8 cells
    (review/18 F1).
 R3 One common window for every mode: the encoded arm's recorded times (the bare arm and the ideal
    curves are linearly interpolated onto them); `n_points[mode]` is the same for all modes.
    An encoded window that ends after the bare arm's last time raises ValueError (F2, F8).
 R4 ESS floor: a mode has an estimate only if its effective sample size is >= ess_floor at EVERY
    window point and its value is finite there. Otherwise `estimate[mode]` is False, its
    residuals are NaN, `reason[mode]` says why, and the window is NOT shortened (F9, step 3).
    Iceberg ESS: `ice["ess"]` if present, else `ice["n_eff"]`, else acceptance * n_traj_ice (a
    lower bound on Kish ESS for weights in [0, 1]). Bare ESS: n_traj_bare. Gauss post-selection
    is exact in the simulation and does not reduce ESS.
 R5 SE: with `per_batch` present, the delete-one-batch jackknife of the window-averaged residual
    (`se_method[mode] == "jackknife"`); otherwise the legacy mean per-point SE, flagged
    `se_method[mode] == "legacy"` (step 2; F5's meaning, F10).
 R6 cost[mode] = mean over the window of 1/acceptance; cost_final[mode] = 1/acceptance at the
    last point (F4). Acceptance: 1 (bare raw), p_in (bare + Gauss), survival (Iceberg),
    survival * p_in (Iceberg + Gauss).
 R7 `pairs`: for each reference, the two headline pairs ("bare + Gauss", "Iceberg") and
    ("bare + Gauss", "Iceberg + Gauss"), each with gap = msd_b - msd_a, sigma =
    sqrt(msd_se_a^2 + msd_se_b^2) and verdict "<winner> better: rms <w:.4f> vs <l:.4f>" when
    |gap| > verdict_k * sigma, "unresolved" otherwise, and "no estimate" when either mode has
    none (step 1). msd = mean_t[(O - O_ref)^2 - Var O], the bias-corrected mean square; legacy
    cells use Var O = se_t^2 and SE(msd) = sqrt(sum_t 4 e_t^2 se_t^2 + 2 se_t^4) / T.

 AMENDED 2026-10-24, before any commit, re-score or re-run: R7 originally ranked on the mean
 |O - O_ref|. Blind review A (finding 1) showed that metric carries a noise floor ~ sqrt(2/pi)
 sigma_t that grows as the effective sample shrinks, so it calls false winners against the noisier
 arm when both are exact. The verdict moved to msd; the |.| residual (R2, R5) is still reported.
 Regression tests for that review: tests/test_q3_rescore_review.py.

Synthetic arrays with closed-form answers only; nothing here is an H2 result.
"""
import numpy as np
import pytest
from src.q3_rescore import MODES, REFS, rescore_cell

OBS = "flippable_density"


def _curve(t, value, se=0.001):
    v = np.full(len(t), float(value)) if np.isscalar(value) else np.asarray(value, dtype=float)
    return (v, np.full(len(t), float(se)))


def _arm(t, raw, cond, *, se=0.001, p_in=1.0, acceptance=None):
    t = np.asarray(t, dtype=float)
    a = {"times": t, "raw": {OBS: _curve(t, raw, se)}, "cond": {OBS: _curve(t, cond, se)},
         "p_in": np.full(len(t), float(p_in)) if np.isscalar(p_in) else np.asarray(p_in, float)}
    if acceptance is not None:
        a["acceptance"] = np.asarray(acceptance, dtype=float)
    return a


T = np.arange(0, 7) * 0.5                         # 0 .. 3.0


def _healthy(se=0.001):
    ideal = _arm(T, 0.30, 0.40)
    bare = _arm(T, 0.31, 0.41, se=se, p_in=0.5)
    ice = _arm(T, 0.305, 0.402, se=se, p_in=0.8, acceptance=np.ones(len(T)))
    return ideal, bare, ice


def _score(ideal, bare, ice, **kw):
    kw.setdefault("ess_floor", 10)
    kw.setdefault("n_traj_bare", 400)
    kw.setdefault("n_traj_ice", 300)
    return rescore_cell(ideal, bare, ice, **kw)


def test_r2_all_eight_cells_are_filled_with_the_constructed_offsets():
    s = _score(*_healthy())
    expected = {("bare raw", "raw"): 0.01, ("bare raw", "cond"): 0.09,
                ("bare + Gauss", "raw"): 0.11, ("bare + Gauss", "cond"): 0.01,
                ("Iceberg", "raw"): 0.005, ("Iceberg", "cond"): 0.095,
                ("Iceberg + Gauss", "raw"): 0.102, ("Iceberg + Gauss", "cond"): 0.002}
    assert set(MODES) == {m for m, _ in expected} and set(REFS) == {"raw", "cond"}
    for key, val in expected.items():
        assert np.isclose(s.residual[key], val, atol=1e-12), (key, s.residual[key])
        assert np.isfinite(s.se[key]), key


def test_r3_common_window_on_the_encoded_grid_with_bare_interpolated():
    t_bare = np.arange(0, 13) * 0.5                       # 0 .. 6.0
    t_ice = np.append(np.arange(0, 10) * 0.5, 4.75)       # 0 .. 4.5, then 4.75 (off the bare grid)
    ideal = _arm(t_bare, 0.30, 0.40)
    bare_raw = 0.30 + 0.01 * t_bare                        # linear: interpolation is exact
    bare = _arm(t_bare, bare_raw, 0.40, p_in=0.5)
    ice = _arm(t_ice, 0.30, 0.40, acceptance=np.ones(len(t_ice)))
    s = _score(ideal, bare, ice)
    assert np.allclose(s.window, t_ice)
    assert len({s.n_points[m] for m in MODES}) == 1 and s.n_points["bare raw"] == len(t_ice)
    assert np.isclose(s.residual[("bare raw", "raw")], np.mean(0.01 * t_ice), atol=1e-12)


def test_r3_encoded_window_beyond_the_bare_arm_raises():
    t_bare = np.arange(0, 3) * 0.5
    t_ice = np.arange(0, 6) * 0.5
    with pytest.raises(ValueError):
        _score(_arm(t_ice, 0.3, 0.4), _arm(t_bare, 0.3, 0.4),
               _arm(t_ice, 0.3, 0.4, acceptance=np.ones(len(t_ice))))


def test_r4_a_point_below_the_floor_removes_the_estimate_without_shortening_the_window():
    t = np.array([0.0, 0.5, 1.0])
    ideal = _arm(t, 0.30, 0.40)
    bare = _arm(t, 0.30, 0.40)
    ice = _arm(t, 0.30, 0.40, acceptance=[1.0, 0.5, 0.01])         # ESS 100, 50, 1
    s = _score(ideal, bare, ice, n_traj_ice=100)
    for m in ("Iceberg", "Iceberg + Gauss"):
        assert not s.estimate[m]
        assert "ESS" in s.reason[m]
        assert all(np.isnan(s.residual[(m, r)]) for r in REFS)
        assert s.n_points[m] == 3, "the window must not shrink to where the arm survived"
    assert s.estimate["bare raw"] and s.estimate["bare + Gauss"]


def test_r4_the_eleventh_cell_reports_no_estimate():
    """The real (20, 0.5, 3) encoded arm: 24 trajectories, survival 0.749 -> 0.125 -> 0.0416, i.e.
    ONE surviving trajectory at the last point. Under any floor > 1 it is not a measurement."""
    t = np.array([0.0, 1.5, 3.0])
    ideal = _arm(t, 0.40, 0.40)
    bare = _arm(t, 0.21, 0.27)
    ice = _arm(t, [0.4, 0.243345, 0.250753], [0.4, 0.269912, 0.280788], se=3e-17,
               acceptance=[0.7490112464026347, 0.12483520773373918, 0.041611735911235244])
    s = _score(ideal, bare, ice, n_traj_bare=60, n_traj_ice=24)
    assert not s.estimate["Iceberg"] and not s.estimate["Iceberg + Gauss"]
    for p in s.pairs:
        if "Iceberg" in (p.a, p.b) or "Iceberg + Gauss" in (p.a, p.b):
            assert p.verdict == "no estimate", p


def test_r4_a_nan_value_inside_the_window_removes_the_estimate():
    t = np.array([0.0, 0.5, 1.0])
    ice = _arm(t, [0.30, np.nan, 0.30], 0.40, acceptance=[1.0, 1.0, 1.0])
    s = _score(_arm(t, 0.30, 0.40), _arm(t, 0.30, 0.40), ice)
    assert not s.estimate["Iceberg"]


def test_r4_ess_prefers_explicit_fields_over_acceptance():
    t = np.array([0.0, 0.5])
    ice = _arm(t, 0.30, 0.40, acceptance=[1.0, 1.0])
    ice["ess"] = np.array([50.0, 5.0])                    # Kish ESS below the floor at t = 0.5
    s = _score(_arm(t, 0.30, 0.40), _arm(t, 0.30, 0.40), ice)
    assert not s.estimate["Iceberg"]
    assert np.isclose(s.ess_min["Iceberg"], 5.0)


def test_r5_jackknife_over_batches_matches_the_hand_value():
    """Four equal-weight batches with constant offsets 0.01..0.04 from the ideal raw curve: the
    pooled residual is 0.025 and the delete-one jackknife SE of the mean is std(ddof=1)/sqrt(4)."""
    t = np.array([0.0, 0.5, 1.0])
    deltas = np.array([0.01, 0.02, 0.03, 0.04])
    ideal = _arm(t, 0.30, 0.40)
    ice = _arm(t, 0.30 + deltas.mean(), 0.40, acceptance=np.ones(3))
    ice["per_batch"] = {"raw": {OBS: [np.full(3, 0.30 + d) for d in deltas]},
                        "cond": {OBS: [np.full(3, 0.40) for _ in deltas]},
                        "wsum": [np.full(3, 75.0) for _ in deltas],
                        "p_in": [np.ones(3) for _ in deltas]}
    s = _score(ideal, _arm(t, 0.30, 0.40), ice)
    assert s.se_method["Iceberg"] == "jackknife"
    assert np.isclose(s.residual[("Iceberg", "raw")], 0.025, atol=1e-12)
    assert np.isclose(s.se[("Iceberg", "raw")], np.std(deltas, ddof=1) / 2, rtol=1e-10)
    assert s.se_method["bare raw"] == "legacy"


def test_r6_cost_is_the_mean_of_inverse_acceptance():
    t = np.array([0.0, 1.0])
    ice = _arm(t, 0.30, 0.40, acceptance=[1.0, 0.01])
    s = _score(_arm(t, 0.30, 0.40), _arm(t, 0.30, 0.40, p_in=0.5), ice, n_traj_ice=100_000)
    assert np.isclose(s.cost["Iceberg"], 50.5)
    assert np.isclose(s.cost_final["Iceberg"], 100.0)
    assert np.isclose(s.cost["bare + Gauss"], 2.0)
    assert np.isclose(s.cost["bare raw"], 1.0)


def test_r7_verdicts_respect_the_combined_error_bar():
    s = _score(*_healthy(se=0.001))
    by = {(p.ref, p.a, p.b): p for p in s.pairs}
    p = by[("cond", "bare + Gauss", "Iceberg + Gauss")]
    se2 = 0.001 ** 2
    msd_a, msd_b = 0.01 ** 2 - se2, 0.002 ** 2 - se2
    sig_a = np.sqrt(7 * (4 * 0.01 ** 2 * se2 + 2 * se2 ** 2)) / 7
    sig_b = np.sqrt(7 * (4 * 0.002 ** 2 * se2 + 2 * se2 ** 2)) / 7
    assert np.isclose(p.gap, msd_b - msd_a) and np.isclose(p.sigma, np.hypot(sig_a, sig_b))
    assert p.verdict == (f"Iceberg + Gauss better: rms {np.sqrt(msd_b):.4f} vs "
                         f"{np.sqrt(msd_a):.4f}")
    loose = _score(*_healthy(se=0.05))
    by = {(p.ref, p.a, p.b): p for p in loose.pairs}
    assert by[("cond", "bare + Gauss", "Iceberg + Gauss")].verdict == "unresolved"
    assert {(p.ref, p.a, p.b) for p in s.pairs} == {
        (r, "bare + Gauss", b) for r in REFS for b in ("Iceberg", "Iceberg + Gauss")}
