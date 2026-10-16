# The 6×6 noise-scaling arm (T-17 / R-14)

**Status (2026-10-16): designed and classically validated; nothing has been run on H2.**
Every number below is a **classical prediction under the ASSUMED research/06 H2 prior**, never an
H2 result. Derivation: `research/derivations/01-noise-scaling-arm.md`. Sources:
`research/07-noise-scaling.md`. Code: `src/noise_scaling.py`, `scripts/run_noise_scaling.py` →
`data/noise_scaling.txt`. Tests: `tests/test_noise_scaling.py` (frozen, written blind from
`01-noise-scaling-arm-testspec.md`).

## Why it exists

T-17 says an H2 Q3 curve is never called thermalization unless it is compared with the noise.
Noise can mimic it: in the 3×3 and 3×4 simulations, noisy conditioned curves drift toward the
infinite-temperature sector baseline B_W₀ (`docs/q3_thermalization.md` §9.2). At 3×4 the noisy
curve can be simulated classically. At 6×6 (36 spins > 24) it cannot. So the run itself must
measure how its observables respond to the noise, by deliberately raising the noise and seeing
whether they move.

## The design (decisions of the project lead, 2026-10-16)

| | decision |
|---|---|
| D1 | **Diagnostic first.** Primary output: does the Gauss-conditioned observable move with the noise scale λ (weighted slope, resolved at \|z\| ≥ 3 [assumed])? A zero-noise extrapolation is reported only when its χ² test passes. |
| D2 | **Pauli insertion** before every 2q gate with probability (λ−1)q_P, from the gate's noise model (the 2503.20870 method), for the ladder; plus **one folded λ = 3 point**, ZZ(a)·ZZ(−a)·ZZ(a), which tests the insertion model. |
| D3 | Only **bare + Gauss post-selection** is scaled. Iceberg runs at λ = 1 only: at λ = 3 its survival falls to 10% by t ≈ 1.4. |
| D4 | λ = **{1, 2, 3}**, exponential fit. |
| D5 | Fit O(λ) = B + (O0 − B)e^{−gλ} with the **asymptote B fixed** at the infinite-T value: B_W₀ for conditioned observables (6×6: 0.3088, MCMC), the full-space value for raw ones. That leaves one degree of freedom for the χ² test. The reference's own form (asymptote 0) is biased for densities. |
| D6 | Folded circuits compile at **TKET optimisation level 0**. Levels 1 and 2 (2 is Quantinuum's default) cancel the fold back to λ = 1 [measured, offline H2-1 compile]. Guarded by test T17; on submission, server-side optimisation must also be off. |
| D7 | Plan the 6×6 arm at **t = 1–3**, resolving slopes of 0.005 per unit λ. No late-time (t > 3) 6×6 value may be called thermalization. |

## What it costs and why the window is short

The 2q scope scales the 6×6 bare fault rate by λ_eff = 1 + 0.938(λ−1), so λ = 3 means λ_eff = 2.88.
At 3×4, 62% of faults break the Gauss law [measured]; applying that fraction at 6×6 [inferred],
post-selection keeps 10% of shots by t ≈ 13.5 at λ = 1 but only by t ≈ 4.7 at λ = 3. Late λ = 3
points then cost tens of thousands of shots each. The full t = 1–8 plan was ≈ 1.7×10⁶ HQC. D7's
early window is ≈ 8×10⁴ HQC (see `data/noise_scaling.txt` §4 for the per-point table). HQC uses
Quantinuum's published formula 5 + C(N1q + 10 N2q + 5 Nm)/5000 [established].

These costs scale as (σ₁/slope)², where σ₁ is the per-shot spread of the flippable density. σ₁ at
6×6 is the sector-ensemble value (MCMC [measured]) times the ideal/ensemble ratio measured at 3×6
[assumed to transfer]. A √N scaling was tried first and **failed its own check**: σ₁ grows from
N = 12 to N = 18. Everything here moves once H2's real 2q error (G2) is known, so recompute then.

## What the 3×4 validation shows [measured; classical prediction, assumed noise]

`data/noise_scaling.txt` §1 (400 trajectories × 20 batches per point, t ≤ 8):
- **Raw flippable density.** The slope is resolved at every t (z = −4.9 to −11.8). Wherever the
  fit passes χ² (7 of 8 times), the extrapolation cuts the λ = 1 error of 0.014–0.066 to
  0.0005–0.010. Insertion and folding agree.
- **Gauss-conditioned.** The λ = 1 value is already within 0.0002–0.0027 of ideal. The slope is
  resolved at 3 of 8 times (|z| ≈ 3.4–4.8, slopes ≈ 0.001–0.003 per unit λ). There the extrapolation brings the
  value within 0.0016 of ideal, and all 8 fits pass χ². So at the prior, Gauss post-selection
  removes most of the noise effect on this observable. The diagnostic still detects the residual
  drift when the SE is small (0.0003), and stays silent at zero noise (test T12).

## Limits

- One noise model (symmetric depolarizing with η = 0.05). Under it, insertion and folding agree by
  construction to first order. On H2 they need not: the ZZ error depends on the angle, and folding
  changes the error *type* for asymmetric channels. That gap is exactly what the folded check point
  is for.
- The fixed asymptote is justified outright for raw observables (full depolarization gives the uniform
  distribution). For conditioned ones, that 2q-only noise drives the λ → ∞ limit to B_W₀ is
  [inferred], not shown. The χ² gate is the guard, and it passed at all 8 times on 3×4; that does not
  establish the form at 6×6.
- The O0 standard error is the unscaled fit error, and it can **understate** the true error. At
  3×4, conditioned, t = 4, O0 = 0.2675 ± 0.0003 against ideal 0.2687: 4 se off, although χ² passed
  (p = 0.43) [measured]. On raw values |O0 − ideal| stays under 1 se. Treat the O0 se as a lower
  bound, and quote the 3×4 residual alongside any 6×6 O0.
- Insertion scales only what its model contains. Idle/memory, leakage and SPAM errors are not
  scaled, and their drift would be invisible to the λ ladder.
- f_G, σ₁ at 6×6 and the slope target carry [inferred]/[assumed] tags. The plan is an estimate,
  not a budget request.
- Nothing in `src/noise_scaling.py` can reach hardware (test T16). Submission stays behind the
  SCOPE §5 gate.
