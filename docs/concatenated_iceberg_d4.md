# Concatenated Iceberg code (d=4) — construction, FT gadget, verification

Deliverable for `handoff/01-concatenated-iceberg-d4.md`. Code: `src/qec/concatenated.py`,
`src/qec/concatenated_gadget.py`; tests: `tests/test_concatenated.py`; data:
`data/concat_d4.txt` (from `scripts/run_concat_d4.py`, settings in `config.py: QECConfig`).

Status tags: **[derived]** = constructed here with a proof sketch and numerical check;
**[measured]** = output of the code in this repo; **[cite-unverified]** = reference
qc-researcher must confirm before it goes in the report.

## 1. Layout [derived]
Inner code Iceberg [[k_i+2, k_i, 2]], outer code Iceberg [[k_o+2, k_o, 2]] (arXiv:2211.06703).
Use n_o = k_o+2 inner blocks (j) and k_i outer blocks (a). **Outer qubit j of outer block a
is inner logical qubit a of inner block j.** Physical index: `j*(k_i+2) + q` with the
IcebergCode local layout (data 0..k_i-1, t=k_i, b=k_i+1). Logical index `a*k_o + i`.
Result: [[n_o(k_i+2), k_i k_o, 4]]; default k_i=k_o=2 → **[[16,4,4]]** (18 qubits with ancilla+flag).
This multi-block interleaving is the same pattern as Knill's C4/C6 scheme
(E. Knill, "Quantum computing with realistically noisy devices," Nature 434, 39–44 (2005),
doi:10.1038/nature03350, Fig. 1 "Block structure of C4/C6 concatenated codes" — confirmed,
research/03-concat-citations.md).

## 2. Stabilizers and logicals [derived; verify_code PASS]
With inner logicals X̄_a^(j) = X_{t,j} X_{a,j}, Z̄_a^(j) = Z_{b,j} Z_{a,j}:
- inner: S_X^(j) = X on block j, S_Z^(j) = Z on block j (j = 0..n_o-1), weight k_i+2;
- outer: S_X^[a] = ∏_j X̄_a^(j), S_Z^[a] = ∏_j Z̄_a^(j) (a = 0..k_i-1), weight 2n_o;
- logicals: X̄_{a,i} = X̄_a^(t_o) X̄_a^(i), Z̄_{a,i} = Z̄_a^(b_o) Z̄_a^(i), weight 4.

The generator count is 2n_o + 2k_i = n − k and the generators are independent (rank checked), so the
group is complete. For [[16,4,4]]: inner `XXXX` / `ZZZZ` on qubits {0-3},{4-7},{8-11},{12-15};
outer S_X^[0] = X on {2,0,6,4,10,8,14,12}, S_X^[1] = X on {2,1,6,5,10,9,14,13}; outer
S_Z^[a] uses b = 3 + 4j instead of t (see `ConcatenatedIceberg.stabilizers()` for the strings).

## 3. Why d = 4 [derived, then measured]
Suppose E is undetected and nontrivial. E must commute with the inner stabilizers, so on each
inner block it is either trivial or an inner logical, and any inner block where it is nontrivial
carries weight ≥ 2. Its induced outer operator must commute with the outer stabilizers and act
nontrivially on some outer block a. That requires an outer logical, i.e. ≥ 2 outer qubits of
block a. Those outer qubits sit in **distinct** inner blocks, because each inner block feeds
block a only once. That gives ≥ 2 blocks × ≥ 2 weight, so wt(E) ≥ 4.
**[measured]** `code_distance` = 4 for (k_i,k_o) ∈ {(2,2),(2,4),(4,2)}. It enumerates every
Pauli of weight ≤ 4 and counts only errors that anticommute with a logical, which fixes
review/02 M2. Witness `XX__XX__________`. The circuit (both bases) detects all 16,248
nonidentity data errors of weight ≤ 3.

## 4. FT syndrome-extraction gadget [derived]
Each round measures, in this order, inner S_Z (all blocks), inner S_X, outer S_Z, outer S_X. Every
stabilizer uses **one ancilla + one flag** (R. Chao & B. W. Reichardt, "Quantum error correction
with only two extra qubits," Phys. Rev. Lett. 121, 050502 (2018), arXiv:1705.02329; §V covers the
[[n,n−2,2]] detection case directly applicable to Iceberg — confirmed, research/03-concat-citations.md).
The flag CNOTs come after the 1st and before the last data CNOT. An ancilla fault that
spreads to ≥ 2 data qubits flips the flag. Outer stabilizers use an interleaved CNOT order:
all t (or b) anchors first, then the slot-a qubits. An unflagged prefix is then weight ≤ 1 on all but one
inner block, so the inner checks still catch it. Ancilla and flag are reset and reused (one
pair, sequential), which suits the H2 all-to-all model.
Memory experiment: prep |0⟩^n (or |+⟩^n), `rounds` rounds, transversal readout in the
same basis. The circuit is CSS, so the Z and X memory experiments together cover X- and Z-type logical failures.

**Discard predicate (across levels):** keep a shot iff no detector fires. The detectors are
(i) every flag outcome, (ii) each inner/outer stabilizer XOR its previous round, and (iii) the final
data parity XOR the last round. Detection only; no correction is attempted at either level. (A
d=4 code could instead correct 1 and detect 2. That is a possible extension and is not built.)

## 5. Fault tolerance [measured]
| gadget | exact search ≤3 faults | `stim.search_for_undetectable_logical_errors` |
|---|---|---|
| flagged (default), Z and X basis | no undetected logical | **4** |
| unflagged ablation | **2** | 2 |

Fault distance > 3 (exact ≤3-fault search) and = 4 (Stim search) holds for rounds ∈ {1,2,3} and
for the [[24,8,4]] variants.
So with flags, no 1, 2 or 3 circuit faults (CX depolarizing, H, idle, reset, measurement)
produce a silent logical error. Without flags, 2 faults suffice (e.g. two weight-2 inner hooks
aligned on the same slots). The search itself is validated: it returns 3 for Steane under
code-capacity noise.

## 6. Post-selection (discard) rate [measured, illustrative noise]
Noise model (stated, **not H2-calibrated**): DEPOLARIZE2(p) after every CX; DEPOLARIZE1(0.1p)
after every H; X_ERROR(p) on every reset and measurement; DEPOLARIZE1(0.1p) idle on data per
stabilizer group. 2 rounds, 200k shots per point, Wilson 95% CIs. Full table in `data/concat_d4.txt`:

| p | discard rate (Z / X memory) | logical errors among kept |
|---|---|---|
| 1e-4 | 3.05% / 3.06% (±0.08%) | 0 (95% UB ≈ 2e-5) |
| 1e-3 | 26.4% / 26.6% (±0.2%) | 0 (95% UB ≈ 2.6e-5) |
| 3e-3 | 59.9% / 60.6% (±0.2%) | 0 (95% UB ≈ 5e-5) |

The discard rate is high because each round has 12 flagged stabilizer measurements (8 weight-4 inner, 4 weight-8 outer): 88 CX per round, 176 for 2 rounds, plus prep and readout.
That cost belongs in the Q4 comparison. Logical-error rates are below the sampling floor at these
shot counts, so they are reported as upper bounds, not as values.

## 7. For the reviewer
- d=4 is the measured first logical weight. Circuit fault distance is **> 3** by the exact
  ≤3-fault DEM search (`fault_distance` returns None) **and exactly 4** by Stim's
  `search_for_undetectable_logical_errors`; the two are consistent. Without flags both methods
  give 2 (the ablation is genuinely not FT to d=4).
- Open: the CX count per round has not been optimised, and the gadget has not been compared with the
  Iceberg-paper two-ancilla gadget. Hardware noise numbers are not used. Both citations above
  (Knill C4/C6; Chao–Reichardt flags) were confirmed by qc-researcher (research/03-concat-citations.md).
