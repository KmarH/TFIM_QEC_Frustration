"""Quote every planned H2 run on the FREE Nexus syntax checker (H2-1SC) and compare with the offline
estimate (handoff/13). Needs a Nexus login (qnx.auth.login(), or NEXUS_REFRESH_TOKEN). Spends no HQC:
syntax_check refuses any device that is not an SC. Each circuit becomes one free SC job, recorded in
runs/nexus_ledger.jsonl; a circuit the server rejects is reported, not hidden.

Randomized-compiling runs quote ONE twirled instance at the full shot count; the k-instance cost is
then quote + 5 (k - 1), because the cost is affine in shots with a 5-HQC per-circuit overhead.

Usage: .venv/bin/python -I scripts/h2_sc_quotes.py [--shots 1000]  ->  data/h2_sc_quotes[TAG].txt
"""

# ruff: noqa: E501  (long report-text lines in log strings)
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
warnings.simplefilter("ignore")

from config import CONFIG  # noqa: E402
from scripts.h2_hqc_budget import RUNS, build  # noqa: E402
from src.h2_backend import offline_compile_backend, syntax_check  # noqa: E402
from src.h2_circuits import compile_for_h2, hqc_estimate, native_counts  # noqa: E402

E = CONFIG.encoded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=1000)
    ap.add_argument("--only", default="", help="comma list of groups to quote (default: all)")
    ap.add_argument("--tag", default="", help="suffix for the output file, e.g. _q1")
    a = ap.parse_args()
    groups = set(filter(None, a.only.split(",")))
    backend = offline_compile_backend(CONFIG.hardware.le_device)
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log(f"# H2-1SC quotes vs offline estimates -- {time.strftime('%Y-%m-%d %H:%M')}  ({a.shots} shots, free tier)")
    log("# quote = Nexus syntax-checker HQC cost; est(Rz) / est(no Rz) = scripts/h2_hqc_budget.py formula.")
    log(f"{'group':9}{'run':50}{'step':>5}{'qubits':>7}{'est(Rz)':>10}{'est(noRz)':>11}{'quote':>10}  status")
    tot = {}
    for group, label, kind, lat, steps, rc in RUNS:
        if groups and group not in groups:
            continue
        k = E.rc_instances if rc else 1
        for n in steps:
            c = compile_for_h2(build(kind, lat, n, rc), backend)
            cnt = native_counts(c)
            e1 = hqc_estimate(cnt, a.shots, count_rz=True)
            e2 = hqc_estimate(cnt, a.shots, count_rz=False)
            try:
                q = syntax_check([c], a.shots, project="tfim-qec-h2", device=CONFIG.hardware.syntax_checker)[0]["quoted_hqc"]
                status = "accepted"
            except Exception as ex:  # noqa: BLE001 -- report whatever the server said
                q, status = float("nan"), f"REJECTED: {type(ex).__name__}: {str(ex)[:90]}"
            adj = q + 5 * (k - 1) if q == q else float("nan")
            log(f"{group:9}{label[:49]:50}{n:>5}{cnt['nqubits']:>7}{e1:>10.2f}{e2:>11.2f}{q:>10.2f}  {status}")
            tot.setdefault(group, [0.0, 0.0, 0.0])
            tot[group][0] += e1 + 5 * (k - 1)
            tot[group][1] += e2 + 5 * (k - 1)
            tot[group][2] += adj
    log()
    log("Totals incl. the +5 per extra RC circuit (est Rz | est no Rz | quoted):")
    for g, (x, y, z) in tot.items():
        log(f"  {g:9}{x:>10.0f} | {y:>8.0f} | {z:>8.0f}")
    out = os.path.join(REPO, CONFIG.data_dir, f"h2_sc_quotes{a.tag}.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
