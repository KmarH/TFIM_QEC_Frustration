"""Pool independently seeded SHARDS of one Q3 sweep cell back into one cell (DECIDED-10, review/18
F13; spec: tests/test_q3_shards.py).

A shard is an ordinary run of the cell (scripts/run_q3_sweep.py --cell ... --shard i) with its own
seed stream (`run_noisy_sweep(seed_extra=(i,))`) and one batch per arm. Batches are independent
sums over trajectories, so concatenating the shards' batches IS a run with more batches: no
choice is made about which data to keep, and the pooled curves are a pure function of the
per-batch detail every arm now stores (`per_batch`: per-batch curves, weights `wsum`, Gauss
acceptance `p_in`, and `w2sum` for the Kish ESS).

Pooling is exact for observables LINEAR in the readout distribution (flippable_density,
defect_density, memory): the pooled mixture of a run is sum_b acc_b / sum_b wsum_b, so
  raw:  O = sum_b wsum_b O_b / sum_b wsum_b
  cond: O = sum_b wsum_b p_in_b O_b / sum_b wsum_b p_in_b    (cond = O(mask P) / p_in)
[derived]. C1 is a connected correlator (non-linear in the distribution) and cannot be pooled
from per-batch values; it is returned as NaN and listed in "unmergeable" rather than
approximated. The merged cell is not bit-identical to a single process run (different streams),
only statistically equivalent.

Classical prediction under the ASSUMED research/06 noise model; never an H2 result.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

LINEAR_OBS = ("flippable_density", "defect_density", "memory")
NONLINEAR_OBS = ("C1",)


def _rows(x) -> np.ndarray:
    return np.asarray(x, dtype=float)


def _batch_se(vals: np.ndarray) -> np.ndarray:
    """The batch-means SE of src/noisy_q3.run_observables: finite batches only, NaN below two."""
    k = np.isfinite(vals).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(k > 1, np.nanstd(vals, axis=0, ddof=1) / np.sqrt(np.maximum(k, 1)), np.nan)


def _pool(vals: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Weighted mean over batches, skipping batches with no weight or no finite value."""
    ok = np.isfinite(vals) & (w > 0)
    num = np.where(ok, vals * w, 0.0).sum(0)
    den = np.where(ok, w, 0.0).sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


def merge_arms(arms: Sequence[dict], n_traj: Sequence[int]) -> dict:
    """Pool the batches of several shards of ONE arm into one arm dict (src/noisy_q3_sweep._arm
    shape). `n_traj[i]` is the number of trajectories shard i ran (for the acceptance)."""
    if not arms or len(arms) != len(n_traj):
        raise ValueError("need one n_traj per arm, and at least one arm")
    times = _rows(arms[0]["times"])
    for a in arms[1:]:
        if not np.allclose(_rows(a["times"]), times):
            raise ValueError("shards were recorded on different time grids")
    pbs = [a["per_batch"] for a in arms]
    cat = {key: np.concatenate([_rows(pb[key]) for pb in pbs], axis=0)
           for key in ("wsum", "p_in")}
    has_w2 = all("w2sum" in pb for pb in pbs)
    if has_w2:
        cat["w2sum"] = np.concatenate([_rows(pb["w2sum"]) for pb in pbs], axis=0)
    has_wp = all("wpsum" in pb and "wp2sum" in pb for pb in pbs)
    if has_wp:
        for k in ("wpsum", "wp2sum"):
            cat[k] = np.concatenate([_rows(pb[k]) for pb in pbs], axis=0)
    w, pin_b = cat["wsum"], cat["p_in"]
    out: dict = {"times": times, "raw": {}, "cond": {}, "unmergeable": list(NONLINEAR_OBS)}
    per_batch: dict = {"raw": {}, "cond": {}, **cat}
    for key, weight in (("raw", w), ("cond", w * np.nan_to_num(pin_b))):
        observables = list(pbs[0][key])
        for o in observables:
            vals = np.concatenate([_rows(pb[key][o]) for pb in pbs], axis=0)
            per_batch[key][o] = vals
            if o in LINEAR_OBS:
                out[key][o] = (_pool(vals, weight), _batch_se(vals))
            else:
                out[key][o] = (np.full(len(times), np.nan), np.full(len(times), np.nan))
    wtot = w.sum(0)
    out["acceptance"] = wtot / float(sum(n_traj))
    out["p_in"] = _pool(pin_b, w)
    out["n_eff"] = wtot
    if has_w2:
        w2 = cat["w2sum"].sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            out["ess"] = np.where(w2 > 0, wtot * wtot / w2, 0.0)
    else:
        out["ess"] = wtot
    if has_wp:
        a, b = cat["wpsum"].sum(0), cat["wp2sum"].sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            out["ess_cond"] = np.where(b > 0, a * a / b, 0.0)
    obs0 = "flippable_density"
    if obs0 in out["raw"]:
        out[obs0], out[f"{obs0}_se"] = out["raw"][obs0]
    out["per_batch"] = {k: ({o: list(v) for o, v in blk.items()} if isinstance(blk, dict)
                            else list(blk)) for k, blk in per_batch.items()}
    return out


_SAME_CELL = ("N", "h", "lam", "ice_steps")
_SAME_SETTINGS = ("record_every", "J", "dt")


def merge_cells(cells: Sequence[dict]) -> dict:
    """Merge shard cell JSONs (scripts/run_q3_sweep.py output) of the SAME cell into one.

    Refuses shards that differ in (N, h, lam), the encoded window, the noise model or the
    recording settings: those are different experiments, not more samples of one."""
    if not cells:
        raise ValueError("no shards to merge")
    c0 = cells[0]
    seeds = [tuple(c["settings"].get("seed_extra") or ()) for c in cells]
    if len(set(seeds)) != len(seeds):
        raise ValueError(f"shards share a seed stream {seeds}: the same trajectories would be "
                         "pooled twice as if independent")
    for c in cells[1:]:
        for k in _SAME_CELL:
            if c["cell"].get(k) != c0["cell"].get(k):
                raise ValueError(f"shard mismatch in cell.{k}: {c['cell'].get(k)} != "
                                 f"{c0['cell'].get(k)}")
        if c["noise"] != c0["noise"]:
            raise ValueError("shards were run under different noise models")
        for k in _SAME_SETTINGS:
            if c["settings"].get(k) != c0["settings"].get(k):
                raise ValueError(f"shard mismatch in settings.{k}")
    # Only the shard(s) run without --skip-ideal carry the (deterministic) ideal reference.
    ideals = [c["ideal"] for c in cells if c.get("ideal") is not None]
    ideal = ideals[0] if ideals else None
    for other in ideals[1:]:
        if not np.allclose(_rows(other["raw"]["flippable_density"][0]),
                           _rows(ideal["raw"]["flippable_density"][0]),
                           rtol=1e-10, atol=1e-12, equal_nan=True):
            raise ValueError("the ideal (zero-noise) reference differs between shards")
    s0 = c0["settings"]
    bare = merge_arms([c["bare"] for c in cells], [c["settings"]["traj_bare"] for c in cells])
    ice = None
    if c0.get("ice") is not None:
        ice = merge_arms([c["ice"] for c in cells], [c["settings"]["traj_ice"] for c in cells])
    settings = {**s0,
                "traj_bare": int(sum(c["settings"]["traj_bare"] for c in cells)),
                "traj_ice": int(sum(c["settings"]["traj_ice"] for c in cells)),
                "batches": int(sum(c["settings"]["batches"] for c in cells)),
                "shards": len(cells),
                "seed_extra": [c["settings"].get("seed_extra") for c in cells]}
    return {"caveat": c0.get("caveat"), "cell": c0["cell"], "settings": settings,
            "noise": c0["noise"], "provenance": {"merged_from_shards": [c.get("provenance")
                                                                       for c in cells]},
            "ideal": ideal, "bare": bare, "ice": ice}
