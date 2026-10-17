"""Regression tests for the findings of review/16 (written by the author, AFTER the review: unlike
tests/test_h2_circuits.py and tests/test_h2_backend.py these were not written blind).

Oracles: a NaN comparison is always False, so the spend gate must be a positive test; the SCOPE §5
state-vector ceiling is 24; PECOS charges p_init only on explicit Init ops, whereas this project's
noise model (src.backends_qc.Noise) charges the initial |0...0> too, so P(measure 1) = p_init
exactly for a lone qubit.
"""

import math
import sys
import types

import numpy as np
import pytest
from pytket import Bit, Circuit

from src.backends import MemoryCeilingError
from src.backends_qc import NEXUS_APPROVAL, Noise, _nexus_preflight
from src.h2_backend import LEWidthError, run_le, submit_nexus


@pytest.fixture
def fake_qnexus(monkeypatch):
    calls = []

    def rec(name):
        def f(*a, **k):
            calls.append(name)
            return types.SimpleNamespace(id="job-1")

        return f

    qnx = types.ModuleType("qnexus")
    qnx.auth = types.SimpleNamespace(is_logged_in=lambda: True, login_with_token=rec("login"))
    qnx.projects = types.SimpleNamespace(get_or_create=rec("project"))
    qnx.start_execute_job = rec("start_execute_job")
    models = types.ModuleType("qnexus.models")
    models.QuantinuumConfig = lambda **k: k
    monkeypatch.setitem(sys.modules, "qnexus", qnx)
    monkeypatch.setitem(sys.modules, "qnexus.models", models)
    monkeypatch.delenv("NEXUS_REFRESH_TOKEN", raising=False)
    return calls


GOOD = dict(
    project="p",
    device="H2-1E",
    allow_hardware=True,
    approval=NEXUS_APPROVAL,
    max_cost_hqc=10.0,
    estimated_hqc=7.5,
)


def _c():
    c = Circuit(2)
    c.CX(0, 1)
    return c


@pytest.mark.parametrize(
    "over",
    [
        {"max_cost_hqc": math.nan},
        {"max_cost_hqc": math.inf},
        {"max_cost_hqc": -math.inf},
        {"estimated_hqc": math.nan},
        {"estimated_hqc": -5.0},
        {"estimated_hqc": 0.0},
        {"estimated_hqc": math.inf},
        {"max_cost_hqc": math.nan, "estimated_hqc": 1e9},
        {"allow_hardware": "no"},
        {"allow_hardware": 1},
    ],
)
def test_spend_gate_rejects_non_finite_and_truthy_values(fake_qnexus, tmp_path, over):
    with pytest.raises((ValueError, PermissionError)):
        submit_nexus([_c()], 10, ledger=tmp_path / "l.jsonl", **{**GOOD, **over})
    assert fake_qnexus == []  # qnexus was never even logged into


@pytest.mark.parametrize("shots", [0, -3, 2.5, True])
def test_spend_gate_rejects_bad_shot_counts(fake_qnexus, tmp_path, shots):
    with pytest.raises(ValueError):
        submit_nexus([_c()], shots, ledger=tmp_path / "l.jsonl", **GOOD)
    assert fake_qnexus == []


def test_shared_preflight_rejects_non_finite_cap():
    spec = types.SimpleNamespace(n_phys=8)
    for cap in (math.nan, math.inf):
        with pytest.raises(ValueError):
            _nexus_preflight(
                spec,
                1,
                10,
                allow_hardware=True,
                approval=NEXUS_APPROVAL,
                max_cost_hqc=cap,
                device="H2-1E",
            )


def test_unwritable_ledger_refuses_before_spending(fake_qnexus, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(OSError):
        submit_nexus([_c()], 10, ledger=blocker / "sub" / "l.jsonl", **GOOD)
    assert "start_execute_job" not in fake_qnexus


def test_run_le_refuses_above_the_scope5_ceiling():
    c = Circuit(25)
    c.add_c_register("m", 1)
    with pytest.raises(LEWidthError) as ei:
        run_le(c, [Bit("m", 0)], 1, 0)
    assert isinstance(ei.value, MemoryCeilingError) and isinstance(ei.value, MemoryError)


def test_noisy_le_charges_p_init_on_the_initial_state():
    pytest.importorskip("pytket_pecos")
    c = Circuit(1)
    m = c.add_c_register("m", 1)
    c.Measure(c.qubits[0], m[0])
    shots, p = 20000, 0.3
    bits = run_le(c, [Bit("m", 0)], shots, 5, Noise(p_init=p))
    f = bits.mean()
    assert abs(f - p) < 4 * math.sqrt(p * (1 - p) / shots)  # fails (0.0) if init is not charged
    assert np.isfinite(f)
