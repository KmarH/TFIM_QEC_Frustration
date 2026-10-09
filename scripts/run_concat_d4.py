"""Concatenated Iceberg d=4 gadget: verification + discard-rate report (handoff/01).

Writes data/concat_d4.txt. All settings from config.CONFIG.qec. Local Stim only.
Usage: python scripts/run_concat_d4.py
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CONFIG  # noqa: E402
from src.qec.concatenated import ConcatenatedIceberg, code_distance  # noqa: E402
from src.qec.concatenated_gadget import (  # noqa: E402
    CSSSpec, NoiseModel, build_memory_circuit, fault_distance, sample,
    undetected_low_weight_errors,
)
from src.qec.verify import verify_code  # noqa: E402


def main() -> None:
    q = CONFIG.qec
    code = ConcatenatedIceberg(q.k_inner, q.k_outer)
    spec = CSSSpec.from_concatenated(code)
    out = []
    log = lambda s="": (print(s), out.append(s))  # noqa: E731

    log(f"# Concatenated Iceberg [[{code.n},{code.k},4]] — inner k={q.k_inner}, outer k={q.k_outer}")
    log(f"# rounds={q.rounds}, flags={q.use_flags}, seed={CONFIG.seed}, {time.strftime('%Y-%m-%d %H:%M')}")
    log("# Noise [illustrative, NOT H2-calibrated]: DEPOLARIZE2(p) per CX, DEPOLARIZE1(p*%g) per H, "
        "X_ERROR(p*%g) meas/reset, DEPOLARIZE1(p*%g) idle per data qubit per stabilizer group"
        % (q.p1_ratio, q.pm_ratio, q.idle_ratio))
    log()
    rep = verify_code("concatenated Iceberg", code.n, code.stabilizers(), code.logical_x(), code.logical_z())
    log(rep.summary())
    d, wit = code_distance(code.n, code.stabilizers(), code.logical_x() + code.logical_z(), max_weight=4)
    log(f"code distance (M2-safe, measured): {d}   witness: {wit}")
    log(f"weight<=3 data errors undetected by circuit (both bases): {len(undetected_low_weight_errors(spec, 3, q.rounds))}")
    log()
    for flags in (True, False):
        for b in "ZX":
            gc = build_memory_circuit(spec, b, q.rounds, NoiseModel.from_config(q, 1e-3), use_flags=flags)
            fd = fault_distance(gc.circuit, 3)
            st = len(gc.circuit.search_for_undetectable_logical_errors(
                dont_explore_detection_event_sets_with_size_above=9999,
                dont_explore_edges_with_degree_above=9999,
                dont_explore_edges_increasing_symptom_degree=False,
                canonicalize_circuit_errors=True))
            log(f"fault distance flags={flags!s:5} basis={b}: exact<=3 search -> "
                f"{'>3' if fd is None else fd}; stim search -> {st}")
    log()
    log("p        basis  shots    discard_rate [95% CI]           post-sel logical rate [95% CI]   discards by level (flag/inner/outer)")
    for i, p in enumerate(q.p_scan):
        for b in "ZX":
            gc = build_memory_circuit(spec, b, q.rounds, NoiseModel.from_config(q, p), use_flags=q.use_flags)
            r = sample(gc, b, p, q.shots, seed=CONFIG.seed + 10 * i + (b == "X"))
            lo, hi = r.discard_ci
            llo, lhi = r.logical_ci
            lab = r.discard_by_label
            log(f"{p:<8.0e} {b:5}  {r.shots:<8d} {r.discard_rate:.4e} [{lo:.3e},{hi:.3e}]   "
                f"{r.logical_errors}/{r.kept} [{llo:.1e},{lhi:.1e}]   "
                f"{lab.get('flag',0)}/{lab.get('inner',0)}/{lab.get('outer',0)}")
    os.makedirs(CONFIG.data_dir, exist_ok=True)
    with open(os.path.join(CONFIG.data_dir, "concat_d4.txt"), "w") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
