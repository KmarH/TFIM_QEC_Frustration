"""Checkpointed, resumable Nexus runs with safe retries (2026-10-24, the project lead's request).

`src/h2_driver.execute` sends a whole plan in one go: a network timeout half-way leaves no record
of which batches were quoted, submitted or fetched. This module runs the SAME plan through the SAME
gates (`h2_driver._emulator_gates`, `h2_backend.syntax_check / submit_nexus`) but stage by stage,
writing a checkpoint file after every step, so a run interrupted by a timeout, a dropped connection
or a closed laptop resumes exactly where it stopped:

    quote (free, SC)  ->  submit (SPENDS HQC)  ->  wait  ->  fetch results  ->  done

Retry policy - the one thing that must never happen is paying twice:
  * read-only calls (quote, status, wait, results, job lookup) are retried with exponential
    backoff on TRANSIENT errors only (timeouts, dropped connections, HTTP 429 / 5xx);
  * a SUBMISSION is never retried blindly. Before submitting, the batch's deterministic job name
    is written to the checkpoint (state "submitting"). If the submit call fails, the run stops.
    On resume, the job is first LOOKED UP by that name on Nexus: if it exists (the server
    accepted it although our call timed out), it is adopted and nothing is resubmitted; only
    if Nexus has no job of that name is it submitted again;
  * a job that FAILED server-side (ERROR / CANCELLED / DEPLETED / TERMINATED) is recorded and
    left alone. It is resubmitted only with `retry_failed=True`, under a new name
    (`-r1`, `-r2`, ...), and that resubmission passes every spending gate again.
Every resume re-runs the emulator gates, so the per-run approval token is needed again.

Checkpoint: runs/nexus_runs/<run_id>/checkpoint.json (atomic writes), results per batch in
runs/nexus_runs/<run_id>/batch<k>.npz (raw bits per circuit, the arrays `run_le` returns). A plan
whose circuits differ from the checkpoint's is refused (no silent mixing of two plans).

Nothing here is ever called automatically: spending HQC still needs the project lead's per-run go.
All network access goes through the injected functions, so the tests run fully offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np

from src.h2_driver import (
    DriverRefused,
    Plan,
    _by_shots,
    _emulator_gates,
    _finite_pos,
    _hw,
)

RUNS = Path(__file__).resolve().parent.parent / "runs" / "nexus_runs"
STATES = ("planned", "quoted", "submitting", "submitted", "completed", "failed")


class ResumableStop(RuntimeError):
    """The run stopped at a safe point (a timeout, a dropped connection, a failed submit call).
    Re-run the same command to resume; nothing already done is repeated or paid for twice."""


# --------------------------------------------------------------------------- #
# Transient-error classification and retry
# --------------------------------------------------------------------------- #
_TRANSIENT_NAMES = {
    "TimeoutError", "ReadTimeout", "ConnectTimeout", "WriteTimeout", "PoolTimeout",
    "TimeoutException", "ConnectError", "ReadError", "WriteError", "NetworkError",
    "RemoteProtocolError", "ProtocolError", "ConnectionClosed", "ConnectionClosedError",
    "ConnectionClosedOK", "InvalidStatus", "InvalidMessage", "ServerDisconnectedError",
}


def is_transient(exc: BaseException) -> bool:
    """True for errors worth retrying: timeouts, broken connections, HTTP 429 and 5xx.
    Authentication failures, server-side job failures and client errors (4xx) are not."""
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    for cls in type(exc).__mro__:
        if cls.__name__ in _TRANSIENT_NAMES:
            return True
    code = getattr(exc, "status_code", None)
    if code is None:
        resp = getattr(exc, "response", None)
        code = getattr(resp, "status_code", None)
    if isinstance(code, int):
        return code == 429 or code >= 500
    # qnexus ResourceFetchFailed / ResourceCreateFailed without a status code: the request never
    # got an answer, which is a transport failure
    if type(exc).__name__ in ("ResourceFetchFailed", "ResourceCreateFailed"):
        return code is None
    return False


def with_retry(fn: Callable, *args, attempts: int = 6, base_delay: float = 5.0,
               max_delay: float = 300.0, sleep: Callable[[float], None] = time.sleep,
               log: Callable[[str], None] = print, **kwargs):
    """Call fn(*args, **kwargs); on a TRANSIENT error wait base_delay * 2^k (+ jitter, capped at
    max_delay) and try again, up to `attempts` calls. Non-transient errors propagate at once.
    Only for calls that are safe to repeat (never a submission)."""
    for k in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if not is_transient(exc) or k == attempts - 1:
                raise
            delay = min(max_delay, base_delay * 2 ** k) * (1 + 0.1 * random.random())
            log(f"transient {type(exc).__name__}: {exc!s:.200}; retry {k + 2}/{attempts} "
                f"in {delay:.0f} s")
            sleep(delay)
    raise AssertionError("unreachable")


# --------------------------------------------------------------------------- #
# Read-only Nexus job access by name / id, for resuming in a fresh process. They reach Nexus only
# through h2_backend._nexus_login() (the login gate); qnexus itself stays confined to
# src/h2_backend.py (tests/test_h2_backend.py pins that).
# --------------------------------------------------------------------------- #
def find_job_by_name(name: str, *, project: str):
    """The id of the Nexus job named exactly `name` in `project`, or None if there is none.
    Read-only. Raises if two jobs share the name: never guess which one was paid for."""
    from src.h2_backend import _nexus_login

    qnx = _nexus_login()
    proj = qnx.projects.get(name_like=project)
    try:
        ref = qnx.jobs.get(name=name, project=proj)
    except Exception as exc:
        if type(exc).__name__ == "ZeroMatches":
            return None
        raise
    return str(ref.id)


def wait_job(job_id: str, timeout: float | None = 3600.0):
    """Wait (read-only) for job `job_id` to complete. qnexus raises JobError if it errored, was
    cancelled, ran out of credits or was terminated, and TimeoutError past `timeout` (which
    with_retry then treats as transient: the job keeps running on Nexus)."""
    from src.h2_backend import _nexus_login

    qnx = _nexus_login()
    return qnx.jobs.wait_for(qnx.jobs.get(id=job_id), timeout=timeout)


def fetch_job_results(job_id: str, cbits_list) -> list[np.ndarray]:
    """Raw bits per circuit of a completed job, by id - the arrays fetch_nexus / run_le return."""
    from src.h2_backend import _nexus_login

    qnx = _nexus_login()
    results = qnx.jobs.results(qnx.jobs.get(id=job_id))
    return [np.asarray(r.download_result().get_shots(cbits=list(cb)), dtype=np.int8)
            for r, cb in zip(results, cbits_list, strict=True)]


# --------------------------------------------------------------------------- #
# Checkpoint
# --------------------------------------------------------------------------- #
def _circuit_hash(c) -> str:
    return hashlib.sha256(json.dumps(c.to_dict(), sort_keys=True).encode()).hexdigest()[:16]


class Checkpoint:
    """One JSON file per run; every change is written atomically before the next step."""

    def __init__(self, run_id: str, root: Path | None = None):
        if not run_id or any(ch in run_id for ch in "/\\:"):
            raise ValueError(f"run_id must be a plain name, got {run_id!r}")
        self.dir = Path(root or RUNS) / run_id
        self.path = self.dir / "checkpoint.json"
        self.run_id = run_id
        self.data: dict = {}
        if self.path.exists():
            with open(self.path, encoding="utf-8") as fh:
                self.data = json.load(fh)

    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(f".{os.getpid()}.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=1)
        os.replace(tmp, self.path)

    def batch(self, k: int) -> dict:
        return self.data["batches"][k]

    def set(self, k: int, **fields) -> None:
        b = self.batch(k)
        if "state" in fields and fields["state"] != b.get("state"):
            b.setdefault("history", []).append(
                {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "state": fields["state"]})
        b.update(fields)
        self.save()


def _init_or_check(cp: Checkpoint, plan: Plan, project: str) -> list:
    groups = _by_shots(plan.items)
    sig = [{"shots": shots, "labels": [i.label for i in items],
            "hashes": [_circuit_hash(i.circuit) for i in items]} for shots, items in groups]
    if not cp.data:
        cp.data = {"run_id": cp.run_id, "group": plan.group, "project": project,
                   "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "batches": [{**s, "state": "planned", "attempt": 0} for s in sig]}
        cp.save()
    else:
        old = [{k: b[k] for k in ("shots", "labels", "hashes")} for b in cp.data["batches"]]
        if old != sig or cp.data.get("group") != plan.group:
            raise DriverRefused(
                f"run {cp.run_id!r}: the plan differs from the checkpointed one (circuits, labels "
                "or shots changed). Use a new run_id; two plans are never mixed in one run.")
    return groups


def _job_name(project: str, run_id: str, k: int, attempt: int) -> str:
    return f"{project}-{run_id}-b{k}" + (f"-r{attempt}" if attempt else "")


def _cbits(item) -> list:
    meta = item.meta
    if "layout" in meta:
        return list(meta["layout"].cbits)
    return list(meta["cbits"])


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #
def run_checkpointed(plan: Plan, *, run_id: str, approval: str | None, hw=None,
                     retry_failed: bool = False, root: Path | None = None,
                     quote_fn: Callable | None = None, submit_fn: Callable | None = None,
                     find_job_fn: Callable | None = None, wait_fn: Callable | None = None,
                     results_fn: Callable | None = None, retry_kw: dict | None = None,
                     log: Callable[[str], None] = print) -> dict:
    """Run `plan` on the Nexus EMULATOR tier with a checkpoint, resuming from any earlier stop.

    The emulator gates of src/h2_driver run first, every time (approval token included). Raises
    ResumableStop at a safe point after a transient failure; re-run the same call to resume."""
    hw = _hw(hw)
    _emulator_gates(plan, hw, approval)
    if quote_fn is None:
        from src.h2_backend import syntax_check as quote_fn
    if submit_fn is None:
        from src.h2_backend import submit_nexus as submit_fn
    if find_job_fn is None:
        find_job_fn = find_job_by_name
    if wait_fn is None:
        wait_fn = wait_job
    if results_fn is None:
        results_fn = fetch_job_results
    rk = {"log": log, **(retry_kw or {})}
    project = hw.nexus_project
    cp = Checkpoint(run_id, root)
    groups = _init_or_check(cp, plan, project)

    # 1. quotes (free; safe to retry)
    for k, (shots, items) in enumerate(groups):
        if cp.batch(k)["state"] != "planned":
            continue
        rows = list(with_retry(quote_fn, [i.circuit for i in items], shots, project=project,
                               device=hw.syntax_checker, **rk))
        if len(rows) != len(items) or not all(_finite_pos(r.get("quoted_hqc")) for r in rows):
            raise DriverRefused(f"batch {k}: unusable SC quotes {rows!r}")
        cp.set(k, state="quoted", quoted_hqc=sum(float(r["quoted_hqc"]) for r in rows))
    total = sum(b.get("quoted_hqc", 0.0) for b in cp.data["batches"])
    if not total <= hw.max_cost_hqc:
        raise DriverRefused(f"SC quote total {total:.2f} HQC exceeds max_cost_hqc "
                            f"{hw.max_cost_hqc:.2f}: nothing submitted")

    # 2. failed batches go back to "quoted" only when asked, under a new job name
    if retry_failed:
        for k, b in enumerate(cp.data["batches"]):
            if b["state"] == "failed":
                cp.set(k, state="quoted", attempt=b.get("attempt", 0) + 1, job_id=None)

    # 3. submissions (SPEND): look up before ever submitting again
    for k, (shots, items) in enumerate(groups):
        b = cp.batch(k)
        name = _job_name(project, run_id, k, b.get("attempt", 0))
        if b["state"] == "submitting":
            found = with_retry(find_job_fn, name, project=project, **rk)
            if found is not None:
                log(f"batch {k}: job {name} already exists on Nexus - adopted, not resubmitted")
                cp.set(k, state="submitted", job_id=str(found))
                continue
            log(f"batch {k}: no job named {name} on Nexus - submitting it now")
        elif b["state"] != "quoted":
            continue
        cp.set(k, state="submitting", job_name=name)
        try:
            job = submit_fn([i.circuit for i in items], shots, project=project,
                            device=hw.emulator_device, allow_hardware=True, approval=approval,
                            max_cost_hqc=hw.max_cost_hqc, estimated_hqc=b["quoted_hqc"],
                            job_name=name)
        except DriverRefused:
            raise
        except Exception as exc:
            cp.set(k, error=f"submit: {type(exc).__name__}: {exc!s:.300}")
            raise ResumableStop(
                f"batch {k}: the submit call failed ({type(exc).__name__}). It may or may not "
                f"have reached Nexus. Re-run to resume: job {name!r} is looked up by name first "
                "and is only submitted again if Nexus has no job of that name.") from exc
        cp.set(k, state="submitted", job_id=str(getattr(job, "id", job)), error=None)

    # 4. wait and fetch (read-only; safe to retry). A server-side failure is recorded, not retried.
    for k, (_shots, items) in enumerate(groups):
        b = cp.batch(k)
        if b["state"] != "submitted":
            continue
        try:
            with_retry(wait_fn, b["job_id"], **rk)
        except Exception as exc:
            if is_transient(exc):
                cp.set(k, error=f"wait: {type(exc).__name__}: {exc!s:.300}")
                raise ResumableStop(f"batch {k}: still waiting for job {b['job_id']} after "
                                    "retries; re-run to resume (the job keeps running on "
                                    "Nexus and is not resubmitted)") from exc
            cp.set(k, state="failed", error=f"{type(exc).__name__}: {exc!s:.300}")
            log(f"batch {k}: job {b['job_id']} failed on the server: {exc!s:.200}")
            continue
        arrays = with_retry(results_fn, b["job_id"], [_cbits(i) for i in items], **rk)
        out = cp.dir / f"batch{k}.npz"
        np.savez_compressed(out, **{f"c{i}": np.asarray(a) for i, a in enumerate(arrays)})
        cp.set(k, state="completed", results=out.name, error=None)

    states = [b["state"] for b in cp.data["batches"]]
    return {"run_id": run_id, "states": states, "quoted_hqc": total,
            "completed": states.count("completed"), "failed": states.count("failed"),
            "checkpoint": str(cp.path)}


def load_results(run_id: str, root: Path | None = None) -> dict[int, list[np.ndarray]]:
    """Raw bits of every completed batch of a run: {batch: [array per circuit]}."""
    cp = Checkpoint(run_id, root)
    out = {}
    for k, b in enumerate(cp.data.get("batches", [])):
        if b["state"] == "completed":
            with np.load(cp.dir / b["results"]) as z:
                out[k] = [z[f"c{i}"] for i in range(len(b["labels"]))]
    return out
