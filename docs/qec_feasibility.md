# QEC feasibility analysis (SCOPE §6, §2 Q4)

> **Superseded (2026-10-09).** This is the early Stage-2 feasibility note. All four codes were later built, run end to end and compared with data (concatenated d=4 included); the current Q4 answer is `docs/encoded_tfim.md` Part B (B5) and `docs/findings_vs_questions.md` Q4. Kept for the record.

Status: Stage-2 feasibility notes. Code definitions are verified in Stim
(`tests/test_qec.py`); the lattice-feasibility judgments below are reasoned,
status-tagged, and to be revisited with data at later milestones. Never asserts a
number that was not measured.

## Scope
SCOPE §6 splits the four QEC codes into an **implemented path** (Iceberg d=2 and
concatenated Iceberg d=4) and an **on-paper path** (5-qubit d=3, Steane d=3), the
latter getting Stim-level definitions + this written feasibility analysis rather
than full lattice simulations.

## Verified in this repo (Stim) [verified]
| Code | [[n,k,d]] | stabilizers commute | all weight-1 detected | measured detection distance |
|------|-----------|:-------------------:|:---------------------:|:---------------------------:|
| Iceberg (k=2) | [[4,2,2]] | yes | yes | 2 |
| Iceberg (k=4) | [[6,4,2]] | yes | yes | 2 |
| Iceberg (k=6) | [[8,6,2]] | yes | yes | 2 |
| 5-qubit perfect | [[5,1,3]] | yes | yes | 3 |
| Steane | [[7,1,3]] | yes | yes | 3 |

(Distance = first error weight that is undetected, from
`src/qec/concatenated.min_undetected_weight`.)

## Iceberg [[k+2, k, 2]] — implemented path [verified definition]
- **Why it fits the TFIM lattice sims:** encodes k logical qubits in only k+2
  physical qubits (optimal distance-2 overhead) with weight-2 logical operators and
  all-to-all friendly gadgets — matches the H2 trapped-ion target and keeps the
  physical register close to the unencoded size. This is the natural logical-vs-
  physical comparison code for SCOPE Q1 on the non-frustrated (square) lattice.
- **Cost:** +2 code qubits + 2 syndrome ancillas = +4 physical qubits total; QED
  post-selection discards any shot with a −1 syndrome, so the sampling overhead
  grows with circuit depth and physical error rate. The discard rate must be
  MEASURED under a stated noise model (not assumed) — deferred to a noisy-sim milestone.

## 5-qubit perfect code [[5,1,3]] — on-paper [verified definition]
- **Capability:** distance 3 → corrects any single-qubit error (not just detect).
  Smallest code that does so (non-CSS, cyclic stabilizers).
- **Feasibility on a non-trivial lattice:** encoding ONE logical qubit costs 5
  physical qubits + syndrome ancillas, and its stabilizers are weight-4 mixed-type
  (XZZXI …), so each syndrome extraction is a weight-4 entangling measurement. For a
  lattice of L logical sites that is 5L+ physical qubits with weight-4 checks per site
  — far heavier than Iceberg's shared weight-n stabilizers. **Judgment [inferred]:**
  usable for single-logical-qubit gadget studies and as a distance-3 reference, but
  a full L-site TFIM lattice in the 5-qubit code is not tractable at the local
  statevector ceilings and is overhead-dominated on H2 vs Iceberg. Keep on-paper.
- **Non-CSS caveat:** no transversal CNOT; logical Clifford set needs more care than
  the CSS codes — another reason it is a reference, not the lattice workhorse.

## Steane code [[7,1,3]] — on-paper, FLAGGED open risk [verified definition]
- **Capability:** CSS distance-3, corrects one error; transversal Clifford group
  (incl. CNOT, H, S) — attractive logically.
- **Feasibility on a non-trivial lattice:** 7 physical qubits per logical qubit plus
  6 stabilizer generators (weight-4 each) and syndrome ancillas. For an L-site TFIM
  this is ≥7L physical qubits — SCOPE §6 explicitly flags Steane's qubit cost on a
  non-trivial lattice as an **open risk**, and that stands: a multi-site Steane-encoded
  TFIM is the most qubit-expensive of the four and is not planned as a full lattice sim.
  **Judgment [inferred]:** implement/verify the single-logical gadget in Stim (done),
  use it for a distance-3 CSS comparison, but do not attempt a full encoded lattice.

## Concatenated Iceberg d=4 — implemented path, NOT YET BUILT [handed off]
The explicit fault-tolerant concatenated gadget is a construction with no single
literature target to check against; per SCOPE §10/§14 it is routed to Claude Code.
See `handoff/01-concatenated-iceberg-d4.md`. The distance-measurement machinery to
check it on arrival is already in `src/qec/concatenated.py`.

## Which works best, and why (preliminary, SCOPE Q4) [inferred — to be backed by data]
- For the logical-vs-physical TFIM comparison on the square lattice, **Iceberg d=2**
  is the right implemented workhorse: minimal overhead, lattice-friendly, matches the
  H2 target and the reproduction article's regime. Concatenated d=4 is the next step
  for stronger protection once its gadget is derived (handoff 01).
- 5-qubit and Steane are kept as distance-3 references (single logical qubit): they
  CORRECT rather than merely detect, but their per-logical overhead and (for 5-qubit)
  non-CSS gate structure make a full TFIM lattice impractical at current ceilings.
- Final ranking is a DATA question (post-selection rate, logical error rate vs physical
  error rate, accessible evolution time) and must be answered with uncertainties at the
  noisy-simulation milestone, compared fairly to the unencoded reference.
