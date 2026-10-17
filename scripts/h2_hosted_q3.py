"""Run the Q3 groups on the Nexus-HOSTED noiseless H2-1LE (free, cost verified 0) and compare with an
independent dense NumPy circuit-order Strang evolution (handoff/14). Needs a Nexus login.

The hosted emulator is noiseless, so a pass proves the PLUMBING and the circuit (qubit order, angles,
Pauli insertion bookkeeping, fold identity, Iceberg decoding) on the real platform; it is not an H2-1E
or hardware result and says nothing about noise. lam > 1 insertion circuits change the unitary (they
insert real Paulis), so only lam = 1 and the folded point (identity in the noiseless limit) are
compared with the ideal value; insertion points are reported against it for information.
Usage: .venv/bin/python -I scripts/h2_hosted_q3.py [--shots 500]  ->  data/h2_hosted_q3.txt
"""

# ruff: noqa: E501
from __future__ import annotations

import argparse
import os
import sys
import time
import warnings
from dataclasses import replace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
warnings.simplefilter("ignore")

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.dimers import TriangularDimers  # noqa: E402
from src.h2_backend import fetch_nexus  # noqa: E402
from src.h2_circuits import codes_records  # noqa: E402
from src.h2_driver import _by_shots, build_plan, execute  # noqa: E402
from src.h2_hosted import check_hosted_cost  # noqa: E402
from src.lattice import triangular_bonds  # noqa: E402
from src.mcmc_baseline import dimer_pattern, initial_spins  # noqa: E402

Q = CONFIG.q3


def exact_probs(Lx, Ly, spins0, n_steps):
    """Dense circuit-order Strang (X half, ZZ, X half), independent of pytket: exp(+i h dt/2 X) per
    site, diag exp(+i J dt ZZ) per bond, qubit 0 = MSB, bit 1 = spin -1."""
    N = Lx * Ly
    J, h, dt = Q.J, Q.noisy_h, Q.dt
    s = np.asarray(spins0).reshape(-1)
    psi = np.zeros(1 << N, dtype=complex)
    psi[int("".join(str((1 - int(v)) // 2) for v in s), 2)] = 1.0
    idx = np.arange(1 << N)
    z = [1 - 2 * ((idx >> (N - 1 - q)) & 1) for q in range(N)]
    diag = np.exp(1j * J * dt * sum(z[i] * z[j] for i, j in triangular_bonds(Lx, Ly, "periodic")))
    a = h * dt / 2
    c, sn = np.cos(a), np.sin(a)

    def xlayer(v):
        v = v.reshape([2] * N)
        for q in range(N):
            v = np.moveaxis(np.tensordot(np.array([[c, 1j * sn], [1j * sn, c]]), v, axes=([1], [q])), 0, q)
        return v.reshape(-1)

    for _ in range(n_steps):
        psi = xlayer(diag * xlayer(psi))
    return np.abs(psi) ** 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", type=int, default=CONFIG.noise_scaling.plan_shots)
    a = ap.parse_args()
    hw = replace(CONFIG.hardware, nexus_tier="hosted-le")
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log(f"# Nexus-HOSTED H2-1LE (noiseless, free) vs dense NumPy Strang -- {time.strftime('%Y-%m-%d %H:%M')}, {a.shots} shots per point")
    log("# NOT an H2-1E / hardware result; proves plumbing + circuit only. Observables: flippable density, defect density, memory (src/dimers.py).")
    log(f"{'group':12}{'item':26}{'qb':>3}{'accept':>7}{'flip (se) | exact':>30}{'defect (se) | exact':>30}{'mem (se) | exact':>28}  worst|z|")
    worst_all = 0.0
    for g in ("Q3-bare", "Q3-iceberg", "Q3-ladder", "Q3-bare-3x6"):
        plan = build_plan(g, a.shots)
        (Lx, Ly, kind) = plan.items[0].meta["case"]
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, CONFIG.ceilings.ed_max_spins)
        N = d.N
        flips = sum(d.flippable(s).astype(float) for s in range(N)) / N
        dens = d.total_defects() / (2 * N)
        n0 = dimer_pattern(d, s0)
        mem = np.stack([d.dimer(b) for b in d.bonds], axis=1).astype(float) @ n0 / N
        F = np.stack([flips, dens, mem])
        out = execute(plan, hw=hw, tier="hosted-le")
        jobs = out["jobs"]
        groups = _by_shots(plan.items)
        for job, (_, items) in zip(jobs, groups, strict=True):
            cb = [it.meta["layout"].cbits if "layout" in it.meta else it.meta["cbits"] for it in items]
            check_hosted_cost(job)
            raw = fetch_nexus(job, cb)
            for it, bits in zip(items, raw, strict=True):
                if "layout" in it.meta:
                    recs = codes_records(bits, it.meta["layout"])
                    acc = np.mean([r[0] for r in recs])
                    logical = np.array([(1 - r[1]) // 2 for r in recs if r[0]])
                else:
                    acc, logical = 1.0, bits
                idx = np.zeros(len(logical), dtype=np.int64)
                for j in range(N):
                    idx = (idx << 1) | logical[:, j].astype(np.int64)
                vals = F[:, idx]
                mean, se = vals.mean(1), vals.std(1, ddof=1) / np.sqrt(vals.shape[1])
                ex = F @ exact_probs(Lx, Ly, s0, it.meta["step"])
                z = (mean - ex) / np.where(se > 0, se, np.inf)
                comparable = it.meta.get("method", "none") != "insert"
                worst = float(np.max(np.abs(z))) if comparable else float("nan")
                if comparable:
                    worst_all = max(worst_all, worst)
                def cell(k, mean=mean, se=se, ex=ex):
                    return f"{mean[k]:+.4f} ({se[k]:.4f}) | {ex[k]:+.4f}"

                tag = "" if comparable else " (insertion: info only)"
                log(f"{g:12}{it.label:26}{it.n_qubits:>3}{acc:>7.3f}{cell(0):>30}{cell(1):>30}{cell(2):>28}  {worst:.2f}{tag}")
    log(f"# worst |z| over comparable points: {worst_all:.2f}  (expect ~< 3 over 19 points x 3 observables = 57 comparisons)")
    out = os.path.join(REPO, CONFIG.data_dir, "h2_hosted_q3.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
