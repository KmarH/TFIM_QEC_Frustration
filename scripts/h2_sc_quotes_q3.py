"""Quote the Q3 run groups on the FREE Nexus syntax checker (H2-1SC) and compare with the offline
estimate (handoff/14). Needs a Nexus login. Spends no HQC: driver tier "sc" only ever talks to an SC.

Usage (one process per group runs in parallel; each writes data/h2_sc_quotes_q3_<group>.txt):
  .venv/bin/python -I scripts/h2_sc_quotes_q3.py --group Q3-ladder [--shots 500]
  .venv/bin/python -I scripts/h2_sc_quotes_q3.py --merge       ->  data/h2_sc_quotes_q3.txt
"""

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
from src.h2_driver import Q3_GROUPS, _by_shots, build_plan, execute  # noqa: E402

DATA = os.path.join(REPO, CONFIG.data_dir)


def quote_group(g: str, shots: int) -> None:
    plan = build_plan(g, shots)
    out = execute(plan, tier="sc")
    order = [it for _, items in _by_shots(plan.items) for it in items]  # quote order == this order
    rows = out["quotes"]
    lines = [
        f"# H2-1SC quotes, group {g} -- {time.strftime('%Y-%m-%d %H:%M')} ({shots} shots per point, free tier; no job run)",
        "# quote = Nexus syntax-checker HQC [measured, server]; est = offline Rz-free formula (src/h2_circuits.hqc_estimate)",
        f"{'item':34}{'qubits':>7}{'shots':>7}{'est':>10}{'quote':>10}",
    ]
    for it, r in zip(order, rows, strict=True):
        lines.append(f"{it.label:34}{it.n_qubits:>7}{it.shots:>7}{it.estimate_hqc:>10.2f}{r['quoted_hqc']:>10.2f}")
    lines.append(f"TOTAL {g} circuits={len(order)} qubits={plan.max_qubits} est={plan.total_estimate_hqc:.1f} quote={out['quoted_hqc']:.1f}")
    with open(os.path.join(DATA, f"h2_sc_quotes_q3_{g}.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(lines[-1])


def merge() -> None:
    lines = [
        f"# H2-1SC quotes for the Q3 groups -- merged {time.strftime('%Y-%m-%d %H:%M')} (per-item detail in data/h2_sc_quotes_q3_<group>.txt)",
        "# quote = server price, a quote not a measurement of any physics; est = offline Rz-free formula.",
        f"{'group':14}{'circuits':>9}{'qubits':>7}{'est HQC':>10}{'quote HQC':>11}",
    ]
    te = tq = 0.0
    for g in Q3_GROUPS:
        with open(os.path.join(DATA, f"h2_sc_quotes_q3_{g}.txt"), encoding="utf-8") as fh:
            tot = [ln for ln in fh if ln.startswith("TOTAL")][0].split()
        kv = dict(x.split("=") for x in tot[2:])
        e, q = float(kv["est"]), float(kv["quote"])
        te, tq = te + e, tq + q
        lines.append(f"{g:14}{kv['circuits']:>9}{kv['qubits']:>7}{e:>10.1f}{q:>11.1f}")
    lines.append(f"{'total':14}{'':>9}{'':>7}{te:>10.1f}{tq:>11.1f}")
    with open(os.path.join(DATA, "h2_sc_quotes_q3.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", choices=Q3_GROUPS)
    ap.add_argument("--shots", type=int, default=CONFIG.noise_scaling.plan_shots)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        merge()
    elif a.group:
        quote_group(a.group, a.shots)
    else:
        ap.error("give --group or --merge")


if __name__ == "__main__":
    main()
