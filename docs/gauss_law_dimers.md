# Triangular TFIM: dimers, winding numbers, emergent Gauss law, and whether it can mitigate noise

Deliverable for `handoff/02-triangular-dimer-gauss-law.md`.
- Code: `src/dimers.py` (observables), `src/gauss_mitigation.py` (noisy simulation and estimators).
- Tests: `tests/test_dimers.py`.
- Data: `data/gauss_law_scaling.txt`, `data/gauss_law_mitigation.txt`, produced by `scripts/run_gauss_law.py`. Settings live in `config.py: GaussLawConfig`.

> **Scope (DECISIONS.md DECIDED-1, decided 2026-10-15):** this study runs at h ≤ 0.5, with h/|J| = 0.3
> as the working point. The reference's own released triangular (quench4) circuits run at
> h/|J| = 2, not 0.3. h/|J| = 0.3 is a deliberate choice of regime — the weak-field point where the
> emergent-Gauss-law / dimer description below is a controlled approximation — not an attempt to
> match or reproduce the reference's triangular experiment. See `DECISIONS.md` DECIDED-1 for the full
> reasoning.

Status tags:
- **[established]**: in a source I checked.
- **[fetched]**: read from arXiv through an automated summary (not hand-checked line by line).
- **[derived]**: proved here and checked exhaustively in tests.
- **[measured]**: output of this repo's code.
- **[inferred]**: reasoned, not tested.
- **[unverified]**: claim not checked.

---

## 1. Convention (stated before any physics)

**[established, confirmed in 2503.20870 v3 full text — research/04-gauss-law-citations.md]**
arXiv:2503.20870 §V writes the triangular experiment as
H = J Σ⟨jk⟩ Z_j Z_k + h Σ_j X_j with "antiferromagnetic (AFM) J>0 couplings, which exhibits
geometric frustration", on a 9×6 torus at dt|J| = 0.25. The paper's own prose (read twice
independently) gives h/|J| = 0.3 — but its own **released** quench4 circuits instead run at
h/|J| = 2 (`research/05-zenodo-dataset-map.md`), and the project never reconciled the two
readings (`DECISIONS.md` DECIDED-1). Against the dataset the project actually has, 0.3 is
**unconfirmed** as the reference's own triangular value.

**This project's h/|J| = 0.3 is OUR OWN choice of regime** (`DECISIONS.md` DECIDED-1, decided
2026-10-15), not a reproduction of either reading above: it is the weak-field point where the
sector-restricted emergent-Gauss-law / dimer description below is a controlled (first-order in
h/|J|) approximation, chosen on physics grounds rather than to match the reference's triangular
quench. dt|J| = 0.25 is unaffected by this choice and is still accurately described as the
reference's own time step.

Our code uses H = −J Σ ZZ − h Σ X (Stage 1). So **the frustrated model is J_ours = −J_ref < 0**,
matching the reference's AFM sign choice. `config.GaussLawConfig` sets J = −1, h = 0.3, dt = 0.25.

The sign of h does not matter here. Conjugating by Π_i Z_i maps h → −h. It leaves Z-basis product states and every
observable below (all diagonal) unchanged.

Why the sign matters: with our default J > 0 every bond of a triangle can be satisfied. The model is then not frustrated
and nothing below applies (`test_ferromagnet_is_not_frustrated`).

## 2. Spin → dimer map and operators [established mapping; derived operator forms]

The mapping is the Moessner–Sondhi picture (Moessner & Sondhi, PRB 63, 224401 (2001),
doi:10.1103/PhysRevB.63.224401 — confirmed in full text, research/04-gauss-law-citations.md)
**[established]**. Reference §V **[established, confirmed in 2503.20870 v3]**: "lowest-energy classical
configurations can be identified with dimer coverings of a dual hexagonal lattice (an edge having a
dimer when AFM order of adjacent spins is frustrated)".

**Gauge group of the emergent constraint [established + fetched; review/06 A7, A10].** The constraint
is a **local Z₂ Gauss law**: the defects are Z₂-valued and appear in ± pairs (the §3 identity 3 below),
and the conserved winding labels are Z₂/topological. The *triangular* (non-bipartite) QDM liquid is a
Z₂, toric-code-class topological phase, whereas the *bipartite/square* dimer problem supports a
U(1)/Coulomb (height-field) description. The precise statement, following Moessner–Sondhi–Fradkin
(PRB 65, 024504, arXiv:cond-mat/0103396 [established]), is subtler than "triangular = Z₂, square = U(1)":
the hardcore dimer constraint itself carries an enhanced **U(1)** invariance, and the full Ising (Z₂)
gauge theory *breaks that U(1) down to Z₂* when the hardcore constraint is relaxed — with
lattice-dependent consequences. The canonical review of this physics — defects behaving as effective
charges, a divergence-free emergent flux, and winding = flux through a non-contractible loop — is
Henley, "The Coulomb phase in frustrated systems," Annu. Rev. CMP 1, 179 (arXiv:0912.4531 [fetched]);
the triangular QDM Z₂ liquid is Moessner–Sondhi, PRL 86, 1881 (arXiv:cond-mat/0007378 [fetched]). This
is a precision gain, not a correction: the project never claimed U(1).

Geometry is the repo's periodic embedding: bonds along (1,0), (0,1), (1,1), with Lx, Ly ≥ 3. Plaquette (x,y) contains two triangles:
- A = {(x,y),(x+1,y),(x+1,y+1)}
- B = {(x,y),(x,y+1),(x+1,y+1)}

The honeycomb dual has its vertices at triangles and its edges crossing bonds. Every bond borders exactly one A and one B triangle,
so the dual lattice is bipartite (tested).

| object | operator (diagonal; Z = ±1) | code |
|---|---|---|
| dimer on bond b=(i,j) | n_b = (1 + Z_iZ_j)/2 | `TriangularDimers.dimer` |
| dimers at triangle t | G_t = Σ_{b∈t} n_b ∈ {1,3} | — |
| Gauss-law violation (defect) | D_t = (G_t − 1)/2 = (1 + Z_aZ_b + Z_bZ_c + Z_aZ_c)/4 | `.defect` |
| charge, with E_b = n_b − 1/3 oriented A→B | Q_t = div E = +2D_t (A), −2D_t (B) | `.charge` |
| winding through row y | W_x(y) = 3·Σ_x n_{(x,y),(x+1,y)} − Lx | `.winding_x` |
| winding through column x | W_y(x) = 3·Σ_y n_{(x,y),(x,y+1)} − Ly | `.winding_y` |
| dimer–dimer correlation | C_r = Σ_{a<b, \|a−b\|=r} ⟨n_a n_b⟩ − ⟨n_a⟩⟨n_b⟩ (reference form) | `.dimer_correlation_by_distance` |
| winding full counting statistics | P(W) | `.winding_distribution` |
| flippable spin | Π_s = Π_k (1 − Z_{h_k}Z_{h_{k+1}})/2 over the cyclic hexagon | `.flippable` |
| effective constrained dynamics | H_QDM = −h Σ_s Π_s X_s | `.qdm_hamiltonian` |

Notes on these definitions:
- W is defined as 3 × (electric flux through a non-contractible cut). It is therefore an integer for every L.
- Normalization and axis **[established, read directly from 2503.20870 v3 §V + Fig. 4, research/04]**: the reference
  defines 𝒲_x, 𝒲_y as "the total electric flux through the two non-contractible loops wrapping around the torus in
  the x and y directions," initializes the **maximal (𝒲_x, 𝒲_y) = (18, 6)** and **minimal (0,0)** sectors on a
  **9×6 lattice**. So the reference's "9" IS our L_x (𝒲_x = 18 is the larger component on the longer, 9-site, axis),
  confirming the repo's axis assumption. Our 3-sublattice state gives (0,0) ✓. Our stripe state gives (2L_x, −L_y),
  i.e. 𝒲_x = 18 on 9×6 (magnitude matches); the **sign of 𝒲_y differs** (we get −6 where the reference reports +6).
  This is a pure orientation/sign convention of the flux and does not affect any sector-labelling result (the sector
  structure, counts, and conservation are sign-independent); the repo winding is internally consistent.
- C_r **[CORRECTION — reviewer/overseer, see §7 open items]**: the reference Eq. (6) defines the distance r as
  "**the number of vertices traversed along the shortest path** connecting (and including) those edges" on the dual
  honeycomb — a GRAPH distance, not the Euclidean one. The repo's `dimer_correlation_by_distance` currently bins by
  the **minimal-image Euclidean distance between bond midpoints**, which is a valid connected dimer correlator but
  does NOT match the reference's graph-distance convention. The connected-correlator form Σ⟨n_a n_b⟩ − ⟨n_a⟩⟨n_b⟩
  itself matches Eq. (6). To compare directly to the reference's C_r(s) curves, the binning metric must be switched to
  the dual-lattice graph distance. Flagged as a (minor) follow-up, not a physics error in the identities/scaling.

## 3. Exact identities [derived; exhaustively tested over the whole basis on 3×3, 3×4, 4×3; also 4×4 and 3×6 in a probe]

1. G_t ∈ {1,3}. A triangle cannot have 0 or 2 parallel pairs.
2. Σ_b n_b = N + Σ_t D_t. Hence the Ising energy is E = |J|(2Σ_t D_t − N): **the classical ground manifold is exactly the
   defect-free (Gauss-law) subspace, and each defect costs 2|J|.** A corollary is that the bond-energy density is not independent
   information: it is the defect count.
3. Σ_{t∈A} D_t = Σ_{t∈B} D_t for every configuration (total charge 0 on the torus). Defects come in A/B pairs, so the
   defect number is always even.
4. W_x(y+1) − W_x(y) = 6(Σ_B D − Σ_A D) over the strip between the two rows (similarly for W_y). On the defect-free
   subspace W_x and W_y are therefore the same for every row and column, so they are genuine sector labels.
5. [H_QDM, D_t] = [H_QDM, W_{x,y}] = 0 exactly. Π_s only allows flips of spins whose 6 neighbours alternate. Such a flip
   keeps all 6 surrounding triangles defect-free and changes exactly one horizontal (and one vertical) bond on each side,
   which cancels. [H_TFIM, D_t] ≠ 0.

Sector counts found: 3×3 has 42 defect-free states, all in sector (0,0), so **winding tests need ≥ 3×4.** 3×4 has 68 states
in 3 sectors; 4×4 has 42 in 6; 3×6 has 860 in 4.

## 4. The emergent Gauss law: statement, order, meaning

**Statement [derived + measured].** For |h| ≪ |J| the low-energy dynamics stays in the defect-free subspace and conserves
(W_x, W_y). At first order in h it is generated by H_QDM. The reason: flipping a flippable spin costs no Ising energy, while flipping
any other spin creates at least two defects and costs ≥ 4|J|. Constraint and sector conservation hold exactly for H_QDM.
For the full TFIM they hold only approximately. The reference **[fetched]** says the same: "conserved by dynamics under
H_QDM, but violated in evolution under H_TFIM by processes that are higher-order in h/J".

**Order [measured, data/gauss_law_scaling.txt].** The bare-constraint violation is **O((h/|J|)²)**. The admixture amplitude of
defect states is h/(4|J|), and the probability is its square.

Fitted log–log slopes of the defect density per triangle against h, with h ∈ {0.025…0.3}:
- **ED ground state**: 1.98 (3×4), 1.96 (3×6).
- **Quench, time-averaged over t ≤ 20/|J|**: 2.00–2.05 (3×4 stripe and flippable, 3×6 3-sublattice) (dt = 0.25 and dt = 0.025).

The winding leakage P(W ≠ W₀) also scales as h^2.08–h^2.09 for the stripe and 3-sublattice starts (h^2.38 for the 3×4 flippable start, whose small-h leak is tiny and noisier).

A quantitative check uses the stripe state, where no spin is flippable and each flip costs 4|J| and makes 2 defects. First-order
perturbation theory predicts a time-averaged defect density per triangle of **(h/|J|)²/8**. The ratio of measured to predicted is
**1.011** at dt = 0.025. At dt = 0.25 **in this repo's own ZZ-outside Trotter splitting** (`src/trotter.trotter2_step`) it is about
10% higher, because Trotter error also flips spins. (That ≈10% is specific to the stripe start and to this splitting. The dt = 0.25
defect-density inflation in the ZZ-outside splitting depends on the start: ≈40% for the 3-sublattice start on 3×6, ≈18% for the
3×4 flippable start, ≈9% for the stripe. It is a blend of Floquet factors; see `docs/q3_thermalization.md` §8.)
**CORRECTION (peer review, MAJOR):** this subsection previously called dt = 0.25 "the reference's dt" and implied these inflation
figures describe the published H2 circuit. They do not: they are specific to `trotter2_step`'s ZZ-outside splitting, which is
**not** the ordering the published circuit implements. The circuit's own (X-outside) splitting, `src/trotter.circuit_trotter2_step`,
**deflates** these quantities at the same dt = 0.25 instead of inflating them — e.g. defect density comes out ≈40% *below* the
continuous-time value on 3×6 (3-sublattice, h = 0.3), ≈25% below on 3×4 flippable, and ≈46–50% below on 3×3 3-sublattice
**[measured, `scripts/run_trotter_order_compare.py` → `data/trotter_order_compare.txt`]**. The stripe start's circuit-order figure
was not computed in this fix; by the same mechanism a sign reversal is expected there too, but no number is asserted for it
**[inferred, not measured]**.
The test is `test_stripe_quench_matches_first_order_prediction`.

**What a violation means.** In noiseless dynamics a defect is real physics: a virtual excitation out of the dimer manifold
of order (h/J)², enhanced by Trotterization. With noise, a defect is *additionally* created by any bit-flip-type error on a
non-flippable spin. The noiseless value is the **physics floor**. Only the excess above it can carry information about noise.
At our working h/|J| = 0.3 (`DECISIONS.md` DECIDED-1) the floor is not small:
- noiseless postselection on "zero defects" keeps only 0.979 (min 0.956 over t ≤ 10) of shots on 3×3;
- it keeps 0.935 (min 0.908); if it simply compounds per 36 triangles, about 0.935³ ≈ 0.82 at 9×6 **[inferred]** on 3×6;
- the cost grows with the number of triangles even with no noise (108 triangles at 9×6 — **[inferred]**, not simulated at that size).

## 5. Can the Gauss law detect, correct, or mitigate noise? (SCOPE §3, skeptical)

### 5.1 Noise model [assumption, stated; not hardware-calibrated]
After every 2nd-order Trotter step, every qubit independently suffers X, Y, Z with probabilities (px, py, pz) and total p.
- Channels tested: depolarizing (⅓,⅓,⅓), pure dephasing (0,0,1), bit-flip-type (½,½,0).
- p ∈ {1e-3, 3e-3, 1e-2} per qubit per step.
- Main benchmark: exact density matrix on a 3×3 torus. Cross-check: 400 Monte-Carlo trajectories on 3×4.
- Physics: J = −1, h = 0.3 (our own weak-field choice, `DECISIONS.md` DECIDED-1), dt = 0.25 (the reference's own time step), starting from the most-flippable defect-free product state. Read out at t = 3.25 and t = 10.
- Error bars assume 10⁴ shots per circuit.

Not modelled: coherent errors, leakage/loss/erasure, crosstalk, SPAM asymmetry, two-qubit correlated errors.
Every platform statement below is conditional on this model.

### 5.2 Detection power [derived + measured]
- **Z errors are invisible at the moment they occur.** Z_q commutes with every D_t, n_b, W. They are also invisible forever under H_QDM,
  which commutes with D_t. Under H_TFIM they become visible only through later dynamics, at O((h/J)²) efficiency.
  Measured response at t = 10 (3×3, `sensitivity` block):
  - dD/dp = **+0.52** for pure Z, against +36.6 (X) and +36.9 (Y): about 70× weaker;
  - the damage to the target observables is only about 3× smaller (e.g. pattern-memory slope 49.5 for Z against 142.7 for X).
- **X/Y errors are detected with probability 0.46–0.54 per single error** (state-dependent, `single_error_detection`).
  A flip of a *flippable* spin is a legal QDM move. It stays in the constrained subspace and is undetectable.
- So in code language the "Gauss-law code" has **undetectable weight-1 errors of every Pauli type**: Z anywhere, and X/Y on flippable
  spins. Its distance is 1. Its "code space" (the dimer manifold) is not even invariant under the ideal Hamiltonian.

### 5.3 Results (3×3 exact density matrix; full table in `data/gauss_law_mitigation.txt`)
Bias = estimate − noiseless value. Cost = shot multiplier for equal statistical error.
Targets: m = initial-pattern memory, NNN⟨ZZ⟩, and farthest-pair ⟨n_a n_b⟩.

| channel, p, t | target | raw | Gauss postselect (cost) | self-mit, oracle floor (cost) | ZNE λ=1,2,3 (cost 57×) |
|---|---|---|---|---|---|
| depol 1e-3, t=10 | NNN⟨ZZ⟩ | −0.113 | **−0.023** (1.16×) | −0.030 (1.24×) | −0.003 |
| depol 1e-3, t=10 | m | +0.103 | +0.041 | +0.070 | +0.005 |
| depol 1e-3, t=3.25 | m | +0.0002 | +0.003 | **+0.017 (worse)** | 0.000 |
| depol 1e-2, t=3.25 | m | −0.014 | +0.024 | **+0.182 (13× worse)** | +0.014 |
| bit-flip 1e-3, t=10 | NNN⟨ZZ⟩ | −0.144 | **−0.019** (1.23×) | −0.023 (1.38×) | −0.004 |
| dephasing 1e-3, t=10 | NNN⟨ZZ⟩ | −0.046 | −0.031 (1.02×) | −0.044 (1.00×) | −0.003 |
| dephasing 1e-2, t=10 | m | +0.336 | +0.323 | +0.335 | +0.093 |
| noiseless, t=10 | NNN⟨ZZ⟩ | 0 | **+0.0135** (physics-floor bias, keeps 0.979) | — | — |

The 3×4 trajectory cross-check (p = 3e-3, t = 10, ±1 SE) agrees qualitatively:
- postselection cuts the NNN⟨ZZ⟩ bias from −0.198 ± 0.009 to +0.015 ± 0.001 (depolarizing), and from −0.268 ± 0.008 to +0.015 ± 0.001 (bit-flip);
- **under dephasing it only flips the sign, from −0.016 to +0.015 ± 0.001.** The residual is the physics floor, not noise.

What the data say:
1. **Postselection on D = 0 is the only Gauss-law method with a consistent benefit, and only against X/Y-type noise.**
   For spin correlators it gives 2–8× bias reduction at 1.1–1.8× cost (p ≤ 3e-3). It is **bounded below by the physics floor**,
   which is about 0.01 here: the same size as its residual at p = 1e-3. Its acceptance falls with system size even without noise.
   Against dephasing it does essentially nothing.
   For the dimer–dimer target the gain is at most about 1.5× and sometimes negative (bit-flip 3e-3, t = 10: 0.039 → 0.040).
   At early times, when the raw bias is already small, postselection can add bias: m goes from 0.0002 to 0.003 at depol 1e-3, t = 3.25.
2. **Self-mitigation (global-depolarizing rescaling with F from the defect density, the draft's proposal) fails as a general
   method under local noise.** F_gauss does not equal the per-observable decay factor. For example, depol 1e-3 at t = 3.25 gives
   F_gauss = 0.965 while the true factors are 1.000 (m) and 0.962 (NNN⟨ZZ⟩). It therefore fixes some observables and makes others
   worse, by up to 13×. Under dephasing F_gauss ≈ 1, so it applies no correction at all.
   The "oracle" floor also requires classically simulating the very circuit, which is circular at sizes where the hardware matters.
   The "naive" floor = 0 variant behaves the same here.
   (`test_estimators_are_exact_on_ideal_global_depolarizing` confirms the estimator is exact *if* the noise were global
   depolarizing. The failure comes from the noise model, not the code.)
3. **ZNE (idealised noise scaling) has the lowest bias** for p ≤ 3e-3. However, its 57× shot cost makes its total error at 10⁴ shots
   comparable to postselection's at low p, and it degrades at p = 1e-2, t = 10. Idealised amplification flatters ZNE.
4. **PEC** is unbiased but costs γ² = 4.2 on 3×3 at p = 1e-3. At the reference scale (54 qubits, 40 steps) that becomes
   **5.7×10³** at p = 1e-3, 1.9×10¹¹ at 3e-3, and 4×10³⁷ at 1e-2. This is not viable beyond p ≈ 1e-3 under this per-step model.
5. **Exact-symmetry methods do not apply to this quench** [derived].
   - The TFIM's only exact internal symmetry is P = Π X (plus lattice symmetries and energy).
   - A Z-basis product initial state has ⟨P⟩ = 0. It is not a P eigenstate, and Pauli channels keep ⟨P⟩ = f·0 = 0.
   - So symmetry verification/expansion (Cai, arXiv:2101.03151) has no sector to project onto, and GUESS-style learning from a
     symmetry decay (arXiv:2603.13060) has no decaying signal from P.
   - Symmetry-adjusted classical shadows (arXiv:2310.03071) target U(1), which the TFIM lacks.
   - Energy-based variants (⟨H⟩ is conserved up to Trotter error) were **not tested**.

   This absence of a usable exact symmetry is the real reason an emergent one is tempting. It does not make the emergent one work.

### 5.4 Verdict (yes/no-and-where)
- **Error correction: NO for the passive emergent constraint.** There is no code: distance 1, no syndrome-to-recovery map, and the
  constraint is violated by the ideal dynamics itself. *(Scope qualifier, review/06 A4: this is about the bare emergent constraint.
  Separately, with added ancillas coupled to the local generators + mid-circuit measurement + feedback, Z₂-LGT bit-flip correction
  has been demonstrated in 1+1d — arXiv:2405.18504 [established]. That is an engineered monitored scheme this project did not model,
  not correction from the emergent constraint; it does not change the NO for the passive case.)*
- **Error detection / postselection: a qualified, modest YES, only where residual errors have a substantial X/Y (bit-flip-type)
  component.** It gives a 2–8× bias reduction on spin correlators at p ≤ 3e-3 on 9–12 sites, floored at O((h/J)²) bias, with acceptance
  that worsens with size even without noise. **NO where errors are dephasing-dominated.** *(The acceptance falling with size here is a
  property of a **distance-1 constraint with a physics floor**, not an inherent limit of postselection — in genuine topological
  (finite-distance) codes postselection accuracy gains can instead be scalable with size, arXiv:2510.05222 [fetched]; the dimer
  manifold is weak specifically because it is not a stabilizer code. The bias-floor-vs-acceptance-cost tradeoff measured here has been
  formalized as certified finite-shot operating windows, arXiv:2606.15464 [fetched].)*
- **Self-mitigation by depolarizing rescaling from the defect density: NO as a general method.** It is unreliable whenever the
  noise is local rather than global depolarizing. It can help only observables that happen to decay like the defect density, and
  one cannot know which those are without the ideal answer.
- **Where (platforms): undetermined by this study.** The answer hinges on the X/Y fraction of each platform's *residual* channel
  (after twirling and any error detection), and no hardware data was used.
  - The draft's ranking (neutral atoms best, H2 worst) and its claim that H2's post-Iceberg residual is ZZ-dominated are **[unverified]**.
    This study is consistent with them only conditionally: *if* a platform is dephasing-dominated, Gauss-law methods are ineffective there.
  - Loss and erasure (neutral atoms) are outside the Pauli model and remain **open**.
  - *Emergent-approximate vs engineered syndrome [review/06 01-4, source verified 2026-10-06].* Gauss-law postselection **has been
    realized on H2**: a measurement-based simulation of the (2+1)d Z₂ gauge theory on H2 extracts one-form-symmetry syndromes from the
    measurement record "at no additional cost" and postselects to strongly suppress Gauss-law violations (Sukeno, Rinaldi, Okuda,
    arXiv:2608.04290 [established — abstract; body not read]). Two caveats keep this from overturning anything here: (i) that syndrome is
    **engineered** (an exact one-form symmetry of a resource state), not the project's **emergent/approximate** dimer constraint; and
    (ii) a successful Gauss-law postselection demonstration *on H2* is in tension with the draft's unverified "H2 worst" ranking — so
    that ranking should be treated as **[unverified] and contested**, not adopted. The platform verdict stays "undetermined," now with a
    concrete data point that the mechanism works on the project's target hardware for an engineered syndrome.
- Compared with the alternatives at reference scale: postselection is cheap but weak and floored. ZNE is the practical baseline
  (which the reference itself used, **[fetched]**). PEC is unaffordable beyond p ~ 1e-3.

### 5.5 Limits of this assessment
- Cluster sizes are tiny: 3×3 (exact) and 3×4 (trajectories), against the reference's 9×6. Size trends are **[inferred]**.
- There is one noise placement (per Trotter step, per qubit), and ZNE scaling is idealised.
- The draft's own numbers (per-Pauli ε ≈ 0.68 against 0.011–0.023, Cai Eq. 40 numerics, calibration transfer, the "2–7×, up to 24×" gains)
  were **not reproduced and remain [unverified]**.
- Our nearest analogue is the X/Y detection probability 0.46–0.54 and the Z response being about 70× weaker. These are the same
  qualitative asymmetry, but the quantities are not identical.
- **Active gauge protection is not modelled [fetched; review/06 A12].** This study uses the emergent constraint *passively* (measure
  defects, postselect/rescale). Adding a defect-penalty / pseudo-generator term to the simulated Hamiltonian to suppress leakage out
  of the dimer manifold before readout is an untested lever (energy-penalty protection: arXiv:2007.00668 / 2108.02203 / 2204.13709
  [fetched]); note those schemes protect mainly against *coherent* gauge-breaking, whereas our threat model is stochastic Pauli noise +
  Trotter leakage. Building it is a scope decision (review/06 K1), not part of this verdict.

## 6. Citation check of the draft's arXiv IDs (abstract pages fetched 2026-10-06)

All ten IDs **resolve** and match the draft's titles and authors:

| ID | title | authors |
|---|---|---|
| 2603.13060 | GUESS | Oliva del Moral et al., 13 Mar 2026 |
| 2604.11085 | emergent hierarchical symmetries for LGT protection | Fu, Zheng, Moessner, Bukov, Zhao |
| 2608.21103 | Symmetry constrained QEM for the Schwinger model | Tomlinson, Van Goffrier, Chakraborty, Cai, 21 Aug 2026 |
| 2508.17513 | RIDA | Miller, Soley |
| 2310.03071 | symmetry-adjusted classical shadows | Zhao, Miyake |
| 2101.03151 | Quantum Error Mitigation using Symmetry Expansion | Cai |
| 2203.08905 | Z₂ LGT confinement | Mildenberger et al. |
| 2101.01690 | global depolarizing mitigation | Vovrosh et al. |
| 2205.09247 | self-mitigating SU(2) Trotter | Rahman et al. |
| 2406.02501 | Quantinuum H2 56-qubit (states 99.843(5)% two-qubit fidelity) | DeCross et al. |

**Confirmed in full text by qc-researcher (research/04-gauss-law-citations.md, 2026-10-06):**
- 2203.08905 **does** use Gauss-law *postselection* (Methods §I.6; local Gauss law outperforms
  global-charge postselection) — **[established]**.
- the draft's quotes and the "5×10⁻⁵ crossover" attributed to 2608.21103 are confirmed near-verbatim
  (§IV–§V; p* ∼ 5·10⁻⁵) — **[established]**.

**Still [unverified]:**
- every per-experiment H2 number the draft attributes to 2503.20870 beyond those fetched in §1
  (hardware numbers; no hardware data used here).
- the reference's exact winding orientation/sign, which axis is its "9" in 9×6, and its C_r pair
  convention — **unverifiable from source** with current tooling (2503.20870 v3 PDF/Supplement not
  renderable; HTML truncates before §V; ar5iv hosts only the pre-triangular v1). These keep the
  [inferred]/[unverified] tags on the §2 winding normalization and C_r pair convention. A human with
  the v3 PDF/Supplement can close them.

## 7. What the reviewer must verify
- That the identities in §3 are proved, not merely tested (proof sketches are inline above), and that the tests cover them exhaustively.
- That the h² scaling is a fit to data (`data/gauss_law_scaling.txt`) and that the stripe prefactor matches first-order theory.
- That §5 separates the physics floor (noiseless rows) from the noise signal, under the stated model, with shot-noise error bars.
- That no platform claim is made beyond the conditional statement in §5.4.

### Convention status (resolved 2026-10-06 by direct read of 2503.20870 v3 §V, research/04)
- **Resolved:** the reference's winding axis ("9" = L_x) and sector labels (max (18,6), min (0,0)) are confirmed; our
  3-sublattice (0,0) and stripe |𝒲_x|=18 match; only the 𝒲_y sign is a (harmless) orientation convention.
- **Open follow-up (minor):** `dimer_correlation_by_distance` bins by Euclidean midpoint distance, but reference Eq. (6)
  uses the dual-lattice **graph distance** (vertices traversed on the shortest path). Switch the binning metric before
  comparing to the reference's C_r(s) curves. The connected-correlator definition itself already matches Eq. (6).
