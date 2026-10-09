"""The figures layer (handoff/08 Part B3) reads only saved data files: check its parsers recover the
numbers those files contain (so a figure is a faithful, reproducible view of data/*.txt).
Parsers only; no figure is written by the tests."""

import importlib.util
import os

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("plot_q3", os.path.join(ROOT, "scripts", "plot_q3.py"))
plot_q3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot_q3)


def _have(name):
    return os.path.exists(os.path.join(ROOT, "data", name))


@pytest.mark.skipif(not _have("q3_relaxation.txt"), reason="data file not generated")
def test_relaxation_parser():
    curves, refs, tables = plot_q3.parse_relaxation()
    c = curves["3x6 3-sublattice h=0.3"]
    assert c.shape[1] == 9 and c[0, 0] == 0.0 and c[0, 1] == pytest.approx(2 / 3, abs=1e-4)
    assert refs["3x6 3-sublattice h=0.3"]["B_f"] == pytest.approx(0.33097)
    assert tables[("3x6", "3-sublattice", 0.3)]["flippable_density"]["late_cond"] == pytest.approx(0.38386)
    assert {("3x4", "stripe", h) for h in (0.1, 0.2, 0.3, 0.5)} <= set(tables)


@pytest.mark.skipif(not _have("trotter_threshold.txt"), reason="data file not generated")
def test_threshold_parser():
    s = plot_q3.parse_threshold()[("3x4", "flippable", 0.3)]
    k = int(np.argmin(np.abs(s[:, 0] - 0.25)))
    assert s[k, 0] == pytest.approx(0.25) and s[k, 1] == pytest.approx(2.05e-3, rel=0.01)


@pytest.mark.skipif(not _have("q3_size.txt"), reason="data file not generated")
def test_size_parser():
    base, budget = plot_q3.parse_size()
    assert list(base[:, 0]) == [18, 36, 54, 72, 144]
    assert [b["N"] for b in budget] == [12, 18, 36, 54]
    assert [b["fits"] for b in budget] == [True, True, True, False]


@pytest.mark.skipif(not _have("q3_noisy.txt"), reason="data file not generated")
def test_noisy_parser():
    rows = plot_q3.parse_noisy()[("3x4", "flippable")]
    assert rows[0][0][0] == 0.0 and rows[0][3][0] == pytest.approx(1 / 3, abs=1e-4)
    assert all(len(r) == 16 for r in rows)   # t, acc, p_in | 6 flippable (incl. ideal cond) | 4 C1 | 3 defect
    assert rows[0][4][0] == pytest.approx(1 / 3, abs=1e-4)   # ideal conditioned at t = 0
