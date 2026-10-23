"""OFFLINE HQC cost of the Q3 generalization study's cells (Stage 5 of the D1-D6 study).

What a hypothetical H2 run of these cells WOULD cost, from compiled gate counts and the standard
formula. **Fully offline: no network, no login, no job, no HQC spent.** The project's hard rule
stands - nothing reaches Nexus or hardware without the project lead's per-run approval - and this
script has no submission path at all.

Reuse only: the circuits are src/h2_q3.triangular_bare_h2_circuit /
triangular_iceberg_h2_circuit (the same programs the trajectory sweep simulates), compiled by
src/h2_circuits.compile_for_h2 against the OFFLINE backend, counted by native_counts and priced by
hqc_estimate (Rz-free by default, DECISIONS D-HQC: the free H2-1SC quotes equalled the Rz-free
estimate to the cent).

Windows: the encoded arm is priced over its SURVIVAL-MATCHED window (data/q3_scaling.txt), the same
window the sweep measured, so the cost and the accuracy belong to the same experiment. The bare arm
is priced over its physics window qdm_times / h, which is what a bare + Gauss run would need.

Usage: .venv/Scripts/python.exe -I scripts/run_q3_hqc.py
"""

from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from config import CONFIG
from src.dimers import TriangularDimers
from src.h2_backend import offline_compile_backend
from src.h2_circuits import compile_for_h2, hqc_estimate, native_counts
from src.h2_q3 import triangular_bare_h2_circuit, triangular_iceberg_h2_circuit
from src.mcmc_baseline import initial_spins
from src.q3_scaling import SIZE_TO_CASE

# The D4 cells actually run by the sweep, with the survival-matched encoded window of
# data/q3_scaling.txt: (N, h, lam, ice_steps).
CELLS: tuple[tuple[int, float, int, int], ...] = (
    (12, 0.1, 1, 48), (12, 0.2, 1, 48), (12, 0.3, 1, 48), (12, 0.5, 1, 48),
    (12, 0.3, 2, 28), (12, 0.3, 3, 19), (12, 0.5, 3, 19),
    (18, 0.3, 1, 36), (18, 0.1, 3, 13),
    (20, 0.3, 1, 33), (20, 0.5, 3, 12),
)
SHOTS = 500          # per circuit, pre post-selection [assumed, = NoiseScalingConfig.plan_shots]


def main() -> None:
    q3 = CONFIG.q3
    backend = offline_compile_backend(CONFIG.hardware.le_device)
    out: list[str] = []

    def log(line: str = "") -> None:
        out.append(line)
        print(line)

    log("# Q3 generalization study - OFFLINE HQC estimate. data/q3_hqc.txt")
    log("# CLASSICAL ESTIMATE from compiled gate counts and the standard formula")
    log("#   HQC = 5 + shots * (N1q + 10 N2q + 5 Nm) / 5000 [established, research/07].")
    log("# NO job was submitted, NO login was used, NO HQC was spent. Not an H2 result.")
    log(f"# Rz-free pricing (DECISIONS D-HQC). Shots per circuit: {SHOTS} [assumed].")
    log("# Encoded arm priced over its SURVIVAL-MATCHED window (data/q3_scaling.txt); bare arm")
    log("#   over its physics window qdm_times / h. One circuit per cell per arm.")
    log(f"# Compile: TKET level 0 against the offline backend for {CONFIG.hardware.le_device}.")

    log(f"\n  {'N':>4s} {'h':>5s} {'lam':>4s} {'arm':>8s} {'steps':>6s} {'qubits':>7s} "
        f"{'n1q':>7s} {'nrz':>6s} {'n2q':>7s} {'nmeas':>6s} {'HQC':>10s}")
    totals = {"bare": 0.0, "bare@ice": 0.0, "iceberg": 0.0}
    rows: list[tuple] = []
    for n_logical, h, lam, ice_steps in CELLS:
        Lx, Ly, kind = SIZE_TO_CASE[n_logical]
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, CONFIG.ceilings.ed_max_spins)
        bare_steps = round((q3.qdm_times / h) / q3.dt)
        # "bare@ice" prices the bare circuit over the ENCODED window, which is the only
        # like-for-like HQC comparison: "bare" covers a much longer physics window and so buys a
        # different measurement. Without this row the encoded arm looks cheap merely for stopping
        # early.
        for arm, steps in (("bare", bare_steps), ("bare@ice", ice_steps), ("iceberg", ice_steps)):
            if arm.startswith("bare"):
                c, _ = triangular_bare_h2_circuit(Lx, Ly, s0, steps, q3.J, h, q3.dt)
            else:
                c, _ = triangular_iceberg_h2_circuit(Lx, Ly, s0, steps, q3.J, h, q3.dt)
            cnt = native_counts(compile_for_h2(c, backend))
            hqc = hqc_estimate(cnt, SHOTS)
            totals[arm] += hqc
            rows.append((n_logical, h, lam, arm, steps, cnt, hqc))
            log(f"  {n_logical:>4d} {h:>5g} {lam:>4g} {arm:>8s} {steps:>6d} "
                f"{cnt['nqubits']:>7d} {cnt['n1q']:>7d} {cnt['nrz']:>6d} {cnt['n2q']:>7d} "
                f"{cnt['nmeas']:>6d} {hqc:>10.1f}")

    log(f"\n# Totals over the {len(CELLS)} cells at {SHOTS} shots each: "
        f"bare(full window) {totals['bare']:.0f} HQC, bare(encoded window) {totals['bare@ice']:.0f} HQC, Iceberg {totals['iceberg']:.0f} HQC, "
        f"both arms {totals['bare'] + totals['iceberg']:.0f} HQC.")
    log("# For scale: the 50,000 HQC allowance and the 39,853 HQC already planned "
        "(docs/h2_budget.md).")
    log("# These are OFFLINE estimates. The free H2-1SC syntax checker would replace them with")
    log("#   server quotes at zero HQC; it needs a NEXUS_REFRESH_TOKEN, absent on this machine.")
    log("# Nothing here is approved to run: every HQC-spending run needs the project lead's")
    log("#   per-run go (CLAUDE.md, docs/nexus_toggle.md).")

    path = os.path.join(REPO, CONFIG.data_dir, "q3_hqc.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {os.path.relpath(path, REPO)}")


if __name__ == "__main__":
    main()
