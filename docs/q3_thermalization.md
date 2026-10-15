# Q3 thermalization: sector-restricted MCMC baseline (handoff/07), Trotter threshold, noisy/encoded curves, size story and figures (handoff/08)

**Code:** `src/mcmc_baseline.py`, `src/trotter_threshold.py` · **tests:** `tests/test_mcmc_baseline.py` (26), `tests/test_trotter_threshold.py` (10) · **scripts:** `scripts/run_q3_baseline.py`, `scripts/run_trotter_threshold.py` · **data:** `data/mcmc_baseline.txt`, `data/q3_relaxation.txt`, `data/trotter_threshold.txt` · **settings:** `config.py: Q3BaselineConfig` (`CONFIG.q3`).

> **Status of every number here:** a CLASSICAL statistical reference (a uniform ensemble over a winding sector, sampled by MCMC or enumerated exactly), or a classical noiseless state-vector simulation of the ideal Trotter circuit. **None is quantum hardware or an H2 result.** No noise model enters anywhere.

> **Scope (DECISIONS.md DECIDED-1, decided 2026-10-15):** this study runs at h ≤ 0.5, working point
> h/|J| = 0.3. The reference's own released triangular (quench4) circuits run at h/|J| = 2; this
> is a deliberately chosen weak-field regime, not an attempt to match or reproduce that
> experiment. See `DECISIONS.md` DECIDED-1 for the full reasoning.

Model: the frustrated triangular TFIM, H = −J Σ ZZ − h Σ X with **J = −1** (AFM in our sign), dt = 0.25, h ∈ {0.1, 0.2, 0.3, 0.5} (0.3 = our working point, chosen because it is where the emergent-Gauss-law description is valid, `DECISIONS.md` DECIDED-1; the scan was broadened from {0.1, 0.3} in handoff/08 A2). Periodic tori, row-major sites, dimer/defect/winding definitions from `src/dimers.py` (docs/gauss_law_dimers.md).

---

## 1. Why the baseline must be per winding sector

ETH in quantum dimer models on the square and triangular lattices holds only **within a topological (winding) sector**, not globally (Lan & Powell, PRB 96, 115140, arXiv:1706.02601) **[established]**. A whole-configuration-space ergodic average mixes sectors the constrained dynamics cannot connect and so manufactures a spurious "non-thermalization".

The data show this directly **[measured, data/mcmc_baseline.txt §2]**. "Global" means uniform over all defect-free configurations, ignoring winding.

| cluster, W₀ | observable | sector value | global value |
|---|---|---|---|
| 3×4, (0, 2) | flippable density | 0.2667 | 0.2353 |
| 3×4, (0, 2) | ρ_v | 0.5000 | 0.4412 |
| 3×4, (0, 2) | C(r = 1) | −0.0296 | −0.0062 |
| 4×5, (2, −2) | ρ_h | 0.5000 | 0.4775 |

For W₀ = (0, 0) on 3×6 the two nearly coincide (846 of the 860 defect-free states are in that sector), so the restriction matters most for off-centre sectors.

## 2. Design decision 1: the ensemble

**Choice: infinite temperature (uniform) over the flip-connected component of the initial configuration c₀ inside its defect-free sector W₀ [derived].**

1. For |h| ≪ |J| the quench is generated at first order by H_QDM = −h Σ_s Π_s X_s inside the defect-free manifold (docs/gauss_law_dimers.md §4).
2. Every basis state has ⟨c|H_QDM|c⟩ = 0. Each flip changes the number of up spins by one, so (−1)^{#up} anticommutes with H_QDM and the spectrum is symmetric about 0.
3. So a product state sits at the band centre, which is infinite temperature for the constrained model. The ETH long-time value is the uniform average over what H_QDM can reach from c₀.
4. "What it can reach" is the flip component of c₀. The **sector census** (§1 of data/mcmc_baseline.txt, exact, every torus up to N = 20: 3×3, 3×4, 3×6, 4×5, plus 3×5, 4×4 in exploration) **[measured]** shows that every sector is either:
   - **one** flip component (e.g. 3×6 W = (0, 0): 846 states, 1 component; 4×5 W = (2, −2): 680, 1), or
   - made **entirely of frozen configurations** (no flippable spin; e.g. the stripe sector (6, −4) on 3×4: 2 states, 2 components). There the baseline is c₀ itself, and the verdict is "frozen".
5. Whether non-frozen sectors are still a single component above N = 20 is **[unverified]**. By construction the MCMC samples the component of c₀, which is the set the first-order dynamics explores in any case.

**Not built (deliberately):** a finite-temperature Metropolis ensemble. The quench is at infinite temperature of the constrained band, and adding one would introduce a free parameter with no target.

**What the ensemble does NOT fix: finite-cluster offsets.** The dynamics conserves ⟨H_QDM²⟩. Since ⟨c|H_QDM²|c⟩ = h²·(number of flippable sites of c) **[derived]**:
- the 3-sublattice start (flippable fraction f(c₀) = 2/3) carries **2.0×** the energy variance of the uniform 3×6 ensemble (⟨f⟩ = 0.331);
- so its finite-cluster long-time state is not the uniform one.

Section 5 measures this offset with the exact H_QDM diagonal ensemble (DE). It shrinks from 3×3 to 3×6 (flippable density DE − uniform = 0.092 → 0.057) **[measured]**. It is expected to vanish as N → ∞, because the energy-density variance h²f(c₀)/N → 0 **[inferred, not demonstrated beyond N = 18]**.

## 3. Design decision 2: the sampler and why it is correct

**Moves.** Pick a site uniformly; flip it iff it is flippable (its six hexagon neighbours alternate). There are no non-local moves; none are needed, given the census above.

- **Detailed balance [derived].** Flippability of s depends only on its neighbours, which the flip leaves unchanged. So each move is its own inverse with the same probability 1/N. The kernel is symmetric, hence doubly stochastic, hence uniform on each component.
  - *Tested:* χ² on 2000 independent final states over the 42 states of 3×3 (`test_sampler_is_uniform_on_the_component_chi2`).
- **Sector preservation [derived + enforced].** A flippable flip is one term of H_QDM, which commutes with every D_t and winding number (tests/test_dimers.py).
  - The sampler re-checks the defect count and **every** row and column winding cut after **every** sweep, and raises if W₀ is ever left. The guard demonstrably fires (`test_sampler_raises_if_not_in_a_sector`).
  - Every visited state is checked against the `src/dimers.py` arrays, and on 3×4 the chain reaches all 60 sector states (`test_sampler_never_leaves_the_sector_checked_against_dimers_arrays`).
- **Mixing / errors.** 32 independent chains, all started **at c₀**. A non-mixing chain would retain memory of c₀, where memory(c₀) = 1.
  - Burn-in is 500 sweeps and 4000 sweeps are measured (1 sweep = N attempts).
  - SE = std(chain means)/√32, which contains the autocorrelation.
  - Naive SE and τ_int = (SE/SE_naive)²/2 are printed beside it. For example, memory has τ_int = 2.2 (3×6) and 3.9 (9×6), so the naive SE would understate the error by 2–3×.
  - Correlations use a jackknife over chains.
- **Scale.** The MCMC works on configurations, not 2^N vectors, so it runs at any size: 6×6 (N = 36) and the reference §V size 9×6 (N = 54) take 10–16 s.

## 4. Observables: identical on both arms

| name | definition (src/dimers.py) | in-sector baseline |
|---|---|---|
| `defect_density` | ⟨Σ_t D_t⟩/2N | **0 exactly** (defect-free ensemble), so the yardstick is the dressed value, §6 |
| `flippable_density` | ⟨Σ_s Π_s⟩/N | discriminating |
| `rho_h/v/d` | orientation-mean ⟨n_b⟩ | **fixed by W₀**: ρ_h = (W_x+L_x)/3L_x, ρ_v = (W_y+L_y)/3L_y [derived, tested] |
| `memory` | Σ_b n_b(c₀)⟨n_b⟩/N (fraction of initial dimers present) | discriminating |
| `C(r)` | per-pair connected ⟨n_a n_b⟩ − ⟨n_a⟩⟨n_b⟩ in bond-midpoint distance shell r | r = 0.5 is near-constant (one dimer per triangle); r = 0.866, 1 are discriminating |

- The quantum arm and the exact references evaluate these with the `src/dimers.py` 2^N operators.
- The MCMC uses a per-configuration evaluator built from the same `TriangularDimers` geometry. It is tested equal to the dimers.py arrays on **every** basis state of 3×3, 3×4 and 4×3.
- Both arms compute C(r) through one function, which is tested equal to `dimer_correlation_by_distance`.
- The C(r) distance metric is Euclidean, as in dimers.py; the graph-distance question (T-7) affects both arms identically and is untouched here.
- **Not added:** a 3-sublattice/clock order parameter (review/06 K3 is the project lead's scope decision; the brief says reuse dimers.py).

## 5. Design decision 3: leakage, and the operational verdict

**Leakage is not hidden by a hard-conserved sector.**
- Under the full TFIM the weight outside the defect-free W₀ sector, P_out, is O((h/|J|)²). The repo's measured winding leak is P(W≠W₀) ∝ h^2.08 (data/gauss_law_scaling.txt).
- The harness reads that table, fits A·h^s to its own points, and predicts the leak of each run. The prediction **agrees with the run's directly measured late-window P(W≠W₀) to 1–25%** **[measured, data/q3_relaxation.txt]**. The match is ≈1–4% on 3×6 for h ≤ 0.3. The >10% misses are the 3×4 flippable start, whose table row is the noisy h^2.38 fit (20% at h = 0.1, 13% at h = 0.3), and h = 0.5, which lies beyond the table's h ≤ 0.3 range. There the extrapolation underpredicts the 3×6 leak by 2× (4.9e-2 vs 9.8e-2) and is flagged as such in the data file. It is a cross-check, not a like-for-like fit: the table averages over T = 20/|J| from t = 0, while the runs use the late half of 12/h.

| case | predicted P(W≠W₀) | measured |
|---|---|---|
| 3×6, h = 0.1 | 1.71e-3 | 1.70e-3 |
| 3×6, h = 0.3 | 1.69e-2 | 1.66e-2 |
| 3×4 stripe, h = 0.3 | 1.06e-1 | 1.20e-1 |
| 3×4 flippable, h = 0.1 | 1.50e-3 (the noisier h^2.38 row) | 1.88e-3 |

**The band.** For any diagonal observable, ⟨O⟩ = (1 − P_out)⟨O⟩_in + P_out⟨O⟩_out. Hence **|⟨O⟩ − ⟨O⟩_in| ≤ P_out·range(O) exactly** [derived; asserted at every time step in `test_leakage_decomposition_bound_holds`].

The harness reports three curves and quantities:
1. the raw curve ⟨O⟩(t);
2. the **sector-conditioned** curve ⟨O⟩_in(t) (the state projected on defect-free ∩ W₀ and renormalised; this is what is compared with the baseline);
3. the measured shift raw − cond, its exact bound P_out·range, and the inferred drift P_out·(O_global − O_W₀) if the leaked weight looked like the winding-blind average **[inferred]**.

The late-window P_out (defect admixture plus winding leak) is 6.2e-3 (h = 0.1) and 5.9e-2 (h = 0.3) on 3×6 **[measured]**.

**Operational definition (per observable, late window = last half of a 12/h-long curve).** For C(r), the late value is C(r) of the window-averaged moments ⟨n_a⟩, ⟨n_a n_b⟩: the window's mixed state, which is comparable with an ensemble's connected correlator. Averaging the instantaneous C(r; t) would add the temporal covariance of ⟨n_a⟩(t); the first version did this (review fix M1, regression test `test_shell_verdict_uses_window_averaged_moments`). The tolerance is tol = (temporal std of the conditioned curve over the window) + 2·SE(baseline). The curve is deterministic; on a small cluster it fluctuates around its long-time value.

| label | meaning |
|---|---|
| **indistinguishable** | within tol of BOTH O_W₀ and the DE: this window cannot tell infinite-T from the finite-cluster value |
| **thermalized-in-sector** | \|late mean of ⟨O⟩_in − O_W₀\| ≤ tol |
| **finite-size-DE-offset** | fails that, but matches the exact H_QDM diagonal ensemble of c₀ within tol: the curve relaxed, yet this finite cluster's long-time value is not the infinite-T one (§2) |
| **not-relaxed-in-window** | neither |
| **frozen** | c₀ has no H_QDM dynamics (component of size 1) |
| **leaking** (reported beside the label, not instead of it) | the raw curve sits off the conditioned one by the measured shift, within the exact bound |

## 6. Results [measured unless tagged]

**MCMC vs brute-force exact (data/mcmc_baseline.txt §2).**
- Clusters: 3×3, 3×4, 3×6 and 4×5 (N = 9–20, within the ED ceiling).
- Every discriminating observable agrees within the autocorrelation-aware SE: flippable density, memory, C(0.866), C(1) and the dressing coefficient. **Max |z| = 1.39** over these (4×5 memory).
- The W₀-fixed ρ's and the zero defect density agree exactly, as derived. The near-fixed C(0.5) agrees to ~1e-6, so its z-scores are noise on a fixed quantity. All three are labelled non-discriminating in the file.

**Per-sector baselines beyond the exact ceiling (MCMC only, §3; W₀ = (0, 0), 3-sublattice c₀).**
- Flippable density: 0.3810 (3×3, exact) → 0.3310 (3×6, exact) → 0.3085 ± 0.0002 (6×6) → **0.3026 ± 0.0002 (9×6)**.
- C(0.866) at 9×6: +0.0972 ± 0.0001.
- The finite-size drift is visible and is the reason the baseline is computed at the reference size.

**Relaxation vs baseline across the field scan (data/q3_relaxation.txt; handoff/08 A2).** Late window, sector-conditioned curve, 3×6 3-sublattice start, W₀ = (0, 0). The table shows the late conditioned value with the verdict label beneath it.

| observable | B_W₀ (uniform) | DE (H_QDM) | h = 0.1 | h = 0.2 | h = 0.3 | h = 0.5 |
|---|---|---|---|---|---|---|
| flippable density | 0.3310 | 0.3880 | 0.3835 ± 0.018 DE-offset | 0.3758 ± 0.017 DE-offset | 0.3839 ± 0.019 DE-offset | 0.3833 ± 0.018 DE-offset |
| C(0.866) | +0.1103 | +0.1283 | +0.1274 DE-offset | +0.1250 DE-offset | +0.1278 DE-offset | +0.1269 DE-offset |
| C(1) | −0.0313 | −0.0448 | −0.0443 DE-offset | −0.0424 DE-offset | −0.0444 DE-offset | −0.0438 DE-offset |
| memory | 0.3333 | 0.3789 | 0.364 indist. | 0.355 indist. | 0.352 indist. | 0.376 DE-offset |
| late P_out (weight outside the sector) | | | 6.2e-3 | 2.5e-2 | 5.9e-2 | **2.6e-1** |
| raw − cond, flippable density | | | −1.3e-3 | −5.0e-3 | −1.2e-2 | **−6.2e-2** |

Notes on the table:
- "DE-offset" = finite-size-DE-offset; "indist." = indistinguishable (within tolerance of both B_W₀ and DE).
- ± is the temporal std over the late window, not a statistical error.
- The ρ's are fixed by W₀ (1/3 here) and are not discriminating.
- In the prose, 0.384 rounds the 0.3835 / 0.3839 entries (review/09 m2).

**Reading.**
- The curves **relax**: c₀ has flippable density 0.667 and memory 1. They relax to the finite-cluster diagonal ensemble. The h = 0.1 and h = 0.3 curves agree, so the offset is not leakage. The offset from the infinite-T sector baseline is the finite-size energy-variance effect of §2.
- On 3×4 (flippable start, 60-state sector) the same picture holds for flippable density, C(0.866) and C(1). Memory and C(0.5) are indistinguishable. (A ≈0.002 C(0.5) "residual" in the first version was the M1 averaging artefact; it is gone.)
- The 3×4 stripe start is **frozen**: in-sector nothing moves. Its raw dimer densities move only through leakage (ρ_h 1 → 0.938 at h = 0.3), within the exact bound P_out = 0.16.
- **Leakage effect on the 3×6 curves:** |raw − cond| ≤ 1.2e-2 (flippable density, h = 0.3), against the bound 5.9e-2. It falls about 10× from h = 0.3 to h = 0.1, consistent with O(h²).
- **Field scan, h = 0.1 → 0.3 [measured].** The in-sector picture does not depend on h: the conditioned values sit at the DE throughout, and the labels are stable on 3×6 and 3×4. This is what a first-order (H_QDM) description predicts, since h only sets the time unit.
- **h = 0.5 is outside the weak-field regime, and the data say so:**
  - 26% of the 3×6 weight (57% for the stripe) is outside the defect-free W₀ sector in the late window;
  - the first-order dressed defect density underpredicts by 1.5–1.6× on 3×6;
  - the leak table, extrapolated past h = 0.3, underpredicts the leak 2×.

  The raw 3×6 flippable density there (0.322) lands near B_W₀ (0.331) **only because a quarter of the weight has left the sector**; it must not be read as thermalization to the sector value. The conditioned curve still sits at the DE (0.383), but it now describes a 74% post-selected subensemble. Treat h = 0.5 as a stress point, not a Q3 result. (Memory's label change at h = 0.5 to DE-offset is borderline: a 0.043 deviation against a 0.035 tolerance, driven by a narrower late spread.)

**Defect density vs the dressed prediction [derived, first order; measured comparison].**
- In-sector the defect density is 0, so the quantum curve is compared with the O(h²) dressing ρ_D ≈ h²[⟨g⟩ + g(c₀)].
- Here g(c) = (1/2N) Σ_s n_s (dt/2)²/sin²(|J| n_s dt): the first-order Floquet admixture for the Strang step, summed over the defects each non-flippable flip creates. The two terms are the static dressing of the visited configurations and the real excitations made at t = 0.
- Measured / predicted:
  - with ⟨g⟩_W₀: 0.96–1.06;
  - with ⟨g⟩_DE (what the finite cluster actually visits): 0.99–1.09 (h = 0.3 within 2–9%, h = 0.1 within 1–6%).
- The stripe limit reproduces the repo's (h/|J|)²/8 (`test_dressing_stripe_limit_is_one_over_sixteen`).
- This first-order formula also explains the ≈10% dt = 0.25 excess in docs/gauss_law_dimers.md §4: Floquet factor 16·(dt/2)²/sin²(2|J|dt) = 1.088 at dt = 0.25, vs the measured 1.098 at the smallest h.

**Internal pre-review** (Claude Code's own read-only sub-agent, before Kiro's milestone review; review/09 then ACCEPTED the build with no Critical/Major findings). The sub-agent rebuilt the geometry, enumeration, dynamics and DE with its own code and reproduced every number checked. It re-derived the Floquet admixture; a frozen stripe at h = 0.01 gives measured/predicted = 1.000 at dt = 0.25 and 1.001 at dt = 0.6, where the Floquet factor is 1.66× the continuum value. Verdict: ACCEPT-WITH-FIXES. M1 (shell averaging), m1 ("indistinguishable" label, ρ's marked), m2 (curve guard moved to the ED ceiling: 2^N × 3N tables), m3 (leak wording) and the nits are all applied.

## 7. What this does and does not establish

- **Does:**
  - a tested, sector-correct, scalable ergodic yardstick for Q3, with autocorrelation-aware errors;
  - a harness that separates in-sector relaxation, finite-size offset and O(h²) leakage on the same curve.
- **Does not:**
  - a thermodynamic-limit thermalization claim. The quantum curves stop at 3×6 (statevector ceiling), and there the finite-size offset dominates the comparison with the infinite-T baseline.
  - any noisy, encoded or hardware statement.
  - a test of Trotter prethermalization (Yang et al., PRX Quantum 4, 030320) **[established citation, no numbers imported]** over long windows. The dt-threshold itself is now measured (§8).
  - the inexact-constraint slow relaxation of arXiv:2401.11294 **[fetched]**. It is consistent with the measured O(h²) leakage scale, but not tested over long windows.
- **Open:** single-component sectors above N = 20 [unverified]; the size trend of the DE offset beyond N = 18 [inferred]. The energy-variance account of the offset is qualitative; it is not a quantitative prediction of the DE value.

## 8. Trotter-threshold / dt-convergence study (handoff/08 Part A1, K2)

**Code:** `src/trotter_threshold.py` · **tests:** `tests/test_trotter_threshold.py` (10) · **script:** `scripts/run_trotter_threshold.py` → `data/trotter_threshold.txt`. Classical, noiseless; NOT an H2 result. This is the same study type as the team's earlier hackathon `run_dt_convergence.py` (journal Entry 30), adapted from the 1D ferromagnet to the frustrated triangular model.

**Ordering fix (peer review, MAJOR):** `src/trotter_threshold.py` (and every number quoted below) uses `src/trotter.trotter2_step`, the ZZ-outside splitting — a different frame from the published H2 circuits' X-outside splitting, now additively provided as `src/trotter.circuit_trotter2_step`. This does not change the threshold results below (a quasienergy/convergence-order statement, frame-independent), but it does change the sign of the defect-density/P_out inflation reported late in this section; see the CORRECTION bullet below (end of this section) and `scripts/run_trotter_order_compare.py` → `data/trotter_order_compare.txt`.

**Why.** A Q3 relaxation curve is only meaningful at a dt below the Trotter threshold, above which local observables stop tracking the target dynamics (Heyl–Hauke–Zoller, Sci. Adv. 5, eaau8342 **[established]**; no numbers imported). This section places the working dt = 0.25 relative to that threshold for this model.

**Method.**
- Fixed physical time T = 20/|J|, starting from the Q3 initial states.
- The repo's 2nd-order Strang step (`src/trotter.trotter2_step`, the step behind every Q3 curve) is compared with exact evolution.
- Exact evolution uses a Chebyshev expansion of e^{−iHt} on the sparse TFIM Hamiltonian, tested against scipy `expm_multiply` and dense diagonalization: the tests assert < 1e-10, and the achieved agreement is ~1e-13 (review/10 reproduced ≤ 3.6e-13 at T = 20).
- Error = |O_Trotter(t) − O_exact(t)|, maximised over the comparison times, for the Q3 observables (flippable density, defect density, memory, C(0.866)). The definitions are tested identical to the Q3 arm. Infidelity is measured at the last compared time (floor(T/dt)·dt ≤ T when dt does not divide T).
- Dense scans: every Trotter time compared, dt = 0.02–1.20 in steps of 0.02, plus 0.25; on 3×3 (3-sublattice) and 3×4 (flippable), h ∈ {0.1, 0.2, 0.3, 0.5}.
- Coarse scan: compared every 2.0, 11 dt values; on 3×6 (3-sublattice), h ∈ {0.1, 0.3}.
- **Operational threshold [assumed criteria], two of them:**
  - **absolute:** the smallest scanned dt at which the time-max flippable-density error reaches ε = 0.05. That is ≈15% of the 3-sublattice start's relaxation signal (0.67 → 0.38), but about the whole signal of the 3×4 flippable start (0.333 → 0.282);
  - **relative:** the error reaches 10% of the start's own signal |f(c₀) − f_DE|, where f_DE is the exact H_QDM long-time value. It is n/a for frozen starts, which have no in-sector signal.

**Prediction [derived, first-order Floquet; module docstring].**
- Flipping a non-flippable spin costs 2|J|n_s (n_s ∈ {2, 4, 6}).
- In the Strang step that admixture ∝ (dt/2)²/sin²(|J| n_s dt), which diverges at **dt = π/(|J| n_s)**: 0.524 (n_s = 6), 0.785 (n_s = 4), 1.571 (n_s = 2). There the Ising gap folds back into the Floquet zone and stops protecting the Gauss law.
- Both Q3 starts contain n_s = 6 spins, so the threshold should sit just below π/6 = 0.524.

**Results [measured, data/trotter_threshold.txt].**

| cluster, start | h | order (local / infid.) | threshold, absolute ε = 0.05 | threshold, relative (10% of signal) | error at dt = 0.25 | dt = 0.25 margin (abs. / rel.) |
|---|---|---|---|---|---|---|
| 3×3, 3-sublattice | 0.1 | 2.03 / 4.02 | 0.46–0.48 | 0.44–0.46 | 7.0e-4 | 1.8–1.9× / 1.8× |
| 3×3, 3-sublattice | 0.3 | 2.00 / 4.01 | 0.38–0.40 | 0.32–0.34 | 9.0e-3 | 1.5–1.6× / 1.3× |
| 3×3, 3-sublattice | 0.5 | 2.00 / 4.02 | 0.32–0.34 | **0.18–0.20** | 2.9e-2 | 1.3× / **< 1 (past it)** |
| 3×4, flippable | 0.1 | 2.01 / 4.02 | 0.50–0.52 | 0.44–0.46 | 2.6e-4 | 2.0× / 1.8× |
| 3×4, flippable | 0.3 | 2.01 / 4.01 | 0.46–0.48 | 0.32–0.34 | 2.1e-3 | 1.8–1.9× / 1.3× |
| 3×4, flippable | 0.5 | 2.01 / 4.01 | 0.40–0.42 | **0.22–0.24** | 5.8e-3 | 1.6× / **< 1 (past it)** |
| 3×6, 3-sublattice | 0.1 | 2.03 / 4.03 | 0.4–0.5 (coarse) | 0.4–0.5 | 4.2e-4 | 1.6–2.0× |
| 3×6, 3-sublattice | 0.3 | 2.03 / 4.02 | 0.4–0.5 (coarse) | 0.4–0.5 | 2.9e-3 | 1.6–2.0× |
| 3×4, stripe (frozen) | 0.1 / 0.3 | 2.0 / 4.0 | not reached / 1.12–1.14 on flippable density* | n/a (no signal) | 7.6e-5 / 6.4e-4 | — |

The error column is the time-max flippable-density error. Margins are threshold ÷ 0.25, using both ends of the bracket. *The flippable-density criterion is blind for the stripe (its signal is ≈0); its defect-density error is the informative column (see Reading).

(h = 0.2 rows are in the data file; they interpolate between h = 0.1 and 0.3.)

**Reading.**
- **Second order confirmed.** The local-error slope is 2.00–2.04 on every observable, case and field; infidelity goes as dt⁴. Halving dt cuts local errors 4× (tested).
- **The threshold is the π/6 Floquet resonance, broadened by h.** It sits just below 0.524 at h = 0.1 and moves down as h grows (to 0.32–0.42 at h = 0.5). Between resonances the error dips again (e.g. 3×6, h = 0.1: 1.4e-2 at dt = 2/3 vs 1.0e-1 at dt = 0.5), and a second spike sits at the n_s = 4 resonance, as predicted: 3×4, h = 0.1 peaks at dt = 0.78 (error 0.25), against π/4 = 0.785 (the error falls back to 7.9e-3 at dt = 0.60, between the two resonances).
- **Weak-field rule.** The relevant n_s is a weak-field property of c₀ and its sector [measured, data file §1 stripe scans].
  - At h = 0.1 the stripe (n_s = 2 only) keeps a small absolute defect-density error up to dt ≈ 1: 1.1e-3 at dt = 0.5, 8.9e-3 at 1.0, 2.5e-2 at 1.2. It breaks toward π/2.
  - "Small" is absolute only: at dt = 0.5 that error is ≈70% of its own tiny late defect density.
  - At h = 0.3 its defect-density error jumps 10× between dt = 0.46 and 0.50 (1.2e-2 → 1.0e-1). The configurations it admixes at higher order carry n_s = 6 gaps, so it feels π/6 too.
- **No visible size dependence.** The threshold is the same on 3×4 and 3×6 to within the coarse 3×6 resolution (0.4–0.5); a local resonance is not expected to move with N [inferred].
- **Where dt = 0.25 sits.**
  - **For h ≤ 0.3** it is below the threshold by both criteria: 1.5–2.0× by the absolute one and 1.3–1.8× by the relative one, with time-max errors of 0.01–0.18 ε.
  - **At h = 0.5 it is past the relative threshold** (0.18–0.24): its error exceeds 10% of the start's own relaxation signal. It sits only 1.3–1.6× below the absolute one.
  - So at our working h = 0.3 the working dt is credible, with a modest margin. h = 0.5 at dt = 0.25 is not a faithful continuous-time simulation, which is a second, independent reason to treat it as a stress point.

**Trotter bias of the Q3 late-window means at dt = 0.25 (§3 of the data file).**
- These are measured on the exact snapshot grid of `data/q3_relaxation.txt`, with C1 from window-averaged moments.
- The **sector-conditioned** means are exactly the quantities the verdicts compare (tested equal to `classify`).
- **The verdict quantities are Trotter-robust.** On the conditioned curves (flippable density, memory, C(0.866)), |bias| ≤ 0.12 × the late temporal std (the tolerance scale) in every non-frozen case, h = 0.1–0.5. The handoff/07 verdicts are not Trotter artefacts.
- **CORRECTION (peer review, MAJOR; `src/trotter.py` ordering finding).** Every number in the rest of this subsection as originally written was computed with `src/trotter.trotter2_step`, this repo's **ZZ-outside** (ABA) Strang splitting: exp(−iA dt/2) exp(−iB dt) exp(−iA dt/2). The published H2 circuits (arXiv:2503.20870) instead implement the **X-outside** splitting exp(−iB dt/2) exp(−iA dt) exp(−iB dt/2) (`src/compare.py:circuit_trotter_states`, now additively available as `src/trotter.circuit_trotter2_step`). The two step operators are unitarily conjugate — same quasienergies, hence the **same dt = 0.25 threshold brackets and margins below** are unaffected — but the two frames read observables along the way differently, and at the published h·dt = 0.5 the difference is large and **opposite in sign**: the ZZ-outside numbers below are *inflated* relative to continuous time; the circuit's own ordering *deflates* the same quantities. Both are reported below **[measured, data/trotter_order_compare.txt]**; the "describes the reference experiment's circuit" claim this subsection previously made for the ZZ-outside numbers is **withdrawn** — it is wrong in sign; the circuit-order column is what actually describes the published circuit.
- **The Trotter bias sits in the leakage.**
  - With the project's own ZZ-outside splitting, dt = 0.25 inflates the weight outside the sector, P_out, by 1.5–2.8 std: about +10–25%, e.g. +22% on 3×6 at h = 0.3 (4.8e-2 → 5.9e-2).
  - So the raw curves carry a larger bias, up to ≈0.5 std at h = 0.5 (0.25 at h = 0.3).
  - This corrects the first version of this section, which quoted only the raw bias as the verdict risk (internal pre-review M2).
  - **In the circuit's own (X-outside) ordering, P_out is instead *deflated* by 19–35% at dt = 0.25** [measured, data/trotter_order_compare.txt]: zz/exact vs circuit/exact is 1.32/0.65 (3×3, h = 0.1), 1.31/0.69 (3×3, h = 0.3), 1.13/0.79 (3×4 flippable, h = 0.1), 1.12/0.81 (3×4 flippable, h = 0.3), 1.22/0.74 (3×6, h = 0.3).
- **Defect density: Trotter-inflated in the ZZ-outside splitting, Trotter-deflated in circuit order.** At dt = 0.25 the ZZ-outside value exceeds the exact (continuous-time) value by **about 40% on 3×6** (0.00493 vs 0.00355 at h = 0.3) and about 18% on 3×4 flippable — both **[measured, this repo's own ordering only]**. The **circuit-order** value at the same dt instead sits *below* the exact value: ≈40% on 3×6 (0.00214 vs 0.00355), ≈25% on 3×4 flippable (0.00495 vs 0.00656), and ≈46–50% on 3×3 3-sublattice (0.00159/0.00297 at h = 0.3, 0.00014/0.00030 at h = 0.1) [measured, data/trotter_order_compare.txt].
  - Mechanism [derived; corrected after the internal pre-review]: the dressed density h²[⟨g⟩ + g(c₀)] has two terms with different Floquet factors at dt = 0.25 vs continuous time, for the ZZ-outside splitting specifically (the admixture formula below is the ZZ-outside Floquet factor; the circuit-order splitting has its own, not re-derived here).
    - g(c₀) contains the n_s = 6 spins of the 3-sublattice start, whose factor (dt/2)²/sin²(6|J|dt) ÷ 1/(12|J|)² is 2.26×.
    - The sector average ⟨g⟩ is inflated only 1.20×.
  - The blend predicts **1.39× (with ⟨g⟩_W₀) to 1.44× (with ⟨g⟩_DE) on 3×6**, against a measured 1.39–1.43 (ZZ-outside). It predicts 1.18× on 3×4 flippable (measured 1.16–1.19, ZZ-outside) and 1.09× for the stripe (measured 1.08–1.10, ZZ-outside).
  - This is why the dressed prediction (§6), which uses the dt = 0.25 ZZ-outside factors, matched the ZZ-outside Trotter curves. The dressed prediction was never re-derived for circuit order; the circuit-order deflation above is reported as a direct measurement only, with no first-order mechanism claimed for it.
  - **Consequence (corrected): absolute defect densities quoted at dt = 0.25 in the rest of this document use this repo's own ZZ-outside splitting, which is NOT the published circuit's frame.** The circuit's own frame instead deflates defect density and P_out at this dt, per the measurements above. Neither frame changes the dt = 0.25 threshold location (§8 below), which is a quasienergy statement common to both.

**Not claimed.** The threshold is located on N ≤ 18 clusters and for these starts. Its value for the 9×6 H2 lattice is [inferred] (resonance physics is local), not measured. Long-time Trotter heating (Yang et al.) was not studied beyond T = 20/|J|.

## 9. Noisy and Iceberg-encoded curves, size story, figures (handoff/08 Part B)

> **Status:** every noisy number in this section is a **classical prediction under an ASSUMED noise model** (the research/06 H2 prior, Pauli-trajectory simulation). **None is an H2 or hardware result.** The ideal curves and the MCMC baselines are classical simulation and statistics.

**Code:** `src/noisy_q3.py` · **tests:** `tests/test_noisy_q3.py` (8), `tests/test_plot_q3.py` (4) · **scripts:** `scripts/run_q3_noisy.py` → `data/q3_noisy.txt`; `scripts/run_q3_size.py` → `data/q3_size.txt`; `scripts/plot_q3.py` → `figures/*.png` · **settings:** `CONFIG.q3` (`noisy_*`, `size_*`), noise from `CONFIG.sensitivity`.

### 9.1 Design (B1)

**Noise model [assumed, research/06 prior].**
- After every 2-qubit gate: a 2-qubit Pauli fault with p2 = 6e-4. A fraction η = 0.05 is an extra Z⊗Z on top of a uniform 1/15 share; this is exactly the Stim channel of `encoded_codes.to_stim`, and its sampling is tested.
- After every 1-qubit gate: a uniform X/Y/Z fault with p1 = 6e-5.
- Readout flips pm = 6e-5; reset errors p_init = 6e-5.
- Assumed absent: idle noise, coherent error, leakage, crosstalk.
- The same model on both arms, gate by gate.

**Circuit.** Both arms run the encoded pipeline's **circuit-order Strang step** (X half, ZZ, X half; `src/encoded_codes`) on the periodic triangular torus.
- It differs from the handoff/07 curves' `trotter.py` (ZZ-outside) ordering at O(dt²): max |Δ| over the window is 4–8e-3 on flippable density and ≤ 1.5e-3 on C(0.866) [measured, data file]. That is below the late-window verdict tolerances (temporal std 0.012–0.02).
- The ideal curve of this section is that same circuit with no noise.

**Arms.**
- **bare:** unencoded, with gate-level faults.
- **Iceberg:** `TriangularIcebergTFIM`, an additive subclass of `EncodedTFIM`. It has triangular bonds and a product-state prep (ry(π) on the down spins via the existing Ybar gadget, so the prep's gate and noise structure is unchanged). **This prep is conservative against Iceberg:** it runs 12 weight-3 parity gadgets, including no-op ry(0) ones, where a frame-only logical-X prep would need no 2-qubit gate, while the bare arm charges one 1q location per down spin. It costs ≈6% survival at t = 0 [measured] (internal pre-review M6). It is [[14,12,2]] on 3×4, 16 physical qubits, with a flagged X^n / Z^n syndrome round after every step and post-selection on every detector.
  - **Iceberg needs an even number of logical qubits, so 3×3 (k = 9) has no encoded arm.**
  - **Transparency:** at zero noise the encoded logical distribution equals the bare circuit's to < 1e-12 at every step [tested].

**Readout.** At every step boundary the runner records the **exact** readout distribution a Z measurement would give there:
- readout flips are included;
- for Iceberg, the final pure-Z detectors are applied and trajectories in which any detector has fired get weight 0;
- logical bits are decoded through the pure-Z readout representatives.

There is no shot noise; errors are batch-means SE over 20 batches of fault patterns (400 bare and 300 Iceberg trajectories). Observables are the `src/dimers.py` definitions on the mixture distribution (raw, and sector-conditioned = **Gauss-law + winding post-selection**, the handoff/02 detection-only mitigation).

### 9.2 Results [classical prediction under the assumed model; data/q3_noisy.txt, figures/q3_noisy.png]

3×4 flippable start, h = 0.3: mean |O_noisy − O_ideal| of the flippable density, with the shot-cost factor 1/acceptance.

| mode | early window t ≤ 12 | late window (t = 20–40) |
|---|---|---|
| bare, raw | 0.052 ± 0.005 (×1) | 0.173 ± 0.005 (×1) |
| bare + Gauss-law post-selection | **0.0017 ± 0.0004** [vs raw ideal 0.0056] (×1.43) | **0.0083 ± 0.0011** [0.0054] (×4.8) |
| Iceberg, post-selected | 0.019 ± 0.008 (×3.1 mean; ×12 at t = 12) | not reachable |
| Iceberg + Gauss-law post-selection | 0.0009 ± 0.0009 [0.0063] (×3.5; ×16 at t = 12): **at the statistical floor** | not reachable |

Notes on the table:
- **Reference.** Gauss-post-selected modes are scored against the ideal **sector-conditioned** curve, the quantity they estimate. The bracket gives the score against the ideal raw curve, which differs from the conditioned one by ≈0.005–0.007.
- **±** is the mean per-point batch SE of the mode. A residual comparable to it is not resolved.
- C(0.866) behaves the same way early: 0.019 / 0.0007 / 0.0077 / 0.0004. (`data/q3_noisy.txt` labels this shell `C1`; it is the same nearest-midpoint shell C(0.866) that `q3_relaxation.txt` / `q3_size.txt` label `C(0.866)` / `C(r=0.866)`; review/11 m2.)
- **3×3** (no Iceberg arm): bare raw vs bare + Gauss is 0.099 → 0.018 early (×1.24 shots) and 0.30 → 0.049 late (×2.5).

**Reading.**
- **Unmitigated, the bare curve is not a Q3 measurement at the prior.** The flippable density decays steadily, 0.33 → 0.08 by t = 40, as faults create defects and heat the state toward the full-space infinite-T value. Over the 160-step window the bare circuit carries ≈ 3.7 faults per shot on 3×4 [derived, Stim rates below].
- **Gauss-law post-selection is the effective, cheap mitigation for these observables.** The size of the gain depends on the lattice and on the reference:
  - 3×4: **≈ 30× early / ≈ 21× late** against the conditioned target, ≈ 9× / 32× against the raw ideal curve;
  - 3×3: **≈ 5.5× / 6×** (≈ 7× against raw);
  - shot cost ×1.2–4.8.
  
  A fault that flips a spin out of the dimer manifold creates detectable defects. Z-type faults do not create defects, but they do not change diagonal observables directly either.
- **Iceberg alone helps less than Gauss post-selection.** It gives ×2.7 (0.019 ± 0.008 vs 0.052) for ×3.1 shots, and its detector survival (8% by t = 12) confines it to the early window. The ×2.7 equals the ratio of Stim's per-step bare-fault to Iceberg-undetected rates (0.0230 / 0.0086) [derived consistency check, internal pre-review].
- **Iceberg + Gauss** reaches a residual of ≤ ~0.001, which is **at the statistical floor** (SE 0.0009): it is not resolved as better than Gauss alone (0.0017 ± 0.0004). It costs ≈ 2.5× the shots on average and ≈ 8× by t = 12 (×16 vs ×2.1).
- **Net, for Q3-type diagonal observables in this model** [measured, 3×4 only]: the encoding's marginal value over the model's own Gauss law is at most modest, and not resolved here, at a substantially higher shot cost.
- **Cross-check:** local-sim's measured Iceberg survival agrees with Stim's first-order exp(−detected_total) to ≈2σ (binomial SE ≈ 0.02–0.03; the points share trajectories): 0.55 vs 0.61 (t = 2), 0.33 vs 0.39 (t = 4), 0.157 vs 0.165 (t = 8), 0.083 vs 0.069 (t = 12). Local-sim is low early and above later, consistent with higher-order effects.
- **Caveat that matters for H2: noise can mimic thermalization.**
  - The sector-conditioned late value of the noisy bare circuit moves from the ideal (DE-like) value **toward the infinite-T sector baseline B_W₀**: 3×3 flippable density 0.427 (noisy) vs 0.477 (ideal), B_W₀ 0.381; 3×4: 0.276 vs 0.284, B_W₀ 0.267.
  - Mechanism [inferred, not measured]: faults that stay inside the sector (e.g. flippable-spin flips, which the Gauss law cannot see) randomize within the sector, which is what infinite-T sector ergodicity looks like. The direction of the drift is measured; the mechanism is reasoning.
  - **A noisy hardware curve landing on B_W₀ is therefore not, by itself, evidence of thermalization.** The noise must be in the comparison (this classical prediction, or a noise-scaling experiment).

### 9.3 Size story (B2; data/q3_size.txt, figures/q3_size.png)

**What follows classically.** The quantum curve stops at N = 18 (state vector ≤ 24; 2^N observable tables ≤ 20). Two things do follow to larger N.

1. **The sector baseline** (MCMC, W₀ = (0, 0)) [measured]:
   - flippable density 0.3304 (3×6) → 0.3088 (6×6) → 0.3026 (9×6) → 0.2996 (12×6) → 0.2947 ± 0.0002 (12×12);
   - C(0.866) +0.110 → +0.0939.
   
   A weighted a + b/N fit on N ≥ 36 gives a(N → ∞) ≈ 0.290 (flippable) and 0.092 (C) [**assumed fit form, inferred extrapolation**]. The 9×6 reference-size value therefore still sits ≈ 0.013 above the fitted limit. The DE offset of §2 cannot be followed beyond N = 18.
2. **The noise budget** (Stim first-order accounting, assumed prior, h = 0.3) [derived accounting]:
   - the per-step rates grow with N: bare P(fault) = 1.92e-3 N and Iceberg P(undetected logical) = 7.2e-4 N (0.375× bare) exactly linearly; Iceberg P(detect) ≈ 4.5e-3 → 4.2e-3 per site from 3×4 to 9×6, since the syndrome round has an N-independent part that amortises;
   - at the reference **9×6** the bare circuit carries ≈ **17 faults per shot** over the 160-step Q3 window;
   - Iceberg detector survival reaches 1% by t ≈ 5 (the window is 40);
   - **Iceberg on 9×6 needs 58 physical qubits, more than H2's 56**, so the encoded Q3 run does not fit at the reference size at all. Smaller tori fit, e.g. 6×6 (40 physical) or 6×8 (52). Iceberg also needs an even number of logical qubits.

**Not claimed.** No thermodynamic-limit statement about thermalization. The fit is an extrapolation of the infinite-T baseline only. The noise budget is first-order accounting under an assumed model, not a device prediction.

### 9.4 Figures (B3, FLAG C)

`scripts/plot_q3.py` parses the saved data files only. It recomputes nothing except the a + b/N fit line on the size figure (the same weighted fit `run_q3_size.py` prints), and its parsers are tested against the files. It writes to `figures/` (gitignored). The palette is the dataviz skill's validated categorical light palette: CVD and normal-vision checks pass. Three slots sit below 3:1 contrast, so series are also distinguished by line style, and the data files are the table view. Every caption carries the classical / assumed-noise / not-H2 status line.

| figure | shows | source |
|---|---|---|
| `figures/q3_relaxation.png` | 3×6 ideal raw and conditioned curves (h = 0.1, 0.3) vs B_W₀ and DE, with the exact leakage envelope | `data/q3_relaxation.txt` |
| `figures/q3_field_scan.png` | late conditioned values vs h (with B_W₀/DE) and late P_out vs h | `data/q3_relaxation.txt` |
| `figures/trotter_threshold.png` | time-max Trotter error vs dt (log-log) with the dt² guide, the π/6 and π/4 resonances, ε and the working dt | `data/trotter_threshold.txt` |
| `figures/q3_noisy.png` | 3×4 ideal vs bare / bare + Gauss / Iceberg / Iceberg + Gauss, and both acceptances | `data/q3_noisy.txt` |
| `figures/q3_size.png` | sector baseline vs 1/N with the inferred fit; noise-budget times vs N at matched survival levels (50%, 1%) | `data/q3_size.txt` |

**Framing (K4).** These are physics and QEC-methodology results on classically reachable sizes: what the observables do, what the circuit and noise budget allow, and which mitigation pays. None is a claim of beyond-classical dynamics.

