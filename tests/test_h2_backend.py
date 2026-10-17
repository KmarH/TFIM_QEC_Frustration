"""FROZEN tests (test-first) for src/h2_backend.py: the H2 local emulator and the Nexus gates.

No test here touches the network or spends HQC. Nexus is replaced by a FAKE `qnexus` module
(and `qnexus.models.QuantinuumConfig`) injected into sys.modules; every call and every import of
`qnexus` made while a test runs is recorded, so a refusal can be shown to happen BEFORE qnexus is
even imported. The real qnexus in .venv is never used.

Emulator tests (noise calibration) start with pytest.importorskip("pytket_pecos"): they run in
.venv-le and skip in .venv. Gate / mocking tests must pass in both environments.

Every noisy number is a classical prediction under an ASSUMED depolarizing model on a LOCAL
emulator, never an H2 result.
"""

import ast
import builtins
import importlib
import json
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest
from pytket import Bit, Circuit, OpType
from src.h2_backend import (
    E_DEVICES,
    HW_DEVICES,
    LE_DEVICES,
    SC_DEVICES,
    DeviceRefused,
    pecos_error_params,
    run_le,
    submit_nexus,
    syntax_check,
)

from src import h2_backend
from src.backends_qc import NEXUS_APPROVAL, Noise

ROOT = Path(__file__).resolve().parents[1]
NSIG = 4          # statistical tolerances: 4 sigma of binomial shot noise sqrt(p(1-p)/n)
ALL_NON_SC = ["H2-1E", "H2-2E", "H2-1", "H2-2", "H2-1LE", "H2-2LE", "bogus"]


# =========================================================================== fake qnexus
class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Recorder:
    def __init__(self):
        self.calls = []          # (name, args, kwargs)
        self.imports = []        # module names imported while the test ran
        self.logged_in = True
        self.cost = 1.25
        self.shots_by_result = []

    def names(self):
        return [c[0] for c in self.calls]

    def called(self, name):
        return [c for c in self.calls if c[0] == name]


def _build_fake(rec):
    qnx = types.ModuleType("qnexus")
    models = types.ModuleType("qnexus.models")

    class QuantinuumConfig:
        def __init__(self, *args, **kwargs):
            assert not args, "QuantinuumConfig is expected to be built from keyword arguments"
            self.kwargs = dict(kwargs)
            rec.calls.append(("QuantinuumConfig", args, dict(kwargs)))

        def __getattr__(self, k):
            kw = self.__dict__.get("kwargs", {})
            if k in kw:
                return kw[k]
            raise AttributeError(k)

    def rec_fn(name, ret):
        def f(*a, **kw):
            rec.calls.append((name, a, kw))
            return ret(*a, **kw) if callable(ret) else ret
        return f

    project = _Obj(name="fake-project", kind="project")
    job = _Obj(id="job-123", kind="job")
    rec.project, rec.job = project, job

    def upload(*a, **kw):
        return _Obj(kind="circuit_ref", circuit=kw.get("circuit", a[0] if a else None))

    def results(*a, **kw):
        out = []
        for arr in rec.shots_by_result:
            def dl(arr=arr):
                def get_shots(*ga, **gkw):
                    rec.calls.append(("get_shots", ga, gkw))
                    return arr
                return _Obj(get_shots=get_shots)
            out.append(_Obj(download_result=dl))
        return out

    qnx.auth = _Obj(login_with_token=rec_fn("auth.login_with_token", None),
                    is_logged_in=rec_fn("auth.is_logged_in", lambda *a, **k: rec.logged_in))
    qnx.projects = _Obj(get_or_create=rec_fn("projects.get_or_create", project))
    qnx.circuits = _Obj(upload=rec_fn("circuits.upload", upload),
                        cost=rec_fn("circuits.cost", lambda *a, **k: rec.cost))
    qnx.start_execute_job = rec_fn("start_execute_job", job)
    qnx.jobs = _Obj(wait_for=rec_fn("jobs.wait_for", None), results=rec_fn("jobs.results", results))
    models.QuantinuumConfig = QuantinuumConfig
    qnx.models = models
    qnx.QuantinuumConfig = QuantinuumConfig
    return qnx, models


@pytest.fixture
def fake_qnexus(monkeypatch):
    rec = _Recorder()
    qnx, models = _build_fake(rec)
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


def _circ(n=3):
    c = Circuit(n, n)
    c.ZZPhase(0.5, 0, 1)
    for q in range(n):
        c.Measure(q, q)
    return c


GOOD = {"project": "tfim-test", "device": "H2-1E", "allow_hardware": True, "approval": NEXUS_APPROVAL,
            "max_cost_hqc": 10.0, "estimated_hqc": 7.5}


def _read_ledger(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


# =========================================================================== constants / config
def test_device_constants():
    assert LE_DEVICES == {"H2-1LE", "H2-2LE"}
    assert SC_DEVICES == {"H2-1SC", "H2-2SC"}
    assert E_DEVICES == {"H2-1E", "H2-2E"}
    assert HW_DEVICES == {"H2-1", "H2-2"}
    assert issubclass(DeviceRefused, PermissionError)


def test_config_hardware_defaults():
    from config import CONFIG
    hw = CONFIG.hardware
    assert hw.allow_hardware is False
    assert hw.allow_real_hardware is False
    assert hw.no_opt is True
    assert hw.le_device == "H2-1LE"
    assert hw.syntax_checker == "H2-1SC"
    assert hw.emulator_device == "H2-1E"
    assert hw.max_cost_hqc == 0


# =========================================================================== import hygiene
def test_import_does_not_import_qnexus_subprocess():
    code = (f"import sys; sys.path.insert(0, {str(ROOT)!r}); import src.h2_backend; "
            "print(sorted(m for m in sys.modules if m.split('.')[0] == 'qnexus'))")
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False,
                         cwd=str(ROOT), timeout=300)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().splitlines()[-1] == "[]"


def test_qnexus_referenced_only_inside_allowed_functions():
    allowed = {"syntax_check", "submit_nexus", "fetch_nexus", "_nexus_login"}
    tree = ast.parse((ROOT / "src" / "h2_backend.py").read_text())

    def is_qnx(name):
        return (name or "").split(".")[0] == "qnexus"

    def refs(node):
        hits = []
        for n in ast.walk(node):
            hit = (
                (isinstance(n, ast.Import) and any(is_qnx(a.name) for a in n.names))
                or (isinstance(n, ast.ImportFrom) and is_qnx(n.module))
                or (isinstance(n, ast.Name) and n.id == "qnexus")
                # importlib.import_module("qnexus") and the like
                or (isinstance(n, ast.Constant) and isinstance(n.value, str) and is_qnx(n.value))
            )
            if hit:
                hits.append(n.lineno)
        return hits

    seen_inside = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in allowed:
            seen_inside += refs(node)
            continue
        assert not refs(node), f"qnexus referenced outside {sorted(allowed)} at lines {refs(node)}"
    assert seen_inside, "qnexus must be imported lazily inside the Nexus functions"


# =========================================================================== pecos params / run_le gates
def test_pecos_error_params_exact():
    d = pecos_error_params(Noise(p2=0.015, p1=0.003, pm=0.002, p_init=0.001))
    assert set(d) == {"p1", "p2", "p_meas", "p_init"}
    assert d["p1"] == pytest.approx(0.003 * 2 / 3, rel=1e-12)
    assert d["p2"] == pytest.approx(0.015 * 4 / 5, rel=1e-12)
    assert d["p_meas"] == pytest.approx(0.002, rel=1e-12)
    assert d["p_init"] == pytest.approx(0.001, rel=1e-12)
    with pytest.raises(ValueError):
        pecos_error_params(Noise(p2=0.01, p_idle=0.001))


@pytest.mark.parametrize("device", ["H2-1E", "H2-2E", "H2-1SC", "H2-2SC", "H2-1", "H2-2", "bogus"])
def test_run_le_refuses_non_le_devices(device):
    c = Circuit(1, 1).Measure(0, 0)
    with pytest.raises(DeviceRefused):
        run_le(c, [Bit(0)], 10, 0, device=device)


def test_run_le_refuses_over_30_qubits():
    c = Circuit(31, 1).Measure(0, 0)
    with pytest.raises(MemoryError):
        run_le(c, [Bit(0)], 10, 0)


# =========================================================================== F. noise calibration (emulator)
SHOTS = 20000


def _p_one(out):
    return float(np.mean(out.any(axis=1)))


def _assert_binom(p_hat, p, n=SHOTS):
    assert abs(p_hat - p) <= NSIG * np.sqrt(p * (1 - p) / n), (p_hat, p)


def test_two_qubit_noise_convention_le():
    """ZZPhase(1.0) on |00> then measure; p2 = 0.1 is the TOTAL probability of a uniform
    non-identity 2q Pauli: 12 of the 15 have an X or Y component and flip a bit, so
    P(any bit 1) = 0.8 p2 = 0.08. PECOS' own 5/4 rescaling would give 0.10 instead."""
    pytest.importorskip("pytket_pecos")
    c = Circuit(2, 2)
    c.ZZPhase(1.0, 0, 1)
    c.Measure(0, 0).Measure(1, 1)
    out = run_le(c, [Bit(0), Bit(1)], SHOTS, 1, noise=Noise(p2=0.1))
    assert out.shape == (SHOTS, 2) and out.dtype == np.int8
    p_hat = _p_one(out)
    _assert_binom(p_hat, 0.08)
    assert abs(p_hat - 0.10) > NSIG * np.sqrt(0.1 * 0.9 / SHOTS)


def test_measurement_noise_le():
    pytest.importorskip("pytket_pecos")
    c = Circuit(1, 1).Measure(0, 0)
    out = run_le(c, [Bit(0)], SHOTS, 2, noise=Noise(pm=0.1))
    _assert_binom(float(out.mean()), 0.1)


def test_one_qubit_noise_le():
    """Two native X gates (PhasedX(1, 0)) = identity, p1 = 0.1 total per gate, uniform X/Y/Z.
    Per gate a bit flip (X or Y) has q = 2p1/3; a flip after gate 1 stays a flip through gate 2
    (X conjugates X->X, Y->-Y), so P(measured 1) = 2 q (1 - q) = 0.12444..."""
    pytest.importorskip("pytket_pecos")
    p1 = 0.1
    q = 2 * p1 / 3
    c = Circuit(1, 1)
    c.add_gate(OpType.PhasedX, [1.0, 0.0], [0])
    c.add_gate(OpType.PhasedX, [1.0, 0.0], [0])
    c.Measure(0, 0)
    out = run_le(c, [Bit(0)], SHOTS, 3, noise=Noise(p1=p1))
    _assert_binom(float(out.mean()), 2 * q * (1 - q))


def _coin():
    c = Circuit(2, 2)
    c.add_gate(OpType.PhasedX, [0.5, 0.0], [0])      # |0> -> 50/50
    c.add_gate(OpType.PhasedX, [0.5, 0.0], [1])
    c.ZZPhase(0.3, 0, 1)
    c.Measure(0, 0).Measure(1, 1)
    return c


def test_zero_noise_and_seeds_le():
    pytest.importorskip("pytket_pecos")
    c, cb = _coin(), [Bit(0), Bit(1)]
    a = run_le(c, cb, 300, 7)
    b = run_le(c, cb, 300, 7)
    z = run_le(c, cb, 300, 7, noise=Noise())
    d = run_le(c, cb, 300, 8)
    assert a.dtype == np.int8 and a.shape == (300, 2)
    assert np.array_equal(a, b)            # same seed -> identical bits
    assert np.array_equal(a, z)            # Noise() (zero) == the noiseless path
    assert not np.array_equal(a, d)        # 600 fair coins: equal by chance w.p. 2^-600
    assert 0.35 < a[:, 0].mean() < 0.65    # sanity: it is a coin (4 sigma ~ 0.115 at n=300)


# =========================================================================== G. Nexus gates (fake qnexus)
def test_nexus_login_with_token(fake_qnexus):
    h2_backend._nexus_login()
    assert fake_qnexus.called("auth.login_with_token")
    c = fake_qnexus.called("auth.login_with_token")[0]
    assert "fake-token" in list(c[1]) + list(c[2].values())


def test_nexus_login_requires_session_without_token(fake_qnexus, monkeypatch):
    monkeypatch.delenv("NEXUS_REFRESH_TOKEN", raising=False)
    fake_qnexus.logged_in = False
    with pytest.raises(RuntimeError):
        h2_backend._nexus_login()
    fake_qnexus.logged_in = True
    h2_backend._nexus_login()
    assert not fake_qnexus.called("auth.login_with_token")


REFUSALS = [
    ({"device": "H2-1SC"}, DeviceRefused),
    ({"device": "H2-2SC"}, DeviceRefused),
    ({"device": "H2-1SC", "allow_real_hardware": True}, DeviceRefused),
    ({"device": "H2-1LE"}, DeviceRefused),
    ({"device": "H2-2LE"}, DeviceRefused),
    ({"device": "H2-1"}, DeviceRefused),
    ({"device": "H2-2"}, DeviceRefused),
    ({"device": "bogus"}, DeviceRefused),
    ({"device": "bogus", "allow_real_hardware": True}, DeviceRefused),
    ({"allow_hardware": False}, PermissionError),
    ({"device": "H2-1", "allow_real_hardware": True, "allow_hardware": False}, PermissionError),
    ({"approval": None}, PermissionError),
    ({"approval": "yes"}, PermissionError),
    ({"approval": NEXUS_APPROVAL + " "}, PermissionError),
    ({"max_cost_hqc": 0.0}, ValueError),
    ({"max_cost_hqc": -1.0}, ValueError),
    ({"estimated_hqc": 10.5}, ValueError),
]


@pytest.mark.parametrize("override,exc", REFUSALS)
def test_submit_nexus_refusals_before_qnexus(fake_qnexus, tmp_path, override, exc):
    kw = {**GOOD, **override}
    led = tmp_path / "ledger.jsonl"
    with pytest.raises(exc):
        submit_nexus([_circ()], 100, ledger=led, **kw)
    assert fake_qnexus.calls == []
    assert fake_qnexus.imports == []
    assert not led.exists()


def test_submit_nexus_refuses_over_56_qubits(fake_qnexus, tmp_path):
    led = tmp_path / "ledger.jsonl"
    with pytest.raises(ValueError):
        submit_nexus([_circ(3), Circuit(57)], 100, ledger=led, **GOOD)
    assert fake_qnexus.calls == [] and fake_qnexus.imports == []
    assert not led.exists()


def test_submit_nexus_all_gates_pass(fake_qnexus, tmp_path):
    led = tmp_path / "ledger.jsonl"
    circs = [_circ(3), _circ(4)]
    job = submit_nexus(circs, 100, ledger=led, **GOOD)
    assert job is fake_qnexus.job
    proj = fake_qnexus.called("projects.get_or_create")
    assert proj and proj[0][2].get("name") == "tfim-test"
    sj = fake_qnexus.called("start_execute_job")
    assert len(sj) == 1
    kw = sj[0][2]
    progs = list(kw["programs"])
    assert len(progs) == 2
    # spec: programs=list(circuits); a CircuitRef from circuits.upload of the same circuit is also
    # accepted (real qnexus types ExecutionProgram as CircuitRef | HUGRRef | QIRRef).
    for p, c in zip(progs, circs):
        assert p is c or getattr(p, "circuit", None) is c
    assert kw["n_shots"] == [100, 100]
    assert kw["max_cost"] == 10.0
    assert kw["project"] is fake_qnexus.project
    cfg = kw["backend_config"]
    assert cfg.kwargs["device_name"] == "H2-1E"
    assert cfg.kwargs["no_opt"] is True
    assert cfg.kwargs["max_cost"] == 10.0
    # no configuration was ever built for a non-E device
    assert all(c[2].get("device_name") == "H2-1E" for c in fake_qnexus.called("QuantinuumConfig"))
    lines = _read_ledger(led)
    assert len(lines) == 1
    ln = lines[0]
    assert ln["tier"] == "E" and ln["device"] == "H2-1E" and ln["shots"] == 100
    assert ln["estimated_hqc"] == 7.5 and ln["max_cost_hqc"] == 10.0
    assert ln["job_id"] == "job-123"


def test_submit_nexus_estimate_equal_to_cap_allowed(fake_qnexus, tmp_path):
    submit_nexus([_circ()], 10, ledger=tmp_path / "l.jsonl", **{**GOOD, "estimated_hqc": 10.0})
    assert len(fake_qnexus.called("start_execute_job")) == 1


def test_submit_nexus_real_hardware_needs_explicit_flag(fake_qnexus, tmp_path):
    led = tmp_path / "ledger.jsonl"
    submit_nexus([_circ()], 10, ledger=led, allow_real_hardware=True, **{**GOOD, "device": "H2-1"})
    kw = fake_qnexus.called("start_execute_job")[0][2]
    assert kw["backend_config"].kwargs["device_name"] == "H2-1"
    assert _read_ledger(led)[0]["tier"] == "HW"


@pytest.mark.parametrize("device", ALL_NON_SC)
def test_syntax_check_refuses_non_sc(fake_qnexus, tmp_path, device):
    led = tmp_path / "ledger.jsonl"
    with pytest.raises(DeviceRefused):
        syntax_check([_circ()], 100, "tfim-test", device=device, ledger=led)
    assert fake_qnexus.calls == [] and fake_qnexus.imports == []
    assert not led.exists()


@pytest.mark.parametrize("device", ["H2-1SC", "H2-2SC"])
def test_syntax_check_sc_path(fake_qnexus, tmp_path, device):
    led = tmp_path / "ledger.jsonl"
    circs = [_circ(3), _circ(5)]
    out = syntax_check(circs, 100, "tfim-test", device=device, ledger=led)
    assert fake_qnexus.called("projects.get_or_create")[0][2].get("name") == "tfim-test"
    ups = fake_qnexus.called("circuits.upload")
    assert [u[2].get("circuit") for u in ups] == circs
    costs = fake_qnexus.called("circuits.cost")
    assert len(costs) == 2
    for (_, _, kw), c in zip(costs, circs):
        assert kw["syntax_checker"] == device
        assert kw["n_shots"] == 100
        assert kw["circuit_ref"].circuit is c
        assert kw["backend_config"].kwargs["device_name"] == device
        assert kw["backend_config"].kwargs["no_opt"] is True
        assert kw["project"] is fake_qnexus.project
    for c in fake_qnexus.called("QuantinuumConfig"):
        assert c[2].get("device_name") in SC_DEVICES          # never an E (or other) name
    assert not fake_qnexus.called("start_execute_job")
    assert len(out) == 2
    for d, c in zip(out, circs):
        assert d["tier"] == "SC" and d["device"] == device and d["shots"] == 100
        assert d["quoted_hqc"] == 1.25 and d["n_qubits"] == c.n_qubits
        assert "circuit" in d
    lines = _read_ledger(led)
    assert len(lines) == 2
    for ln, d in zip(lines, out):
        assert "time" in ln
        assert {k: v for k, v in ln.items() if k != "time"} == json.loads(json.dumps(d))


def test_fetch_nexus_mocked(fake_qnexus):
    a = np.array([[0, 1], [1, 1]], dtype=np.int8)
    b = np.array([[1, 0, 0]], dtype=np.int8)
    fake_qnexus.shots_by_result = [a, b]
    cb = [[Bit(0), Bit(1)], [Bit(0), Bit(1), Bit(2)]]
    out = h2_backend.fetch_nexus(fake_qnexus.job, cb, timeout=5)
    assert fake_qnexus.called("jobs.wait_for") and fake_qnexus.called("jobs.results")
    assert len(out) == 2
    assert np.array_equal(out[0], a) and np.array_equal(out[1], b)
    gs = fake_qnexus.called("get_shots")
    assert [list(g[2].get("cbits", g[1][0] if g[1] else None)) for g in gs] == cb
    assert not fake_qnexus.called("start_execute_job")

