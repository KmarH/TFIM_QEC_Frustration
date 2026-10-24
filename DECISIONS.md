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

**The full evidence trail** - the paper quotations, the Zenodo QASM gate-count table, the
independent cross-checks and the list of corrections applied - was moved to
[`docs/resolved-1-triangular-field.md`](docs/resolved-1-triangular-field.md) on 2026-10-23
to cut per-session context. It is unedited; this entry is the summary, that file is the record.

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

## DECIDED-6, formerly OPEN-4 — Where the 6×6 physics runs (opened and decided 2026-10-17)

**DECIDED 2026-10-17 (the project lead):** (1) the Q1 headline lattice is **4×5** (24 physical qubits encoded, 20 bare; server-quoted 11,636 HQC); (2) the 6×6 noise-scaling arm is **shrunk to 3×4 / 3×6** (the λ ladder at 3×4, the bare size story at 3×6); the 6×6 circuits stay a Stim-only design, run nowhere. Built as the `Q3-*` groups of `src/h2_driver.py` (handoff/14). The analysis below is the record that led to it.

**D-HQC (decided 2026-10-17, the project lead):** `src.h2_circuits.hqc_estimate` is Rz-free by default, because the free H2-1SC quoted Rz (plain and conditional) as free [measured]. One frozen assertion changed (`tests/test_h2_circuits.py`, 5.74 → 5.72); new SHA-256 `ab1eaf63632a51171e71abebf8997cbaf752766d9d55e81c74880744eb02b147` (old `dceab7c37f6c110463c1f0f3e07e87f7f7c29af350294444ac2308cdc5e2ed80`).

**Original status line (before the decision): OPEN, the project lead's call.**

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
documentation (docs.quantinuum.com, "System Model H2 Emulators" and "Quantinuum Emulators", read in
full on 2026-10-17 [established]) lists for **H2-1E / H2-2E: 32 qubits in state-vector mode, 56 in
stabilizer mode**, advises state-vector runs below 28 qubits, and says the stabilizer emulator is for
circuits "involving only Clifford operations". [The free H2-1SC acceptance test is still worth running
to confirm the width the server accepts.] So, for non-Clifford circuits:

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

## DECIDED-7 — The Q3 generalization study, and the encoded λ runner (D1–D6, 2026-10-22/23)

**Why.** The Iceberg-vs-Gauss-law conclusion of `docs/q3_thermalization.md` §9.2 — Gauss-law
post-selection of the bare circuit beats Iceberg encoding for Q3 diagonal observables — rested on
a **single grid cell** (N = 12, h = 0.3, λ = 1). A single cell cannot separate a general statement
from an accident of one lattice at one field at one noise strength, and the project's Q3
recommendation rests on it. Write-up: `docs/q3_scaling.md`; data: `data/q3_scaling.txt`,
`data/q3_sweep.txt`.

### D1–D5 — The axes and the method (2026-10-22)
- **D1 sizes:** N = 12 (3×4 flippable), 18 (3×6 3-sublattice), 20 (4×5 flippable), each mapped to
  an already-validated case; N = 36, 54 in the Stim stage only.
- **D2 fields:** h = 0.1, 0.2, 0.3, 0.5 (the existing `Q3BaselineConfig.h_curves`).
- **D3 noise:** the existing λ = 1, 2, 3 insertion ladder, extended to the encoded arm (see D6).
- **D4:** one axis at a time around the published cell plus three extreme combinations, behind a
  cheap Stim-only prefilter; the full 36-cell cross product is priced but not run.
- **D5:** a wall-clock probe before the trajectory budget is committed.

### D6 — Build the encoded λ runner, rather than infer it (2026-10-22)
**The gap, found during implementation:** the repository could amplify noise on the **bare** arm
only (`src/noise_scaling.run_bare_scaled`). D-NS3 had scaled "bare + Gauss only" and the exclusion
was never revisited in code, so the λ ladder had no encoded arm at all. The sweep therefore
**raised** rather than return λ = 1 Iceberg numbers under a λ > 1 label.

Options put to the project lead: (a) build `run_iceberg_scaled`; (b) drop Iceberg from the λ axis;
(c) take Iceberg's λ dependence from the Stim prefilter alone. **Decision: (a).** The λ axis is one
of the three the study exists to test, and a Stim-only answer would have been first-order
accounting compared against trajectory measurements on the other arm — not a like-for-like
comparison.

**What was built** (`src/noise_scaling.run_iceberg_scaled`, additive; spec frozen in
`tests/test_iceberg_scaled.py` **before** the function existed, SHA-256 `30837339…8f99`, verified
failing on import first; 13/13 pass):
- Pauli insertion before every 2-qubit gate of the encoded circuit — logical ZZ rotations **and**
  syndrome-extraction CX gates — the same mechanism and channel as the bare arm, so both arms of
  the ladder are amplified alike; 1q, SPAM and idle noise stay at λ = 1.
- **λ = 1 is bitwise identical** to `run_iceberg` at the same seed, so the ladder's λ = 1 rung
  stays comparable to the published cell.
- `method="fold"` is **refused**: folding the encoded circuit would fold its syndrome CX gates too,
  changing the code's detection structure and not only its error rate. That is a separate design
  question and is not assumed here. **This remains open if a folded encoded point is ever wanted.**

### Comparison rule — matched survival, not matched window (2026-10-22)
At the assumed prior, Iceberg's detector survival over the published 48-step window is 0.069 at
N = 12 but 0.021 at N = 18 and 0.014 at N = 20, and each λ step roughly halves the reach
[derived, `data/q3_scaling.txt`]. Comparing every cell over the same window would pit ~2 %-survival
noise against 7 %. **Each cell's encoded arm therefore runs to the largest window whose predicted
survival still clears 5 %, and every cell states its own window.** The shrinking encoded reach is
reported as a result, not absorbed into the error bars. Consequence to keep in mind when reading
the λ rows: they cover shorter (easier) windows, so Iceberg's measured λ degradation is if anything
understated.

### HQC
Offline `hqc_estimate` plus the free H2-1SC quotes; the machine the study ran on has no
`NEXUS_REFRESH_TOKEN`, so the server quotes are pending one. **Nothing was submitted to a paying
tier and no HQC was spent.**

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
