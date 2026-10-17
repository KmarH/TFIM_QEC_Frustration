# Open decisions and scope corrections

This file records decisions that belong to the project lead and that the repository cannot settle
on its own, plus the scope corrections already applied. It exists because the working decision
record (`Conversation history/project-journal.md` and `open-questions.md`) is intentionally not in
this repository, so a reader of the public repo previously had no way to tell an open question from
a settled one. Peer review, October 2026, finding R-Laptop-R2-2.

Status tags follow the project convention: [established] [derived] [measured] [inferred] [assumed]
[unverified].

---

## RESOLVED-1, formerly OPEN-1 then DECIDED-1 — The triangular field: h/|J| = 0.3 or 2?

**Status: RESOLVED 2026-10-15 on evidence. h/|J| = 0.3 is CORRECT, and this project's triangular
configuration (h/|J| = 0.3, dt|J| = 0.25, 9×6) MATCHES the reference's §V. The `h/|J| = 2`
reading came from the released quench4 circuit files, and those files are defective: they carry
the reference's own *square*-quench field value. Nothing in the configuration needed changing —
it was right all along.**

**The one-line version.** The paper's Figure 4(e) states, verbatim, *"All data taken at
(h/|J|, dt|J|)=(0.3, 0.25)."* §V's body sets the regime as a weak transverse field, and the
lattice is 9×6. The project's own `research/04` read this correctly from the start. The circuit
files disagree, and the circuit files are wrong.

**Why this entry has three statuses.** It was opened as OPEN-1 when the peer review found the
conflict; it was closed on 2026-10-15 as DECIDED-1 by choosing to treat the work as a
self-contained weak-field study (because the paper's §V body appeared unreadable, so the
circuits were the only hard evidence); and it was reopened and resolved the same day once the
full text was finally retrieved. The earlier DECIDED-1 framing — that the work does *not*
reproduce the reference — was an over-correction and has been withdrawn from the documentation.
The sequence is kept here deliberately: the conflict was hard to find precisely because earlier
records were tidied rather than annotated.

### The evidence (2026-10-15)

**The paper** (arXiv:2503.20870v3, read in full):

- §V, *"Emergent gauge theory on a frustrated lattice"*, sets the regime: **"For weak transverse
  field (0 < h ≪ J)"**. [established]
- **Figure 4(e) caption: "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)."** [established]
- The triangular lattice is **9×6** (§V, and again Methods §VII.1) — 54 sites. [established]
- There is **one** triangular run at **one** field. The maximal and minimal winding sectors are
  two initial states within it, not separate runs. [established]
- The paper states the **square** quenches use **h = 2|J|**, explicitly a different system.
  [established]

Earlier fetch attempts failed only because the HTML is 244,452 characters and truncated before
Figure 4 — not because the value was missing. `research/04`'s caveat that §V's body was never
reached is now closed.

**The released circuits** (read from `~/zenodo_18487089/zenodo_data/circuits/`):

| file | rzz | rx (two half-layers) | ry | qreg |
|---|---|---|---|---|
| `quench1_step1.qasm` (square 7×8) | 112 × `rzz(0.5)` | 112 × `rx(0.5)` | 56 × `ry(π/6)` | 56 |
| `quench4_step1.qasm` (triangular 9×6) | **162 × `rzz(0.5)`** | **108 × `rx(0.5)`** | 54 × `ry(0)` | 54 |

- The gate **counts are correct** for 9×6: 162 = 3N bonds, 108 = two half-layers on 54 qubits. The
  geometry really is the triangular one. [measured]
- The **angles are the square quench's**. With dt|J| = 0.25 that is h·dt = 0.5, i.e. h/|J| = 2.
  At the paper's h/|J| = 0.3 each half-layer would be **`rx(0.0375)`**, about 13× smaller.
  [measured]
- The dataset's gauge identities only flip **signs** of (J, h, θ); they cannot change a magnitude.
  So this is not a gauge artefact. [derived]
- **The release already documents these circuits as not the experiment's.** README, verbatim:
  *"For quench4, the circuits in the folder are initialized to the |0...0> state, while the
  experiments initialized to two different bitstring configurations."* The wrong field is a
  second, undocumented instance. The same README offers the circuits "to cross-check against the
  gate angles and circuit geometry we used" — which is exactly the use that misled this project.
  [established]

**The physics agrees with the paper, not the circuits.** §V's whole subject is an emergent Z₂
Gauss law and dimer description that exists only for h ≪ J. At h/|J| = 2 there is nothing of the
kind to observe: three independent reviewers measured, noiselessly, that the in-sector probability
collapses from 1.0 to 0.13–0.63 within a **single** Trotter step, with in-sector weight falling
with size (0.55 at N = 9, 0.11 at N = 12). A paper reporting dimer correlations relaxing toward
Markov-chain Monte Carlo values cannot have been at h/|J| = 2. [measured]

### Consequences

- **`research/04` was right.** Its reading stands; the caveat added to it earlier on 2026-10-15 is
  corrected.
- **`research/05` read the files correctly**; only its inference about the experiment was wrong,
  because the files misrepresent the experiment. It is now the detailed home for this finding.
- **Q3 and the Gauss-law thread may again be described as matching the reference's §V**, now cited
  to Figure 4(e) rather than assumed.
- **The weak-field physics argument is kept**, reframed: it explains why the reference's own choice
  of a weak field is the right regime and why the conclusions are safe at 0.3. It corroborates the
  value instead of substituting for it.
- **New finding, recorded in `research/05`:** the released quench4 circuits are inconsistent with
  the paper's stated parameters in both field and initial state. Do not use them to infer the
  triangular experiment's parameters; use the paper.
- **T-5 narrows.** The two winding sectors **are** identified in the release, as the
  `quench4_min_winding_*` and `quench4_max_winding_*` data files. What is missing is the explicit
  initial bitstrings and circuits matching them.

### What did not change

No physics constant, no code, no number. `h = 0.3` and `dt = 0.25` were correct before any of
this and are untouched; the suite stays at 274/274 on three platforms. Only the claims about what
the work corresponds to moved — back to the project's original position, sourced this time.

### How the conflict arose (history, kept for the record)

Everything from here on describes the state of knowledge **before** the resolution above. It is
kept because the failure mode is instructive, not because it is current.

Q2, Q3 and the Gauss-law thread all run at h/|J| = 0.3, described in several places as "matching
arXiv:2503.20870 §V". For a time that description could not be defended, because the project's own
two research threads independently derived **opposite** values from the same paper and never
cross-checked each other:

| source | value | basis |
|---|---|---|
| the paper's own prose (abstract, intro, §V), read twice independently | h/\|J\| = 0.3 | `research/04-gauss-law-citations.md` item 3 [established] |
| the paper's own **released quench4 circuits** | **h/\|J\| = 2** | `research/05-zenodo-dataset-map.md`; `rzz(0.5)`, `rx(0.5)`/`rx(1.0)`, identical to the square quenches, in all 80 QASM files [established] |

`research/04` additionally states that §V's body text was never actually reached, which at the time
appeared to weaken the prose reading — the opposite of the truth, as it turned out: §V's body and
Figure 4(e) both confirm 0.3. `research/05` concluded "the 0.3 appears to be an error in the brief"
but that finding never propagated to `GaussLawConfig` / `Q3BaselineConfig`, and every later entry
kept both the 0.3 value and the "matching the reference" framing. In the end the config was right
and the propagation failure was harmless, but only by luck: nobody had checked which source was
authoritative.

**The lesson worth keeping.** A released artefact that *looks* like primary evidence — a circuit
file, published by the authors, offered expressly for cross-checking gate angles — outranked the
paper's own text in two independent analyses here. It should not have. When an artefact and the
publication disagree, the publication describes the experiment; the artefact describes whatever was
exported. Check the physics for which one is coherent: at h/|J| = 2 the phenomenon §V reports
cannot occur, and that alone should have settled it without needing the full text at all.

**What the review established about the consequences** (two reviewers, independently, in circuit
order, noiseless):

- At h/|J| = 2 the dimer / emergent-Gauss-law / B_W₀ framework **does not apply**. The
  sector-restricted effective theory is first order in h/|J|, so it is not a controlled
  approximation when the field dominates. Operationally, the probability of remaining in the
  defect-free sector collapses from 1.0 to 0.13–0.63 within a *single* Trotter step, against the
  slow O((h/|J|)²) leakage the h ≤ 0.5 design assumes. [measured]
- Noiseless in-sector weight: 0.55 at N = 9, 0.11 at N = 12 — i.e. falling with system size, so on
  the reference's 7×8 torus Gauss-law post-selection would keep an exponentially small fraction of
  shots even at zero noise. [measured]
- Defect density per triangle at h = 2 reaches 0.11–0.18, up to ~69% of the infinite-temperature
  value 0.25. [measured]
- **Q2 is unaffected either way:** it is a ground-state ED statement, and the 3–5× weakening holds
  at h = 2 as well (ratio 4.98 on the matched 4×4 pair). [measured]
- The released quench4 circuits also prepare `ry(0)` on all 54 qubits with **zero** `x` gates, so
  they encode *neither* candidate winding-sector initial state. (Narrowed by the resolution above:
  the two sectors *are* identified in the release, as the `quench4_min_winding_*` and
  `quench4_max_winding_*` data files; it is the explicit bitstrings and matching circuits that are
  absent. See T-5.) [measured]

**The decision taken at the time, since superseded.** With §V's body believed unreadable, the
options were:

- **(a) CHOSEN 2026-10-15, then WITHDRAWN the same day.** Keep h ≤ 0.5 and state the work as a
  deliberately chosen, self-contained study of the weak-field regime with no published
  counterpart, dropping every "matching §V" claim. **Withdrawn** once Figure 4(e) was read: the
  published counterpart exists and the match is real, so this framing understated the work.
- **(b) Not chosen, and now moot.** Build a genuine h/|J| = 2 study. There is no reason to: the
  reference's triangular experiment is itself at 0.3.

**The weak-field argument, which survives the reversal.** It no longer carries the choice of
h/|J| = 0.3 — Figure 4(e) does that — but it remains true, and it is why the reference's own
choice of a weak field is the right regime and why this thread's conclusions are safe there:

- The sector-restricted / quantum-dimer description is an effective theory to **first order in
  h/|J|**. It needs h ≪ |J| to be a controlled approximation at all.
- Leakage out of the defect-free sector scales as about **h²** (the measured exponent is 2.08),
  so at h ≤ 0.3 the in-sector population stays dominant and conditioning on it is a correction
  rather than a reinterpretation.
- The project's own field scan already shows the in-sector verdicts stable for h ≤ 0.3 and
  straining at h = 0.5 (26% of the weight out of sector) — so 0.3 sits inside the validated range
  and 0.5 is its stress point.
- At h/|J| = 2 none of that holds: noiselessly the in-sector probability collapses to 0.13–0.63
  within a *single* Trotter step, and the in-sector weight falls with system size (0.55 at N = 9,
  0.11 at N = 12), so on the reference's 7×8 torus Gauss-law post-selection would retain an
  exponentially small share of shots even with zero noise. [measured]

This is also the decisive consistency argument: the phenomenon §V reports — dimer correlations
relaxing toward Markov-chain Monte Carlo values inside winding sectors — cannot occur at
h/|J| = 2. That alone identified which of the two conflicting sources had to be wrong, before the
paper's text was ever retrieved.

**Scope of the documentation change, as it now stands.** No physics constant was changed at any
point, and no number moved: `h = 0.3` and `dt = 0.25` are exactly as they always were, and the
suite is unchanged at 274/274 on three platforms. The net effect on the documentation is:

- Q3 and the Gauss-law write-ups describe the configuration as matching the reference's §V, cited
  to Figure 4(e), and additionally carry the weak-field argument above.
- Q2 is relabelled as a **ground-state** exact-diagonalization result — a genuine improvement that
  survives independently of all this — and noted to be robust either way: the 3–5× weakening also
  holds at h/|J| = 2 (4.98 on the matched 4×4 pair, against 4.59 at h = 1). [measured]
- The released quench4 circuits are documented as unsafe for inferring the experiment's
  parameters, in `research/05-zenodo-dataset-map.md`.
- `config.py`'s triangular blocks, the report, the findings map and the README cite the reference
  for the field again, with Figure 4(e) as the source.
- The research notes and handoff briefs that recorded the original readings were **not
  rewritten** — they are dated records, and rewriting them is what would make a conflict like
  this hard to find again. Each carries a dated note pointing here. The notes added on
  2026-10-15 under the withdrawn framing were themselves corrected rather than layered over,
  since they were a day old and wrong.

**T-5, narrowed (independent of the field question).** The released quench4 circuits prepare
`ry(0)` on all 54 qubits with zero `x` gates, so the circuits encode neither candidate
winding-sector initial state. But the two sectors **are** identified in the release, as the
`quench4_min_winding_*` and `quench4_max_winding_*` data files. So what is missing is the explicit
initial bitstrings and circuits matching them, not the sector identification itself. [measured]

---

## OPEN-2 — The Q1 lattice

**Status: DECIDED in principle, implementation pending.**

The original Q1 design was "the same physical observables, encoded vs the released physical-qubit
data, with encoding as the only axis that varies". That cannot be run:

- Iceberg uses k+2 code qubits plus a syndrome ancilla and a flag, i.e. **k+4 physical** with k
  even. The reference's 7×8 lattice (56 logical) therefore needs **60 > 56** physical qubits.
  [derived]
- The design is a single Iceberg block; two blocks would need ≥ 62 physical qubits, and inter-block
  logical ZZ would no longer be the native weight-2 gate. So 7×8 cannot be encoded on H2 in any
  variant. [derived]
- Largest lattices that fit 56 physical qubits: 4×13 (56), 5×10 (54), **6×8 (52, closest in shape
  to 7×8)**, 6×6 (40). [derived]
- The project already made exactly this reduction for Q3 (6×6 and 3×4) but never for Q1.

**Decision:** Q1's head-to-head is **encoded vs bare, matched shots, on one reduced lattice that
fits both arms** (6×8 recommended). The released 7×8 data becomes an external reference:
quantitative at step 1 via an exact light-cone finite-size correction (the step-1 Z₂ pair average
moves only slowly with N — 0.7653 at 4×4, 0.7610 at 4×5, 0.7503 at 7×8 [measured]), and a trend
comparison thereafter.

**Still to do:** recompute the η crossover on the chosen non-degenerate lattice (the headline
η\* = 0.25 comes from the degenerate 2×2 4-site ring; η\* rises to 0.36 at 2×3 and 0.44 on a true
4×4 torus, so the margin improves — but the number quoted should match the lattice actually used).

---

## OPEN-3 — Randomized compiling (implemented 2026-10-16; submission path still open)

**Status: IMPLEMENTED 2026-10-16, and the `[unverified]` gate-count item below is now measured.
What remains open is the hardware submission path (the `nexus` backend), not the twirling. This
is still a precondition for the Q1 conclusion, not a refinement.**

**What exists now.** `src/twirl.py` twirls every `ZZPhase` (and `XXPhase`, unused in practice),
threading a Pauli frame through the H/CX-only syndrome segments and across their resets;
`encoded_tfim.twirl_program` builds one instance of the whole encoded program with its classical
corrections; and `backends_qc.run(..., rc=True, rc_instances=N)` is the switch — OFF by default,
dividing a fixed shot budget over N twirled instances and pooling the records, since randomized
compiling spreads a budget over randomizations rather than granting extra shots. The local-sim,
Stim and Selene paths all consume it. Covered by 86 tests in `tests/test_twirl.py`.

**Two bugs were found and fixed before merge, both by independent review.** Worth recording,
because both were invisible to the tests as first written:
- The fresh random Pauli drawn at each twirled gate was XORed into the frame **without any gate
  being emitted for it**, on the reasoning that it "rides along for free". Free absorption applies
  to a Pauli already physically present, not to a newly drawn one — so every twirled shot carried
  an uncorrected random logical error, even at zero noise.
- `build_stim(..., basis="X")` applied the **Z-basis** correction mask. The data is conjugated by
  H before measuring, so an X-basis readout is flipped by the frame's Z-component, not its
  X-component; it was wrong for every seed tested. The test meant to cover it **could not fail**:
  Stim's `compile_detector_sampler` reference-subtracts, so a noiseless deterministic circuit
  yields all-zero detectors whatever the correction is (corrupting every bit of the mask went
  undetected, 0/36). It now compares raw measurement records in both bases and asserts the mask
  is load-bearing (30/30 corruptions caught).

**Gate-count answer, settling the `[unverified]` item below.** Iceberg 2×2, 3 Trotter steps,
through Selene's native pipeline: **two-qubit gates unchanged (×1.000)** — twirling never adds an
entangler — and **one-qubit native gates 422 → 495 (×1.17)**. So the twirling Paulis do **not**
absorb into the native arbitrary-angle rotations for free; they compile to their own native ops,
each exposed to `p_1q`. See `scripts/twirl_gate_count.py` → `data/twirl_gate_count.txt`. No
committed prediction was rewritten on the strength of this. [measured]

**On the reference's cadence.** 2503.20870 applies RC every two Trotter layers; this
implementation twirls every `ZZPhase`, which is a *superset* of those locations. For a Pauli
channel it is a no-op either way, and against coherent error finer twirling is never worse. So
`EncodedConfig.rc_period` is job-packaging granularity — how many layers go into one submitted
job — not a change to the distribution over twirled circuits, and it stays unused until the
`nexus` backend exists. Any phrasing claiming to "match 2503.20870's RC protocol" would be
inaccurate: this twirls more, not differently.

The "encoding helps at η ≈ 0.05" GO rests explicitly on randomized compiling (decision D-RC,
★ FLAG-0, `report.tex` §Q1, `handoff/11`). It gates the headline Q1 claim, so it is recorded here
as well as in the handoff.

### Randomized compiling is a HARDWARE technique, and twirling the simulation is a no-op

This is easy to misread, so it is worth stating plainly. Randomized compiling conjugates each
entangling gate with random Paulis, runs many instances on the device and averages. Its effect is
to convert the device's *actual* error channel — which has coherent components — into a stochastic
**Pauli** channel.

This project's noise model is **already** a Pauli channel: depolarizing with a ZZ-biased fraction
η (`src/encoded_codes.py`). Twirling preserves a Pauli channel's diagonal, so twirling something
that is already Pauli changes nothing. **Implementing RC and rerunning the predictions would not
move a single number.** [derived]

So the dependency runs the other way round from what "not implemented" suggests. RC is not needed
to *compute* the Q1 prediction; it is needed to make the prediction's central assumption *true of
the hardware*. Without RC on H2, the device is not well described by a Pauli channel and the whole
Stim / first-order accounting stops applying to it.

### Why that threatens Q1 specifically, and not just generally

The failure is not symmetric. `docs/encoded_tfim.md` already works this out: the over-rotation
option is only a "Pauli-twirled stand-in"; un-twirled coherent ε is "the only in-range flip risk,
and this model cannot show the flip itself"; and on a logical-ZZ gate the un-twirled coherent ZZ
component is **ZZ-aligned, which raises the effective η toward the crossover**. η is precisely the
quantity the Q1 verdict turns on (η\* ≈ 0.25 at 2×2). So without RC the error moves in the one
direction, in the one parameter, that erodes encoding's advantage. [inferred, from the project's
own noise analysis]

### What "implementing" it therefore means

Not a classical-prediction change, but **hardware readiness**: emit randomized-compiled circuits
on the submission path, so the emulator and hardware runs can be switched on without further
circuit work, and prove locally that twirling preserves the logic.

For an arbitrary-angle `ZZPhase(α)` the twirl rule is exact and simple: pick a random two-qubit
Pauli P; if P **commutes** with Z⊗Z the gate is unchanged, and if P **anticommutes** the angle is
negated, since `P·exp(−iθZZ/2)·P† = exp(+iθZZ/2)`. The inserted Paulis then propagate to a final
Pauli frame that must be applied to the Z-basis readout. [derived]

When it is built, re-verify the transparency check (encoded == bare at zero noise) with twirling
switched on — this matters more than usual because Iceberg uses mid-circuit measurement and reset,
so the Pauli frame has to be tracked across those.

### One genuine classical-side question it raises

The committed acceptance and undetected-rate predictions are computed on **un-twirled** circuits.
RC inserts Paulis. On H2 these can normally be absorbed into the native arbitrary-angle
single-qubit rotations at no extra gate cost, in which case nothing changes — but that is an
assumption, not a measurement here. If they are *not* absorbed, the single-qubit error budget
grows, and this project already measured that Selene charges `p_1q` on about **3.85× more native
operations** than pytket-level counting suggests (`data/selene_gap.txt`). So the gate-count
overhead of twirling should be checked rather than assumed. [unverified]

---

## DECIDED-4 — Active error correction is in scope for THIS article

**Status: DECIDED 2026-10-16 by the project lead. Active error correction for the distance-3/4
codes (G4 / HW-2) belongs to this article, and nothing is deferred to a later paper.**

Until now the d ≥ 3 codes were run as **detect-and-discard**: a detected fault throws the shot
away. `docs/findings_vs_questions.md` records decoding-instead-of-discarding as "the main lever"
left untouched for Q4. That lever is now in scope.

**Why this matters to the existing Q4 conclusion, and should be stated plainly in the write-up.**
"Iceberg is recommended" currently rests on a comparison in which the distance-3/4 codes are
denied the thing that justifies having distance 3 or 4 at all. They buy ≈1.2× on the undetectable
residual while paying 2.9–3.9× in acceptance and 6.6–8.6× in two-qubit gates — but they pay that
acceptance cost *because* they discard rather than correct. With active correction the trade moves
in their favour by construction, since the discarded shots are the ones a decoder would recover.
So the recommendation is conditional on the detect-and-discard regime, and this decision is what
makes testing that conditional part of the article rather than future work.

**What it implies, not yet built:** a decoder for the Steane / 5-qubit / concatenated codes, the
syndrome extraction to feed it, and a re-run of the Q4 comparison with correction enabled against
the same residual/acceptance/gate-count axes. `handoff/05` already frames this as G4 and requires
it to be designed and verified in Stim and Selene before hardware.

---

## DECIDED-5 — The 6×6 noise-scaling arm (T-17 / R-14)

**Status: DECIDED and built 2026-10-16 by the project lead (D1–D7), classically validated, blind
reviewed (`review/15`). Nothing has run on H2.** Every number is a classical prediction under the
ASSUMED research/06 prior. Design: `docs/q3_noise_scaling.md`. Derivation:
`research/derivations/01-noise-scaling-arm.md`. Sources: `research/07-noise-scaling.md`.

### D-NS1 — Purpose (2026-10-16)
Decided: diagnostic first; extrapolation only when its χ² test passes. Options: diagnostic only | ZNE only | both.
Why: T-17 needs "does it move with the noise", and the same runs give the extrapolation. By: user.
Rests on: derivations/01 (d); 2407.04770 (precedent). Revisit if: H2 time is so short that only λ = {1, 3} fits.

### D-NS2 — Amplification (2026-10-16)
Decided: Pauli insertion before the 2q gates for the λ ladder, plus one folded λ = 3 point. Options: insertion | folding | both.
Why: insertion is the reference's method and costs ≈ 1× HQC; the fold tests the insertion model. By: user.
Rests on: 2503.20870 §VII.2, 2005.10921, derivations/01 (a, b). Revisit if: a learned H2 noise model (G2) disagrees with the fold check.

### D-NS3 — Arms scaled (2026-10-16)
Decided: bare + Gauss post-selection only; Iceberg runs at λ = 1. Options: bare only | also Iceberg.
Why: at λ = 3, Iceberg survives only to t ≈ 1.4 at 6×6 [derived accounting]. By: user. Rests on: derivations/01 (c).
Revisit if: H2's real error is far below the prior.

### D-NS4 — λ set and fit (2026-10-16)
Decided: λ = {1, 2, 3}, exponential. Options: {1, 2, 3} | {1, 3} | {1, 4}.
Why: the third point makes the fit falsifiable. By: user. Rests on: derivations/01 (d). Revisit if: the budget forces the diagnostic-only fallback {1, 3}.

### D-NS5 — Fit asymptote (2026-10-16)
Decided: fixed at the infinite-T value (B_W₀ conditioned, the full-space value raw). Options: fixed B_W₀ | free | the reference's 0.
Why: it leaves 1 dof for χ²; the reference's B = 0 is biased for densities. By: user.
Rests on: derivations/01; Cai 2007.01265; Kim 2023. Revisit if: the χ² test fails systematically on H2 data.

### D-NS6 — Folded circuits compile at TKET level 0 (2026-10-16)
Decided: `NoiseScalingConfig.compile_opt_level = 0`; frozen tests T4/T5 moved to 3×3; new frozen test T17. Options: 3×3 + T17 | 3×3 only | dense oracle.
Why: an offline H2-1 compile at levels 1–2 (2 is the default) cancels ZZ(a)ZZ(−a)ZZ(a), giving 2Q counts of 27/27 instead of 27/81 [measured]. The λ = 3 point would silently run as λ = 1. By: user.
Rests on: research/07 (no-opt), review/15. Revisit if: the submission path (`nexus`) is built. Server-side optimisation must also be off.

### D-NS7 — 6×6 window and resolution (2026-10-16)
Decided: t = 1–3, slope resolution 0.005 per unit λ, one fold at t = 2: ≈ 8.3×10⁴ HQC [derived estimate].
Options: t ≤ 3 @ 0.005 | t ≤ 8 @ 0.01 (≈ 4.4×10⁵) | 500 shots per circuit (≈ 5.3×10⁴).
Why: late λ = 3 points lose ~98% of shots to post-selection. By: user.
Consequence: **no late-time (t > 3) 6×6 value may be called thermalization.** Revisit if: G2 gives H2's real 2q error. Recompute the plan then.

---

## OPEN-4 — Where the 6×6 physics runs (opened 2026-10-17)

**Status: OPEN, the project lead's call. Nothing is blocked today; the Q1 and small-lattice work
proceeds without it.**

**The question.** The Q3 noise-scaling arm (DECIDED-5) lives on 6×6 = 36 spins (bare / Gauss
post-selection) and 40 physical qubits (Iceberg). H2 *hardware* has 56 qubits, so the circuits fit
there (the emulators are narrower; see below). The classical machines this project owns cannot
*simulate* them as exact state vectors [derived]:

| arm | qubits | amplitudes × 16 B | this host |
|---|---|---|---|
| 3×4 bare / Iceberg | 12 / 16 | 64 kB / 1 MB | fine |
| 6×6 bare | 36 | ≈ 1.1 TB | ~6 GB RAM |
| 6×6 Iceberg | 40 | ≈ 17.6 TB | ~6 GB RAM |
| 6×8 Iceberg (G3, Q1 headline) | 52 | ≈ 72 PB (7×10^4 TB) | impossible |

**Why batching does not help.** A state vector must hold every amplitude at once, because each
gate mixes amplitudes across the whole vector. Splitting a run into batches splits the *shots*, and
every shot still needs the full state. Out-of-core simulation would need 1–18 TB of disk and is
orders of magnitude too slow.

**What does run locally at 6×6 (and is already used):** Stim at Clifford angles (exact, unbounded;
checks circuit logic, post-selection, wiring), plus gate counts, the O0 fold-survival check and the
HQC cost. **What does not:** a noiseless or noisy 6×6 *physics* curve.

**The Nexus emulator has its own width limit, and it is below 6×6.** Quantinuum's emulator
documentation (docs.quantinuum.com, "System Model H2 Emulators", read as search-result excerpts on
2026-10-17; the page itself was blocked by this container's network policy, so re-read it
directly) lists for **H2-1E / H2-2E: 32 qubits in state-vector mode, 56 in stabilizer mode**, and
advises state-vector runs below 28 qubits. Stabilizer mode is Clifford-only. [unverified: confirm on
the page; confirm with a free H2-1SC acceptance test.] So, for non-Clifford circuits:

| run | qubits | H2-1E state vector (≤ 32)? |
|---|---|---|
| Q1 headline at 6×8 (G3 as first drafted) | 52 | **no** |
| 6×6 noise-scaling arm, bare / Iceberg | 36 / 40 | **no / no** |
| Q1 at 4×5 (k = 20, Iceberg 24, bare 20) | 24 | yes; also within this host's SCOPE §5 ceiling |
| Q1 at 4×6 (k = 24, Iceberg 28, bare 24) | 28 | yes (at the recommended limit) |
| Q3 at 3×4 (bare 12, Iceberg 16), 3×6 | ≤ 22 | yes |

So the 6×6 target (T-18) and the 52-qubit Q1 lattice can run only on **real H2 hardware**, for
which the usage page shows no allowance, or in a classical simulator this project does not have.

**Options for 6×6 physics.**
1. **Shrink the target to what the emulator can run** (≤ 28–32 qubits): e.g. Iceberg-encoded
   triangular 4×6 (28 physical) and bare 5×6 (30). Loses the 6×6 / 9×6 size story; keeps the
   noise-scaling method, which is the point of T-17.
2. **Real hardware (H2-1 / H2-2)** for the full 6×6 arm: needs a hardware allowance that is not on
   the usage page, and a separate budget decision (≈ 8.3×10⁴ HQC under D-NS7, more than the whole
   50k emulator allowance even if it applied).
3. **A tensor-network (MPS) classical simulator** as the independent anchor. PECOS ships an `MPS`
   simulator class [measured: present in the pinned LE environment]; whether it is accurate at the
   entanglement these quenches generate is untested [unverified], and PROC-2 froze new classical
   depth, so this needs approval.
4. Drop the 6×6 arm and keep 3×4 as the largest lattice with a classical cross-check.

**Recommendation:** 1 for Q1 (move the headline lattice from 6×8 to 4×5, which also runs on this
host's local emulator, so the same circuits are cross-checked locally and on H2-1E), and for Q3
run 3×4 first, then decide between 1 and 3 for the noise-scaling arm once the free SC has confirmed
the width the emulator accepts.

**Also recorded (2026-10-17):** the 50,000 HQC shown on the Nexus usage page are for **H2-1E / H2-2E
(emulators)**; the syntax checkers are unlimited and free. No real-hardware allowance is shown, so
every HQC estimate here is for the emulator [inferred from the usage page]. The SC tier is
pre-approved by the project lead; every HQC-spending run still needs a per-run go.

---

## Applied corrections (no decision needed)

These were wrong independently of the decisions above and have been fixed:

| what | where |
|---|---|
| Defect-density and P_out "Trotter inflation" figures were attributed to the reference circuit; in the published circuits' gate order the bias has the **opposite sign** | `docs/q3_thermalization.md`, `docs/gauss_law_dimers.md`, `docs/findings_vs_questions.md`, `docs/report/report.tex` |
| The circuit sign check compared magnitudes only, while the report claimed it checked gauge signs | `scripts/run_compare.py`, `docs/report/report.tex` |
| Text I/O used the platform default encoding, breaking the project on Windows | all of `src/`, `scripts/`, `main.py`, `config.py` |
| `python -I main.py` failed, though the project documents `-I` as the convention | `main.py` |
| Step-1 H2-vs-simulation gap quoted as ≈3σ; against the exact N = 56 value it is ≈2.0σ | `docs/q1_compare.md` |
| Gate-count penalty for the distance-3/4 codes quoted as 3–7×; matched-lattice value is 6.6–8.6× | `docs/encoded_tfim.md` |
| Assorted doc/data mismatches (13× vs 32×, acceptance ratios, slopes, "one early point", stale memory figures and test counts) | various |

The full review, with the evidence for each item, is in the peer-review reports kept with the
project lead (three independent reviewers, three platforms, three rounds).
