"""FROZEN tests (test-first, blind) for src/h2_driver.py: the H2 run driver and its CLI.

No test here touches the network or spends HQC. Nexus is replaced by a FAKE `qnexus` module (and
`qnexus.models.QuantinuumConfig`) injected into sys.modules, in the style of tests/test_h2_backend.py;
every call and every import of `qnexus` while a test runs is recorded. Where the interface allows,
fake quote_fn / submit_fn / hosted_fn callables are passed and every call is logged in order, so a
refusal can be shown to happen BEFORE anything is called. The Nexus ledger is redirected to tmp_path
in every test so no test can write to runs/.

src.h2_driver is imported inside the `drv` fixture so this file collects cleanly before the module
exists (every test then errors on the missing module).

Any HQC number here is an OFFLINE estimate or a FAKE quote, never an H2 result.
"""

import builtins
import importlib
import math
import subprocess
import sys
import types
from dataclasses import replace
from pathlib import Path

import pytest
from pytket import Circuit

from config import CONFIG
from src import h2_backend
from src.backends_qc import NEXUS_APPROVAL

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_GROUPS = ("G1", "Q1", "Q1-alt", "Q4", "bare-2x2-step1")


# =========================================================================== fake qnexus
class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _Recorder:
    def __init__(self):
        self.calls = []  # (name, args, kwargs)
        self.imports = []  # qnexus module names imported while the test ran
        self.logged_in = True
        self.cost = 1.25

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

    qnx.auth = _Obj(
        login_with_token=rec_fn("auth.login_with_token", None),
        is_logged_in=rec_fn("auth.is_logged_in", lambda *a, **k: rec.logged_in),
    )
    qnx.projects = _Obj(get_or_create=rec_fn("projects.get_or_create", project))
    qnx.circuits = _Obj(
        upload=rec_fn("circuits.upload", upload),
        cost=rec_fn("circuits.cost", lambda *a, **k: rec.cost),
    )
    qnx.start_execute_job = rec_fn("start_execute_job", job)
    qnx.jobs = _Obj(wait_for=rec_fn("jobs.wait_for", None), results=rec_fn("jobs.results", []))
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


@pytest.fixture(autouse=True)
def _ledger_to_tmp(monkeypatch, tmp_path):
    """Safety: any default Nexus function a test reaches writes its ledger to tmp, not runs/."""
    monkeypatch.setattr(h2_backend, "LEDGER", tmp_path / "ledger.jsonl")


@pytest.fixture
def drv():
    return importlib.import_module("src.h2_driver")


# =========================================================================== helpers
class _Log:
    """Ordered log of every fake fn call: (kind, circuits, shots, kwargs)."""

    def __init__(self, quotes=None, fail_submit=None):
        self.events = []
        self.quotes = quotes or {}  # id(circuit) -> quoted_hqc
        self.fail_submit = fail_submit

    def kinds(self):
        return [e[0] for e in self.events]

    def of(self, kind):
        return [e for e in self.events if e[0] == kind]

    def quote_fn(self, circuits, shots, **kw):
        circuits = list(circuits)
        self.events.append(("quote", circuits, shots, kw))
        return [{"quoted_hqc": self.quotes.get(id(c), 1.0), "shots": shots} for c in circuits]

    def submit_fn(self, circuits, shots, **kw):
        circuits = list(circuits)
        self.events.append(("submit", circuits, shots, kw))
        if self.fail_submit is not None:
            raise self.fail_submit
        return f"emu-job-{len(self.of('submit'))}"

    def hosted_fn(self, circuits, shots, **kw):
        circuits = list(circuits)
        self.events.append(("hosted", circuits, shots, kw))
        return f"hosted-job-{len(self.of('hosted'))}"

    def fns(self):
        return {"quote_fn": self.quote_fn, "submit_fn": self.submit_fn, "hosted_fn": self.hosted_fn}


def _never(*a, **k):
    raise AssertionError("this function must not be called")


NEVER = {"quote_fn": _never, "submit_fn": _never, "hosted_fn": _never}


def _qc(n, tag=0):
    c = Circuit(n, n)
    c.Rz(0.1 * (tag + 1), 0)
    c.ZZPhase(0.25, 0, 1)
    for q in range(n):
        c.Measure(q, q)
    return c


def _hand_plan(drv):
    """Three items, two distinct shot counts (100, 100, 50), widths 3, 4, 5; estimates 6.0 + 7.0 +
    5.5 = 18.5. Per-shot: 0.06, 0.07, 0.11. Quotes (fake) 8 + 9 + 4 = 21 differ from the estimates
    so a driver that forwards the offline estimate instead of the server quote is caught."""
    a, b, c = _qc(3, 0), _qc(4, 1), _qc(5, 2)
    items = [
        drv.PlannedCircuit(label="A", group="hand", shots=100, circuit=a, n_qubits=3,
                           estimate_hqc=6.0, meta={}),
        drv.PlannedCircuit(label="B", group="hand", shots=100, circuit=b, n_qubits=4,
                           estimate_hqc=7.0, meta={}),
        drv.PlannedCircuit(label="C", group="hand", shots=50, circuit=c, n_qubits=5,
                           estimate_hqc=5.5, meta={}),
    ]
    plan = drv.Plan(group="hand", items=items)
    quotes = {id(a): 8.0, id(b): 9.0, id(c): 4.0}
    return plan, quotes


def _emu_hw(**kw):
    """A hardware config on which the emulator gates all pass for _hand_plan with approval."""
    base = {
        "nexus_tier": "emulator",
        "allow_hardware": True,
        "max_cost_hqc": 25.0,
        "emulator_device": "H2-2E",
        "syntax_checker": "H2-2SC",
        "nexus_project": "tfim-test",
        "emulator_max_qubits": 5,
        "max_shots_per_job": 100,
        "max_hqc_per_shot": 0.11,
    }
    base.update(kw)
    return replace(CONFIG.hardware, **base)


@pytest.fixture(scope="module")
def bare_plan():
    d = importlib.import_module("src.h2_driver")
    return d.build_plan("bare-2x2-step1", 1000)


@pytest.fixture(scope="module")
def g1_plan():
    d = importlib.import_module("src.h2_driver")
    return d.build_plan("G1", 1003)


# =========================================================================== module surface
def test_tiers_and_refusal_type(drv):
    """Oracle: SPEC B constants -- the four tiers in order, refusals are PermissionErrors."""
    assert tuple(drv.TIERS) == ("dry-run", "sc", "hosted-le", "emulator")
    assert issubclass(drv.DriverRefused, PermissionError)


def test_group_names_include_required(drv):
    """Oracle: SPEC B -- group_names() lists at least the five named groups."""
    names = drv.group_names()
    for g in REQUIRED_GROUPS:
        assert g in names


def test_plan_properties_on_hand_plan(drv):
    """Oracle: hand sums -- total 6+7+5.5 = 18.5 and max width 5 (not the first or last-listed)."""
    plan, _ = _hand_plan(drv)
    # reorder so the widest is in the middle: max must not be first/last item's width
    plan.items = [plan.items[0], plan.items[2], plan.items[1]]
    assert plan.total_estimate_hqc == pytest.approx(18.5, abs=1e-12)
    assert plan.max_qubits == 5


# =========================================================================== build_plan
@pytest.mark.parametrize("group", ["nope", "g1", "Q1-draft-x", ""])
def test_build_plan_unknown_group_refused(drv, group):
    """Oracle: SPEC B -- an unknown group name raises DriverRefused."""
    with pytest.raises(drv.DriverRefused):
        drv.build_plan(group, 1000)


@pytest.mark.parametrize("shots", [0, -1, True, 1.5, "1000", 10001])
def test_build_plan_bad_shots_refused(drv, shots):
    """Oracle: SPEC B -- shots must be an int (not bool) with 1 <= shots <= max_shots_per_job."""
    with pytest.raises(drv.DriverRefused):
        drv.build_plan("bare-2x2-step1", shots)


def test_build_plan_shot_cap_read_from_hw(drv):
    """Oracle: SPEC B -- the cap is hw.max_shots_per_job, not a constant: 501 > 500 refused, 500 ok."""
    hw = replace(CONFIG.hardware, max_shots_per_job=500)
    with pytest.raises(drv.DriverRefused):
        drv.build_plan("bare-2x2-step1", 501, hw=hw)
    assert drv.build_plan("bare-2x2-step1", 500, hw=hw).items[0].shots == 500
    assert drv.build_plan("bare-2x2-step1", 10000).items[0].shots == 10000  # default cap inclusive


def test_build_plan_is_offline(drv, fake_qnexus):
    """Oracle: fake-qnexus import recorder -- building a plan imports and calls no qnexus."""
    drv.build_plan("bare-2x2-step1", 100)
    assert fake_qnexus.imports == [] and fake_qnexus.calls == []


def test_bare_step1_is_one_compiled_bare_2x2_circuit(drv, bare_plan):
    """Oracle: independent rebuild -- bare_h2_circuit(2x2, 1 step) compiled at level 0 has the same
    native counts; the item is valid for the offline H2 backend; 4 qubits, 4 measurements."""
    from src.encoded_tfim import IcebergTFIM
    from src.h2_circuits import bare_h2_circuit, compile_for_h2, native_counts

    E = CONFIG.encoded
    assert len(bare_plan.items) == 1
    it = bare_plan.items[0]
    assert it.shots == 1000 and it.n_qubits == 4 and it.circuit.n_qubits == 4
    assert bare_plan.max_qubits == 4
    spec = IcebergTFIM(2, 2, "periodic", E.J, E.h, E.dt, E.theta, 1)
    backend = h2_backend.offline_compile_backend(CONFIG.hardware.le_device)
    ref = compile_for_h2(bare_h2_circuit(spec, 1)[0], backend)
    assert native_counts(it.circuit) == native_counts(ref)
    assert native_counts(it.circuit)["nmeas"] == 4
    assert backend.valid_circuit(it.circuit)


def test_estimates_are_rz_free_formula(drv, bare_plan, g1_plan):
    """Oracle: hqc_estimate(native_counts(circuit), item.shots, count_rz=False) recomputed per item;
    and the Rz-counting value differs (discriminating: the circuits contain Rz)."""
    from src.h2_circuits import hqc_estimate, native_counts

    some_rz = False
    for plan in (bare_plan, g1_plan):
        for it in plan.items:
            nc = native_counts(it.circuit)
            assert it.estimate_hqc == pytest.approx(hqc_estimate(nc, it.shots, count_rz=False),
                                                    rel=1e-12)
            if nc["nrz"]:
                some_rz = True
                assert it.estimate_hqc < hqc_estimate(nc, it.shots, count_rz=True)
        assert plan.total_estimate_hqc == pytest.approx(sum(i.estimate_hqc for i in plan.items))
    assert some_rz


def test_g1_rc_split(drv, g1_plan):
    """Oracle: SPEC B RC rule -- with shots=1003 and k=rc_instances, RC items get 1003//k (floor),
    in whole groups of k; the non-RC points keep all 1003 shots; nothing gets any other count."""
    k = CONFIG.encoded.rc_instances
    per = 1003 // k
    assert k > 1 and per != 1003
    counts = [it.shots for it in g1_plan.items]
    assert set(counts) <= {1003, per}
    n_rc = counts.count(per)
    assert n_rc > 0 and n_rc % k == 0
    assert counts.count(1003) > 0
    assert all(it.group == "G1" for it in g1_plan.items)
    assert g1_plan.max_qubits == max(it.circuit.n_qubits for it in g1_plan.items)
    assert all(it.n_qubits == it.circuit.n_qubits for it in g1_plan.items)
    # twirled instances are different circuits (not k copies of one)
    rc_items = [it for it in g1_plan.items if it.shots == per]
    assert len({str(it.circuit.get_commands()) for it in rc_items[:k]}) > 1


def test_g1_circuits_are_h2_native(drv, g1_plan):
    """Oracle: the offline H2 backend's own predicates (valid_circuit) on every compiled item."""
    backend = h2_backend.offline_compile_backend(CONFIG.hardware.le_device)
    assert all(backend.valid_circuit(it.circuit) for it in g1_plan.items)


# =========================================================================== execute: dry-run
def test_dry_run_calls_nothing(drv, fake_qnexus):
    """Oracle: SPEC B dry-run dict from hand sums; fns that raise prove none was called; no qnexus."""
    plan, _ = _hand_plan(drv)
    out = drv.execute(plan, **NEVER)
    assert out["tier"] == "dry-run" and out["submitted"] is False
    assert out["estimate_hqc"] == pytest.approx(18.5)
    assert out["n_circuits"] == 3 and out["max_qubits"] == 5
    assert fake_qnexus.imports == [] and fake_qnexus.calls == []


def test_explicit_dry_run_beats_emulator_config(drv, fake_qnexus):
    """Oracle: SPEC B step-down rule -- fully-gated emulator config + approval, tier='dry-run' -> dry run."""
    plan, _ = _hand_plan(drv)
    out = drv.execute(plan, hw=_emu_hw(), tier="dry-run", approval=NEXUS_APPROVAL, **NEVER)
    assert out["tier"] == "dry-run" and out["submitted"] is False
    assert fake_qnexus.imports == [] and fake_qnexus.calls == []


@pytest.mark.parametrize("tier", ["E", "Emulator", "hardware", "H2-1E", "le", ""])
def test_unknown_tier_refused(drv, fake_qnexus, tier):
    """Oracle: SPEC B -- any tier outside TIERS raises DriverRefused and calls nothing."""
    plan, _ = _hand_plan(drv)
    with pytest.raises(drv.DriverRefused):
        drv.execute(plan, hw=_emu_hw(), tier=tier, approval=NEXUS_APPROVAL, **NEVER)
    assert fake_qnexus.imports == []


# =========================================================================== execute: sc
def test_sc_quotes_per_shot_count_in_plan_order(drv, fake_qnexus):
    """Oracle: hand plan -- two quote calls ([A,B]@100 then [C]@50), device = hw.syntax_checker
    (H2-2SC, not the default), sum of fake quotes 21; submit/hosted never called."""
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    hw = replace(CONFIG.hardware, nexus_project="proj-x", syntax_checker="H2-2SC")
    out = drv.execute(plan, hw=hw, tier="sc", quote_fn=log.quote_fn, submit_fn=_never,
                      hosted_fn=_never)
    assert log.kinds() == ["quote", "quote"]
    (_, c1, s1, k1), (_, c2, s2, k2) = log.events
    assert (s1, s2) == (100, 50)
    assert c1 == [plan.items[0].circuit, plan.items[1].circuit] and c2 == [plan.items[2].circuit]
    for kw in (k1, k2):
        assert kw["project"] == "proj-x" and kw["device"] == "H2-2SC"
    assert out["tier"] == "sc" and out["submitted"] is False
    assert out["quoted_hqc"] == pytest.approx(21.0)
    assert out["estimate_hqc"] == pytest.approx(18.5)
    assert "quotes" in out
    assert fake_qnexus.imports == []


def test_sc_needs_project(drv):
    """Oracle: SPEC B -- tier 'sc' with nexus_project '' refuses before quoting."""
    plan, _ = _hand_plan(drv)
    with pytest.raises(drv.DriverRefused):
        drv.execute(plan, hw=replace(CONFIG.hardware, nexus_project=""), tier="sc", **NEVER)


def test_sc_default_quote_fn_is_syntax_check(drv, fake_qnexus):
    """Oracle: fake qnexus -- the default quote path costs each circuit on the SC (1.25 each)."""
    plan, _ = _hand_plan(drv)
    hw = replace(CONFIG.hardware, nexus_project="proj-x", syntax_checker="H2-1SC")
    out = drv.execute(plan, hw=hw, tier="sc", submit_fn=_never, hosted_fn=_never)
    assert len(fake_qnexus.called("circuits.cost")) == 3
    assert out["quoted_hqc"] == pytest.approx(3 * 1.25)
    assert fake_qnexus.called("start_execute_job") == []
    assert all(c[2]["device_name"] == "H2-1SC" for c in fake_qnexus.called("QuantinuumConfig"))


# =========================================================================== execute: hosted-le
def test_hosted_le_calls_hosted_fn_per_shot_count(drv, fake_qnexus):
    """Oracle: hand plan -- hosted_fn([A,B],100) then ([C],50) on hw.le_device; spent 0; no approval."""
    plan, _ = _hand_plan(drv)
    log = _Log()
    hw = replace(CONFIG.hardware, nexus_project="proj-x", le_device="H2-2LE")
    out = drv.execute(plan, hw=hw, tier="hosted-le", quote_fn=_never, submit_fn=_never,
                      hosted_fn=log.hosted_fn)
    assert log.kinds() == ["hosted", "hosted"]
    assert [e[2] for e in log.events] == [100, 50]
    assert log.events[0][1] == [plan.items[0].circuit, plan.items[1].circuit]
    assert all(e[3]["device"] == "H2-2LE" and e[3]["project"] == "proj-x" for e in log.events)
    assert out["tier"] == "hosted-le" and out["submitted"] is True
    assert out["spent_hqc"] == 0.0
    assert out["jobs"] == ["hosted-job-1", "hosted-job-2"]


def test_hosted_le_width_cap_20(drv):
    """Oracle: Nexus-hosted 20-qubit cap -- a 21-qubit item refuses before any call; 20 passes."""
    log = _Log()
    hw = replace(CONFIG.hardware, nexus_project="p")
    for n, ok in [(21, False), (20, True)]:
        it = drv.PlannedCircuit(label="w", group="hand", shots=10, circuit=_qc(n), n_qubits=n,
                                estimate_hqc=5.1, meta={})
        plan = drv.Plan(group="hand", items=[it])
        if ok:
            drv.execute(plan, hw=hw, tier="hosted-le", hosted_fn=log.hosted_fn, quote_fn=_never,
                        submit_fn=_never)
            assert log.kinds() == ["hosted"]
        else:
            with pytest.raises(drv.DriverRefused):
                drv.execute(plan, hw=hw, tier="hosted-le", **NEVER)


def test_hosted_le_needs_project(drv):
    """Oracle: SPEC B -- hosted-le with nexus_project '' refuses before calling anything."""
    plan, _ = _hand_plan(drv)
    with pytest.raises(drv.DriverRefused):
        drv.execute(plan, hw=replace(CONFIG.hardware, nexus_project=""), tier="hosted-le",
                    **NEVER)


def test_hosted_le_default_fn_uses_fake_qnexus(drv, fake_qnexus):
    """Oracle: fake qnexus -- default hosted path starts a job on the LE device with no max_cost."""
    plan, _ = _hand_plan(drv)
    hw = replace(CONFIG.hardware, nexus_project="proj-x")
    out = drv.execute(plan, hw=hw, tier="hosted-le", quote_fn=_never, submit_fn=_never)
    jobs = fake_qnexus.called("start_execute_job")
    assert len(jobs) == 2 and out["spent_hqc"] == 0.0
    assert all(c[2]["device_name"] == "H2-1LE" for c in fake_qnexus.called("QuantinuumConfig"))
    assert fake_qnexus.called("circuits.cost") == []


# =========================================================================== execute: emulator
def test_emulator_happy_path_quotes_then_submits_server_quote(drv, fake_qnexus):
    """Oracle: hand plan + fake quotes -- all quotes precede all submits; estimated_hqc per call is
    the SERVER quote (17, 4; offline would be 13, 5.5); same circuit objects quoted and submitted."""
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    hw = _emu_hw()
    out = drv.execute(plan, hw=hw, approval=NEXUS_APPROVAL, quote_fn=log.quote_fn,
                      submit_fn=log.submit_fn, hosted_fn=_never)
    kinds = log.kinds()
    assert kinds.count("quote") == 2 and kinds.count("submit") == 2
    assert kinds.index("submit") > max(i for i, k in enumerate(kinds) if k == "quote")
    for e in log.of("quote"):
        assert e[3]["device"] == "H2-2SC" and e[3]["project"] == "tfim-test"
    subs = log.of("submit")
    assert [s[2] for s in subs] == [100, 50]
    assert [s[3]["estimated_hqc"] for s in subs] == [pytest.approx(17.0), pytest.approx(4.0)]
    for s in subs:
        kw = s[3]
        assert kw["device"] == "H2-2E" and kw["project"] == "tfim-test"
        assert kw["allow_hardware"] is True
        assert kw["approval"] == NEXUS_APPROVAL
        assert kw["max_cost_hqc"] == 25.0
    quoted = [c for e in log.of("quote") for c in e[1]]
    submitted = [c for e in subs for c in e[1]]
    assert all(q is s for q, s in zip(quoted, submitted, strict=True))
    assert submitted == [it.circuit for it in plan.items]
    assert out["tier"] == "emulator" and out["submitted"] is True
    assert out["quoted_hqc"] == pytest.approx(21.0)
    assert out["jobs"] == ["emu-job-1", "emu-job-2"]
    assert fake_qnexus.imports == []


def test_emulator_quote_equal_to_cap_allowed(drv):
    """Oracle: SPEC B boundary -- quote_total == max_cost_hqc (21 == 21) is allowed."""
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    drv.execute(plan, hw=_emu_hw(max_cost_hqc=21.0), approval=NEXUS_APPROVAL, **log.fns())
    assert log.kinds().count("submit") == 2


def test_emulator_quote_over_cap_refused_before_submit(drv):
    """Oracle: SPEC B -- estimate 18.5 fits cap 20 but quote 21 does not: quoted, never submitted."""
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    with pytest.raises(drv.DriverRefused):
        drv.execute(plan, hw=_emu_hw(max_cost_hqc=20.0), approval=NEXUS_APPROVAL, **log.fns())
    assert "submit" not in log.kinds() and "quote" in log.kinds()


@pytest.mark.parametrize("bad", [float("nan"), 0.0, -3.0, float("inf"), None])
def test_emulator_bad_quote_refused(drv, bad):
    """Oracle: SPEC B -- any quote that is not finite and > 0 refuses before any submit."""
    plan, quotes = _hand_plan(drv)
    quotes[id(plan.items[2].circuit)] = bad
    log = _Log(quotes)
    with pytest.raises(drv.DriverRefused):
        drv.execute(plan, hw=_emu_hw(), approval=NEXUS_APPROVAL, **log.fns())
    assert "submit" not in log.kinds()


_GATE_CASES = {
    "allow_hardware False": ({"allow_hardware": False}, NEXUS_APPROVAL),
    "allow_hardware truthy 1": ({"allow_hardware": 1}, NEXUS_APPROVAL),
    "allow_hardware 'yes'": ({"allow_hardware": "yes"}, NEXUS_APPROVAL),
    "approval None": ({}, None),
    "approval wrong": ({}, "yes"),
    "approval trailing space": ({}, NEXUS_APPROVAL + " "),
    "approval lowercase": ({}, NEXUS_APPROVAL.lower()),
    "cap zero": ({"max_cost_hqc": 0.0}, NEXUS_APPROVAL),
    "cap negative": ({"max_cost_hqc": -25.0}, NEXUS_APPROVAL),
    "cap nan": ({"max_cost_hqc": float("nan")}, NEXUS_APPROVAL),
    "cap inf": ({"max_cost_hqc": float("inf")}, NEXUS_APPROVAL),
    "device real H2-1": ({"emulator_device": "H2-1", "allow_real_hardware": True}, NEXUS_APPROVAL),
    "device real H2-2": ({"emulator_device": "H2-2", "allow_real_hardware": True}, NEXUS_APPROVAL),
    "device SC": ({"emulator_device": "H2-1SC"}, NEXUS_APPROVAL),
    "device LE": ({"emulator_device": "H2-1LE"}, NEXUS_APPROVAL),
    "device bogus": ({"emulator_device": "H2-Emulator"}, NEXUS_APPROVAL),
    "no project": ({"nexus_project": ""}, NEXUS_APPROVAL),
    "too wide": ({"emulator_max_qubits": 4}, NEXUS_APPROVAL),
    "too many shots per item": ({"max_shots_per_job": 99}, NEXUS_APPROVAL),
    "per-shot HQC over (item C 0.11 > 0.1)": ({"max_hqc_per_shot": 0.1}, NEXUS_APPROVAL),
    "estimate over cap": ({"max_cost_hqc": 18.0}, NEXUS_APPROVAL),
}


@pytest.mark.parametrize("case", list(_GATE_CASES), ids=list(_GATE_CASES))
def test_emulator_gates_refuse_before_any_call(drv, fake_qnexus, case):
    """Oracle: SPEC B gate list -- one failing gate each on an otherwise-passing config: DriverRefused,
    no fn called (not even the free quote), no qnexus imported."""
    edits, approval = _GATE_CASES[case]
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    with pytest.raises(drv.DriverRefused):
        drv.execute(plan, hw=_emu_hw(**edits), tier="emulator", approval=approval, **log.fns())
    assert log.events == []
    assert fake_qnexus.imports == [] and fake_qnexus.calls == []


def test_emulator_gate_baseline_passes(drv):
    """Oracle: control for the gate table -- the unedited _emu_hw config does submit (so each
    refusal above is caused by its one edit, and the limits are inclusive: 5 qubits, 100 shots,
    0.11 HQC/shot)."""
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    drv.execute(plan, hw=_emu_hw(), tier="emulator", approval=NEXUS_APPROVAL, **log.fns())
    assert log.kinds().count("submit") == 2


@pytest.mark.parametrize("est", [float("nan"), 0.0, float("inf")])
def test_emulator_refuses_nonfinite_or_zero_estimate(drv, est):
    """Oracle: SPEC B -- plan.total_estimate_hqc must be finite and > 0."""
    it = drv.PlannedCircuit(label="z", group="hand", shots=10, circuit=_qc(3), n_qubits=3,
                            estimate_hqc=est, meta={})
    log = _Log()
    with pytest.raises(drv.DriverRefused):
        drv.execute(drv.Plan(group="hand", items=[it]), hw=_emu_hw(), approval=NEXUS_APPROVAL,
                    **log.fns())
    assert log.events == []


def test_config_edit_alone_cannot_spend(drv, fake_qnexus):
    """Oracle: SPEC B -- nexus_tier='emulator', allow_hardware, cap and project set, approval=None
    (tier taken from config): refuses, calls nothing."""
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    with pytest.raises(drv.DriverRefused):
        drv.execute(plan, hw=_emu_hw(), **log.fns())
    assert log.events == [] and fake_qnexus.imports == []


def test_submit_exception_is_not_swallowed(drv):
    """Oracle: SPEC B -- an exception from submit_fn propagates unchanged (same object)."""

    class Boom(RuntimeError):
        pass

    err = Boom("nexus down")
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes, fail_submit=err)
    with pytest.raises(Boom) as ei:
        drv.execute(plan, hw=_emu_hw(), approval=NEXUS_APPROVAL, **log.fns())
    assert ei.value is err


def test_emulator_step_down_to_sc(drv):
    """Oracle: SPEC B step-down -- emulator config + approval, tier='sc' -> quotes only."""
    plan, quotes = _hand_plan(drv)
    log = _Log(quotes)
    out = drv.execute(plan, hw=_emu_hw(), tier="sc", approval=NEXUS_APPROVAL,
                      quote_fn=log.quote_fn, submit_fn=_never, hosted_fn=_never)
    assert out["submitted"] is False and set(log.kinds()) == {"quote"}


def test_emulator_default_fns_end_to_end_with_fake_qnexus(drv, fake_qnexus):
    """Oracle: fake qnexus -- default syntax_check quotes 1.25 x 3 = 3.75; default submit_nexus then
    starts 2 jobs on the E device with the cap as max_cost and no_opt; nothing reaches a network."""
    plan, _ = _hand_plan(drv)
    hw = _emu_hw(syntax_checker="H2-1SC", emulator_device="H2-1E")
    out = drv.execute(plan, hw=hw, approval=NEXUS_APPROVAL)
    assert out["quoted_hqc"] == pytest.approx(3.75)
    jobs = fake_qnexus.called("start_execute_job")
    assert len(jobs) == 2
    assert all(j[2]["max_cost"] == 25.0 for j in jobs)
    names = fake_qnexus.names()
    assert max(i for i, n in enumerate(names) if n == "circuits.cost") < names.index(
        "start_execute_job")
    e_cfgs = [c[2] for c in fake_qnexus.called("QuantinuumConfig") if c[2]["device_name"] == "H2-1E"]
    assert e_cfgs and all(c["no_opt"] is True and c["max_cost"] == 25.0 for c in e_cfgs)


# =========================================================================== CLI
def test_cli_dry_run_default(drv, fake_qnexus, capsys):
    """Oracle: SPEC C -- default CONFIG: exit 0, 'DRY RUN', group name and plan table; no qnexus."""
    rc = drv.cli(["--group", "bare-2x2-step1", "--shots", "1000"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "DRY RUN" in out and "bare-2x2-step1" in out
    assert "1000" in out
    assert fake_qnexus.imports == [] and fake_qnexus.calls == []


def test_cli_unknown_group_exits(drv):
    """Oracle: SPEC C -- --group outside group_names() -> SystemExit with nonzero code."""
    with pytest.raises(SystemExit) as ei:
        drv.cli(["--group", "nope"])
    assert ei.value.code not in (0, None)


def test_cli_cannot_select_emulator_tier(drv, fake_qnexus):
    """Oracle: SPEC C -- --tier choices are only free tiers; 'emulator' is an argparse error."""
    with pytest.raises(SystemExit) as ei:
        drv.cli(["--group", "bare-2x2-step1", "--tier", "emulator", "--approval", NEXUS_APPROVAL])
    assert ei.value.code not in (0, None)
    assert fake_qnexus.calls == []


def test_cli_emulator_config_without_approval_refuses(drv, fake_qnexus, monkeypatch):
    """Oracle: SPEC C -- config edited to the emulator tier, no --approval: nonzero or DriverRefused,
    and nothing is quoted or submitted on the fake Nexus."""
    cfg = replace(CONFIG, hardware=replace(
        CONFIG.hardware, nexus_tier="emulator", allow_hardware=True, max_cost_hqc=1000.0,
        nexus_project="p"))
    monkeypatch.setattr(drv, "CONFIG", cfg)
    try:
        rc = drv.cli(["--group", "bare-2x2-step1", "--shots", "100"])
    except drv.DriverRefused:
        rc = None
    assert rc is None or rc != 0
    assert fake_qnexus.called("start_execute_job") == []
    assert fake_qnexus.called("circuits.cost") == []


def test_cli_explicit_dry_run_with_emulator_config(drv, fake_qnexus, monkeypatch, capsys):
    """Oracle: SPEC B/C step-down -- emulator config + approval but --tier dry-run -> exit 0, DRY RUN."""
    cfg = replace(CONFIG, hardware=replace(
        CONFIG.hardware, nexus_tier="emulator", allow_hardware=True, max_cost_hqc=1000.0,
        nexus_project="p"))
    monkeypatch.setattr(drv, "CONFIG", cfg)
    rc = drv.cli(["--group", "bare-2x2-step1", "--shots", "100", "--tier", "dry-run",
                  "--approval", NEXUS_APPROVAL])
    assert rc == 0 and "DRY RUN" in capsys.readouterr().out
    assert fake_qnexus.calls == []


def test_script_dry_run_subprocess():
    """Oracle: SPEC C -- the script under `python -I`, from the repo root: exit 0, DRY RUN, group."""
    out = subprocess.run(
        [sys.executable, "-I", "scripts/run_h2_nexus.py", "--group", "bare-2x2-step1",
         "--shots", "1000"],
        capture_output=True, text=True, check=False, cwd=str(ROOT), timeout=600,
    )
    assert out.returncode == 0, out.stderr
    assert "DRY RUN" in out.stdout and "bare-2x2-step1" in out.stdout


def test_cli_does_not_import_qnexus_subprocess():
    """Oracle: a fresh interpreter's sys.modules -- after a default cli() dry run, no qnexus module."""
    code = (
        f"import sys; sys.path.insert(0, {str(ROOT)!r}); import src.h2_driver as d; "
        "rc = d.cli(['--group', 'bare-2x2-step1', '--shots', '1000']); "
        "print('RESULT', rc, any(m.split('.')[0] == 'qnexus' for m in sys.modules))"
    )
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True,
                         check=False, cwd=str(ROOT), timeout=600)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().splitlines()[-1] == "RESULT 0 False"


def test_hand_plan_oracle_arithmetic():
    """Oracle: arithmetic sanity of this file's own fixture numbers (guards the hand oracles)."""
    assert 6.0 + 7.0 + 5.5 == 18.5 and 8.0 + 9.0 + 4.0 == 21.0
    assert 5.5 / 50 > 0.1 and max(6.0 / 100, 7.0 / 100) < 0.1 and math.isclose(5.5 / 50, 0.11)
