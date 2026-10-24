"""Noisy bare + Iceberg Q3 sweep over (case, h, lam) — the expensive stage of the Q3
generalization study (research-flow decision cards D1-D5, 2026-10-22).

Generalizes the single cell of scripts/run_q3_noisy.py (3x4 flippable, h = 0.3, lam = 1;
data/q3_noisy.txt) over the three axes of the study:
  D1  lattice size   — the validated (Lx, Ly, start) cases of src/q3_scaling.SIZE_TO_CASE;
  D2  field strength — Q3BaselineConfig.h_curves instead of only noisy_h;
  D3  noise regime   — the NoiseScalingConfig lambda-insertion ladder (bare arm; see the
                       Iceberg limitation below).

EVERY number produced here is a CLASSICAL PREDICTION under the ASSUMED research/06 H2 prior
(Pauli-trajectory Monte Carlo), NEVER an H2 / hardware result.

Reuse only: the arms are src/noisy_q3.run_bare / run_iceberg (and
src/noise_scaling.run_bare_scaled for lam > 1), the observables src/noisy_q3.run_observables.
No simulation or observable logic is reimplemented here.

RESOLVED (D6, project lead, 2026-10-22). The gap surfaced during implementation — src/noise_scaling
had run_bare_scaled only, because decision D-NS3 ran Iceberg at lam = 1 and that exclusion was
never revisited in code — is closed: `src/noise_scaling.run_iceberg_scaled` amplifies the encoded
arm by the same Pauli insertion on the same 2q channel, so both arms of the ladder are amplified
alike and a lam > 1 Iceberg number here is a real measurement rather than a relabelled lam = 1 one.
The `arms="bare"` mode is kept (it is how a bare-only ladder cell is run, and what the timing probe
uses for lam > 1 cells it is not asked to encode).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates
from src.encoded_tfim import check_physical_ceiling
from src.mcmc_baseline import Shells, initial_spins
from src.noise_scaling import run_bare_scaled, run_iceberg_scaled
from src.noisy_q3 import make_iceberg, run_bare, run_iceberg, run_observables

OBSERVABLE = "flippable_density"
ICEBERG_OVERHEAD = 4          # [[N+2, N, 2]] data qubits + 2 syndrome ancillas [established]


def prior_noise() -> NoiseRates:
    """The research/06 H2 prior, built as scripts/run_q3_noisy.py builds it from
    config.SensitivityConfig [assumed noise model]."""
    s = CONFIG.sensitivity
    p1 = s.p2_prior * s.p1_ratio
    return NoiseRates(p2=s.p2_prior, p1=p1, pm=p1, p_init=p1, zz_bias=s.zz_bias_prior)


def _arm(d, s0, sh, run, max_spins: int) -> dict:
    """One arm's curves. The three keys of the frozen spec are the RAW observable; the rest
    (acceptance, p_in, and the sector-conditioned curves of every observable) are kept because
    the §9.2 verdict is a conditioned-vs-raw statement at a stated shot cost, and discarding them
    would make the generalized cells unscorable against the published one."""
    obs = run_observables(d, s0, sh, run, max_spins)
    value, se = obs.raw[OBSERVABLE]
    out = {"times": np.asarray(obs.times, dtype=float),
           "flippable_density": np.asarray(value, dtype=float),
           "flippable_density_se": np.asarray(se, dtype=float),
           "acceptance": np.asarray(obs.acceptance, dtype=float),
           "p_in": np.asarray(obs.p_in, dtype=float),
           "raw": {o: (np.asarray(v, dtype=float), np.asarray(s, dtype=float))
                   for o, (v, s) in obs.raw.items()},
           "cond": {o: (np.asarray(v, dtype=float), np.asarray(s, dtype=float))
                    for o, (v, s) in obs.cond.items()}}
    # Additive [2026-10-24]: the batch-level detail behind the aggregates, so a re-score under a
    # different window / cost / SE convention needs no new simulation. Stored as a LIST of 1-D
    # rows per batch because the JSON writer ravels an ndarray and would lose the (B, T) shape.
    if obs.n_eff is not None:
        out["n_eff"] = np.asarray(obs.n_eff, dtype=float)
    if obs.ess is not None:
        out["ess"] = np.asarray(obs.ess, dtype=float)
    if obs.ess_cond is not None:
        out["ess_cond"] = np.asarray(obs.ess_cond, dtype=float)
    if obs.per_batch is not None:
        pb = {}
        for key, block in obs.per_batch.items():
            if isinstance(block, dict):                 # "raw" / "cond": obs -> (B, T)
                pb[key] = {o: [np.asarray(row, dtype=float) for row in arr]
                           for o, arr in block.items()}
            else:                                       # "wsum" / "p_in" / "w2sum": (B, T)
                pb[key] = [np.asarray(row, dtype=float) for row in block]
        out["per_batch"] = pb
    return out


def run_noisy_sweep(cases: Sequence[tuple[int, int, str]], h_values: Sequence[float],
                    lams: Sequence[float], *, n_traj_bare: int, n_traj_ice: int,
                    n_batches: int, seed: int, noise: NoiseRates | None = None,
                    return_meta: bool = False, steps: int | None = None,
                    arms: str = "both", ice_steps: int | None = None,
                    record_every: int | None = None, mem_gb: float | None = None,
                    seed_extra: Sequence[int] = ()) -> dict:
    """Run the bare and Iceberg arms for every (case, h, lam) and return their RAW
    flippable-density curves with batch-means SE.

    cases      (Lx, Ly, start_label) tuples, e.g. (3, 4, "flippable").
    steps      None = the default windows (bare qdm_times / h, Iceberg noisy_ice_steps);
               an int caps BOTH arms at that many Trotter steps (runtime cap).
    noise      default = prior_noise(); NoiseRates() requests the ideal (zero-noise) circuit.
    return_meta  adds cell["meta"]["physical_qubits"] (the Iceberg register actually used).
    arms       "both" (default) or "bare" to skip the encoded arm (cell["ice"] is then None).
    ice_steps  None = CONFIG.q3.noisy_ice_steps (the published 48-step window); an int sets the
               encoded window only, which is how the SURVIVAL-MATCHED window per size is run
               (project lead, 2026-10-22) without shortening the bare arm.
    record_every, mem_gb
               None = the CONFIG.q3 values. They are per-size settings at larger N, where the
               accumulators (n_batches * n_records * 2^N * 8 bytes) would otherwise be refused.
    seed_extra extra integers appended to each cell's seed sequence (additive, 2026-10-24): an
               independent stream per SHARD of a cell (src/q3_shards.py). () is bitwise the
               pre-2026-10-24 stream.

    Classical prediction under an ASSUMED noise model; not an H2 result.
    """
    q3, ceil = CONFIG.q3, CONFIG.ceilings
    if arms not in ("both", "bare"):
        raise ValueError(f"arms must be 'both' or 'bare', got {arms!r}")
    noise = prior_noise() if noise is None else noise
    out: dict = {}
    for ci, (Lx, Ly, kind) in enumerate(cases):
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, ceil.ed_max_spins)
        sh = Shells.build(d, q3.n_shells)
        n_phys = d.N + ICEBERG_OVERHEAD
        has_ice = d.N % 2 == 0 and arms == "both"
        if has_ice:
            # refuse before allocating (SCOPE §5: the PHYSICAL register is what counts)
            check_physical_ceiling(n_phys, ceil.statevector_max_spins)
        for hi, h in enumerate(h_values):
            n_bare = steps if steps is not None else round((q3.qdm_times / h) / q3.dt)
            n_ice = steps if steps is not None else (q3.noisy_ice_steps if ice_steps is None
                                                     else int(ice_steps))
            for li, lam in enumerate(lams):
                kw = {"J": q3.J, "h": h, "dt": q3.dt,
                      "record_every": q3.noisy_record_every if record_every is None
                      else int(record_every),
                      "mem_gb": q3.noisy_mem_gb if mem_gb is None else float(mem_gb)}
                rng = np.random.default_rng([seed, ci, hi, li, *seed_extra])
                if lam == 1:
                    bare_run = run_bare(d, s0, n_steps=n_bare, noise=noise, n_traj=n_traj_bare,
                                        n_batches=n_batches, rng=rng,
                                        max_spins=ceil.ed_max_spins, **kw)
                else:
                    bare_run = run_bare_scaled(d, s0, lam=lam, method="insert", n_steps=n_bare,
                                               noise=noise, n_traj=n_traj_bare,
                                               n_batches=n_batches, rng=rng,
                                               max_spins=ceil.ed_max_spins, **kw)
                cell: dict = {"bare": _arm(d, s0, sh, bare_run, ceil.ed_max_spins), "ice": None}
                if has_ice:
                    if lam == 1:
                        ice_run = run_iceberg(d, s0, n_steps=n_ice, noise=noise,
                                              n_traj=n_traj_ice, n_batches=n_batches, rng=rng,
                                              max_spins=ceil.statevector_max_spins, **kw)
                    else:
                        # D6 (project lead, 2026-10-22): the encoded arm now has its own
                        # lambda-amplified runner, so a lam > 1 Iceberg number is a real
                        # amplified measurement, not a relabelled lam = 1 one.
                        ice_run = run_iceberg_scaled(d, s0, lam=lam, method="insert",
                                                     n_steps=n_ice, noise=noise,
                                                     n_traj=n_traj_ice, n_batches=n_batches,
                                                     rng=rng,
                                                     max_spins=ceil.statevector_max_spins, **kw)
                    cell["ice"] = _arm(d, s0, sh, ice_run, ceil.ed_max_spins)
                if return_meta:
                    cell["meta"] = {"physical_qubits": n_phys if d.N % 2 == 0 else 0}
                out[(Lx, Ly, kind, h, lam)] = cell
    return out


@dataclass
class ModeScore:
    """One mitigation mode's accuracy and shot cost over one window, scored exactly as
    docs/q3_thermalization.md §9.2 scores the published N = 12 cell."""

    mode: str
    window: str
    observable: str
    residual: float          # mean |O_noisy - O_ideal| over the window, vs the mode's OWN target
    residual_vs_raw: float   # Gauss modes only: the same mean against the ideal RAW curve
    se: float                # mean per-point batch SE of the mode (the resolution floor)
    cost: float              # shot-cost factor 1 / mean(acceptance) over the window
    cost_final: float        # 1 / acceptance at the last window point
    n_points: int

    @property
    def resolved(self) -> bool:
        """A residual comparable to the mode's own SE is at the statistical floor, i.e. NOT
        resolved as a difference (the §9.2 reading rule, made explicit).

        An SE of exactly 0 means there was no spread to estimate from (a single batch), not that
        the residual is infinitely well resolved, so it reports NOT resolved."""
        return bool(np.isfinite(self.residual) and np.isfinite(self.se) and self.se > 0
                    and self.residual > self.se)


def _mean_abs(v, ref, mask) -> float:
    return float(np.mean(np.abs(np.asarray(v)[mask] - np.asarray(ref)[mask]))) if mask.any() else float("nan")


def score_cell(ideal: dict, bare: dict, ice: dict | None, *, observable: str = OBSERVABLE,
               early_t: float | None = None) -> list[ModeScore]:
    """Score one sweep cell's modes against the ideal circuit, with the shot-cost factor.

    The metric is lifted from scripts/run_q3_noisy.py (the script that produced
    data/q3_noisy.txt), so a generalized cell is comparable to the published one by construction:
      * raw modes are scored against the ideal RAW curve;
      * Gauss-post-selected modes are scored against the ideal SECTOR-CONDITIONED curve - the
        quantity they actually estimate - with the score against the raw curve reported alongside;
      * the Iceberg arm is scored on its own (shorter) time grid, with the ideal curve interpolated
        onto it, and its cost includes the detector survival (times the Gauss acceptance for
        Iceberg + Gauss);
      * SE is the mean per-point batch SE: a residual below it is at the statistical floor.

    `early_t` bounds the early window (default: the encoded arm's own last time, i.e. matched
    survival); the late window is the second half of the bare arm's times.

    Classical prediction under an ASSUMED noise model; never an H2 result.
    """
    t_bare = np.asarray(bare["times"], dtype=float)
    t_ideal = np.asarray(ideal["times"], dtype=float)
    ref_raw = np.asarray(ideal["raw"][observable][0], dtype=float)
    ref_cond = np.asarray(ideal["cond"][observable][0], dtype=float)
    if early_t is None:
        early_t = float(np.asarray(ice["times"])[-1]) if ice else float(t_bare[-1])

    def on_bare(curve):
        return np.interp(t_bare, t_ideal, curve)

    out: list[ModeScore] = []
    windows = [("early", t_bare <= early_t + 1e-9), ("late", t_bare >= t_bare[-1] / 2)]
    for wname, wb in windows:
        for mode, key, acc in (("bare raw", "raw", np.ones_like(t_bare)),
                               ("bare + Gauss", "cond", np.asarray(bare["p_in"], dtype=float))):
            v, se = (np.asarray(x, dtype=float) for x in bare[key][observable])
            m = wb & np.isfinite(v) & (acc > 0)
            tgt = on_bare(ref_cond if key == "cond" else ref_raw)
            out.append(ModeScore(
                mode=mode, window=wname, observable=observable,
                residual=_mean_abs(v, tgt, m),
                residual_vs_raw=_mean_abs(v, on_bare(ref_raw), m) if key == "cond" else float("nan"),
                se=float(np.nanmean(se[m])) if m.any() else float("nan"),
                cost=float(1 / np.mean(acc[m])) if m.any() else float("nan"),
                cost_final=float(1 / acc[m][-1]) if m.any() else float("nan"),
                n_points=int(m.sum())))
    if ice is not None:
        t_ice = np.asarray(ice["times"], dtype=float)
        surv = np.asarray(ice["acceptance"], dtype=float)
        p_in = np.asarray(ice["p_in"], dtype=float)
        for mode, key, acc in (("Iceberg", "raw", surv), ("Iceberg + Gauss", "cond", surv * p_in)):
            v, se = (np.asarray(x, dtype=float) for x in ice[key][observable])
            m = np.isfinite(v) & (acc > 0)
            tgt = np.interp(t_ice, t_ideal, ref_cond if key == "cond" else ref_raw)
            out.append(ModeScore(
                mode=mode, window="early", observable=observable,
                residual=_mean_abs(v, tgt, m),
                residual_vs_raw=(_mean_abs(v, np.interp(t_ice, t_ideal, ref_raw), m)
                                 if key == "cond" else float("nan")),
                se=float(np.nanmean(se[m])) if m.any() else float("nan"),
                cost=float(1 / np.mean(acc[m])) if m.any() else float("nan"),
                cost_final=float(1 / acc[m][-1]) if m.any() else float("nan"),
                n_points=int(m.sum())))
    return out


def iceberg_physical_qubits(n_logical: int) -> int:
    """Iceberg [[N+2, N, 2]] plus 2 syndrome ancillas [established; verified against
    data/q3_noisy.txt (12 -> 16) and docs/q3_thermalization.md (54 -> 58)]."""
    return n_logical + ICEBERG_OVERHEAD


def make_iceberg_program(Lx: int, Ly: int, kind: str, h: float):
    """The Iceberg program of a case, for gate counts / HQC estimates (no simulation)."""
    q3 = CONFIG.q3
    d = TriangularDimers(Lx, Ly)
    s0 = initial_spins(d, kind, CONFIG.ceilings.ed_max_spins)
    return make_iceberg(d, s0, q3.J, h, q3.dt)
