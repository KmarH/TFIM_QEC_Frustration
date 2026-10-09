"""Part B (handoff/04): Steane, 5-qubit, concatenated-d4 (and Iceberg via the same pipeline).

Decisions recorded by Kevin (2026-10-07): FT standard B = measured accounting, no pass/fail bar;
budget (ii) = H2 ~55 physical qubits for build/discard, Stim at budget size, execution only at
reduced size <= statevector ceiling; residual = MEASURED (Stim) undetected-logical rate.
Writes data/encoded_codes.txt line by line. Every noisy number is a classical prediction under
an ASSUMED generic depolarizing model; none is an H2 result.
Usage: python scripts/run_encoded_codes.py [--skip-exec | --exec-only]
  --exec-only appends section 5 (Selene execution) to an existing data/encoded_codes.txt.
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.backends_qc import Noise, run_bare_local  # noqa: E402
from src.compare import simulate_z2  # noqa: E402
from src.encoded_codes import (  # noqa: E402
    BareTFIM, EncodedTFIM, NoiseRates, detected_total, exact_logical_z2, gate_counts,
    logical_pauli_table, make_code, run_selene, to_stim, undetected_rate_per_step,
)
from src.encoded_tfim import IcebergTFIM  # noqa: E402
from src.qec.verify import verify_code  # noqa: E402

E = CONFIG.encoded
MAXS = CONFIG.ceilings.statevector_max_spins
H2 = 55
CODES = ["iceberg", "steane", "five", "concat"]
REDUCED = {"iceberg": (2, 2), "steane": (1, 2), "five": (1, 2), "concat": (2, 2)}
BUDGET_LATTICES = [(1, 2), (2, 2), (2, 3), (2, 4), (3, 4), (4, 4)]
SHOTS = {"iceberg": 1000, "five": 400, "steane": 300, "concat": 150}


def main():
    skip_exec = "--skip-exec" in sys.argv
    exec_only = "--exec-only" in sys.argv
    path = os.path.join(REPO, CONFIG.data_dir, "encoded_codes.txt")
    fh = open(path, "a" if exec_only else "w")

    def log(s=""):
        print(s, flush=True)
        fh.write(s + "\n")
        fh.flush()

    if exec_only:
        return execute(log, fh)
    log(f"# Part B encoded-TFIM comparison — {time.strftime('%Y-%m-%d %H:%M')}")
    log("# Standard B (measured accounting, no pass/fail FT bar); budget (ii): H2 ~55 qubits; "
        "Stim at budget size; execution (selene) at reduced size <= 24 qubits.")
    log("# CAVEAT: classical predictions under ASSUMED generic depolarizing noise; not H2 results.")

    # ------------------------------------------------------------- 1. budget table
    log("\n## 1. Physical-qubit budget (data + 1 syndrome/rotation ancilla + 1 flag)")
    log(f"{'code':8s} " + " ".join(f"{f'{a}x{b}':>7s}" for a, b in BUDGET_LATTICES) + "   (<=24 local | <=55 H2)")
    for name in CODES:
        cells = []
        for a, b in BUDGET_LATTICES:
            k = a * b
            if name == "iceberg" and k % 2:
                cells.append("   odd")
                continue
            n = EncodedTFIM(make_code(name, k), a, b, "periodic", E.J, E.h, E.dt, E.theta).n_phys
            mark = "L" if n <= MAXS else ("H" if n <= H2 else "x")
            cells.append(f"{n:>5d}{mark:>2s}")
        log(f"{name:8s} " + " ".join(cells))
    log("   L = runs locally and fits H2; H = fits H2 only (Stim verification only here); x = exceeds ~55")

    # ------------------------------------------------- 2. logical-gate cost per step
    log("\n## 2. Logical operation cost (reduced lattice) — physical ops per Trotter step")
    for name in CODES:
        a, b = REDUCED[name]
        prog = EncodedTFIM(make_code(name, a * b), a, b, "periodic", E.J, E.h, E.dt, E.theta)
        gc = gate_counts(prog)
        log(f"{name:8s} {a}x{b}: weights field Xbar={prog.rep_x(0).weight}, bond ZbarZbar="
            f"{prog.rep_zz(*prog.bonds[0]).weight}, prep Ybar={prog.rep_y(0).weight}; per step: "
            f"{gc['2q']} two-qubit, {gc['1q']} one-qubit, {gc['meas']} measurements; "
            f"stabilizers per round {len(prog.stabs)}")
    bare = BareTFIM(2, 2, "periodic", E.J, E.h, E.dt, E.theta)
    log(f"bare     2x2: per step {len(bare.bonds)} two-qubit, {2 * bare.k} one-qubit")

    # ------------------------------------------------- 3. verification, reduced size
    log("\n## 3. Verification at the reduced (executable) size")
    for name in CODES:
        a, b = REDUCED[name]
        code = make_code(name, a * b)
        rep = verify_code(code.name, code.n, code.stabilizers, code.logical_x, code.logical_z)
        prog = EncodedTFIM(code, a, b, "periodic", E.J, E.h, E.dt, E.theta)
        silent = all(not to_stim(prog.schedule(2, bs), NoiseRates()).compile_detector_sampler(seed=1)
                     .sample(64, separate_observables=True)[i].any() for bs in "ZX" for i in (0, 1))
        trans = max(abs(exact_logical_z2(prog, s) - simulate_z2(a, b, "periodic", E.J, E.h, E.dt, E.theta, [s], MAXS)[0])
                    for s in (1, 2, 3))
        cl = EncodedTFIM(code, a, b, "periodic", E.clifford_J, E.clifford_h, E.dt, np.pi / 2)
        worst = max(np.abs(np.subtract(*logical_pauli_table(cl, s)[1:])).max() for s in (1, 2))
        log(f"{name:8s} {a}x{b}: verify_code {'PASS' if rep.ok else 'FAIL'}; clean Stim images silent {silent}; "
            f"transparency max|dZ2| {trans:.1e}; Stim<->local over all {4 ** prog.k} logical Paulis "
            f"(Clifford instance) max|d| {worst:.1e}")

    # ------------------------------------------------- 4. accounting at budget size
    log("\n## 4. MEASURED undetected-logical probability per Trotter step (Stim, first order)")
    for p2 in E.p2_scan[:2]:
        nz = NoiseRates(p2=p2, p1=p2 * E.p1_ratio, pm=p2 * E.pm_ratio, p_init=p2 * E.init_ratio)
        log(f"\n### p2={p2:g}, p1=pm=p_init={p2 * E.p1_ratio:g} [assumed]")
        for lat in [(1, 2), (2, 2), (2, 3)]:
            a, b = lat
            row = []
            for name in CODES:
                if name == "iceberg" and (a * b) % 2:
                    row.append(f"{name} n/a")
                    continue
                prog = EncodedTFIM(make_code(name, a * b), a, b, "periodic", E.J, E.h, E.dt, E.theta)
                if prog.n_phys > H2:
                    row.append(f"{name} >55")
                    continue
                u = undetected_rate_per_step(prog, nz)
                acc3 = np.exp(-detected_total(prog, nz, 3))
                row.append(f"{name}(n={prog.n_phys}) undetected {u['total']:.2e} acc@3 {acc3:.3f}")
            ub = undetected_rate_per_step(BareTFIM(a, b, "periodic", E.J, E.h, E.dt, E.theta), nz)["total"]
            log(f"{a}x{b}: " + " | ".join(row) + f" | bare unprotected {ub:.2e}")
    log("   acc@3 = exp(-first-order detection probability of the 3-step program incl. prep) [Stim]")

    if skip_exec:
        fh.close()
        return
    execute(log, fh)


def execute(log, fh):
    # ------------------------------------------------- 5. execution (selene), reduced size
    log(f"\n## 5. Executed on Selene (Quest) at the reduced size; bare = local-sim, same rates "
        f"({time.strftime('%Y-%m-%d %H:%M')})")
    for name in CODES:
        a, b = REDUCED[name]
        prog = EncodedTFIM(make_code(name, a * b), a, b, "periodic", E.J, E.h, E.dt, E.theta)
        ideal = simulate_z2(a, b, "periodic", E.J, E.h, E.dt, E.theta, [1, 2, 3], MAXS)
        sp_bare = IcebergTFIM(a, b, "periodic", E.J, E.h, E.dt, E.theta) if (a * b) % 2 == 0 else None
        for p2 in E.p2_scan[:2]:
            nz = NoiseRates(p2=p2, p1=p2 * E.p1_ratio, pm=p2 * E.pm_ratio, p_init=p2 * E.init_ratio)
            for s in (1, 2, 3):
                t = time.time()
                res = run_selene(prog, s, SHOTS[name], nz, seed=11 * s + int(p2 * 1e5), max_spins=MAXS,
                                 n_processes=2)
                acc = np.array([x for x, _ in res])
                vals = np.array([v for x, v in res if x])
                ar = acc.mean()
                if len(vals) >= 2:
                    m2 = (vals.sum(1) ** 2) / prog.k ** 2
                    z, se = m2.mean(), m2.std(ddof=1) / np.sqrt(len(m2))
                else:
                    z, se = float("nan"), float("nan")
                bl = ""
                if sp_bare is not None:
                    zb = run_bare_local(sp_bare, s, 1000, Noise(p2=nz.p2, p1=nz.p1, pm=nz.pm, p_init=nz.p_init),
                                        seed=500 + s, max_spins=MAXS)
                    mb = (zb.sum(1).astype(float) ** 2) / prog.k ** 2
                    bl = f" | bare Z2 {mb.mean():.4f}±{mb.std(ddof=1) / np.sqrt(len(mb)):.4f}"
                log(f"{name:8s} {a}x{b} p2={p2:g} step {s}: accept {ar:.3f}±{np.sqrt(ar * (1 - ar) / len(acc)):.3f} "
                    f"(n={len(acc)}) | enc Z2 {z:.4f}±{se:.4f} | ideal {ideal[s - 1]:.4f}{bl} ({time.time() - t:.0f}s)")
    fh.close()


if __name__ == "__main__":
    main()
