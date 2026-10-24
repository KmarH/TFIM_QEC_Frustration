"""Run an H2 plan group on the Nexus EMULATOR with a checkpoint, and resume it after any timeout.

    # start (or resume - it is the same command):
    python -I scripts/h2_run_resumable.py --group Q3-iceberg --shots 500 --run-id q3ice-01 \\
        --approval <per-run token>
    # see where a run stands (offline, no login, nothing sent):
    python -I scripts/h2_run_resumable.py --run-id q3ice-01 --status
    # resubmit batches that FAILED on the server (spends again; asks for the approval again):
    ... --retry-failed

Exit codes: 0 finished; 3 stopped at a safe point after a transient error (timeout, dropped
connection) - re-run the same command to resume; 2 refused by a gate. Spending still needs
config.hardware.nexus_tier = "emulator", allow_hardware = True, a max_cost_hqc and the project
lead's per-run approval token, exactly as scripts/h2 runs through src/h2_driver.py. Nothing
here runs automatically. See src/h2_resume.py for the retry and no-double-spend rules.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from config import CONFIG
from src.h2_driver import DriverRefused, build_plan, group_names
from src.h2_resume import Checkpoint, ResumableStop, run_checkpointed


def status(run_id: str) -> int:
    cp = Checkpoint(run_id)
    if not cp.data:
        print(f"no checkpoint for run {run_id!r} in {cp.dir}")
        return 1
    print(f"run {run_id}: group {cp.data['group']}, project {cp.data['project']}, "
          f"created {cp.data['created']}")
    for k, b in enumerate(cp.data["batches"]):
        print(f"  batch {k}: {len(b['labels'])} circuits x {b['shots']} shots  {b['state']:<10s}"
              f" quote {b.get('quoted_hqc', '-')}  job {b.get('job_name') or '-'}"
              + (f"  error: {b['error']}" if b.get("error") else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--group", choices=group_names())
    ap.add_argument("--shots", type=int, default=1000)
    ap.add_argument("--approval", default=None)
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    if a.status:
        return status(a.run_id)
    if not a.group:
        ap.error("--group is required to start or resume a run")
    try:
        plan = build_plan(a.group, a.shots, hw=CONFIG.hardware)
        out = run_checkpointed(plan, run_id=a.run_id, approval=a.approval,
                               retry_failed=a.retry_failed)
    except DriverRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    except ResumableStop as e:
        print(f"STOPPED SAFELY: {e}\nRe-run the same command to resume.", file=sys.stderr)
        return 3
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
