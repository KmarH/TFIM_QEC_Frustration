# Handoff 01 — Concatenated Iceberg (d=4) fault-tolerant syndrome gadget

**Route to:** Claude Code (SCOPE §10/§14 — dense algorithm design / construction
with no single literature target to check against). **Agents cannot launch it; Kevin
runs it.** Written by qc-overseer during the hands-off BUILD run.

## Why this is a hard stop (not invented)
The single-level Iceberg [[k+2, k, 2]] code is fully specified by its primary source
(arXiv:2211.06703) and is IMPLEMENTED + VERIFIED in this repo:
- `src/qec/iceberg.py` — stabilizers S_X, S_Z and logicals Xbar_i=X_tX_i, Zbar_i=Z_bZ_i.
- `src/qec/verify.py` — confirms the stabilizer group, logical algebra, and that every
  weight-1 Pauli error is detected (distance-2 detection), for k=2,4,6.
- `src/qec/syndrome.py` — two-round Stim syndrome-extraction circuit; clean runs are
  silent and every weight-1 data error fires a detector (verified in tests/test_qec.py).

The **concatenated d=4** code is different. SCOPE §6 names "concatenated Iceberg d=4"
as an implemented path, but:
1. Concatenating a distance-2 code with itself giving distance 4 is a standard EXPECTATION,
   but the explicit **fault-tolerant syndrome-extraction gadget** for the concatenated
   Iceberg (ancilla scheduling, flag-qubit placement, order of inner/outer checks, and
   the discard logic across levels) is NOT pinned to a single equation set in the sources
   fetched (arXiv:2211.06703 gives the single-level gadget; 2504.21172 gives co-compiled
   gadgets; 2608.06187 is future-dated and must NOT be trusted — see SCOPE §11).
2. Designing that gadget correctly (fault-tolerantly, so one physical fault cannot cause
   an undetected logical error) is dense algorithm design. Inventing it here would violate
   SCOPE §12 ("never invent results") and §10/§14 (route such work to Claude Code).

A generic distance *probe* (`src/qec/concatenated.py:min_undetected_weight`) is provided
and correctly measures single-level Iceberg distance = 2, so once a concatenated stabilizer
group is supplied the distance claim can be checked immediately — but the group + gadget
themselves are the deliverable below.

## Goal
Produce, with correctness arguments, the concatenated Iceberg code targeting distance 4:
(a) its stabilizer generators and logical operators as explicit Pauli strings on the
physical register, and (b) a fault-tolerant syndrome-extraction circuit (Stim) with the
discard/post-selection rule, such that the repo's verifier confirms detection distance 4
and the circuit's clean run is silent while all weight ≤ 3 errors are detected.

## Physical context
- Base code: Iceberg [[k+2, k, 2]], QED (post-selection on any −1 stabilizer), tailored to
  all-to-all trapped-ion connectivity (Quantinuum H2). Logicals have weight-2 physical
  support; stabilizers S_X, S_Z span all physical qubits.
- Concatenation intent: re-encode the physical qubits of an outer Iceberg block into inner
  Iceberg blocks so a single physical fault is caught at the inner level before it can
  become an outer logical error — raising the detection distance from 2 toward 4.

## Inputs (already in repo)
- `src/qec/iceberg.py`, `src/qec/verify.py`, `src/qec/syndrome.py`, `src/qec/concatenated.py`.
- `research/02-stage2-iceberg.md` (code definition, status-tagged).
- Stim 1.16.0 installed in `.venv` (Python 3.12 — see handoff/plan.md for the 3.11 flag).

## Constraints
- No new citations invented; if a construction is used, cite a resolvable source or mark it
  explicitly as a derived construction with a correctness proof.
- Must plug into `verify_code` / `min_undetected_weight` (stim.PauliString interface) and the
  two-round detector-sampler pattern in `syndrome.py`.
- Local/Stim only; no hardware. Memory is not a concern (stabilizer sim).

## Equations / objects to produce
1. Physical qubit layout and index map for the concatenated register.
2. Full stabilizer generator list S_i (Pauli strings) and logical Xbar/Zbar.
3. FT syndrome-extraction schedule (which stabilizers, ancillas, flags, order).
4. The discard predicate across concatenation levels.

## Done-check
- `verify_code(...)`: stabilizers commute, logicals commute with stabilizers, symplectic
  algebra holds.
- `min_undetected_weight(n, stabilizers, max_weight=4) == 4` (detection distance 4).
- A Stim syndrome circuit whose clean run is silent and that detects every weight ≤ 3 error;
  the post-selection (discard) rate under a given per-gate error rate is reported, not asserted.

## What the reviewer must verify
- That the claimed distance 4 is the MEASURED first-undetected weight (not assumed from
  "2×2"), that the gadget is fault-tolerant (one fault → detected, never silent logical
  error — check with Stim circuit-level error injection, not just code-capacity Paulis), and
  that the post-selection rate is computed from a stated noise model, with uncertainty.
