# Research Note 06 — H2 native-2Q-gate error composition: a published prior on η and ε

**Purpose.** Feed ★ FLAG-0 / HW-1. The classical sensitivity analysis
(`docs/encoded_tfim.md` → "Noise-model sensitivity"; `data/noise_sensitivity.txt`) shows the
go/no-go for encoding the TFIM on Quantinuum H2 FLIPS on two properties of H2's **native
two-qubit gate** error:
- **η** = fraction of each 2Q-gate error that is **Z⊗Z-type** (aligned with the logical ZZ
  rotation; crossover at **η ≈ 0.25**, exact for Iceberg; ×1.5 at η = 0.5);
- **ε** = **coherent over-rotation** angle of the native 2Q entangler (twirled stand-in
  sin²ε per gate), which erodes any gain toward ×1.

This note extracts the best **published prior** on (η, ε) for System Model H2 (H2-1 / H2-2), so
Claude Code can rerun `scripts/run_noise_sensitivity.py` at realistic values for a
**prediction-from-prior** go/no-go. **This is a prior, not a measurement.** Every noisy curve
in this project remains a classical prediction under an assumed model (KIRO.md hard rules).

**Status tags:** [established] stated in a source I read, with citation + location;
[inferred] my reasoned mapping, reasoning shown; [unverified] could not confirm; [assumed]
declared modelling choice.

**Provenance of this note [established].** I read the arXiv **HTML** full text + Supplement of
2503.20870v3 (downloaded to a scratch dir, tag-stripped, grepped; scratch deleted) and the
arXiv HTML of 2305.03828v2, plus both abstract pages. The PDFs were NOT needed — the HTML
Methods/SI rendered. I also **read Figure S3 of 2503.20870 as an image** (the cycle-benchmarking
Pauli-probability plot `cb_data_figure.png`); the η number below is a visual read-off of that
plot, tagged accordingly. No numbers or citations are invented. Project convention followed:
report non-resolving / future-dated IDs rather than trusting them (SCOPE §11; see §7).

---

## 0. Headline (the answer)

**[established] The native 2Q gate on H2 is the arbitrary-angle `U_ZZ(θ) = exp(−i θ Z⊗Z/2)`
partial entangler** (a phase-sensitive Mølmer–Sørensen gate wrapped in 1Q pulses). This is
exactly the gate our Iceberg logical-ZZ rotation and the parity-gadget `ZZPhase`s compile to —
so the η question is physically the right question.

**[inferred, from reading Fig. S3 of 2503.20870] The STOCHASTIC Z⊗Z fraction of H2's 2Q-gate
error is small: η_ZZ ≈ 0.04–0.05**, i.e. the ZZ Pauli term is among the *smallest* components
of the learned 2Q error channel, not the dominant one. The dominant stochastic 2Q error is
**IZ+ZI (single-qubit-Z / dephasing-type), ≈ 3×10⁻⁴**, with the ZZ term ≈ 3–5×10⁻⁵.

**[established] The COHERENT ZZ over-rotation ε exists in the model as a fit parameter `θ_ε`
(2503.20870 Eq. S7) but its NUMERICAL VALUE IS NOT PUBLISHED** in the text; it lives (if
anywhere) implicitly in the Fig. S3 fits, which are rescaled away. For the reference experiment
it is also **deliberately twirled into stochastic error by randomized compiling**, so a
"typical un-mitigated H2 coherent ZZ over-rotation" is **not separately published**.

**Predicted go/no-go [prediction-from-prior, NOT a measurement]:** on the published stochastic
Pauli channel, **η ≈ 0.04–0.05 ≪ 0.25**, which lands the project **BELOW** the crossover — i.e.
the prior predicts **encoding still helps** on H2's *stochastic* 2Q noise. The caveat that can
flip this is coherent ZZ over-rotation (ε), whose value is unpublished and which the reference
experiment removed by twirling. See §4–§6.

---

## 1. The native two-qubit gate [established]

- **2503.20870** (main text, below Eq. 2; S1.5): the Trotter ZZ layer is implemented with
  `U_ZZ(2Jdt) = exp[−i(Jdt) Z⊗Z]`, the **native arbitrary-angle gate**; both signs
  `U_ZZ(+θ)` and `U_ZZ(−θ)` are directly implementable and are *physically inequivalent gates
  with different error models* (S1.2). The specific gate used throughout is `U_ZZ(0.5)`
  (since `2Jdt = 0.5`). Matches `research/05` (`rzz(0.5)`, J·dt = 0.25) exactly.
- **2305.03828** (Moses et al., *A Race-Track Trapped-Ion Quantum Processor*, PRX 13, 041052
  (2023)), §II / Fig. 2–3: "2Q gates are implemented with a **phase-sensitive
  Mølmer–Sørensen (MS) gate** sandwiched between 1Q wrapper pulses … to generate the
  parameterized gate `U_ZZ(θ) = exp(−i θ ZZ/2)`." So the project's `ZZPhase` IS H2's native
  entangler; no CNOT-frame decomposition is needed for the Iceberg logical-ZZ and the bond
  rotations. [established]
  - **Mapping caveat (unchanged from `docs/encoded_tfim.md` model note):** for the d≥3 parity
    gadgets, the CNOTs are themselves compiled from `U_ZZ` + 1Q on H2, so applying the ZZ bias
    "in the CNOT frame" is an approximation; the crossover is exact only for Iceberg's bare
    `ZZPhase`. [inferred]

---

## 2. Published 2Q error MAGNITUDE (bounds total error, not η) [established]

Keep the skeptical prior: a fidelity bounds **total** 2Q error; by itself it gives **no** η.

| source | quantity | value | where |
|---|---|---|---|
| 2503.20870 abstract | native partial-entangler fidelity | **99.94(1)%** (⇒ ≈6×10⁻⁴ infid.) | abstract; main text "see SI IIB" |
| 2503.20870 S3 | avg 2Q gate infidelity, `U_ZZ(±0.5)`, over all expts | **6(1)×10⁻⁴** (low-T), **5.0(6)×10⁻⁴** (interm-T), **7.1(8)×10⁻⁴** (hydro) | S3, Fig. S7(c) |
| 2503.20870 S3 | pre-quench cycle-benchmarking infidelity | 7.3(7)×10⁻⁴ (H2-1 low-T); 7.9(9)×10⁻⁴ (H2-2 low-T); 5.5(5)×10⁻⁴ (hydro); 5.7(6)×10⁻⁴ (interm-T) | S3 |
| 2503.20870 S3 | triangular quench (expt d) avg 2Q infidelity | **3.3×10⁻⁴** | S3 |
| 2503.20870 S1.1 | 1Q gate infidelity | ~3×10⁻⁵ | S1.1 |
| 2305.03828 abstract | H2 launch (2023): 2Q infid / 1Q infid / SPAM | **1.84(5)×10⁻³** / 2.5(3)×10⁻⁵ / 1.6(1)×10⁻³ | abstract; §V |
| 2305.03828 §II | `U_ZZ(θ→0)` residual infidelity | ≈5×10⁻⁴, "predominantly laser phase noise and spontaneous emission" | §II, Fig. 3 |
| 2406.02501 (DeCross et al.) [unverified — from `drafts/`, not re-opened here] | H2 launch 2Q fidelity | 99.843(5)% | cited in `drafts/gauss_law_self_mitigation_assessment.md` |

So the current (2026) H2 2Q gate is ≈**5–7×10⁻⁴** total infidelity — a 3× improvement over the
2023 launch (1.84×10⁻³). **None of these numbers alone gives η.** [established]

---

## 3. The ZZ fraction η — the actual composition [the key result]

### 3a. Where the composition lives [established]
2503.20870 **S2.1** learns a per-gate error model for the sign-averaged `U_ZZ(±0.5)` gate via a
**non-Clifford cycle-benchmarking (pseudo-twirl)** variant. The learned model is explicitly
(S2.1, verbatim): *"a Pauli error channel composed with a coherent Z⊗Z rotation."* The decay
model (Eq. S7) is
> E(P_j)(l) = A·[f_j]^l for [P_j, ZZ]=0, and A·[f_j]^l·cos(θ_ε·l) for {P_j, ZZ}=0,
> where **θ_ε is a coherent ZZ error angle**.

This cleanly separates the two things we need:
- the **stochastic Pauli** probabilities p_j (→ η, the ZZ-type *stochastic* fraction), and
- the **coherent** ZZ over-rotation **θ_ε** (→ ε).

### 3b. The stochastic ZZ fraction, read off Fig. S3 [inferred — visual read-off of a plot]
Figure S3 plots p_j for each 2Q Pauli for `U_ZZ(±0.5)` (low-T panel a, interm-T panel b),
H2-1 and H2-2, before/after. I read the image directly. Approximate bar heights (units 10⁻⁴;
each label is the *sum* over the two listed Paulis):

| Pauli group | low-T p_j (×10⁻⁴) | interm-T p_j (×10⁻⁴) |
|---|---|---|
| IX+XI | ~1.2 | ~1.0 |
| IY+YI | ~1.3 | ~1.0 |
| **IZ+ZI (dominant)** | **~3.7** | **~3.3** |
| XX | ~0.1 | ~0.05 |
| XY+YX | ~0.1 | ~0.05 |
| XZ+ZX | ~1.3 | ~1.0 |
| YY | ~0.1 | ~0.05 |
| YZ+ZY | ~1.2 | ~1.0 |
| **ZZ** | **~0.5** | **~0.3** |

Σ p_j ≈ 9.5×10⁻⁴ (low-T) / 7.7×10⁻⁴ (interm-T) — consistent with the ≈6–7×10⁻⁴ *average* gate
infidelity (average infid = d/(d+1)·process infid, so Σp_j is the right order). [inferred]

**η_ZZ (stochastic) = p_ZZ / Σp_j ≈ 0.05 (low-T), ≈ 0.04 (interm-T).** [inferred, read-off]

- **Dominant error is IZ+ZI (~40% of the budget), i.e. single-qubit-Z dephasing-type**, not ZZ.
  This matches 2305.03828's attribution of the `U_ZZ` residual to laser phase noise, spontaneous
  emission and memory dephasing (§II; §III memory errors), none of which is ZZ-aligned.
  [established + inferred]
- **Uncertainty on the read-off:** bar heights have ~20–40% error bars in the figure and I am
  reading pixels. A conservative bracket is **η_ZZ ∈ [0.03, 0.08]**. Even the top of that bracket
  is **far below 0.25**. [inferred]
- **Caveat — this is the TWIRLED/stochastic ZZ fraction.** It is exactly the quantity our model's
  `zz_bias` represents (a stochastic Z⊗Z Pauli component, see §5). It does *not* include the
  coherent part, which the model handles separately as `overrot` (§4).

### 3c. 2305.03828 corroboration [established, qualitative]
The racetrack paper twirls `U_ZZ(θ→0)` over SU(2)⊗SU(2) and fits per-irrep decay rates
r_{II}, r_{IZ}=r_{ZI}=r₁, r_{ZZ}=r₂ (App. A.3, Eqs. 22–26). It reports only the aggregated
process/average infidelity numerically in the text, **not** a tabulated r_ZZ, so no independent
numeric η from this paper. But it independently establishes that the zero-angle `U_ZZ` error is
"predominantly laser phase noise and spontaneous emission" — incoherent/leakage, **not** a ZZ
over-rotation. [established]

---

## 4. The coherent over-rotation ε — not separately published [established as a gap]

- **Form is published** (2503.20870 Eq. S7): a single coherent ZZ angle θ_ε multiplies the
  anticommuting-Pauli decays. **The numeric value of θ_ε is NOT in the SI text** I read, and the
  Fig. S3 fits are *rescaled* to relative Pauli probabilities, so θ_ε is not recoverable from the
  figure. [established — "not separately published"]
- **The reference experiment removes most of it.** S1.2: randomized compiling (Pauli twirling,
  applied every two Trotter layers) *"partially converts the original 2Q gate error model into a
  stochastic Pauli error model."* S1.2 states the only coherent ZZ residual that survives
  twirling is a +θ/−θ *correlated* over-/under-rotation (S1.1 line: "if a coherent over-rotation
  by θ_ε in `U_ZZ(θ)` is correlated with an under-rotation by θ_ε in `U_ZZ(−θ)`, this error will
  still be present"). The surviving piece is not quantified. [established]
- **Closest published coherent-angle number is for the 1Q gate, not the ZZ gate** (S1.1):
  typical 1Q over/under-rotation **δθ ~ 5×10⁻³ rad**, with 1Q infidelity ~δθ²/6 ~ 4×10⁻⁶. The
  team found 1Q coherent errors accumulate within a Trotter step to an effective **field shift
  δh ~ 4·δθ/(2dt) ~ 4×10⁻²**, inducing an observable error ⟨Z²_tot⟩ ~ 0.04 if left un-mitigated.
  [established]
  - **Mapping to ε [inferred]:** δθ~5×10⁻³ rad is a *1Q* over-rotation. If (and only if) the
    native 2Q `U_ZZ` carries a *comparable* coherent over-rotation angle after calibration — a
    plausible-but-unverified assumption — then sin²ε ≈ (5×10⁻³)² ≈ **2.5×10⁻⁵ per gate**, i.e.
    *smaller* than the `overrot = 1e-4` scan point in `data/noise_sensitivity.txt`. There is **no
    published 2Q θ_ε to confirm this**, so treat it as an order-of-magnitude *upper-ish* guess,
    not a value. [inferred / assumed]

---

## 5. How this maps to our model

Our `scripts/run_noise_sensitivity.py` + `src/encoded_codes.py` (`NoiseRates`,
`to_stim`) implement, per 2Q gate at rate `p2`:
- **`zz_bias = η`:** a biased Pauli channel — `p2·(1−η)/15` on each of the 14 non-ZZ 2Q Pauli
  components, and `p2·(1−η)/15 + p2·η` on the ZZ component (code lines ~583–595). So η is the
  **extra ZZ-type stochastic weight on top of the uniform baseline**. [verified in code]
- **`overrot = sin²ε`:** on every native `ZZPhase`, apply the ZZ generator with probability
  sin²ε (a Pauli-twirled coherent over-rotation) — an undetectable logical fault at the gadget.
  [verified in code]

**Mapping from the literature:**
1. **η ← Fig. S3 stochastic ZZ fraction.** Our `zz_bias` IS a stochastic Z⊗Z Pauli weight, so
   the Fig. S3 read-off (η_ZZ ≈ 0.04–0.05) maps **directly** onto `zz_bias`, modulo the
   baseline-vs-total convention: our model's η is the ZZ *fraction of the 2Q error*, which is
   precisely p_ZZ/Σp_j. **Use `zz_bias ≈ 0.05` (bracket 0.03–0.08).** [inferred]
2. **ε ← θ_ε (unpublished for 2Q).** No published 2Q coherent angle to anchor sin²ε. The only
   related number is the 1Q δθ~5×10⁻³ rad (§4), giving a *speculative* sin²ε ~ 2.5×10⁻⁵. The
   honest input is to **scan ε** (e.g. sin²ε ∈ {0, 1e-5, 1e-4, 1e-3}) rather than fix it.
   [inferred / assumed]

**Caveats (must travel with any rerun):**
- **CNOT-frame vs ZZPhase-frame.** η-bias is exact for Iceberg's bare `ZZPhase`; for d≥3 parity
  gadgets the CNOTs are compiled `U_ZZ`+1Q, so the bias in the CNOT frame is approximate — the
  η≈0.25 crossover is exact only for Iceberg (`docs/encoded_tfim.md` model note; review/08 M1).
- **Pauli-twirl approximation.** `overrot` is a twirled stand-in; a real coherent error can
  accumulate faster than sin²ε (code comment; `docs/encoded_tfim.md`). On un-twirled encoded
  circuits the true coherent ZZ error could exceed this stand-in.
- **Twirled vs raw channel.** The Fig. S3 η is the *randomized-compiled* channel. If the project's
  encoded H2 circuits do **not** apply randomized compiling, residual coherent ZZ over-rotation
  (the θ_ε that twirling would have removed) adds on top of the stochastic η — pushing the
  *effective* ZZ-aligned error up. This is why ε must be scanned, not assumed zero. [inferred]

---

## 6. Recommended values to feed `scripts/run_noise_sensitivity.py`

**Primary prior (prediction-from-prior; NOT an H2 measurement):**
- `p2` ≈ **6×10⁻⁴** (current H2 2Q infidelity; the script's `P2 = 1e-3` is slightly pessimistic —
  consider 6e-4). [established magnitude]
- `zz_bias = η` ≈ **0.05**, bracket **[0.03, 0.08]**. [inferred from Fig. S3]
- `overrot = sin²ε`: **scan {0, 1e-5, 1e-4, 1e-3}**; no published 2Q anchor. Speculative central
  guess ~2.5e-5 from the 1Q δθ (clearly flagged [assumed]). [inferred/assumed]
- `p1 = pm = p_init`: keep p2/10 (consistent with H2's ~3×10⁻⁵ 1Q vs ~6×10⁻⁴ 2Q; p2/10 is mildly
  pessimistic on 1Q but matches the project baseline). Note HW-4: whether native `rz` is virtual
  on H2 is still open and affects 1Q exposure. [inferred]

**Predicted go/no-go [prediction-from-prior]:**
- At **η ≈ 0.05 ≪ 0.25**, the project is **BELOW** the ZZ crossover: on H2's *stochastic*
  (randomized-compiled) 2Q channel, **encoding is predicted to still help** (the ×0.42–0.50
  baseline regime, not the ×1.5 reversal). This is the first *quantitative, prior-backed* answer
  to FLAG-0 and it points **GO**, conditionally.
- **The condition that can flip it to NO-GO is ε** (coherent ZZ over-rotation on un-twirled
  circuits). At sin²ε = 1e-3 the gain already erodes to ×0.86 (still a help); combined
  η=0.5+over-rot the table shows ×1.31 (no help) — but η=0.5 is **~10× the published prior**, so
  that pessimistic row is **not** representative of H2. The realistic combined row to generate is
  **η≈0.05 + over-rot scanned**, which Claude Code should run. [prediction-from-prior]
- **Bottom line for the article spine:** the published H2 gate characterization supports
  "encoding helps" — but *only* with randomized compiling / twirling in place (so the ZZ error is
  stochastic and small), and *not* if the encoded H2 circuits run un-twirled and carry a coherent
  ZZ over-rotation. State it conditionally; it is a prediction from a prior, confirmable only on
  the H2 emulator/device (HW-1/HW-5).

---

## 7. What is NOT available / must wait for the H2 emulator or device (feeds HW-1)

1. **A directly published numeric η for H2.** The ZZ fraction is only *readable off a plot*
   (Fig. S3), not tabulated; my 0.04–0.05 is a visual read-off with ~±0.03 uncertainty. A clean
   η needs the raw cycle-benchmarking p_j (dataset or emulator noise model). [must verify]
2. **A numeric coherent ZZ over-rotation θ_ε (= our ε) for the 2Q gate.** Published only as a fit
   *form* (Eq. S7), never a value; twirled away in the reference experiment. Must come from the
   H2 emulator noise model or a dedicated calibration run (HW-5). [not available]
3. **Whether the project's encoded circuits will be randomized-compiled on H2.** The η≈0.05 prior
   is the *post-twirl* channel. If encoded runs are un-twirled, the effective ZZ-aligned error is
   larger (coherent θ_ε adds back). [design decision + hardware]
4. **The per-irrep r_ZZ coherent/incoherent split from 2305.03828** — the model exists (App. A.3)
   but the numbers are not in the text. [not available in text]
5. **HW-4 interaction:** native `rz` virtual-vs-noisy on H2 changes the 1Q exposure that feeds
   `p1`; unresolved. [open]
6. **Direct test (HW-1/HW-5):** Iceberg 2×2, 1 step on the H2 emulator with its real noise model,
   vs the Stim/Selene predictions, is the only thing that confirms this prior. [deferred to
   hardware, `handoff/05`]

---

## 8. Citations resolved / flagged

- **arXiv:2503.20870v3** — Haghshenas et al., *Digital quantum magnetism on a trapped-ion
  quantum computer*, **Nature 653, 56–62 (2026)**. Abstract + HTML full text + Supplement
  (S1.1–S1.5, S2.1, S3) + **Fig. S3 image** read directly. **RESOLVES.** [established]
- **arXiv:2305.03828v2** — Moses et al., *A Race-Track Trapped-Ion Quantum Processor*,
  **PRX 13, 041052 (2023)** / DOI 10.1103/PhysRevX.13.041052. Abstract + HTML (§II, §V,
  App. A.3) read. **RESOLVES.** [established]
- **arXiv:2406.02501** — DeCross et al. (H2 launch, 99.843(5)% 2Q). **NOT re-opened here**; number
  taken from `drafts/gauss_law_self_mitigation_assessment.md`. [unverified — flag]
- **arXiv:2602.22211** — Quantinuum, *Computing with many encoded logical qubits beyond
  break-even* (SCOPE §3 seed). **Not used in this note**; prior scout notes it resolves on its
  abstract page (research/scout/INDEX.md), but I did not re-verify it here. [unverified in this
  pass]
- **Project convention honoured:** no numbers/citations invented; the one visual read-off (η) is
  tagged [inferred]; the unpublished ε is reported as a gap, not a fabricated value; future-dated
  IDs elsewhere in the repo (2608.*, 2603.*, 2604.*) are untouched and remain flagged per SCOPE
  §11 / §12.

---

## 9. One-paragraph summary for the overseer / project lead

H2's native 2Q gate is the arbitrary-angle `U_ZZ(θ)` partial entangler (phase-sensitive MS),
current infidelity ≈6×10⁻⁴ (99.94%). The reference experiment (2503.20870) learns its error as
a **stochastic Pauli channel + a coherent ZZ rotation θ_ε**. Reading their cycle-benchmarking
plot (Fig. S3), the **stochastic ZZ fraction is small, η ≈ 0.04–0.05** (dominant error is
single-qubit-Z dephasing, not ZZ) — **well below the η≈0.25 crossover**, so the prior
**predicts encoding still helps on H2's twirled 2Q noise (conditional GO)**. The coherent
over-rotation ε is the catch: its 2Q value is **not published** (and the experiment twirls it
away with randomized compiling), so it must be **scanned**, and the "encoding helps" claim holds
**only if** the encoded H2 circuits are likewise twirled. Feed Claude Code: `p2≈6e-4`,
`zz_bias≈0.05` (bracket 0.03–0.08), `overrot` scanned {0,1e-5,1e-4,1e-3}; the realistic
η≈0.05 rows are the ones to generate, not the η=0.5 pessimistic rows already in the table. This
is a **prediction from a prior**, confirmable only on the H2 emulator (HW-1/HW-5).
