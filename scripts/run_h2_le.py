"""Validate the H2 circuits on the H2 LOCAL emulator (handoff/13; run in .venv-le).

Writes data/h2_le_validation.txt. Everything here is local: the offline LE (an ideal state vector,
docs/quantinuum_issues.md QI-2) and, for the noisy comparison, the same PECOS emulator with a
depolarizing model. A noisy number is a CLASSICAL PREDICTION under the ASSUMED generic model of
src/backends_qc.Noise, never an H2 result. No network, no login, no HQC.

Sections: 1 noiseless transparency (encoded == exact, plain and randomized-compiled); 2 bare
reference; 3 other codes (five-qubit by default; Steane and concatenated with --slow, they take
~0.25 and ~1.2 s per shot); 4 noisy emulator vs the repo's local-sim at the same rates, with the
modelling differences stated.

Usage: .venv-le/bin/python -I scripts/run_h2_le.py [--slow] [--shots N]
"""

# ruff: noqa: E501  (long report-text lines in log strings)
from __future__ import annotations

import argparse
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.backends_qc import Noise, local_exact_logical_z2, run, run_bare_local  # noqa: E402
from src.encoded_codes import EncodedTFIM, exact_logical_z2, make_code, stim_exact_z2  # noqa: E402
from src.encoded_tfim import IcebergTFIM, accepted, twirl_program, z2_from_logical  # noqa: E402
from src.h2_backend import offline_compile_backend, run_le  # noqa: E402
from src.h2_circuits import (  # noqa: E402
    bare_h2_circuit,
    bare_z,
    codes_h2_circuit,
    codes_records,
    compile_for_h2,
    encoded_h2_circuit,
    shot_records,
)

E = CONFIG.encoded
SEED = 20261017


def sig(z, ref, se):
    return (z - ref) / se if se and se > 0 else float("nan")


def iceberg_z2(spec, backend, n, shots, noise, rc, seed):
    """(acceptance, Z2, se) of the encoded program on the LE; RC splits shots over instances."""
    inst = E.rc_instances if rc else 1
    recs = []
    for i in range(inst):
        prog = twirl_program(spec, n, seed + i) if rc else None
        c, lay = encoded_h2_circuit(spec, n, prog)
        bits = run_le(compile_for_h2(c, backend), lay.cbits, shots // inst, seed + 1000 * i, noise)
        recs += shot_records(bits, lay, prog)
    acc = [accepted(r) for r in recs]
    zb = np.array(
        [spec.logical_from_bits(r.final[None, :])[0] for r, a in zip(recs, acc, strict=True) if a]
    )
    z2, se = z2_from_logical(zb)
    return float(np.mean(acc)), z2, se


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slow", action="store_true")
    ap.add_argument("--shots", type=int, default=4000)
    ap.add_argument("--out", default=None, help="output file (default data/h2_le_validation.txt)")
    a = ap.parse_args()
    backend = offline_compile_backend(CONFIG.hardware.le_device)
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log(f"# H2 local-emulator validation -- {time.strftime('%Y-%m-%d %H:%M')}  (shots {a.shots})")
    log(
        "# H2-1LE is an IDEAL state vector (QI-2). Noisy rows use the PECOS depolarizing model with "
        "src.backends_qc.Noise rates [ASSUMED]: classical predictions, NOT H2 results."
    )
    log()
    log("## 1. Noiseless transparency: encoded Iceberg on the LE vs the exact logical Z2")
    log("lattice steps   mode    accept     Z2 +- se        exact    (Z2-exact)/se")
    for lat in ((2, 2), (2, 3)):
        spec = IcebergTFIM(*lat, "periodic", E.J, E.h, E.dt, E.theta, 1)
        for n in (1, 2, 3):
            ex = local_exact_logical_z2(spec, n)
            for rc in (False, True):
                acc, z2, se = iceberg_z2(spec, backend, n, a.shots, None, rc, SEED)
                log(
                    f"{lat[0]}x{lat[1]}     {n}     {'RC   ' if rc else 'plain'}   {acc:6.4f}   "
                    f"{z2:.4f} +- {se:.4f}   {ex:.4f}   {sig(z2, ex, se):+.2f}"
                )
    log()
    log("## 2. Noiseless bare reference on the LE vs the same exact value (encoded == bare)")
    for lat in ((2, 2), (2, 3)):
        spec = IcebergTFIM(*lat, "periodic", E.J, E.h, E.dt, E.theta, 1)
        for n in (1, 3):
            c, cb = bare_h2_circuit(spec, n)
            zb = bare_z(run_le(compile_for_h2(c, backend), cb, a.shots, SEED))
            z2, se = z2_from_logical(zb)
            ex = local_exact_logical_z2(spec, n)
            log(
                f"bare {lat[0]}x{lat[1]} step {n}: Z2 {z2:.4f} +- {se:.4f}  exact {ex:.4f}  "
                f"({sig(z2, ex, se):+.2f} se)"
            )
    log()
    log("## 3. Other codes on the LE (detection only; round-0 feedforward as conditional gates)")
    cases = [("five", (1, 2), (1, 2, 3), 1000)]
    if a.slow:
        cases += [("steane", (1, 2), (1, 2), 300), ("concat", (2, 2), (1,), 150)]
    for name, lat, steps, sh in cases:
        prog = EncodedTFIM(
            make_code(name, lat[0] * lat[1]), *lat, "periodic", E.J, E.h, E.dt, E.theta
        )
        cl = EncodedTFIM(
            make_code(name, lat[0] * lat[1]),
            *lat,
            "periodic",
            E.clifford_J,
            E.clifford_h,
            E.dt,
            np.pi / 2,
        )  # as scripts/run_encoded_codes.py
        for n in steps:
            for tag, pr, ex in (
                ("generic ", prog, exact_logical_z2(prog, n)),
                ("Clifford", cl, stim_exact_z2(cl, n)),
            ):
                c, lay = codes_h2_circuit(pr, n)
                t = time.time()
                recs = codes_records(run_le(compile_for_h2(c, backend), lay.cbits, sh, SEED), lay)
                zb = np.array([r[1] for r in recs if r[0]])
                z2, se = z2_from_logical(zb)
                log(
                    f"{name:6} {lat[0]}x{lat[1]} step {n} {tag}: accept {np.mean([r[0] for r in recs]):.3f} "
                    f"Z2 {z2:.4f} +- {se:.4f} exact {ex:.4f} ({sig(z2, ex, se):+.2f} se) "
                    f"[{time.time() - t:.0f}s, {sh} shots]"
                )
    log()
    log(
        "## 4. Noisy emulator vs the repo's local-sim at the same ASSUMED rates (Iceberg 2x2, plain)"
    )
    log(
        "Differences are expected, not errors: local-sim charges rates per authored gate, the LE per "
        "COMPILED native gate (CX -> ZZPhase + 1q gates), so its one-qubit exposure is larger."
    )
    spec = IcebergTFIM(2, 2, "periodic", E.J, E.h, E.dt, E.theta, 1)
    for p2 in E.p2_scan[:2]:
        nz = Noise(p2=p2, p1=p2 * E.p1_ratio, pm=p2 * E.pm_ratio, p_init=p2 * E.init_ratio)
        for n in (1, 3):
            acc, z2, se = iceberg_z2(spec, backend, n, a.shots, nz, False, SEED)
            recs = run(spec, n, a.shots, nz, "local-sim", seed=SEED, max_spins=24)
            ac = [accepted(r) for r in recs]
            zl = np.array(
                [
                    spec.logical_from_bits(r.final[None, :])[0]
                    for r, k in zip(recs, ac, strict=True)
                    if k
                ]
            )
            z2l, sel = z2_from_logical(zl)
            log(
                f"p2={p2:g} step {n}: LE accept {acc:.3f} Z2 {z2:.4f}+-{se:.4f} | local-sim accept "
                f"{np.mean(ac):.3f} Z2 {z2l:.4f}+-{sel:.4f} | exact {local_exact_logical_z2(spec, n):.4f}"
            )
    for p2 in E.p2_scan[:2]:
        nz = Noise(p2=p2, p1=p2 * E.p1_ratio, pm=p2 * E.pm_ratio, p_init=p2 * E.init_ratio)
        c, cb = bare_h2_circuit(spec, 3)
        z2, se = z2_from_logical(bare_z(run_le(compile_for_h2(c, backend), cb, a.shots, SEED, nz)))
        z2l, sel = z2_from_logical(run_bare_local(spec, 3, a.shots, nz, SEED, 24).astype(float))
        log(f"bare p2={p2:g} step 3: LE Z2 {z2:.4f}+-{se:.4f} | local-sim Z2 {z2l:.4f}+-{sel:.4f}")
    out = a.out or os.path.join(REPO, CONFIG.data_dir, "h2_le_validation.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
