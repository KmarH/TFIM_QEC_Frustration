"""Resumable job queue for the DECIDED-10 re-runs of the Q3 sweep (one worker = one core).

Every job is one process of scripts/run_q3_sweep.py:
  shard   "<N>:<h>:<lam>/s<i>"  -> runs/q3_sweep/shards/cell_..._shardNN.json   (shard 0 also
                                    computes the ideal reference; the others pass --skip-ideal)
  replay  "<N>:<h>:<lam>/replay" -> runs/q3_sweep/replay/cell_....json           (an N = 12 cell
                                    re-run at its ORIGINAL seed and settings, to gain per-batch
                                    detail; it must reproduce the existing cell file)

A worker walks its host's job list in order, skips jobs whose output exists, and claims a job by
creating runs/q3_sweep/queue/<job>.claim exclusively. A claim whose process is gone (a reboot, a
killed worker) is taken over, so any worker can be relaunched at any time and the set of jobs
done never depends on which machine ran what. Nothing here chooses data: the job list is the
pre-declared budget of config.Q3ScalingConfig.rerun.

Usage
  list:    python -I scripts/q3_queue.py --list
  worker:  python -I scripts/q3_queue.py --worker --jobs-file runs/q3_sweep/queue/<host>.txt
  status:  python -I scripts/q3_queue.py --status --jobs-file ...

Classical prediction under the ASSUMED research/06 noise model; nothing touches hardware.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from config import CONFIG

WORK = os.path.join(REPO, "runs", "q3_sweep")
QDIR = os.path.join(WORK, "queue")
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
               "NUMEXPR_NUM_THREADS")
REPLAYS = ((12, 0.1, 1), (12, 0.2, 1), (12, 0.3, 1), (12, 0.3, 2), (12, 0.3, 3),
           (12, 0.5, 1), (12, 0.5, 3))


def _cell(n, h, lam) -> str:
    return f"{n}:{h:g}:{lam:g}"


def all_jobs() -> list[str]:
    qs = CONFIG.q3_scaling
    jobs = [f"{_cell(*c)}/replay" for c in REPLAYS]
    for c in sorted(qs.rerun, key=lambda c: (-c[0], c[1], c[2])):
        jobs += [f"{_cell(*c)}/s{i}" for i in range(qs.rerun_shards)]
    return jobs


def _parse(job: str):
    cell, kind = job.split("/")
    n, h, lam = cell.split(":")
    return int(n), float(h), float(lam), kind


def output_path(job: str) -> str:
    n, h, lam, kind = _parse(job)
    base = f"cell_N{n}_h{h:g}_lam{lam:g}"
    if kind == "replay":
        return os.path.join(WORK, "replay", base + ".json")
    return os.path.join(WORK, "shards", f"{base}_shard{int(kind[1:]):02d}.json")


def command(job: str) -> list[str]:
    n, h, lam, kind = _parse(job)
    cmd = [sys.executable, "-I", os.path.join(REPO, "scripts", "run_q3_sweep.py"),
           "--cell", _cell(n, h, lam)]
    if kind == "replay":
        return [*cmd, "--out-dir", os.path.join(WORK, "replay")]
    i = int(kind[1:])
    return [*cmd, "--shard", str(i)] + ([] if i == 0 else ["--skip-ideal"])


def _safe(job: str) -> str:
    return job.replace(":", "_").replace("/", "__")


def _alive(pid: int) -> bool:
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True,
                             text=True, check=False).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _stale(path: str, host: str) -> bool:
    """True when the claim's worker is gone: a same-host claim whose pid is dead, or an empty /
    unreadable claim older than a minute (its worker died between create and write)."""
    try:
        with open(path, encoding="utf-8") as fh:
            other = json.load(fh)
    except FileNotFoundError:
        return False
    except (OSError, ValueError):
        try:
            return time.time() - os.path.getmtime(path) > 60
        except OSError:
            return False
    return other.get("host") == host and not _alive(int(other.get("pid", -1)))


def _claim(job: str) -> bool:
    """Claim a job by creating its claim file exclusively. A stale claim is taken over by renaming
    it to a unique tombstone: of several workers racing for it only one rename succeeds. (A worker
    that is slow enough to rename a FRESH claim makes the job run twice; the shard is deterministic
    in its seed, so that wastes compute but cannot corrupt data. Review B 2026-10-24.)"""
    os.makedirs(QDIR, exist_ok=True)
    path = os.path.join(QDIR, _safe(job) + ".claim")
    me = {"host": socket.gethostname(), "pid": os.getpid(), "t": time.time()}
    for _ in range(3):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if not _stale(path, me["host"]):
                return False
            try:
                os.rename(path, f"{path}.stale.{os.getpid()}.{time.time_ns()}")
            except OSError:
                return False                    # another worker took it over first
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(me, fh)
        return True
    return False


def _release(job: str) -> None:
    try:
        os.remove(os.path.join(QDIR, _safe(job) + ".claim"))
    except OSError:
        pass


def worker(jobs: list[str]) -> None:
    env = {**os.environ, **{v: "1" for v in THREAD_VARS}}
    logs = os.path.join(QDIR, "logs")
    os.makedirs(logs, exist_ok=True)
    for job in jobs:
        if os.path.exists(output_path(job)) or not _claim(job):
            continue
        if os.path.exists(output_path(job)):     # finished while we were claiming
            _release(job)
            continue
        t0 = time.time()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] start {job}", flush=True)
        try:
            with open(os.path.join(logs, _safe(job) + ".log"), "a", encoding="utf-8") as log:
                rc = subprocess.run(command(job), stdout=log, stderr=subprocess.STDOUT,
                                    env=env, cwd=REPO, check=False).returncode
        finally:
            _release(job)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] end {job} rc={rc} "
              f"{time.time() - t0:.0f} s", flush=True)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] worker finished its list", flush=True)


def status(jobs: list[str]) -> None:
    done = [j for j in jobs if os.path.exists(output_path(j))]
    claimed = [j for j in jobs if os.path.exists(os.path.join(QDIR, _safe(j) + ".claim"))]
    print(f"done {len(done)}/{len(jobs)}; running {len(claimed)}: {', '.join(claimed) or '-'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print every pre-declared job")
    ap.add_argument("--worker", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--jobs-file", help="one job per line (default: every job)")
    a = ap.parse_args()
    jobs = all_jobs()
    if a.jobs_file:
        with open(a.jobs_file, encoding="utf-8") as fh:
            jobs = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
        unknown = sorted(set(jobs) - set(all_jobs()))
        if unknown:
            raise SystemExit(f"not pre-declared jobs: {unknown}")
    if a.list:
        print("\n".join(jobs))
    elif a.status:
        status(jobs)
    elif a.worker:
        worker(jobs)
    else:
        ap.error("--list, --status or --worker")


if __name__ == "__main__":
    main()
