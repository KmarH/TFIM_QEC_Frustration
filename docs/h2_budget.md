# HQC budget for the Nexus H2 emulator (drafted 2026-10-17; refine with the free SC quotes)

**Everything here is an estimate. Nothing has been submitted and no HQC has been spent.** The 50,000
HQC on the Nexus usage page are for **H2-1E / H2-2E (emulators)**; the syntax checkers (H2-1SC /
H2-2SC) are free and unlimited, and no real-hardware allowance is shown [established, usage page].

How the numbers are made: `scripts/h2_hqc_budget.py` compiles each planned circuit offline to H2's
native gates at TKET level 0 and applies HQC = 5 + C·(N1q + 10·N2q + 5·Nm)/5000 [established: Quantinuum
workflow page, read 2026-10-17, "all execute jobs submitted to Quantinuum Systems consume HQCs"]
with Nm = the initial implicit state preparation + measurements + resets [established, same page];
output `data/h2_hqc_budget.txt`. Rz is charged as a one-qubit gate (conservative). Shots per point are [assumed] 1000 (Q1, Q4) and
500 (Q3); cost is linear in shots plus 5 HQC per circuit. Randomized compiling (D-RC) splits the
shots over 20 twirled circuits, each paying the 5-HQC overhead. **[unverified] until the free SC
quotes them:** whether H2 charges Rz (the page does not say). A job's quote is returned with its result.

## What fits the emulator (the constraint that reshaped the plan)
H2-1E / H2-2E: **32 qubits state-vector, 56 stabilizer (Clifford only)**; state-vector below 28
recommended [established: Quantinuum emulator pages, read 2026-10-17; see DECISIONS.md OPEN-4]. So the
first draft's 6×8 Q1 lattice (52 qubits) and the 6×6 Q3 arm (36/40) **cannot run on the emulator**.

## Runs and costs (compiled, 1000 shots per point, Rz counted)

| group | run | qubits | HQC |
|---|---|---|---|
| **G1** | Iceberg 2×2 plain (steps 1–3) + RC + bare 2×2 | 8 / 4 | **2,135** |
| **Q1** | Iceberg **4×5** RC (steps 1–6) + bare 4×5 — recommended headline lattice | 24 / 20 | **13,159** |
| Q1-alt | Iceberg 4×6 RC + bare 4×6 (28 qubits: at the recommended limit) | 28 / 24 | 15,485 |
| Q1-draft | Iceberg 6×8 RC + bare 6×8 — **does not fit the emulator** | 52 / 48 | (29,419) |
| **Q4** | Steane 1×2 + 5-qubit 1×2 + concatenated 2×2, steps 1–3 (no RC) | 16 / 12 / 18 | **11,713** |
| Q3 (derived) | 3×4 triangular bare + Gauss, t = 1…8, 500 shots | 12 | ≈ 6,000 [derived from the formula, not compiled] |
| Q3 (derived) | 3×4 triangular Iceberg, t ≤ 4 only, 500 shots | 16 | ≈ 5,500 [derived, not compiled] |
| Q3 6×6 arm | λ ladder + fold | 36 / 40 | **cannot run on the emulator**; ≈ 83,000 under D-NS7 is moot |

G1 + Q1 (4×5) + Q4 = **27,007 HQC (54%)**. Q3 rows are formula estimates until their circuits are
compiled in the next pass.

## Suggested allocation of the 50,000 HQC (the project lead's decision)

| item | HQC |
|---|---|
| G1: first emulator run, 2×2, checks Nexus against the local emulator and Selene | 2,135 |
| Q1 headline, 4×5 (encoded RC vs bare, matched) | 13,159 |
| Q4 codes at the smallest executable sizes | 11,713 |
| Q3 3×4 bare + Gauss (500 shots) | ≈ 6,000 |
| Q3 3×4 Iceberg, t ≤ 4 (500 shots) | ≈ 5,500 |
| **subtotal** | **≈ 38,500** |
| reserve for reruns, SC surprises, a second Q1 seed or doubled Q1 shots | ≈ 11,500 |

Order of use, each step gated on your go: SC quotes for everything (free) → G1 (≈ 2.1k, the
cheapest end-to-end test of the whole path, and it can be compared with three local predictions) →
Q1 → Q4 → Q3. Stop after G1 and compare before spending more.

**Not affordable or not possible within 50k / on the emulator:** the 6×6 and 6×8 runs (OPEN-4); Q4
at larger H2-only sizes (Steane 2×2 is 30 qubits, the 5-qubit 2×3 is 32, concatenated 2×3 is 34;
at or near the 32-qubit limit; roughly 15–25k HQC together [inferred, not compiled]).
