# Review 06 — Adjudication of qc-scout's literature-discovery recommendations

**Reviewer:** qc-reviewer (adjudicator) · **Date:** 2026-10-06
**Inputs reviewed:** `research/scout/sweeps/01-gauss-law-and-ice.md`, `research/scout/sweeps/02-frustration-and-simulation.md`,
`research/scout/INDEX.md`; targets `docs/findings_vs_questions.md`, `docs/gauss_law_dimers.md`, `docs/qec_feasibility.md`,
`SCOPE.md §2/§3`, `research/01-stage1-conventions.md`, `research/03-stage3-triangular.md`, `research/04-gauss-law-citations.md`.
**What this file is:** findings only. I rule on each of the scout's 7+7 "what should change" items. I write no docs/src/config;
the overseer applies approved edits. SCOPE's skeptical prior and the never-invent-numbers rule are kept.
**Note on `sources.md`:** the task named `Conversation history/sources.md`; no such file exists in the repo (`**/sources.md`
returns nothing). The scout's `INDEX.md` and `research/04-gauss-law-citations.md` are the source registries I used instead.

---

## 0. Sources I independently verified this session (verbatim abstract text, arXiv abstract pages, 2026-10-06)

All fetched live from arxiv.org abstract pages. Quotes are copied from the page I read.

- **arXiv:1706.02601** (Lan & Powell, PRB 96, 115140 (2017)): "We find that ETH is clearly satisfied only when each topological
  sector is treated separately, and only for moderate ratios of the potential and kinetic terms in the Hamiltonian. By contrast,
  when the spectrum is treated as a whole, ETH breaks down on the square lattice, and apparently also on the triangular lattice."
  → the scout's Q3 "per-sector ergodic baseline" claim is **verbatim-accurate**, square AND triangular. **VERIFIED.**
- **arXiv:2405.18504** (Wauters, Ballini, Biella, Hauke; v3, 19 Mar 2025): "a sharp transition, triggered by the measurement rate,
  between a protected gauge-theory regime resistant to simulation errors and an irregular regime… the paradigmatic example of a
  **1+1d Z₂ LGT**… protection through **projective measurements of ancillary qubits coupled to the local symmetry generators**…
  Additionally, we design an **on-chip feedback mechanism that corrects bit-flip errors** and significantly enhances the discrete-time
  scheme." → the scout's "on-chip bit-flip correction + measurement-rate threshold" claim is **verbatim-accurate**. **VERIFIED.**
  Caveats the scout under-stated: it is **1+1d** (not 2D), and correction is via **engineered ancillas coupled to the generators +
  feedback**, i.e. an *added* apparatus, not the project's bare emergent constraint.
- **arXiv:cond-mat/0302105** (Isakov & Moessner, PRB 68, 104409 (2003)): "extended critical phase in the transverse field Ising
  magnet on the triangular lattice… separated by two Kosterlitz-Thouless transitions from the paramagnet on one hand and the
  quantum-fluctuation driven three-sublattice ordered phase on the other… the zero temperature quantum phase transition is in the
  3d XY universality class." → scout's phase-diagram claim **verbatim-accurate**. **VERIFIED.**
- **arXiv:cond-mat/0103396** (Moessner, Sondhi, Fradkin, PRB 65, 024504 (2002)): QDMs "arise as particular limits of Ising (Z_2)
  gauge theories, but… in these limits the system develops a larger local U(1) invariance that has different consequences on
  different lattices… the standard Z_2 gauge theory is a generalised quantum dimer model, in which the particular relaxation of the
  hardcore constraint for the dimers breaks the U(1) down to Z_2." → the Z₂/U(1) statement is **real but subtler than the scout's
  gloss**; see item 01-3 below. **VERIFIED (with correction to the scout's framing).**
- **arXiv:1303.0883** (Iglovikov, Scalettar, Oitmaa, Singh, PRB 87, 214415 (2013)): "square lattice with nearest-neighbor
  antiferromagnetic exchange interaction J and one diagonal second-neighbor interaction J′, interpolating between square-lattice
  (J′=0) and triangular-lattice (J′=J) limits… the disorder-line… where the correlations go from Neel to incommensurate, meets the
  zero temperature axis at J′≈0.7J… the incommensurate phase at larger J′… is a floating phase with power-law decaying
  correlations." → scout's "J′=J IS the project's embedding; disorder line + floating phase" claim **verbatim-accurate**. **VERIFIED.**
- **arXiv:2308.05077** (Begušić, Gray, Chan, Sci. Adv. 10, eadk4321 (2024)): classical methods "simulate these observables orders
  of magnitude faster than the quantum experiment… sandwich bond dimension >16,000,000, achieving an absolute accuracy, without
  extrapolation, in the observables of <0.01… we identify inaccuracies in the experimental extrapolations." → scout's
  classical-frontier claim **verbatim-accurate**. **VERIFIED.**
- **arXiv:2303.08461** (Yang et al., PRX Quantum 4, 030320 (2023)): "study thermalization even with a relatively coarse Trotter
  decomposition… the system prethermalizes in accordance with previous results for Floquet systems. The dynamics closely resemble
  the thermalization of the model underlying the Trotterization up to long times… error mitigation scheme based on measurement and
  rescaling of survival probabilities… two-dimensional XY model." → scout's expected-results anchor **verbatim-accurate**. **VERIFIED.**
- **arXiv:1806.11123** (Heyl, Hauke, Zoller, Sci. Adv. 5, eaau8342 (2019)): "Trotter errors can become independent of system size
  and total simulation time… characterized by a sharp threshold as a function of the Trotter step size… separates a regular region
  with controllable Trotter errors… from a quantum chaotic regime." → scout's Trotter-threshold anchor **verbatim-accurate**. **VERIFIED.**

Prior project verification I rely on (not re-done here): `research/04-gauss-law-citations.md` already VERIFIED 2203.08905
(Gauss-law postselection, local > global, Methods §I.6), 2608.21103 (p* ∼ 5e−5 crossover), Moessner–Sondhi PRB 63 224401, and
all ten draft IDs resolve. The overseer independently re-verified 1706.02601 (per the task statement); my fetch concurs.

**Could NOT independently confirm this session (flagged, not relied upon):** 2608.04290 (the scout's "single most on-target"
source and the lever behind items 01-1/01-4), 2606.15464, 2001.00024, 2007.00668, 2108.02203, 2204.13709, 2510.05222,
2401.11294, 1602.02979, Semeghini Science 374. These were not fetched this session; where a ruling leans on one, I mark it
**[scout-asserted, not re-verified by me]** and route accordingly. 2405.09462 remains [unverified] in the scout's own notes.

---

## 1. The load-bearing physics question: does per-sector ETH survive an *approximate* constraint?

This is the hinge for the whole Q3 thread, so I reason it out explicitly before ruling.

1706.02601 is proved for the **quantum dimer model** — a Hamiltonian (plaquette flip + potential) under which the topological
(winding) sectors are **exactly** conserved. The project's dynamics is the **TFIM**, under which the project has itself derived and
measured that the winding is conserved only **approximately**: `docs/gauss_law_dimers.md §3 identity 5` ([H_QDM, W]=0 exactly, but
[H_TFIM, D_t]≠0), and `§4` measures the leakage out of the initial sector as **P(W≠W₀) ∝ h^2.08–2.09** (stripe / 3-sublattice
starts), i.e. **O((h/|J|)²)**, with the defect density itself ∝ (h/|J|)² (slopes 1.96–2.05).

My assessment [inferred, grounded in the project's own [derived]+[measured] results + 1706.02601 + 2401.11294-as-asserted]:

- **The per-sector *statement* is the correct frame, not the global one.** Over the time window where sector leakage is small
  (≲ (h/|J|)² × t²-ish growth, bounded while h/|J|=0.3), the dynamics is quasi-confined to the initial winding sector, so the
  natural ergodic reference is the within-sector infinite-time average, exactly as 1706.02601 demands for the exact model. A
  *global* infinite-T baseline is reached only via the slow leakage channel and is the wrong first-order comparator. So the scout's
  core recommendation (01 of sweep 02) is physically right **for the near-term window**.
- **But "sector" is not a sharp label under H_TFIM**, so the baseline must be defined with a stated tolerance/time-window, not as a
  hard projector. The honest construction is: (i) MCMC restricted to the initial winding sector gives the leading ergodic target;
  (ii) the measured O((h/|J|)²) leakage sets how long that target is valid and provides a *second*, slow approach toward the global
  value. This is a refinement of the scout's wording, which says "restrict the MCMC to the sector" without noting that the project's
  constraint is only approximate — the very distinction the project is careful about everywhere else. The approximate-constraint →
  anomalously-slow-thermalization mechanism (2401.11294, scout-asserted) is the right citation for the *leakage* channel, but I did
  not re-verify it this session.

**Net:** per-sector baseline = accept the frame; require the "approximate sector / finite window + slow residual leakage"
qualification so the project does not over-promise a sharp conserved quantity it has already shown is only emergent.

---

## 2. Rulings — Sweep 01 (Gauss-law / ice-states), items 1–7

### 01-1. Soften "EC: NO on any platform" → "NO for the passive emergent constraint; conditionally YES only with mid-circuit measurement + feedback."
**RULING: ACCEPT-WITH-MODIFICATION.**
The unconditional "on any platform" phrasing does overreach, and 2405.18504 (VERIFIED) genuinely demonstrates feedback bit-flip
*correction* in a Z₂ LGT. But the scout slightly over-eggs it: 2405.18504 is **1+1d** and uses **ancilla qubits coupled to the
symmetry generators + designed feedback** — it is *not* correction from the bare emergent constraint, and it is not a demonstration
on the project's 2D triangular TFIM. The project's reasoning (distance-1, no syndrome→recovery map, constraint violated by the ideal
dynamics) is correct and must stay as the headline. Only the scope qualifier changes.

*Approved wording* for `docs/gauss_law_dimers.md §5.4` first bullet and the `docs/findings_vs_questions.md` Gauss-table "Error
correction" row, status stays [derived]+[measured] for the NO, new clause tagged [established] for the pointer:
> **Error correction: NO for the passive emergent constraint** — distance 1, no syndrome→recovery map, and the constraint is
> violated by the ideal dynamics itself. *(Separately: with added ancillas coupled to the local generators and mid-circuit
> measurement + feedback, Z₂-LGT bit-flip correction has been demonstrated in 1+1d (arXiv:2405.18504 [established]); that is an
> engineered monitored scheme the project did not model, not correction from the bare emergent constraint.)*

### 01-2. Add active gauge protection (energy-penalty / pseudo-generator) as an explicitly-considered, scoped option.
**RULING: DEFER-TO-KEVIN** (scope/physics-direction), with a note.
Adding a defect-penalty term to `GaussLawConfig` and simulating active protection is a *new scheme* and a new simulation — SCOPE
§3's benchmark list does not include it, and SCOPE §10/§14 route "new scheme design" to a Claude Code hand-off / Kevin decision.
This is not a correctness fix to an existing claim; it is a new lever. The three protection sources (2007.00668 / 2108.02203 /
2204.13709) are **[scout-asserted, not re-verified by me]** and all concern protection against **coherent/unitary** gauge-breaking,
whereas the project's threat model is stochastic Pauli noise + Trotter leakage — so even if adopted, the claim must be narrowly
scoped. Recommend: the overseer may add a **one-sentence "not modelled" note** to `docs/gauss_law_dimers.md §5.5` (limits) listing
active protection as an untested lever (caveated to coherent breaking); building it is Kevin's call.

### 01-3. State the gauge group (Z₂, non-bipartite) explicitly in the ice-states framing.
**RULING: ACCEPT-WITH-MODIFICATION.**
I verified cond-mat/0103396 and the scout's reading needs correction. MSF do **not** say "triangular = Z₂, square = U(1)" as a
clean bipartite/non-bipartite dichotomy. What they say verbatim: the QDM limit of a Z₂ gauge theory develops a *larger* **U(1)**
invariance from the **hardcore dimer constraint**, and *relaxing* that constraint "breaks the U(1) down to Z₂" — the U(1)/Z₂
distinction there is about the **hardcore constraint vs. the generalized gauge theory**, on *all* lattices, with lattice-dependent
*consequences*. The cleaner, defensible statement combining 0103396 + 0007378 (0007378 **[scout-asserted, not re-verified by me]**)
+ Henley (**[scout-asserted, not re-verified]**) is:
> The emergent constraint is a **local Z₂ Gauss law** (defects are Z₂-valued, appear in ± pairs — the project's §3 identity 3 —
> and the conserved winding labels are Z₂/topological). The *triangular* QDM liquid is a Z₂ (toric-code-class) topological phase,
> whereas the *bipartite/square* dimer problem supports a U(1)/Coulomb (height-field) description; the hardcore dimer constraint
> itself carries an enhanced U(1) that the full gauge theory breaks to Z₂ (Moessner–Sondhi–Fradkin, PRB 65, 024504).

Approve adding this (tagged [established] for 0103396, [fetched]/[unverified] for 0007378/Henley until re-read) to
`docs/gauss_law_dimers.md §2` or a new short "gauge group" note. It is a precision gain, not a correction of an error — the project
never claimed U(1). Do **not** let it graduate as a bare "triangular is Z₂, square is U(1)" one-liner; that is an oversimplification
of what 0103396 actually says.

### 01-4. Reconcile the platform line with 2608.04290 (Gauss-law postselection benefit realized on H2).
**RULING: DEFER-TO-KEVIN / PARK** — because I could **not** verify 2608.04290 this session.
2608.04290 is the single load-bearing source for this item and for the scout's headline "most important source," and it is a
**future-dated 2026 ID** (2608 = Aug 2026) that I did not independently open. Per SCOPE §12 / never-trust-unverified, I will not
graduate a change to the platform verdict on an unconfirmed source. The current doc already correctly leaves the platform ranking
[inferred]/[unverified]; that is the honest state. **Flagged scout claim I could not confirm.** If/when the overseer or Kevin
verifies 2608.04290's full text (acceptance rates, which observables, how the one-form syndrome is extracted), the reconciliation
the scout proposes (distinguish *emergent-approximate* vs *engineered one-form syndrome*) is a reasonable framing to add — but as a
[fetched] note, still not overturning the [unverified] H2-worst line. Until then: no edit.

### 01-5. Cite 2606.15464 as independent backing for the "modest, floored, regime-dependent" postselection verdict.
**RULING: ACCEPT-WITH-MODIFICATION (cite as [fetched], do not let it do load-bearing work).**
This only *adds a corroborating citation* to a verdict the project already derived+measured itself, so the risk is low. But I did
not re-verify 2606.15464 (also a 2026 ID), so it must enter tagged **[fetched]**, as supporting context, not as the basis of any
number. Approved: a one-line citation in `docs/gauss_law_dimers.md §5.4` / §5.5 noting that the bias-floor-vs-acceptance-cost
tradeoff the project measured has been formalized as certified finite-shot operating windows (arXiv:2606.15464 [fetched]).
No project number changes.

### 01-6. Use 2510.05222 to sharpen *why* the dimer constraint is weak (reword the "acceptance worsens with size" line).
**RULING: ACCEPT-WITH-MODIFICATION.**
The physics point is sound and sharpens an existing claim without inventing numbers: the project's "postselection acceptance
worsens with size even noiseless" is a property of a **distance-1 constraint with a physics floor**, not a universal law —
genuine topological codes can get *scalable* postselection gains. I did not re-verify 2510.05222 (2026 ID) and will not import its
specific exponent (b≥2, b=3.1 toric). Approved wording for `docs/gauss_law_dimers.md §4`/§5.4 (the size-scaling caveat), with the
source tagged [fetched] and **no number quoted**:
> The acceptance falling with size here is a consequence of the constraint being **distance-1 with a physics floor**, not an
> inherent limit of postselection: in genuine topological (finite-distance) codes, postselection accuracy gains can instead be
> *scalable* with size (arXiv:2510.05222 [fetched]). The dimer manifold is weak specifically because it is not a stabilizer code.

### 01-7. Add Henley 0912.4531 as the canonical ice/Coulomb-phase citation (defects=charges, divergence-free flux, winding=flux sector).
**RULING: ACCEPT-WITH-MODIFICATION (cite as [fetched] pending a full-text read).**
Low-risk citation addition that strengthens the §2 mapping and does not change any result. The scout read it "in full via abstract";
I did not re-verify it this session, so it enters tagged **[fetched]** (upgrade to [established] once the overseer/researcher reads
the review body or confirms the DOI 10.1146/annurev-conmatphys-070909-104138). Approved: add Henley as the canonical review citation
for the "defects behave as effective charges / divergence-free flux / winding = flux sector" correspondence in
`docs/gauss_law_dimers.md §2`. The project's identities are independently [derived], so this is pure attribution support.

---

## 3. Rulings — Sweep 02 (Frustration theory / digital-simulation core), items 1–7

### 02-1. Adopt 1706.02601 as the canonical ETH-in-QDM citation and **define the Q3 ergodic/MCMC baseline per winding sector**.
**RULING: ACCEPT-WITH-MODIFICATION. Highest-impact item.**
VERIFIED verbatim. This is the single most consequential recommendation. The modification is the one derived in §1 above: the
baseline must be **per winding sector *with an explicit finite-time / approximate-sector qualifier***, because under H_TFIM the
sectors leak at the project's own measured O((h/|J|)²) rate (P(W≠W₀) ∝ h^2.08). Approved concrete edits:
- `docs/findings_vs_questions.md` Q3 "Done when" row: change to *"relaxation/observable curves with **per-winding-sector** ergodic
  (MCMC) baselines and uncertainties; the sector-restricted baseline is the leading reference, with the measured O((h/|J|)²) sector
  leakage giving the slow residual approach to the global value."* Cite 1706.02601 [established].
- `docs/findings_vs_questions.md` Q3 "relaxation curves… vs ergodic reference values" row: note the MCMC baseline (still [pending]/
  not built) **must be sector-restricted**; a whole-configuration-space MCMC would manufacture a spurious non-thermalization (the
  scout's G1 — correct).
- SCOPE §2 Q3 wording is Kevin's to change (see §4/Kevin list); the docs change above does not require a SCOPE edit, it refines the
  "done-when" interpretation already recorded in `findings_vs_questions.md`.

**Does the Q3 finding make the current `findings_vs_questions.md` Q3 row WRONG (not just incomplete)?**
**No — not wrong, but its "done-when" is under-specified in a way that could have produced a wrong result.** The row currently says
Q3 is [pending] because the MCMC baseline "is NOT built," and notes the reference takes ergodic values from classical MCMC. That is
factually correct and nothing stated there is false. What is *missing* is the specification that the baseline must be
**sector-restricted**. The danger is latent, not realized: *if* the (unbuilt) MCMC were to sample the whole configuration space, the
quantum dynamics could never reach it and the project would report a spurious "fails to thermalize." So the row is **incomplete and
needs the sector qualifier added before the MCMC is built**, but it is not currently making a false claim. I therefore rule
ACCEPT-WITH-MODIFICATION (add the qualifier), **not** "the row is wrong."

### 02-2. Cite 2303.08461 + 1806.11123 as expected-results theory; add a dt-convergence / Trotter-threshold study to validation.
**RULING: split.**
- **Citing 2303.08461 (PRX Quantum 4, 030320) and 1806.11123 (Sci. Adv. 5, eaau8342): ACCEPT.** Both VERIFIED verbatim. They are
  the correct, canonical license for finite-dt 2nd-order Trotter (local observables faithful below a sharp dt threshold; coarse
  Trotter still prethermalizes tracking the target model). Approved: add both [established] to `research/01-stage1-conventions.md`
  (Trotter section) and to the Q3 context in `docs/findings_vs_questions.md` as the expected-results theory. No numbers imported.
- **Adding a dt-convergence/Trotter-threshold study to the Stage-1/3 validation plan: DEFER-TO-KEVIN.** This is new scope/work (the
  repo currently validates vs ED at fixed small dt). It is a sensible validation and well-supported, but it is a build decision, and
  the *model-specific* threshold for the triangular TFIM has nothing in the literature to check against (scout G3) — that part would
  be a SCOPE §10 Claude Code hand-off. Reviewer recommendation: worth doing; Kevin/overseer decides whether it is in scope now.

### 02-3. Adopt cond-mat/0302105 (phase diagram) + 1602.02979 (clock-order pattern) for any 3-sublattice/clock-order statement.
**RULING: split.**
- **Citing cond-mat/0302105 (PRB 68, 104409): ACCEPT** — VERIFIED verbatim (extended BKT critical phase, 3-sublattice order,
  3d-XY QCP). It is the right phase-diagram anchor for Q2. Approved: add [established] to `research/03-stage3-triangular.md` and the
  Q2 narrative in `docs/findings_vs_questions.md` as the canonical triangular-TFIM phase diagram.
- **1602.02979 clock-order pattern (M, −M/2, −M/2): ACCEPT-AS-[fetched]** — I did not re-verify it this session; enter tagged
  [fetched]. **Important guard:** the project currently measures only *ground-state energy/bond, M_z, ⟨ZZ⟩, defect density* and does
  **not** compute a 3-sublattice/clock order parameter. The citation may be added as context, but **no clock-order claim may be
  graduated as [measured]** until such an observable is actually built. Adding the observable is a scope decision → Kevin (see 02 of
  "Kevin decides"). So: cite yes; claim clock order only if/when measured.

### 02-4. Record 2308.05077 + 2306.14887 + 2308.03082 as the classical frontier; frame the contribution as physics+QEC methodology; optionally run a classical baseline.
**RULING: split.**
- **Recording the classical-frontier caveat (2308.05077 VERIFIED; 2306.14887 / 2308.03082 [fetched]): ACCEPT.** This is a
  skeptical-prior-preserving honesty item squarely in SCOPE's spirit. Approved: add a short "classical frontier" note to
  `docs/findings_vs_questions.md` (Q2/Q3 context or a new caveat line) stating that local observables of Trotterized 2D-Ising
  dynamics at ~50–130 qubits are, so far, classically reachable (2308.05077 [established], Sci. Adv. 10, eadk4321), so the project's
  defensible contribution is **frustration/sector physics + the logical-qubit/QEC methodology**, not beyond-classical dynamics.
- **"Frame the headline contribution as physics+methodology, not quantum advantage": DEFER-TO-KEVIN.** This reframes the project's
  headline claim — a scope/positioning decision, not a correctness fix. The caveat (above) should be recorded regardless; how the
  *headline* is phrased is Kevin's.
- **Running a BP / sparse-Pauli classical baseline: DEFER-TO-KEVIN** (new build, new scope).

### 02-5. Flag 1303.0883: the triangular embedding is the J′=J point of a model with a disorder line + incommensurate floating phase; Q2 ⟨ZZ⟩ contrast may be incommensurate/non-monotonic and finite-size-sensitive.
**RULING: ACCEPT.** VERIFIED verbatim — J′=J is exactly the project's "square + one diagonal" embedding. This is a genuine
interpretation guard for the Q2 ⟨ZZ⟩ comparison and preserves the skeptical prior. Approved: add a caveat to the Q2 write-up in
`docs/findings_vs_questions.md` (the "Q2 comparison" section) and/or `research/03-stage3-triangular.md`:
> The triangular embedding here is the J′=J point of the anisotropic model of arXiv:1303.0883 (PRB 87, 214415 [established]), which
> hosts a Stephenson disorder line (Néel→incommensurate) and, at larger J′, an incommensurate floating phase. The square-vs-
> triangular two-point ⟨ZZ⟩ contrast may therefore be incommensurate / non-monotonic and is finite-size-sensitive at the project's
> small cluster sizes; do not read a clean "frustration monotonically weakens order" story into it.

### 02-6. Note 2401.11294 (inexact constraint ⇒ exp. slow thermalization) + 2506.13856 (dephasing mixes within a sector): predict anomalously slow, sector-bottlenecked relaxation; reframe dephasing as a within-sector equilibration tool.
**RULING: ACCEPT-WITH-MODIFICATION (both as [fetched], not re-verified by me).**
Physically coherent and ties directly to the project's approximate constraint (§1) and its existing dephasing finding. Neither
source was re-verified this session, so both enter tagged [fetched], and the statement must be a *prediction/context* note, not a
[measured] claim. Approved: add to the Q3 context in `docs/findings_vs_questions.md` a note that an *inexact* constraint predicts
anomalously slow / bottlenecked relaxation (2401.11294 [fetched]) and that controlled dephasing can act as a within-sector
equilibration probe rather than only noise (2506.13856 [fetched]) — **as expected-behaviour context, to be tested once the
sector-restricted MCMC and relaxation curves exist**, not as a present result. Cross-reference the existing dephasing verdict in
`docs/gauss_law_dimers.md §5` (which stands).

### 02-7. If the project adds the inhomogeneous-quench / diffusion observable, cite 2405.16975 (ETH↔hydrodynamics) + 1909.01351 (long-range⇒Lévy).
**RULING: DEFER-TO-KEVIN (conditional).** The diffusion/hydrodynamics observable is **not built** (the project is currently
ground-state + constrained-dynamics observables). Adding it to match the reproduction target is a scope decision for Kevin/overseer.
The two citations (both [fetched], not re-verified) are appropriate context **only if** that observable is added; they graduate
nothing on their own. No edit now.

---

## 4. Ranking of accepted/accepted-with-mod items by how much they change the project

1. **02-1 (per-sector Q3 baseline, + approximate-sector qualifier).** Largest. It changes the definition of "done" for Q3 and the
   spec of the not-yet-built MCMC; getting it wrong would manufacture a spurious non-thermalization result. [established] source.
2. **02-4 caveat + 02-5 (classical-frontier honesty + floating-phase guard).** Reshape how Q2/Q3 *results are interpreted and
   claimed*; both preserve the skeptical prior and both rest on VERIFIED sources (2308.05077, 1303.0883).
3. **01-1 (soften EC "any platform").** Corrects an over-reaching headline qualifier on a verdict; the NO itself is unchanged.
   VERIFIED source (2405.18504), mod/scoped.
4. **02-2 citations + 02-3 phase-diagram citation.** Add canonical [established] theory anchors (Trotter threshold / prethermal /
   triangular phase diagram); strengthen but do not change results.
5. **01-3 (state Z₂ gauge group, corrected framing).** Precision gain in the ice-states §2; not a correction of an error.
6. **01-6 (reword size-scaling caveat), 01-5 / 01-7 ([fetched] corroborating citations), 02-6 ([fetched] context).** Smallest;
   sharpen wording / add supporting citations without importing numbers.

---

## 5. Consolidated APPLY LIST (overseer may apply; wording approved above)

Each edit keeps the never-invent-numbers rule; imported citations carry the tag shown.

| # | File | Change | Source tag |
|---|---|---|---|
| A1 | `docs/findings_vs_questions.md` Q3 rows | Baseline is **per winding sector** + approximate-sector/finite-window qualifier + O((h/\|J\|)²) slow residual; MCMC (still [pending]) must be sector-restricted | 1706.02601 [established] |
| A2 | `docs/findings_vs_questions.md` Q2 "comparison" §; `research/03-stage3-triangular.md` | Floating-phase / disorder-line guard: J′=J point; ⟨ZZ⟩ may be incommensurate/non-monotonic, finite-size-sensitive | 1303.0883 [established] |
| A3 | `docs/findings_vs_questions.md` Q2/Q3 context | Classical-frontier caveat: local 2D-Ising Trotter observables classically reachable ~50–130 qubits; contribution = physics/sector + QEC methodology | 2308.05077 [established]; 2306.14887/2308.03082 [fetched] |
| A4 | `docs/gauss_law_dimers.md §5.4` + `findings_vs_questions.md` Gauss "Error correction" row | Qualify "EC: NO" → **NO for the passive emergent constraint**; add the monitored-feedback (1+1d, ancilla+feedback) pointer as a distinct engineered scheme not modelled | 2405.18504 [established] |
| A5 | `research/01-stage1-conventions.md` (Trotter) + `findings_vs_questions.md` Q3 context | Cite expected-results theory: sharp dt threshold for local observables; coarse Trotter prethermalizes tracking target model | 1806.11123 [established]; 2303.08461 [established] |
| A6 | `research/03-stage3-triangular.md` + `findings_vs_questions.md` Q2 | Cite canonical triangular-TFIM phase diagram (extended BKT critical phase, 3-sublattice order, 3d-XY QCP) | cond-mat/0302105 [established]; 1602.02979 [fetched] (no clock-order *claim* until measured) |
| A7 | `docs/gauss_law_dimers.md §2` (or new short note) | State the emergent constraint is a **local Z₂ Gauss law** (Z₂ defects, ± pairs, Z₂/topological winding); triangular QDM liquid Z₂, bipartite/square U(1)/Coulomb; **use MSF's actual framing** (hardcore constraint carries U(1), full gauge theory breaks it to Z₂) — NOT a bare "triangular=Z₂, square=U(1)" | cond-mat/0103396 [established]; 0007378 / Henley 0912.4531 [fetched] |
| A8 | `docs/gauss_law_dimers.md §4`/§5.4 | Reword size-scaling caveat: acceptance-worsens-with-size is a distance-1/physics-floor property, not an inherent limit; genuine topological codes get scalable gains (no number) | 2510.05222 [fetched] |
| A9 | `docs/gauss_law_dimers.md §5.4`/§5.5 | One-line corroboration: bias-floor-vs-acceptance-cost tradeoff formalized as certified finite-shot operating windows | 2606.15464 [fetched] |
| A10 | `docs/gauss_law_dimers.md §2` | Add Henley as canonical ice/Coulomb-phase review citation for defects-as-charges / divergence-free-flux / winding=flux-sector | Henley 0912.4531 [fetched] |
| A11 | `docs/findings_vs_questions.md` Q3 context | Expected-behaviour note (NOT a result): inexact constraint ⇒ anomalously slow/bottlenecked relaxation; dephasing as within-sector equilibration probe; to be tested once sector MCMC + curves exist | 2401.11294 [fetched]; 2506.13856 [fetched] |
| A12 | `docs/gauss_law_dimers.md §5.5` (limits) | One-sentence "not modelled" note: active gauge protection (energy-penalty/pseudo-generator) is an untested lever, caveated to *coherent* gauge-breaking | 2007.00668/2108.02203/2204.13709 [fetched] — note only; *building it* is a Kevin decision (see K-list) |

**[established] vs [fetched] in the apply list:** only A1, A2, A3 (2308.05077 part), A4, A5, A6 (0302105 part), A7 (0103396 part)
rest on sources I verified verbatim this session. Everything tagged [fetched] above is a scout assertion I did **not** re-verify
and must enter the docs with the [fetched] tag; none of them import a number.

---

## 6. KEVIN DECIDES (scope / physics-direction, not correctness)

- **K1 (01-2 / A12 build):** Is **active gauge protection** (add a defect-penalty term to `GaussLawConfig` and simulate leakage
  suppression) in scope for the Gauss thread? It is the largest unexplored lever but a *new scheme* (SCOPE §10 → likely a Claude
  Code hand-off). The one-line "not modelled" note (A12) can go in regardless; building it needs Kevin.
- **K2 (02-2):** Add a **dt-convergence / Trotter-threshold study** to Stage-1/3 validation? Well-supported; the model-specific
  triangular-TFIM threshold has nothing to check against (would be a Claude Code derivation).
- **K3 (02-3 / A6):** Add a **3-sublattice / clock-order order parameter** (M, −M/2, −M/2) observable to connect to the phase
  diagram, or keep the project purely dynamical? No clock-order claim can graduate until this is built.
- **K4 (02-4):** Reframe the **headline contribution** as physics/sector insight + logical-qubit/QEC methodology (given the classical
  frontier), and/or run a **BP/sparse-Pauli classical baseline** to bound the project's own observables? The caveat (A3) stands
  regardless; the headline framing and the extra build are Kevin's.
- **K5 (02-7):** Add the **inhomogeneous-quench / diffusion (hydrodynamics)** observable to match the reproduction target? If yes,
  2405.16975 / 1909.01351 become relevant context.
- **K6 (01-3 / A7):** Does the project want to **commit to the Z₂ (vs U(1)) characterization** in print, or keep "Gauss law"
  generic? (Correctness-neutral labeling choice; A7 is approved either way as the accurate statement if committed.)

---

## 7. REJECTED / PARKED

- **PARKED — 01-4 (reconcile platform line with 2608.04290):** I could **not** independently verify 2608.04290 (future-dated 2026
  ID, not opened this session). It is the sole basis for the item and for the scout's "most important source." Per SCOPE §12, no
  platform-verdict change graduates on an unconfirmed source. **No edit.** Reopen if the overseer/Kevin verifies the full text; even
  then it enters as a [fetched] framing note, not an overturn of the [unverified] "H2-worst" line.
- **PARKED — any upgrade of [fetched] sources to [established]:** 2001.00024, 2606.15464, 2007.00668, 2108.02203, 2204.13709,
  2510.05222, 2401.11294, 1602.02979, 0007378, Henley 0912.4531, 2506.13856, 2306.14887, 2308.03082, 2608.04290, Semeghini Science
  374 were **not re-verified by me this session**. They may be cited only at [fetched]/[unverified] until read in full.
- **No item REJECTED outright on correctness.** The closest to a rejection is the scout's **01-3 framing** ("triangular is Z₂,
  square is U(1)") — rejected *as worded* (it misstates what cond-mat/0103396 says) and replaced with the corrected A7 statement.
- **Scout claims I could NOT confirm (flagged):** 2608.04290's on-H2 postselection benefit (01-1/01-4/01-7 lean on it as context);
  2405.09462 (scout's own [unverified]); the specific exponents of 2510.05222 (not imported); 2401.11294's exponential-slowness
  (imported only as [fetched] context). None of these carry a graduated number.

---

## 8. Verdict

**Per item:** 01-1 ACCEPT-WITH-MOD · 01-2 DEFER-TO-KEVIN · 01-3 ACCEPT-WITH-MOD (framing corrected) · 01-4 PARK (unverified source)
· 01-5 ACCEPT-WITH-MOD ([fetched]) · 01-6 ACCEPT-WITH-MOD · 01-7 ACCEPT-WITH-MOD ([fetched]) · 02-1 ACCEPT-WITH-MOD (**highest
impact**) · 02-2 ACCEPT (citations) + DEFER (dt study) · 02-3 ACCEPT (0302105) + conditional (clock-order observable) · 02-4 ACCEPT
(caveat) + DEFER (headline/baseline build) · 02-5 ACCEPT · 02-6 ACCEPT-WITH-MOD ([fetched] context) · 02-7 DEFER-TO-KEVIN.

**Overall: APPROVE WITH CONDITIONS.** The scout's load-bearing sources that I could reach (1706.02601, 2405.18504, cond-mat/0302105,
cond-mat/0103396, 1303.0883, 2308.05077, 2303.08461, 1806.11123) are all accurately represented. The highest-value recommendation
(02-1, per-sector Q3 baseline) is correct and should be applied, with the project's own-measured approximate-constraint caveat
attached. Conditions: (i) the Q3 baseline change must carry the "approximate sector / finite window + O((h/|J|)²) residual leakage"
qualifier, not a hard-conserved-sector claim; (ii) nothing resting on an unverified 2026-dated source (notably 2608.04290) graduates
— 01-4 is parked; (iii) all [fetched] citations enter the docs with the [fetched] tag and import no numbers; (iv) new observables /
schemes / headline reframes (active protection, dt-threshold study, clock-order parameter, diffusion observable, quantum-advantage
framing) are Kevin/overseer scope decisions, not reviewer-approved edits.

**On the specific question asked — is the current `findings_vs_questions.md` Q3 row WRONG?** No. It is **incomplete** (missing the
sector-restriction qualifier) in a way that could have led to a wrong result once the MCMC is built, but as written it states
nothing false. Fix = add the qualifier (A1), not retract the row.

**Open items for the overseer:** apply A1–A11 as worded (A12 as a note only); route K1–K6 to Kevin; verify 2608.04290 before
reopening 01-4; upgrade [fetched] citations to [established] only after full-text reads.
