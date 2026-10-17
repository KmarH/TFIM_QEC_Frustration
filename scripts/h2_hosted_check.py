"""Prove the Nexus submit / fetch / post-process path on the Nexus-HOSTED noiseless emulator H2-1LE
(handoff/13), BEFORE any HQC is spent. Free per Quantinuum's docs (Simulation quota in seconds, not
HQC); `check_hosted_cost` verifies the server reports no cost and aborts loudly otherwise. Needs a
Nexus login. Compares each result with the exact value and with the offline local emulator.

The hosted emulator is noiseless, so a pass proves the PLUMBING (upload, execute, result retrieval,
classical-register ordering, frame corrections, conditional gates) on the real platform, not any noisy
physics. It says nothing about H2-1E (HQC, noisy, <= 32 qubits).

Usage: .venv/bin/python -I scripts/h2_hosted_check.py [--shots 1000]  ->  data/h2_hosted_check.txt
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

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.backends_qc import local_exact_logical_z2  # noqa: E402
from src.encoded_codes import EncodedTFIM, exact_logical_z2, make_code, stim_exact_z2  # noqa: E402
from src.encoded_tfim import IcebergTFIM, accepted, twirl_program, z2_from_logical  # noqa: E402
from src.h2_backend import fetch_nexus, offline_compile_backend  # noqa: E402
from src.h2_circuits import (  # noqa: E402
    bare_h2_circuit,
    bare_z,
    codes_h2_circuit,
    codes_records,
    compile_for_h2,
    encoded_h2_circuit,
    shot_records,
)
from src.h2_hosted import check_hosted_cost, submit_hosted_le  # noqa: E402

E = CONFIG.encoded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=1000)
    a = ap.parse_args()
    backend = offline_compile_backend(CONFIG.hardware.le_device)
    ice = IcebergTFIM(2, 2, "periodic", E.J, E.h, E.dt, E.theta, 1)
    five = EncodedTFIM(make_code("five", 2), 1, 2, "periodic", E.J, E.h, E.dt, E.theta)
    five_cl = EncodedTFIM(make_code("five", 2), 1, 2, "periodic", E.clifford_J, E.clifford_h, E.dt, np.pi / 2)
    tw = {n: twirl_program(ice, n, 11 + n) for n in (1, 3)}

    items = []  # (label, circuit, cbits, decode(bits) -> (acc, z2, se), exact)

    def ice_decode(prog, lay):
        def f(bits):
            recs = shot_records(bits, lay, prog)
            ac = [accepted(r) for r in recs]
            zb = np.array([ice.logical_from_bits(r.final[None, :])[0] for r, k in zip(recs, ac, strict=True) if k])
            return (float(np.mean(ac)), *z2_from_logical(zb))
        return f

    for n in (1, 3):
        for rc in (False, True):
            prog = tw[n] if rc else None
            c, lay = encoded_h2_circuit(ice, n, prog)
            items.append((f"Iceberg 2x2 step {n} {'RC' if rc else 'plain'}", compile_for_h2(c, backend), lay.cbits, ice_decode(prog, lay), local_exact_logical_z2(ice, n)))
    for n in (1, 3):
        c, cb = bare_h2_circuit(ice, n)
        items.append((f"bare 2x2 step {n}", compile_for_h2(c, backend), cb, lambda bits: (1.0, *z2_from_logical(bare_z(bits))), local_exact_logical_z2(ice, n)))
    for tag, pr, n, ex in (("generic", five, 2, exact_logical_z2(five, 2)), ("Clifford", five_cl, 2, stim_exact_z2(five_cl, 2))):
        c, lay = codes_h2_circuit(pr, n)

        def dec(bits, lay=lay):
            recs = codes_records(bits, lay)
            return (float(np.mean([r[0] for r in recs])), *z2_from_logical(np.array([r[1] for r in recs if r[0]])))
        items.append((f"five-qubit 1x2 step {n} {tag} (conditional gates)", compile_for_h2(c, backend), lay.cbits, dec, ex))

    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log(f"# Hosted noiseless emulator H2-1LE on Nexus -- {time.strftime('%Y-%m-%d %H:%M')}  ({a.shots} shots/circuit)")
    log("# NOISELESS: proves plumbing on the real platform, not noisy physics. No HQC (cost checked below).")
    job = submit_hosted_le([i[1] for i in items], a.shots, project="tfim-qec-h2")
    log(f"job {job.id}: submitted {len(items)} circuits")
    log(f"server-reported cost: {check_hosted_cost(job)} HQC")
    out = fetch_nexus(job, [i[2] for i in items])
    log(f"{'circuit':58}{'accept':>8}{'Z2 +- se':>20}{'exact':>9}{'z':>7}")
    for (label, _, _, dec, ex), bits in zip(items, out, strict=True):
        acc, z2, se = dec(bits)
        log(f"{label:58}{acc:>8.3f}{z2:>12.4f} +- {se:.4f}{ex:>9.4f}{(z2 - ex) / se:>+7.2f}")
    path = os.path.join(REPO, CONFIG.data_dir, "h2_hosted_check.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
