# Review 10 — handoff/08 Part A (Q3 Trotter-threshold study, K2) — CHECKPOINT

**Verdict: ACCEPT-WITH-FIXES. No Critical or Major finding. Part B may be released.**
All fixes below are minor (doc/data wording) and belong to Claude Code — the reviewer edits nothing.

Reviewer: qc-reviewer (independent). Environment: `.venv`, Python 3.12.14, suite re-run green
(**205 passed in 107.9 s**, confirmed by me, not reported). Every discriminating check below was
run with my OWN scipy-only reference code (dense `scipy.linalg.expm` / sparse
`scipy.sparse.linalg.expm_multiply`), never the authors' Chebyshev propagator and never by
re-running their tests. Scratch scripts were deleted after use.

Scope reviewed: `src/trotter_threshold.py`, `tests/test_trotter_threshold.py` (10),
`scripts/run_trotter_threshold.py` → `data/trotter_threshold.txt`, `config.py:Q3BaselineConfig`
(`thr_*`, `h_curves`), `data/q3_relaxation.txt`, `docs/q3_thermalization.md` §6/§8,
`docs/findings_vs_questions.md` K2 row, journal Entry 32.

---

## (A) Independently verified correct — with evidence

**A1. The Chebyshev `ExactPropagator` is actually exact (load-bearing).** `src/trotter_threshold.py:70-108`.
My own reference, both dense `expm` and sparse `expm_multiply`, on a random complex state:

| cluster | h | t=0.13 | t=1.7 | t=5.0 | t=20.0 |
|---|---|---|---|---|---|
| 3×3 (N=9) | 0.3 | 4e-16 | 9e-15 | 1e-13 | 3.6e-13 |
| 3×4 (N=12) | 0.1 | 5e-16 | 2e-14 | 3.5e-14 | 9.6e-14 |
| 3×3 (N=9) | 0.5 | 5e-16 | 8e-15 | 5e-14 | 2.6e-13 |

(L2 norm of the difference.) Agreement is ≤ ~3.6e-13 even at the full study time T=20, i.e. well
inside the "~1e-12 or better" ask; Kiro's own ~1e-15..1e-13 range is confirmed. The error grows
only linearly-ish with t (coefficient truncation), as expected. **The reference everything is
measured against is exact.** [verified]

**A2. O(dt²) Strang / O(dt⁴) infidelity.** `src/trotter.trotter2_step`, 3×3 3-sublattice, h=0.3,
T=5, my dense-`expm` reference at common times (independent of their Chebyshev and their
`loglog_slope`):
- flippable-density max error at dt = (0.1, 0.05, 0.025): ratios 4.12, 4.03; **log-log slope 2.025**.
- infidelity ratios 16.78, 16.19; **log-log slope 4.043**.
Matches the data file's per-case slopes (2.00–2.04 local, 4.00–4.03 infidelity, all 24 rows).
[verified]

**A3. Threshold ≈ π/(|J| n_s) Floquet resonance, and the derivation is sound.** The physics is
standard and correct: flipping a non-flippable spin creates `n_s` defects each costing 2|J|
(`src/mcmc_baseline.py:136` `equal_hex_pairs`, "flipping s creates n_s defects"), so the Ising gap
is `E = 2|J| n_s`. The stroboscopic Trotter drive aliases this gap to zero when `E·dt = 2π`, i.e.
**|J| n_s dt = π** — exactly the claimed resonance, and the first-order Floquet/Magnus
admixture denominator `sin²(E dt/2) = sin²(|J| n_s dt)` is the correct, standard form (matches the
dressing term `src/mcmc_baseline.py` `dressing`). The derivation is not an overreach.
My own dense-`expm` scan confirms the blow-up:
- **3×3 3-sublattice (n_s=6 → 0.524):** time-max flippable error 6.1e-3 (dt=0.25) → 4.7e-2 (0.40)
  → 0.11 (0.45) → 0.22 (0.50): a sharp jump straddling 0.524, as predicted.
- **3×4 stripe (n_s=2 only → 1.571), discriminating:** 6.5e-5 (0.25) → 2.7e-4 (0.50) → 2.6e-3 (1.0)
  → 6.5e-2 (1.5): stays smooth through dt=0.5 (where the n_s=6 start has already broken) and only
  breaks near its own π/2. The data file's §1 stripe scans and the n_s=4 secondary spike at
  dt≈0.785 (3×4 flippable) are consistent. **The resonance picture is real and discriminating.** [verified]

**A4. dt = 0.25 placement is stated honestly, not overstated.** From `data/trotter_threshold.txt`
§Summary and my reading of the per-case tables:
- h ≤ 0.3: dt=0.25 is below both the absolute (×1.5–2.0) and relative (×1.3–1.8) thresholds; time-max
  flippable error 0.01–0.18 ε. Correct.
- **h = 0.5: dt=0.25 is PAST the relative threshold** (3×3 3-sub relative bracket (0.18,0.20]; 3×4
  flippable (0.22,0.24]) — both below 0.25, so threshold/dt < 1 ("0.72–0.80× dt", "0.88–0.96× dt" in
  the summary). It remains ×1.3–1.6 below the *absolute* threshold. The doc (§8) and K2 row flag
  h=0.5 explicitly as a stress point "not a result". **Not overstated.** [verified]

**A5. Late-window bias: conditioned verdict quantities are Trotter-robust; raw/P_out/defect are not.**
Reproduced independently with `expm_multiply` on 3×6 (N=18) and 3×4, matching the data file §3 to the
printed digits:

| case | h | cond_flip bias (/std) | raw P_out bias (%) | raw defect bias (%) |
|---|---|---|---|---|
| 3×6 3-sub | 0.3 | −2.4e-3 (**0.12**) | +22.3% (2.77 std) | **+39.0%** (6.29 std) |
| 3×6 3-sub | 0.5 | +9.2e-4 (**0.06**) | +13.0% (2.83 std) | +25.7% (6.40 std) |
| 3×4 flippable | 0.5 | −3.1e-4 (**0.03**) | +9.8% (1.55 std) | +16.0% (2.71 std) |

The sector-conditioned verdict quantities (flippable density, memory, C) carry ≤ 0.12× the verdict
tolerance (temporal std) across h=0.1–0.5 — the Q3 verdicts are **not** Trotter artefacts at dt=0.25.
`test_bias_table_conditioned_value_is_the_verdict_quantity` ties the COND columns to
`src/mcmc_baseline.classify.late_cond`/`late_raw` (I confirmed those fields exist, `mcmc_baseline.py:598`).
The raw P_out inflation (10–25%) and raw defect-density inflation (~40% on 3×6 at h=0.3) are real and
correctly attributed to sector leakage, not to the conditioned signal. **Verified; the
conditioned-vs-raw distinction is substantive, not cosmetic.** [verified]

**A6. Discipline / ceilings / additivity.**
- **Ceilings:** `check_exact_ceiling` is called in `ExactPropagator.__init__`, `observable_function`,
  `trotter_error_scan`, and `late_window_bias` before any 2^N allocation;
  `test_ceilings_refuse_before_allocating` and `test_public_builders_guard_the_ceiling` exercise
  N=21 > 20 → `MemoryCeilingError`. [verified]
- **Additive to cores:** `trotter_threshold.py` *imports and reuses* `trotter2_step`,
  `ising_diagonal`, `tfim_hamiltonian`, and the handoff/07 `mcmc_baseline` API
  (`relaxation_curve`, `Shells`, `classify`, `ConfigEvaluator`, `check_exact_ceiling`); it defines no
  new physics in the cores. The field scan uses `curve_cases`/`initial_spins` unchanged from
  handoff/07. `config.py` additions are a new `thr_*` block + `h_curves` broadened (0.1,0.3)→
  (0.1,0.2,0.3,0.5). [verified — by reuse, since there is no git history to diff]
- **Classical / no-H2 tagging:** data header "CLASSICAL noiseless simulation only … NOT quantum
  hardware, NOT an H2 result"; `q3_relaxation.txt` carries the same caveat; §8 and the K2 row say
  "Classical only". [verified]
- **10 tests, all green**, collected and named sensibly. [verified]

**A7. Done-check items present.** `src/trotter_threshold.py` (ExactPropagator, dt scans,
`floquet_resonances`, `locate_threshold`, `late_window_bias`) ✓; 10 tests ✓; script →
`data/trotter_threshold.txt` ✓; `config.py:Q3BaselineConfig` `thr_*` + broadened `h_curves` ✓;
`data/q3_relaxation.txt` regenerated with h∈{0.1,0.2,0.3,0.5} ✓; `docs/q3_thermalization.md` §6
updated + new §8 ✓; K2 row in `findings_vs_questions.md` ✓; journal Entry 32 ✓; suite 205/205 ✓.

---

## (B) Could not verify (stated plainly)

- **`mcmc_baseline.txt` content unchanged.** The file's mtime (18:14) is inside this pass, and
  `scripts/run_q3_baseline.py` writes it unconditionally, so it *was rewritten*. There is no git
  history in the repo to diff against, so I cannot byte-confirm the content is identical to the
  prior version. The MCMC baseline (sector census + per-sector averages) is field-independent, so a
  content change would be physically surprising; I judge this low-risk but **unverified** (mtime ≠
  authorship/content, per KIRO.md). Suggest Claude confirm the baseline numbers are untouched.
- **9×6 threshold value.** The study locates the threshold on N ≤ 18 only; its value on the 9×6 H2
  lattice is [inferred] in §8 (resonance physics is local). Correct non-claim; not independently
  checkable here (above the ED ceiling), and the doc does not claim it. No action.
- **Long-time Trotter heating (Yang et al. prethermalization).** Not studied beyond T=20/|J|; §8 says
  so. Out of Part-A scope; fine.

---

## (C) Findings by severity

**Critical:** none.

**Major:** none.

**minor (all Claude Code's to apply — reviewer does not edit the work):**

- **m1 — §8 vs test tolerance wording.** `docs/q3_thermalization.md` §8 "Method" says the Chebyshev
  propagator is tested "to ≤ 1e-10". The test asserts `< 1e-10` but the actual agreement is
  ~1e-13 (and I measure ~3.6e-13 at T=20). The "≤ 1e-10" is a conservative *test bound*, not the
  achieved accuracy; consider stating "asserted < 1e-10; achieved ~1e-13" so the propagator's real
  quality isn't understated. Cosmetic.
- **m2 — defect-density inflation figure differs by start.** §8 and the K2 row quote "~40% on 3×6,
  ~18% on 3×4". `docs/gauss_law_dimers.md:130` still says the dt=0.25 defect density is "about 10%
  higher" (measured on the 3×4 *flippable* start in that study). Both are correct for their own
  start, but a reader hitting both docs will see 10% vs 40% with no bridge. See T-15 below. Doc
  consistency only.
- **m3 — `mcmc_baseline.txt` rewrite.** As in (B): either make `run_q3_baseline.py` leave
  `mcmc_baseline.txt` untouched when only the field scan changed, or state in the header that it is
  regenerated identically. Housekeeping, not a correctness issue.
- **m4 — stripe "small error" framing.** §8 "Reading" is already careful ("'Small' is absolute only:
  at dt=0.5 that error is ≈70% of its own tiny late defect density"), which is the honest statement.
  No change needed — noted here only so the overseer sees it was checked and is sound, not an
  overreach.

---

## T-15 recommendation (Kiro's doc decision, one line)

**Yes — add a one-line cross-reference in `docs/gauss_law_dimers.md` (near line 130) pointing to
`q3_thermalization.md` §8**, because the new study shows the dt=0.25 defect-density Trotter
inflation is start-dependent (≈40% on the 3-sublattice start, ≈18% on 3×4 flippable, ≈10% stripe) —
so the gauss-law doc's standalone "~10%" is only the flippable-start value and reads as inconsistent
without the pointer; the §8 blend-of-Floquet-factors mechanism (predicted 1.39–1.44× on 3×6, matching
measured) explains why.

---

## Bottom line

No Critical/Major finding. The exact propagator is genuinely exact, the O(dt²) order and the
π/(|J| n_s) Floquet-resonance threshold reproduce under fully independent scipy references, dt=0.25
is placed honestly (safe for h ≤ 0.3, flagged as a stress point at h=0.5), and the sector-conditioned
Q3 verdicts are Trotter-robust while the inflation correctly lives in the leakage. Discipline
(classical tagging, ceilings, core additivity, handoff/07 reuse) holds. **ACCEPT-WITH-FIXES — release
Part B.** The four minor items are Claude Code's to apply and do not gate the checkpoint.
