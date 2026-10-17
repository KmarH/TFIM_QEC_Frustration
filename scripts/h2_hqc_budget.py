"""HQC budget for everything the project would run on the Nexus H2 emulator (handoff/13).

OFFLINE: compiles each planned circuit to H2's native gates at TKET level 0 (no network, no login,
no HQC) and applies the standard cost formula, HQC = 5 + C (N1q + 10 N2q + 5 Nm)/5000
[established, research/07], with Nm = qubit preparations + measurements + resets. Rz is counted as
a one-qubit gate (conservative); the "Rz free" column drops it. The free Nexus syntax checker
(src/h2_backend.syntax_check) gives the authoritative quote; this is the plan to compare it with.

Shots per point are [assumed]; the cost is linear in them (plus the 5-HQC per-circuit overhead).
Randomized compiling runs `rc_instances` twirled circuits sharing the shot budget, so it pays the
overhead per instance. Width flags use the Nexus emulator limits (docs excerpt, [unverified]):
H2-1E state vector <= 32 qubits (recommended < 28), stabilizer <= 56 (Clifford only).

Usage: .venv/bin/python -I scripts/h2_hqc_budget.py        -> data/h2_hqc_budget.txt
Nothing here submits anything (SCOPE §5).
"""

# ruff: noqa: E501  (long report-text lines in log strings)
from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


from config import CONFIG  # noqa: E402
from src.encoded_codes import EncodedTFIM, make_code  # noqa: E402
from src.encoded_tfim import IcebergTFIM, twirl_program  # noqa: E402
from src.h2_backend import offline_compile_backend  # noqa: E402
from src.h2_circuits import (  # noqa: E402
    bare_h2_circuit,
    codes_h2_circuit,
    compile_for_h2,
    encoded_h2_circuit,
    hqc_estimate,
    native_counts,
)

E = CONFIG.encoded
BUDGET = 50_000.0  # HQC on H2-1E / H2-2E, Nexus usage page 2026-10-17
SHOTS = 1000  # [assumed] per (circuit, step) point
SV_MAX, SV_REC, LOCAL_MAX = 32, 28, 24

# (group, label, kind, lattice, steps, rc)
RUNS = [
    ("G1", "Iceberg 2x2, plain", "enc", (2, 2), (1, 2, 3), False),
    ("G1", "Iceberg 2x2, RC", "enc", (2, 2), (1, 2, 3), True),
    ("G1", "bare 2x2", "bare", (2, 2), (1, 2, 3), False),
    (
        "Q1",
        "Iceberg 4x5, RC   (recommended headline lattice)",
        "enc",
        (4, 5),
        tuple(range(1, 7)),
        True,
    ),
    ("Q1", "bare 4x5", "bare", (4, 5), tuple(range(1, 7)), False),
    ("Q1-alt", "Iceberg 4x6, RC", "enc", (4, 6), tuple(range(1, 7)), True),
    ("Q1-alt", "bare 4x6", "bare", (4, 6), tuple(range(1, 7)), False),
    (
        "Q1-draft",
        "Iceberg 6x8, RC  (first draft; does NOT fit the emulator)",
        "enc",
        (6, 8),
        tuple(range(1, 7)),
        True,
    ),
    ("Q1-draft", "bare 6x8", "bare", (6, 8), tuple(range(1, 7)), False),
    ("Q4", "Steane 1x2", "code:steane", (1, 2), (1, 2, 3), False),
    ("Q4", "5-qubit 1x2", "code:five", (1, 2), (1, 2, 3), False),
    ("Q4", "concatenated Iceberg 2x2", "code:concat", (2, 2), (1, 2, 3), False),
]


def build(kind, lat, n, rc):
    Lx, Ly = lat
    if kind.startswith("code:"):
        prog = EncodedTFIM(
            make_code(kind[5:], Lx * Ly), Lx, Ly, "periodic", E.J, E.h, E.dt, E.theta
        )
        return codes_h2_circuit(prog, n)[0]
    spec = IcebergTFIM(Lx, Ly, "periodic", E.J, E.h, E.dt, E.theta, 1)
    if kind == "bare":
        return bare_h2_circuit(spec, n)[0]
    return encoded_h2_circuit(spec, n, twirl_program(spec, n, 0) if rc else None)[0]


def main():
    backend = offline_compile_backend(CONFIG.hardware.le_device)
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log(f"# H2 HQC budget (OFFLINE estimate) -- {time.strftime('%Y-%m-%d %H:%M')}")
    log(
        "# CLASSICAL ESTIMATE from compiled gate counts + the standard formula; no job was submitted."
    )
    log(
        f"# {SHOTS} shots per point [assumed]; RC = {E.rc_instances} twirled instances share the shots."
    )
    log(f"# Budget: {BUDGET:.0f} HQC on H2-1E/H2-2E (Nexus usage page). Rz counted (conservative).")
    log()
    log(f"{'group':9}{'run':58}{'qubits':>7}{'fits E?':>16}{'HQC':>10}{'HQC Rz-free':>13}")
    group_tot, group_free = {}, {}
    for group, label, kind, lat, steps, rc in RUNS:
        tot = free = 0.0
        width = 0
        for n in steps:
            c = compile_for_h2(build(kind, lat, n, rc), backend)
            cnt = native_counts(c)
            width = max(width, cnt["nqubits"])
            k = E.rc_instances if rc else 1
            tot += k * hqc_estimate(cnt, SHOTS // k)
            free += k * hqc_estimate(cnt, SHOTS // k, count_rz=False)
        fits = (
            "no (>32)"
            if width > SV_MAX
            else "at limit (>28)"
            if width > SV_REC
            else "yes"
            if width > LOCAL_MAX
            else "yes (+local)"
        )
        log(f"{group:9}{label:58}{width:>7}{fits:>16}{tot:>10.0f}{free:>13.0f}")
        group_tot[group] = group_tot.get(group, 0.0) + tot
        group_free[group] = group_free.get(group, 0.0) + free
    log()
    log("Totals by group (HQC, Rz counted | Rz free):")
    for g in group_tot:
        log(f"  {g:9}{group_tot[g]:>10.0f} | {group_free[g]:>8.0f}")
    core = sum(group_tot[g] for g in ("G1", "Q1", "Q4"))
    log()
    log(f"G1 + Q1 (4x5) + Q4 = {core:.0f} HQC of {BUDGET:.0f} ({100 * core / BUDGET:.0f}%).")
    log(
        "Q3 rows are not here: their circuits land in the next pass (Phase 2); the 6x6 arm does not fit "
        "the emulator at all (DECISIONS.md OPEN-4)."
    )
    log(
        "[unverified] until the free syntax checker quotes them: whether Rz is charged, and whether "
        "the emulator charge equals this formula."
    )
    out = os.path.join(REPO, CONFIG.data_dir, "h2_hqc_budget.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
