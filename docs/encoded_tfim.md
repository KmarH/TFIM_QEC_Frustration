# Encoded TFIM baseline — Part A: Iceberg [[k+2, k, 2]] reference build

Deliverable for `handoff/04-encoded-tfim-baseline.md`, **Checkpoint 1 (Part A only)**.
- Code: `src/encoded_tfim.py` (authored circuit, Stim verifier), `src/backends_qc.py` (toggle).
- Settings: `config.py: EncodedConfig`.
- Script and data: `scripts/run_encoded.py` → `data/encoded_iceberg.txt`.
- Tests: `tests/test_encoded_tfim.py` (20 tests). Nexus plan: `docs/nexus_toggle.md`.

Status tags: **[established]** from a cited source or the repo's verified code; **[derived]** argued here and checked by a test; **[measured]** output of this repo; **[assumed]** declared modelling choice; **[unverified]** not checked.

> Every noisy number in this document and in `data/encoded_iceberg.txt` is a **classical prediction under an assumed generic depolarizing model**. None is an H2 hardware result.

## 1. What was built

**Encoding.** The logical 2×3 periodic square lattice (k = 6) sits in **one** Iceberg block, [[8, 6, 2]] (arXiv:2211.06703; repo `src/qec/iceberg.py` layout). One syndrome ancilla and one flag are added, so **n_phys = 10**.
- Why one block: Iceberg encodes k logicals at a cost of only 2 extra qubits, and the logical bonds and fields are then weight-2 physical rotations.
- Iceberg requires even k, so odd lattices (3×3) are refused.

**Logical gates [derived; the transparency test confirms them].**

| logical operation | physical gate |
|---|---|
| exp(−iφ Z̄_iZ̄_j) | exp(−iφ Z_iZ_j) = `ZZPhase(2φ/π)` on (i, j) |
| exp(−iφ X̄_i) | exp(−iφ X_tX_i), authored as H⊗H · `ZZPhase` · H⊗H on (t, i) |
| logical ry(θ) | S̄ R̄x(θ) S̄†, with S̄ = exp(−iπ/4 Z_bZ_i) |

- Selene's HUGR-QIS compiler (selene-sim 0.3.4) **rejects pytket `XXPhase`** [measured]. The H-conjugated form is the same operator, and it uses H2's native ZZ entangler.
- The Trotter step is the Q1 harness's circuit-order Strang step at J·dt = 0.25, h·dt = 0.5, (J, h) = (+1, +2), with θ = π/6 (quench1).

**Syndrome round [established pattern, rebuilt as pytket segments].** A flagged S_Z, then a flagged S_X: one ancilla and one flag, Chao–Reichardt single-flag placement, the same as `src/qec/concatenated_gadget.py`.

**QED discard rule.** Keep a shot only if all of the following hold:
- every flag reads 0;
- every S_Z equals the previous one (round-0 reference = 0, since |0ⁿ⟩ has S_Z = +1);
- every S_X equals the round-0 S_X (random, used as the frame reference; S_X's sign is a pure frame that commutes with every gate);
- the final data parity equals the last S_Z.

**Cadence.** A syndrome round runs **after every Trotter step** (`syndrome_every = 1`). This is justified by the measured discard rate: a step already discards several percent of shots at p2 = 1e-3 (§4), so a sparser cadence would let undetected multi-fault combinations accumulate between checks. The cadence is configurable.

**One source of truth.** The pytket segments are:
- executed by **local-sim**. pytket core 2.18.4 ships no shot simulator: `get_statevector()` rejects mid-circuit `Measure`/`Reset` [measured]. So an in-repo state-vector engine runs the pytket commands one by one, and is cross-checked against `get_statevector()` to 1e-12 on every segment.
- loaded into **Guppy** with `guppy.load_pytket` and run on **Selene** (Quest state vector, `DepolarizingErrorModel`). Syndrome ancillas are measured mid-circuit (`project_z(...).read()` plus `reset`), the discard verdict is computed in-program, and **once a detector fires every later quantum block is skipped (feedforward)**. Tests check this two ways: the in-program verdict equals the Python predicate shot for shot, and discarded shots run fewer rounds.
- translated into **Stim** for verification only.

**Toggle.** `backends_qc.run(..., backend=)` accepts `local-sim` (default) or `selene`. `nexus` raises `NotImplementedError("Nexus backend: requires Quantinuum credentials/credits; flip toggle when access is granted")`; see `docs/nexus_toggle.md`. The physical register is checked against `statevector_max_spins` **before** any allocation: a 4×6 lattice needs n_phys = 28 and is refused.

## 2. Verification (Stim) — the fault-tolerance result
Pauli faults pass through a Pauli rotation exp(−iφP) unchanged; only φ's sign flips. So for fault propagation, each rotation is exactly the identity in the Stim image [derived]. Both readout bases are checked: Z-basis (|0ⁿ⟩ prep, Z̄ observables) and X-basis (|+ⁿ⟩ prep, X̄ observables), so both X-type and Z-type logical faults are visible.

| check (2×3 lattice, 3 steps) | result [measured] |
|---|---|
| `verify_code` on the [[8,6,2]] block | PASS |
| clean run, both bases | detectors silent, observables clean |
| every single-qubit X/Y/Z on every code qubit after every step | detected |
| single faults on **syndrome CX, H, measurement, reset, idle** locations | **0** undetected logical errors |
| single faults on the **logical rotation gates** | **42 mechanisms** (Z and X images) cause undetected logical errors |

**The brief's done-check "no single-fault undetected logical error" FAILS for this construction, and cannot pass for any construction of this kind [derived; measured].**
- A logical gate exp(−iφ P_aP_b) acts on exactly two physical qubits. A fault after it can leave **X_aX_b, Y_aY_b or Z_aZ_b**. Each of these commutes with S_X = Xⁿ and S_Z = Zⁿ, and each is a nontrivial logical operator. This is distance 2 with weight-2 logical gates.
- Stim lists 63 distinct undetected Paulis. **All are XX, YY or ZZ, and each sits on the support of one of the 21 logical gates**: 21 × 3, with nothing else (`test_single_fault_accounting_isolates_the_logical_gates`).
- Under uniform two-qubit depolarizing noise that is **3 of 15 Pauli components, i.e. 1/5 of every logical-gate fault**, which the code cannot see.
- So the honest statement is: **the syndrome-extraction gadget is single-fault tolerant; the encoded Trotter step is not.** The undetectable residue is first order in the logical-gate error rate.

## 3. Zero-noise consistency [measured]
- **Encoding transparency.** At the physical parameters, encoded logical Z2 equals the bare `simulate_z2` on the same 2×3 lattice to ≤ 6e-15 for steps 1–6. It also holds for both quench angles and a 2×2 lattice in the tests.
- **Stim ↔ pytket/Guppy agreement.** At a Clifford-angle instance of the *same* program (J·dt = π/4, h·dt = π/2, θ = 0), Stim's exact tableau result, local-sim's exact result and bare `simulate_z2` agree exactly. Z2 alternates 1/6, 1, 1/6, 1, so the comparison discriminates. Selene's sampled value agrees within statistical error.

## 4. Noisy curves and limits assessment
Source: `data/encoded_iceberg.txt`.
- Setup: 2×3 periodic lattice, θ = π/6. 1,000 shots per point per backend; every point is an independent run.
- Noise **[assumed]**: p2 per 2-qubit gate, with p1 = pm = p_init = p2/10 and no idle term.
- "dev" = |Z2 − ideal|, where ideal = the noiseless Trotter circuit. ± is 1 standard error.
- "bare" = the same logical circuit on 6 bare qubits at the same per-gate rates (local-sim): field rotations are 1-qubit Rx gates, bonds are ZZPhase.

| p2 | step | acceptance (local / selene) | encoded dev (local / selene) | bare dev |
|---|---|---|---|---|
| 1e-3 | 1 | 0.93 / 0.90 | 0.012 / 0.018 (SE 0.012) | 0.006 (SE 0.012) |
| 1e-3 | 4 | 0.80 / 0.77 | 0.007 / 0.004 (SE 0.014) | 0.029 (SE 0.013) |
| 1e-3 | 6 | 0.75 / 0.72 | 0.017 / 0.009 (SE 0.012) | **0.049** (SE 0.011) |
| 3e-3 | 5 | 0.48 / 0.40 | 0.050 / 0.024 (SE 0.018–0.019) | 0.033 (SE 0.012) |
| 3e-3 | 6 | 0.42 / 0.35 | 0.019 / 0.034 (SE 0.016–0.018) | **0.092** (SE 0.012) |
| 1e-2 | 3 | 0.21 / 0.16 | 0.034 / 0.061 (SE 0.03) | 0.074 (SE 0.013) |
| 1e-2 | 6 | **0.053 / 0.037** | 0.17 / 0.15 (SE 0.06) | 0.24 (SE 0.012) |

**The three application risks, answered for this lattice and this assumed model:**

1. **When does discard make the encoded run inefficient? [measured]** Acceptance decays per step. By step 6 it is about 0.75 at p2 = 1e-3 (1.3× shots), about 0.4 at 3e-3 (2.4–2.9×), and **about 0.04–0.05 at 1e-2 (20–27× shots)**.
   - At p2 = 1e-2 the encoded run is inefficient beyond about 2–3 steps.
   - At p2 ≤ 3e-3 it stays affordable to step 6 on this lattice.
   - Acceptance falls roughly exponentially with gate count, and the gate count grows with lattice size: k field gates, the bonds, and a syndrome round of about 2(k+2) CX. Larger logical lattices discard faster **[inferred, not measured here]**.
2. **Does encoded Z2 track the ideal longer than bare at matched physical noise? [measured, modest]**
   - **At p2 = 1e-3 and 3e-3: yes, by step 6, within statistical resolution.** Bare drifts 4.5σ (1e-3) and 7.7σ (3e-3) from ideal, while post-selected encoded stays within about 2σ on both backends.
   - At earlier steps the two cannot be distinguished at 1,000 shots, and one point (3e-3, step 5, local-sim) has encoded *worse* than bare. The advantage is not uniform.
   - **At p2 = 1e-2:** encoded is not resolvably better, given its error bars (only about 50 accepted shots survive by step 6).
3. **Does encoding buy reachable time? (skeptical)** For this tiny lattice and model, **a modest yes at p2 ≤ 3e-3, bought with 1.3–3× shots; no at p2 = 1e-2**. Four caveats bound that yes:
   - (a) **A residual is uncorrectable by construction (§2).** One fifth of every logical-gate fault is undetectable, so post-selected Z2 keeps a first-order error floor in p2; post-selection removes most errors, not all.
   - (b) **The encoded step costs more per step.** It runs 2-qubit gates where bare runs 1-qubit field gates, plus the syndrome rounds, so "matched per-gate rates" is not "matched cost".
   - (c) 2×3 is far from the 56-qubit experiment, and no size trend was measured.
   - (d) **The noise model is generic and assumed**, not H2's.

   Whether the advantage survives a calibrated H2 channel, larger lattices, or idle noise is open.

**Backend agreement [measured].** local-sim and Selene agree on Z2 within errors. **Selene's acceptance is systematically 3–8 points lower.** The likely reason is that Selene applies `p_1q`/`p_2q` to its own compiled native gates: CX and H decompose differently, and its channel definitions are **[unverified]**. This is a stated difference, not tuned away.

## 5. Not done in Checkpoint 1
- Part B (Steane, 5-qubit, concatenated d=4): awaiting confirmation.
- No idle noise in the scans (Selene has no idle term).
- No θ = −10° (quench2) noisy scan; only transparency was checked at that angle.
- No exact (density-matrix) post-selected curves, which would remove shot noise at n_phys = 10.

---

# Part B — Steane [[7,1,3]], 5-qubit [[5,1,3]], concatenated Iceberg [[16,4,4]]

**Decisions recorded by Kevin (2026-10-07):**
- **Standard B:** measured fault accounting, with **no pass/fail FT bar**.
- **Budget (ii):** build or discard is judged against **~55 physical qubits (H2 scale)**. Stim analysis runs at budget size; noisy execution runs only at the reduced size that fits the 24-qubit state-vector ceiling.
- **Residual:** the undetected-logical rate is **measured** in Stim, and Iceberg is re-measured with the same machinery.

Code: `src/encoded_codes.py`. Script and data: `scripts/run_encoded_codes.py` → `data/encoded_codes.txt`. Tests: `tests/test_encoded_codes.py` (27 tests: 12 test functions, some parametrized).

## B1. One generic pipeline for every code [derived; verified by tests]
- **Same program shape as Part A.** Prep, round 0, logical ry(θ), Strang Trotter steps, a syndrome round after every step, then Z readout. Every stabilizer is measured with a flagged ancilla (flag used for weight ≥ 3), with a basis change for X/Y components.
- **Frame correction by feedforward.** Round 0 makes the random-sign stabilizers' outcomes reference values. The program then applies each such stabilizer's **pure error** (anticommutes with that stabilizer only and commutes with every logical; solved over GF(2)) when it read −1.
  - After this, every stabilizer is +1. Logical operators can then be replaced by **minimum-weight stabilizer-equivalent representatives**, signs included. Without the correction, those representatives would flip the rotation angle's sign on some shots.
- **Logical rotation exp(−iφP̄):**
  - weight 2 → one `ZZPhase`, which is Iceberg's native gate;
  - weight > 2 → **parity gadget**: basis-change the support, CNOT it onto the ancilla (interleaved across blocks so no proper prefix is a logical), apply `Rz` on the ancilla, uncompute, then **measure the ancilla (a detector)** and reset it.
- **One schedule object drives all three forms:**
  - local-sim, the state-vector interpreter;
  - **Stim**, with rotations as identity for fault propagation or as Clifford gates for the consistency check;
  - **Selene**, through a generated Guppy module. Every measurement is mid-circuit, the frame corrections and detector checks are evaluated in-program, and later work is skipped after a detection.

| check (reduced lattice) | Iceberg 2×2 | Steane 1×2 | 5-qubit 1×2 | concat 2×2 |
|---|---|---|---|---|
| `verify_code` on the block | PASS | PASS | PASS | PASS |
| clean Stim images (Z and X) silent | yes | yes | yes | yes |
| encoding transparency (vs bare `simulate_z2`) | 1.7e-14 | 4.6e-14 | 4.3e-14 | 5.1e-14 |
| **Stim ↔ local-sim on the whole logical state** (all 4^k logical Pauli expectations, Clifford instance) | 2.5e-14 (256) | 3.5e-14 (16) | 2.2e-14 (16) | 5.7e-14 (256) |
| Selene noiseless run: all accepted, exact Z2 | yes | yes | yes | yes |

Z2 alone cannot discriminate on a 2-site lattice: the Clifford dynamics keeps ⟨Z̄₁Z̄₂⟩ fixed. That is why the consistency check compares the **full logical state** rather than Z2.

## B2. Budget against the ~55-qubit H2 scale [measured counts]
Physical qubits = data + 1 ancilla + 1 flag. L = runs locally and fits H2; H = fits H2 only; x = over ~55.

| code | 1×2 | 2×2 | 2×3 | 2×4 | 3×4 | 4×4 |
|---|---|---|---|---|---|---|
| Iceberg | 6 L | 8 L | 10 L | 12 L | 16 L | 20 L |
| Steane | 16 L | 30 H | 44 H | 58 x | 86 x | 114 x |
| 5-qubit | 12 L | 22 L | 32 H | 42 H | 62 x | 82 x |
| concat d=4 | 18 L | 18 L | 34 H | 34 H | 50 H | 66 x |

**Logical-gate cost [measured from the schedules]:**

| code (lattice) | field X̄ weight | bond Z̄Z̄ weight | 2q ops / step | 1q ops / step | measurements / step |
|---|---|---|---|---|---|
| Iceberg 2×2 | 2 | 2 | 28 | 48 | 4 |
| Steane 1×2 | 3 | 6 | 108 | 101 | 29 |
| 5-qubit 1×2 | 3 | 6 | 84 | 109 | 21 |
| concat 2×2 | 4 | 4 | 184 | 164 | 36 |
| bare 2×2 | — | — | 4 | 8 | — |

## B3. Measured undetected-logical probability per Trotter step [Stim, first order]
Noise **[assumed]**: p2 per 2-qubit gate; p1 = pm = p_init = p2/10.

| lattice, p2 = 1e-3 | Iceberg | Steane | 5-qubit | concat | **bare** |
|---|---|---|---|---|---|
| 1×2 | 1.00e-3 | 8.3e-4 | 8.3e-4 | 8.3e-4 | 1.40e-3 |
| 2×2 | 2.40e-3 | 2.00e-3 | 2.00e-3 | 2.00e-3 | 4.80e-3 |
| 2×3 | 4.20e-3 (n=10) | 3.50e-3 (n=44) | 3.50e-3 (n=32) | 3.50e-3 (n=34) | 1.02e-2 |
| first-order acceptance after 3 steps, 2×3 | 0.83 | 0.21 | 0.28 | 0.23 | — |

At p2 = 3e-3 the residuals scale ×3. First-order acceptance after 3 steps at 2×2 becomes Iceberg 0.67, Steane 0.06, 5-qubit 0.10, concat 0.10. All values are in `data/encoded_codes.txt`.

**What the accounting shows [measured; matched exactly by the derived formulas in `test_measured_accounting_matches_first_order_derivation`]:**
1. **The syndrome-extraction gadgets of all four codes contribute zero** undetected single faults.
2. **The entire undetectable residual sits at the logical rotations, and it is independent of code distance.**
   - Iceberg's native gate leaves XX, YY or ZZ on its own support: 3/15 · p2 per gate.
   - Every parity gadget leaves its own generator through the fault at the rotation point: 2/15 · p2 (from the adjacent CNOTs) plus 1/3 · p1 (from the ancilla `Rz`), regardless of whether the code has d = 2, 3 or 4.
3. Per step, every code suppresses the unprotected error of the bare circuit by about **2–3×**: 2.4e-3 vs 4.8e-3 at 2×2, and 3.5–4.2e-3 vs 1.02e-2 at 2×3. **The d = 3 and d = 4 codes buy only a further ~1.2× over Iceberg**, from the cheaper gadget residual, at **3–4× lower acceptance** and 3–7× more two-qubit gates per step.

## B4. Executed noisy runs at reduced size (Selene) [measured]
- Source: `data/encoded_codes.txt` §5. Setup: θ = π/6; p1 = pm = p_init = p2/10 **[assumed]**; ± is 1 standard error.
- Shots are limited by Selene's run time at 16–18 qubits: Iceberg 1,000, 5-qubit 400, Steane 300, concat 150.
- Bare = the same logical circuit on bare qubits under local-sim, 1,000 shots.
- "Predicted" = Stim first-order acceptance exp(−detection probability) of the same 3-step program.

| code (lattice) | p2 | acceptance step 1 / 2 / 3 | predicted @3 | encoded Z2 @3 | ideal @3 | bare Z2 @3 |
|---|---|---|---|---|---|---|
| Iceberg (2×2) | 1e-3 | 0.918 / 0.856 / 0.829 | 0.875 | 0.587 ± 0.015 | 0.589 | 0.581 ± 0.013 |
| Iceberg (2×2) | 3e-3 | 0.774 / 0.653 / 0.568 | 0.670 | 0.581 ± 0.018 | 0.589 | 0.583 ± 0.013 |
| Steane (1×2) | 1e-3 | 0.767 / 0.617 / 0.547 | 0.642 | 0.890 ± 0.025 | 0.874 | 0.875 ± 0.011 |
| Steane (1×2) | 3e-3 | 0.407 / 0.227 / 0.140 | 0.264 | 0.810 ± 0.061 | 0.874 | 0.861 ± 0.011 |
| 5-qubit (1×2) | 1e-3 | 0.805 / 0.690 / 0.585 | 0.713 | 0.893 ± 0.020 | 0.874 | 0.875 ± 0.011 |
| 5-qubit (1×2) | 3e-3 | 0.557 / 0.315 / 0.200 | 0.363 | 0.825 ± 0.043 | 0.874 | 0.861 ± 0.011 |
| concat (2×2) | 1e-3 | 0.640 / 0.507 / 0.333 | 0.472 | 0.655 ± 0.056 | 0.589 | 0.581 ± 0.013 |
| concat (2×2) | 3e-3 | 0.253 / 0.067 / 0.033 | 0.105 | 0.55 ± 0.18 (5 shots kept) | 0.589 | 0.583 ± 0.013 |

What the execution shows:
- All four pipelines run end to end on Selene, with real mid-circuit measurement and feedforward discard.
- **Acceptance ranks exactly as the Stim accounting predicts:** Iceberg ≫ 5-qubit > Steane > concat. Executed acceptance is consistently **below** the first-order prediction (by 5–15 points at 1e-3). The likely reasons are Selene's own native-gate decomposition (as in Part A) and the first-order exp approximation **[inferred]**.
- **Z2:** at 3 steps on these 2–4-site lattices, neither encoded nor bare Z2 deviates resolvably from ideal. Every point is within about 1.7σ. **The execution therefore cannot show an encoding advantage at this size and depth; it does not show a disadvantage either.**
  - The d ≥ 3 codes keep so few shots that their error bars are 2–14× the bare ones.
  - The quantitative comparison rests on the measured accounting (B3), not on these curves.

## B5. Build / discard decision per code (standard B, budget ii)

| code | decision | quantitative basis |
|---|---|---|
| **Iceberg [[k+2,k,2]]** | **BUILT — the reference, and the recommended encoded baseline** | Fits H2 up to 4×4 (20 qubits). Residual is 0.42–0.50× bare per step. First-order acceptance after 3 steps is 0.83 (2×3, p2 = 1e-3). |
| **Steane [[7,1,3]]** | **BUILT, not recommended** (dominated by Iceberg) | Fits ≤ 55 up to 2×3 (44 qubits); 2×4 needs 58. Pipeline verified (B1). Residual is **only 1.2× lower than Iceberg** (3.5e-3 vs 4.2e-3 per step at 2×3), because it comes from the rotation gadgets, not the distance. Acceptance is **4× lower** (0.21 vs 0.83 after 3 steps), with 108 two-qubit gates per step for just 2 logical qubits. |
| **5-qubit [[5,1,3]]** | **BUILT, not recommended** (dominated by Iceberg) | Fits ≤ 55 up to 2×4 (42 qubits). The handoff expected a discard on logical-gate cost. **The measurement does not support that:** with the frame-corrected, minimum-weight representatives, its gates cost about the same as Steane's (field weight 3, bond weight 6; 84 two-qubit gates per step vs Steane's 108), and it keeps slightly more shots (0.28 vs 0.21). Same residual as Steane. |
| **Concatenated Iceberg [[16,4,4]]** | **BUILT, not recommended** (dominated by Iceberg) | Fits ≤ 55 up to 3×4 (50 qubits), the largest d ≥ 3 lattice here. Highest cost: 184 two-qubit gates per step at 2×2. Lowest executed acceptance (0.33 after 3 steps at 1e-3; 0.03 at 3e-3). Same residual as the d = 3 codes. **Distance 4 buys nothing over d = 3 for this residual.** |

**None of the three is discarded.** Under budget (ii), each fits the ~55-qubit scale for at least a 2×2 lattice, and its pipeline is built, verified and executed. A budget or "harder to implement" discard would therefore be weak, and the brief rules those out. The measured comparison is still unambiguous for this setting (QED post-selection, distillation-free rotations, assumed depolarizing noise):

> **Higher code distance does not reduce the undetectable residual, because the residual is set by the arbitrary-angle rotation gadgets, not by the code. The d = 3 and d = 4 codes buy about 1.2× on that residual and pay 3–5× in acceptance (more at higher p2) and 3–7× in two-qubit gates. Iceberg is the right encoded baseline for Q1.**

## B6. Open, not done
- **Active error correction for the d ≥ 3 codes.** They are run here as *detection* codes, which is the brief's post-selection pipeline. Correcting single errors instead of discarding would raise their acceptance substantially, and it is the main lever that could change B5. It would **not** remove the rotation-gadget residual, and decoding adds its own failure modes. This is not built.
- **Lower-residual rotations.** Magic-state injection with distillation, or flagged/verified rotation gadgets, could cut the residual. Distillation is excluded at this scale by the brief.
- **Scale.** Execution runs at 2–4 logical qubits; the 2×3 numbers come from Stim only. Selene takes about 1–4 s per shot at 16–18 qubits, so larger executed shot counts need much more time.
- The Selene-vs-prediction acceptance gap is unexplained beyond the decomposition hypothesis.

---

# Noise-model sensitivity of the Part B conclusion (2026-10-07)

Question asked: *can the Part B result ("Iceberg is the best encoding") be carried over to H2?* The test changes ONE assumption of the Part B baseline at a time and re-measures with Stim.
- Script: `scripts/run_noise_sensitivity.py` → `data/noise_sensitivity.txt`.
- Lattice and rates: 2×2; p2 = 1e-3, p1 = pm = p_init = 1e-4 **[assumed]**. Stim first-order accounting, no execution. This table is section 2 of the data file. Section 1 is the H2-prior rerun (handoff/06; see "Rerun at the researched H2 prior" below).
- Each cell: undetected-logical probability per Trotter step / first-order acceptance after 3 steps (ratio to bare's unprotected error per step).

| scenario | Iceberg | Steane | 5-qubit | concat d=4 | bare |
|---|---|---|---|---|---|
| baseline: uniform depolarizing | 2.4e-3 / 0.88 (×0.50) | 2.0e-3 / 0.38 (×0.42) | 2.0e-3 / 0.47 (×0.42) | 2.0e-3 / 0.47 (×0.42) | 4.8e-3 |
| *stress-test, ≈10× the H2 prior (research/06), NOT representative:* 2q errors ZZ-biased, η = 0.5 | 7.2e-3 / 0.89 (**×1.50**) | 7.2e-3 / 0.41 (×1.50) | 7.2e-3 / 0.50 (×1.50) | 7.2e-3 / 0.50 (×1.50) | 4.8e-3 |
| *stress-test, ≈10× the H2 prior (research/06), NOT representative:* 2q errors ZZ-biased, η = 0.9 | 1.1e-2 / 0.91 (**×2.30**) | 1.14e-2 / 0.44 (×2.37) | 1.14e-2 / 0.53 (×2.37) | 1.14e-2 / 0.52 (×2.37) | 4.8e-3 |
| idle noise 1e-4 | 2.4e-3 / 0.87 (×0.46) | 2.0e-3 / 0.38 (×0.38) | 2.0e-3 / 0.46 (×0.38) | 2.0e-3 / 0.47 (×0.38) | 5.2e-3 |
| idle noise 1e-3 | 2.4e-3 / 0.84 (×0.27) | 2.0e-3 / 0.32 (×0.23) | 2.0e-3 / 0.42 (×0.23) | 2.0e-3 / 0.42 (×0.23) | 8.8e-3 |
| over-rotation, sin²ε = 1e-4 | 3.6e-3 / 0.88 (×0.60) | 3.2e-3 / 0.38 (×0.53) | 3.2e-3 / 0.47 (×0.53) | 3.2e-3 / 0.47 (×0.53) | 6.0e-3 |
| over-rotation, sin²ε = 1e-3 | 1.44e-2 / 0.88 (×0.86) | 1.40e-2 / 0.38 (×0.83) | 1.40e-2 / 0.47 (×0.83) | 1.40e-2 / 0.47 (×0.83) | 1.68e-2 |
| *stress-test, ≈10× the H2 prior (research/06), NOT representative:* combined η = 0.5, idle 1e-4, over-rot 1e-4 | 8.4e-3 / 0.89 (**×1.31**) | 8.4e-3 / 0.41 (×1.31) | 8.4e-3 / 0.49 (×1.31) | 8.4e-3 / 0.49 (×1.31) | 6.4e-3 |

**Model notes.**
- **ZZ bias:** a fraction η of each two-qubit error is Z⊗Z; the rest stays uniform. For Iceberg's logical gates, which are native `ZZPhase`, this is the physically relevant frame. For the parity-gadget CNOTs of the d ≥ 3 codes, applying the bias in the CNOT frame is an approximation: on H2 a CNOT is compiled from `ZZPhase` plus single-qubit gates **[inferred]**.
  - The η-bias is **exact for Iceberg's native `ZZPhase`**, which is H2's native two-qubit gate (research/06 §1 **[established]**), so the η ≈ 0.25 crossover is exact there. The d ≥ 3 ZZ-biased ratios are frame-approximate **[inferred]**. The robustness conclusion rests on the Iceberg crossover, so it is unaffected.
- **Over-rotation:** a Pauli-twirled stand-in. A real coherent error can add up faster than its twirled version.
- The Iceberg values match the derivation exactly: 12 gates × p2(0.2 + 0.8η), plus 12 × sin²ε (`test_noise_sensitivity_options_match_derivation`).

**What is robust [measured across all 8 scenarios]:**
- **The ranking among codes.** Iceberg's undetected residual is always within about 1.2× of the d ≥ 3 codes, and in no scenario do they beat it by more. Iceberg also keeps about 2× more shots (0.84–0.91 vs 0.32–0.53).
- **Iceberg vs Steane / 5-qubit / concat transfers to any of these noise variations.**

**What is NOT robust: whether encoding helps at all.**
- **ZZ-biased two-qubit errors reverse it.**
  - A ZZ error on the gate that implements a logical ZZ rotation *is* that rotation's generator, a logical operator. No code here can see it, Iceberg or d ≥ 3.
  - The crossover is **η ≈ 0.25** (Iceberg: 12·p2(0.2 + 0.8η) = 4.8e-3) and about 0.27 for the d ≥ 3 codes. If more than about a quarter of the native two-qubit gate error is ZZ-type, every encoding studied here leaves *more* undetected error per step than the bare circuit's total unprotected error, while still costing shots.
- **Coherent over-rotation** adds the same logical error to every code and to bare, eroding the advantage toward ×1 (×0.83–0.86 at sin²ε = 1e-3).
- **Idle noise** goes the other way: it hurts bare more, because encoded idle errors are detected. It favours encoding (×0.23–0.27 at 1e-3), at a small cost in shots kept, larger for the d ≥ 3 codes.

**Bottom line.** "Iceberg over Steane / 5-qubit / concat" carries over to H2-like noise variations. "Encoding buys reachable time" does **not** carry over unconditionally: it hinges on the **ZZ fraction η of H2's native two-qubit gate error** and on its coherent over-rotation. Those quantities must be measured, from the H2 emulator's noise model, the reference experiment's gate characterization (not verified here), or cycle benchmarking, before any claim about the machine. The combined stress-test setting (η = 0.5, idle 1e-4, over-rotation 1e-4) gives ×1.31, which means no gain. η = 0.5 is about 10× the H2 prior (research/06), so that row is a stress-test and NOT representative of H2. See the rerun below.

## Rerun at the researched H2 prior (handoff/06, 2026-10-07)

**This is a prediction from a published prior, NOT an H2 measurement.** Every number below is a classical Stim first-order prediction under an assumed noise model. There is no hardware or emulator run.

- Inputs from `research/06-h2-noise-prior.md` §6, also set in `config.py` (`SensitivityConfig`):
  - p2 = 6e-4 **[inferred from published 2q infidelity]**; p1 = pm = p_init = p2/10 = 6e-5 **[inferred]**.
  - ZZ fraction η = 0.05, bracket 0.03–0.08 **[inferred, Fig. S3 read-off of 2503.20870]**.
  - sin²ε ∈ {0, 1e-5, 1e-4, 1e-3} **[assumed; the 2q ε is unpublished, so it is scanned, not fixed]**.
- Data: section 1 of `data/noise_sensitivity.txt`. Same 2×2 lattice and cell format as the table above **[measured, Stim]**.

| scenario (p2 = 6e-4) | Iceberg | Steane | 5-qubit | concat d=4 | bare |
|---|---|---|---|---|---|
| uniform depolarizing (η = 0; ZZ share 1/15) | 1.44e-3 / 0.92 (×0.50) | 1.20e-3 / 0.56 (×0.42) | 1.20e-3 / 0.63 (×0.42) | 1.20e-3 / 0.64 (×0.42) | 2.88e-3 |
| **H2 prior η = 0.05**, sin²ε = 0 | 1.73e-3 / 0.92 (**×0.60**) | 1.51e-3 / 0.57 (×0.53) | 1.51e-3 / 0.64 (×0.52) | 1.51e-3 / 0.64 (×0.53) | 2.88e-3 |
| η = 0.05, sin²ε = 1e-5 | 1.85e-3 / 0.92 (×0.62) | 1.63e-3 / 0.57 (×0.54) | 1.63e-3 / 0.64 (×0.54) | 1.63e-3 / 0.64 (×0.54) | 3.00e-3 |
| η = 0.05, sin²ε = 1e-4 | 2.93e-3 / 0.92 (×0.72) | 2.71e-3 / 0.57 (×0.66) | 2.71e-3 / 0.64 (×0.66) | 2.71e-3 / 0.64 (×0.66) | 4.08e-3 |
| η = 0.05, sin²ε = 1e-3 | 1.37e-2 / 0.92 (×0.92) | 1.35e-2 / 0.57 (×0.91) | 1.35e-2 / 0.64 (×0.91) | 1.35e-2 / 0.64 (×0.91) | 1.49e-2 |
| bracket η = 0.03 | 1.61e-3 / 0.92 (×0.56) | 1.39e-3 / 0.56 (×0.48) | 1.39e-3 / 0.64 (×0.48) | 1.39e-3 / 0.64 (×0.48) | 2.88e-3 |
| bracket η = 0.08 | 1.90e-3 / 0.92 (×0.66) | 1.70e-3 / 0.57 (×0.59) | 1.70e-3 / 0.64 (×0.59) | 1.70e-3 / 0.64 (×0.59) | 2.88e-3 |
| in-range corner: η = 0.08, sin²ε = 1e-3 | 1.39e-2 / 0.92 (×0.93) | 1.37e-2 / 0.57 (×0.92) | 1.37e-2 / 0.64 (×0.92) | 1.37e-2 / 0.64 (×0.92) | 1.49e-2 |
| *stress-test, ≈10× the H2 prior, NOT representative:* η = 0.5 | 4.32e-3 / 0.93 (×1.50) | 4.32e-3 / 0.59 (×1.50) | 4.32e-3 / 0.66 (×1.50) | 4.32e-3 / 0.66 (×1.50) | 2.88e-3 |
| *stress-test, ≈10× the H2 prior, NOT representative:* η = 0.9 | 6.62e-3 / 0.94 (×2.30) | 6.82e-3 / 0.61 (×2.37) | 6.82e-3 / 0.68 (×2.37) | 6.82e-3 / 0.68 (×2.37) | 2.88e-3 |

**Predicted go/no-go [prediction-from-prior; classical, assumed model; NOT an H2 measurement].**
- **At the prior, encoding is predicted to still help.**
  - At η ≈ 0.05 the project sits **below the η ≈ 0.25 crossover** (exact for Iceberg; about 0.27 for the d ≥ 3 codes). Every code leaves less undetected error per step than bare: Iceberg ×0.60, d ≥ 3 ×0.52–0.53.
  - It stays below across the whole bracket η = 0.03–0.08: Iceberg ×0.56–0.66, d ≥ 3 ×0.48–0.59 **[measured, Stim]**.
  - The ranking and the acceptance gap are unchanged: Iceberg keeps 0.92 of shots after 3 steps vs 0.56–0.64 for the d ≥ 3 codes.
- **Coherent ε on un-twirled circuits is the only in-range flip risk, and this model cannot show the flip itself.**
  - The over-rotation option is a Pauli-twirled stand-in. It adds the same 12·sin²ε per step to every code and to bare, so the ratio climbs toward ×1 (×0.62 / ×0.72 / ×0.92 at sin²ε = 1e-5 / 1e-4 / 1e-3; ×0.93 at the corner η = 0.08, sin²ε = 1e-3) but never crosses it. The absolute gain per step, bare minus Iceberg ≈ 1.15e-3, does not change **[derived + measured]**.
  - A sign flip needs what the stand-in leaves out **[inferred, research/06 §5]**:
    - A coherent over-rotation that is not randomized-compiled adds in amplitude, so its error can grow faster than n·sin²ε, up to quadratically when repeated rotations stay aligned.
    - On a logical-ZZ gate, the un-twirled coherent ZZ part is ZZ-aligned, which raises the *effective* η toward the crossover.
  - research/06's speculative 1q-anchored guess, sin²ε ~ 2.5e-5 **[assumed]**, falls between the 1e-5 and 1e-4 scan points.
- **The η mapping is conservative.** `zz_bias` adds η *on top of* the uniform 1/15 ZZ share, so zz_bias = 0.05 means a total ZZ share of 0.11. That is about 2× the Fig. S3 read-off of 0.04–0.05 **[derived from `to_stim`]**.
  - Even the uniform row (ZZ share 0.067) is at or above the read-off.
  - Read-off composition (research/06 §3b): XX ≈ YY ≈ 0.05–0.1, ZZ ≈ 0.3–0.5, out of Σ ≈ 7.7–9.5 (all ×10⁻⁴). Iceberg's undetectable set per `ZZPhase` is {XX, YY, ZZ}, so the read-off puts its share at roughly 0.05–0.07, vs 0.24 in this model at η = 0.05 **[inferred; not run, because the code has no non-uniform Pauli-channel option]**.
  - Both effects push in the direction that favours encoding.
- **Conditional GO.** Encoding is predicted to help on H2's stochastic two-qubit noise *provided the encoded circuits are randomized-compiled* (or ε is small). Only the H2 emulator or the device can confirm this (HW-1 hardware half / HW-5, `handoff/05`). Cross-reference: `research/06-h2-noise-prior.md` §3–§6.

**Lattice dependence of the crossover (added 2026-10-08, review/13 M1) [derived; cross-checked against `data/q3_size.txt`].** The η ≈ 0.25 crossover and the ×0.60 ratio above are for the **2×2 test lattice**, where the periodic torus is degenerate (B = N bonds). In general the Iceberg step has B + 2N logical rotations (bonds + both Strang field halves) and the bare step B two-qubit + 2N one-qubit gates, so the crossover solves (B + 0.2N)/(B + 2N) = 0.2 + 0.8η: **η ≈ 0.36 on 2×3, ≈ 0.44 on large square tori (B = 2N), ≈ 0.55 on triangular tori (B = 3N)**, and the ratio at η = 0.05 falls from 0.60 (2×2) to 0.49, 0.44 and 0.375. The triangular value equals the repo's Stim accounting (q3_size.txt: Iceberg undetected 0.0086 / bare 0.0230 per step on 3×4 = 0.37). So the 2×2 numbers are the **most pessimistic** case; the conclusion "below the crossover at the prior" only gets stronger on realistic lattices.


---

# Why Selene keeps fewer shots than the Stim prediction (2026-10-07)

Script: `scripts/diagnose_selene_gap.py` → `data/selene_gap.txt`. Setup: Iceberg 2×2, 3 steps, assumed rates.

1. **Not the first-order approximation, not the local engine [measured].** First-order exp(−D) = 0.670, exact Stim sampling = 0.673, local-sim = 0.655 ± 0.015, all at p2 = 3e-3. The gap is specific to Selene.
2. **One noise channel at a time (rate 3e-3), Selene vs Stim [measured]:**

   | channel | result |
   |---|---|
   | two-qubit | agree (+2σ) |
   | **one-qubit** | **0.143 vs 0.594 (−70.6σ)** |
   | measurement | agree |
   | init/reset | −5σ |

3. **Cause, from Selene's own `with_metrics()` counts [measured]:**
   - Native two-qubit ops (`rzz`) = 124, which equals the model's 124 (88 CX + 36 ZZPhase).
   - **Native one-qubit ops = 355 `rxy` + 369 `rz` = 724, vs the 188 pytket-level gates the model charges: ×3.85.** Selene's `DepolarizingErrorModel` applies `p_1q` to every native single-qubit operation, including `rz`.
   - It also applies `p_init` to qubit allocations: 54 reset events (34 allocations) vs the model's 20.
4. **Stim with p1 × 3.85 and p_init × 1.5 [measured]** explains **about 60–80% of the gap**. Matched vs Selene: 0.834 vs 0.807 ± 0.009; 0.580 vs 0.554 ± 0.011; 0.753 vs 0.735 ± 0.010; 0.909 vs 0.900 ± 0.007. A **1–3σ residual remains, Selene still lower**. The likely reason is that Selene places its extra native noise and allocation resets at different points than a uniform count scaling assumes **[inferred, not resolved]**.

**Consequences:**
- **This is a noise-model definition difference, not a bug in either pipeline.** "p1 per gate" means something different in each simulator.
- On hardware what counts is the native operations *and* whether a native `rz` is actually noisy. On trapped ions `rz` is often implemented virtually **[inferred, unverified for H2]**, so the true 1q exposure is unknown. That is another reason to compare against H2-emulator or hardware runs before quoting absolute discard rates.
- **The code ranking is unaffected and Iceberg's lead widens** under native counting. First-order acceptance after 3 steps at 2×2, p2 = 1e-3: Iceberg 0.875 → 0.831, Steane 0.383 → 0.309, 5-qubit 0.469 → 0.373, concat 0.472 → 0.399. At 3e-3: Iceberg 0.574 vs 0.030–0.063.
