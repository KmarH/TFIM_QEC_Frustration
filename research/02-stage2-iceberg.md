# Research Note 02 — Stage 2 (square encoded) QEC: Iceberg code

**Purpose:** minimal literature pass to implement the Iceberg d=2 error-detection
code and its concatenation (d=4) correctly in Stim (SCOPE §6). In service of code.
Status tags as in note 01.

## Primary source [established]
Self, Benedetti, Amaro, "Protecting Expressive Circuits with a Quantum Error
Detection Code," arXiv:2211.06703 (v2, 26 Jul 2024). Fetched 2026-10-06.
Nicknamed the **Iceberg code**. Also: Co-Compilation arXiv:2504.21172 (gadgets),
Error-detected surgery arXiv:2608.06187 (future-dated; flagged — do NOT trust).

## Code definition [established, from 2211.06703 §I / Fig. 1]
- **[[k+2, k, 2]]**: an even number k of logical qubits encoded into n = k+2
  physical qubits. Physical qubits: numbered 1..k plus two special qubits named
  **top (t)** and **bottom (b)**. Code distance 2 -> detects ANY single-qubit error
  (cannot correct). Optimal: minimum physical qubits for k logical at distance 2.
- **Stabilizers (exactly two):**
    S_X = X_1 X_2 ... X_k X_t X_b   (X on ALL n physical qubits)
    S_Z = Z_1 Z_2 ... Z_k Z_t Z_b   (Z on ALL n physical qubits)
  They commute because they overlap on all n qubits (n even => even overlap).
- **Logical operators (per logical qubit i = 1..k):**
    Xbar_i = X_t X_i       (Pauli-X logical: top qubit and numbered qubit i)
    Zbar_i = Z_b Z_i       (Pauli-Z logical: bottom qubit and numbered qubit i)
  "Iceberg" structure: logicals have weight-2 physical support (the small visible
  tip), while the stabilizers span all qubits (the submerged bulk).
- **Syndrome / detection:** measure S_X and S_Z. A -1 outcome of either stabilizer
  flags a detected error -> the shot is DISCARDED (post-selection). QED, not QEC.

## Logical commutation checks to verify in code [established]
- Xbar_i and Zbar_i anticommute: Xbar_i on {t,i}, Zbar_i on {b,i}; overlap only on
  qubit i where X,Z anticommute -> single anticommuting site -> anticommute. ✓
- Xbar_i and Zbar_j (i!=j) commute (disjoint numbered qubits / only t,b overlap).
- Logicals commute with both stabilizers (even number of anticommuting sites).
  Verify ALL of this explicitly with a Stim tableau, do not assume.

## Concatenated Iceberg (d=4) [inferred — SCOPE §6 "concatenated Iceberg d=4"]
Concatenating a distance-2 code with itself yields distance d = 2*2 = 4. The exact
concatenated gadget is NOT pinned to one equation set in the fetched material.
Plan: build the single-level code + verifier first; attempt concatenation by
composing encoders and VERIFY the resulting distance empirically in Stim (inject
weight 1..3 errors). If a specific concatenation construction is required that has
nothing in the literature to check against, that is a Claude Code hand-off (new
construction) — write handoff/NN-task.md, do NOT invent it.

## Stim implementation plan [plan]
- Represent the code by explicit stabilizer generators + logicals (above).
- Build a verifier that: constructs the stabilizer group, checks all generators
  mutually commute, checks each logical commutes with all stabilizers, checks the
  Xbar_i/Zbar_i symplectic (anti)commutation, and injects every weight-1 Pauli to
  confirm at least one stabilizer anticommutes (distance >= 2 detection guarantee).
- Use stim tableau/PauliString algebra for the checks; no hardware.
