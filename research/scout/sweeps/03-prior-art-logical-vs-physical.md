# Sweep 03 — Prior-art / novelty sweep for the ARTICLE THESIS (logical-vs-physical observables)

**Author:** qc-scout. **Date:** 2026-10-06. **Scope:** focused novelty sweep, notes only.
**North star tested:** `Conversation history/project-journal.md` ★ box / Entry 14; `docs/findings_vs_questions.md` Q1; `SCOPE.md` §2 Q1.

Status tags: **[established]** = primary text read (abstract verbatim and/or body); **[fetched]** = seen via
summary/snippet; **[unverified]** = secondhand only. No ID/DOI invented. Current host date 2026-10-06 — IDs
up to 2610.* (Oct 2026) are in the past/at-cutoff; none required are future-dated.

---

## 1. The single question

Has anyone already done — or come close to — the project's intended headline:
**compute the SAME physical TFIM (or close spin-model) observables with LOGICAL / error-detected / error-corrected
qubits and compare head-to-head against a PHYSICAL-qubit baseline, on hardware (ideally trapped-ion / Quantinuum H2)?**
The reproduction target 2503.20870 computes these observables on PHYSICAL qubits; logical-qubit work historically
runs QEC *benchmarks* or *simulation* without computing those physical observables. **Is that loop still unclosed?**

## 2. Search strategy actually used

- **Forward-citation hop from 2503.20870** via Semantic Scholar graph API (`/paper/arXiv:2503.20870/citations`,
  74 citing papers retrieved on the 2nd retry after 429s — [established] list obtained). Scanned every title for
  "logical / encoded / error-detect / fault-tolerant + Ising/magnetism".
- **Seed re-reads (then left):** 2602.22211 (beyond break-even) and 2504.21172 (Iceberg co-compilation) abstracts
  read in full to see whether they compute simulation observables logically-vs-physically.
- **Concept searches (web):** "error-detected quantum simulation Iceberg observables Quantinuum H2"; "logical qubit
  Ising dynamics observables comparison physical trapped ion"; "logical encoded TFIM magnetization fault-tolerant
  2026"; "digital quantum magnetism logical qubits error correction"; "logical vs physical observables encoded
  unencoded neutral atom superconducting advantage".
- **Cross-platform check:** neutral-atom and superconducting logical-simulation lines (megaquop architectures;
  IBM partially-FT simulation).
- **Could NOT fully exploit:** Semantic Scholar was rate-limited (429) on first attempts; forward-citation abstracts
  not pulled (titles+IDs only). The two IBM/UW competitor papers were found by concept search, not via the citation
  graph (they are hep-lat–classed and cite the physical-qubit line indirectly). I did not read the FULL body of the
  two closest competitors (2607.24947 / 2608.02944) — abstracts only; see "what I could not check".

---

## 3. The three buckets

### (A) CLOSES-THE-GAP / direct competitor — logical observables AND a physical-qubit head-to-head on hardware

- **arXiv:2607.24947** — "Realizing Error Suppression in Partially Fault-Tolerant Quantum Simulations with IBM
  Quantum Computers," Froland … Savage, Yao, Zemlevskiy et al., 27 Jul 2026. **[established — abstract]**.
  **The single most threatening source.** Encoded ([[4,2,2]] Iceberg, 21 blocks, 42 logical qubits on 136 physical
  heavy-hex qubits) **vs unencoded** simulation of the **Ising model in 1+1D and 2+1D**, estimating **local
  observables**, on **IBM `ibm_boston` superconducting hardware**. Reports the matched comparison explicitly:
  encoded beats unencoded by **2–6% at intermediate times in 1+1D, growing to >200% in 2+1D at late times**.
  Introduces "Observable-Ranked Postselection" to beat the shot-loss problem.
  *How close:* this IS the project's Q1 experiment — matched logical-vs-physical local-observable accuracy for the
  Ising model, encoded in the Iceberg code, on real hardware, with the cost/post-selection tradeoff quantified.
  *What it does NOT pre-empt:* (i) it is **superconducting (IBM), not trapped-ion / Quantinuum H2** — the H2 noise
  profile, all-to-all connectivity, and native 2-qubit fidelity are materially different; (ii) it uses the small
  **[[4,2,2]]** code, **not** the project's high-rate Iceberg [[k+2,k,2]] d=2 or **concatenated d=4**; (iii) it does
  **not** reproduce 2503.20870's specific TFIM observable set/geometry (9×6 torus, its M_z/variance/C_r conventions)
  as a named head-to-head against that Nature baseline; (iv) **no frustration / triangular lattice**. So the *generic*
  claim "encoded Ising simulation beats unencoded on hardware observables" is now **taken**; the *H2 + concatenated
  code + matched-to-2503.20870 + frustration* instantiation is not.

- **arXiv:2602.22211** (SEED — beyond break-even), Dasu, DeCross … Amaro, Quantinuum, 25 Feb 2026.
  **[established — abstract].** On the **98-qubit Quantinuum Helios** processor, demonstrates computations that
  **outperform their unencoded counterparts** in high-rate Iceberg [[k+2,k,2]] QED **and two-level concatenated
  Iceberg [[(k2+2)(k1+2),k2k1,4]] QEC** (48–94 logical qubits), with the benchmark suite including **"a pFT quantum
  simulation of the three-dimensional XY model of quantum magnetism."**
  *How close:* this is the project's OWN seed, and it already does **encoded quantum-magnetism simulation that beats
  unencoded on Quantinuum trapped-ion hardware, using exactly the project's code family (Iceberg d=2 + concatenated
  d=4).** It is the strongest evidence that the H2/Helios logical-vs-physical magnetism comparison is being actively
  occupied by the hardware vendor.
  *What it does NOT pre-empt:* model is the **3D XY model, not the TFIM**; it is a vendor **capability/break-even
  demonstration**, not a reproduction of 2503.20870's observables, not framed as a physics-observable-accuracy
  reproduction, and **no frustration / triangular physics / dimer observables.** The "beyond break-even on
  magnetism simulation" headline on H2-class hardware is, however, essentially already published by Quantinuum.

### (B) PARTIAL / ADJACENT — logical dynamics or logical observables, but not the matched TFIM-on-H2 comparison

- **arXiv:2608.02944** — "The Utility of Sparse Error Detection in Quantum Simulations," Froland et al.
  (same UW/IQuS group as 2607.24947), 3 Aug 2026. **[established — abstract].** Time evolution of the **lattice
  Schwinger model** embedded in Iceberg [[N+2,N,2]] and Hypercube [[2^N,N,2]] codes; **noisy classical simulation**
  (not hardware) with infrequent syndrome measurement + physics-aware postselection; finds error detection
  **improves observable estimation** and extra rounds "drive errors in observables to the noise floor set by the
  code." *Close on method (encoded dynamics observables + postselection floor — mirrors the project's own
  O((h/J)²) floor finding), but it is a different model (Schwinger LGT), simulation-only, no physical-qubit
  hardware head-to-head.* Pre-empts the generic "encoded-dynamics observables hit a code-set noise floor" message;
  does NOT pre-empt TFIM-on-H2 logical-vs-physical.

- **arXiv:2504.21172** — "Iceberg Beyond the Tip: Co-Compilation…," Jin et al. (JPMorgan + Quantinuum), v2 Apr 2026.
  **[established — abstract].** **QAOA** on the **Quantinuum H2-1**, Iceberg [[k+2,k,2]], shows **better-than-unencoded**
  success probability up to 34 algorithmic qubits (44%→65% at 22 qubits; post-selection 4%→33%). *Logical-vs-physical
  on H2 with the project's code — but the observable is a QAOA cost function (optimization), not TFIM dynamics
  observables, and not a reproduction of a physical-qubit physics baseline.* Strong methodological prior art for
  co-optimizing Iceberg gadgets with the algorithm; not a physics-simulation competitor.

- **arXiv:2509.25326** (SEED), "Error detection without post-selection in adaptive quantum circuits," Chertkov et al.
  **[fetched — title/role from SCOPE §11].** Error-detection method line (adaptive circuits), relevant to how the
  project could run logical observables without paying the full post-selection cost — adjacent method, not a matched
  TFIM observable comparison. (Not re-read in this sweep; already a project seed.)

- **arXiv:2408.10079** (from sweep 02), Floquet-circuit **error mitigation** on 38/116 qubits reaching early
  prethermalization — observables under mitigation, not logical encoding; adjacent only.

- **Megaquop-scale logical simulation architectures (neutral atom):** **arXiv:2509.18294** ("Transversal architecture
  for megaquop-scale quantum simulation with neutral atoms") and **arXiv:2606.25011** ("Fast and Parallel High-Rate
  STAR Architecture for Megaquop Quantum Simulation"). **[fetched — snippet].** These are *architecture/resource*
  proposals for logical simulation; they do not compute 2503.20870's observables logically-vs-physically on hardware.
  Confirm the field is racing toward exactly this, but none closes the matched-observable loop on TFIM.

### (C) CONFIRMS-GAP-OPEN — supports that the specific loop is still unclosed

- **arXiv:2503.20870** (SEED, reproduction target). **[established — abstract/role].** v2 title *"Digital quantum
  magnetism at the frontier of classical simulations"*; the published Nature version computes TFIM observables
  entirely on **physical** qubits — **no logical encoding, no logical-vs-physical comparison.** The gap it leaves is
  explicit by omission.
- **Forward-citation scan of 2503.20870 (74 citing papers, [established] list).** The ONLY citing paper that pairs
  the reproduction target with logical encoding is **2602.22211** (bucket A, XY not TFIM). The remaining 73 are
  classical-simulation competitors (e.g. **2511.19340** 2D-TFIM classical comparative numerics; **2602.02433**
  "triangular quantum magnet … hard quantum simulation target"; **2511.20388**; **2601.08772**), mitigation/benchmark,
  or unrelated. **No citing paper redoes 2503.20870's TFIM observables with logical qubits and compares to physical
  qubits.** This is the strongest direct evidence the exact loop is unclosed.
- Note on frustration spine (priority 2): **2602.02433** explicitly frames the **triangular quantum magnet** as a
  *hard quantum-simulation target* — supports the frustration angle's novelty but also warns referees see it as a
  known target.

---

## 4. VERDICT

**The gap is PARTIALLY OCCUPIED — and closing fast. Confidence: moderate-to-high on the generic claim, moderate on
the exact instantiation.**

- The **generic** headline — "compute matched physical-vs-logical (error-detected) observables for an Ising/spin
  model on hardware and show encoding wins" — is **already demonstrated**: on **IBM superconducting** for the Ising
  model (2607.24947, [[4,2,2]], 1+1D & 2+1D, local observables, 2–>200% accuracy gain) and on **Quantinuum Helios**
  for the **3D XY model** with the project's exact code family (2602.22211, Iceberg d=2 + concatenated d=4,
  beyond break-even). A referee can reasonably say "logical-beats-physical on quantum-magnetism observables" is done.
- The **specific** instantiation the project claims as its spine — **TFIM observables matched to 2503.20870, on
  Quantinuum H2, with the Iceberg/concatenated codes, extended to the frustrated triangular lattice** — appears
  **NOT yet published**: no forward-citation of 2503.20870 redoes it logically; the two closest competitors use a
  different platform (IBM), a different code ([[4,2,2]]), or a different model (XY, Schwinger, QAOA), and none adds
  frustration/dimer observables.
- **Therefore:** the project's novelty is **narrowing to the delta**, not the headline. Defensible remaining novelty
  = (i) **H2/trapped-ion** TFIM logical-vs-physical specifically matched to the 2503.20870 Nature baseline;
  (ii) the **concatenated-d=4** code on this problem; (iii) the **frustrated triangular lattice + dimer/winding
  observables under encoding** (priority-2 spine) — which none of the competitors touch. The pure "logical beats
  physical on magnetism observables" framing is **largely pre-empted** and should NOT be the headline.

**What I could not check (caveats on confidence):**
- Did not read the FULL bodies of 2607.24947 or 2608.02944 — only abstracts; whether 2607.24947 happens to use the
  *exact* transverse-field Ising with 2503.20870's conventions, or a kicked/other Ising, is unconfirmed.
- Semantic Scholar citation abstracts were not pulled (rate limits) — I scanned titles only; a mis-titled TFIM-logical
  paper could be hidden among the 74.
- Did not sweep very recent (Sep–Oct 2026) non-arXiv or vendor-blog preprints; a Quantinuum H2 TFIM-logical note could
  exist outside this net.
- 2509.18294/2606.25011 read at snippet level only.

---

## 5. Single most threatening competitor

**arXiv:2607.24947** (Froland et al., IBM partially-FT encoded Ising simulation, Jul 2026). It is the closest
published realization of the project's Q1 experiment — matched encoded-vs-unencoded local-observable accuracy for the
Ising model in 1+1D AND 2+1D with the Iceberg code on hardware. Its existence means the project must position its
contribution as the **trapped-ion / H2 + concatenated-code + frustration** delta, and must cite and differentiate
from it explicitly rather than claiming the comparison itself as new. (Second-most threatening: the project's own
seed 2602.22211, which already shows beyond-break-even encoded *magnetism* simulation on Quantinuum hardware.)

---

## 6. "What should change" — recommendations for the overseer (NOT auto-applied)

1. **Reframe the Q1 headline.** The ★ box claim "nobody has closed the loop (same observables, logical vs physical,
   same H2 tooling)" is now **too strong as written** — 2607.24947 closes it generically on IBM, and 2602.22211
   closes the beyond-break-even-on-magnetism loop on Quantinuum. Recommend the headline move from *"first logical-vs-
   physical observable comparison"* to *"first **TFIM** logical-vs-physical comparison **on trapped-ion H2, matched to
   the 2503.20870 Nature baseline, with concatenated-d=4 encoding, extended to the frustrated triangular lattice."*
2. **Add both competitors to the project's related-work / Q1 differentiation** as mandatory citations:
   2607.24947 (platform=IBM, code=[[4,2,2]], model=Ising, result=encoded wins) and 2602.22211 (platform=Helios,
   codes=Iceberg+concat, model=3D-XY, result=beyond break-even). Build the Q1 comparison table to explicitly contrast
   platform / code / model / observable set against these.
3. **Elevate the frustration spine (priority 2) in the novelty argument.** The triangular-lattice + dimer/winding
   observables under logical encoding is the part NO competitor touches (2602.02433 only names it as a hard target).
   Recommend the referee-facing novelty rest more heavily here than on the bare logical-vs-physical claim.
4. **Before any H2 campaign**, verify by reading the FULL bodies of 2607.24947 and 2608.02944 whether their
   "Ising/Schwinger" setups coincide with the project's TFIM conventions — this changes how much of Q1 is left.
   This is a verification task for qc-researcher, not scout.
5. **Do not graduate** any of these into project claims yet; this is discovery/triage only.

---

## 7. Most important source a human should read next

**arXiv:2607.24947 (full PDF).** Read it in full before committing credits to an H2 campaign: it tells you exactly
how much of the Q1 logical-vs-physical-observable story is already published, what "Observable-Ranked Postselection"
is (likely directly reusable), and precisely where the trapped-ion / concatenated-code / TFIM / frustration delta
begins. Then re-read 2602.22211 §(3D-XY simulation) for the Quantinuum-hardware precedent.

## 8. Open questions for Kevin / the overseer

1. **Is the H2 campaign still worth the credits** if the generic logical-beats-physical-on-magnetism result is
   already published (IBM) and already shown on Quantinuum hardware (2602.22211, XY)? Is the TFIM + trapped-ion +
   concatenated + frustration delta a strong enough referee-facing contribution on its own?
2. **Should the paper's spine shift** from Q1 (logical-vs-physical) toward Q2 (frustration/dimer under encoding),
   given Q2 is the least-pre-empted piece?
3. **Does 2607.24947's "Observable-Ranked Postselection"** supersede or complement the project's own postselection
   analysis / the Gauss-law postselection thread? (Needs full-text read.)
4. Confirm 2607.24947's exact Ising Hamiltonian vs the project's TFIM conventions — overlap determines residual novelty.
