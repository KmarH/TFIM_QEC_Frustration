# Scout Sweep 02 — Frustration theory + Digital simulation core & expected results (WIDE)

**Scout:** qc-scout (sweep 2) · **Date:** 2026-10-06 · **Scope:** the SCIENTIFIC CORE —
(A) the frustrated transverse-field Ising model (TFIM) on the triangular lattice (SCOPE §2 Q2, §4 stage 3), and
(B) the digital-quantum-simulation engine and its EXPECTED RESULTS (SCOPE §2 Q3 thermalization + the reproduction target).
**Mandate:** discovery BEYOND the project's seed sources, hunting corroborating AND contradicting/reframing work.
Notes only — this file changes no project claim and writes no project code. Every source is status-tagged.

Status vocabulary (carried from SCOPE/research and sweep 1):
**[established]** = primary source read in full here (arXiv abstract page read verbatim, journal ref confirmed, and/or body quoted);
**[fetched]** = seen via an automated summary/snippet, not hand-checked line by line;
**[inferred]** = my reasoning; **[unverified]** = only a snippet/secondhand seen.
No ID/DOI/number was invented. Every arXiv ID below resolved on its arXiv abstract page unless flagged. Future-dated IDs are reported as-found.

---

## 0. What the project already uses (the baseline I am extending)

From `research/01-stage1-conventions.md`, `research/03-stage3-triangular.md`, `docs/findings_vs_questions.md`:
- **Model:** `H = -J Σ_<ij> Z_iZ_j − h Σ_i X_i`; square + "square-grid + one-diagonal" triangular embedding (coordination 6, 3N bonds on torus).
- **Engine:** 2nd-order Suzuki–Trotter (Strang), statevector ≤~24 spins, sparse ED ≤~22–24, Stim unbounded.
- **Reproduction target:** Haghshenas et al. 2503.20870 (Nat. 653, 56 (2026)) — digitized Ising dynamics on H2, square baseline + triangular-PBC frustrated extension; thermalization / relaxation of an inhomogeneous state; emergent hydrodynamics / diffusion; the paper's own line "thermalization consistent with emergent gauge and topological constraints resulting from lattice frustration."
- **Frustration observables already built:** dimer density, defect D_t, charge, winding W_x/W_y, flippable count, H_QDM, dimer C_r, winding FCS; defect density ∝ (h/|J|)² measured (slopes 1.96–1.98); sectors (3×4→3, 3×3→1).
- **Thermalization (Q3): the MCMC ergodic baseline is NOT built** — flagged [pending]. The reference draws its ergodic reference values from classical Markov-chain Monte Carlo.
- **Already-held frustration anchors (sweep 1 / seeds):** Moessner–Sondhi–Chandra "Ising models of quantum frustration" (cond-mat/0011250 = PRB 63, 224401 — a project seed); Moessner–Sondhi triangular QDM RVB (cond-mat/0007378, PRL 86,1881); Moessner–Sondhi–Fradkin Z₂-gauge mapping (cond-mat/0103396, PRB 65,024504); Henley Coulomb-phase review (0912.4531); emergent-RK 2106.05518; string picture cond-mat/0409776.

Seeds mined for terms **then left** this sweep: 2503.20870, 2509.25326, 2602.22211, 2211.06703, cond-mat/0011250
(Moessner–Sondhi PRB 63 224401), 1705.02329, and the draft's IDs.

---

## 1. Search strategy actually used

Term-mining the seeds gave two concept trees. Each branch was searched independently; community in brackets.

**(A) Frustration theory tree** [condensed matter / stat-mech]:
"triangular transverse-field Ising antiferromagnet", "order by disorder", "three-sublattice / clock order",
"quantum phase diagram vs transverse field", "3d XY universality", "Kosterlitz–Thouless / floating phase",
"disorder line (Stephenson)", "quantum dimer model triangular", "ETH quantum dimer", "Hilbert-space fragmentation dimer winding".
Citation hops: forward from Moessner–Sondhi(–Chandra) → Isakov–Moessner finite-T phase diagram → anisotropic-triangular floating phase → long-range-TFIM QMC (clock order) → pCUT order-by-disorder → ETH-in-QDM → inexact-constraint HSF.

**(B) Digital-simulation / expected-results tree** [quant-ph / AMO / stat-mech]:
"Trotter error threshold", "digital quantum simulation quantum chaos", "Floquet prethermalization heating time",
"prethermal plateau", "digital simulation of prethermalization near-term", "emergent hydrodynamics diffusion spin",
"ETH 2D Ising", "classical simulation kicked Ising utility", "sparse Pauli dynamics", "tensor network belief propagation", "PEPO".
Citation hops: from the kicked-top Trotter-threshold line (Heyl–Hauke–Zoller → kicked-top chaos → universal Trotterisation)
and from the IBM-utility classical-frontier cluster (Begušić–Chan ↔ Tindall et al. ↔ PEPO).

Directions used: forward+backward citations, author trails (Moessner/Sondhi; Heyl/Hauke/Zoller; Begušić/Chan),
and cross-community bridges (dimer ETH ↔ generic ETH ↔ digital-simulation prethermalization).

---

## 2. TARGET A — Frustration theory: three buckets

### 2A. CORROBORATING / canonical (establish the theory the project rests on)

- **arXiv:cond-mat/0302105** — Isakov & Moessner, "Interplay of quantum and thermal fluctuations in a frustrated magnet,"
  **Phys. Rev. B 68, 104409 (2003)**. **[established — abstract read in full, journal ref confirmed].**
  *What it says:* QMC phase diagram of the triangular-lattice TFIM: an **extended critical (BKT) phase** separating the paramagnet
  from a **quantum-fluctuation-driven three-sublattice ordered phase**, bounded by **two Kosterlitz–Thouless transitions**;
  the **zero-T quantum phase transition is 3d-XY universality class**. *Why it matters:* this is the **canonical quantitative
  phase-diagram anchor** for the project's main lattice — it fixes what "order" and "critical fluctuations" mean at finite T and
  pins the QCP universality. The project currently cites only the Moessner–Sondhi(–Chandra) mapping papers; this is the
  phase-diagram companion and should be the reference for any clock/3-sublattice-order statement.

- **arXiv:cond-mat/9910499** — Moessner, Sondhi, Chandra, "Two-dimensional periodic frustrated Ising models in a transverse field,"
  (PRL 84, 4457 (2000)). **[fetched — abstract seen].** *What it says:* the short-paper precursor to the project's seed
  PRB 63, 224401; interplay of classical degeneracy and quantum dynamics at T=0 across triangular/kagome/etc. *Why it matters:*
  the primary short-form statement that the triangular case orders by quantum order-by-disorder while kagome does not — the
  canonical origin of "order by disorder" for this exact family. (Pairs with the project's seed cond-mat/0011250.)

- **arXiv:1602.02979** — Humeniuk, "Quantum Monte Carlo Study of Long-Range Transverse-Field Ising Models on the Triangular Lattice,"
  **Phys. Rev. B 93, 104412 (2016)**. **[established — abstract read in full, journal ref confirmed].**
  *What it says:* SSE-QMC; for AFM interactions the transverse field **stabilizes a clock-ordered phase with sublattice
  magnetization (M, −M/2, −M/2), unsaturated M<1, via order-by-disorder**; a semiquantitative α-dependent phase diagram
  interpolating NN↔infinite-range. *Why it matters:* gives the **explicit clock-order pattern and magnitude** the project's
  3-sublattice observables should see, and connects to trapped-ion (Penning-trap) long-range realizations — relevant because
  H2's native interactions are not strictly NN.

### 2B. CONTRADICTING / REFRAMING (complicate the "simple frustration" picture)

- **arXiv:1706.02601** — Lan & Powell, "Eigenstate thermalization hypothesis in quantum dimer models,"
  **Phys. Rev. B 96, 115140 (2017)**. **[established — abstract read in full, journal ref confirmed].**
  *What it says:* ED on **square and triangular** QDMs: because local plaquette-flip dynamics is non-ergodic, Hilbert space
  **splits into topological-invariant sectors**; **ETH holds clearly only when each topological sector is treated separately**,
  and only for moderate potential/kinetic ratios; treating the whole spectrum, **ETH breaks down on the square lattice and
  apparently on the triangular lattice too.** *Why it reframes:* this is the single most important reframing for Q3 — it says the
  project's thermalization question is **sector-conditional**: the right ergodic baseline is **per winding/topological sector**,
  not a global infinite-T value. The project's winding-FCS and sector observables are exactly the right tools, but the
  "approach to ergodic MCMC values" claim must be qualified **within a sector**. Directly on-target and partly contradicts a naive
  global-thermalization expectation.

- **arXiv:2401.11294** — Han, Chen, Lake, "Exponentially slow thermalization and the robustness of Hilbert space fragmentation,"
  (quant-ph; v2 2 Apr 2026). **[established — abstract read in full].** *What it says:* when fragmentation constraints are
  **not exact** (a chain with pair-flip constraints coupled to an ergodicity-restoring bath), thermalization time is
  **exponentially long** in system size, from strong bottlenecks in configuration space. *Why it reframes:* the project's
  emergent Gauss law / dimer constraint is **approximate** (violated at O((h/J)²) by the ideal dynamics and by noise). This paper
  is the general statement that an *inexact* constraint still produces **anomalously slow, prethermal-like relaxation** rather than
  prompt thermalization — a concrete, citable mechanism for what the triangular quench should show *differently* from the square
  case, and a caution that "approach to ergodic values" may be exponentially slow, not merely delayed.

- **arXiv:1303.0883** — "Disorder Line and Incommensurate Floating Phases in the Quantum Ising Model on an Anisotropic Triangular
  Lattice," **Phys. Rev. B 87, 214415 (2013)**. **[fetched — abstract + APS accepted-version snippet].**
  *What it says:* interpolates square↔triangular via one diagonal second-neighbour coupling J′; a **Stephenson disorder line**
  (Néel→incommensurate correlations) meets the T=0 axis near J′≈0.7J at B_x=J; the incommensurate large-J′ regime is a
  **floating phase with power-law correlations**; connects to Isakov–Moessner at J′=J. *Why it reframes:* the project's triangular
  geometry **is literally the "square + one diagonal" J′=J point** of this model. This paper warns that the square→triangular
  interpolation passes through a **disorder line and an incommensurate/floating regime** — the two-point ⟨ZZ⟩ comparison the project
  runs (square vs triangular) can show **incommensurate, non-monotonic correlations**, not a clean "frustration weakens order"
  story. Important interpretation guard for Q2.

### 2C. ADJACENT / METHOD

- **arXiv:2402.10584** — Koziol, Mühlhauser, Schmidt, "Order-by-disorder and long-range interactions in the afTFIM on the
  triangular lattice — a perturbative point of view," (cond-mat.str-el, 2024). **[established — abstract read in full].**
  *What it says:* pCUT effective model for the degenerate GS manifold; a **level crossing between a plain stripe phase (small h)
  and the clock-ordered phase (intermediate h)** at h≈0.129 (α=6, N=36, order-3 PT). *Why it matters:* a modern perturbative map of
  the low-field phase structure; a method cross-check for small-h behaviour and a pointer to the stripe-vs-clock competition the
  project could see in its field scans.
- **arXiv:1603.06473** — "Singular ferromagnetic susceptibility of the transverse-field Ising antiferromagnet on the triangular
  lattice," (cond-mat). **[fetched — abstract seen].** Order-by-disorder (Moessner–Sondhi 2001) induces three-sublattice order;
  singular χ_FM signatures. Adjacent susceptibility probe.
- **arXiv:1207.1657** — "Finite-temperature phase transitions in the quantum fully frustrated Ising models," (cond-mat).
  **[fetched — abstract seen].** Finite-T transitions where degeneracy + fluctuations compete; broader finite-T context for Q3.
- **arXiv:1310.3468** — "Reentrant Berezinskii–Kosterlitz–Thouless Transition in a Triangular Ising Thin Film," (cond-mat).
  **[fetched — abstract seen].** Derives an effective dimer theory for the low-T physics and maps the classical film to the
  single-layer quantum Ising model — a method bridge between the classical ice ensemble and the quantum problem.
- **arXiv:cond-mat/0409776** — "String Picture of a Frustrated Quantum Magnet and Dimer Model." **[fetched — already in INDEX
  from sweep 1]**; listed here for the Target-A thread (TIAF↔non-crossing-string↔dimer mapping).

---

## 3. TARGET B — Digital-simulation core & expected results: three buckets

### 3B.1 CORROBORATING / canonical (the engine's error theory and the expected-results theory)

- **arXiv:1806.11123** — Heyl, Hauke, Zoller, "Quantum localization bounds Trotter errors in digital quantum simulation,"
  **Sci. Adv. 5, eaau8342 (2019)**. **[established — abstract read in full, journal ref confirmed].**
  *What it says:* for **local observables**, Trotter error is bounded by a many-body-localization-in-Floquet-space mechanism and
  can be **independent of system size and total time** below a **sharp threshold in the Trotter step dt**; above it, dynamics is
  quantum-chaotic and errors proliferate. *Why it matters:* this is the **theoretical license for the project's 2nd-order Trotter
  at finite dt** — it says local observables (magnetization, correlators, defect density) stay faithful below a step threshold even
  though the global wavefunction fidelity decays. It also defines the *failure mode* to watch for (chaotic proliferation) and
  motivates a **dt-convergence study** as a first-class validation. Canonical and directly actionable.

- **arXiv:2303.08461** — Yang, Christianen, Coll-Vinent, Smelyanskiy, Bañuls, O'Brien, Wild, Cirac, "Simulating prethermalization
  using near-term quantum computers," **PRX Quantum 4, 030320 (2023)**. **[established — abstract read in full, journal ref confirmed].**
  *What it says:* a **coarse** Trotter decomposition (step too large for a rigorous Trotter-error bound) still **prethermalizes in
  accordance with Floquet results**, and the digital dynamics **closely resemble the thermalization of the underlying model up to
  long times**; demonstrated on the **2D XY model** with realistic superconducting noise; adds a **survival-probability
  measurement-and-rescaling error-mitigation** scheme. *Why it matters:* this is the **single best "expected results" anchor** for
  the project — it says what the simulation *should* show (a prethermal plateau tracking the target model, then slow heating), even
  with the coarse steps H2 budgets allow, and offers a concrete error-mitigation route distinct from the project's symmetry/
  postselection thread.

- **arXiv:1812.05876** — Sieberer, Olsacher, Elben, Heyl, Hauke, Haake, Zoller, "Digital Quantum Simulation, Trotter Errors, and
  Quantum Chaos of the Kicked Top," (npj Quantum Information 5, 78 (2019)). **[fetched — abstract + body snippet; journal ref
  unverified here].** *What it says:* regular kicked-top dynamics ⇒ Trotterization converges; **chaos above a sharp dt threshold ⇒
  proliferation of Trotter errors**, with Floquet-operator spectral statistics matching random matrix theory. *Why it matters:*
  the mechanistic companion to 1806.11123; gives the chaos/RMT diagnostic for the breakdown of a digital simulation.

- **arXiv:2110.11113** — "Quantum Chaos and Universal Trotterisation Behaviours in Digital Quantum Simulations,"
  (Hauke, Heyl, Zoller et al.; v5). **[fetched — abstract seen].** *What it says:* across several models a **shared Trotterisation
  threshold** governs performance; an onset of quantum chaos directly induced by digitisation errors causes the breakdown.
  *Why it matters:* generalises the threshold picture; supports stating a **model-independent dt-threshold caveat**.

### 3B.2 CONTRADICTING / REFRAMING (what sets "hard", and when the digital result is not an achievement)

- **arXiv:2308.05077** — Begušić, Gray, Chan, "Fast and converged classical simulations of evidence for the utility of quantum
  computing before fault tolerance," **Sci. Adv. 10, eadk4321 (2024)**. **[established — abstract read in full, journal ref confirmed].**
  *What it says:* the 127-qubit kicked-Ising "quantum utility" observables are reproduced **orders of magnitude faster and more
  accurately** on classical hardware via **sparse Pauli dynamics + tensor networks** (effective sandwich bond dimension >1.6×10⁷,
  absolute accuracy <0.01 without extrapolation); identifies inaccuracies in the experiment's extrapolation. *Why it reframes:*
  this is the **classical frontier that sets what is "hard."** For the project it is a direct warning: **local observables of
  Trotterized 2D Ising dynamics on ~50–130 qubits are, so far, classically reachable.** The project's scientific contribution
  must therefore be framed as *physics insight (frustration/sector structure) and the logical-vs-physical/QEC methodology*, not
  "beyond-classical dynamics." Challenges any implicit quantum-advantage framing of the reproduction.

- **arXiv:2306.14887** — Tindall, Fishman, Stoudenmire, Sels, "Efficient tensor network simulation of IBM's Eagle kicked Ising
  experiment," (PRX Quantum 5, 010308 (2024)). **[fetched — abstract + body snippet; journal ref unverified here].**
  *What it says:* a **lattice-geometry tensor network contracted by belief propagation** classically beats the 127-qubit processor
  in accuracy/precision. *Why it reframes:* second independent demonstration that the kicked-Ising-utility regime is classically
  tractable; **belief-propagation TN is a cheap, strong classical baseline the project could run itself** to bound its own
  observables and to state honestly where (if anywhere) the triangular-frustrated case is harder.

- **arXiv:2308.03082** — "Simulation of IBM's kicked Ising experiment with Projected Entangled Pair Operator," (PEPO, Heisenberg
  picture). **[fetched — abstract seen].** Third classical route (PEPO) reproducing the same experiment. *Why it reframes:* adds a
  2D-native tensor-operator method; relevant because the project's **triangular 2D geometry** is exactly where PEPS/PEPO methods are
  the natural classical competitor to beat or benchmark against.

### 3B.3 ADJACENT / METHOD

- **arXiv:2306.16716** — "Prethermal stability of eigenstates under high frequency Floquet driving." **[fetched — abstract seen].**
  Rigorous-flavoured statement of exponentially-slow heating under high-frequency drive; underpins the "prethermal plateau then
  slow heating" expectation and the heating-timescale ∼ exp(const·ω) scaling.
- **arXiv:2212.00041** — "Quantum and classical Floquet prethermalization." **[fetched — abstract seen].** Review-style framing
  that prethermalization survives into the classical limit; context for the heating-time concept the project's long-time runs test.
- **arXiv:2405.16975** — "Hydrodynamics and the eigenstate thermalization hypothesis." **[fetched — abstract read].**
  Links off-diagonal ETH at small energy difference to **diffusive/super-diffusive transport** via local conservation laws;
  numerically on non-integrable spin-1 Ising models. *Why it matters:* the modern bridge between ETH and the **emergent
  hydrodynamics/diffusion** the reproduction target reports — the theory for extracting a diffusion constant from relaxation curves.
- **arXiv:1909.01351** — "Non-local emergent hydrodynamics in a long-range quantum spin system," (PRX 10, 011042 (2020)).
  **[fetched — abstract read].** Long-range couplings replace plain diffusion with **Lévy-flight / anomalous transport**; relevant
  because H2's interactions are not strictly NN, so the expected hydrodynamic exponent may deviate from pure diffusion.
- **arXiv:1902.01859** — "Emergent hydrodynamics in non-equilibrium quantum systems" (DMT; PRL 122, 250602 (2019)).
  **[fetched — abstract read].** Density-matrix-truncation method that extracts energy diffusion coefficients from large spin
  chains; a **classical method baseline** for the diffusion observable and another entry in the "what's hard" ledger.
- **arXiv:2506.13856** — "Probing Hilbert space fragmentation using controlled dephasing." **[fetched — abstract read in full].**
  Shows that **added dephasing mixes within a single Krylov sector** so simple observables (sublattice imbalance) reveal the
  sector's average; imbalance dips to a sector-characteristic minimum then returns to zero. *Why it matters:* directly relevant to
  the project's **dephasing analysis + winding/sector observables** — reframes dephasing not only as noise but as a *tool* that
  equilibrates within a sector; a concrete protocol the triangular dimer data could emulate.

**Future-dated / implausible IDs seen while searching (reported as-found, NOT used as evidence):**
- **arXiv:2604.13781** ("On Exponentially Long Prethermalization Timescales in Isolated Quantum Systems," v2) — ID is 2026-04;
  reported as-found, not relied upon.
- **arXiv:2604.12907** ("Hilbert Space Fragmentation from Generalized Symmetries") — ID is 2026-04; reported as-found.
- **arXiv:2607.01323** ("Noisy quantum circuit simulation with the tensor jump method") — ID is 2026-07; reported as-found.
- **arXiv:2408.10079** (Floquet-circuit error-mitigation on 38/116 qubits reaching early prethermalization) — plausible 2024 ID,
  abstract not read in full; **[unverified]**, listed for follow-up.
These are consistent with the SCOPE §11 note that the draft/environment contains 2026-relative IDs; I did not alter them.

---

## 4. EXPECTED RESULTS — what theory predicts the simulation should produce, and which project observable tests it

This subsection synthesises the above into testable predictions. Status of each *prediction* is [inferred] from the cited
[established]/[fetched] sources unless noted; the project must confirm against the reproduction target's own numbers (not extracted).

| # | Theory prediction (and source) | Project observable that tests it | Expected signature |
|---|---|---|---|
| E1 | **Prethermal plateau then slow heating** under coarse 2nd-order Trotter (2303.08461 [established]; 2306.16716) | `src/trotter.py:evolve` relaxation curves of local M_z / staggered M / energy vs Trotter time, several dt | observable relaxes fast to a quasi-stationary plateau tracking the *target-Hamiltonian* thermal value, then drifts toward infinite-T on a much longer, dt-dependent timescale |
| E2 | **Sharp Trotter-step threshold**: below it local observables are faithful & size/time-independent; above it chaotic proliferation (1806.11123 [established]; 1812.05876; 2110.11113) | dt-convergence study of the same observables; compare dt against a threshold | curves collapse across dt (and sizes) below threshold; qualitative breakdown + RMT-like spectral statistics above |
| E3 | **Ergodic/thermal value is per-sector, not global** (1706.02601 [established]) | winding W_x/W_y, winding FCS, sector-resolved correlators; MCMC baseline **restricted to the initial winding sector** | relaxation approaches the *within-sector* ergodic value; a *global* infinite-T baseline will be systematically missed on the frustrated lattice |
| E4 | **Frustrated lattice relaxes anomalously slowly / sector-constrained** vs square, because the (approximate) dimer constraint fragments configuration space (2401.11294 [established]; 1706.02601) | triangular-vs-square relaxation of matched observables; defect density D_t(t); flippable-count dynamics | triangular curves show slower, bottlenecked relaxation and residual memory of the initial sector relative to square; defect density grows then saturates near the (h/|J|)² scale |
| E5 | **Clock / three-sublattice order at intermediate h; 3d-XY QCP; BKT-bounded critical phase at finite T** (cond-mat/0302105 [established]; 1602.02979 [established]; 2402.10584) | 3-sublattice order parameter / sublattice magnetization (M,−M/2,−M/2); field scan of ground-state observables | an intermediate-field ordered window with unsaturated M<1; order-by-disorder, not a simple monotone melting |
| E6 | **Emergent hydrodynamics / diffusion** of the conserved density after a quench (2405.16975; 1909.01351; 1902.01859; the reproduction target) | spatially-resolved relaxation / spreading of an inhomogeneous initial M_z profile; extract a diffusion constant | diffusive (or, with H2's longer-range couplings, possibly super-diffusive/Lévy) spreading of the density profile |
| E7 | **The dynamics are (currently) classically reachable for local observables** (2308.05077 [established]; 2306.14887; 2308.03082) | run belief-propagation / sparse-Pauli / PEPO baselines alongside the project's own sims | classical baselines should match the project's local observables to <~0.01; "advantage" is in *physics/method*, not raw dynamics |

**Net expected-results statement (the one-paragraph version for the overseer):** the project's digital TFIM quench on H2 tooling
should, below a Trotter-step threshold (E2), show a **prethermal plateau tracking the target Hamiltonian's thermal values and then
slow heating** (E1); on the **triangular** lattice this relaxation should be **sector-constrained and anomalously slow** relative to
square, with the correct ergodic reference being the **within-winding-sector** value, not a global infinite-T value (E3,E4); the
ground-state/field-scan side should show **order-by-disorder three-sublattice (clock) order at intermediate field with a 3d-XY QCP**
(E5); the inhomogeneous-quench side should show **emergent diffusion/hydrodynamics** (E6). All of this is, for local observables,
**within reach of strong classical methods today** (E7) — so the project's defensible contribution is the frustration/sector physics
and the logical-qubit/QEC methodology, not beyond-classical dynamics.

---

## 5. Gaps and conflicts

- **G1 (conflict, important):** The project's Q3 "done when" asks for relaxation curves vs **ergodic MCMC** values. 1706.02601
  [established] says ETH/ergodicity on the dimer manifold holds **only per topological sector**. These conflict unless the MCMC
  baseline is **sector-restricted**. If the project's MCMC (not yet built) samples the whole configuration space, it will produce
  a baseline the quantum dynamics *cannot* reach, manufacturing a spurious "non-thermalization." **The ergodic baseline must be
  defined per winding sector.**
- **G2 (conflict of framing):** The reproduction target and the project treat the Trotterized dynamics as the scientific object;
  2308.05077 [established] shows the analogous kicked-Ising regime is classically cheap. The literature does **not** settle whether
  the *triangular-frustrated, logical-qubit* variant is harder — a genuine open question the project could partially answer by
  running the BP/sparse-Pauli baselines itself.
- **G3 (gap):** No source read here fixes the **heating timescale for 2nd-order Trotter of the specific triangular TFIM** — the
  Floquet-prethermalization timescale ∼exp(const·ω) (2306.16716) is generic; the model-specific prefactor/threshold is unknown and
  would need the project's own dt-scan (E2) or a Claude Code derivation.
- **G4 (gap):** The square→triangular interpolation passes through a **disorder line / incommensurate floating regime** (1303.0883).
  Whether the project's exact "square + one diagonal" torus sizes sit in a commensurate or incommensurate correlation regime is not
  settled by the literature at the project's small sizes; the two-point ⟨ZZ⟩ comparison may be finite-size-dominated.
- **G5 (gap):** The reproduction target's **exact initial states, dt, and diffusion-constant extraction** remain unextracted
  (consistent with `research/*` [unverified] flags). The expected-results table E1/E6 can be stated qualitatively but not matched
  numerically until those are obtained.
- **G6 (unverified IDs):** 2604.13781, 2604.12907, 2607.01323 are 2026-relative and were not relied on; 2408.10079 abstract not
  read in full. These are flagged, not used.

---

## 6. "What should change" — recommendations for the overseer (NOT auto-applied)

Each names the project artifact/claim it supports or challenges. Recommendations only.

1. **(Supports Q3; challenges the current ergodic-baseline plan.)** Adopt **1706.02601 [established]** as the canonical ETH-in-QDM
   citation and **define the Q3 ergodic/MCMC baseline per winding/topological sector**, not globally. This resolves G1 and makes
   the frustrated-vs-square thermalization comparison well-posed. Highest-priority change.

2. **(Supports Q3; adds the missing theory anchor.)** Cite **2303.08461 [established]** (PRX Quantum 4, 030320) and **1806.11123
   [established]** (Sci. Adv. 5, eaau8342) as the **expected-results theory**: coarse-Trotter prethermal plateau tracking the target
   model (E1), with faithfulness below a **sharp dt threshold** (E2). Recommend adding a **dt-convergence study** to the Stage-1/3
   validation plan — currently the repo validates vs ED at fixed small dt but does not scan dt against a threshold.

3. **(Supports Q2; adds the canonical phase diagram.)** Adopt **cond-mat/0302105 [established]** (Isakov–Moessner, PRB 68, 104409)
   as the triangular-TFIM phase-diagram reference and **1602.02979 [established]** (PRB 93, 104412) for the explicit clock-order
   pattern (M,−M/2,−M/2) and order-by-disorder. The project's §Q2 notes cite the mapping papers but not the phase diagram; any
   "three-sublattice/clock order" statement should cite these.

4. **(Challenges a possible quantum-advantage framing.)** Record **2308.05077 [established]** (Sci. Adv. 10, eadk4321), **2306.14887**
   and **2308.03082** as the **classical frontier**. Recommend the report frame the contribution as **frustration/sector physics +
   logical-qubit/QEC methodology**, and (optionally) run a **belief-propagation / sparse-Pauli classical baseline** to bound the
   project's own local observables honestly. Addresses G2.

5. **(Reframes Q2 interpretation.)** Flag **1303.0883** (PRB 87, 214415): the project's triangular embedding is the J′=J point of a
   model with a **disorder line and incommensurate floating phase**; the square-vs-triangular ⟨ZZ⟩ contrast may be incommensurate/
   non-monotonic and finite-size-sensitive. Recommend a caveat in the Q2 write-up (G4).

6. **(Supports Q3 + the dephasing thread.)** Note **2401.11294 [established]** (inexact-constraint ⇒ exponentially slow
   thermalization) and **2506.13856** (dephasing mixes within a sector): together they predict the triangular quench shows
   **anomalously slow, sector-bottlenecked relaxation** (E4) and reframe dephasing as a within-sector equilibration tool, not only
   noise. Compare against the project's existing dephasing finding in `docs/findings_vs_questions.md`.

7. **(Supports Q3; hydrodynamics observable.)** If the project adds the inhomogeneous-quench / diffusion observable to match the
   reproduction target, cite **2405.16975** (ETH↔hydrodynamics) and note **1909.01351** (long-range ⇒ anomalous/Lévy transport) as
   the reason the extracted exponent may not be plain diffusion on H2's longer-range couplings (E6).

---

## 7. Open questions

**For the overseer:**
- Should Q3's "done when" be rewritten so the ergodic baseline is **per winding sector** (per 1706.02601)? This changes the MCMC
  build spec that is currently [pending].
- Is a **dt-convergence/Trotter-threshold study** (E2) in scope for the Stage-1/3 validation, or routed to Claude Code for the
  model-specific threshold derivation (G3)?
- Should the project run a **classical BP/sparse-Pauli baseline** (2308.05077, 2306.14887) to bound its own observables and state
  classical hardness honestly, or is that out of scope?

**For the user:**
- Is the frustrated contribution to be framed as **physics insight + QEC methodology** (given the classical frontier E7/G2), rather
  than beyond-classical dynamics? This affects the report's headline claim.
- For the ground-state/field-scan side, do you want the **three-sublattice/clock order parameter** (M,−M/2,−M/2) added as an
  observable to connect to cond-mat/0302105 and 1602.02979, or is the project purely dynamical?

---

## 8. Single most important source a human should read next

**arXiv:1706.02601** — Lan & Powell, "Eigenstate thermalization hypothesis in quantum dimer models," **Phys. Rev. B 96, 115140
(2017)** **[established]**. It is the one source that most directly determines whether the project's central Q3 comparison is
well-posed: on **both square and triangular** dimer manifolds, ETH holds **only per topological sector**, so the ergodic baseline
must be sector-restricted. Everything in the "expected results" table for thermalization hinges on this.

Runner-up: **arXiv:2303.08461** (PRX Quantum 4, 030320) for the coarse-Trotter prethermal-plateau expectation, and
**arXiv:cond-mat/0302105** (PRB 68, 104409) as the canonical triangular-TFIM phase diagram.
