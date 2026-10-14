"""Trotter-ordering comparison (peer-review MAJOR fix) -> data/trotter_order_compare.txt.

`src/trotter.trotter2_step` is the ZZ-outside (ABA) Strang splitting; the published H2 circuits
(arXiv:2503.20870) use the X-outside splitting, now additively provided as
`src/trotter.circuit_trotter2_step` (same formula as `src/compare.circuit_trotter_states`). The
two step operators are unitarily conjugate (same quasienergies, hence the same Trotter-threshold
location), but observables read out along the way differ between the two frames.

This script computes, for the Q3 defect-free quench starts, the late-window (last half of the
curve, matching src/mcmc_baseline.relaxation_curve / src/trotter_threshold.late_window_bias) RAW
(not sector-conditioned) defect density and P_out (weight outside the defect-free W0 sector), at
the working dt = 0.25, for THREE arms: exact (Chebyshev) evolution, the ZZ-outside Trotter step,
and the circuit-order Trotter step. It reports the two Trotter/exact ratios side by side so the
sign flip documented in docs/q3_thermalization.md §8 (and the one surviving conclusion: the dt =
0.25 threshold brackets, which do NOT depend on this ordering choice) is directly reproducible.

All settings from config.CONFIG.q3 / CONFIG.ceilings (same J, dt, qdm_times, late_fraction,
max_snapshots as the existing Q3 curves). Classical, noiseless simulation only; NOT quantum
hardware, NOT an H2 result. Does not touch any existing committed data file.
Usage: python -I scripts/run_trotter_order_compare.py
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
from src.mcmc_baseline import Shells, initial_spins  # noqa: E402
from src.trotter import circuit_trotter2_step, ising_diagonal, trotter2_step  # noqa: E402
from src.trotter_threshold import ExactPropagator  # noqa: E402

Q = CONFIG.q3
C = CONFIG.ceilings
CAVEAT = ("# CLASSICAL noiseless simulation only (exact Chebyshev evolution vs the TWO 2nd-order "
          "Strang orderings); NOT quantum hardware, NOT an H2 result. No noise model.")

# (Lx, Ly, start kind, [h values]) - the clusters/fields the docs quote (handoff/ordering-fix brief).
# 3x6 is the "~40%" headline cluster; kept to h=0.3 only to fit the CPU budget (2 cores, serial).
CASES = (
    (3, 3, "3-sublattice", (0.1, 0.3)),
    (3, 4, "flippable", (0.1, 0.3)),
    (3, 6, "3-sublattice", (0.3,)),
)


def late_window_both_orders(d: TriangularDimers, spins0: np.ndarray, *, J: float, h: float,
                            dt: float, total_time: float, max_snapshots: int, late_fraction: float,
                            max_spins: int):
    """Late-window raw defect density and P_out for exact / ZZ-outside / circuit-order arms.

    Mirrors src/trotter_threshold.late_window_bias's snapshot grid and window exactly (so the
    numbers are directly comparable to the committed data/trotter_threshold.txt and
    data/q3_relaxation.txt), but runs on a pluggable step function instead of being limited to
    trotter2_step, since that module is a verified core and is not touched by this fix.
    """
    n_steps = int(round(total_time / dt))
    rec = max(1, math.ceil(n_steps / max_snapshots))
    diag = ising_diagonal(d.N, d.bonds, J)
    D = d.total_defects() / (2 * d.N)
    i0 = d.product_state_index(spins0)
    wx, wy = d.winding_x(0), d.winding_y(0)
    in_sector = (d.total_defects() == 0) & (wx == wx[i0]) & (wy == wy[i0])
    U = ExactPropagator(d, J, h, max_spins=max_spins)

    def raw(psi):
        p = np.abs(psi) ** 2
        return float(p @ D), 1.0 - float(p[in_sector].sum())

    psi_zz = np.zeros(1 << d.N, dtype=np.complex128)
    psi_zz[i0] = 1.0
    psi_circ, psi_exact = psi_zz.copy(), psi_zz.copy()

    times = [0.0]
    series = {"exact": [raw(psi_exact)], "zz": [raw(psi_zz)], "circuit": [raw(psi_circ)]}
    for step in range(1, n_steps + 1):
        psi_zz = trotter2_step(psi_zz, d.N, diag, h, dt)
        psi_circ = circuit_trotter2_step(psi_circ, d.N, diag, h, dt)
        if step % rec == 0:
            psi_exact = U(psi_exact, rec * dt)
            times.append(step * dt)
            series["exact"].append(raw(psi_exact))
            series["zz"].append(raw(psi_zz))
            series["circuit"].append(raw(psi_circ))

    times = np.array(times)
    late = np.nonzero(times >= (1.0 - late_fraction) * times[-1])[0]

    def window_means(arm):
        dd = np.mean([series[arm][k][0] for k in late])
        po = np.mean([series[arm][k][1] for k in late])
        return float(dd), float(po)

    return {arm: window_means(arm) for arm in ("exact", "zz", "circuit")}


def main():
    out = []

    def log(line=""):
        out.append(line)
        print(line, flush=True)

    log(f"# generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/run_trotter_order_compare.py "
        "(peer-review ordering fix)")
    log(CAVEAT)
    log(f"# Frustrated triangular TFIM, J={Q.J}, dt={Q.dt}; total_time = {Q.qdm_times}/h per the "
        "Q3 convention; late window = last "
        f"{Q.late_fraction:.0%} of the curve, same snapshot grid as data/q3_relaxation.txt / "
        "data/trotter_threshold.txt. defect_density = <sum_t D_t>/2N (RAW, full state, src/dimers.py "
        "definition). P_out = weight outside the defect-free, same-winding-as-c0 sector (RAW). "
        "Both are evaluated on the exact (Chebyshev) curve and on BOTH Trotter orderings: 'zz' = "
        "src/trotter.trotter2_step (ZZ-outside, the ordering the rest of this repo's docs used), "
        "'circuit' = src/trotter.circuit_trotter2_step (X-outside, what the published H2 circuits "
        "implement; src/compare.py).")
    log(f"\n{'cluster':22s} {'h':>5s} {'observable':14s} {'exact':>10s} "
        f"{'zz':>10s} {'zz/exact':>9s} {'circuit':>10s} {'circuit/exact':>14s}")

    for Lx, Ly, kind, hs in CASES:
        d = TriangularDimers(Lx, Ly)
        s0 = initial_spins(d, kind, C.ed_max_spins)
        for h in hs:
            t0 = time.time()
            res = late_window_both_orders(
                d, s0, J=Q.J, h=h, dt=Q.dt, total_time=Q.qdm_times / h,
                max_snapshots=Q.max_snapshots, late_fraction=Q.late_fraction,
                max_spins=C.ed_max_spins)
            for k, obs in enumerate(("defect_density", "p_out")):
                e = res["exact"][k]
                zz = res["zz"][k]
                ci = res["circuit"][k]
                rz = zz / e if e != 0 else float("nan")
                rc = ci / e if e != 0 else float("nan")
                log(f"  {Lx}x{Ly} {kind:14s} {h:5.2f} {obs:14s} {e:10.5f} "
                    f"{zz:10.5f} {rz:9.3f} {ci:10.5f} {rc:14.3f}")
            print(f"    ({Lx}x{Ly} {kind} h={h}: {time.time() - t0:.0f}s)", flush=True)

    log("\n# Reading: 'zz/exact' > 1 ('circuit/exact' < 1) reproduces the documented sign flip - "
        "the ZZ-outside ordering INFLATES these quantities at dt=0.25, h*dt=0.5, while the "
        "published circuit's own ordering DEFLATES them relative to continuous time. This affects "
        "only which frame an absolute number is read in; it does not change the dt=0.25 "
        "Trotter-threshold location (src/trotter_threshold.py), which is a quasienergy statement "
        "and is the same in both orderings.")

    with open(os.path.join(REPO, CONFIG.data_dir, "trotter_order_compare.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote data/trotter_order_compare.txt")


if __name__ == "__main__":
    main()
