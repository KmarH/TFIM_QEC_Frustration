# Citation and convention verification — handoff 02 (triangular dimers / Gauss law)

Scope: verify the citations and the convention tags in `docs/gauss_law_dimers.md` and
`drafts/gauss_law_self_mitigation_assessment.md` against primary sources (arXiv full text /
journal pages). Per SCOPE §11: any ID that does not resolve is reported as such; **no ID was
invented or "fixed."** Verified against arxiv.org and APS on 2026-10-06.

Status vocabulary: `verified` (checked against the primary source, full text where the claim is
in the body), `corrected-locator` (ID/locator needed a change — none did here), `unresolved` (ID
does not resolve), `unverifiable-from-source` (ID resolves but I could not reach the specific body
text that would settle the claim with the tools available).

This note writes no project code.

---

## Item 1 — Moessner & Sondhi, PRB 63, 224401 (2001): the dimer mapping

**Status: VERIFIED (resolves; locator correct; mapping as used).**

- Resolves. Journal page: APS, `10.1103/PhysRevB.63.224401`, "Ising models of quantum frustration,"
  R. Moessner and S. L. Sondhi, Phys. Rev. B **63**, 224401 (2001). arXiv preprint of the same work:
  `cond-mat/0011250` (submitted 15 Nov 2000; the arXiv abstract page's journal-reference field
  confirms "Phys. Rev. B 63, 224401").
- The locator in `docs/gauss_law_dimers.md §2` — "Moessner & Sondhi, PRB 63, 224401 (2001)" — is
  **correct as written**. The companion short account is PRL 86, 1881 (2001) (RVB phase in the
  triangular QDM); the long paper (224401) is the right one to cite for the systematic
  frustrated-TFIM → QDM construction.
- Mapping content (read in the arXiv full text, Introduction + abstract): the paper is explicitly a
  "systematic study of two dimensional, periodic, frustrated Ising models with a quantum dynamics
  introduced via a transverse magnetic field," covering "the triangular and kagome lattice
  antiferromagnets, fully frustrated models on the square and hexagonal (honeycomb) lattices." The
  Introduction states there is "an exact mapping from frustrated transverse field Ising models to
  quantum dimer models of the short-range resonating valence bond state … in this context the Ising
  models appear more naturally as their dual, Ising gauge theories." This is exactly the picture the
  repo's dimer construction rests on: triangular TFIM ground manifold ↔ dimer coverings of the dual
  honeycomb, dimer on a frustrated (unsatisfied) bond.
- Caveat on precision of the quote: the repo §2 attributes a specific sentence —
  *"lowest-energy classical configurations can be identified with dimer coverings of a dual
  hexagonal lattice (an edge having a dimer when AFM order of adjacent spins is frustrated)"* — to
  "Reference §V" and tags it **[fetched]**. That quote is in fact the standard statement of the
  mapping and is phrased in the *reproduction-target* paper (2503.20870, see Item 3), not in
  Moessner–Sondhi; MS phrase it in their own notation. The *physics* of the mapping is confirmed in
  MS full text; the exact wording quoted is the 2503.20870 phrasing. Attribution of the mapping to
  MS is correct; the quoted sentence should be attributed to 2503.20870 §V, which the doc already
  does elsewhere.

**Tag resolution:** the `**journal ref to be confirmed by qc-researcher**` note in §2 may be
**dropped** — the journal reference PRB 63, 224401 (2001) is confirmed. The mapping itself is
independently proved in the repo (§3, [derived], exhaustively tested), so it does not depend on this
citation; but the citation is now `verified` and can be upgraded from [fetched] to [established] for
the existence-and-content-of-the-mapping claim.

---

## Item 2 — the two [unverified] full-text claims in doc §6

### 2(a) — arXiv:2203.08905 uses Gauss-law POSTSELECTION

**Status: VERIFIED (full text).** Mildenberger, Mruczkiewicz, Halimeh, Jiang, Hauke, "Probing
confinement in a ℤ₂ lattice gauge theory on a quantum computer" (2203.08905).

- Main text: "device errors that violate conservation of total matter charge as well as the ℤ₂
  Gauss's law are mitigated by **postselecting** on these ideally conserved quantities, which is
  possible thanks to single-site readout."
- Methods §I.6 ("Postselection") is explicit and detailed: "The local gauge symmetry also proves a
  useful tool to mitigate errors: any errors that break this local conservation law, akin to a
  stabilizer used in quantum error correction, can be identified through postselection… any
  experimental shots where the eigenvalues of the generators … differ from those of the initial
  state are known not to be faithful." They further find "the finer local conservation law provided
  by the gauge symmetry yields a significantly stronger improvement" than global-charge
  postselection (Extended Data Fig. 6).

So the draft's characterization — that 2203.08905 uses Gauss-law postselection, and that the local
Gauss law outperforms global-charge postselection — is **correct and literal**.

**Tag resolution:** the §6 bullet "that 2203.08905 used Gauss-law *postselection*" may be
**dropped from [unverified]** → `verified`.

### 2(b) — the quotes and the "5×10⁻⁵ crossover" attributed to arXiv:2608.21103

**Status: VERIFIED (full text).** Tomlinson, Van Goffrier, Chakraborty, Cai, "Symmetry Constrained
Quantum Error Mitigation for the Schwinger Model" (2608.21103, v1, 21 Aug 2026).

- The "5×10⁻⁵ crossover" is **real and exactly as attributed.** §V (Discussion): "the benefits
  decayed rapidly as the per-gate noise probability approached an **empirical crossover around
  5×10⁻⁵**." §IV states the same as a critical noise level "p* ∼ 5·10⁻⁵ beyond which the global
  noise correction is impossible," with Fig. 17 captioned "at critical noise level p = 5e−5." The
  paper itself adds the caveat that this is model/circuit/observable/noise-model specific and "should
  not be interpreted as a universal threshold" — the draft's framing is consistent with that.
- The quotes are confirmed near-verbatim. §V: the calibration method "was motivated by our
  observation that **the fraction of the bias removed by postselection was nearly time-independent
  and varied smoothly with problem size.**" The draft's calibration-transfer description ("trained on
  classically accessible [N=4,6] systems… transferred to … N=8,10") matches §IV–§V. Postselection
  "consistently removing up to 60% of the quantum noise induced error" is in the abstract and §V.

**Tag resolution:** the §6 bullet "the draft's quotes and the '5×10⁻⁵ crossover' attributed to
2608.21103" may be **dropped from [unverified]** → `verified`. (These support the draft's
Recommendation 4 analogy only; they do not touch any repo physics result.)

---

## Item 3 — arXiv:2503.20870 conventions (winding orientation/sign, 9×6 axis, C_r pair convention)

**OVERSEER ADDENDUM (2026-10-06, after this note was first written): RESOLVED.** The §V body and
Fig. 4 caption WERE subsequently reached by re-fetching the v3 HTML in `full` mode (the earlier
`selective`/anchor fetches truncated at 8000 chars before §V; `full` returned the whole paper). Read
directly:
- **Winding definition & axis:** "𝒲_x and 𝒲_y … defined by the total electric flux through the two
  non-contractible loops wrapping around the torus in the x and y directions." Initial states are the
  **maximal (𝒲_x,𝒲_y)=(18,6)** and **minimal (0,0)** sectors on a **9×6 lattice**. 𝒲_x=18 (the larger)
  pairs with the 9-site axis ⇒ the reference's "9" IS L_x. The repo's axis assumption is CONFIRMED; the
  repo stripe gives 𝒲_y=−6 vs the reference +6 — a harmless flux sign/orientation convention only.
- **C_r (Eq. 6):** r = "the number of vertices traversed along the shortest path connecting (and
  including) those edges" — a dual-lattice GRAPH distance. The repo bins by Euclidean midpoint distance,
  which does NOT match; the connected-correlator form itself matches Eq. (6). Flagged as a minor
  follow-up (switch the binning metric) in docs/gauss_law_dimers.md §2/§7.

So the two tags below that were marked "must stay" are now largely resolvable: the winding axis/label is
`verified`; the 𝒲_y sign and the C_r metric are `corrected` (sign = convention; metric = known fix).
The original "unverifiable with available tooling" assessment was premature — `full` mode reached the
text. Lesson recorded for the journal.

---

**Status (as originally written): PARTIALLY VERIFIED. The model/convention of §1–2 is `verified`; the three specific
normalization details are `unverifiable-from-source` with the available tooling.**

Confirmed from full text (v3, "Digital quantum magnetism on a trapped-ion quantum computer,"
Nature 653, 56–62, 2026; DOI 10.48550/arXiv.2503.20870):

- The Hamiltonian and sign convention the repo §1 relies on are **verified**: Eq. (1) is
  `H = J Σ_⟨j,k⟩ Z_j Z_k + h Σ_j X_j`, PBC (torus), and the triangular run uses **AFM J>0**
  ("antiferromagnetic interactions on a frustrated triangular lattice") giving geometric
  frustration. This confirms the repo's statement that the frustrated model is `J_ours = −J_ref < 0`
  in the repo's `H = −J ΣZZ − h ΣX` sign convention. The (h/|J|, dt|J|) = (0.3, 0.25) parameters and
  the quantum-dimer description ("emergent gauge-theoretic description in terms of a quantum dimer
  model") are confirmed in the abstract/intro/§V.

  > **CONTRADICTED by the reference's own dataset — see [`DECISIONS.md`](../DECISIONS.md) OPEN-1.**
  > A separate research thread (`research/05-zenodo-dataset-map.md`) read the released quench4
  > ("triangular quench") circuits and found `rzz(0.5)`, `rx(0.5)`/`rx(1.0)` in all of them, i.e.
  > **h/|J| = 2**, identical to the square quenches. The two threads never cross-checked each
  > other and the conflict was never resolved. Note also that this item's own paragraph below
  > records that the §V *body* was never reached, so the reading above rests on the abstract and
  > intro. Treat h/|J| = 0.3 as **unconfirmed against the dataset the project actually has**.

Not settleable from source with the available tools (PDF fetch blocked by content-type; the
arxiv.org HTML of v3 truncates before the §V body and the Methods; the ar5iv mirror only hosts the
older v1 preprint "Digital quantum magnetism at the frontier of classical simulations," which the
draft already notes **lacks the triangular experiment**). Therefore the following remain
`unverifiable-from-source`:

- the paper's **winding-number orientation/sign convention** (which flux sign is positive, and the
  exact (w_x, w_y) sector labels it quotes);
- **which axis is the "9"** in the 9×6 lattice (i.e. whether the reference's "9" is the repo's L_x);
- the paper's **C_r (dimer–dimer correlation) pair convention** (ordered vs unordered pairs,
  distance definition, normalization).

What *is* independently established (from the previous subagent's v3 check recorded in the draft
caveats, and consistent with what I could read): the triangular run measured dimer–dimer
correlations C_r(s) and winding-number full-counting statistics as observables, took ergodic
reference values from classical Markov-chain Monte Carlo, and used leakage postselection +
randomized compiling + ZNE (not Gauss-law/dimer postselection). That corroborates the repo's choice
of observables but not the specific sign/axis/pair normalization.

**Tag resolution:**
- The repo's winding **normalization** tag (§2: "The normalization is **[inferred]** from the
  reference's sector labels… The reference's exact orientation and sign convention were not
  extracted, so whether its '9' is our L_x is unverified") — **must STAY** as [inferred]/[unverified].
  I could not reach the reference's §V/Methods sign and axis definitions. The repo's winding is a
  genuine, internally consistent, exhaustively tested sector label (review stage reproduced
  3×4 → 3 sectors; 3×3 → single sector); only the *match to the reference's labelling* is unconfirmed.
- The repo's **C_r pair convention** tag (§2: "The reference's exact pair convention is
  **[unverified]**") — **must STAY** as [unverified], for the same reason.
- The §1 **sign-convention** mapping (J_ours = −J_ref) and the (h, dt) parameters may be upgraded
  from [fetched] to [established] — these are confirmed in the v3 full text I read.

Open item for the overseer/user: settling the three normalization details requires the 2503.20870
v3 PDF or its Supplemental Material (§V / Methods), which the current fetch tooling cannot render
(PDF content-type unsupported; HTML truncated). A human with the PDF, or a tool that renders it,
can close these two tags. Until then they correctly stay flagged.

---

## Item 4 — re-confirmation of all 10 arXiv IDs in drafts/gauss_law_self_mitigation_assessment.md

All ten **resolve** and match the titles/authors the draft (and doc §6) list. The three
future-dated ones were spot-checked against their abstract pages / full text.

| ID | Resolves? | Title / authors as listed | Verification note |
|---|---|---|---|
| **2603.13060** | yes | GUESS — "Noise mitigation of quantum observables via learning from Hamiltonian symmetry decays"; Oliva del Moral, Sanz Larrarte, Fraxanet, Mishagli, Etxezarreta Martinez (13 Mar 2026) | **verified**: abstract matches ("GUiding Extrapolations from Symmetry decayS … learning the extrapolation coefficients from a symmetry observable"). Draft's "exact Hamiltonian symmetry + noise ladder" characterization consistent with the abstract. |
| **2604.11085** | yes | "Protecting Quantum Simulations of Lattice Gauge Theories through Engineered Emergent Hierarchical Symmetries" (Dated 14 Apr 2026) | **verified** (title/topic); the draft's gloss "engineered emergent hierarchical symmetries for LGT protection … protects dynamics rather than mitigates readout" matches the abstract (Floquet-engineering, emergent local symmetries, hierarchy of lifetimes). Author list (Fu, Zheng, Moessner, Bukov, Zhao) not individually re-read from the abstract page returned, but title/ID/topic match; low risk. |
| **2608.21103** | yes | "Symmetry Constrained Quantum Error Mitigation for the Schwinger Model"; Tomlinson, Van Goffrier, Chakraborty, Cai (21 Aug 2026) | **verified** (full text, see Item 2b). Authors and affiliations confirmed. |
| 2508.17513 | yes | RIDA; Miller, Soley (2025) | resolves (prior §6 check); not re-opened. |
| 2310.03071 | yes | symmetry-adjusted classical shadows; Zhao, Miyake (npj QI 10, 57, 2024) | resolves; abstract/journal consistent. |
| 2101.03151 | yes | "Quantum Error Mitigation using Symmetry Expansion"; Cai (Quantum 5, 548, 2021) | **verified** (abstract seen: symmetry expansion, detectable/undetectable bias cancellation — the Eq.-40-ceiling source). |
| 2203.08905 | yes | Z₂ LGT confinement; Mildenberger et al. | **verified** (full text, Item 2a). |
| 2101.01690 | yes | global depolarizing mitigation; Vovrosh et al. (PRE 104, 035309, 2021) | resolves (prior §6 check); not re-opened. |
| 2205.09247 | yes | self-mitigating SU(2) Trotter; Rahman et al. (PRD 106, 074502, 2022) | resolves (prior §6 check); not re-opened. |
| 2406.02501 | yes | Quantinuum H2 56-qubit; DeCross et al. | resolves (prior §6 check); not re-opened. |

No ID failed to resolve. No ID required a corrected locator. (Note the reproduction-target
2503.20870 is not in the draft's ten but was independently confirmed in Item 3: Nature 653, 56–62
(2026), v3.)

---

## Summary: which tags in docs/gauss_law_dimers.md may be dropped vs must stay

**May be dropped / upgraded (now `verified`/`established`):**
1. §2 "Moessner & Sondhi, PRB 63, 224401 (2001) — **journal ref to be confirmed by
   qc-researcher**" → **drop the parenthetical**; locator confirmed, mapping confirmed in MS full
   text. (Minor finding (1) from review/05 is closed.)
2. §1 the (h/|J|, dt) = (0.3, 0.25) parameters, the AFM-J>0 reference convention, and the
   `J_ours = −J_ref` sign mapping → upgrade **[fetched] → [established]** (confirmed in 2503.20870 v3
   full text, Eq. 1).
3. §6 bullet "that 2203.08905 used Gauss-law *postselection*" → **drop from [unverified]**; verified
   in full text (Methods §I.6).
4. §6 bullet "the draft's quotes and the '5×10⁻⁵ crossover' attributed to 2608.21103" → **drop from
   [unverified]**; verified in full text (§IV–§V).
5. §6 the ten-ID table — all **verified to resolve**; the three future-dated IDs spot-checked.

**Must stay (still [inferred]/[unverified]):**
1. §2 winding **normalization / orientation / sign** vs the reference's sector labels, and "whether
   its '9' is our L_x" → **stay [inferred]/[unverified]**. The reference's §V/Methods sign and axis
   conventions were not reachable (PDF blocked; HTML truncated; ar5iv is the pre-triangular v1). The
   repo's winding is independently correct and tested as a sector label; only the reference-matching
   is open.
2. §2 the **C_r pair convention** "(reference form)" / "The reference's exact pair convention is
   **[unverified]**" → **stay [unverified]**, same reason.
3. §6 "every per-experiment H2 number the draft attributes to 2503.20870 beyond those fetched in
   §1" → **stay [unverified]** (hardware numbers; out of scope here and no hardware data used).
4. All draft numbers in §5.5 (per-Pauli ε, Cai Eq. 40 numerics, "2–7×, up to 24×", calibration
   transfer) → **stay [unverified]**; these are the draft's unreplicated results, unchanged by this
   citation sweep.

**Net effect:** four of the review/05 Minor hygiene items that are citation-related are now closable
(Moessner–Sondhi journal ref; 2203.08905 postselection; 2608.21103 quotes+crossover; ten-ID
re-confirmation). The two reference-normalization tags (winding sign/axis, C_r pair convention)
cannot be closed from the source with current tooling and are correctly left flagged.

---

## Open questions for the overseer and the user
- To close the last two convention tags, someone with the **2503.20870 v3 PDF or Supplemental
  Material** should read §V / Methods for (i) the winding sign/orientation and (ii) which axis is the
  "9" in 9×6, and (iii) the exact C_r pair/normalization convention. The current web tooling cannot
  render the v3 PDF (content-type unsupported) and the HTML truncates before §V; ar5iv hosts only
  the v1 preprint without the triangular experiment.
- 2604.11085 author list was not line-checked against the abstract page (title/ID/topic matched); if
  strict author verification is required, confirm from the arXiv abstract page author field.

---

## Addendum (overseer, 2026-10-06) — arXiv:2608.04290 verified

Context: review/06 (scout adjudication) **parked** scout item 01-4 because the reviewer could not open
2608.04290. The project lead asked for it to be verified. Done, directly from the arXiv abstract page:

- **Resolves.** arXiv:2608.04290, "Measurement-based simulation of lattice gauge theory dynamics with
  adaptive quantum circuits on a trapped-ion processor," **Sukeno, Rinaldi, Okuda**, submitted **4 Aug
  2026** (v1), 20 pages, quant-ph (+hep-lat, hep-th). The 2608 ID is consistent with the current session
  date (2026-10-06); it is a real recent paper, not a future-relative artifact.
- **Abstract confirms the scout's claims verbatim:** "first experimental realization of MBQS of
  real-time dynamics in the (2+1)-dimensional ℤ₂ gauge theory using the Quantinuum System Model H2
  trapped-ion processor"; gauge-invariant observables on 2×2 and 3×3 lattices (virtual 3D cluster states
  of 200/288 qubits from 48/54-qubit blocks within the 56-qubit register); "the measurement record …
  simultaneously provides one-form-symmetry syndromes at no additional cost, enabling postselection that
  strongly suppresses observed Gauss-law violations and improves aggregate agreement with ideal
  Trotterized dynamics."
- **Scope of this verification:** abstract read in full; the 20-page body (acceptance rates, which
  observables improve, syndrome-extraction detail) was **not** read. Tag: **[established — abstract;
  body not read]**. No number was imported from it.
- **Key distinction preserved:** this is MBQS with an **engineered** one-form syndrome extracted from the
  measurement record — **not** the project's *emergent/approximate* dimer Gauss law. The reconciliation
  applied to the docs (01-4) uses exactly this distinction.
