"""Iceberg-encoded TFIM: Stim verification + noisy Z2/discard curves through the toggle.

handoff/04 Part A. Writes data/encoded_iceberg.txt. Settings: config.CONFIG.encoded.
Usage: python scripts/run_encoded.py [--backends local-sim,selene] [--quick]

Every noisy number here is a CLASSICAL PREDICTION under an ASSUMED generic depolarizing
model; none is an H2 hardware result. Stim proves the fault-tolerance facts; local-sim and
selene execute the authored pytket/Guppy program.
"""

from __future__ import annotations

import argparse
import dataclasses
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.backends import MemoryCeilingError  # noqa: E402
from src.backends_qc import (  # noqa: E402
    Noise, local_exact_logical_z2, run, run_bare_local,
)
from src.compare import simulate_z2  # noqa: E402
from src.encoded_tfim import (  # noqa: E402
    IcebergTFIM, accepted, build_stim, single_fault_report, stim_exact_logical_z2,
    weight1_injection_all_detected, z2_from_logical,
)
from src.qec.iceberg import IcebergCode  # noqa: E402
from src.qec.verify import verify_code  # noqa: E402

CAVEAT = ("CAVEAT [SCOPE §3/§12]: classical prediction under an ASSUMED generic depolarizing "
          "model (rates below are declared assumptions, not measurements, not H2-calibrated). "
          "Not an H2 result. Stim proves FT facts; local-sim/selene execute the program.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backends", default="local-sim,selene")
    ap.add_argument("--quick", action="store_true", help="few shots/steps (smoke test, not written)")
    args = ap.parse_args()
    E = CONFIG.encoded
    maxs = CONFIG.ceilings.statevector_max_spins
    steps = list(E.steps[:2] if args.quick else E.steps)
    shots_l = 60 if args.quick else E.shots_local
    shots_s = 60 if args.quick else E.shots_selene
    p2s = list(E.p2_scan[-1:] if args.quick else E.p2_scan)
    backends = [b for b in args.backends.split(",") if b]
    spec = IcebergTFIM(E.Lx, E.Ly, E.boundary, E.J, E.h, E.dt, E.theta, E.syndrome_every)
    out = []

    def log(s=""):
        print(s, flush=True)
        out.append(s)

    log(f"# Encoded TFIM (Iceberg [[{spec.k + 2},{spec.k},2]]) — {time.strftime('%Y-%m-%d %H:%M')}"
        + (" [QUICK SMOKE RUN]" if args.quick else ""))
    log(f"# logical lattice {E.Lx}x{E.Ly} {E.boundary}, k={spec.k}, physical n={spec.n_phys} "
        f"(k+2 code, 1 ancilla, 1 flag); J={E.J} h={E.h} dt={E.dt} theta={E.theta:.6f}; "
        f"syndrome round every {E.syndrome_every} step(s)")
    log("# " + CAVEAT)

    # ---------------------------------------------------------------- 1. Stim verification
    log("\n## 1. Verification (Stim; rotations act as identity for Pauli-fault propagation)")
    code = IcebergCode(spec.k)
    rep = verify_code(f"Iceberg k={spec.k}", code.n, code.stabilizers(),
                      [code.logical_x(i) for i in range(spec.k)],
                      [code.logical_z(i) for i in range(spec.k)])
    log(f"verify_code on the block: {'PASS' if rep.ok else 'FAIL'}")
    nv = max(2, min(3, steps[-1]))
    for b in "ZX":
        d, o = build_stim(spec, nv, basis=b).compile_detector_sampler(seed=1).sample(256, separate_observables=True)
        log(f"clean run ({b}-basis image, {nv} steps): detectors silent {not d.any()}, observables clean {not o.any()}")
    ok1, missed = weight1_injection_all_detected(spec, nv)
    log(f"every weight-1 X/Y/Z on every code qubit after every Trotter step detected: {ok1} {missed[:5]}")
    rep_f = single_fault_report(spec, nv)
    log("single-fault mechanisms that flip a logical observable while firing no detector, per class:")
    for cls, v in rep_f.items():
        kinds = sorted({"".join(c for c in p if c.isalpha()) for p in v["paulis"]})
        log(f"  {cls:6s} mechanisms={v['mechanisms']:5d}  undetected-logical={v['undetected_logical']:4d}  "
            f"Pauli types={kinds}")
    log("VERDICT: syndrome extraction (flagged CX), H, measurement, reset and idle locations are "
        "single-fault safe; the LOGICAL ROTATION gates are NOT: a single fault on a logical gate "
        "can leave XX, YY or ZZ on that gate's own two qubits, which commutes with S_X and S_Z and "
        "is a nontrivial logical operator (distance-2 code, weight-2 logical gates).")

    # ---------------------------------------------- 2. consistency + transparency (zero noise)
    log("\n## 2. Zero-noise checks")
    cl = IcebergTFIM(E.Lx, E.Ly, E.boundary, E.clifford_J, E.clifford_h, E.dt, E.clifford_theta,
                     E.syndrome_every)
    log(f"Clifford instance (J dt={E.clifford_J * E.dt:.4f}, h dt={E.clifford_h * E.dt:.4f}, theta={E.clifford_theta}):")
    for s in steps[:4]:
        st = stim_exact_logical_z2(cl, s)
        lo = local_exact_logical_z2(cl, s)
        ba = simulate_z2(E.Lx, E.Ly, E.boundary, E.clifford_J, E.clifford_h, E.dt, E.clifford_theta, [s], maxs)[0]
        line = f"  step {s}: Stim exact {st:.6f} | local-sim exact {lo:.6f} | bare simulate_z2 {ba:.6f}"
        if "selene" in backends:
            recs = run(cl, s, shots_s, Noise(), "selene", seed=100 + s, max_spins=maxs)
            acc = [r for r in recs if accepted(r)]
            z, se = z2_from_logical(cl.logical_from_bits(np.array([r.final for r in acc])))
            line += f" | selene sampled {z:.4f}±{se:.4f} (accepted {len(acc)}/{len(recs)})"
        log(line)
    ideal = simulate_z2(E.Lx, E.Ly, E.boundary, E.J, E.h, E.dt, E.theta, steps, maxs)
    enc0 = np.array([local_exact_logical_z2(spec, s) for s in steps])
    log(f"encoding transparency at the physical parameters: max|Z2_encoded - Z2_bare| = "
        f"{np.abs(enc0 - ideal).max():.2e} over steps {steps}")

    # ---------------------------------------------------------------- 3. noisy curves
    log("\n## 3. Noisy runs (post-selected logical Z2 and discard rate per Trotter step)")
    log("columns: ideal = noiseless circuit Z2; enc = encoded, accepted shots only; bare = same "
        "logical circuit on k bare qubits at the same per-gate rates (local-sim); errors are 1 SE")
    for p2 in p2s:
        nz = Noise(p2=p2, p1=p2 * E.p1_ratio, pm=p2 * E.pm_ratio, p_init=p2 * E.init_ratio, p_idle=E.p_idle)
        log(f"\n### p2={p2:g}, p1={nz.p1:g}, pm={nz.pm:g}, p_init={nz.p_init:g}, p_idle={nz.p_idle:g}  [assumed]")
        hdr = f"{'step':>4} {'ideal':>7}"
        for b in backends:
            hdr += f" | {b + ' accept':>16} {b + ' enc Z2':>18} {'|dev|':>6}"
        hdr += f" | {'bare Z2':>15} {'|dev|':>6}"
        log(hdr)
        for k_, s in enumerate(steps):
            row = f"{s:>4} {ideal[k_]:>7.4f}"
            for b in backends:
                recs = run(spec, s, shots_l if b == "local-sim" else shots_s, nz, b,
                           seed=1000 * s + int(p2 * 1e6), max_spins=maxs)
                acc = np.array([accepted(r) for r in recs])
                ar = acc.mean()
                ase = np.sqrt(ar * (1 - ar) / len(acc))
                if acc.sum() >= 2:
                    z, se = z2_from_logical(spec.logical_from_bits(np.array([r.final for r, a in zip(recs, acc) if a])))
                else:
                    z, se = float("nan"), float("nan")
                row += f" | {ar:>9.3f}±{ase:.3f} {z:>10.4f}±{se:.4f} {abs(z - ideal[k_]):>6.3f}"
            zb = run_bare_local(spec, s, shots_l, nz, seed=7000 + s, max_spins=maxs)
            zz, zse = z2_from_logical(zb)
            row += f" | {zz:>8.4f}±{zse:.4f} {abs(zz - ideal[k_]):>6.3f}"
            log(row)

    # ---------------------------------------------------------------- 4. toggle + ceiling
    log("\n## 4. Toggle and ceiling")
    try:
        run(spec, 1, 1, Noise(), "nexus", seed=0, max_spins=maxs)
    except NotImplementedError as e:
        log(f"nexus backend: NotImplementedError('{e}')")
    big = IcebergTFIM(4, 6, "periodic", E.J, E.h, E.dt, E.theta)
    try:
        run(big, 1, 1, Noise(), "local-sim", seed=0, max_spins=maxs)
    except MemoryCeilingError as e:
        log(f"4x6 logical lattice (n_phys={big.n_phys}) refused before allocation: {e}")

    if not args.quick:
        with open(os.path.join(REPO, CONFIG.data_dir, "encoded_iceberg.txt"), "w") as fh:
            fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
