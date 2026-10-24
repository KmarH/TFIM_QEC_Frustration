"""Local-emulator check of the EXACT encoded lambda > 1 circuits that would be submitted to H2
(DECIDED-9; Stage 6b of the 2026-10-24 pass). Run it in the LE environment:

    .venv-le/Scripts/python -I scripts/le_q3_encoded_lambda.py      (Windows; .venv-le/bin/python)

What it does. The 3x4 Iceberg-encoded Q3 circuit (src/h2_q3.triangular_iceberg_h2_circuit) is
built, given lambda = 3 by src/h2_q3.iceberg_noise_scaled_circuits (a Pauli before every two-qubit
gate with probability (lambda - 1) q_P, the research/06 prior channel), compiled for H2 and run on
the NOISELESS local emulator (PECOS), so the only errors are the inserted Paulis. Averaged over the
insertion instances, the detector acceptance must match Stim's first-order prediction for the
inserted channel alone, exp(-detected_total) at p2' = (lambda - 1) p2 with 1q / SPAM noise off - a
different code path (fault propagation, not execution). At lambda = 1 the acceptance must be 1.

Free tier (local emulator, pre-approved); nothing touches Nexus; no HQC. The result is a check of
the circuit's construction, not an H2 result. Writes data/q3_le_encoded_lambda.txt.
"""

from __future__ import annotations

import math
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np

from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates, detected_total
from src.h2_backend import offline_compile_backend, run_le
from src.h2_circuits import compile_for_h2
from src.h2_q3 import iceberg_noise_scaled_circuits, triangular_iceberg_h2_circuit
from src.mcmc_baseline import initial_spins
from src.noisy_q3 import make_iceberg

STEPS, LAM, INSTANCES, SHOTS = 2, 3, 40, 20


def acceptance(bits: np.ndarray, layout) -> float:
    ok = np.ones(len(bits), dtype=bool)
    for det in layout.detectors:
        ok &= (bits[:, det].sum(axis=1) % 2) == 0
    return float(ok.mean())


def main() -> None:
    Q, S = CONFIG.q3, CONFIG.sensitivity
    d = TriangularDimers(3, 4)
    s0 = initial_spins(d, "flippable", CONFIG.ceilings.ed_max_spins)
    base, layout = triangular_iceberg_h2_circuit(3, 4, s0, STEPS, Q.J, Q.noisy_h, Q.dt)
    be = offline_compile_backend()
    out = ["# data/q3_le_encoded_lambda.txt - exact encoded lambda circuits on the NOISELESS local",
           "# H2 emulator (PECOS); only the inserted Paulis act. Construction check, NOT an H2",
           "# result; free tier, no Nexus, no HQC. scripts/le_q3_encoded_lambda.py",
           (f"# 3x4 Iceberg, {STEPS} Trotter steps, h = {Q.noisy_h}, lambda = {LAM}, "
            f"{INSTANCES} instances x {SHOTS} shots")]
    (plain,) = iceberg_noise_scaled_circuits(base, 1)
    bits = run_le(compile_for_h2(plain.circuit, be), layout.cbits, SHOTS, seed=1)
    a1 = acceptance(bits, layout)
    out.append(f"lambda = 1: acceptance {a1:.4f} over {SHOTS} shots (must be 1: transparency)")
    accs = []
    for sc in iceberg_noise_scaled_circuits(base, LAM, instances=INSTANCES, seed=2026):
        b = run_le(compile_for_h2(sc.circuit, be), layout.cbits, SHOTS, seed=sc.instance + 7)
        accs.append(acceptance(b, layout))
    accs = np.array(accs)
    m, se = float(accs.mean()), float(accs.std(ddof=1) / math.sqrt(len(accs)))
    prog = make_iceberg(d, s0, Q.J, Q.noisy_h, Q.dt)
    inserted = NoiseRates(p2=(LAM - 1) * S.p2_prior, p1=0.0, pm=0.0, p_init=0.0,
                          zz_bias=S.zz_bias_prior)
    pred = math.exp(-detected_total(prog, inserted, STEPS))
    out.append(f"lambda = {LAM}: mean acceptance over instances {m:.4f} +- {se:.4f}; Stim first-order "
               f"prediction for the inserted channel {pred:.4f}; deviation {(m - pred) / se:+.1f} sigma")
    path = os.path.join(REPO, CONFIG.data_dir, "q3_le_encoded_lambda.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
