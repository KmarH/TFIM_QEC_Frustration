"""src/h2_resume.py: checkpointed, resumable emulator runs that never pay twice.

Fully offline: every Nexus call is a fake that can be told to time out or fail. The plan is the
real Q3-bare / Q3-iceberg plan of src/h2_driver (circuits are built, never sent). The safety
properties pinned here:
  * a timeout while WAITING stops the run at a safe point and the resume finishes it without a
    second submission;
  * a timeout during SUBMISSION is resolved on resume by looking the job up by its deterministic
    name - adopted if it exists, submitted again only if Nexus has no such job;
  * a job that failed server-side is never resubmitted unless asked, and then under a new name;
  * the spending gates (per-run approval) run on every resume, and a changed plan is refused.
"""
import dataclasses
from types import SimpleNamespace

import numpy as np
import pytest

from config import CONFIG
from src.backends_qc import NEXUS_APPROVAL
from src.h2_driver import DriverRefused, build_plan
from src.h2_resume import (
    ResumableStop,
    is_transient,
    load_results,
    run_checkpointed,
    with_retry,
)

HW = dataclasses.replace(CONFIG.hardware, nexus_tier="emulator", allow_hardware=True,
                         max_cost_hqc=1e9, nexus_project="test-proj")
FAST = {"sleep": lambda s: None, "attempts": 3}


class JobError(Exception):
    """Stands in for qnexus.exceptions.JobError (a server-side job failure)."""


class ReadTimeout(Exception):
    """Same class name as httpx.ReadTimeout."""


class FakeNexus:
    def __init__(self):
        self.submits, self.jobs = [], {}
        self.wait_plan: dict = {}        # job_id -> list of exceptions to raise, in order
        self.submit_plan: list = []      # exceptions to raise on the next submits
        self.accept_before_raise = False

    def quote(self, circuits, shots, *, project, device):
        return [{"quoted_hqc": 2.0} for _ in circuits]

    def submit(self, circuits, shots, *, job_name, **kw):
        self.submits.append(job_name)
        if self.submit_plan:
            exc = self.submit_plan.pop(0)
            if self.accept_before_raise:          # the server took it, the reply was lost
                self.jobs[job_name] = f"id-{job_name}"
            raise exc
        self.jobs[job_name] = f"id-{job_name}"
        return SimpleNamespace(id=f"id-{job_name}")

    def find(self, name, *, project):
        return self.jobs.get(name)

    def wait(self, job_id):
        todo = self.wait_plan.get(job_id, [])
        if todo:
            raise todo.pop(0)

    def results(self, job_id, cbits_list):
        return [np.ones((3, len(cb)), dtype=np.int8) for cb in cbits_list]


@pytest.fixture(scope="module")
def plan():
    return build_plan("Q3-bare", 100, hw=HW)


def _run(plan, fake, tmp_path, run_id="r1", **kw):
    kw.setdefault("approval", NEXUS_APPROVAL)
    return run_checkpointed(plan, run_id=run_id, hw=HW, root=tmp_path, quote_fn=fake.quote,
                            submit_fn=fake.submit, find_job_fn=fake.find, wait_fn=fake.wait,
                            results_fn=fake.results, retry_kw=FAST, log=lambda m: None, **kw)


def test_happy_path_completes_and_stores_results(plan, tmp_path):
    fake = FakeNexus()
    out = _run(plan, fake, tmp_path)
    assert out["completed"] == len(out["states"]) and out["failed"] == 0
    assert len(fake.submits) == len(out["states"])
    res = load_results("r1", tmp_path)
    assert sum(len(v) for v in res.values()) == len(plan.items)
    again = _run(plan, fake, tmp_path)                     # a finished run is a no-op
    assert again["completed"] == out["completed"] and len(fake.submits) == len(out["states"])


def test_timeout_while_waiting_resumes_without_resubmitting(plan, tmp_path):
    fake = FakeNexus()
    first_job = None

    def wait(job_id):
        nonlocal first_job
        first_job = first_job or job_id
        if job_id == first_job and fake.blocking:
            raise TimeoutError("read timed out")
    fake.blocking = True
    fake.wait = wait
    with pytest.raises(ResumableStop):
        _run(plan, fake, tmp_path)
    n = len(fake.submits)
    fake.blocking = False
    out = _run(plan, fake, tmp_path)
    assert out["failed"] == 0 and out["completed"] == len(out["states"])
    assert len(fake.submits) == n, "a timeout while waiting must never cause a second submission"


def test_submit_timeout_after_the_server_accepted_is_adopted_not_repaid(plan, tmp_path):
    fake = FakeNexus()
    fake.submit_plan = [ReadTimeout("no reply")]
    fake.accept_before_raise = True
    with pytest.raises(ResumableStop):
        _run(plan, fake, tmp_path)
    assert len(fake.submits) == 1
    out = _run(plan, fake, tmp_path)
    assert out["completed"] == len(out["states"])
    assert fake.submits.count(fake.submits[0]) == 1, "the accepted job was submitted twice"


def test_submit_timeout_before_the_server_saw_it_is_submitted_once_more(plan, tmp_path):
    fake = FakeNexus()
    fake.submit_plan = [ConnectionError("reset")]
    with pytest.raises(ResumableStop):
        _run(plan, fake, tmp_path)
    out = _run(plan, fake, tmp_path)
    assert out["completed"] == len(out["states"])
    assert fake.submits.count(fake.submits[0]) == 2


def test_server_side_failure_is_left_alone_unless_retry_failed(plan, tmp_path):
    fake = FakeNexus()
    fake.wait_plan = {}
    orig_submit = fake.submit

    def submit(circuits, shots, *, job_name, **kw):
        r = orig_submit(circuits, shots, job_name=job_name, **kw)
        if not job_name.endswith("-r1"):
            fake.wait_plan[r.id] = [JobError("Job errored with detail: x")]
        return r
    fake.submit = submit
    out = _run(plan, fake, tmp_path)
    assert out["failed"] == len(out["states"]) and out["completed"] == 0
    n = len(fake.submits)
    _run(plan, fake, tmp_path)
    assert len(fake.submits) == n, "failed jobs were resubmitted without retry_failed"
    out = _run(plan, fake, tmp_path, retry_failed=True)
    assert out["completed"] == len(out["states"])
    assert all(s.endswith("-r1") for s in fake.submits[n:]) and len(fake.submits) == 2 * n


def test_every_resume_needs_the_per_run_approval(plan, tmp_path):
    fake = FakeNexus()
    called = []
    fake.quote = lambda *a, **k: called.append(1) or []
    with pytest.raises(DriverRefused):
        _run(plan, fake, tmp_path, approval=None)
    assert not called


def test_a_changed_plan_is_refused(plan, tmp_path):
    fake = FakeNexus()
    _run(plan, fake, tmp_path)
    other = build_plan("Q3-bare", 200, hw=HW)
    with pytest.raises(DriverRefused):
        _run(other, fake, tmp_path)


@pytest.mark.parametrize("exc, transient", [
    (TimeoutError(), True), (ConnectionError(), True), (ReadTimeout(), True),
    (type("E", (Exception,), {"status_code": 503})(), True),
    (type("E", (Exception,), {"status_code": 429})(), True),
    (type("E", (Exception,), {"status_code": 404})(), False),
    (ValueError(), False), (JobError(), False),
])
def test_transient_classification(exc, transient):
    assert is_transient(exc) is transient


def test_with_retry_retries_only_transient_errors():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError
        return "ok"
    assert with_retry(flaky, sleep=lambda s: None, log=lambda m: None, attempts=5) == "ok"
    assert len(calls) == 3
    calls.clear()

    def broken():
        calls.append(1)
        raise ValueError("not transient")
    with pytest.raises(ValueError):
        with_retry(broken, sleep=lambda s: None, log=lambda m: None)
    assert len(calls) == 1


def test_iceberg_batches_resume_too(tmp_path):
    p = build_plan("Q3-iceberg", 100, hw=HW)
    fake = FakeNexus()
    fake.submit_plan = [TimeoutError()]
    with pytest.raises(ResumableStop):
        _run(p, fake, tmp_path, run_id="ice")
    out = _run(p, fake, tmp_path, run_id="ice")
    assert out["completed"] == len(out["states"])


def test_default_job_lookup_goes_through_the_login_gate(monkeypatch):
    """find_job_by_name uses h2_backend._nexus_login (never qnexus directly) and maps qnexus's
    ZeroMatches to None, so a resume can tell 'never reached Nexus' from 'accepted'."""
    import src.h2_backend as hb
    from src.h2_resume import find_job_by_name

    class ZeroMatches(Exception):
        pass

    jobs = {"p-r-b0": SimpleNamespace(id="uuid-1")}

    def get(name=None, project=None, **kw):
        if name not in jobs:
            raise ZeroMatches(name)
        return jobs[name]
    fake = SimpleNamespace(projects=SimpleNamespace(get=lambda **kw: "proj"),
                           jobs=SimpleNamespace(get=get))
    monkeypatch.setattr(hb, "_nexus_login", lambda: fake)
    assert find_job_by_name("p-r-b0", project="p") == "uuid-1"
    assert find_job_by_name("p-r-b1", project="p") is None
