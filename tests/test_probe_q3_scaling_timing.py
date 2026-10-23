"""FROZEN test spec (test-first) for scripts/probe_q3_scaling_timing.py: wall-clock probe of the
noisy Q3 sweep per grid cell. Written BEFORE the script exists; the implementation must make
these pass WITHOUT editing this file.

Import path: tests/conftest.py inserts the repo root into sys.path (the same REPO-root insertion
the scripts/ headers do), so `scripts.probe_q3_scaling_timing` imports as a namespace package
(scripts/ has no __init__.py). The script must keep its work under `if __name__ == "__main__":`
so importing it runs nothing.

Interface under test (black box):
    probe_timing(cells, n_traj_probe: int = 50, *, steps=None) -> dict

    steps: int or None, default None = the full default window (unchanged behaviour); an int caps
           the probed run at that many Trotter steps (runtime cap, coordinator decision
           2026-10-22; used by 3.2).

Shape FIXED by this spec:
    cells: iterable of src.q3_scaling.GridCell (the prefilter_grid output type).
    return: {(cell.N, cell.h, cell.lam): seconds}, one entry per input cell, seconds a finite
            float > 0. (Keyed by tuple, not by the cell: a non-frozen dataclass is unhashable.)

No pytest-timeout plugin is installed (requirements*.txt, tests/conftest.py), so the wall-clock
cap in 3.1 is recorded in the assertion message but NOT enforced.
"""

import math
import time

import pytest
from scripts.probe_q3_scaling_timing import probe_timing
from src.q3_scaling import GridCell

H = 0.3
SOFT_CAP_S = 600.0   # 3.1 generous wall-clock cap (documented only, not enforced)
SHORT_STEPS = 8      # 3.2 runtime cap (coordinator decision 2026-10-22)


def _cell(N, lam):
    # survival / keep are placeholders: the probe times the sweep, it does not filter.
    return GridCell(N=N, h=H, lam=lam, survival=1.0, keep=True)


def _check_seconds(out, cells):
    assert isinstance(out, dict)
    assert set(out) == {(c.N, c.h, c.lam) for c in cells}
    for k, v in out.items():
        assert isinstance(v, float), (k, type(v))
        assert math.isfinite(v) and v > 0, (k, v)


def test_probe_timing_smoke_small_cells():
    """3.1: two small N = 12 cells, tiny probe; returns positive float seconds per cell."""
    cells = [_cell(12, 1), _cell(12, 3)]
    t0 = time.perf_counter()
    out = probe_timing(cells, n_traj_probe=5)
    elapsed = time.perf_counter() - t0
    _check_seconds(out, cells)
    # Soft cap, not asserted (no timeout plugin): reported for the reader.
    print(f"probe_timing smoke: {elapsed:.1f}s wall (soft cap {SOFT_CAP_S:.0f}s)")


@pytest.mark.slow
def test_probe_timing_grows_with_n():
    """3.2: N = 20 costs more than N = 12 at the same (h, lam) (directional only, no ratio).
    Capped window (steps=8): the direction does not need the full window."""
    small, large = _cell(12, 1), _cell(20, 1)
    out = probe_timing([small, large], n_traj_probe=5, steps=SHORT_STEPS)
    _check_seconds(out, [small, large])
    assert out[(20, H, 1)] > out[(12, H, 1)], out
