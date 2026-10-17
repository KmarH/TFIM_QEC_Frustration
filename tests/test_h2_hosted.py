"""Tests for the hosted-LE tier (src/h2_hosted.py) and for submit_nexus uploading its circuits.

Written by the author after review/16 found that qnexus's `accept_circuits_for_programs` only renames
the keyword and does NOT upload, so raw pytket circuits cannot be passed as programs. Oracles: the
fake qnexus records every call; a hosted LE job must never target any non-LE device; the free-tier
claim is the docs', so a reported cost must raise.
"""

import ast
import pathlib
import sys
import types

import pytest
from pytket import Circuit

from src.backends_qc import NEXUS_APPROVAL
from src.h2_backend import DeviceRefused, submit_nexus
from src.h2_hosted import check_hosted_cost, submit_hosted_le

ROOT = pathlib.Path(__file__).resolve().parent.parent


class FakeQnx:
    def __init__(self, cost=None):
        self.calls = []
        self.cost = cost
        self.uploaded = []
        qnx = types.ModuleType("qnexus")
        qnx.auth = types.SimpleNamespace(is_logged_in=lambda: True)
        qnx.projects = types.SimpleNamespace(get_or_create=lambda **k: "proj")
        qnx.circuits = types.SimpleNamespace(upload=self._upload)
        qnx.start_execute_job = self._start
        qnx.jobs = types.SimpleNamespace(wait_for=self._wait)
        models = types.ModuleType("qnexus.models")
        models.QuantinuumConfig = lambda **k: types.SimpleNamespace(kwargs=k)
        self.modules = {"qnexus": qnx, "qnexus.models": models}

    def _upload(self, circuit, name, project):
        ref = types.SimpleNamespace(circuit=circuit, name=name)
        self.uploaded.append(ref)
        return ref

    def _start(self, **kw):
        self.calls.append(kw)
        return types.SimpleNamespace(id="job-7")

    def _wait(self, job, **k):
        return types.SimpleNamespace(cost=self.cost)


@pytest.fixture
def fake(monkeypatch):
    f = FakeQnx()
    for k, v in f.modules.items():
        monkeypatch.setitem(sys.modules, k, v)
    monkeypatch.delenv("NEXUS_REFRESH_TOKEN", raising=False)
    return f


def _c(n=2):
    c = Circuit(n)
    c.CX(0, 1)
    return c


@pytest.mark.parametrize(
    "dev", ["H2-1E", "H2-2E", "H2-1SC", "H2-1", "H2-Emulator", "bogus", "h2-1le"]
)
def test_hosted_refuses_every_non_le_device_before_qnexus(fake, tmp_path, dev):
    with pytest.raises(DeviceRefused):
        submit_hosted_le([_c()], 10, project="p", device=dev, ledger=tmp_path / "l.jsonl")
    assert fake.calls == [] and fake.uploaded == []


@pytest.mark.parametrize("shots", [0, -1, 1.5, True])
def test_hosted_refuses_bad_shots(fake, tmp_path, shots):
    with pytest.raises(ValueError):
        submit_hosted_le([_c()], shots, project="p", ledger=tmp_path / "l.jsonl")
    assert fake.calls == []


def test_hosted_refuses_over_20_qubits_and_empty(fake, tmp_path):
    with pytest.raises(ValueError):
        submit_hosted_le([_c(21)], 10, project="p", ledger=tmp_path / "l.jsonl")
    with pytest.raises(ValueError):
        submit_hosted_le([], 10, project="p", ledger=tmp_path / "l.jsonl")
    assert fake.calls == []


def test_hosted_uploads_circuits_and_passes_references(fake, tmp_path):
    cs = [_c(), _c(3)]
    job = submit_hosted_le(cs, 25, project="p", ledger=tmp_path / "l.jsonl")
    assert job.id == "job-7"
    kw = fake.calls[0]
    assert [p.circuit for p in kw["programs"]] == cs  # references, not raw circuits
    assert kw["n_shots"] == [25, 25]
    assert kw["backend_config"].kwargs == {"device_name": "H2-1LE", "no_opt": True}
    assert "max_cost" not in kw
    assert "LE-hosted" in (tmp_path / "l.jsonl").read_text()


def test_submit_nexus_also_uploads_circuits(fake, tmp_path):
    cs = [_c()]
    submit_nexus(
        cs,
        10,
        project="p",
        device="H2-1E",
        allow_hardware=True,
        approval=NEXUS_APPROVAL,
        max_cost_hqc=10.0,
        estimated_hqc=7.5,
        ledger=tmp_path / "l.jsonl",
    )
    assert [p.circuit for p in fake.calls[0]["programs"]] == cs


def test_hosted_cost_check_raises_if_any_cost_reported(monkeypatch, tmp_path):
    for cost, ok in [(None, True), (0, True), (0.0, True), (5.0, False), (0.01, False)]:
        f = FakeQnx(cost=cost)
        for k, v in f.modules.items():
            monkeypatch.setitem(sys.modules, k, v)
        job = types.SimpleNamespace(id="j")
        if ok:
            assert check_hosted_cost(job, ledger=tmp_path / "l.jsonl") == 0.0
        else:
            with pytest.raises(RuntimeError, match="STOP"):
                check_hosted_cost(job, ledger=tmp_path / "l.jsonl")


def test_hosted_module_imports_qnexus_only_inside_functions():
    tree = ast.parse((ROOT / "src" / "h2_hosted.py").read_text())

    def mentions(node):
        return any(
            (isinstance(n, ast.Import) and any(a.name.split(".")[0] == "qnexus" for a in n.names))
            or (isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "qnexus")
            for n in ast.walk(node)
        )

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            assert not mentions(node), "qnexus imported at module level"
    assert any(mentions(n) for n in tree.body if isinstance(n, ast.FunctionDef))
