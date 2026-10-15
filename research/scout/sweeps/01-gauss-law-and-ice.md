# Scout Sweep 01 — Gauss-law detect/correct/mitigate (WIDE) + Ice-states theory

**Scout:** qc-scout (sweep 1) · **Date:** 2026-10-06 · **Scope:** SCOPE §3 skeptical thread + ice-states mapping.
**Mandate:** discovery BEYOND the project's seed sources, actively hunting contradicting/reframing work.
Notes only — this file changes no project claim and writes no project code. Every source is status-tagged.

Status vocabulary (carried from SCOPE/research): **[established]** = primary source read in full (here: abstract
read verbatim via arXiv abstract page, and/or body text where quoted); **[fetched]** = seen through an automated
summary/snippet, not hand-checked line by line; **[inferred]** = my reasoning; **[unverified]** = only a snippet/secondhand seen.
I did NOT invent any ID/DOI/number. Every arXiv ID below was resolved on its arXiv abstract page unless flagged otherwise.

---

## 0. What the project already concluded (the baseline I am testing)

From `docs/gauss_law_dimers.md §5`, `docs/findings_vs_questions.md`, `research/04-gauss-law-citations.md`:
- **EC: NO** (distance-1 "code"; undetectable weight-1 Z anywhere + X/Y on flippable spins; constraint violated by ideal dynamics).
- **Postselection on D=0: modest YES, X/Y (bit-flip-type) noise only**; 2–8× bias cut on spin correlators at p≤3e-3, 1.1–1.8× cost;
  **floored at O((h/J)²)** (~0.013 at h/|J|=0.3); **acceptance worsens with size** even noiseless.

  > **Note added 2026-10-15, corrected the same day.** The earlier version of this note said h/|J| = 0.3 was the
  > project's own choice and "not the field of 2503.20870's triangular quench". **That is wrong.** The paper's
  > Figure 4(e) states verbatim "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)", §V's body sets a weak transverse field
  > (0 < h ≪ J), and the lattice is 9×6 — so **h/|J| = 0.3 is the reference's §V field**, and the baseline above sits
  > in the reference's own regime. [established] The h/|J| = 2 reading came from the released `quench4_*.qasm` files,
  > which carry the square quench's field angle and are defective (`research/05-zenodo-dataset-map.md` §3). It remains
  > true that at h/|J| = 2 the O((h/J)²) floor and the dimer description behind it would not be a controlled
  > approximation — but that field is the paper's *square* value, not the triangular one, so the caveat does not bear
  > on this sweep's baseline.
- **Under dephasing: NO** (Z commutes with every D_t).
- **Depolarizing self-mitigation from defect density: NO as a general method** (F_gauss ≠ per-observable decay under local noise).
- **Exact-symmetry methods (GUESS, Cai, symmetry-adjusted shadows): N/A** to a Z-product quench (⟨P⟩=⟨ΠX⟩=0, no U(1)).
- **Platforms: undetermined**; draft's neutral-atoms-best / H2-worst ranking stays [unverified].

The seeds I mined for terms then left: 2503.20870, 2509.25326, 2602.22211, 2211.06703 (Iceberg), Moessner–Sondhi PRB 63 224401,
Chao–Reichardt 1705.02329, and the draft's ten IDs (2603.13060, 2101.03151, 2310.03071, 2203.08905, 2608.21103, 2604.11085,
2508.17513, 2101.01690, 2205.09247, 2406.02501).

---

## 1. Search strategy actually used

Term-mining from seeds produced these concept clusters, which I searched independently (community in brackets):
1. **Gauss-law / gauge-invariance protection by energy penalty** [cold atoms, LGT] — "gauge protection", "energy penalty",
   "single-body terms", "emergent global symmetry".
2. **Monitored / measurement-based gauge protection & postselection** [LGT + QEC + trapped ion] — "Zeno", "measurement rate",
   "syndrome", "one-form symmetry", "adaptive circuits", "on-chip feedback bit-flip correction".
3. **Symmetry verification scaling / finite-shot limits** [QEM] — "symmetry verification", "virtual distillation",
   "finite-shot operating window", "acceptance probability", "postselection scalable".
4. **Postselection accuracy gains in genuine codes** [QEC/stat-mech] — "postselection", "logical failure", "large deviation".
5. **Coulomb phase / ice rules / emergent gauge field** [condensed matter] — "divergence-free flux", "ice rule two-in-two-out",
   "pinch point", "height field", "Rokhsar–Kivelson", "triangular Ising dimer", "Z2 Ising gauge theory".
6. **Hardware ice/dimer realizations** [Rydberg/neutral atom] — "Rydberg kagome dimer", "triangular TFIM Rydberg", "erasure conversion".

Directions: forward/backward citation hops from Moessner–Sondhi (→ Moessner–Sondhi–Fradkin Z2-gauge mapping; → Henley review;
→ triangular QDM RVB; → emergent-RK realistic Ising) and from 2203.08905 / 2608.21103 (→ Halimeh–Hauke protection family;
→ monitored-LGT Zeno; → MBQS trapped-ion H2 postselection).

---

## 2. Target A — three buckets

### 2A. CORROBORATING (strengthen the current verdict)

- **arXiv:2608.04290** — Sukeno, Rinaldi, Okuda, "Measurement-based simulation of lattice gauge theory dynamics … on a
  trapped-ion processor" (Quantinuum **H2**, submitted 4 Aug 2026). **[established — abstract read in full].**
  *What it says:* first MBQS of (2+1)d Z₂ gauge theory on H2; the measurement record "simultaneously provides one-form-symmetry
  syndromes at no additional cost, enabling postselection that strongly suppresses observed Gauss-law violations and improves
  aggregate agreement with ideal Trotterized dynamics." *Why it matters:* this is the **single most on-target source** — Gauss-law
  postselection on the exact hardware the project targets, 2026, and it reports a *qualitative benefit*. Corroborates the project's
  "postselection = modest YES" and its platform caution, but see §2B: it also pressures the "undetermined platforms / H2 worst" line
  because here the benefit is realized *on H2*. It uses a one-form syndrome from an ancilla/measurement record — i.e. the detection
  is engineered, not relied on from an emergent approximate constraint, which is consistent with the project's EC=NO reasoning.

- **arXiv:2203.08905** (already a seed, but note the forward-citation neighborhood) — the Z₂-LGT confinement experiment that
  the project already cites for Gauss-law postselection. Its forward citations (2608.04290, 2608.21103, 2405.18504) all reinforce
  that **local gauge-law postselection beats global-charge postselection** — consistent with the project's "detection must be local."

- **arXiv:2606.15464** — Scavino Alfaro, "Certified Finite-Shot Operating Windows for Virtual Distillation and Symmetry
  Verification" (13 Jun 2026). **[established — abstract read in full].**
  *What it says:* proves MSE laws for symmetry verification (SV) and virtual distillation that "separate the residual bias from
  undetectable errors from the sampling penalty set by the acceptance probability," yielding a *regime statement, not a universal
  ranking* — windows explain "when mitigation advantages should appear or disappear." *Why it matters:* independently formalizes
  exactly the project's own finding — that SV/postselection has (i) a residual bias floor from undetectable errors and (ii) a
  shot cost from acceptance, and that whether it beats alternatives is regime-dependent. Strong theoretical backing for the
  project's "modest, conditional YES … floored" framing and for not making a universal claim.

- **arXiv:2001.00024** — Halimeh & Hauke, "Reliability of lattice gauge theories" (PRL 125, 030503, 2020). **[established — abstract].**
  *What it says:* with a gauge-breaking term, "the gauge violation accumulates only perturbatively at short times before
  proliferating only at very long times." *Why it matters:* this is the general version of the project's measured **O((h/J)²)**
  short-time violation floor and the "physics floor" idea — the violation grows controllably at short time. Corroborates the
  scaling claim and the notion that the constraint is meaningfully conserved only over a finite window.

### 2B. CONTRADICTING / REFRAMING (weaken or reframe the current verdict)

- **arXiv:2007.00668** — Halimeh, Hauke et al., "Gauge-Symmetry Protection Using Single-Body Terms." **[established — abstract].**
  *What it says:* single-body **energy-penalty** terms (single-qubit gates / local chemical potentials) can render undesired gauge
  sectors "inaccessible by any unitary dynamics for at least exponentially long times"; "the gauge-invariant subspace is protected
  by an emergent global symmetry … immediately applied to other symmetries," verified in digital and continuous-time simulation up
  to t>10¹⁰/J. *Why it REFRAMES:* the project tests the emergent Gauss law *passively* (measure defects, postselect/rescale). This
  line says you can **actively protect** the constraint by adding a penalty term to the simulated Hamiltonian — turning the
  approximate emergent constraint into a dynamically enforced one, suppressing leakage out of the dimer manifold *before* readout.
  The project's EC=NO / "constraint violated by ideal dynamics" verdict is about the *bare* TFIM; it does **not** consider adding a
  protection term. This is a method the project never named that could change the "detection only" conclusion toward "protection +
  detection." Caveat: protection against *coherent/unitary* gauge-breaking, not against stochastic Pauli noise per se — needs reading.

- **arXiv:2108.02203** — Halimeh et al., "Stabilizing Lattice Gauge Theories Through Simplified Local Pseudo Generators."
  **[established — abstract].** *What it says:* "simplified local pseudo generators designed such that within the physical sector
  they act identically to the actual local generator" reliably stabilize gauge invariance with fewer terms. *Why it REFRAMES:*
  gives a cheaper, hardware-feasible route to protection; relevant to whether a dimer-constraint penalty is practical on H2.

- **arXiv:2204.13709** — Halimeh & Hauke, "Stabilizing Gauge Theories in Quantum Simulators: A Brief Review" (2022).
  **[established — abstract + author/affiliation block read].** *What it says:* reviews "linear gauge protection" schemes and their
  power to protect gauge invariance, disorder-free localization, scars, etc. *Why it matters:* the authoritative entry point to the
  entire protection family the project's verdict omits. **Recommend as a required-reading anchor for the overseer.**

- **arXiv:2405.18504** — Wauters, Ballini, Biella, Hauke, "Symmetry-protection Zeno phase transition in monitored lattice gauge
  theories" (PRL-track; v3 Mar 2025). **[established — abstract read in full].** *What it says:* a **sharp transition** in the
  measurement rate between "a protected gauge-theory regime resistant to simulation errors and an irregular regime"; and they
  "design an **on-chip feedback mechanism that corrects bit-flip errors** and significantly enhances the discrete-time scheme."
  *Why it CONTRADICTS/REFRAMES:* (i) a *threshold* exists — above a measurement rate the gauge sector is actively protected, which
  is stronger than the project's passive-detection picture; (ii) explicit **bit-flip correction via feedback** challenges the
  project's flat "EC: NO on any platform" — correction *is* possible if you add mid-circuit measurement + feedback (which H2 and
  neutral-atom platforms support). The project's EC=NO is correct *for the bare emergent constraint with no ancilla/feedback*, but
  this source shows the door the project closed can be reopened with monitoring. Reframes "NO" → "NO without feedback; conditionally
  YES with measurement-and-feedback at sufficient rate."

- **arXiv:2405.09462** — "[gauge drift suppression via the Zeno effect]" (title not fully resolved from snippet; **[unverified]** —
  only a search snippet seen; ID resolves to a quant-ph PDF). *What it says (snippet):* suppress gauge drift via frequent projection
  onto the physical subspace; adds a technique to slow the drift and reduce required projection frequency. *Why it matters:* another
  active-protection route. **Flagged [unverified]; abstract not yet read — do not rely on specifics.**

- **arXiv:2510.05222** — Chen, Xu, Sommers, Huse, Thompson, Gopalakrishnan, "Scalable accuracy gains from postselection in quantum
  error correcting codes" (v3 May 2026). **[established — abstract read in full].** *What it says:* in the toric-code coding phase,
  logical failures are dominated by exponentially unlikely syndromes, so "postselecting on not seeing these … offers a **scalable
  accuracy gain**"; logical error suppressed p_f → p_f^b with b≥2 (b=3.1(1) for the toric code). *Why it REFRAMES:* the project
  asserts postselection "acceptance worsens with size even without noise" as a limitation. This paper shows that in a *genuine*
  topological code, postselection accuracy gains can be **scalable** (abort rate controlled, gain grows). The project's distance-1
  dimer "code" is a different regime (no code distance, physics floor), so this does NOT directly overturn the verdict — but it
  reframes the blanket pessimism: the limiting factor is the *distance-1/physics-floor* nature of the emergent constraint, not
  postselection per se. Useful contrast to sharpen *why* the dimer case is weak (it is not a stabilizer code).

- **arXiv:2608.04290** (also in 2A) **cuts both ways on platforms:** it realizes Gauss-law postselection benefit **on H2**,
  which pressures the draft's "H2 worst platform" claim that the project left [unverified]. Reframes the platform question toward
  "benefit is observable on H2 for an *engineered* one-form syndrome," distinct from the *emergent approximate* constraint the
  project studied.

### 2C. ADJACENT / METHOD (benchmarks, context, methods to compare against)

- **arXiv:2112.14262** — "Digital Quantum Simulation of the Schwinger Model and Testing Symmetry Protection with Trapped Ions"
  (PRX Quantum 3, 020324). **[fetched — abstract snippet].** Trapped-ion Schwinger model with symmetry-protection + symmetry-inspired
  postselection; a direct methodological predecessor to 2608.21103 and a benchmark for symmetry postselection on ions.
- **arXiv:2411.07778** — "Trapped-ion quantum simulation of the Fermi-Hubbard model as a lattice gauge theory using hardware-aware
  native gates." **[fetched — snippet].** Maps FHM→Z₂ LGT to a symmetry-protected subspace enabling **postselection error mitigation**,
  verified in noisy classical sim. Adjacent method: same "constraint → postselection" logic in a different model; a comparison target.
- **arXiv:2412.07844** — "Symmetry verification for noisy quantum simulations of non-Abelian lattice gauge theories." **[fetched —
  snippet].** Extends symmetry verification to non-Abelian LGT; adjacent for how far symmetry-postselection generalizes.
- **arXiv:1807.10050** — "Low-cost error mitigation by symmetry verification" (Bonet-Monroig, Sagastizabal, Singh, O'Brien).
  **[fetched — snippet].** Foundational SV reference incl. a **zero-cost post-processing** variant (subspace-expansion-equivalent);
  the methodological ancestor of the whole SV family and a baseline the project's postselection should be positioned against.
- **arXiv:2211.01380** — "[D-dimensional Z₂ LGT realization in a Bose–Hubbard Lieb superlattice with emergent gauge protection]."
  **[fetched — snippet].** Cold-atom realization using an *emergent gauge protection term* — adjacent to the active-protection idea.
- **arXiv:2310.12201** — "Cold-atom quantum simulators of gauge theories" (review). **[fetched — snippet].** Broad review context for
  the platform discussion; good for the "where" question across cold-atom hardware.

---

## 3. Target B — ICE-STATES THEORY: the precise mapping

The project's emergent Gauss law (defect-free dimer manifold on the dual honeycomb, defects as ±charges, winding sectors) is a
**specific instance of the Coulomb phase of a frustrated magnet**. The authoritative sources below pin down the correspondence.

### 3.1 Authoritative sources (established via abstracts; one review via its journal DOI)

- **Henley, "The Coulomb phase in frustrated systems," arXiv:0912.4531**, Annu. Rev. Condens. Matter Phys. **1**, 179 (2010),
  **DOI 10.1146/annurev-conmatphys-070909-104138**. **[established — abstract read in full; journal DOI confirmed on the abstract page].**
  The definitive review. Abstract (verbatim core): the Coulomb phase is "an emergent state for lattice models (particularly highly
  frustrated antiferromagnets) which have **local constraints that can be mapped to a divergence-free flux**. The coarse-grained …
  flux … behave analogously to electric or magnetic fields; in particular, **defects at which the local constraint is violated behave
  as effective charges with Coulomb interactions**." Covers power-law correlations, **pinch points** in reciprocal space, quantum
  generalizations, phase transitions to LRO, and disorder.
- **Moessner, Sondhi, Fradkin, "Short-ranged RVB physics, quantum dimer models and Ising gauge theories," arXiv:cond-mat/0103396**,
  **Phys. Rev. B 65, 024504 (2002)**. **[established — abstract read in full].** QDMs "arise as particular limits of Ising (Z₂) gauge
  theories, but in these limits the system develops a **larger local U(1) invariance** that has different consequences on different
  lattices." The standard Z₂ gauge theory is a generalized QDM in which relaxing the hardcore constraint "breaks the U(1) down to Z₂."
- **Moessner & Sondhi, "An RVB phase in the triangular lattice quantum dimer model," arXiv:cond-mat/0007378**, PRL 86, 1881 (2001).
  **[established — abstract].** The triangular QDM has "a truly short ranged resonating valence bond (RVB) phase … deconfined, gapped,
  spinons for a finite range of parameters," plus three crystalline phases — i.e. the triangular dimer Gauss law is **non-bipartite /
  Z₂** and supports a genuine Z₂ topological (toric-code-class) liquid, unlike the bipartite (U(1)/Coulomb-critical) square case.
- **"Emergent Rokhsar-Kivelson point in realistic quantum Ising models," arXiv:2106.05518.** **[fetched — snippet].** QMC on the
  triangular TFIM finds "the multicritical point in the phase diagram corresponds to the **RK point of the QDM on the honeycomb
  lattice**." Direct bridge: the project's triangular-TFIM → honeycomb-dimer construction has a known RK point in its phase diagram.
- **Semeghini et al., "Probing topological spin liquids on a programmable quantum simulator," Science 374, 6572 (2021)** (Rydberg
  kagome dimer/Z₂ spin liquid; referenced by arXiv:2506.21255 and 2207.04412). **[unverified — citation seen secondhand in those
  arXiv papers; I did not open the Science page].** The flagship *experimental* ice/dimer realization: Z₂ dimer liquid in a Rydberg
  array. **Report as-found; verify the Science DOI before relying on it.**
- Supporting condensed-matter context (all **[fetched — snippets]**): classical TIAF ↔ dimer mapping (cond-mat/0409776 "String
  Picture…"; cond-mat/0011250 Moessner–Sondhi long paper — a seed); honeycomb fully-frustrated TFIM dimer phases
  (researchgate PRB, Jiang–Emeljenko-type); quench dynamics of frustrated Ising (arXiv:2403.00091).

### 3.2 The precise mapping (how the project's emergent Gauss law maps onto ice rules / Coulomb phase)

**[inferred, from the established sources above + the project's own §2–§3 identities]:**

| project object (`docs/gauss_law_dimers.md`) | ice/Coulomb-phase counterpart | correspondence |
|---|---|---|
| dimer on frustrated bond, n_b=(1+Z_iZ_j)/2 | dimer / occupied link on dual honeycomb | identical; triangular-Ising ground manifold ↔ hard-core dimer coverings of the dual honeycomb |
| triangle constraint G_t∈{1,3} (odd), §3 identity 1 | **ice rule / vertex constraint** (fixed parity of flux at each vertex) | each dual-lattice vertex (triangle) has exactly one dimer in the GS manifold ⇒ the honeycomb hard-core-dimer constraint = the vertex ice rule |
| defect D_t=(G_t−1)/2, charge Q_t=div E=±2D_t | **monopole / defect = source of emergent flux** (Henley: "defects … behave as effective charges with Coulomb interactions") | a Gauss-law violation is a magnetic monopole in the Coulomb-phase language; the project's "each defect costs 2|J|, defects come in ± pairs" = charge-neutral monopole pairs |
| electric field E_b=n_b−1/3 oriented A→B; div E=Q_t | **divergence-free coarse-grained flux** B(r) with ∇·B=charge density (Henley) | the project's E_b IS the lattice flux; "defect-free ⇒ div E=0 everywhere" = the Coulomb-phase divergence-free condition |
| winding W_x, W_y (electric flux through non-contractible loops) | **topological/flux sectors** of the Coulomb phase (height-field winding) | sector labels = global flux; the project's §3 identity 4 (W constant across rows on the defect-free subspace) = flux conservation |
| defect density ∝ (h/|J|)² | thermally/quantum-activated **monopole density** | finite monopole density destroys strict Coulomb-phase power laws; the project's floor = a nonzero monopole density |

**The key physics distinction the project should state precisely [inferred, grounded in cond-mat/0103396 + 0007378 + Henley]:**
- The **square-lattice / bipartite** dimer (and classic spin ice on pyrochlore) Coulomb phase has a **U(1)** emergent gauge field:
  algebraic (dipolar, pinch-point) correlations, a *height field*, a genuine Coulomb phase.
- The **triangular-Ising → honeycomb-dimer** case is on a **non-bipartite** triangle lattice. Per Moessner–Sondhi(–Fradkin), the
  triangular QDM's liquid is a **Z₂** (toric-code-class) topologically ordered RVB phase, **not** a U(1) Coulomb phase; the honeycomb
  *dual* on which dimers live is bipartite, so there is a height description, but the triangular QDM at its RK point sits at the
  boundary of a Z₂ liquid. **Consequence for the project:** calling the triangular emergent constraint a "Gauss law" is correct
  (it IS a local divergence constraint with ± monopole defects), but the *gauge group* is **Z₂**, not U(1). This matters because:
  (i) the "charge" is Z₂-valued (defects come in pairs, parity-conserved — exactly the project's §3 identity 3), and (ii) the
  symmetry that could be used for mitigation is a **Z₂ one-form / gauge symmetry**, which is precisely the symmetry exploited in
  the Z₂-LGT postselection works (2203.08905, 2608.04290). This ties target B back to target A: **the project's emergent Gauss law
  is the same Z₂ gauge constraint whose postselection is demonstrated on H2 in 2608.04290.**

**Where the project DIFFERS from textbook spin ice / Coulomb phase [inferred]:**
- Spin ice (pyrochlore, two-in/two-out) is a **3D U(1)** Coulomb phase with deconfined monopoles at finite T; the project is a **2D**
  constrained magnet whose liquid (at the QDM/RK point) is **Z₂**. The "ice rule" analogy is structural (local parity constraint +
  defects-as-charges) but the universality class differs (Z₂ topological vs U(1) Coulomb).
- The project studies **quench dynamics under the TFIM**, where the constraint is only *emergent and approximate* (violated at
  O((h/J)²)), whereas the Coulomb-phase/ice literature is largely about *equilibrium* constrained ensembles. The project's
  "physics floor" is the dynamical monopole density; the ice literature's analog is the thermal monopole density.
- Six-vertex / F-model: the triangular-Ising dimer constraint is the honeycomb hard-core-dimer (one-dimer-per-vertex) rule, which is
  the honeycomb analog of the six-vertex ice rule on the square lattice. I did **not** find a source that maps the project's specific
  honeycomb-dimer constraint onto the six-vertex model directly; the standard route is dimer→height→Coulomb, not dimer→six-vertex.
  **Flagged as a gap (§4).**

---

## 4. Gaps and conflicts

- **GAP (six-vertex):** no source cleanly maps the project's honeycomb-dimer Gauss law onto the six-vertex/F-model; the honeycomb
  dimer ↔ square six-vertex equivalence is lattice-specific. The project should either drop the six-vertex framing or cite the
  dimer→height→Coulomb route (Henley) rather than a direct six-vertex map.
- **GAP (U(1) vs Z₂ labeling):** the project calls the constraint a "Gauss law" and an "emergent gauge field" without stating the
  gauge group. The condensed-matter sources say the triangular QDM liquid is **Z₂**, the bipartite/square one is **U(1)**. This is a
  precision gap, not an error.
- **CONFLICT (EC verdict):** the project says "Error correction: NO, on any platform." arXiv:2405.18504 demonstrates **on-chip
  feedback bit-flip correction** in a monitored Z₂ LGT, and 2608.04290 shows syndrome extraction on H2. These do not refute the
  project's *bare-constraint, no-ancilla* reasoning, but they conflict with the *unconditional* phrasing "NO on any platform."
  The honest reconciliation: NO for the *passive emergent constraint*; conditionally YES for *monitored/feedback* schemes the project
  did not model.
- **CONFLICT (platforms / H2):** the draft's "H2 worst" (left [unverified] by the project) is in tension with 2608.04290, which
  realizes Gauss-law postselection benefit *on H2*. The distinction (emergent-approximate vs engineered one-form syndrome) resolves
  it but should be stated.
- **GAP (active protection never considered):** the entire Halimeh–Hauke energy-penalty / pseudo-generator protection family
  (2007.00668, 2108.02203, 2204.13709) is absent from the project's analysis. The project tested *passive* use of the constraint;
  *actively adding a penalty* to suppress leakage is an unexplored, literature-backed option that could change "detection-only" to
  "protection + detection."
- **UNVERIFIED items to close:** Semeghini et al. Science 374 (2021) DOI (seen secondhand); arXiv:2405.09462 abstract (snippet only);
  arXiv:2106.05518 and 2403.00091 bodies (snippets only).

---

## 5. "What should change" — recommendations for the overseer (NOT auto-applied)

Framed as recommendations only; each names the project claim it supports/challenges.

1. **Soften "EC: NO on any platform" to "NO for the passive emergent constraint; conditionally YES only with mid-circuit
   measurement + feedback."** *Challenges* the EC verdict's phrasing. Basis: 2405.18504 (on-chip bit-flip correction), 2608.04290
   (H2 syndrome extraction). The project's underlying reasoning (distance-1, no bare syndrome→recovery) is correct and should stay;
   only the *unconditional* "any platform" wording overreaches.
2. **Add active gauge protection as an explicitly-considered-and-scoped option.** *Challenges* the completeness of the mitigation
   survey. Basis: 2007.00668 / 2108.02203 / 2204.13709. Recommend a one-paragraph "not tested: adding a defect-penalty term to
   suppress leakage before readout" note, with the caveat that these protect mainly against *coherent* gauge-breaking.
3. **State the gauge group (Z₂, non-bipartite) explicitly in the ice-states framing.** *Supports and sharpens* the dimer/Gauss-law
   mapping. Basis: cond-mat/0103396, cond-mat/0007378, Henley 0912.4531. Note the triangular liquid is Z₂ (toric-code-class), the
   bipartite/square one is U(1)/Coulomb — the project's emergent "Gauss law" is a **Z₂** gauge constraint, which is *the same symmetry*
   exploited by the Z₂-LGT postselection experiments (ties the condensed-matter and QEM halves together).
4. **Reconcile the platform line with 2608.04290.** *Challenges* the draft's [unverified] "H2 worst." Basis: 2608.04290 realizes
   Gauss-law postselection benefit on H2. Recommend distinguishing *emergent-approximate* (project) vs *engineered one-form syndrome*
   (that paper) rather than leaving the ranking open-ended.
5. **Cite 2606.15464 as independent theoretical backing for the "modest, floored, regime-dependent" postselection verdict.**
   *Supports* the postselection verdict. Basis: its MSE law separates undetectable-error bias from acceptance-driven shot cost — the
   project's finding, formalized and certified.
6. **Use 2510.05222 to sharpen *why* the dimer constraint is weak.** *Supports* the EC=NO reasoning while *reframing* the
   "acceptance worsens with size" line. Basis: postselection accuracy gains ARE scalable in genuine topological codes (p_f→p_f^b);
   the dimer case is weak specifically because it is distance-1 with a physics floor, not because postselection is inherently
   unscalable. Recommend rewording the size-scaling caveat accordingly.
7. **Add Henley 0912.4531 as the canonical ice/Coulomb-phase citation** for the "defects = charges, divergence-free flux, winding =
   flux sector" mapping. *Supports* the dimer section; currently the project leans only on Moessner–Sondhi (seed) and 2503.20870.

---

## 6. Open questions

For the overseer:
- Is active gauge protection (energy penalty / pseudo-generator) in scope for the Gauss thread, or explicitly out of scope? It is the
  largest unexplored lever and would require a new simulation (penalty term in `GaussLawConfig`) — likely a reviewer/overseer call,
  possibly a Claude Code hand-off per SCOPE §10 (new scheme design).
- Should the project distinguish *emergent-approximate* vs *engineered* Gauss-law postselection explicitly in its verdict, given
  2608.04290 does the engineered version on the target hardware?

For the project lead:
- Does the project want to claim anything about the Z₂ (vs U(1)) nature of the emergent gauge field, or keep "Gauss law" generic?
- Is a monitored/feedback error-*correction* variant (2405.18504-style) of interest, or is the Gauss thread deliberately limited to
  passive detection/mitigation?

---

## 7. Single most important source a human should read next

**arXiv:2608.04290** — Sukeno, Rinaldi, Okuda, "Measurement-based simulation of lattice gauge theory dynamics with adaptive quantum
circuits on a trapped-ion processor" (Quantinuum H2, Aug 2026). It is the closest existing work to the project's thread on the
project's exact hardware: it performs **Gauss-law (one-form-symmetry) postselection on H2** and reports it "strongly suppresses
observed Gauss-law violations." Reading its noise/postselection analysis (acceptance rates, which observables improve, how the
one-form syndrome is extracted "at no additional cost") would directly calibrate the project's postselection verdict and its
platform claim, and shows a concrete route (engineered syndrome) that differs from the project's emergent-approximate constraint.
Second priority: **Henley, Annu. Rev. CMP 1, 179 (2010) / arXiv:0912.4531** for the authoritative ice/Coulomb-phase mapping.
