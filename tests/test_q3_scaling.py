"""FROZEN test spec (test-first) for src/q3_scaling.py: Stim first-order rate table, survival
curve and the (N, h, lam) prefilter grid. Written BEFORE the module exists; the implementation
must make these pass WITHOUT editing this file.

Interface under test (black box):
    StimRates(bare_fault_per_step, iceberg_detect_per_step, iceberg_undetected_per_step,
              iceberg_detect_prep_offset: float = 0.0)
    stim_rate_table(N_logical, lam, noise, *, scope="all") -> StimRates
    survival_curve(rates, steps) -> np.ndarray          (Iceberg detector survival vs Trotter steps)
        = exp(-(rates.iceberg_detect_prep_offset + rates.iceberg_detect_per_step * steps))
    (coordinator decision 2026-10-22: the offset is the step-independent prep + final-readout
    detection; bare_fault and iceberg_undetected stay plain per-step rates, no offset.)
    GridCell(N, h, lam, survival, keep)
    prefilter_grid(sizes, lams, hs, noise, qdm_times, dt, survival_floor=0.05) -> list[GridCell]

Every number here is Stim first-order fault ACCOUNTING under the ASSUMED research/06 H2 prior
(a classical prediction, never an H2 result).

Oracles (all read from the primary files, 2026-10-22):
  * data/q3_noisy.txt:56 (3x4 flippable, N = 12): Stim first-order exp(-detected_total) at
    t = 2, 4, 8, 12 = 0.607, 0.393, 0.165, 0.069 (3 decimals printed) [derived accounting].
  * research/derivations/01-noise-scaling-arm.md:52,55 (6x6, N = 36), "(c) Survival at 6x6":
    lam = 1 row 0.0691 / 0.1522 / 0.0259 and "all gates" lam = 3 row 0.2074 / 0.4556 / 0.0778
    (bare fault/step, Iceberg detect/step, Iceberg undetected/step; 4 decimals printed)
    [derived accounting]. The lam = 1 row equals data/q3_size.txt:20 (6x6) exactly.
  * docs/q3_thermalization.md:336 (§9.3): bare P(fault) = 1.92e-3 N and Iceberg P(undetected)
    = 7.2e-4 N per step "exactly linearly"; Iceberg P(detect) "≈ 4.5e-3 → 4.2e-3 per site from
    3x4 to 9x6" [derived accounting].

NOTE FOR THE IMPLEMENTER (not an interface guess; it is what the oracle itself contains):
  data/q3_noisy.txt's exp(-detected_total) is computed by src/encoded_codes.detected_total,
  whose docstring says "prep included" (encoded_codes.py:700). Re-measured 2026-10-22 with the
  repo's own functions on the 3x4 flippable Iceberg program [measured, scratch check]:
  detected_total(steps) = 0.06526 + 0.0542761 * steps EXACTLY (constant offset at 8/16/32/48
  steps), i.e. exp(-0.0542761 * steps) alone gives 0.648 / 0.420 / 0.176 / 0.0739, which
  misses tests 1.1 and 1.7 by ~7%. Hence the 4th StimRates field iceberg_detect_prep_offset
  (approved by the coordinator 2026-10-22); stim_rate_table must fill it, and survival_curve
  must use it. Its default 0.0 leaves test 1.2 (pure per-step rates) unaffected.
"""

import math

import numpy as np
import pytest
from src.q3_scaling import (
    GridCell,
    StimRates,
    prefilter_grid,
    stim_rate_table,
    survival_curve,
)

from config import CONFIG
from src.encoded_codes import NoiseRates

# --------------------------------------------------------------------------- fixtures / oracles
# The research/06 H2 PRIOR, built exactly as scripts/run_q3_noisy.py:34-35 builds it from
# config.SensitivityConfig (p2_prior = 6e-4, p1_ratio = 0.1 -> p1 = pm = p_init = 6e-5,
# zz_bias_prior = 0.05; config.py:331-333). data/q3_noisy.txt:3 records the same values.
_S = CONFIG.sensitivity
_P1 = _S.p2_prior * _S.p1_ratio
PRIOR = NoiseRates(p2=_S.p2_prior, p1=_P1, pm=_P1, p_init=_P1, zz_bias=_S.zz_bias_prior)

# Q3 baseline time settings (config.Q3BaselineConfig: dt = 0.25, qdm_times = 12.0).
DT = CONFIG.q3.dt
QDM_TIMES = CONFIG.q3.qdm_times

# 1.1 oracle: data/q3_noisy.txt line 56, "Stim first-order exp(-detected_total) [derived]"
# values of the "t=..: <local-sim> vs <Stim>" pairs (the second number of each pair).
STIM_SURVIVAL_N12 = {2.0: 0.607, 4.0: 0.393, 8.0: 0.165, 12.0: 0.069}
# Printed to 3 decimals: half a unit in the last place is 5e-4, which exceeds 0.5 % of 0.069
# (3.45e-4). The tolerance is therefore 0.5 % relative OR the printed rounding, whichever is larger.
HALF_ULP_3DEC = 5e-4


def _tol_3dec(ref: float) -> float:
    return max(0.005 * ref, HALF_ULP_3DEC)


# 1.2 oracle: research/derivations/01-noise-scaling-arm.md, "(c) Survival at 6x6" table.
#   line 52: | — | 1 | 0.0691 | 0.1522 | 0.0259 | ...
#   line 55: | all gates | 3 | 0.2074 | 0.4556 | 0.0778 | ...
# (bare fault/step, Iceberg detect/step, Iceberg undetected/step). 4 decimals printed: half a
# unit (5e-5) is <= 0.19 % of the smallest entry, inside the 0.5 % tolerance.
ROWS_6x6 = {
    1: (0.0691, 0.1522, 0.0259),
    3: (0.2074, 0.4556, 0.0778),
}

# 1.4 oracle: docs/q3_thermalization.md:336 (§9.3).
BARE_PER_SITE = 1.92e-3
UNDET_PER_SITE = 7.2e-4
SIZES = (12, 18, 20, 36, 54)

# 1.5 oracle: docs/q3_thermalization.md:336 states the detect-per-site range as
# "≈ 4.5e-3 → 4.2e-3", i.e. to 2 significant figures. The unrounded per-site values printed in
# data/q3_size.txt:22 are 4.52e-3 (3x4), 4.38e-3 (3x6), 4.23e-3 (6x6), 4.18e-3 (9x6); 4.52e-3
# and 4.18e-3 lie OUTSIDE a literal [4.2e-3, 4.5e-3]. The range is therefore applied at the
# precision it was stated with: [4.15e-3, 4.55e-3) (every value that rounds to 4.2e-3 .. 4.5e-3).
DETECT_PER_SITE_LO = 4.15e-3
DETECT_PER_SITE_HI = 4.55e-3


def _rel_close(x: float, ref: float, rel: float) -> bool:
    return abs(x - ref) <= rel * abs(ref)


def test_oracle_provenance_prior_matches_data_header():
    """Guard: the prior built from config is the one the oracles were generated with
    (data/q3_noisy.txt:3, data/q3_size.txt:15: p2=0.0006, eta=0.05, p1=pm=p_init=6e-05), and the
    time settings are those of the baseline (dt = 0.25, qdm_times = 12)."""
    assert PRIOR.p2 == pytest.approx(6e-4, rel=1e-12)
    assert PRIOR.p1 == pytest.approx(6e-5, rel=1e-12)
    assert PRIOR.pm == pytest.approx(6e-5, rel=1e-12)
    assert PRIOR.p_init == pytest.approx(6e-5, rel=1e-12)
    assert PRIOR.zz_bias == pytest.approx(0.05, rel=1e-12)
    assert DT == 0.25
    assert QDM_TIMES == 12.0


# --------------------------------------------------------------------------- 1.1
def test_survival_n12_matches_stim_exp_minus_detected_total():
    """1.1: N = 12, lam = 1: survival_curve at steps = t/dt for t = 2, 4, 8, 12 equals the Stim
    first-order exp(-detected_total) of data/q3_noisy.txt:56 within 0.5 % (or printed rounding)."""
    rates = stim_rate_table(12, 1, PRIOR)
    assert isinstance(rates, StimRates)
    # the oracle contains a step-independent detection term (module NOTE), so it must be filled
    assert rates.iceberg_detect_prep_offset > 0
    ts = sorted(STIM_SURVIVAL_N12)
    steps = np.array([round(t / DT) for t in ts])               # 8, 16, 32, 48
    assert list(steps) == [8, 16, 32, 48]
    curve = np.asarray(survival_curve(rates, steps), dtype=float)
    assert curve.shape == (len(ts),)
    # the 4-field survival formula, exactly
    expect = np.exp(-(rates.iceberg_detect_prep_offset + rates.iceberg_detect_per_step * steps))
    assert np.allclose(curve, expect, rtol=1e-12, atol=0.0)
    for t, s in zip(ts, curve):
        ref = STIM_SURVIVAL_N12[t]
        assert abs(s - ref) <= _tol_3dec(ref), f"t={t}: survival {s:.5f} vs Stim {ref} (tol {_tol_3dec(ref):.2e})"


def test_survival_curve_formula_and_offset_default():
    """1.1 (4-field form): StimRates built with 3 fields has offset 0.0, and survival_curve is
    exp(-(offset + detect * steps)) for a hand-built rate set; bare/undetected rates do not enter."""
    steps = np.array([0, 1, 8, 48])
    plain = StimRates(bare_fault_per_step=0.02, iceberg_detect_per_step=0.05, iceberg_undetected_per_step=0.008)
    assert plain.iceberg_detect_prep_offset == 0.0
    assert np.allclose(np.asarray(survival_curve(plain, steps), dtype=float), np.exp(-0.05 * steps),
                       rtol=1e-12, atol=0.0)
    off = StimRates(bare_fault_per_step=0.9, iceberg_detect_per_step=0.05, iceberg_undetected_per_step=0.7,
                    iceberg_detect_prep_offset=0.1)
    assert np.allclose(np.asarray(survival_curve(off, steps), dtype=float), np.exp(-(0.1 + 0.05 * steps)),
                       rtol=1e-12, atol=0.0)


# --------------------------------------------------------------------------- 1.2
@pytest.mark.parametrize("lam", [1, 3])
def test_rate_table_n36_matches_derivation_01_all_gates_row(lam):
    """1.2: N = 36 (6x6) rates match research/derivations/01 (c): lam = 1 row and the
    'all gates' lam = 3 row, each field within 0.5 % relative."""
    rates = stim_rate_table(36, lam, PRIOR) if lam == 1 else stim_rate_table(36, lam, PRIOR, scope="all")
    assert isinstance(rates, StimRates)
    bare, det, und = ROWS_6x6[lam]
    assert _rel_close(rates.bare_fault_per_step, bare, 0.005), (rates.bare_fault_per_step, bare)
    assert _rel_close(rates.iceberg_detect_per_step, det, 0.005), (rates.iceberg_detect_per_step, det)
    assert _rel_close(rates.iceberg_undetected_per_step, und, 0.005), (rates.iceberg_undetected_per_step, und)


# --------------------------------------------------------------------------- 1.3
@pytest.mark.parametrize("N", [12, 36])
@pytest.mark.parametrize("lam", [2, 3])
def test_iceberg_undetected_scales_exactly_with_lambda(N, lam):
    """1.3: the Iceberg undetected rate comes entirely from logical-ZZ locations, so it is
    exactly x lam (research/derivations/01:57-58 [derived accounting]); 1e-9 relative."""
    r1 = stim_rate_table(N, 1, PRIOR).iceberg_undetected_per_step
    rl = stim_rate_table(N, lam, PRIOR).iceberg_undetected_per_step
    assert r1 > 0
    assert _rel_close(rl, lam * r1, 1e-9), (N, lam, rl, lam * r1)


# --------------------------------------------------------------------------- 1.4
@pytest.mark.parametrize("N", SIZES)
def test_bare_and_undetected_rates_linear_in_n(N):
    """1.4: bare fault/step = 1.92e-3 N and Iceberg undetected/step = 7.2e-4 N within 1 %
    (docs/q3_thermalization.md §9.3; the linear formula is the oracle at every listed N)."""
    rates = stim_rate_table(N, 1, PRIOR)
    assert _rel_close(rates.bare_fault_per_step, BARE_PER_SITE * N, 0.01), (N, rates.bare_fault_per_step)
    assert _rel_close(rates.iceberg_undetected_per_step, UNDET_PER_SITE * N, 0.01), (
        N, rates.iceberg_undetected_per_step)


# --------------------------------------------------------------------------- 1.5
def test_detect_rate_per_site_amortises_and_stays_in_range():
    """1.5: Iceberg detect/step per site is non-increasing in N (the syndrome round's
    N-independent part amortises, data/q3_size.txt:23) and lies in the §9.3 range (applied at
    its stated 2-significant-figure precision, see DETECT_PER_SITE_LO/HI). Iceberg needs an even
    number of logical qubits: odd N are filtered out (none of the listed sizes is odd)."""
    ns = sorted(n for n in SIZES if n % 2 == 0)
    assert ns == sorted(SIZES)
    per_site = [stim_rate_table(n, 1, PRIOR).iceberg_detect_per_step / n for n in ns]
    for n, v in zip(ns, per_site):
        assert DETECT_PER_SITE_LO <= v < DETECT_PER_SITE_HI, f"N={n}: detect/site {v:.4e}"
    diffs = np.diff(per_site)
    assert np.all(diffs <= 1e-12), dict(zip(ns, per_site))


# --------------------------------------------------------------------------- 1.6
@pytest.mark.parametrize("N,lam", [(12, 1), (12, 3), (20, 1), (36, 1), (36, 3), (54, 2)])
def test_survival_curve_non_increasing(N, lam):
    """1.6: survival can only fall as steps grow, for any increasing steps sequence."""
    rates = stim_rate_table(N, lam, PRIOR)
    for steps in (np.arange(0, 241), np.array([0, 1, 2, 5, 8, 16, 48, 160, 400])):
        curve = np.asarray(survival_curve(rates, steps), dtype=float)
        assert curve.shape == steps.shape
        assert np.all(np.isfinite(curve))
        assert np.all(np.diff(curve) <= 1e-12), (N, lam)


# --------------------------------------------------------------------------- 1.7
def test_prefilter_grid_single_cell_matches_n12_survival_and_keeps():
    """1.7: one (N=12, h=0.3, lam=1) cell with the baseline qdm_times / dt. Its survival must
    equal test 1.1's t = 12 value (0.069, data/q3_noisy.txt:56), so the prefilter evaluates the
    Iceberg survival at steps = qdm_times / dt = 48 (t = 12), NOT at the Q3 window
    qdm_times / h = 40 (160 steps, where survival would be ~1e-4 and keep False), using the
    4-field survival formula (prep offset included). 0.069 > 0.05 -> keep is True."""
    cells = prefilter_grid([12], [1], [0.3], PRIOR, qdm_times=QDM_TIMES, dt=DT, survival_floor=0.05)
    assert isinstance(cells, list)
    assert len(cells) == 1
    c = cells[0]
    assert isinstance(c, GridCell)
    assert c.N == 12
    assert math.isclose(c.h, 0.3)
    assert c.lam == 1
    ref = STIM_SURVIVAL_N12[12.0]
    assert abs(c.survival - ref) <= _tol_3dec(ref), (c.survival, ref)
    # consistent with the 4-field curve of the same rates at steps = qdm_times / dt = 48
    s48 = float(np.asarray(survival_curve(stim_rate_table(12, 1, PRIOR), np.array([48])), dtype=float)[0])
    assert math.isclose(c.survival, s48, rel_tol=1e-9)
    assert c.keep is True
