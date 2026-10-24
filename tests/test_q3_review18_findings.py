"""Regression tests for the review/18 findings on `src/noisy_q3_sweep.score_cell`.

**Written AFTER the code, as a review artifact** — not a frozen spec. Their job is to make the
review/18 findings tamper-evident: each defect gets a test that states the *correct* behaviour and
is marked `xfail(strict=True)`, so

  * the suite stays green while the project lead's two rulings are pending, and
  * the moment a defect is fixed the test XPASSes, strict xfail turns that into a failure, and
    whoever fixed it must come here and drop the marker. A silent fix is impossible.

No test here touches `data/`, `runs/`, a frozen spec file or a verified core. All inputs are
synthetic and tiny: no lattice, no state vector, no trajectories.

Findings covered (see `review/18-q3-scaling-code.md`):
  F1  the common-estimand comparison is never computed (4 modes x 2 references = 8 cells, 6 filled)
  F2  the encoded mask carries no window term, so an explicit `early_t` bounds only the bare arm
  F4  `cost = 1/mean(acc)` understates the `mean(1/acc)` a per-point error target needs (Jensen)
  F5  `se` carries no shot noise, so an epsilon-sized SE passes the `se > 0` resolution guard
  F8  nothing enforces `n_ice <= n_bare`
  F9  zero-acceptance / NaN-SE points are dropped silently rather than flagged

Classical-prediction scaffolding only; nothing here is an H2 result.
"""
import numpy as np
import pytest

from src.noisy_q3_sweep import OBSERVABLE, ModeScore, score_cell

OBS = OBSERVABLE


def _curve(times, value):
    """A (values, SEs) pair of the shape score_cell expects, constant in time."""
    v = np.full(len(times), float(value))
    return [v.tolist(), np.zeros(len(times)).tolist()]


def _ideal(times, raw=0.30, cond=0.40):
    return {"times": list(times),
            "raw": {OBS: _curve(times, raw)},
            "cond": {OBS: _curve(times, cond)}}


def _bare(times, raw=0.30, cond=0.40, p_in=1.0):
    return {"times": list(times),
            "raw": {OBS: _curve(times, raw)},
            "cond": {OBS: _curve(times, cond)},
            "p_in": np.full(len(times), float(p_in)).tolist()}


def _ice(times, acceptance, raw=0.30, cond=0.40, p_in=1.0, se=None):
    blk_raw = _curve(times, raw)
    blk_cond = _curve(times, cond)
    if se is not None:
        blk_raw[1] = list(se)
        blk_cond[1] = list(se)
    return {"times": list(times),
            "raw": {OBS: blk_raw},
            "cond": {OBS: blk_cond},
            "acceptance": list(acceptance),
            "p_in": np.full(len(times), float(p_in)).tolist()}


def _row(scores, mode, window="early"):
    hits = [s for s in scores if s.mode == mode and s.window == window]
    assert len(hits) == 1, f"expected exactly one {mode!r}/{window!r} row, got {len(hits)}"
    return hits[0]


# --------------------------------------------------------------------------- F2

@pytest.mark.xfail(strict=True, reason="review/18 F2: the encoded mask has no window term, so an "
                                       "explicit early_t bounds only the bare arm")
def test_f2_explicit_early_t_bounds_the_encoded_arm_too():
    """An `early_t` narrower than the encoded grid must bound BOTH arms.

    Otherwise two rows both labelled window='early' are averaged over different time ranges, and
    their residuals are not comparable. Measured on real cells: N=12 h0.3 lam3 scored the bare arm
    on 10 points to t=4.50 and the Iceberg arm on 11 points to t=4.75.
    """
    t = [0.0, 1.0, 2.0, 3.0]
    scores = score_cell(_ideal(t), _bare(t), _ice(t, [1.0, 1.0, 1.0, 1.0]), early_t=1.0)
    # t <= 1.0 keeps two points on either arm
    assert _row(scores, "bare raw").n_points == 2
    assert _row(scores, "Iceberg").n_points == 2


# --------------------------------------------------------------------------- F4

@pytest.mark.xfail(strict=True, reason="review/18 F4: cost is 1/mean(acc); holding a target error "
                                       "at every window point needs mean(1/acc)")
def test_f4_cost_covers_the_worst_point_not_just_the_mean():
    """The shot-cost factor must not understate what a per-point error target costs.

    With acceptance [1.0, 0.01] the shots needed to hold a fixed error at *every* point scale as
    mean(1/acc) = 50.5, while 1/mean(acc) = 1.98 — a factor 25 apart. Jensen guarantees the
    reported figure is the smaller one, and it is the one the write-up quotes as 'x N shots'.
    """
    t = [0.0, 1.0]
    scores = score_cell(_ideal(t), _bare(t), _ice(t, [1.0, 0.01]), early_t=1.0)
    ice = _row(scores, "Iceberg")
    assert ice.cost == pytest.approx(50.5, rel=1e-6)


# --------------------------------------------------------------------------- F5

def test_f5_zero_se_is_not_resolved():
    """The guard that DOES work: an SE of exactly 0 reports NOT resolved.

    This one passes today and is here to pin it, so the epsilon case below is clearly a gap in the
    same guard rather than an absent guard.
    """
    assert not ModeScore("m", "early", OBS, residual=1e-3, residual_vs_raw=float("nan"),
                         se=0.0, cost=1.0, cost_final=1.0, n_points=3).resolved


@pytest.mark.xfail(strict=True, reason="review/18 F5: se carries no shot noise, so a machine-"
                                       "epsilon SE passes the se > 0 guard")
def test_f5_epsilon_se_is_not_resolved():
    """An SE at machine epsilon is no spread at all, and must not count as resolved.

    These are the real numbers from the 11th sweep cell (20, 0.5, 3) [measured 2026-10-23]: the
    encoded arm survived on ONE trajectory of 24, so every batch agreed to floating point and the
    residual collapsed onto the ideal curve. `se > 0` passed on 3.3e-17 and the cell was reported
    as resolved, which is how an artifact came within one step of being published as the study's
    first 'Iceberg wins' row.
    """
    assert not ModeScore("Iceberg", "early", OBS, residual=1.0140736045327614e-07,
                         residual_vs_raw=float("nan"), se=3.282302723603568e-17,
                         cost=3.277047529438764, cost_final=24.031681882562324,
                         n_points=3).resolved


# --------------------------------------------------------------------------- F9

@pytest.mark.xfail(strict=True, reason="review/18 F9: zero-acceptance points are dropped silently, "
                                       "so a collapsing arm is scored only where it survived")
def test_f9_collapsed_acceptance_does_not_flatter_the_residual():
    """An arm whose acceptance dies mid-window must not be scored only where it lived.

    Here the encoded arm is accurate for the first two points and wrong at the third, but its
    acceptance is 0 exactly where it is wrong — so dropping that point reports a perfect residual
    for a mode that has no estimate at all at the end of its own window.
    """
    t = [0.0, 1.0, 2.0]
    ice = _ice(t, [1.0, 1.0, 0.0], raw=0.30)
    ice["raw"][OBS][0] = [0.30, 0.30, 0.99]          # badly wrong exactly where acc == 0
    scores = score_cell(_ideal(t, raw=0.30), _bare(t), ice, early_t=2.0)
    row = _row(scores, "Iceberg")
    assert not np.isfinite(row.residual) or row.n_points == 3, (
        f"a dead point was dropped without a flag: residual={row.residual}, "
        f"n_points={row.n_points}")


# --------------------------------------------------------------------------- F8

@pytest.mark.xfail(strict=True, reason="review/18 F8: nothing enforces n_ice <= n_bare, so the "
                                       "encoded arm can be scored past the bare arm's last time")
def test_f8_encoded_window_may_not_outrun_the_bare_window():
    """The encoded arm must not be scored at times the bare arm never reached.

    `n_bare = (qdm_times/h)/dt` shrinks with h while the encoded step count does not, so at a
    large enough field the default `early_t` (the encoded arm's own last time) exceeds the bare
    arm's whole window and the two arms stop being comparable at all.
    """
    t_bare = [0.0, 1.0]
    t_ice = [0.0, 1.0, 2.0, 3.0]
    with pytest.raises((ValueError, AssertionError)):
        score_cell(_ideal(t_ice), _bare(t_bare), _ice(t_ice, [1.0] * 4))


# --------------------------------------------------------------------------- F1

@pytest.mark.xfail(strict=True, reason="review/18 F1: only 6 of the 4 modes x 2 references cells "
                                       "are computed, so there is no common-estimand comparison")
def test_f1_every_mode_is_scored_against_both_references():
    """Every mode needs a residual against BOTH ideal curves, or no verdict is like-for-like.

    Today the raw modes carry `residual` (vs raw) and NaN for `residual_vs_raw`, and the Gauss
    modes carry both — so bare-raw-vs-cond and Iceberg-raw-vs-cond are never computed and the
    question 'is Iceberg more accurate than bare + Gauss' has no common-reference answer. The
    published verdict instead subtracts across the diagonal, mixing estimator error with the
    ref_cond - ref_raw offset.
    """
    t = [0.0, 1.0, 2.0]
    scores = score_cell(_ideal(t), _bare(t), _ice(t, [1.0, 1.0, 1.0]), early_t=2.0)
    for mode in ("bare raw", "bare + Gauss", "Iceberg", "Iceberg + Gauss"):
        row = _row(scores, mode)
        assert np.isfinite(row.residual), f"{mode}: residual vs its own target is not finite"
        assert np.isfinite(row.residual_vs_raw), (
            f"{mode}: no residual against the common raw reference, so this mode cannot enter a "
            f"like-for-like verdict")
