# Review 09 — Q3 sector-restricted MCMC ergodic baseline (handoff/07)

**VERDICT: ACCEPT. No Critical or Major findings.** Three minor items for relay (all in Claude Code's docs/data; none affect correctness). Full suite 195/195 verified; the 26 new tests pass; every claim I could reach was reproduced with independent code.

Reviewer: qc-reviewer (independent). Deliverable: `src/mcmc_baseline.py`, `tests/test_mcmc_baseline.py` (26), `scripts/run_q3_baseline.py` → `data/mcmc_baseline.txt`, `data/q3_relaxation.txt`, `docs/q3_thermalization.md`, `config.py: Q3BaselineConfig`, journal Entry 26, open-questions T-11/T-12/T-13.

Method: I re-implemented the geometry-independent pieces (basis enumeration, defect/flippable/winding operators, H_QDM build, connected-components, diagonal ensemble, flippable-flip chain, Floquet dressing, leakage decomposition) in a fresh script that imports `src.dimers` **only** for bond/triangle/hexagon geometry, and compared against the write-up's numbers and the data files. Script and raw output retained at `/tmp/indep_check.py` (ephemeral; findings below quote its output).

---

## (A) Independently verified correct — with evidence

**A1. Per-sector restriction is correct AND necessary (brief item 1).** My own brute-force enumeration of 3×4, picking the most-flippable defect-free state as c₀, gives **W₀ = (0, 2)** and:
- sector flippable density **0.2667**, global (winding-blind defect-free) **0.2353** — exact match to `docs/q3_thermalization.md §1` and `data/mcmc_baseline.txt §2`;
- sector ρ_v **0.5000** vs global **0.4412** — exact match;
- sector size 60, global size 68, and the 68 defect-free states split across **three** disconnected winding sectors {(0,−4), (0,2), (6,−4)}.
A winding-blind average therefore mixes sectors the flippable-flip dynamics cannot connect and yields a different (spurious) value. **Verified: the restriction changes the answer and is required.** `src/mcmc_baseline.py:exact_references` reproduces the component / sector / global split correctly (`ExactReferences`, L~300).

**A2. Ensemble choice = infinite-T over the flip component (brief item 2).** Independent build of H_QDM = −h Σ Π_s X_s restricted to the 3×4 W₀ component (dim 60): spectrum ∈ [−3.464, 3.464], **Σ eigenvalues = 5.8e-15** (symmetric about 0 to machine precision, `|w_i + w_{−i}|_max = 2.9e-15`). The anticommutation argument is exact: with P = diag((−1)^{#up}), **|P H P + H|_max = 0.00e+00**, so P H P = −H and the spectrum is symmetric → a product state sits at the band centre = infinite temperature for the constrained model. **Verified.** (Matches the module docstring and §2.)

**A3. Sampler correctness (brief item 3).** The flippable-flip kernel: flippability of s depends only on its hexagon neighbours, which the flip leaves fixed, so the move is its own inverse at probability 1/N ⇒ symmetric ⇒ uniform on each component; and each move is one term of H_QDM, which commutes with every D_t and winding cut ⇒ sector-preserving. I ran my own 5000 independent chains on 3×3 (100 sweeps from the 3-sublattice c₀): **χ² uniformity p = 0.87** over the 42-state component, **all final states in the component**, defects stayed 0. `src/mcmc_baseline.py:sample_sector` additionally re-checks the defect count and every row/column winding cut each sweep and raises on violation (`test_sampler_raises_if_not_in_a_sector` confirms the guard fires). **Verified.**

**A4. Convergence with autocorrelation-aware errors (brief item 4).** The code's SE is the between-chain SE = std(chain means)/√M, which absorbs autocorrelation; τ_int = (SE/SE_naive)²/2 is reported beside it (`_estimate`, L~360). My own long single chain for `memory` on 3×6 gives **τ_int ≈ 3.9**, so the naive 1/√N SE understates the error by **≈2×** — consistent with the data file's τ_int = 2.2 (3×6) / 3.9 (9×6) and the write-up's "2–3× too small" claim. The MCMC-vs-exact table (`data/mcmc_baseline.txt §2`) has max |z| = 1.39 over discriminating observables across 3×3/3×4/3×6/4×5; I re-derived the sector exact values for 3×4 and they match. **Verified: errors are not naive, and convergence is real.**

**A5. O(h²) dressing / Floquet formula (brief item 5).** I re-derived g(c) = (1/2N) Σ_s n_s (dt/2)² / sin²(|J| n_s dt) for the Strang step and checked:
- **stripe limit:** n_s = 2 everywhere, g(dt→0) = **0.0625 = 1/16** exactly → ρ_D = (h/|J|)²/8, the value in `docs/gauss_law_dimers.md §4`;
- **against direct Trotter** on 3×4 at h = 0.05: measured ρ_D = 2.09e-4, predicted h²(⟨g⟩_DE + g(c₀)) = 2.07e-4, **ratio 1.008** — matches the test `test_dressed_defect_density_matches_dynamics_small_h` (rel 0.03) and the data file ratios (0.96–1.09).
**Verified.** The two-term structure (static dressing of visited configs + real excitations of c₀ frozen by the Ising energy label) is physically sound for a sudden quench time-averaged over the diagonal ensemble.

**A6. Leakage bound (brief item 6).** |⟨O⟩ − ⟨O⟩_in| = P_out·|⟨O⟩_out − ⟨O⟩_in| ≤ P_out·range(O) is elementary from the convex decomposition ⟨O⟩ = (1−P_out)⟨O⟩_in + P_out⟨O⟩_out. On my own 3×6 Trotter runs the tighter form the test asserts (range ≤ 1) holds with **max(|raw − cond| − P_out) = 0.00e+00** at both h = 0.1 and h = 0.3. The measured late-window P(W≠W₀) is **1.703e-3 (h=0.1)** and **1.662e-2 (h=0.3)**, matching the data file exactly, and my log-log fit of the `data/gauss_law_scaling.txt` 3×6 row gives slope **2.082** (file prints 2.08). The scaling-table prediction matches the run to ≈1% on 3×6. **Verified: bound holds, slope is the repo's own measured value, no hard-conserved-sector claim is made.**

**A7. Ceilings respected (brief item 8).** `check_exact_ceiling` refuses 2^N enumeration above ED=20; `relaxation_curve` is guarded at the **ED** ceiling because it builds 2^N×3N occupation tables (review-fix m2, confirmed in `test_ceilings_refuse_before_allocating` at N=21). The MCMC itself works on configurations only and scales to 9×6 (N=54) in ~15 s (`test_mcmc_runs_beyond_the_exact_ceiling`). Every output line in both data files carries the "CLASSICAL … NOT quantum hardware, NOT an H2 result" caveat; no number is presented as a quantum/H2 result. **Verified.**

**A8. Observable definitions identical on both arms (brief item 9).** `ConfigEvaluator` rebuilds the dimer/defect/flippable/winding operators from the same `TriangularDimers` geometry and is tested equal to the `src/dimers.py` 2^N arrays on **every** basis state of 3×3/3×4/4×3 (`test_config_evaluator_equals_dimers_operators_on_every_basis_state`). Both arms route C(r) through one `shell_correlations`, tested equal to `dimer_correlation_by_distance`. The quantum arm uses the dimers.py arrays directly. **Verified: the comparison is like-for-like.**

**A9. Coherence after the two-session collision (T-13).** No duplicate function/class definitions, no dead code, no leftover-session markers in `src/mcmc_baseline.py` or `scripts/run_q3_baseline.py`. The module imports cleanly, the script is config-driven (`CONFIG.q3`), and `config.py:Q3BaselineConfig` is added additively in the existing dataclass style. The surviving code is internally consistent. **Verified: nothing from the discarded session leaked in incoherently.**

**A10. Suite + done-check.** `python -m pytest -q` → **195 passed** (verified, 106 s). `tests/test_mcmc_baseline.py` → **26 passed**. `docs/findings_vs_questions.md` Q3 row updated to [measured]; data caveats present; sampler/sector/convergence/leakage/ceiling tests all present. All handoff/07 done-check items are met.

---

## (B) Could not fully verify (scope / size bounded — honestly flagged by the authors)

**B1. Single-component sectors above N = 20 (T-11).** The claim "each non-frozen sector is one flip component" is exact-enumeration-backed only to N ≤ 20 (I did not re-run the full census, but reproduced the component/sector equality on 3×4). Above N = 20 the MCMC samples the component of c₀ *by construction*, so "sector = component" is genuinely [unverified] there — and the write-up (§2 point 5) and T-11 say exactly this. Not a defect; correctly tagged.

**B2. Thermodynamic-limit thermalization.** The quantum curves stop at 3×6 (statevector ceiling), where the finite-size offset dominates. The write-up §7 explicitly declines any N→∞ thermalization claim. Correctly bounded.

**B3. dt-dependence / Trotter-threshold / prethermalization.** Only dt = 0.25 was run; the Heyl–Hauke–Zoller and Yang et al. anchors are cited with no numbers imported. The slow-relaxation 2401.11294 behaviour is noted as consistent-but-untested. Correct per the brief ("import no numbers").

---

## (C) Findings by severity

**Critical: none. Major: none.**

**T-12 scrutiny (brief item 7) — SOUND and honestly reported; recorded as context, not a finding.**
The claim: the DE-vs-uniform offset (flippable density **0.092 at N=9 → 0.057 at N=18**) vanishes as N→∞ via the energy-density variance h²f(c₀)/N → 0. I reproduced the offsets exactly (my enumeration: +0.0919 at 3×3, +0.0571 at 3×6). Assessing the physics:
- The DE weights eigenstates by |⟨E|c₀⟩|², i.e. a microcanonical shell at energy density e₀ = 0 with intensive variance σ²/N = f(c₀) (h is only the time unit here and drops out). By the band's exact 0-symmetry (A2) the linear response at the band centre vanishes, so the leading offset is governed by the *energy-density width* → 0 as 1/√N, and the observable offset by its square-ish suppression. The mechanism is physically reasonable.
- My N-trend check: N·offset = {0.83 (N=9), 1.03 (N=18)} at **fixed** c₀ (f(c₀)=0.667) is roughly O(1), i.e. **consistent with offset ∝ 1/N**. The third point, N=20 (4×5), uses a *different* c₀ (f(c₀)=0.400), so it is not on the same curve and should not be read as a trend point.
- **Honesty check:** the write-up tags this **"[inferred, not demonstrated beyond N = 18]"** in §2, repeats it in §7 Open, and T-12 states "vanishing as N→∞ is [inferred]" and "the energy-variance account … is qualitative; it is not a quantitative prediction of the DE value." This is exactly right. The evidence is 2 same-c₀ points — thin, as admitted. **No overreach.** The argument is sound as a scaling expectation and correctly not sold as proof.

**minor (relay to Claude Code — do not edit; these live in Claude's docs/data):**

- **m1.** `docs/q3_thermalization.md §5` says the leak prediction matches "to 1–25%". The widest miss in `data/q3_relaxation.txt` is the 3×4 flippable h=0.1 row: predicted 1.503e-3 vs measured 1.884e-3 ≈ **20% (within range)**; the h=0.3 row is 2.055e-2 vs 1.820e-2 ≈ 13%. The "1–25%" band is honest, but it would be clearer to name that the >10% misses are the noisy h^2.38 3×4-flippable fit (the write-up already attributes it to "where the table fit is poor"). Wording only.

- **m2.** `docs/q3_thermalization.md §6` quotes the 3×6 late conditioned flippable density as **0.384** against DE 0.388 and B_W₀ 0.331; the data file late_cond values are 0.3835 (h=0.1) / 0.3839 (h=0.3). Consistent; just note the doc rounds to 0.384 while the headline table in `findings_vs_questions.md` also says 0.384 — fine, but the §6 table shows "0.3835 ± 0.018 / 0.3839 ± 0.019" with the ± labelled a temporal std. The DE value 0.388 is confirmed by my independent diagonalization (0.3880). No numeric error; optional precision note.

- **m3.** `docs/q3_thermalization.md §6` "Review" paragraph refers to an internal reviewer sub-agent's ACCEPT-WITH-FIXES. That is Claude Code's own internal review, not this (Kiro) milestone review; harmless, but a reader could conflate them. Consider a one-word clarifier ("internal pre-review"). Doc wording only.

None of m1–m3 affects correctness or the verdict.

---

## Bottom line
The baseline is correct, the sampler is provably uniform and sector-preserving, the errors are autocorrelation-aware, the dressing and leakage formulae re-derive and match direct dynamics, ceilings and the classical-only discipline are respected, observables are identical across arms, and the surviving code is coherent after the session collision. The one claim that could overreach — the N→∞ vanishing of the finite-size offset (T-12) — is explicitly and correctly tagged [inferred, not demonstrated beyond N=18], and my own scaling check is consistent with it. **ACCEPT.** Relay m1–m3 to Claude Code; T-6 may move to Resolved; the next stage (qc-annotator) can proceed.
