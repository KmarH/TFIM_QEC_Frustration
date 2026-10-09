"""Q3 classical size story (handoff/08 Part B2) -> data/q3_size.txt.

What can be followed classically toward the 9x6 (54-spin) reference lattice, and how:
  1. the per-sector ergodic baseline (MCMC, src/mcmc_baseline.sample_sector): runs at any N;
  2. the noise budget of the bare and Iceberg-encoded circuits (Stim first-order fault accounting,
     src/noisy_q3.size_row): runs at any N, under the ASSUMED research/06 H2 prior.
The quantum relaxation curve itself cannot follow (state vector <= 24 spins, 2^N observable tables
<= 20; SCOPE §5): no thermodynamic-limit statement is made. CLASSICAL ONLY; NOT an H2 result.
Usage: python -I scripts/run_q3_size.py
"""

from __future__ import annotations

import math
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.dimers import TriangularDimers  # noqa: E402
from src.encoded_codes import NoiseRates  # noqa: E402
from src.mcmc_baseline import Shells, initial_spins, sample_sector  # noqa: E402
from src.noisy_q3 import size_row  # noqa: E402

Q = CONFIG.q3
S = CONFIG.sensitivity
C = CONFIG.ceilings
P1 = S.p2_prior * S.p1_ratio
NOISE = NoiseRates(p2=S.p2_prior, p1=P1, pm=P1, p_init=P1, zz_bias=S.zz_bias_prior)
H2_QUBITS = CONFIG.compare.n_data


def main():
    out = []

    def log(line=""):
        out.append(line)
        print(line, flush=True)

    log(f"# generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/run_q3_size.py (handoff/08 Part B2)")
    log("# CLASSICAL only (MCMC statistics; Stim first-order fault accounting under an ASSUMED noise model, the "
        "research/06 H2 prior). NOT quantum hardware, NOT an H2 result. No thermodynamic-limit claim.")

    log("\n## 1. Per-sector ergodic baseline vs size (W0 = (0, 0), 3-sublattice c0; uniform over the flip component; "
        f"MCMC {Q.n_chains} chains x {Q.n_sweeps} sweeps, SE from chain means) [measured]")
    log(f"  {'lattice':>8s} {'N':>4s} {'flippable_density':>20s} {'C(r=0.866)':>20s} {'dressing <g>':>20s} {'tau_int(mem)':>12s}")
    rows = []
    cases = [(3, 6), (6, 6), (9, 6)] + [(lx, ly) for lx, ly, _ in Q.size_mcmc_cases]
    for k, (Lx, Ly) in enumerate(cases):
        d = TriangularDimers(Lx, Ly)
        sh = Shells.build(d, Q.n_shells)
        t0 = time.time()
        r = sample_sector(d, initial_spins(d, "3-sublattice", C.ed_max_spins), sh, J=Q.J, dt=Q.dt, n_chains=Q.n_chains,
                          n_sweeps=Q.n_sweeps, burn_in=Q.burn_in, rng=np.random.default_rng(CONFIG.seed + 300 + k))
        f, c1, g = r.scalars["flippable_density"], r.shells[1], r.dressing
        rows.append((d.N, f.value, f.se, c1[0], c1[1]))
        log(f"  {Lx:>3d}x{Ly:<4d} {d.N:4d} {f.value:12.5f} ± {f.se:.5f} {c1[0]:+12.5f} ± {c1[1]:.5f} "
            f"{g.value:12.5f} ± {g.se:.5f} {r.scalars['memory'].tau_int:12.2f}   ({time.time() - t0:.0f}s)")
    n = np.array([r[0] for r in rows], float)
    for j, name in ((1, "flippable_density"), (3, "C(r=0.866)")):
        y = np.array([r[j] for r in rows])
        w = 1 / np.array([r[j + 1] for r in rows]) ** 2
        big = n >= 36
        slope, icpt = np.polyfit(1 / n[big], y[big], 1, w=np.sqrt(w[big]))   # w = 1/sigma
        log(f"  {name}: weighted fit y = a + b/N on N >= 36 [assumed fit form; inferred extrapolation]: "
            f"a (N->inf) = {icpt:+.4f}, b = {slope:+.3f}; spread of the N >= 36 values {np.ptp(y[big]):.4f}")

    log("\n## 2. Noise budget vs size: Stim first-order per-Trotter-step probabilities [derived accounting, ASSUMED noise]")
    log(f"#   noise: p2={NOISE.p2:g} (eta={NOISE.zz_bias:g}), p1=pm=p_init={P1:g}; h={Q.noisy_h}, dt={Q.dt}; "
        f"Q3 window = {Q.qdm_times}/h = {Q.qdm_times / Q.noisy_h:g} (= {int(round(Q.qdm_times / Q.noisy_h / Q.dt))} steps). "
        f"H2 has {H2_QUBITS} qubits (CompareConfig.n_data).")
    log("#   bare: P(any fault) per step (all unprotected). Iceberg: P(detected -> discarded) and P(undetected logical "
        "fault) per step; survival exp(-rate*steps) is the first-order prediction.")
    survive = Q.size_survival
    log(f"  {'lattice':>8s} {'N':>3s} {'ice phys':>8s} {'fits H2':>7s} {'bare fault':>10s} {'ice detect':>10s} {'ice undet':>10s} "
        f"{'faults/window bare':>18s} " + " ".join(f"{'t(ice surv=' + format(s, 'g') + ')':>17s}" for s in survive)
        + " " + " ".join(f"{'t(bare clean=' + format(s, 'g') + ')':>19s}" for s in survive))
    win = int(round(Q.qdm_times / Q.noisy_h / Q.dt))
    persite = []
    for Lx, Ly, kind in Q.size_stim_cases:
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        t0 = time.time()
        r = size_row(Lx, Ly, s0, J=Q.J, h=Q.noisy_h, dt=Q.dt, noise=NOISE)
        ts_ice = [Q.dt * math.log(1 / s) / r.ice_detected for s in survive]
        ts_bare = [Q.dt * math.log(1 / s) / r.bare_unprotected for s in survive]
        log(f"  {Lx:>3d}x{Ly:<4d} {r.n_logical:3d} {r.n_phys_iceberg:8d} {('yes' if r.n_phys_iceberg <= H2_QUBITS else 'NO'):>7s} "
            f"{r.bare_unprotected:10.4f} {r.ice_detected:10.4f} {r.ice_undetected:10.4f} {win * r.bare_unprotected:18.2f} "
            + " ".join(f"{t:17.2f}" for t in ts_ice) + " " + " ".join(f"{t:19.2f}" for t in ts_bare)
            + f"   ({time.time() - t0:.0f}s)")
        persite.append((Lx, Ly, r.bare_unprotected / r.n_logical, r.ice_detected / r.n_logical, r.ice_undetected / r.n_logical))
    log("  Per-site rates (rate / N) [derived]: " + "; ".join(f"{a}x{b}: bare {x:.2e}, ice det {y:.2e}, ice undet {z:.2e}"
                                                            for a, b, x, y, z in persite))
    log("  Bare and Iceberg-undetected rates are exactly linear in N; the Iceberg detection rate per site drifts down "
        "slightly with N: each syndrome round has an N-independent part (the +4 of its 2(N+2) CNOTs, the flag "
        "CNOTs, ancilla readout/reset), so its rate is a*N + c and the constant amortises. 'Linear in N' is approximate for it. Time to a fixed survival shrinks ~1/N.")
    with open(os.path.join(REPO, CONFIG.data_dir, "q3_size.txt"), "w") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote data/q3_size.txt")


if __name__ == "__main__":
    main()
