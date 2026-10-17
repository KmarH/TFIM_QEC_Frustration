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
shots over 20 twirled circuits, each paying the 5-HQC overhead. The free SC has since quoted every circuit below (Rz is not charged).

## What fits the emulator (the constraint that reshaped the plan)
H2-1E / H2-2E: **32 qubits state-vector, 56 stabilizer (Clifford only)**; state-vector below 28
recommended [established: Quantinuum emulator pages, read 2026-10-17; see DECISIONS.md OPEN-4]. So the
first draft's 6×8 Q1 lattice (52 qubits) and the 6×6 Q3 arm (36/40) **cannot run on the emulator**.

## Runs and costs: SERVER-QUOTED on the free H2-1SC (1000 shots per point, 2026-10-17)

`data/h2_sc_quotes.txt` and `data/h2_sc_quotes_q1.txt` (42 circuits, all accepted). **Rz is not charged**:
the Rz-free estimate equals the quote to the cent for every Iceberg and bare circuit and is within
0.5% for the Steane and concatenated circuits (conditional gates) [measured]. The Rz-counted
figures in earlier drafts were 15–20% too high. RC runs add 5 HQC per extra twirled circuit.

| group | run | qubits | HQC (quoted) |
|---|---|---|---|
| **G1** | Iceberg 2×2 plain + RC (steps 1–3) + bare 2×2 | 8 / 4 | **1,901** |
| **Q1** | Iceberg **4×5** RC (steps 1–6) + bare 4×5 — recommended headline lattice | 24 / 20 | **11,636** |
| Q1-alt | Iceberg 4×6 RC + bare 4×6 (28 qubits: at the recommended limit) | 28 / 24 | 13,679 |
| **Q4** | Steane 1×2 + 5-qubit 1×2 + concatenated 2×2, steps 1–3 (no RC) | 16 / 12 / 18 | **9,817** |
| **Q3-bare** | 3×4 triangular bare (Gauss post-selection is classical), t = 1…8, 500 shots | 12 | **5,670** |
| **Q3-iceberg** | 3×4 triangular Iceberg, t = 1…4, 500 shots (no RC) | 16 | **5,283** |
| **Q3-ladder** | 3×4 noise-scaling ladder: λ = 1, Pauli insertion λ = 2, 3 (10 instances each), one fold λ = 3 at t = 2; t = 1, 2, 3; 500 shots/point | 12 | **4,093** |
| **Q3-bare-3x6** | 3×6 triangular bare, t = 1…3, 500 shots | 18 | **1,453** |
| Q3 6×6 arm | λ ladder + fold | 36 / 40 | **cannot run on the emulator** (OPEN-4) |
| Q1 draft | Iceberg 6×8 + bare 6×8 | 52 / 48 | **cannot run on the emulator** |

G1 + Q1 (4×5) + Q4 = **23,354 HQC (47%)**, all server-quoted. The Q3 groups are now quoted too
(`data/h2_sc_quotes_q3.txt`, 2026-10-17, [measured]; offline estimate = quote to the cent, total **16,499**): the full plan
G1 + Q1 + Q4 + Q3 = **39,853 HQC (80%)**, leaving about **10,147** for reruns. The earlier "≈ 10k" Q3 figure was a formula guess
and was low by 6.5k, mostly because the 3×4 bare curve runs to t = 8 (32 Trotter steps) and Iceberg to t = 4. Trimming options
(the project lead's call): bare t ≤ 6 (−2,339), Iceberg t ≤ 3 (−2,012), or 250 shots per Q3 point (about −45%).

## Suggested allocation of the 50,000 HQC (the project lead's decision; none of it is committed)

| item | HQC |
|---|---|
| G1: first emulator run, 2×2; checks the emulator against the local emulator and Selene | 1,901 |
| Q1 headline, 4×5 (encoded RC vs bare, matched) | 11,636 |
| Q4 codes at the smallest executable sizes | 9,817 |
| Q3 groups (Q3-bare, Q3-iceberg, Q3-ladder, Q3-bare-3x6), quoted | 16,499 |
| **subtotal** | **39,853** |
| reserve: reruns, or part of a second Q1 seed | ≈ 10,147 |

Order of use, each step gated on your go: G1 first. The cheapest single end-to-end check is the bare
2×2 circuit at step 1 (23.40 HQC for 1000 shots). Stop after G1 and compare before spending more.

**Not affordable or not possible on the emulator:** the 6×6 and 6×8 runs (OPEN-4). Q4 at larger
H2-only sizes (Steane 2×2 is 30 qubits, the 5-qubit 2×3 is 32, concatenated 2×3 is 34) are at or near
the 32-qubit limit; roughly 15–25k HQC together [inferred, not compiled].

## Limits enforced by the run driver [established: docs.quantinuum.com "H2 Operation", read 2026-10-17]
"Each shot submitted to hardware has a 50 HQC hard limit." and "Each job submitted to hardware is limited to 10,000 shots
(500,000 HQC hard limit)." The page does not say whether emulators share them (QI-15), so `src/h2_driver.py` applies them
(`HardwareConfig.max_hqc_per_shot`, `max_shots_per_job`, `emulator_max_qubits`; a config may tighten but not loosen them).
Our circuits cost about 0.02-0.4 HQC per shot, far below 50.

## Note on the first quote file
`data/h2_sc_quotes.txt` (11:14) has a stale `est(noRz)` column for Steane / concatenated (it predates the conditional-gate
fix in `native_counts`); `data/h2_sc_quotes_q4.txt` is the refreshed Q4 comparison with the fixed counts (estimate = quote to the cent).
