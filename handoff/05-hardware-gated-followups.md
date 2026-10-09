# Handoff 05 — Hardware-gated follow-ups to handoff 04: H2 gate-error composition, active correction, first Nexus run

**Status: DEFERRED (the project lead, 2026-10-07)** until Quantinuum Nexus / H2 access exists and SCOPE §5 is satisfied: `allow_hardware=True` plus explicit per-run approval.
**Written by:** Claude Code, at the project lead's request. Normally qc-overseer writes briefs, so the overseer may adopt, rework or split it. The registry entry is `handoff/plan.md` §12. Open items are also tracked in `Conversation history/open-questions.md` (HW-1 … HW-5).

## Why this exists
Handoff 04 delivered the classical encoded-TFIM baseline and its build/discard decisions (`docs/encoded_tfim.md`). Two of its questions can't be settled classically, and the project lead chose to answer them on hardware rather than from literature or simulation alone:

1. **Does encoding help on H2 at all? (HW-1)**
   - The Stim sensitivity check shows the code *ranking* (Iceberg over Steane / 5-qubit / concat d=4) is robust.
   - **Whether any encoding beats the bare circuit is not robust.** It flips once the ZZ fraction η of H2's native two-qubit gate error exceeds ≈ 0.25, and coherent over-rotation erodes it further.
   - **This is a go/no-go input for the article thesis (journal ★ box, Q1 spine).**
2. **Can active correction rescue the d ≥ 3 codes? (HW-2)** Run as detect-and-discard, they keep 3–5× fewer shots than Iceberg for only ~1.2× less undetected error.

## Goals (in order, each gated as stated)
- **G1 — calibration run (HW-5).** Flip `backend="nexus"` for **Iceberg 2×2, 1 Trotter step, on the H2 emulator**. Compare the discard rate and logical Z2 against the Selene and Stim predictions *before* any hardware HQC. Then repeat on hardware once the project lead approves the cost.
- **G2 — measure the inputs that decide HW-1.**
  - Obtain H2's native two-qubit gate error composition (η = ZZ share, over-rotation ε) from the best available source, labelled as such: the H2 emulator's noise model; device benchmarking; the published characterization in arXiv:2503.20870 (qc-researcher, full text; currently [unverified]).
  - Then **rerun `scripts/run_noise_sensitivity.py` at those values** and state whether encoding is predicted to help.
- **G3 — the decisive direct test.** Run **encoded (Iceberg) and bare** versions of the same TFIM circuit on H2 at matched shots, and compare post-selected Z2 deviation and discard rate per step. This answers HW-1 directly, without needing η.
- **G4 — active correction (HW-2), design locally first.**
  - Add a decoder (lookup table for d = 3; concat inner/outer decoding) to the Part B schedule, so syndromes are corrected rather than discarded.
  - Verify it in Stim (logical failure rate and acceptance) and on Selene (real-time feedforward), then test on hardware.
  - Report whether it changes the Part B ranking.

## Decisions recorded since this brief (the project lead, 2026-10-08; open-questions R-7, R-14, R-15)
- **Randomized compiling** on every encoded H2 run (R-7).
- **Q3 lattices for the encoded H2 run:** **6×6** (40 physical) and the minimal relevant **3×4** (16 physical). 9×6 does not fit Iceberg on 56 qubits (R-15).
- **T-17 rule:** an H2 Q3 curve is never called thermalization without comparing it with the noise. At 3×4 the classical noisy prediction exists (`data/q3_noisy.txt`); at 6×6 it cannot be computed (36 > 24 spins), so the run **includes a noise-scaling arm** (R-14).
- Expect the 6×6 Iceberg arm to reach only early times under the assumed prior (survival 10% at t ≈ 3.8; `data/q3_size.txt`).

## Inputs (already in the repo)
- `src/encoded_tfim.py`, `src/backends_qc.py`: Part A (Iceberg), with the toggle and the `nexus` stub.
- `src/encoded_codes.py`: the generic pipeline for all four codes (schedule → local-sim / Stim / generated Guppy on Selene), measured accounting, and the noise options (`zz_bias`, `overrot`, `p_idle`).
- `scripts/run_encoded.py`, `scripts/run_encoded_codes.py`, `scripts/run_noise_sensitivity.py`, `scripts/diagnose_selene_gap.py`.
- `docs/encoded_tfim.md` (Parts A and B, the sensitivity check, the Selene gap) and `docs/nexus_toggle.md` (the integration steps).
- Data: `data/encoded_iceberg.txt`, `data/encoded_codes.txt`, `data/noise_sensitivity.txt`, `data/selene_gap.txt`.

## Constraints
- **SCOPE §5:** nothing reaches Nexus or hardware without `allow_hardware=True` **and** the project lead's per-run approval, with the HQC cost estimate recorded. Credentials never go in the repo.
- **Dependencies:** pin `qnexus` and/or `pytket-quantinuum` after confirming the live versions. FLAG A (Python 3.11 vs 3.12) must be decided first.
- **Labelling:** every number states whether it is a classical prediction, an H2-*emulator* result or an H2-*hardware* result. Never mix them.
- Stim remains the fault-tolerance verifier. Hardware data does not prove fault tolerance.
- No local code is deleted. Only the `nexus` stub's `raise` is replaced (see `docs/nexus_toggle.md`).

## Objects / equations
- Iceberg undetected residual per logical gate (derived, Stim-verified): p2·(η + (1 − η)·3/15), plus the over-rotation probability sin²ε.
- Crossover against bare (2×2, p1 = p2/10): 12·p2·(0.2 + 0.8η) = 4.8e-3 at p2 = 1e-3 → **η ≈ 0.25**.
- Selene native-count factor: ×3.85 single-qubit exposure (rxy + rz) relative to the pytket-level model, per `data/selene_gap.txt`.

## Done-check
- G1: emulator acceptance and Z2 are reported next to the Selene and Stim predictions, with error bars. Any discrepancy is explained or listed as open.
- G2: η and ε are stated with their source and status tag, and the sensitivity table is rerun at those values.
- G3: encoded-vs-bare on H2 with matched shots, and a yes / no / inconclusive verdict on "encoding helps" at that size and depth.
- G4: the decoder is verified in Stim (no single fault produces an undetected *uncorrected* logical error in the Clifford parts), and the Part B ranking is re-stated with correction.

## What the reviewer must verify
- No emulator or hardware number is presented as a classical prediction, or the reverse.
- The SCOPE §5 approval and HQC cost are recorded for every hardware job.
- The encoded and bare runs are matched (same lattice, steps, shots, θ, observable).
- Any claim that "encoding helps" survives its error bars and states η and ε or the direct G3 result.
