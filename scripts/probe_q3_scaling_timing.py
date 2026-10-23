"""Wall-clock probe of the noisy Q3 sweep, per prefilter grid cell (decision card D5, 2026-10-22).

Before committing the full trajectory budget of the Q3 generalization study, measure what one
cell actually costs ON THIS HOST at a small trajectory count. The existing baseline cost is
known for one cell only (N = 12, h = 0.3, lam = 1: ~186 s bare + ~559 s Iceberg at 400 / 300
trajectories, data/q3_noisy.txt:53, measured on the 2-core Oracle VM), and the state vector
grows as 2^(physical qubits), so N = 20 (24 physical) is far more expensive than N = 12 (16).

This script only TIMES src/noisy_q3_sweep.run_noisy_sweep; it produces no physics numbers.
Nothing here touches hardware or spends HQC.

Usage: .venv/Scripts/python.exe -I scripts/probe_q3_scaling_timing.py
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterable

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from config import CONFIG
from src.noisy_q3_sweep import run_noisy_sweep
from src.q3_scaling import SIZE_TO_CASE, GridCell

# Arms timed per cell. The lam ladder has no encoded runner (src/noisy_q3_sweep LIMITATION), so
# a lam > 1 cell times the bare arm alone; a lam = 1 cell times bare + Iceberg. The returned
# seconds are therefore "what this cell can currently run", which is what a budget needs.
PROBE_BATCHES = 1


def probe_timing(cells: Iterable[GridCell], n_traj_probe: int = 50, *,
                 steps: int | None = None) -> dict[tuple[int, float, float], float]:
    """Wall-clock seconds of one small run_noisy_sweep call per cell.

    cells          src.q3_scaling.GridCell values (prefilter_grid output).
    n_traj_probe   trajectories per arm (small: this is a timing probe, not a measurement).
    steps          None = the default windows; an int caps the probed run (runtime cap).

    Returns {(N, h, lam): seconds}. Keyed by tuple because GridCell is not frozen.
    """
    out: dict[tuple[int, float, float], float] = {}
    for cell in cells:
        case = SIZE_TO_CASE[cell.N]
        # lam > 1 has no encoded runner yet, so those cells time the bare arm alone.
        arms = "both" if cell.lam == 1 else "bare"
        t0 = time.perf_counter()
        run_noisy_sweep([case], [cell.h], [cell.lam], n_traj_bare=n_traj_probe,
                        n_traj_ice=n_traj_probe, n_batches=PROBE_BATCHES, seed=CONFIG.seed,
                        steps=steps, arms=arms)
        out[(cell.N, cell.h, cell.lam)] = float(time.perf_counter() - t0)
    return out


def _extrapolate(seconds: float, n_traj_probe: int, target_traj: int) -> float:
    """Linear-in-trajectories cost estimate [assumed: per-trajectory cost is constant]."""
    return seconds * target_traj / n_traj_probe


def main() -> None:
    q3 = CONFIG.q3
    probe_traj, cap = 5, 8
    cells = [GridCell(N=n, h=q3.noisy_h, lam=1, survival=float("nan"), keep=True)
             for n in (12, 18, 20)]
    print(f"# D5 timing probe: {probe_traj} trajectories/arm, window capped at {cap} steps, "
          f"h = {q3.noisy_h}, lam = 1. Wall clock on THIS host; no HQC, no hardware.")
    out = probe_timing(cells, n_traj_probe=probe_traj, steps=cap)
    print(f"  {'N':>4s} {'physical':>9s} {'probe s':>9s} {'s/traj':>9s} "
          f"{'est. full-traj s (capped window)':>33s}")
    for cell in cells:
        s = out[(cell.N, cell.h, cell.lam)]
        full = _extrapolate(s, probe_traj, q3.noisy_traj_ice)
        print(f"  {cell.N:>4d} {cell.N + 4:>9d} {s:>9.1f} {s / probe_traj:>9.2f} {full:>33.0f}")
    print("# The full study window is far longer than the probe cap, so these are LOWER BOUNDS "
          "[inferred]; scale by (window steps / cap) for a window estimate.")


if __name__ == "__main__":
    main()
