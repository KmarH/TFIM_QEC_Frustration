"""Regression tests for the findings of review/17 (written by the author, AFTER the review: unlike
tests/test_h2_driver.py, test_h2_hardening.py and test_h2_q3.py these were not written blind).

Oracles: the claim "the emulator tier is reachable only when CONFIG says so" (an explicit tier
argument may step DOWN, never UP); a NaN comparison is always False, so every limit must be a
positive finite test; a quote list shorter than the circuit list leaves circuits unquoted; the
Q3 items must be the circuits the config names (step = round(t / dt)), with distinct insertion seeds.
No test touches the network: Nexus is replaced by logging fakes.
"""

import importlib
from dataclasses import replace

import numpy as np
import pytest
from pytket import Circuit

from config import CONFIG
from src import h2_backend
from src.backends_qc import NEXUS_APPROVAL

TOK = NEXUS_APPROVAL


@pytest.fixture
def drv():
    return importlib.import_module("src.h2_driver")


@pytest.fixture(autouse=True)
def _ledger_to_tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(h2_backend, "LEDGER", tmp_path / "ledger.jsonl")


def _qc(n, tag=0):
    c = Circuit(n, n)
    c.Rz(0.1 * (tag + 1), 0)
    c.ZZPhase(0.25, 0, 1)
    for q in range(n):
        c.Measure(q, q)
    return c


def _plan(drv):
    items = [
        drv.PlannedCircuit(label=f"i{k}", group="hand", shots=100, circuit=_qc(4, k), n_qubits=4,
                           estimate_hqc=6.0, meta={})
        for k in range(2)
    ]
    return drv.Plan(group="hand", items=items)


def _hw(**kw):
    base = {"nexus_tier": "emulator", "allow_hardware": True, "max_cost_hqc": 25.0,
            "emulator_device": "H2-2E", "syntax_checker": "H2-2SC", "nexus_project": "t"}
    base.update(kw)
    return replace(CONFIG.hardware, **base)


class _Log:
    def __init__(self, short=False):
        self.events, self.short = [], short

    def quote_fn(self, circuits, shots, **kw):
        self.events.append("quote")
        rows = [{"quoted_hqc": 3.0} for _ in circuits]
        return rows[:-1] if self.short else rows

    def submit_fn(self, circuits, shots, **kw):
        self.events.append("submit")
        return "job"

    def fns(self):
        return {"quote_fn": self.quote_fn, "submit_fn": self.submit_fn, "hosted_fn": self.submit_fn}


# --- review A, major: the explicit tier cannot step UP -----------------------------------------
@pytest.mark.parametrize("cfg_tier", ["dry-run", "sc", "hosted-le"])
def test_explicit_emulator_tier_cannot_override_config(drv, cfg_tier):
    """Oracle: docs/nexus_toggle.md -- spending needs the CONFIG edit AND the token; with config
    tier != 'emulator', execute(tier='emulator') must refuse and call nothing."""
    log = _Log()
    with pytest.raises(drv.DriverRefused):
        drv.execute(_plan(drv), hw=_hw(nexus_tier=cfg_tier), tier="emulator", approval=TOK, **log.fns())
    assert log.events == []


# --- review A, minor: a short quote list leaves circuits unquoted ------------------------------
@pytest.mark.parametrize("tier", ["sc", "emulator"])
def test_short_quote_list_refused(drv, tier):
    """Oracle: one quote per circuit -- 1 row for 2 circuits is refused, nothing is submitted."""
    log = _Log(short=True)
    with pytest.raises(drv.DriverRefused):
        drv.execute(_plan(drv), hw=_hw(), tier=tier, approval=TOK, **log.fns())
    assert "submit" not in log.events


# --- review A, minor: limits must be finite, positive and within the documented hard limits ----
@pytest.mark.parametrize("field", ["emulator_max_qubits", "max_shots_per_job", "max_hqc_per_shot"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 0, None])
def test_bad_limits_refused(drv, field, bad):
    """Oracle: NaN/inf/<=0/None limits would silently disable a gate (x > nan is False)."""
    log = _Log()
    with pytest.raises(drv.DriverRefused):
        drv.execute(_plan(drv), hw=_hw(**{field: bad}), approval=TOK, **log.fns())
    assert log.events == []


@pytest.mark.parametrize("field,over", [("emulator_max_qubits", 33), ("max_shots_per_job", 10001),
                                        ("max_hqc_per_shot", 50.5)])
def test_limits_above_documented_hard_limits_refused(drv, field, over):
    """Oracle: docs.quantinuum.com (32-qubit emulator state vector; 10,000 shots/job; 50 HQC/shot):
    a config may tighten but not loosen them."""
    log = _Log()
    with pytest.raises(drv.DriverRefused):
        drv.execute(_plan(drv), hw=_hw(**{field: over}), approval=TOK, **log.fns())
    assert log.events == []


def test_build_plan_nan_shot_limit_refused(drv):
    """Oracle: shots > NaN is False, so a NaN max_shots_per_job must be refused, not ignored."""
    with pytest.raises(drv.DriverRefused):
        drv.build_plan("bare-2x2-step1", 100, hw=replace(CONFIG.hardware, max_shots_per_job=float("nan")))


# --- review B: Q3 plan contents ----------------------------------------------------------------
def test_ladder_refuses_fewer_shots_than_instances(drv):
    """Oracle: shots // k with k = insert_instances; 5 shots over 10 instances would invent shots."""
    with pytest.raises(drv.DriverRefused):
        drv.build_plan("Q3-ladder", CONFIG.noise_scaling.insert_instances - 1)


@pytest.fixture(scope="module")
def ice_plan():
    return importlib.import_module("src.h2_driver").build_plan("Q3-iceberg", 500)


@pytest.fixture(scope="module")
def ladder_plan():
    return importlib.import_module("src.h2_driver").build_plan("Q3-ladder", 500)


def test_iceberg_items_are_the_named_circuits(ice_plan):
    """Oracle: independent rebuild -- item for time t is triangular_iceberg_h2_circuit at
    round(t / dt) steps compiled at level 0 (a 2x step count would be caught)."""
    from src.dimers import TriangularDimers
    from src.h2_circuits import compile_for_h2
    from src.h2_q3 import triangular_iceberg_h2_circuit
    from src.mcmc_baseline import initial_spins

    Q = CONFIG.q3
    s0 = initial_spins(TriangularDimers(3, 4), "flippable", 24)
    backend = h2_backend.offline_compile_backend(CONFIG.hardware.le_device)
    for it in ice_plan.items[:2]:
        n = round(it.meta["time"] / Q.dt)
        assert it.meta["step"] == n
        ref = compile_for_h2(triangular_iceberg_h2_circuit(3, 4, s0, n, Q.J, Q.noisy_h, Q.dt)[0], backend)
        assert it.circuit == ref


def test_ladder_step_counts_match_time(ladder_plan):
    """Oracle: 36 triangular bonds per Trotter step on 3x4 -- the lam=1 item at time t has
    36 * (t / dt) two-qubit gates (a 2x step count would double it)."""
    from src.h2_circuits import two_qubit_count

    for it in ladder_plan.items:
        if it.meta["lam"] == 1:
            assert two_qubit_count(it.circuit) == 36 * round(it.meta["time"] / CONFIG.q3.dt)


def test_insertion_seeds_differ_across_points(ladder_plan):
    """Oracle: independent draws per (lam, t) -- with seed = 1000*lam + step the rng streams
    default_rng((seed, i)) differ for different points (a constant seed would reuse one stream)."""
    seeds = {(1000 * it.meta["lam"] + it.meta["step"]) for it in ladder_plan.items if it.meta["method"] == "insert"}
    assert len(seeds) == 2 * len(CONFIG.noise_scaling.h2_ladder_times)
    a = np.random.default_rng((1000 * 2 + 4, 0)).random(8)
    b = np.random.default_rng((1000 * 2 + 8, 0)).random(8)
    assert not np.allclose(a, b)


# --- review B: q3 module -------------------------------------------------------------------------
def test_gauss_mask_needs_winding_y():
    """Oracle: hand mixture -- a defect-free state with the same W_x but another W_y is OUTSIDE the
    sector, so p_in = 1/2 (deleting the W_y condition would give 1)."""
    from src.dimers import TriangularDimers
    from src.h2_q3 import q3_observables
    from src.mcmc_baseline import Shells, initial_spins

    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable", 24)
    i0 = d.product_state_index(s0)
    wx, wy, df = d.winding_x(0), d.winding_y(0), d.total_defects()
    cand = np.nonzero((df == 0) & (wx == wx[i0]) & (wy != wy[i0]))[0]
    if len(cand) == 0:
        pytest.skip("no defect-free same-W_x, other-W_y state on 3x4")
    p = np.zeros(1 << d.N)
    p[i0] = p[cand[0]] = 0.5
    out = q3_observables(d, s0, Shells.build(d, CONFIG.q3.n_shells), p)
    assert out["p_in"] == pytest.approx(0.5)


def test_noise_scaled_circuits_rejects_midcircuit_measurement():
    """Oracle: only FINAL measurements are carried over; a mid-circuit one must raise a clear ValueError."""
    from src.h2_q3 import noise_scaled_circuits

    c = Circuit(2)
    c.add_c_register("m", 2)
    c.ZZPhase(0.2, 0, 1)
    c.Measure(0, c.get_c_register("m")[0])
    c.ZZPhase(0.2, 0, 1)
    c.Measure(1, c.get_c_register("m")[1])
    with pytest.raises(ValueError, match="mid-circuit|final"):
        noise_scaled_circuits(c, 3, "fold")
