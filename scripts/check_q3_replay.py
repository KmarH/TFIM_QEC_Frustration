"""Check that the N = 12 replays (scripts/q3_queue.py "<cell>/replay" jobs: the original seed and
settings, run by the 2026-10-24 code that also records per-batch detail) reproduce the stored
cell files, and only then adopt them.

For every runs/q3_sweep/replay/cell_*.json the stored runs/q3_sweep/cell_*.json must agree on
every pooled curve, SE and acceptance of both arms and of the ideal reference to rtol 1e-10. A
replay that agrees replaces the stored file (which moves to runs/q3_sweep/superseded/<date>/,
never deleted); one that does not is reported and left alone - a disagreement is a finding, not
something to paper over. Usage: python -I scripts/check_q3_replay.py [--adopt]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "runs", "q3_sweep")
OBS = ("flippable_density", "defect_density", "memory", "C1")


def _f(x):
    return np.asarray(x, dtype=float)


def compare(old: dict, new: dict) -> list[str]:
    bad = []
    for arm in ("ideal", "bare", "ice"):
        a, b = old.get(arm), new.get(arm)
        if (a is None) != (b is None):
            bad.append(f"{arm}: present in one file only")
            continue
        if a is None:
            continue
        pairs = [("times", a["times"], b["times"]), ("p_in", a["p_in"], b["p_in"])]
        if "acceptance" in a:
            pairs.append(("acceptance", a["acceptance"], b["acceptance"]))
        for key in ("raw", "cond"):
            for o in OBS:
                pairs.append((f"{key}.{o}.value", a[key][o][0], b[key][o][0]))
                pairs.append((f"{key}.{o}.se", a[key][o][1], b[key][o][1]))
        for name, x, y in pairs:
            x, y = _f(x), _f(y)
            if x.shape != y.shape or not np.allclose(x, y, rtol=1e-10, atol=1e-13, equal_nan=True):
                d = np.nanmax(np.abs(x - y)) if x.shape == y.shape else "shape"
                bad.append(f"{arm}.{name}: max |diff| {d}")
    return bad


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adopt", action="store_true", help="replace stored cells that reproduce")
    a = ap.parse_args()
    reps = sorted(glob.glob(os.path.join(WORK, "replay", "cell_*.json")))
    if not reps:
        raise SystemExit("no replays yet")
    failed = 0
    for rp in reps:
        name = os.path.basename(rp)
        sp = os.path.join(WORK, name)
        with open(rp, encoding="utf-8") as fh:
            new = json.load(fh)
        if not os.path.exists(sp):
            print(f"{name}: no stored cell to compare with")
            failed += 1
            continue
        with open(sp, encoding="utf-8") as fh:
            old = json.load(fh)
        if "per_batch" in (old.get("ice") or {}):
            print(f"{name}: stored cell already carries per-batch data (adopted earlier)")
            continue
        bad = compare(old, new)
        if bad:
            failed += 1
            print(f"{name}: DOES NOT REPRODUCE ({len(bad)} fields), e.g. {bad[:3]}")
            continue
        print(f"{name}: reproduces the stored cell (rtol 1e-10)")
        if a.adopt:
            dest = os.path.join(WORK, "superseded", time.strftime("%Y-%m-%d"), name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            os.replace(sp, dest)
            os.replace(rp, sp)
            print(f"  adopted; stored file moved to {os.path.relpath(dest, REPO)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
