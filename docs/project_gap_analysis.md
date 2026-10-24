# Project gap analysis — what is simulated, what is still missing (2026-10-23)

**Purpose.** A stock-take across all four SCOPE questions plus the §3 Gauss-law thread: what has
actually been computed, what is still missing before the project's data can carry the intended
preliminary analysis, and what each missing piece costs. Written at the project lead's request
while the Q3 size-axis cells were still running.

**Status conventions** (CLAUDE.md): every claim is tagged
[established] / [derived] / [measured] / [inferred] / [assumed] / [unverified].

**Standing caveat, true of every noisy number in this repository.** All noisy curves are
**classical predictions under an ASSUMED noise model** (the research/06 H2 prior), never H2 results.
**Nothing has been submitted to Quantinuum; 0 HQC have been spent.** The 50,000 HQC on the Nexus
usage page are emulator credits (H2-1E / H2-2E); no real-hardware allowance is shown
[established, usage page 2026-10-17].

---

## 1. What is simulated today

| SCOPE question | what exists | where | tag |
|---|---|---|---|
| **Q1** logical vs physical | Z2 second moment vs the **released Zenodo raw data** of 2503.20870: quench1 (θ = +30°) and quench2, local 4×4 and 4×5 against their 7×8 = 56-site H2 run, matched J·dt = 0.25, h·dt = 0.5, circuit-order Strang, ry(θ) prep; their ZNE+ZNR and raw columns with bootstrap bars; QASM bond set verified equal to `square_bonds(7,8,'periodic')` | `data/q1_compare.txt`, `docs/q1_compare.md` | [measured] |
| | encoded (Iceberg) machinery, comparison harness, noise-sensitivity prior — built and reviewed; **the matched encoded-vs-physical head-to-head is NOT run** | `handoff/05` | hardware-gated |
| **Q2** frustration | ground-state ED triangular vs square at 3×4 = 12: E/site, \|M_z\|, mean⟨ZZ⟩, defect density vs h | `data/frustration_compare.txt` | [measured] |
| | dimer correlations, winding sectors, constraint violations | `data/frustration_correlations.txt`, `docs/q2_frustration.md` | [measured] |
| | **emergent Gauss law confirmed quantitatively**: defect density per triangle ∝ (h/\|J\|)², measured slope **2.00–2.05** over four lattices/sectors, vs the first-order prediction (h/\|J\|)²/8 — ratio 1.01–1.10 at the smallest field | `data/gauss_law_scaling.txt` | [measured] |
| **Q3** thermalization | sector-restricted MCMC ergodic baselines at N = 18, 36, 54, 72, **144**, with 1/N extrapolation | `data/q3_size.txt`, `mcmc_baseline.txt` | [measured] |
| | Trotter-threshold and Trotter-order studies; ideal / noisy / encoded relaxation curves at 3×4; the λ noise-scaling ladder | `trotter_threshold.txt`, `trotter_order_compare.txt`, `q3_noisy.txt`, `q3_relaxation.txt`, `noise_scaling.txt` | [measured] |
| | **generalization study** (this pass): 7 of 11 cells at N = 12 over h ∈ {0.1, 0.2, 0.3, 0.5} and λ ∈ {1, 2, 3}; 4 size-axis cells (N = 18, 20) in flight | `q3_sweep.txt`, `q3_scaling.txt`, `docs/q3_scaling.md` | [measured] |
| **Q4** codes | all four built and Stim-verified end-to-end: Iceberg [[k+2,k,2]]; **concatenated Iceberg [[16,4,4]], measured distance 4**, all weight-1 errors detected, 0 undetected weight ≤ 3 data errors in both bases; 5-qubit [[5,1,3]]; Steane [[7,1,3]] | `data/encoded_codes.txt`, `concat_d4.txt`, `docs/qec_feasibility.md`, `docs/concatenated_iceberg_d4.md` | [measured] |
| | physical-qubit budget per code × lattice (what fits ≤ 24 locally / ≤ 55 on H2) | `data/encoded_codes.txt` §1 | [derived] |
| **§3** Gauss thread | 3×3 torus (N = 9) **exact density matrix**; post-selection benchmarked against ZNE (Richardson λ = 1,2,3, 57× sampling cost); single-error defect-detection probability **X/Y = 0.543, Z = 0.000** | `data/gauss_law_mitigation.txt`, `docs/gauss_law_dimers.md` | [measured] |
| platform layer | local-emulator + Selene validation; Nexus-hosted noiseless H2-1LE vs independent NumPy (19 points × 3 observables, worst \|z\| = 2.52, cost 0 HQC); 79+ circuits SC-quoted free; three-machine cross-platform checks; 15+ logged Quantinuum issues | `h2_le_validation*.txt`, `h2_hosted_*.txt`, `h2_sc_quotes*.txt`, `xplat_vm*.txt`, `docs/quantinuum_issues.md` | [measured] |

**One-line summary.** The machinery is built and verified, and one axis (Q3) is finished at
classically reachable sizes. What is missing is not components but **head-to-head comparisons**:
the project can currently describe each piece, and cannot yet rank them on a common task.

---

## 2. The four gaps

All four are **classical and need 0 HQC**. None requires hardware or the emulator.

### Gap A — codes at different distances: the advantage and its scaling

**Where it stands.** `docs/qec_feasibility.md` §"Which works best, and why" concludes Iceberg,
on the argument that the undetectable residual sits at the **arbitrary-angle rotation gadgets, not
the code distance**, so d ≥ 3 is dominated. That document tags the conclusion
**[inferred — to be backed by data]**. It is a plausible argument, not a measurement.

**Why it matters.** This is the whole answer to SCOPE Q4. As written, a referee can ask "how do you
know d = 4 does not help?" and the repo has no curve to show.

**What to run.**
1. **Same-task head-to-head.** Identical TFIM circuits, same lattice, same observable, same assumed
   prior, same shot budget, scored with the `score_cell` residual-vs-resource metric already built
   for Q3. Sizes that fit the local ceiling, from `data/encoded_codes.txt` §1:
   - **1×2 lattice: all four codes fit** — Iceberg 6, 5-qubit 12, Steane 16, concatenated 18
     physical qubits.
   - **2×2 lattice: three fit** — Iceberg 8, concatenated 18, 5-qubit 22; **Steane is 30 and is
     refused** by `check_physical_ceiling` [derived].
2. **Stim distance-scaling curves.** Logical error rate vs physical p for d = 2, 3, 4 at several
   code sizes, testing for the expected p^⌈d/2⌉ suppression and locating where it saturates. Stim
   is unbounded and free.
3. **Isolate the rotation-gadget residual as its own term** and show it is d-independent. This is
   the step that converts the central Q4 claim from [inferred] to [measured]; it wants a short
   derivation (the `derive` skill) alongside the Stim measurement.

**Cost.** Per the runtime model in §4: the 1×2 comparison is **minutes per code**; at 2×2 the
5-qubit arm (22 physical) is the expensive one at roughly **2.5 s per trajectory-step**
[derived from the measured 2^(physical) anchor]. Stim curves are minutes. No HQC.

### Gap B — Gauss-law post-selection: the definite yes/no

**Where it stands.** The (h/|J|)² law is measured; the N = 9 exact benchmark against ZNE is
measured; the Q3 sweep now shows bare + Gauss beating Iceberg for diagonal observables across a
fivefold field range and λ = 1–3 [measured, assumed prior].

**What is missing, in priority order.**
1. **The single-prior exposure.** Every noisy number in the project assumes one noise model
   (research/06). Given that Gauss-law detection is **blind to Z errors** (detection probability
   Z = 0.000 [measured, N = 9]), the verdict could be an artifact of that prior's Pauli
   composition. **A sensitivity sweep over the noise model itself** — X/Y/Z weights, gate-vs-
   measurement error ratio, with the λ ladder held fixed — is the highest-value missing classical
   run in the project, because it is the first thing a referee will ask and the cheapest to answer.
2. **Z-blindness as a scaling statement**, not one number at one size: it bounds what the method
   can ever achieve and is the physical reason it is a *detection*, not a *correction*, scheme.
3. **The benchmarks SCOPE §3 names are incomplete.** ZNE is done. **GUESS, symmetry-adjusted
   shadows, Cai's symmetry expansion and PEC are not** — and "benchmarked against exact-symmetry
   methods" is part of §3's own definition of done.
4. **Measured acceptance vs size** beyond N = 20, once the in-flight cells land, against the Stim
   accounting already in `data/q3_scaling.txt`.

**Cost.** The sensitivity sweep reuses the existing N = 12 cell path: observed wall time for the
seven landed N = 12 cells was roughly **0.5–2 h per cell** on the machines as they were loaded
[measured]; a 6–8 point noise-composition sweep is an overnight run on two hosts, serially per
host. No HQC.

### Gap C — logical vs physical for physical observables

**The sharpest gap in the project, and it cuts against our own headline.** The Q3 result holds for
**diagonal** observables only. The comparison was run exactly where Gauss-law post-selection is
strongest, so "bare + Gauss beats Iceberg" is currently a one-sided test.

**A structural point to settle first, by derivation.** The dimer/Gauss constraint operators are
**diagonal in Z** (products of Z on a triangle). Post-selecting on the constraint therefore requires
a Z-basis measurement, which destroys the X-basis information in the *same shot* — so for a global
off-diagonal observable (⟨X_i⟩, the energy's transverse term) post-selection and measurement appear
to be **mutually exclusive within a shot** [derived, NOT yet verified — this needs the `derive`
treatment before any code is written]. If that holds, it is a *structural* limit on the method, not
a numerical one, and it predicts that Iceberg should win the off-diagonal case for reasons
independent of noise strength. That is a stronger and more interesting result than the current
one-sided statement, and it is the honest completion of the claim.

**What to run,** after the derivation fixes the design:
- the encoded-vs-bare comparison on an observable set that includes **non-diagonal** operators
  (transverse-field term, X-basis correlators, total energy), at N = 12 and 18 where exact
  reference curves exist;
- note the implementation constraint: the encoded arm needs logical-X readout through the code's
  logical operators, and `src/observables.py` is a **verified core** — additive functions only.

**Cost.** Implementation is the dominant cost, not compute; the runs themselves are N = 12/18 cells
at the rates in §4. No HQC. Afterwards the calibrated version is the emulator run at
4×5 (**11,636 HQC**) or 4×6 (**13,679 HQC**), both already SC-quoted [measured].

### Gap D — frustration: NOT a gap. **Correction to an earlier version of this document.**

**An earlier version of this section called Q2 "thin" and recommended triangular-vs-square dimer
and winding contrasts at matched N plus larger sizes. That was wrong on two counts** and is
withdrawn:

1. **Q2 already meets its own definition of done.** `docs/q2_frustration.md` Part A is the
   triangular-vs-square comparison, by exact diagonalization on the matched **4×4** pair, and it is
   **reviewed ACCEPT** (`review/12`). `docs/findings_vs_questions.md`'s Q2 row records the
   "done when" as satisfied. Headline [measured]: the triangular nearest-neighbour ⟨ZZ⟩_c is
   **3.01× (h = 0.1) to 4.59× (h = 1.0)** weaker than on the bipartite square, and **4.98×** at
   h/|J| = 2, while the bipartite square shows no decay across the torus at all.
2. **The work it recommended was cancelled by the project lead, not left undone.** Part B (size
   trend, error bars, winding/defect presence-vs-absence) was **CANCELLED under PROC-2** (no new
   classical depth after handoff/09). Recommending it back is relitigating a decision.

Two further facts make the recommendation ill-posed as well as out of scope: the dimer, defect and
winding observables are **triangular-only by construction**, so there is no square counterpart to
compare them against (they belong to `docs/gauss_law_dimers.md`, where the defect density
∝ (h/|J|)² law, slopes 1.96–1.98, already lives); and within the ED ≤ 20 ceiling there is exactly
**one** clean bipartite square torus, 4×4 (T-21), so a square size trend has a single point — which
is *why* Part B was cancelled rather than deferred.

**What is genuinely open on Q2**, both recorded as flags in `docs/q2_frustration.md` §0:

- **T-20, the clock-order parameter K3** — the only observable that separates genuine
  three-sublattice (clock) order from the torus-shape sign effects Part A reports but declines to
  interpret. Not built; **the project lead's call**, since PROC-2 bars new classical depth.
- **T-21** — structural, not fixable below the ceiling.

So the only Q2 decision available is whether to revisit PROC-2 for K3. If the article's novelty is
to rest on the frustration spine, that is the one measurement that would strengthen it — but it is
a scope decision, not a gap I can close.

**Note on wording elsewhere:** SCOPE §2's Q2 status line reads "dimer-correlation/winding-vs-square
contrasts and larger sizes still thin", which reads as unfinished when it is in fact scoped down by
decision. SCOPE is the contract and has not been edited; the discrepancy is flagged here so the
next reader does not repeat this mistake.

---

## 3. Decision cards (for `DECISIONS.md` if approved — the project lead's call)

Numbering continues the file's open series (OPEN-2 and OPEN-3 are still open; OPEN-4 became
DECIDED-6).

### OPEN-5 — Does the project add non-diagonal observables to the encoded-vs-bare comparison?

**Question.** The Q3 verdict covers diagonal observables only. Do we extend the comparison to
off-diagonal observables (transverse term, X-basis correlators, energy)?

| option | what it costs | what it buys |
|---|---|---|
| **(a) derive first, then implement** (recommended) | a derivation pass, then additive observable code + N = 12/18 runs | settles whether Gauss post-selection is *structurally* excluded off-diagonal; makes the headline two-sided; likely a stronger result than the present one |
| (b) implement directly, no derivation | less up-front work | risks building a comparison whose negative result was predictable on paper |
| (c) leave the claim diagonal-only | nothing | leaves the article's central efficiency claim open to a one-sentence referee objection |

**Recommendation: (a).** The derivation is cheap and may convert a numerical finding into a
structural one. State the diagonal-only restriction explicitly in the write-up either way.

### OPEN-6 — Does the noise-model sensitivity sweep happen before any H2 spend?

**Question.** Every noisy conclusion assumes the research/06 prior. Do we sweep the noise model's
composition before committing emulator credits?

| option | cost | consequence |
|---|---|---|
| **(a) sweep first** (recommended) | one overnight classical run, 0 HQC | the published verdict carries a robustness range instead of a single assumed prior; Z-blindness is quantified where it matters |
| (b) spend credits first, sweep later | 0 extra | risks calibrating against a prior whose composition drives the answer |
| (c) no sweep | 0 | the strongest available objection to the Gauss result goes unanswered |

**Recommendation: (a).** It is the cheapest defensive run in the project and needs no credits.

### OPEN-7 — How is the code-distance question settled?

**Question.** Q4's "which code works best and why" currently rests on an [inferred] argument that
the rotation-gadget residual dominates code distance.

| option | cost | consequence |
|---|---|---|
| **(a) same-task head-to-head at 1×2 and 2×2 + Stim d = 2,3,4 curves + isolate the gadget residual** (recommended) | hours of classical compute; some new scoring glue | converts the central Q4 claim to [measured]; gives a figure rather than a paragraph |
| (b) Stim curves only | less | shows distance scaling but not the gadget term that is the actual argument |
| (c) keep it [inferred] | 0 | Q4's definition of done ("implemented path has data") is not met |

**Recommendation: (a)**, with Steane excluded at 2×2 (30 physical qubits exceeds the ceiling and
must be refused, not approximated).

---

## 4. Runtime model used for the estimates above

Anchored on measurements taken during this pass, so the estimates are auditable rather than guessed:

- cost is **per trajectory and scales as 2^(physical qubits)** [measured, this pass]: 16 physical
  qubits ran at ~0.039 s per trajectory-step uncontended, 22 physical at ~2.5 s — a factor 64 for
  2^6 more amplitudes [derived];
- interpolating that anchor: **18 physical ≈ 0.16 s, 20 physical ≈ 0.6 s, 24 physical ≈ 10 s** per
  trajectory-step [derived, not individually measured];
- the dominant cost is gate-by-gate state-vector application (~68 % in `numpy.tensordot` via
  `backends_qc.apply1/apply2`, with ~245 k non-contiguous `reshape` copies), and observable
  evaluation is ~24 % [measured, cProfile];
- therefore **heavy cells run serially, one per host, with `OMP_NUM_THREADS=1`** and the
  OpenBLAS/MKL/numexpr equivalents: parallel heavy cells on one host lose more to memory bandwidth
  than they gain in concurrency [measured — four concurrent cells ran ~28× slower each than the
  baseline implies];
- Stim and MCMC are cheap: the whole Stim prefilter is minutes, and MCMC baselines ran 6–77 s per
  size up to N = 144 [measured].

An optimisation opportunity exists and has **not** been taken: an in-place / reshape-free gate
applier could plausibly cut the dominant term 2–3×. `src/backends_qc.py` is not on the
verified-core list but is load-bearing for the whole encoded pipeline, so any such change needs the
transparency and Stim cross-checks re-run. The project lead's call.

---

## 5. Recommended order, and what is actually hardware-gated

1. **Finish the Q3 size axis** (in flight: 18:0.3:1, 18:0.1:3, 20:0.3:1, 20:0.5:3).
2. **Gap C** — non-diagonal observables (derivation first). Fixes the one-sided headline.
3. **Gap B** — noise-model sensitivity sweep. Fixes the single-prior exposure.
4. **Gap A** — code head-to-head + Stim distance curves. Makes Q4 definite.
5. **Gap D is withdrawn** (Q2 is done and Part B was cancelled). If the frustration spine is to
   carry the novelty, the live question is **T-20 / K3**, which is a PROC-2 scope decision.
6. **Then** emulator credits, each step gated on the project lead's go: G1 (1,901 HQC) first, compare
   against the local emulator and Selene, then Q1 at 4×5 (11,636) or 4×6 (13,679).

Steps 2–5 need **no credits at all**. The emulator spend is a calibration layer on top of them,
which also means a late hardware allowance costs the project nothing in the meantime.

**Genuinely hardware-gated** (not fixable by classical work): the matched encoded-vs-physical
head-to-head on H2 noise; any 6×6 triangular run (36 bare / 40 encoded qubits — fits H2's 56-qubit
hardware register, exceeds the emulator's 32-qubit state-vector mode, and cannot be verified
classically: 1.1 TB / 17.6 TB of amplitudes [derived, DECIDED-6]); and the H2-calibrated code
ranking. Relevant limits on the encoded 6×6 arm, from `data/q3_scaling.txt` [derived, 2q scope]:
Iceberg survival reaches 5 % at t = 4.61 and 1 % at t = 7.26 against an h = 0.3 physics window of
t ≈ 8, while the bare arm carries ≈ 11 faults per shot over that window — so a hardware 6×6 run
buys a **shorter time window**, not the same study at a larger size.
