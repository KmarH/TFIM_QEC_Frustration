# Review 08 — handoff/04 Part B: four-code encoded-TFIM comparison, noise-model sensitivity, Selene-gap diagnosis

Reviewer: qc-reviewer (independent milestone peer review). Date: 2026-10-07.
Artifact: `docs/encoded_tfim.md` (Part B, "Noise-model sensitivity", "Why Selene keeps fewer shots"),
`data/encoded_codes.txt`, `data/noise_sensitivity.txt`, `data/selene_gap.txt`, `src/encoded_codes.py`,
`scripts/run_encoded_codes.py`, `scripts/run_noise_sensitivity.py`, `scripts/diagnose_selene_gap.py`,
`tests/test_encoded_codes.py`.
Standard applied: B (measured accounting, no pass/fail FT bar), budget (ii) (~55 physical qubits).

## Verdict: ACCEPT-WITH-FIXES

The central scientific claims are **independently reproduced and correct**. I re-derived the
accounting formulas by hand, recomputed every table from the source (not from the write-up's
numbers), ran the test suite, and the headline conclusions all hold: the undetectable residual
sits entirely at the logical rotations and is code-distance independent; higher distance buys
~1.2× on the residual at 3–5× worse acceptance; "Iceberg over the others" is robust across the 8
noise scenarios; "encoding helps at all" is NOT robust and flips at ZZ fraction η ≈ 0.25; the
Selene gap is a noise-model definition difference, not a bug. The required fixes are all
documentation/traceability items (a stale test count, incomplete hardware-caveat labelling on two
data files, and one under-specified approximation direction) — none touches a result.

---

## What I ran

- `.venv/bin/python -m pytest tests/test_encoded_codes.py -q` → **27 passed** (73 s).
- `/tmp/verify.py` — independent re-derivation of the accounting formulas, crossover η, Selene
  arithmetic, the budget table, and acc@3 (2×3).
- `/tmp/verify2.py` — per-lattice residuals for all four codes + bare; d≥3 crossover; concat
  structure.
- `/tmp/verify3.py` — full regeneration of the noise-sensitivity table (all 8 scenarios × 4 codes
  + bare, undetected / acceptance / ratio-to-bare).
- `grep` for the nexus stub and the hardware-prediction caveats in the three data files.
- Read `tests/test_encoded_codes.py::test_single_fault_accounting_isolates_the_logical_gates`
  (actually in `tests/test_encoded_tfim.py`, Part A) and the three Part B tests named in the brief.

---

## VERIFIED CORRECT

**V1 — Accounting formulas match an independent derivation and the Stim DEM output (brief item 1).**
Re-derived by hand and recomputed from source:
- Iceberg native gate: `3/15·p2` per gate, 12 gates/step at 2×2 → `12·p2·3/15 = 2.40e-3`.
  Measured `undetected_rate_per_step(prog("iceberg",2,2))["total"] = 2.4000e-3`. Match.
- Parity gadget: `2/15·p2 + 1/3·p1` per gadget, 5 gadgets/step at 1×2 →
  `5·(2/15·p2 + 1/3·p1) = 8.333e-4`. Measured for Steane and 5-qubit = `8.3333e-4`, and the class
  split is exactly `rot-cx = 5·2/15·p2 = 6.67e-4`, `rot-1q = 5·1/3·p1 = 1.67e-4`. Match.
- Bare 2×2: `4·p2 + 8·p1 = 4.80e-3`, measured `4.8000e-3`. Match.
- All B3 per-lattice residuals reproduce exactly: 1×2 (1.00e-3 / 8.33e-4 / 8.33e-4 / 8.33e-4),
  2×2 (2.40e-3 / 2.00e-3 ×3), 2×3 (4.20e-3 / 3.50e-3 ×3), with the same bare values.
- acc@3 at 2×3, p2=1e-3: Iceberg 0.827, Steane 0.213, 5-qubit 0.284, concat 0.226 — matches B3
  (0.83 / 0.21 / 0.28 / 0.23).

**V2 — The accounting is NON-VACUOUS (brief item 1).**
`undetected_rate_per_step` builds a Stim circuit (`to_stim`), takes its
`detector_error_model(...)`, filters mechanisms that flip a logical and fire no detector, and
sums component probabilities via `explain_detector_error_model_errors` + `_component_prob`
(`src/encoded_codes.py:617–676`). That is genuine Stim fault propagation. The tests then assert
equality against a **separately hand-written closed form** (`12*p2*3/15`,
`5*(2/15*p2 + p1/3)`, `4*p2 + 8*p1`) in
`test_measured_accounting_matches_first_order_derivation` — Stim-measured vs independent formula,
not measured-vs-itself. Confirmed non-vacuous.

**V3 — "Distance 4 buys nothing on the residual" is real (brief item 2).**
concat d=4 at 2×2 = `2.00e-3` and at 2×3 = `3.50e-3`, identical to the d=3 codes, not lower. The
residual is set by the rotation gadget, not the distance — directly supported.

**V4 — Budget table B2 is correct (brief item 2).**
Regenerated `n_phys` for every (code, lattice) and the L/H/x marks against ≤24 / ≤55: Iceberg
6/8/10/12/16/20 (all L); Steane 16L/30H/44H/58x/86x/114x; 5-qubit 12L/22L/32H/42H/62x/82x; concat
18/18/34/34/50H/66x. Exact match to B2 and `data/encoded_codes.txt §1`.

**V5 — Build/discard logic follows from standard B + budget (ii) (brief item 2).**
Under "measured accounting, no pass/fail bar", there is no bar to fail, so no numeric trigger for
a discard; each code fits ≤55 for ≥ a 2×2 lattice and has a verified, executed pipeline (B1/B3/B4),
so a budget discard is unavailable and a "harder to implement" discard is explicitly ruled out by
the brief. "Built, not recommended (dominated)" is the only disposition the chosen standard
permits. Logic is sound.

**V6 — The 5-qubit discard reversal is justified by measured counts, not hand-waved (brief item 2).**
The brief predicted a 5-qubit discard on logical-gate cost. B2's measured per-step counts show
5-qubit at 84 two-qubit gates/step vs Steane's 108, field weight 3 / bond weight 6 for both, and
acc@3 0.284 vs Steane 0.213 — i.e. 5-qubit is *cheaper* than Steane here, so the gate-cost basis
for a discard does not hold. This is an evidence-backed reversal; the frame-corrected
minimum-weight representatives (`min_weight_rep`, GF(2) `pure_errors`) are what make the non-CSS
code's logicals cheap, and `test_min_weight_reps_are_equivalent_and_short` checks the
representatives are stabilizer-equivalent and short. Reversal justified.

**V7 — Crossover η ≈ 0.25 (brief item 3).**
Solving Iceberg `12·p2·(0.2 + 0.8η) = 4.8e-3` gives η = **0.2500** exactly; the measured Iceberg
undetected rate under `zz_bias=η` reproduces `12·p2·(0.2+0.8η)` to rel 1e-6 at η=0, 0.25, 0.5, 0.9,
with ratios-to-bare 0.50 / 1.00 / 1.50 / 2.30. For the d≥3 codes the ratio crosses 1.0 between
η=0.25 (0.958) and η=0.27 (1.002), confirming the doc's "about 0.27". The physical mechanism (a
Z⊗Z error on a logical-ZZ-rotation gate *is* that rotation's generator, invisible to every code
here) is correct.

**V8 — Full sensitivity table reproduces (brief item 3).**
All 8 scenarios × (4 codes + bare), regenerated from source, match
`data/noise_sensitivity.txt`/the doc table cell-for-cell, including every ratio-to-bare: ZZ η=0.5
(×1.50), η=0.9 (×2.30/2.37), idle 1e-4 (×0.46/0.38), idle 1e-3 (×0.27/0.23), over-rot 1e-4
(×0.60/0.53), over-rot 1e-3 (×0.86/0.83), combined (×1.31). The internal consistency of the three
knobs is sound: idle hurts bare more (encoded idle is detected → favours encoding); over-rotation
adds the same logical error everywhere (→ ×1); ZZ bias is the only knob that reverses the sign of
the benefit. The "ranking robust / encoding-helps NOT robust" split is supported by the data:
Iceberg's residual stays within ~1.2× of the d≥3 codes in every row and it always keeps ~2× more
shots, while the ratio-to-bare crosses 1 only in the ZZ-biased and combined rows.

**V9 — Selene-gap arithmetic (brief item 4).**
`355 + 369 = 724`; `724 / 188 = 3.851` (doc: ×3.85). The one-channel-at-a-time 1q row:
`(0.1430 − 0.5943)/0.0064 = −70.5σ` (doc: −71σ, acceptable rounding; see m3). The channel table
isolates the 1q channel as the sole large discrepancy (2q +2σ, meas −0.6σ, init −5σ). The
native-matched Stim (p1×3.85, p_init×1.5) closes the gap to a stated 1–3σ residual that is left
explicitly OPEN (T-1 in open-questions.md; `data/selene_gap.txt §4`), not explained away.
"Noise-model definition difference, not a bug" is justified: p2 counts are identical (124 = 124),
only the single-qubit and allocation accounting differs by definition. "Code ranking unaffected,
Iceberg's lead widens" is supported by B's native-counting acceptance drop (Iceberg 0.875→0.831
vs Steane 0.383→0.309 etc., larger relative loss for the d≥3 codes).

**V10 — No sim-as-hardware (brief item 5).**
`src/backends_qc.py:323` raises `NotImplementedError(NEXUS_MSG)`; the nexus backend is a stub.
Every noisy table in the doc carries `[assumed]`/`[measured]` tags and the blanket
"classical prediction under an assumed generic depolarizing model" caveat.
`data/encoded_codes.txt` header says "classical predictions under ASSUMED generic depolarizing
noise; not H2 results." Selene is correctly described as a local emulator (Quest state vector),
not an H2 emulator or device. No hardware claim found. (But see m2 for the two unlabelled data
files.)

**V11 — Honest FT statement inherited correctly (brief item 6).**
Part A reports the done-check "no single-fault undetected logical error" FAILS by construction,
and `test_single_fault_accounting_isolates_the_logical_gates`
(`tests/test_encoded_tfim.py:123`) proves the undetectable set is exactly {XX, YY, ZZ} on each
logical-gate support (3 × number of gates), with syndrome-CX/H/meas/reset/idle contributing zero.
Part B's "the syndrome-extraction gadgets contribute zero; the entire residual sits at the logical
rotations" (B3 point 1–2) is the same statement, and
`test_measured_accounting_matches_first_order_derivation` confirms the non-syndrome classes are
exactly `{rot-cx, rot-1q}`. The framing — gadget is single-fault tolerant, encoded Trotter step is
not — is accurate and consistently carried into Part B.

---

## COULD NOT VERIFY / OUT OF SCOPE OF A CHEAP CHECK

**U1 — The executed Selene Z2 points in B4.** I did not re-run Selene (the full execution block is
minutes of emulation and would not change the accounting-based conclusions, which the doc itself
says the quantitative comparison rests on). The acceptance ranking Iceberg ≫ 5-qubit > Steane >
concat and "below the first-order prediction by 5–15 points" are internally consistent with the
Stim predictions I did reproduce, but the specific Selene Z2 ± SE values are **[unverified]** here.
This is acceptable: B4 explicitly states the execution "cannot show an encoding advantage at this
size and depth" and defers the quantitative claim to B3.

**U2 — H2's real η and ε.** Correctly deferred to HW-1; the doc does not claim to know them. Not a
defect.

---

## DEFECTS / FIXES

### Required fixes (traceability only; no result changes)

**m1 (minor) — Stale test count.** The doc (Part B header, B1) and
`scripts/run_encoded_codes.py` docstring say "26 tests". The file has 12 test functions that
collect to **27 tests** (`pytest --collect-only` → "27 tests collected"; the extra over 26 is
parametrization). Fix: say "27" or "12 test functions (27 with parametrization)".
Evidence: `tests/test_encoded_codes.py`, `pytest` collection.

**m2 (minor) — Hardware-prediction caveat missing from two data-file headers.** Only
`data/encoded_codes.txt` carries the explicit "not H2 results" line. `data/noise_sensitivity.txt`
says "[assumed], none is H2-calibrated" (adequate) but `data/selene_gap.txt` only says
"[assumed rates]". For a file that quotes Selene-vs-Stim acceptance numbers, add the same
one-line "classical simulators only; not an H2 result" caveat the other files carry, so a reader
opening the data file alone cannot mistake it for device data. Evidence: `grep` across the three
data files found the caveat in `encoded_codes.txt:3` only.

**m3 (minor) — "−71σ" vs computed −70.5σ.** `data/selene_gap.txt §2` reports "−70.6 sigma"; the
doc rounds to "−71σ". My recomputation from the quoted mean/SE gives −70.5σ. All three are the
same number to rounding; just note the doc's "−71σ" is a round of the data file's −70.6σ. Cosmetic;
flagging only because the brief asked for the exact value. No fix strictly required.

### Optional improvements

**M1 (major-but-disclosed → downgraded to optional) — ZZ-bias-in-CNOT-frame approximation is
flagged but its direction is not bounded (brief item 3).** `to_stim` applies the ZZ bias to the
*gate's own* Z⊗Z component for every two-qubit gate, including the parity-gadget CNOTs
(`src/encoded_codes.py:592–598`, `len(qs)==2` covers CX and ZZPhase alike). For the d≥3 gadgets a
CNOT is compiled on H2 from a native `ZZPhase` plus single-qubit gates, so the physically-biased
axis is the native ZZPhase's, not the CNOT's; biasing the CNOT frame's Z⊗Z is a different channel.
The doc **correctly flags this as an approximation [inferred]** ("Model notes" under the
sensitivity table), which is why this is not a critical finding. What is missing: the note does not
say in which direction it could be wrong. Because the headline η-crossover (0.25) is derived from
**Iceberg's native ZZPhase**, where the bias frame is exact, the crossover and the
"encoding-helps-not-robust" conclusion do not depend on this approximation — so the conclusion is
safe. But the d≥3 ratios under ZZ bias (×1.50, ×2.37) are frame-approximate and could move under a
faithful native model. Suggest one sentence: "the d≥3 ZZ-bias ratios are frame-approximate; the
η≈0.25 crossover is exact because it is set by Iceberg's native ZZPhase, so the robustness
conclusion is unaffected." Optional because the claim actually relied on is already exact.

**M2 (optional) — "~1.2× less undetected error" phrasing.** B5 and the brief summary say the d≥3
codes give "~1.2× less undetected error". The measured ratio is 2.0e-3 vs 2.4e-3 (2×2) = 0.833, i.e.
Iceberg's residual is 1.2× the others', or equivalently the others are 1.2× *lower*. The phrasing
is correct but easy to misread as "1.2× more protection per shot"; since it costs 3–5× acceptance,
a reader could over-weight the 1.2×. The doc does state the acceptance cost right next to it, so
this is purely stylistic.

**M3 (optional) — Over-rotation twirl understatement is noted but not quantified.** The doc says a
real coherent error "can add up faster than its twirled version" ([inferred]). True and honestly
flagged; no bound is given. Fine for this stage (coherent accumulation is an HW-era question), but
worth an explicit HW-1 cross-reference since it is part of the same "measure η and ε before
claiming the machine" caveat.

---

## Interpretation check (SCOPE Q1 — logical vs physical, QEC choice)

The conclusion "Iceberg is the right encoded baseline for Q1" is supported by the data shown with
uncertainties: the measured residual ordering, the budget table, and the acceptance costs all point
the same way, and the skeptical caveats (residual is first-order uncorrectable; advantage conditional
on η; 2×3 is far from 56 qubits; no size trend — T-8) are all stated. The comparison to the bare
circuit uses matched per-gate rates and the doc is explicit that this is not matched *cost* (Part A
risk 3b). No overclaim found: the write-up repeatedly says the execution "cannot show an encoding
advantage at this size" and rests the quantitative claim on the Stim accounting, which is the
honest position. The HW-1 dependency ("encoding helps" not robust) is correctly surfaced as the
gating open question, consistent with R-4 in open-questions.md.

---

## Open items for the author

1. (m1) Fix the test count to 27 (or "12 functions, 27 parametrized") in the doc and the script
   docstring.
2. (m2) Add the "classical simulators only; not an H2 result" caveat line to
   `data/selene_gap.txt` (and optionally reinforce it in `data/noise_sensitivity.txt`).
3. (M1) Add one sentence bounding the ZZ-bias-in-CNOT-frame approximation and noting the η≈0.25
   crossover is exact because it rests on Iceberg's native ZZPhase.
4. (m3) Harmonise "−71σ" with the data file's −70.6σ (cosmetic).
5. Keep T-1 (Selene 1–3σ residual) and T-8 (no size trend) open — both are correctly left open.

No result or code change is required; all fixes are documentation/traceability.
