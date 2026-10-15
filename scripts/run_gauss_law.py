"""Stage 3 Gauss-law study (handoff/02): constraint-violation scaling + mitigation benchmark.

Writes data/gauss_law_scaling.txt and data/gauss_law_mitigation.txt. All settings from
config.CONFIG.gauss. Local ED / statevector / density matrix only, within SCOPE §5.
Usage: python scripts/run_gauss_law.py [--skip-scaling]
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402
import scipy.sparse.linalg as sla  # noqa: E402

from config import CONFIG  # noqa: E402
from src.dimers import TriangularDimers  # noqa: E402
from src.gauss_mitigation import (  # noqa: E402
    Targets, evolve_dm, evolve_trajectories, pec_gamma_single, richardson,
    single_error_detection, trotter_unitary,
)
from src.operators import tfim_hamiltonian  # noqa: E402
from src.trotter import ising_diagonal, trotter2_step  # noqa: E402

G = CONFIG.gauss


def most_flippable_state(d: TriangularDimers) -> np.ndarray:
    """Defect-free basis state with the most flippable spins (richest constrained dynamics);
    the 3-sublattice state when the torus allows it."""
    if d.Lx % 3 == 0 and d.Ly % 3 == 0:
        return d.three_sublattice_spins()
    free = np.nonzero(d.total_defects() == 0)[0]
    nflip = sum(d.flippable(s)[free].astype(int) for s in range(d.N))
    idx = int(free[np.argmax(nflip)])
    bits = [(idx >> (d.N - 1 - s)) & 1 for s in range(d.N)]
    return (1 - 2 * np.array(bits)).reshape(d.Ly, d.Lx)


def slope(x, y):
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


# --------------------------------------------------------------------------- #
def scaling(log) -> None:
    log("# Gauss-law violation vs h/|J|  (noiseless; J=%g)" % G.J)
    log("# defect density = <sum_t D_t>/(2N) per triangle; leak = P(W != W0); T = 20/|J|, time-averaged")
    hs = np.array(G.h_scan)
    cases = [(3, 4, "stripe", (0.25, 0.025)), (3, 4, "flippable", (0.25,)), (3, 6, "3-sublattice", (0.25,))]
    for Lx, Ly, kind, dts in cases:
        d = TriangularDimers(Lx, Ly)
        spins = d.stripe_spins() if kind == "stripe" else most_flippable_state(d)
        i0 = d.product_state_index(spins)
        Dn = d.total_defects() / (2 * d.N)
        wx, wy = d.winding_x(0), d.winding_y(0)
        W0 = (int(wx[i0]), int(wy[i0]))
        diag = ising_diagonal(d.N, d.bonds, G.J)
        for dt in dts:
            dd, lk = [], []
            for h in hs:
                n = int(round(20.0 / dt))
                psi = np.zeros(1 << d.N, complex)
                psi[i0] = 1
                acc = leak = 0.0
                rec = max(1, n // 80)
                for s in range(1, n + 1):
                    psi = trotter2_step(psi, d.N, diag, h, dt)
                    if s % rec == 0:
                        p = np.abs(psi) ** 2
                        acc += p @ Dn
                        leak += p[(wx != W0[0]) | (wy != W0[1])].sum()
                dd.append(acc / (n // rec))
                lk.append(leak / (n // rec))
            log(f"{Lx}x{Ly} {kind:12s} W0={W0} dt={dt:<6} defect/tri: "
                + " ".join(f"{v:.3e}" for v in dd) + f"  slope={slope(hs, dd):.2f}"
                + "   leak: " + " ".join(f"{v:.2e}" for v in lk) + f"  slope={slope(hs, lk):.2f}")
            if kind == "stripe":
                log(f"    stripe first-order prediction (h/|J|)^2/8: "
                    + " ".join(f"{h * h / 8:.3e}" for h in hs)
                    + f"   measured/predicted at smallest h: {dd[0] / (hs[0] ** 2 / 8):.3f}")
    for Lx, Ly in [(3, 4), (3, 6)]:
        d = TriangularDimers(Lx, Ly)
        gs = []
        for h in hs:
            v = sla.eigsh(tfim_hamiltonian(d.N, d.bonds, G.J, h), k=1, which="SA")[1][:, 0]
            gs.append(d.defect_density(v))
        log(f"{Lx}x{Ly} ED ground state     defect/tri: " + " ".join(f"{v:.3e}" for v in gs)
            + f"  slope={slope(hs, gs):.2f}")
    log("h_scan = " + " ".join(f"{h:g}" for h in hs))
    # noiseless acceptance of zero-defect postselection at our working h (physics floor cost;
    # h/|J| = 0.3 is our own choice, not the reference's triangular field; DECISIONS.md OPEN-1)
    for Lx, Ly in [(3, 3), (3, 6)]:
        d = TriangularDimers(Lx, Ly)
        i0 = d.product_state_index(d.three_sublattice_spins())
        psi = np.zeros(1 << d.N, complex)
        psi[i0] = 1
        D = d.total_defects()
        diag = ising_diagonal(d.N, d.bonds, G.J)
        acc = []
        for s in range(1, G.n_steps + 1):
            psi = trotter2_step(psi, d.N, diag, G.h, G.dt)
            acc.append(float((np.abs(psi) ** 2)[D == 0].sum()))
        log(f"{Lx}x{Ly} ({2 * d.N} triangles) h={G.h} dt={G.dt}: noiseless P(zero defects) "
            f"min over t<= {G.n_steps * G.dt:g} = {min(acc):.4f}, at t_final = {acc[-1]:.4f}")


# --------------------------------------------------------------------------- #
def mitigation(log) -> None:
    d = TriangularDimers(G.dm_Lx, G.dm_Ly)
    spins = most_flippable_state(d)
    i0 = d.product_state_index(spins)
    psi0 = np.zeros(1 << d.N, complex)
    psi0[i0] = 1
    U = trotter_unitary(d.N, d.bonds, G.J, G.h, G.dt)
    T = Targets.build(d, spins)
    steps = G.n_steps
    ideal = evolve_dm(psi0, d.N, U, steps, (0.0, 0.0, 0.0))
    eval_steps = (steps // 3, steps)
    c = richardson(G.zne_lambdas)
    zne_cost = len(G.zne_lambdas) * float(np.sum(c ** 2))

    log(f"# Mitigation benchmark: {d.Lx}x{d.Ly} torus (N={d.N}, {2 * d.N} triangles), exact density matrix")
    log(f"# J={G.J}, h={G.h}, dt={G.dt}, initial = most-flippable defect-free product state, "
        f"Trotter steps {steps} (t={steps * G.dt:g})")
    log("# noise: per Trotter step, per qubit Pauli channel, total prob p split as (px,py,pz) [assumption]")
    log(f"# ZNE: Richardson on lambda={G.zne_lambdas}, coeffs={np.round(c, 3).tolist()}, "
        f"sampling cost {zne_cost:.1f}x; shots per circuit for error bars: {G.shots}")
    log("# cost = shot multiplier for equal statistical error; err = sqrt(bias^2 + cost*Var/shots)")
    for s in eval_steps:
        pf = ideal[s]
        ps0, acc0 = T.postselect(pf)
        log(f"\n## t = {s * G.dt:g}: ideal (noiseless Trotter) values: "
            + ", ".join(f"{n}={v:+.4f}" for n, v in zip(T.names, T.raw(pf))))
        log(f"   physics floor: defect/tri={T.defect_density(pf):.4e}; noiseless postselection keeps "
            f"{acc0:.4f} and biases targets by " + ", ".join(f"{v:+.4f}" for v in ps0 - T.raw(pf)))
        det = single_error_detection(d, pf)
        log(f"   single-error defect-detection prob at this time: X/Y={det['X']:.3f}, Z={det['Z']:.3f}")

    rows = []
    for cname, frac in G.channels:
        for p in G.p_scan:
            runs = {lam: evolve_dm(psi0, d.N, U, steps, tuple(lam * p * f for f in frac))
                    for lam in G.zne_lambdas}
            gamma = pec_gamma_single(tuple(p * f for f in frac)) ** (2 * d.N * steps)
            for s in eval_steps:
                pi, pn = ideal[s], runs[1.0][s]
                Oi = T.raw(pi)
                var = T.shot_variance(pn)
                obar = np.array([v.mean() for v in T.values])
                F_obs = (T.raw(pn) - obar) / (Oi - obar)
                est = {"raw": (T.raw(pn), 1.0)}
                o, acc = T.postselect(pn)
                est["postselect"] = (o, 1 / acc)
                o, F = T.selfmit(pn, T.defect_density(pi))
                est["selfmit-oracle"] = (o, 1 / F ** 2)
                o, F0 = T.selfmit(pn, 0.0)
                est["selfmit-naive"] = (o, 1 / F0 ** 2)
                est["zne"] = (sum(ci * T.raw(runs[l][s]) for ci, l in zip(c, G.zne_lambdas)), zne_cost)
                est["pec"] = (Oi, gamma)
                log(f"\n## channel={cname} p={p:g} t={s * G.dt:g}: defect/tri={T.defect_density(pn):.4e} "
                    f"(floor {T.defect_density(pi):.4e}); F_gauss={F:.4f}; per-target true F="
                    + ", ".join(f"{v:.4f}" for v in F_obs))
                log(f"   {'method':15s} " + "  ".join(f"{n[:22]:>34s}" for n in T.names) + "     cost")
                for m, (o, cost) in est.items():
                    bias = o - Oi
                    err = np.sqrt(bias ** 2 + cost * var / G.shots)
                    log(f"   {m:15s} " + "  ".join(f"bias {b:+.4f} err {e:.4f}".rjust(34) for b, e in zip(bias, err))
                        + f"   {cost:.3g}x")
                    rows.append((cname, p, s, m, bias, err, cost))

    # sensitivity of the Gauss-law signal to each Pauli type
    log("\n## sensitivity: d(defect/tri)/dp at t=final vs damage d|target bias|/dp  (p=1e-3, pure channels)")
    for lbl, frac in [("X", (1, 0, 0)), ("Y", (0, 1, 0)), ("Z", (0, 0, 1))]:
        r = evolve_dm(psi0, d.N, U, steps, tuple(1e-3 * f for f in frac))[steps]
        dD = (T.defect_density(r) - T.defect_density(ideal[steps])) / 1e-3
        dO = (T.raw(r) - T.raw(ideal[steps])) / 1e-3
        log(f"   pure {lbl}: dD/dp={dD:+.3f}   dO/dp=" + ", ".join(f"{v:+.3f}" for v in dO))

    # Trajectory cross-check on a second cluster
    d2 = TriangularDimers(G.traj_Lx, G.traj_Ly)
    sp2 = most_flippable_state(d2)
    psi2 = np.zeros(1 << d2.N, complex)
    psi2[d2.product_state_index(sp2)] = 1
    T2 = Targets.build(d2, sp2)
    log(f"\n## cross-check {d2.Lx}x{d2.Ly} (N={d2.N}) Monte-Carlo trajectories, n={G.traj_n}, "
        f"t={steps * G.dt:g}, p=3e-3; errors = batch-mean standard error")
    ideal2 = evolve_trajectories(psi2, d2.N, d2.bonds, G.J, G.h, G.dt, steps, (0, 0, 0), 1, 0)[0][steps]
    log("   ideal: " + ", ".join(f"{n}={v:+.4f}" for n, v in zip(T2.names, T2.raw(ideal2)))
        + f"; floor defect/tri={T2.defect_density(ideal2):.4e}")
    for cname, frac in G.channels:
        mean, batch = evolve_trajectories(psi2, d2.N, d2.bonds, G.J, G.h, G.dt, steps,
                                          tuple(3e-3 * f for f in frac), G.traj_n, CONFIG.seed)
        def stats(fn):
            vals = np.array([fn(b[steps]) for b in batch])
            return fn(mean[steps]), vals.std(0, ddof=1) / np.sqrt(len(vals))
        raw, raw_se = stats(lambda q: T2.raw(q) - T2.raw(ideal2))
        ps, ps_se = stats(lambda q: T2.postselect(q)[0] - T2.raw(ideal2))
        sm, sm_se = stats(lambda q: T2.selfmit(q, T2.defect_density(ideal2))[0] - T2.raw(ideal2))
        dD, dD_se = stats(lambda q: np.array([T2.defect_density(q)]))
        log(f"   {cname:12s} defect/tri={dD[0]:.4e}+-{dD_se[0]:.1e}")
        for lbl, v, e in (("raw", raw, raw_se), ("postselect", ps, ps_se), ("selfmit-oracle", sm, sm_se)):
            log(f"      {lbl:15s} bias " + ", ".join(f"{a:+.4f}+-{b:.4f}" for a, b in zip(v, e)))

    # PEC overhead at reference scale for context
    nref, stepsref = 54, 40
    for p in G.p_scan:
        g = pec_gamma_single((p / 3, p / 3, p / 3)) ** (2 * nref * stepsref)
        log(f"   PEC sampling overhead gamma^2, depolarizing p={p:g}, N={nref}, {stepsref} steps: {g:.3g}")


def main() -> None:
    out = []

    def log(s=""):
        print(s, flush=True)
        out.append(s)

    os.makedirs(CONFIG.data_dir, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M")
    if "--skip-scaling" not in sys.argv:
        log(f"# generated {stamp} by scripts/run_gauss_law.py")
        scaling(log)
        with open(os.path.join(CONFIG.data_dir, "gauss_law_scaling.txt"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(out) + "\n")
        out.clear()
    log(f"# generated {stamp} by scripts/run_gauss_law.py")
    mitigation(log)
    with open(os.path.join(CONFIG.data_dir, "gauss_law_mitigation.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
