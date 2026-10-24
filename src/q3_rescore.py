"""v2 scoring of the Q3 sweep (DECIDED-8, DECIDED-10; spec: tests/test_q3_rescore.py).

What changes against `src/noisy_q3_sweep.score_cell` (kept byte-identical as the legacy section
9.2 metric, so its review/18 strict xfails keep documenting the legacy defects):

  * every mode is scored against BOTH ideal references, raw and Gauss-conditioned: the 4 x 2
    common-estimand table (F1), and a winner is called only within one reference;
  * one common window for all modes, the encoded arm's recorded times, with the bare arm and the
    ideal curves interpolated onto them; a window outside the bare or ideal grid raises (F2, F8);
  * a pre-declared effective-sample-size floor: a mode whose Kish ESS is below the floor, whose
    value is non-finite or whose acceptance is zero at ANY window point has NO estimate - its
    window is never shortened to where it survived (F9, the 3e-17 artifact of cell (20, 0.5, 3)).
    The Gauss-conditioned modes use their OWN Kish ESS, (sum w p_in)^2 / sum (w p_in)^2, which is
    smaller than the raw one (blind review 2026-10-24, A2); cells without it use the lower bound
    acceptance * p_in * n_traj;
  * the error bar is the delete-one-batch jackknife whenever per-batch detail exists, with at
    least `min_batches` batches (else no estimate, A3); older cells fall back to the legacy
    per-point SE and are flagged `se_method == "legacy"`;
  * the VERDICT uses the bias-corrected mean-square residual
        msd = mean_t [ (O(t) - O_ref(t))^2 - Var O(t) ]
    because the mean |O - O_ref| carries a noise floor of about sqrt(2/pi) * sigma_t that grows as
    the effective sample shrinks and so penalises the noisier (encoded) arm even when both arms
    are exact (blind review 2026-10-24, A1). Var O(t) is the per-point jackknife variance; the SE
    of msd is a jackknife over batches with the variance recomputed inside each replicate.
    The mean |O - O_ref| is still reported, as a descriptive number continuous with section 9.2;
  * cost = mean(1/acceptance) over the window, the shot multiplier that holds a target error at
    every point when the per-shot variance is the same at every point (F4), with 1/acceptance at
    the last point alongside.

Two currencies are kept apart (review/18 F5): ESS and the jackknife SE are over fault
TRAJECTORIES (the readout distribution is exact, no shot noise); `cost` is in hardware SHOTS.

Sources and derivation: research/08-postselected-estimators.md (S3 Owen ch. 9: eq. 9.13 Kish
ESS; S8 Young 1210.3781 eq. 52 jackknife; S10 Schmeiser 1982 batch count) and
research/derivations/02-postselected-estimator.md. The floor value is a convention fixed in
config.Q3ScalingConfig.ess_floor BEFORE any re-score [assumed]; no source gives a number.

Classical prediction under the ASSUMED research/06 noise model; never an H2 result.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

MODES = ("bare raw", "bare + Gauss", "Iceberg", "Iceberg + Gauss")
REFS = ("raw", "cond")
HEADLINE = (("bare + Gauss", "Iceberg"), ("bare + Gauss", "Iceberg + Gauss"))
OBS = "flippable_density"

# mode -> (arm, curve key, uses the Gauss acceptance p_in)
_SPEC = {"bare raw": ("bare", "raw", False), "bare + Gauss": ("bare", "cond", True),
         "Iceberg": ("ice", "raw", False), "Iceberg + Gauss": ("ice", "cond", True)}


@dataclass
class PairVerdict:
    ref: str
    a: str
    b: str
    gap: float          # msd_b - msd_a (negative: b is closer to the reference)
    sigma: float        # combined SE of the msd's
    verdict: str


@dataclass
class CellScore:
    window: np.ndarray
    residual: dict = field(default_factory=dict)      # (mode, ref) -> mean |O - O_ref|
    se: dict = field(default_factory=dict)            # (mode, ref) -> SE of that residual
    msd: dict = field(default_factory=dict)           # (mode, ref) -> bias-corrected mean square
    msd_se: dict = field(default_factory=dict)        # (mode, ref) -> SE of msd
    rms: dict = field(default_factory=dict)           # (mode, ref) -> sign(msd) sqrt|msd|
    se_method: dict = field(default_factory=dict)     # mode -> "jackknife" | "legacy" | "none"
    n_batches: dict = field(default_factory=dict)     # mode -> batches behind the jackknife
    estimate: dict = field(default_factory=dict)      # mode -> bool
    reason: dict = field(default_factory=dict)        # mode -> why there is no estimate
    ess_min: dict = field(default_factory=dict)       # mode -> min ESS over the window
    cost: dict = field(default_factory=dict)          # mode -> mean(1/acceptance)
    cost_final: dict = field(default_factory=dict)    # mode -> 1/acceptance at the last point
    n_points: dict = field(default_factory=dict)      # mode -> points in the window
    pairs: list = field(default_factory=list)


def _fmt_rms(x: float) -> str:
    """rms for a verdict line; a non-positive bias-corrected mean square is inside the noise."""
    return f"{x:.4f}" if x > 0 else "<noise"


def _f(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


def _on(window, t_src, y) -> np.ndarray:
    """y(t_src) linearly interpolated onto the window (exact when the grids coincide)."""
    t_src, y = _f(t_src), _f(y)
    if len(t_src) == len(window) and np.allclose(t_src, window):
        return y.copy()
    return np.interp(window, t_src, y)


def _ess(arm: dict, which: str, gauss: bool, window, n_traj: int) -> np.ndarray:
    t = arm["times"]
    if gauss:
        if arm.get("ess_cond") is not None:
            return _on(window, t, arm["ess_cond"])
        surv = _on(window, t, arm["acceptance"]) if which == "ice" else 1.0
        return surv * _on(window, t, arm["p_in"]) * n_traj      # sum w p_in: a lower bound
    for key in ("ess", "n_eff"):
        if arm.get(key) is not None:
            return _on(window, t, arm[key])
    if which == "ice":
        return _on(window, t, arm["acceptance"]) * n_traj        # sum w: a lower bound
    return np.full(len(window), float(n_traj))


def _pooled(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    D = den.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(D > 0, num.sum(0) / np.where(D > 0, D, 1.0), np.nan)


def _point_var(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    """Delete-one-group jackknife variance of the pooled ratio, per time point."""
    B = num.shape[0]
    N, D = num.sum(0), den.sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        reps = (N - num) / (D - den)
    return (B - 1) / B * np.sum((reps - reps.mean(0)) ** 2, axis=0)


def _msd_stat(num, den, ref) -> float:
    r = _pooled(num, den)
    return float(np.mean((r - ref) ** 2 - _point_var(num, den)))


def _jackknife(num: np.ndarray, den: np.ndarray, ref: np.ndarray):
    """(SE of mean|R - ref|, msd, SE of msd) by delete-one-group jackknife; NaN when a replicate
    has no weight at some point (one group carries all of it)."""
    B = num.shape[0]
    D = den.sum(0)
    if np.any(D - den <= 0):
        return float("nan"), float("nan"), float("nan")
    N = num.sum(0)
    abs_reps = np.array([np.mean(np.abs((N - num[b]) / (D - den[b]) - ref)) for b in range(B)])
    se_abs = float(np.sqrt((B - 1) / B * np.sum((abs_reps - abs_reps.mean()) ** 2)))
    msd = _msd_stat(num, den, ref)
    if B < 3:
        return se_abs, msd, float("nan")
    keep = np.ones(B, dtype=bool)
    msd_reps = np.empty(B)
    for b in range(B):
        keep[b] = False
        msd_reps[b] = _msd_stat(num[keep], den[keep], ref)
        keep[b] = True
    se_msd = float(np.sqrt((B - 1) / B * np.sum((msd_reps - msd_reps.mean()) ** 2)))
    return se_abs, msd, se_msd


def rescore_cell(ideal: dict, bare: dict, ice: dict | None, *, ess_floor: float,
                 n_traj_bare: int, n_traj_ice: int, verdict_k: float = 1.0,
                 min_batches: int = 2, observable: str = OBS) -> CellScore:
    t_bare = _f(bare["times"])
    t_ideal = _f(ideal["times"])
    window = _f(ice["times"]) if ice is not None else t_bare
    if ice is not None and window[-1] > t_bare[-1] + 1e-9:
        raise ValueError(f"encoded window ends at t = {window[-1]} after the bare arm's last "
                         f"time {t_bare[-1]}: the arms would not be comparable (review/18 F8)")
    for name, grid in (("bare", t_bare), ("ideal", t_ideal)):
        if window[0] < grid[0] - 1e-9 or window[-1] > grid[-1] + 1e-9:
            raise ValueError(f"window [{window[0]}, {window[-1]}] is outside the {name} grid "
                             f"[{grid[0]}, {grid[-1]}]: interpolation would extrapolate")
    refs = {r: _on(window, t_ideal, ideal[r][observable][0]) for r in REFS}
    out = CellScore(window=window)
    arms = {"bare": bare, "ice": ice}
    nan = float("nan")
    for mode in MODES:
        which, key, gauss = _SPEC[mode]
        arm = arms[which]
        out.n_points[mode] = len(window)
        if arm is None:
            out.estimate[mode], out.reason[mode] = False, "no encoded arm in this cell"
            for r in REFS:
                for d in (out.residual, out.se, out.msd, out.msd_se, out.rms):
                    d[(mode, r)] = nan
            out.cost[mode] = out.cost_final[mode] = out.ess_min[mode] = nan
            out.se_method[mode], out.n_batches[mode] = "none", 0
            continue
        t = arm["times"]
        v = _on(window, t, arm[key][observable][0])
        se_pt = _on(window, t, arm[key][observable][1])
        surv = _on(window, t, arm["acceptance"]) if which == "ice" else np.ones(len(window))
        acc = surv * _on(window, t, arm["p_in"]) if gauss else surv
        ess = _ess(arm, which, gauss, window, n_traj_ice if which == "ice" else n_traj_bare)
        out.ess_min[mode] = float(np.min(ess))
        with np.errstate(divide="ignore"):
            inv = np.where(acc > 0, 1.0 / np.where(acc > 0, acc, 1.0), np.inf)
        out.cost[mode] = float(np.mean(inv))
        out.cost_final[mode] = float(inv[-1])
        problems = []
        if not np.all(np.isfinite(v)):
            problems.append(f"non-finite value at t = {window[~np.isfinite(v)].tolist()}")
        if not np.all(acc > 0):
            problems.append(f"zero acceptance at t = {window[~(acc > 0)].tolist()}")
        low = ess < ess_floor
        if np.any(low):
            problems.append(f"ESS {float(np.min(ess)):.3g} < floor {ess_floor:g} at t = "
                            f"{window[low].tolist()}")
        pb = arm.get("per_batch")
        num = den = None
        if pb is not None and "wsum" in pb:
            vals = np.array([_on(window, t, row) for row in pb[key][observable]])
            w = np.array([_on(window, t, row) for row in pb["wsum"]])
            if gauss:
                w = w * np.nan_to_num(np.array([_on(window, t, row) for row in pb["p_in"]]))
            ok = np.isfinite(vals) & (w > 0)
            num, den = np.where(ok, vals * w, 0.0), np.where(ok, w, 0.0)
            out.se_method[mode], out.n_batches[mode] = "jackknife", int(vals.shape[0])
            if vals.shape[0] < min_batches:
                problems.append(f"{vals.shape[0]} batches < min_batches {min_batches}")
            elif np.any(den.sum(0) - den <= 0):
                problems.append("one batch carries all the weight at some window point")
        else:
            out.se_method[mode], out.n_batches[mode] = "legacy", 0
        out.estimate[mode] = not problems
        out.reason[mode] = "; ".join(problems)
        for r in REFS:
            if not out.estimate[mode]:
                for d in (out.residual, out.se, out.msd, out.msd_se, out.rms):
                    d[(mode, r)] = nan
                continue
            e = v - refs[r]
            out.residual[(mode, r)] = float(np.mean(np.abs(e)))
            if num is not None:
                se_abs, msd, msd_se = _jackknife(num, den, refs[r])
            else:
                s2 = np.nan_to_num(se_pt) ** 2
                se_abs = float(np.nanmean(se_pt))
                msd = float(np.mean(e * e - s2))
                msd_se = float(np.sqrt(np.sum(4 * e * e * s2 + 2 * s2 * s2)) / len(e))
            out.se[(mode, r)], out.msd[(mode, r)], out.msd_se[(mode, r)] = se_abs, msd, msd_se
            out.rms[(mode, r)] = float(np.sign(msd) * np.sqrt(abs(msd)))
    for r in REFS:
        for a, b in HEADLINE:
            if not (out.estimate[a] and out.estimate[b]):
                out.pairs.append(PairVerdict(r, a, b, nan, nan, "no estimate"))
                continue
            gap = out.msd[(b, r)] - out.msd[(a, r)]
            sigma = float(np.hypot(out.msd_se[(a, r)], out.msd_se[(b, r)]))
            if np.isfinite(sigma) and abs(gap) > verdict_k * sigma:
                win, lose = (b, a) if gap < 0 else (a, b)
                verdict = (f"{win} better: rms {_fmt_rms(out.rms[(win, r)])} vs "
                           f"{_fmt_rms(out.rms[(lose, r)])}")
            else:
                verdict = "unresolved"
            out.pairs.append(PairVerdict(r, a, b, float(gap), sigma, verdict))
    return out
