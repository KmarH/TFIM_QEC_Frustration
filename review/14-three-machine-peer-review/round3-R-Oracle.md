# Round 3 — Adjudication by R-Oracle

Method: for each dispute assigned to me I designed a decisive check (a from-scratch calculation, a
direct read of the raw Zenodo QASM, a read of the private journal, or a run of the project's own
unmodified code on an input chosen to discriminate between positions) rather than re-reading prose.
One heavy reproduction (D13) was delegated to a single background subagent (one heavy computation
at a time, as instructed); everything else I ran myself. Scratch code: `peer-review/scratch/oracle_r3/`
and `peer-review/scratch/d13/`. Nothing outside `peer-review/` was modified.

---

## 1. Dispute rulings (assigned to R-Oracle)

### D4 — R-Main-3 severity (step-1 gap "≈3σ" / "size-independent")
**Ruling: DISMISSED down to MINOR** (agrees with R-Laptop, against my own and R-Main's Round-1 MAJOR).

Decisive check: grepped every doc and `report.tex` for σ/significance language tied to the step-1
gap, and read the actual table/caption.
- `report.tex`'s Table 1 (the only external-facing, report-level presentation of this number) makes
  **zero** σ claims. Its caption explicitly flags `_err`'s 1σ-vs-CI status as **unverified**, and the
  prose immediately below the table calls it "a finite-size trend comparison and nothing more... it
  contains no logical-qubit number." No conclusion anywhere in `report.tex` is drawn from "3σ" or "2σ".
- The actual "**≈3 bootstrap σ**" sentence lives only in the internal working doc `docs/q1_compare.md:29`,
  computed against the 4×5 proxy lattice, not the exact N=56 light-cone value (which the exact value
  gives ≈2.0σ/zne+znr, ≈3.2σ/raw — R-Main's Round-1 number, confirmed independently by all three of us).
  The same doc, 30 lines later, already tags `_err`'s 1σ status `[unverified]`, so a careful reader of
  that doc is already warned not to over-read the number.
- "size-independent": the changelog at `docs/q1_compare.md:81` claims "m7: wording overclaims...fixed:
  softened in code and caveat." The *code* docstring (`src/compare.py:260`, `pair_average_from_z2`) is
  correctly hedged: "The pair correlations themselves still depend on size." But the *doc prose* at
  `docs/q1_compare.md:57` still literally reads "this size-independent version" — the changelog's claim
  of a fix is only half true (fixed in code, not fully in the doc's own wording).

**Why MINOR, not MAJOR:** the overstated number and the residual "size-independent" phrase sit only in
an internal technical doc, are already partially self-caveated in the same doc, and are never used to
support any headline claim in `report.tex` or `findings_vs_questions.md` — the report-level framing is
already conservative ("no logical-qubit number"). **Fix (small, worth doing):** replace "about 3
bootstrap σ" in `q1_compare.md:29` with the correct ≈2.0σ (zne+znr, exact N=56 light-cone value) /
≈3.2σ (raw), and delete the word "size-independent" at `q1_compare.md:57` to match the already-fixed
code docstring.

### D5 — R-Main-4 severity (sign-blind circuit check)
**Ruling: DISMISSED down to MINOR** (agrees with R-Laptop; the condition R-Laptop set — "MAJOR only if
the real QASM signs differ" — is now checked and resolved in the negative).

Decisive check: extracted every `rzz`/`rx`/`ry` angle, **with sign**, from all 80 real circuit files
(`quench{1,2,3,4}_step{1..20}.qasm`) in `~/zenodo_18487089/zenodo_data/circuits/`, not just the
step1/step8 spot-checks earlier reviewers used:
```
rzz: always rzz(0.5) — never negative, in any of the 80 files.
rx:  always rx(0.5) or rx(1.0)/rx(1) — never negative.
ry:  0.5235987755982988 (q1), -0.17453292519943295 (q2/q3), pi (q3, 4 qubits only), 0 (q4) — the
     per-quench prep angle; never a sign variant within one quench's 1120 rzz/rx gate instances.
```
No negative `rzz`/`rx` anywhere, pooled over every quench and every step. The real dataset never
exercises the non-gauge sign pattern (`rzz(+)`, `rx(−)`) that R-Main's synthetic adversarial probe
constructed and that `_same_up_to_sign` would wrongly accept.

Also found the origin of the gap while reading the changelog: `docs/q1_compare.md:76` — "**m2: QASM
check used exact equality and rejected gauge signs | fixed: |angle| with a tolerance**." The
sign-blindness is not an oversight; it is the direct, documented result of an earlier fix that
removed sign-checking *on purpose* to stop the check from rejecting legitimate gauge-equivalent
sign flips, without noticing this also lets through genuinely non-gauge sign combinations.

**Why MINOR, not MAJOR:** on the actual released data, the bug is latent, not live — it has not
caused and currently cannot cause an actual wrong comparison, because the real circuits are
sign-uniform throughout. **Fix (still worth doing, for robustness and documentation honesty):**
check the signed (rzz, rx, ry) triple against the four gauge-equivalent sign patterns (as R-Main
suggested), and correct `report.tex:231-233`'s "gauge signs were re-checked" to say what the code
actually checks (magnitudes, with the signed `ry` already checked separately).

### D9 — R-Oracle-3 matched-lattice gate counts
**Ruling: CONFIRMED, R-Main's numbers exactly reproduced.** Ran the project's own unmodified
`EncodedTFIM`/`gate_counts`/`BareTFIM` (`src/encoded_codes.py`) at a genuinely matched 2×2 lattice
for all four codes (overriding the project's own `REDUCED` dict, which deliberately runs Steane and
5-qubit at 1×2 instead — confirmed at `scripts/run_encoded_codes.py:37`):
```
iceberg  2x2: 28 two-qubit gates/step   (n_phys=8)
steane   2x2: 240 two-qubit gates/step  (n_phys=30)   240/28 = 8.57x
five     2x2: 192 two-qubit gates/step  (n_phys=22)   192/28 = 6.86x
concat   2x2: 184 two-qubit gates/step  (n_phys=18)   184/28 = 6.57x
bare     2x2: 4 two-qubit gates/step
```
Matches R-Main's Round-2 numbers (28/240/192/184, 8.6×/6.9×/6.6×) to the gate. The true matched-lattice
range is **6.6–8.6×**, not the "3–7×" the docs currently headline. **Severity: stays MINOR.** This
does not threaten the "Iceberg recommended" conclusion — if anything it strengthens it: the
undercount makes the higher-distance codes look *cheaper* relative to Iceberg than they really are,
which biases *against*, not for, the project's own preferred answer. **Fix:** state 6.6–8.6× (matched
2×2) as the headline, or explicitly flag the Steane/5-qubit numbers as lower bounds from a smaller lattice.

### D10 — Degenerate small lattices (R-Main-8 / R-Oracle-R2-2)
**Ruling: DISMISSED as a threat to Q1/Q4; the headline numbers are confirmed conservative, not
inflated.** Ran the project's own unmodified `EncodedTFIM`/`BareTFIM`/`undetected_rate_per_step`
(no project code modified, no independent re-derivation needed — this directly tests production
behavior) at three lattices, none of them cherry-picked to match the doc's claim in advance:

| lattice | B (bonds) | η* (crossover) | ratio at η=0.05 |
|---|---|---|---|
| 2×2 (degenerate ring, B=N) | 4 | **0.2500** | **0.6000** |
| 2×3 (ladder, B=1.5N) | 9 | **0.3600** | **0.4941** |
| 4×4 (genuine non-degenerate square torus, B=2N) | 32 | **0.4404** | **0.4364** |

All three numbers match `docs/encoded_tfim.md:305`'s claimed generalization (η*≈0.25/0.36/0.44, ratio
0.60/0.49/0.44) essentially exactly, using the project's own code on a lattice (4×4) that is not
degenerate and was not one of the project's own pre-computed examples. **The 2×2 toy lattice is
confirmed to be the most pessimistic case for Iceberg, not a cherry-picked favorable one** — the
real advantage margin only grows on realistic lattice sizes. Checked disclosure coverage across every
doc that quotes a 2×2/2×3 result (`docs/encoded_tfim.md`, `docs/findings_vs_questions.md`,
`docs/report/report.tex`, `README.md`, `docs/nexus_toggle.md`): the degenerate-lattice caveat and the
larger-lattice numbers are present in all three conclusion-bearing documents (`encoded_tfim.md:305`,
`findings_vs_questions.md:21`, `report.tex:98,101,278-287,630`); `README.md:94`'s one mention is a
proposed hardware-calibration step description, not a conclusion, and needs no caveat. **R-Oracle-R2-2
is resolved: no undisclosed instance found.** Final severity for R-Main-8: stays MINOR, as R-Main/
R-Laptop/R-Oracle converged on in Round 2.

### D13 — Third check of R-Laptop-R2-1 (Trotter-ordering sign error in the Q3 defect-density claim)
**Ruling: CONFIRMED** (third independent reproduction; delegated to a subagent, instructions and
result verified by me). 3×6 triangular torus, 3-sublattice start, h=0.3, J=−1, dt=0.25, late window
(`CONFIG.q3`'s own window, t∈[20,40]), using the project's own `trotter.trotter2_step`,
`compare.circuit_trotter_states`, and `trotter_threshold.ExactPropagator`:
```
ZZ-outside (trotter.py, what the docs actually used):    ratio to exact = 1.3902   (R-Laptop: 1.389)
circuit order (compare.py, the real reference ordering):  ratio to exact = 0.6037   (R-Laptop: 0.605)
```
Matches R-Laptop's numbers to 3 significant figures. The sign flip is unambiguous and now
triple-confirmed (R-Main, R-Laptop, R-Oracle, three different hosts/runs): `docs/q3_thermalization.md:
234-243`'s claim that the ZZ-outside-computed, ≈40%-inflated defect density "describes the reference
experiment's circuit" is **wrong** — the real circuit ordering *deflates* the defect density by
≈40%, it does not inflate it. **Final severity: MAJOR** (R-Laptop-R2-1 / R-Main-R2-1), confirmed.
This also means the companion claims — P_out "Trotter-inflated ≈10–25%" and the noiseless
`run_gauss_law.py:103` zero-defect floor — are unchecked in circuit order and should not be assumed
to carry the same sign without a rerun (I did not rerun these two myself; D3a/D3b cover them and were
assigned to R-Laptop/R-Main).

### D15 — Was the h/|J| conflict (0.3 vs 2) ever resolved?
**Ruling: NOT RESOLVED — and the private journal shows it is worse than an unresolved disagreement:
it is two independently-run research threads that each individually verified an opposite number from
the *same paper*, and were never cross-checked against each other.**

Read `Conversation history/project-journal.md`, `open-questions.md`, and `research/04-gauss-law-citations.md`
(all in `~/KiroTest-project/`, read-only, quoted minimally below):
- **Entry 6** (2026-10-06, the Gauss-law/Q3 build): "arXiv:2503.20870 §V (fetched) writes H = J ΣZZ +
  h ΣX... on a 9×6 lattice with (h/|J|, dt|J|) = (0.3, 0.25)." `GaussLawConfig`/`Q3BaselineConfig` are
  built with h=0.3 on this basis and the doc language "matching arXiv:2503.20870 §V" is adopted.
- **`research/04-gauss-law-citations.md` Item 3** (same day, an "OVERSEER ADDENDUM... RESOLVED" after a
  full-text re-fetch of the v3 HTML, which the first fetch attempt had truncated before §V):
  independently **confirms "(h/|J|, dt|J|) = (0.3, 0.25)"** are "confirmed in the abstract/intro/§V" —
  i.e., a second, independent reading of the paper's own prose, done specifically to verify this
  number, also lands on 0.3.
- **`research/05-zenodo-dataset-map.md`** (2026-10-06/07, a *different* research thread, parsing the
  released QASM circuit files directly): finds `quench4_step*.qasm` (labelled "triangular quench" in
  the dataset's own README) gives `rzz(0.5)`/`rx(0.5)` ⇒ **h/|J| = 2**, identical to the square
  quenches, and concludes "**the 0.3 appears to be an error in the brief**," resolving "in favour of
  the QASM" for the Q1/`compare.py` harness (which does use 2, correctly, for its own work).
- **I found no entry, in either research doc or the journal, that cross-references the other.**
  `research/04` never mentions quench4's QASM angles; `research/05` calls the 0.3 figure an error in
  "the brief" without checking whether it had actually been independently confirmed from the paper's
  own text by a sibling research thread the same day. Every subsequent Gauss-law/Q3 journal entry
  (25, 26, 32, 33, 38, 40, 41, 43, 44 — through the final standstill) continues to use h=0.3 and the
  "matching the reference" framing, with no trace of anyone noticing the contradiction persists.
  `open-questions.md` tracks no T-number for this; R-15 (Entry 44, the latest hardware-lattice
  decision) still writes "h = 0.3... as the reference" unchanged.
- **This was not a deliberate choice to study the frustrated regime instead of matching the
  experiment.** Nothing in the journal states that reasoning; it reads as an oversight — the
  QASM-level finding from `research/05` simply never propagated to the Gauss-law config, and the two
  research threads never checked each other's work on the one number both independently touched.
- **Bonus, relevant to D11 (R-Main's):** while extracting the signed angles for D5, I noticed
  `quench4_step1.qasm`'s `ry` prep layer is `ry(0)` on all 54 qubits — a literal no-op, with **zero**
  `x` gates anywhere in the file. The released quench4 circuits do not encode either winding-sector
  initial bitstring (min (0,0) or max (18,6)) at all. This directly confirms `open-questions.md`'s
  **T-5** ("quench4 min/max-winding initial bitstrings are not in the dataset") by direct inspection,
  and means the Gauss-law/Q3 "which winding sector does the real experiment start in" question is not
  just a convention mismatch (0.3 vs 2) but **unanswerable from the released circuits at all** — worth
  folding into R-Main's D11 ruling on whether the Q3/Gauss-law framing "describes the reference
  experiment" at any h.

**What would fully settle it:** someone with the actual PDF or Supplemental Material of
arXiv:2503.20870 (not the HTML mirror, which both research threads note truncates/omits parts of §V
and the Methods) checking whether the paper describes *multiple* triangular runs at different field
strengths, one of which could genuinely be h/|J|=0.3 while the released quench4 QASM represents a
different one at h/|J|=2. Until then, the project should treat 0.3 as **unconfirmed against the
dataset it actually has**, regardless of what the paper's abstract/intro text says.

---

## 2. Own Round-1 findings: final disposition

- **R-Oracle-1 (first-order DEM claims not labelled as such): ACCEPT the downgrade to MINOR.**
  Independently re-confirmed by grep: "first order"/"first-order" appears 13× in `docs/encoded_tfim.md`
  alone, including the B3 section header `[Stim, first order]`, plus 6× in `report.tex` and 2× in
  `findings_vs_questions.md`. My Round-1 claim that this was "nowhere stated" was wrong; what survives
  is the narrower point that the `[measured]` tag itself is not glossed with "no sampling error,"
  which is a documentation nit, not a MAJOR finding.
- **R-Oracle-2 (first-order approximation breaks down at low acceptance; explains the Selene gap):
  ACCEPT the refutation, with my own third confirmation.** I ran my own fresh Stim Monte Carlo
  (200,000 shots, independent seed, using the project's own `to_stim`/`detected_total` but genuinely
  sampling via `compile_detector_sampler`, not reusing either other reviewer's numbers) at exactly the
  lowest-acceptance case I had flagged in Round 1 as suspect:
  ```
  steane  2x3 p2=3e-3 steps=3: first-order exp(-D)=0.0097  MC=0.0096 ± 0.0002   diff=0.0000
  concat  2x2 p2=3e-3 steps=3: first-order exp(-D)=0.1050  MC=0.1062 ± 0.0007   diff=0.0011
  iceberg 2x2 p2=1e-3 steps=3: first-order exp(-D)=0.8751  MC=0.8749 ± 0.0007   diff=0.0002
  ```
  The method does not degrade at low acceptance; my Round-1 reasoning ("a code accepting only 1-3% of
  shots is dominated by multi-fault terms the first-order expansion does not resolve") was wrong for
  this specific quantity (`exp(-D)` is not a 1−D truncation, it already exponentiates the first-order
  rate, so it stays accurate). The Selene gap is, as the project's own `data/selene_gap.txt` already
  showed, a native-gate noise-counting difference, unrelated to this approximation. **R-Oracle-2 is
  REFUTED**, now confirmed by all three reviewers independently.

---

## 3. Opinions on disputes assigned to others (evidence found incidentally)

- **D11 (R-Main):** see the D15 bonus finding above — quench4's released QASM has no winding-sector
  initial-state information at all (confirmed by direct inspection, zero `x` gates, `ry(0)` identity
  prep on all 54 qubits). This is independent of, and additional to, the h/|J|=2 vs 0.3 question:
  even if the field value were reconciled, the specific initial bitstring the Q3/Gauss-law "which
  sector" framing depends on is simply not recoverable from the data release.
- **D1 (R-Laptop):** no new evidence from me this round; R-Main's point that the guard *does* fire
  correctly from a genuine in-sector start (only the regression-test construction is vacuous) reads as
  sound on the Round-2 record, which would argue MINOR, but I did not independently re-run this check
  and defer to R-Laptop's ruling.

---

## 4. Final severity table (all findings I consider real, after all three rounds)

| finding | final severity | why |
|---|---|---|
| R-Main-1 / Strang-ordering mismatch vs published circuits, used in Q3/Gauss-law | **MAJOR** | triple-confirmed; wrong-ordering numbers feed the live Q3/Gauss-law config |
| R-Laptop-R2-1 / R-Main-R2-1 — Q3 defect-density inflation claim has the wrong sign vs the real circuit order | **MAJOR** | triple-confirmed (D13, this round); directly contradicts "describes the reference circuit" |
| R-Main-2 — h/\|J\| = 0.3 vs 2 for the triangular reference | **MAJOR** | confirmed from raw QASM; D15 shows it was never reconciled and is deeper than a typo — two independent research threads each confirmed an opposite number from the same paper |
| R-Main-5 — Q1 can't fit the released 7×8 lattice on H2 (60 > 56); no shot/estimator accounting in `compare.py`'s `Series` | **MAJOR** | confirmed by all three; blocks any real logical-vs-physical comparison against the released data as currently scoped |
| R-Main-3 — step-1 gap "≈3σ" / "size-independent" | **MINOR** (D4) | confined to an internal doc, already partly self-caveated, never used in `report.tex`'s conclusions |
| R-Main-4 — sign-blind circuit check | **MINOR** (D5) | real gap, but the real QASM is sign-uniform throughout; currently inert |
| R-Oracle-3 — "3-7x" gate-count headline mixes lattice sizes | **MINOR** (D9) | confirmed understated (true range 6.6-8.6x); biases against, not for, the project's preference |
| R-Main-8 / R-Oracle-R2-2 — 2x2/2x3 degenerate lattice behind the headline η crossover | **MINOR** (D10) | tested, physically forced, disclosed in all three conclusion-bearing docs; crossover improves on realistic lattices |
| R-Oracle-1 — first-order numbers not labelled as such | **MINOR** | "first order" appears 13x+ in the docs; only the `[measured]`-tag gloss is missing |
| R-Oracle-2 — first-order method breaks down at low acceptance | **REFUTED** | triple-confirmed by Monte Carlo to ≤1.1e-3 even at 1% acceptance |
| R-Main-6 — no `encoding=` on Windows | MINOR | real, reproduced independently, trivial fix |
| R-Main-7 — "Néel" state is column stripes | MINOR | low impact, only one test touches it |
| R-Main-9 — core test gaps (no E0 closed-form assertion, etc.) | MINOR | partly refuted (triangular IS tested); the E0 assertion gap is real |
| R-Main-10 — Q1 fixture circular, run script untested | MINOR | confirmed, no safety-critical path |
| R-Main-11 — doc/data mismatches | MINOR, mixed | "63 vs 42" retracted (two correct metrics); "32x" confirmed real (already settled); others confirmed minor wording |
| R-Main-12 — stale docs (memory figures, test count) | MINOR/trivial | cosmetic |
| R-Laptop-1 — sector-escape guard vacuous | MINOR-leaning (D1, assigned to R-Laptop) | guard works from a real in-sector start; only the regression test is vacuous |
| R-Laptop-2 — thermalization statistic | unresolved (D2, assigned to R-Laptop) | |
| R-Laptop-3 — ARPACK portability | MINOR, not a bug | |
| R-Laptop-4/5/6 — stale doc, cross-ref ambiguity, untested `postselect` | MINOR | all confirmed |
| R-Laptop-R2-2 — decision journal not in the repo | MINOR, but consequential | confirmed first-hand this round: it is the only reason D15 could be settled at all, and only on this one machine |
| Randomized compiling (D-RC) not yet implemented | MINOR (disclosed) but hardware-gating | `handoff/11` already flags it; the "encoding helps" GO explicitly rests on it per `report.tex:101` |

No fabricated numbers and no tautological test (beyond the already-flagged R-Laptop-1) were found by
any reviewer across three rounds, three independent machines/OSes/Python versions, and roughly 40
independent re-derivations.

---

## 5. Bottom line

**Q1 (encoding helps at η≈0.05): supported as a conditional classical prediction, not yet as a
hardware result.** The arithmetic is right — I and the other two reviewers each independently
re-derived the η≈0.25 crossover and its generalization to larger lattices from scratch, and the
first-order Stim accounting that the whole Q1/Q4 case rests on matches exact Monte Carlo to ≤1.1e-3
even at 1% acceptance (triple-confirmed this round). But the conclusion remains three steps away from
anything that could be called established: (1) η itself is an **[inferred]** prior, not H2-measured;
(2) randomized compiling, which the GO explicitly depends on (`report.tex:101`), is not built; (3) the
harness that would do a real logical-vs-physical comparison against the released data cannot fit
Iceberg's qubit count on H2 at the released lattice size and has no shot/acceptance/estimator
accounting (R-Main-5, MAJOR, unresolved). The step-1 "≈3σ" gap claim is a documentation overstatement
in an internal doc (MINOR) and does not affect this.

**Q2 (triangular correlations 3-5x weaker): well supported.** Independently re-derived bit-for-bit by
a different reviewer on a different OS/architecture/Python version from scratch; the odd-length-square
frustration correction (T-19) was caught and applied; the disorder-line caveat is honestly stated, not
overclaimed. No open issues.

**Q3 (thermalization results): the core relaxation/MCMC physics is sound, but the claim that it
"describes the reference experiment's circuit" is not currently true, and may not be fixable as
framed.** The sector-conditioned relaxation curves, the finite-size offset to the diagonal ensemble,
and the MCMC baseline are all independently re-derived and confirmed. But: (a) the specific
dt=0.25-inflation numbers in `docs/q3_thermalization.md` §8 use the wrong ordering and get the *sign*
of the bias wrong relative to the actual published circuit (MAJOR, triple-confirmed, D13); (b) whether
h≤0.5 (used throughout Q3/Gauss-law) has anything to do with the real triangular reference experiment
at all is unresolved — the paper's own text says h/|J|=0.3 (confirmed twice, independently, from the
abstract/intro/§V), but its own released circuits say 2 (confirmed from the raw QASM), and the project
never reconciled this (MAJOR, D15); (c) the released quench4 circuits don't even specify which winding
sector was used, so "matching the reference's winding sector" cannot currently be verified from the
data the team actually has, regardless of (b).

**Q4 (Iceberg recommended, d≥3 buys ~1.2x): well supported, and the evidence is more favorable than
the headline states.** Code distances, the η crossover and its generalization, and the first-order
accounting method are all independently verified multiple times. The "3-7x gate cost" headline
actually understates the case for Iceberg (true matched range 6.6-8.6x), and the 2×2 toy lattice used
for the headline η* and ratio numbers turns out to be the *most pessimistic* case, not a
favorably-chosen one — both of these biases run against, not for, the project's own preferred
conclusion, which is a point in the project's favor.

**Gauss-law mitigation (modest yes for post-selection against bit-flip/X-Y noise, floored at
O((h/|J|)²); no for dephasing/general self-mitigation): the math is right, but it inherits Q3's
h/|J| and winding-sector problems** — it is a correct classical study of a specific model at h≤0.5,
not yet demonstrated to be the reference experiment's model.

### Ready for hardware as-is?
**No.** The physics core (lattices, Hamiltonians, evolution, ED, the QEC code constructions, the
noise accounting method) is correct and has been independently re-verified from scratch by three
reviewers on three platforms with no fabricated numbers found anywhere. What is not ready is the
*framing* — whether several of the headline claims actually describe the experiment they say they
describe — and one piece of required machinery that is simply not built yet.

### Must-fix-before-hardware, smallest possible ordered list
1. **Reconcile h/|J| = 0.3 vs 2 for the triangular reference** (R-Main-2/D15). This is a project-lead
   decision, not a code fix: either the released quench4 circuits are the wrong reference for the
   Q3/Gauss-law thread's h≤0.5 work (in which case relabel that work as a self-contained classical
   study, drop "matching §V", and stop citing it as validated against the released dataset), or the
   team has independent reason (not yet in the repo) to believe the paper describes a second
   triangular run at h/|J|=0.3 that the released QASM doesn't represent. Either answer is fine; leaving
   it unreconciled, as it has been since 2026-10-07, is not.
2. **Fix the ordering sign error** (R-Main-1 / R-Laptop-R2-1, D13, MAJOR, now triple-confirmed): rerun
   `docs/q3_thermalization.md` §8's and `gauss_law_dimers.md`'s defect-density/P_out numbers in circuit
   order, and correct "describes the reference experiment's circuit" everywhere it is wrong, or add a
   circuit-order option to `src/trotter.py` and use it for every claim that invokes the reference circuit.
3. **Build randomized compiling** (D-RC, `handoff/11`): currently not implemented at all; the Q1
   "encoding helps" GO is explicitly conditional on it per `report.tex:101`.
4. **Give the Q1 harness a real logical-vs-physical comparison path** (R-Main-5): pick a reduced
   lattice that actually fits both Iceberg's physical-qubit count and H2's 56 qubits (as Q3 already did
   for its own hardware-lattice choice, R-15/Entry 44), and add shot/acceptance/estimator-class fields
   to `compare.py`'s `Series` so a post-selected logical run can be compared on equal footing with the
   released ZNE+ZNR data.
5. **Make the circuit sign-check sign-aware** (R-Main-4/D5): low urgency since today's data never
   triggers it, but cheap to fix, and `report.tex`'s current claim about what the check does is false.

ROUND3-DONE
