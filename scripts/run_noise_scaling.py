"""6x6 noise-scaling arm (T-17 / R-14) -> data/noise_scaling.txt.

What it computes (CLASSICAL ONLY, under the ASSUMED research/06 H2 prior; NOT an H2 result):
  1. 3x4 validation by trajectories (src/noise_scaling.run_bare_scaled): Pauli-insertion ladder
     lam = (1, 2, 3) and the folded lam = 3 point; the slope diagnostic and the fixed-asymptote
     exponential extrapolation (D1-D5), raw and Gauss-conditioned, against the ideal circuit;
  2. sigma_1, the per-shot SD of the flippable density, from ideal 3x4 / 3x6 distributions;
  3. the 6x6 first-order (Stim) rates at each lam (src/noise_scaling.scaled_stim_rates);
  4. a 6x6 shot and HQC plan (an ESTIMATE; nothing is submitted, SCOPE §5).
Decisions and derivation: research/derivations/01-noise-scaling-arm.md.
Usage: python -I scripts/run_noise_scaling.py
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
from src.noise_scaling import (  # noqa: E402
    extrapolate_exp,
    hqc_cost,
    run_bare_scaled,
    scaled_stim_rates,
    slope_test,
)
from src.noisy_q3 import NoisyRun, TriangularBareTFIM, make_iceberg, run_bare, run_observables  # noqa: E402

NS = CONFIG.noise_scaling
Q = CONFIG.q3
S = CONFIG.sensitivity
C = CONFIG.ceilings
P1 = S.p2_prior * S.p1_ratio
NOISE = NoiseRates(p2=S.p2_prior, p1=P1, pm=P1, p_init=P1, zz_bias=S.zz_bias_prior)
OBS = "flippable_density"


def flips_table(d: TriangularDimers) -> np.ndarray:
    """Per-configuration flippable density (src/trotter_threshold.observable_function's table)."""
    return sum(d.flippable(s).astype(np.float64) for s in range(d.N)) / d.N


def sector_mask(d: TriangularDimers, s0) -> np.ndarray:
    i0 = d.product_state_index(s0)
    wx, wy = d.winding_x(0), d.winding_y(0)
    return (d.total_defects() == 0) & (wx == wx[i0]) & (wy == wy[i0])


def uniform_run(N: int) -> NoisyRun:
    return NoisyRun("uniform", np.array([0]), Q.dt, np.full((1, 1, 1 << N), 1.0 / (1 << N)),
                    np.ones((1, 1)), 1)


def main():
    out = []

    def log(line=""):
        print(line, flush=True)
        out.append(line)

    t_start = time.time()
    stamp = time.strftime("%Y-%m-%d %H:%M")
    log(f"# generated {stamp} by scripts/run_noise_scaling.py (T-17 / R-14)")
    log("# CLASSICAL PREDICTION UNDER AN ASSUMED NOISE MODEL (research/06 H2 prior) — NOT an H2 / "
        "hardware result. Nothing here was submitted anywhere.")
    log(f"# Noise [assumed]: p2={NOISE.p2} (eta={NOISE.zz_bias}), p1=pm=p_init={P1:g}; no idle, "
        "leakage, crosstalk or coherent error. h=0.3, dt=0.25, J=-1.")
    log("# Decisions (the project lead, 2026-10-16): D1 diagnostic first, extrapolation reported "
        "only "
        "if the chi2 test passes; D2 Pauli insertion before 2q gates (lam ladder) + one folded "
        "lam=3 point; D3 bare + Gauss post-selection only; D4 lam=(1,2,3), exponential; D5 "
        "asymptote "
        "fixed at the infinite-T value; D6 folded circuits compile at TKET level 0.")
    log(f"# Slope 'resolved' at |z| >= {NS.z_min} [assumed]; fit 'consistent' at chi2 p >= "
        f"{NS.p_consistent} [assumed].")
    log()

    # ---------------- 1. 3x4 validation ----------------
    Lx, Ly, kind = NS.val_case
    d = TriangularDimers(Lx, Ly)
    s0 = initial_spins(d, kind, C.ed_max_spins)
    sh = Shells.build(d, Q.n_shells)
    kw = dict(J=Q.J, h=Q.noisy_h, dt=Q.dt, n_steps=NS.val_steps, noise=NOISE, n_traj=NS.val_traj,
              n_batches=NS.val_batches, record_every=NS.val_record_every, max_spins=C.ed_max_spins)
    runs = {}
    for i, (method, lam) in enumerate([("insert", 1), ("insert", 2), ("insert", 3), ("fold", 3)]):
        t0 = time.time()
        rng = np.random.default_rng(500 + i)
        run = run_bare_scaled(d, s0, lam=lam, method=method, rng=rng, **kw)
        runs[(method, lam)] = (run, run_observables(d, s0, sh, run, C.ed_max_spins))
        print(f"  {method} lam={lam}: {time.time() - t0:.0f}s", flush=True)
    ideal_run = run_bare(d, s0, rng=np.random.default_rng(0),
                         **{**kw, "noise": NoiseRates(), "n_traj": 1, "n_batches": 1})
    ideal = run_observables(d, s0, sh, ideal_run, C.ed_max_spins)
    uni = run_observables(d, s0, sh, uniform_run(d.N), C.ed_max_spins)
    B = {"raw": float(uni.raw[OBS][0][0]), "cond": float(uni.cond[OBS][0][0])}
    log(f"## 1. {Lx}x{Ly} start={kind} validation: {NS.val_traj} trajectories x {NS.val_batches} "
        f"batches per point; flippable density [measured; classical prediction]")
    log(f"#   asymptotes (exact, uniform distribution): raw (full space) {B['raw']:.4f}, "
        f"cond (W0 sector, = B_W0) {B['cond']:.4f}")
    log("#   insert ladder lam=(1,2,3): z = slope/se; O0 = fixed-asymptote exponential (shown only "
        "when consistent, else '--'); fold: lam=(1,3) slope and closed-form two-point O0")
    lams = np.array([1.0, 2.0, 3.0])
    for mode in ("raw", "cond"):
        I_v = getattr(ideal, mode)[OBS][0]
        log(f"  [{mode}]    t   ideal    O(1)±se         O(2)      O(3)     z_ins  O0_ins (chi2,p)"
            f"           O(3,fold)  z_fold  O0_fold   |O(1)-ideal| |O0_ins-ideal|")
        for t in range(1, len(ideal_run.steps)):
            v = np.array([getattr(runs[("insert", int(lam))][1], mode)[OBS][0][t] for lam in lams])
            s = np.array([getattr(runs[("insert", int(lam))][1], mode)[OBS][1][t] for lam in lams])
            r = slope_test(lams, v, s)
            e = extrapolate_exp(lams, v, s, asymptote=B[mode])
            vf = getattr(runs[("fold", 3)][1], mode)[OBS]
            rf = slope_test([1.0, 3.0], [v[0], vf[0][t]], [s[0], vf[1][t]])
            ratio = (vf[0][t] - B[mode]) / (v[0] - B[mode])
            o0f = B[mode] + (v[0] - B[mode]) / math.sqrt(ratio) if ratio > 0 else float("nan")
            o0 = f"{e.O0:.4f}±{e.se:.4f} ({e.chi2:4.2f},{e.p_value:.2f})" if e.consistent else \
                f"--     ({e.chi2:5.2f},{e.p_value:.2f})"
            err0 = f"{abs(e.O0 - I_v[t]):.4f}" if e.consistent else "--"
            log(f"  {'':8s}{ideal.times[t]:4.1f}  {I_v[t]:.4f}  {v[0]:.4f}±{s[0]:.4f}  {v[1]:.4f}  "
                f"{v[2]:.4f}  {r.z:+6.2f}  {o0:28s}  {vf[0][t]:.4f}  {rf.z:+6.2f}  {o0f:.4f}"
                f"      {abs(v[0] - I_v[t]):.4f}       {err0}")
    pin = runs[("insert", 1)][1].p_in
    steps = ideal_run.steps
    k = np.polyfit(steps[1:], -np.log(pin[1:]), 1)[0]
    bare34 = scaled_stim_rates(TriangularBareTFIM(Lx, Ly, "periodic", Q.J, Q.noisy_h, Q.dt, 0.0),
                               NOISE, 1.0)["bare_or_undetected"]
    f_gauss = k / bare34
    log(f"  Gauss acceptance decay at lam=1 [measured]: -d ln p_in / d step = {k:.5f} vs Stim bare "
        f"fault rate {bare34:.5f}/step -> fraction of faults leaving the sector "
        f"f_G = {f_gauss:.3f}")
    log()

    # ---------------- 2. sigma_1 ----------------
    log("## 2. sigma_1 = per-shot SD of the flippable density, Gauss-conditioned [measured]: "
        "ideal circuit (N <= 18) and the sector ensemble B_W0 by MCMC (any N)")
    sig = {}
    for Lx2, Ly2, kind2 in NS.sigma_cases:
        d2 = TriangularDimers(Lx2, Ly2)
        s2 = initial_spins(d2, kind2, C.ed_max_spins)
        r2 = run_bare(d2, s2, rng=np.random.default_rng(0), J=Q.J, h=Q.noisy_h, dt=Q.dt,
                      n_steps=NS.val_steps, noise=NoiseRates(), n_traj=1, n_batches=1,
                      record_every=NS.val_record_every, max_spins=C.ed_max_spins)
        f = flips_table(d2)
        m = sector_mask(d2, s2)
        vals = []
        for p in r2.mixture()[1:]:
            pc = np.where(m, p, 0.0)
            pc = pc / pc.sum()
            vals.append(math.sqrt(max(pc @ f ** 2 - (pc @ f) ** 2, 0.0)))
        sig[d2.N] = float(np.mean(vals))
        log(f"  {Lx2}x{Ly2} (N={d2.N}): sigma_1 over t=2..8 mean {np.mean(vals):.4f} "
            f"(min {min(vals):.4f}, max {max(vals):.4f})")
    # sqrt(N) scaling FAILED on these numbers (sigma grows from N=12 to 18), so 6x6 is measured
    # in the sector ensemble instead: sigma_1 = se_naive * sqrt(n_sweeps * n_chains), exactly.
    smc = {}
    for Lx2, Ly2, kind2 in (NS.sigma_cases[-1], NS.target):
        d2 = TriangularDimers(Lx2, Ly2)
        s2 = initial_spins(d2, kind2, C.ed_max_spins)
        r = sample_sector(d2, s2, Shells.build(d2, Q.n_shells), J=Q.J, dt=Q.dt,
                          n_chains=Q.n_chains, n_sweeps=Q.n_sweeps, burn_in=Q.burn_in,
                          rng=np.random.default_rng(7))
        e = r.scalars[OBS]
        smc[d2.N] = e.se_naive * math.sqrt(Q.n_sweeps * Q.n_chains)
        log(f"  {Lx2}x{Ly2} (N={d2.N}) sector ensemble (MCMC {Q.n_chains}x{Q.n_sweeps}): "
            f"sigma_1 {smc[d2.N]:.4f} (mean {e.value:.4f})")
    n_cal = max(sig)
    ratio = max(1.0, max(sig.values()) / smc[n_cal])
    sig36 = smc[36] * ratio
    log(f"  calibration at N={n_cal}: ideal-circuit / ensemble = {sig[n_cal] / smc[n_cal]:.3f}; "
        f"6x6 estimate sigma_1 = ensemble x max(1, that) = {sig36:.4f} [assumed: the ratio "
        "transfers from N=18 to 36]")
    log()

    # ---------------- 3. 6x6 rates ----------------
    Lx6, Ly6, kind6 = NS.target
    d6 = TriangularDimers(Lx6, Ly6)
    s6 = initial_spins(d6, kind6, C.ed_max_spins)
    bare6 = TriangularBareTFIM(Lx6, Ly6, "periodic", Q.J, Q.noisy_h, Q.dt, 0.0)
    ice6 = make_iceberg(d6, s6, Q.J, Q.noisy_h, Q.dt)
    log(f"## 3. {Lx6}x{Ly6} first-order (Stim) rates per Trotter step at noise scale lam, 2q scope "
        "[derived accounting, ASSUMED noise]")
    log("    lam   bare fault  lam_eff   Gauss p_in 10% at t   Iceberg detect  undetected  "
        "Iceberg surv 10% at t")
    rate1 = None
    lam_eff = {}
    for lam in NS.lams:
        rb = scaled_stim_rates(bare6, NOISE, lam, scope=NS.fold_scope)["bare_or_undetected"]
        ri = scaled_stim_rates(ice6, NOISE, lam)
        rate1 = rb if rate1 is None else rate1
        lam_eff[lam] = rb / rate1
        tg = Q.dt * math.log(10) / (f_gauss * rb)
        ti = Q.dt * math.log(10) / ri["detected"]
        log(f"    {lam:3d}   {rb:.4f}      {lam_eff[lam]:.3f}     {tg:6.2f} [inferred: f_G of 3x4]"
            f"      {ri['detected']:.4f}       {ri['bare_or_undetected']:.4f}      {ti:6.2f}")
    log("  Iceberg is scaled here for reference only; D3 runs it at lam=1. Folding gives the same "
        "first-order rates as insertion under this symmetric prior [derived, "
        "research/derivations/01].")
    log()

    # ---------------- 4. shot and HQC plan ----------------
    le = np.array([lam_eff[lam] for lam in NS.lams])
    sxx = float(((le - le.mean()) ** 2).sum())
    n_acc = math.ceil((NS.z_min * sig36 / (NS.plan_slope * math.sqrt(sxx))) ** 2)
    log(f"## 4. {Lx6}x{Ly6} plan: shots to resolve a conditioned slope of {NS.plan_slope} per unit "
        f"lam_eff at z={NS.z_min} [assumed target] — an ESTIMATE, nothing submitted")
    log(f"  accepted shots per (lam, t) point: n_acc = (z sigma_1 / (s sqrt(Sxx)))^2 = {n_acc} "
        f"(sigma_1={sig36:.4f}, Sxx over lam_eff={sxx:.3f})")
    log("  HQC = 5 + C (N1q + 10 N2q + 5 Nm)/5000 [established, Quantinuum docs via research/07]; "
        "bare step: N2q=108, N1q=72; prep N1q=36; Nm=36; insertion adds ~(lam-1) p2 N2q 1q gates")
    log("      t  steps   lam=1 shots  lam=2 shots  lam=3 shots  |  HQC lam=1   lam=2   lam=3  "
        "fold3(if run) | fixed-500-shot HQC/lam")
    tot = {lam: 0.0 for lam in NS.lams}
    tot_fold = tot_fixed = 0.0
    for t in NS.plan_times:
        n = round(t / Q.dt)
        row, hq = [], []
        for lam in NS.lams:
            p_in = math.exp(-f_gauss * lam_eff[lam] * rate1 * n)
            shots = math.ceil(n_acc / p_in)
            n1 = 72 * n + 36 + round((lam - 1) * NOISE.p2 * 108 * n)
            h = hqc_cost(n1, 108 * n, 36, shots)
            row.append(shots)
            hq.append(h)
            tot[lam] += h
        p_in3 = math.exp(-f_gauss * lam_eff[NS.fold_lam] * rate1 * n)
        hf = hqc_cost(72 * n + 36, 108 * NS.fold_lam * n, 36, math.ceil(n_acc / p_in3))
        if abs(t - NS.fold_plan_time) < 1e-9:      # D2: one folded check point
            tot_fold += hf
        fixed = hqc_cost(72 * n + 36, 108 * n, 36, NS.plan_shots)
        tot_fixed += fixed
        log(f"    {t:4.1f}  {n:4d}   {row[0]:9d}  {row[1]:11d}  {row[2]:11d}  |  {hq[0]:8.0f} "
            f"{hq[1]:7.0f} {hq[2]:7.0f} {hf:7.0f}  | {fixed:7.0f}")
    total = sum(tot.values())
    log(f"  totals: insertion ladder {total:.3g} HQC (lam=1 {tot[1]:.3g}, lam=2 {tot[2]:.3g}, "
        f"lam=3 "
        f"{tot[3]:.3g}); one folded lam=3 check at t={NS.fold_plan_time} {tot_fold:.3g} HQC; "
        f"fixed {NS.plan_shots} "
        f"shots per circuit: {tot_fixed:.3g} HQC per lam point")
    log("  Read: sigma_1, f_G and the slope target carry [assumed]/[inferred] tags; the plan "
        "scales "
        "as (sigma_1 / slope)^2, so halving the slope target quadruples the HQC.")
    log(f"# total runtime {time.time() - t_start:.0f}s")

    path = os.path.join(REPO, CONFIG.data_dir, "noise_scaling.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
