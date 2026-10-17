"""FROZEN tests (test-first, blind) for the H2 hardening pass (SPEC A and D).

1. native_counts counts a pytket Conditional by the gate it wraps (1q / Rz / 2q), once.
2. hqc_estimate's default is Rz-free.
3. submit_hosted_le builds QuantinuumConfig with no_opt=True (QI-8); refusals still precede qnexus.
4. HardwareConfig defaults for the new driver fields.

Nexus is a FAKE `qnexus` injected into sys.modules (style of tests/test_h2_backend.py); no test touches
the network or spends HQC. Every HQC number is an OFFLINE estimate, never an H2 result.
"""

import builtins
import importlib
import sys
import types

import pytest
from pytket import Circuit, OpType

from config import CONFIG
from src.h2_backend import DeviceRefused, offline_compile_backend
from src.h2_circuits import (
    codes_h2_circuit,
    compile_for_h2,
    hqc_estimate,
    native_counts,
)
from src.h2_hosted import submit_hosted_le

# Ops that are not charged as gates (Measure/Reset are counted separately).
_NOT_GATES = {
    OpType.Measure, OpType.Reset, OpType.Barrier, OpType.ClassicalTransform, OpType.SetBits,
    OpType.CopyBits, OpType.RangePredicate, OpType.ExplicitPredicate, OpType.ExplicitModifier,
    OpType.MultiBit,
}


# =========================================================================== fake qnexus
class _Recorder:
    def __init__(self):
        self.calls = []
        self.imports = []

    def called(self, name):
        return [c for c in self.calls if c[0] == name]


@pytest.fixture
def fake_qnexus(monkeypatch):
    rec = _Recorder()
    qnx = types.ModuleType("qnexus")
    models = types.ModuleType("qnexus.models")

    class QuantinuumConfig:
        def __init__(self, *args, **kwargs):
            assert not args
            self.kwargs = dict(kwargs)
            rec.calls.append(("QuantinuumConfig", args, dict(kwargs)))

    def rec_fn(name, ret):
        def f(*a, **kw):
            rec.calls.append((name, a, kw))
            return ret(*a, **kw) if callable(ret) else ret

        return f

    qnx.auth = types.SimpleNamespace(login_with_token=rec_fn("auth.login_with_token", None),
                                     is_logged_in=rec_fn("auth.is_logged_in", True))
    qnx.projects = types.SimpleNamespace(get_or_create=rec_fn("projects.get_or_create", "proj"))
    qnx.circuits = types.SimpleNamespace(
        upload=rec_fn("circuits.upload", lambda *a, **k: types.SimpleNamespace(c=k.get("circuit"))))
    qnx.start_execute_job = rec_fn("start_execute_job", types.SimpleNamespace(id="job-9"))
    models.QuantinuumConfig = QuantinuumConfig
    qnx.models = models
    monkeypatch.setitem(sys.modules, "qnexus", qnx)
    monkeypatch.setitem(sys.modules, "qnexus.models", models)
    real_import, real_import_module = builtins.__import__, importlib.import_module

    def is_qnx(name):
        return isinstance(name, str) and (name == "qnexus" or name.startswith("qnexus."))

    def tracking_import(name, *a, **kw):
        if is_qnx(name):
            rec.imports.append(name)
        return real_import(name, *a, **kw)

    def tracking_import_module(name, *a, **kw):
        if is_qnx(name):
            rec.imports.append(name)
        return real_import_module(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", tracking_import)
    monkeypatch.setattr(importlib, "import_module", tracking_import_module)
    monkeypatch.setenv("NEXUS_REFRESH_TOKEN", "fake-token")
    return rec


# =========================================================================== D1 conditionals
def _mixed_circuit():
    """3 qubits, 3 bits. Gates: plain Rz, plain PhasedX, plain ZZPhase; conditional Rz x2,
    conditional X, conditional ZZPhase, conditional CX; 2 Measures, 1 Reset."""
    c = Circuit(3, 3)
    c.Rz(0.3, 0)
    c.add_gate(OpType.PhasedX, [0.5, 0.25], [1])
    c.ZZPhase(0.25, 0, 1)
    c.Measure(0, 0)
    c.Rz(0.2, 1, condition_bits=[0], condition_value=1)
    c.Rz(0.7, 2, condition_bits=[0], condition_value=0)
    c.X(2, condition_bits=[0], condition_value=1)
    c.ZZPhase(0.5, 1, 2, condition_bits=[0], condition_value=1)
    c.CX(1, 2, condition_bits=[0], condition_value=1)
    c.Reset(0)
    c.Measure(1, 1)
    return c


def test_mixed_circuit_really_has_conditionals():
    """Oracle: pytket's own command list -- the fixture holds 5 Conditional commands (guards D1)."""
    cmds = _mixed_circuit().get_commands()
    assert sum(cmd.op.type == OpType.Conditional for cmd in cmds) == 5


def test_native_counts_conditionals_by_wrapped_gate():
    """Oracle: hand count -- n1q = Rz + PhasedX + 2 cond Rz + cond X = 5; nrz = 3 (plain + 2 cond);
    n2q = ZZPhase + cond ZZPhase + cond CX = 3; 2 measures, 1 reset, 3 qubits."""
    assert native_counts(_mixed_circuit()) == {
        "n1q": 5, "nrz": 3, "n2q": 3, "nmeas": 2, "nreset": 1, "nqubits": 3,
    }


@pytest.mark.parametrize("shots", [1, 100, 1000, 7777])
def test_hqc_estimate_mixed_matches_hand_formula(shots):
    """Oracle: 5 + shots*(N1q_nonRz + 10*N2q + 5*Nm)/5000 by hand: N1q_nonRz = 2 (PhasedX, cond X),
    N2q = 3, Nm = 3 qubits + 2 measures + 1 reset = 6 (Rz not charged)."""
    expected = 5 + shots * (2 + 10 * 3 + 5 * 6) / 5000
    assert hqc_estimate(native_counts(_mixed_circuit()), shots) == pytest.approx(expected, rel=1e-12)


def _unwrapped_counts(c):
    """Independent count: unwrap each Conditional to its inner op, then classify."""
    n1 = n2 = nrz = ncond = 0
    for cmd in c.get_commands():
        op = cmd.op
        if op.type == OpType.Conditional:
            ncond += 1
            op = op.op
        if op.type in _NOT_GATES:
            continue
        nq = len(cmd.qubits)
        if nq == 1:
            n1 += 1
            nrz += op.type == OpType.Rz
        elif nq == 2:
            n2 += 1
    return {"n1q": n1, "n2q": n2, "nrz": nrz, "ncond": ncond}


@pytest.fixture(scope="module")
def steane_compiled():
    from src.encoded_codes import EncodedTFIM, make_code

    E = CONFIG.encoded
    prog = EncodedTFIM(make_code("steane", 2), 1, 2, "periodic", E.J, E.h, E.dt, E.theta)
    backend = offline_compile_backend(CONFIG.hardware.le_device)
    return compile_for_h2(codes_h2_circuit(prog, 1)[0], backend)


def test_steane_compiled_conditionals_counted(steane_compiled):
    """Oracle: independent unwrapping of every Conditional in the compiled Steane 1x2 circuit --
    native_counts' n1q, n2q and nrz equal the unwrapped totals (feedforward Rz are Rz)."""
    exp = _unwrapped_counts(steane_compiled)
    assert exp["ncond"] > 0  # the instance is discriminating only if it has conditionals
    nc = native_counts(steane_compiled)
    assert nc["n1q"] == exp["n1q"]
    assert nc["n2q"] == exp["n2q"]
    assert nc["nrz"] == exp["nrz"]
    assert nc["n1q"] + nc["n2q"] == exp["n1q"] + exp["n2q"]


# =========================================================================== D2 Rz-free default
def test_hqc_estimate_default_is_rz_free():
    """Oracle: hand counts with nrz > 0 -- default == count_rz=False == 5 + 100*(3+20+25)/5000;
    count_rz=True adds the 4 Rz as 1q gates (discriminates the two defaults)."""
    nc = {"n1q": 7, "nrz": 4, "n2q": 2, "nmeas": 3, "nreset": 0, "nqubits": 2}
    free = 5 + 100 * (3 + 10 * 2 + 5 * 5) / 5000
    with_rz = 5 + 100 * (7 + 10 * 2 + 5 * 5) / 5000
    assert hqc_estimate(nc, 100) == pytest.approx(free, rel=1e-12)
    assert hqc_estimate(nc, 100) == hqc_estimate(nc, 100, count_rz=False)
    assert hqc_estimate(nc, 100, count_rz=True) == pytest.approx(with_rz, rel=1e-12)
    assert free != with_rz


# =========================================================================== D3 hosted no_opt
def _c(n):
    c = Circuit(n)
    c.ZZPhase(0.25, 0, 1)
    return c


def test_hosted_le_sends_no_opt(fake_qnexus, tmp_path):
    """Oracle: fake QuantinuumConfig kwargs -- device_name is the LE asked for (H2-2LE) and
    no_opt is True (QI-8: server optimisation would cancel folded ZZ gates)."""
    submit_hosted_le([_c(2), _c(3)], 10, project="p", device="H2-2LE",
                     ledger=tmp_path / "l.jsonl")
    cfgs = fake_qnexus.called("QuantinuumConfig")
    assert len(cfgs) == 1
    kw = cfgs[0][2]
    assert kw["device_name"] == "H2-2LE"
    assert kw.get("no_opt") is True
    assert "max_cost" not in kw
    assert len(fake_qnexus.called("start_execute_job")) == 1


@pytest.mark.parametrize("dev", ["H2-1E", "H2-1SC", "H2-1", "bogus"])
def test_hosted_le_device_refusal_before_qnexus(fake_qnexus, tmp_path, dev):
    """Oracle: import recorder -- a non-LE device is refused with no qnexus import or call."""
    with pytest.raises(DeviceRefused):
        submit_hosted_le([_c(2)], 10, project="p", device=dev, ledger=tmp_path / "l.jsonl")
    assert fake_qnexus.imports == [] and fake_qnexus.calls == []


def test_hosted_le_width_refusal_before_qnexus(fake_qnexus, tmp_path):
    """Oracle: import recorder -- 21 qubits refused with no qnexus import or call."""
    with pytest.raises(ValueError):
        submit_hosted_le([_c(2), _c(21)], 10, project="p", ledger=tmp_path / "l.jsonl")
    assert fake_qnexus.imports == [] and fake_qnexus.calls == []


# =========================================================================== D4 / SPEC A config
def test_hardware_config_new_defaults():
    """Oracle: SPEC A defaults (Quantinuum 'Hardware Credit Limitations': 50 HQC/shot, 10,000
    shots/job; 32-qubit Nexus emulator) and the off-by-default gate."""
    hw = CONFIG.hardware
    assert hw.nexus_tier == "dry-run"
    assert hw.nexus_tier != "emulator"
    assert hw.allow_hardware is False
    assert hw.max_cost_hqc == 0.0
    assert hw.emulator_max_qubits == 32
    assert hw.max_shots_per_job == 10000
    assert hw.max_hqc_per_shot == 50.0
    assert isinstance(hw.max_hqc_per_shot, float)


def test_fresh_hardware_config_defaults_match():
    """Oracle: a freshly constructed HardwareConfig has the same defaults (CONFIG not mutated)."""
    from config import HardwareConfig

    hw = HardwareConfig()
    assert (hw.nexus_tier, hw.emulator_max_qubits, hw.max_shots_per_job, hw.max_hqc_per_shot) == (
        "dry-run", 32, 10000, 50.0)
    assert hw.allow_hardware is False and hw.max_cost_hqc == 0.0
