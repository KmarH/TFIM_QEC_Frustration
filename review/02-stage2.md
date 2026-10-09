# Review 02 — Stage 2 (square encoded / QEC gadgets)

**Reviewer:** qc-reviewer (independent milestone review)
**Date:** 2026-10-06
**Scope reviewed:** `src/qec/iceberg.py`, `verify.py`, `syndrome.py`, `concatenated.py`,
`on_paper_codes.py`, `tests/test_qec.py`; `research/02-stage2-iceberg.md`,
`docs/qec_feasibility.md`, `handoff/01-concatenated-iceberg-d4.md`; against SCOPE §6/§10/§14.
**Primary literature target:** arXiv:2211.06703v2 (Self, Benedetti, Amaro), Nat. Phys. 20, 219–224 (2024).

All checks below were run independently (my own PauliString lists / my own two-round
circuit), not by trusting the repo's objects. Environment: `. .venv/bin/activate`,
stim 1.16.0, Python 3.12.14.

---

## Summary verdict: APPROVE

Stage 2 as scoped (single-level Iceberg d=2 + algebra/syndrome verification + on-paper
d=3 codes + distance probe) is correct, matches its primary source, and is independently
reproduced. The concatenated d=4 FT gadget is correctly and legitimately NOT built — it is
routed to Claude Code per SCOPE §10/§14, with no invented construction or numbers. The
findings below are minor; none blocks approval.

---

## What passes (verified independently)

**Iceberg [[k+2,k,2]] definition vs arXiv:2211.06703** — VERIFIED.
Fig. 1a text of the paper (fetched from arxiv.org/html/2211.06703v2) states verbatim:
"Pauli-X logical operators act on t and a numbered qubit, while Pauli-Z logical operators
act on b and a numbered qubit. The two stabiliser operators S_X and S_Z consist on the
product of X and Z operators on all physical qubits." This matches `iceberg.py` exactly:
S_X = X^⊗n, S_Z = Z^⊗n, Xbar_i = X_t X_i, Zbar_i = Z_b Z_i. The abstract confirms
[[k+2,k,2]], even k, distance 2 detecting any single-qubit error, and "another two
ancillas … for syndrome measurement" (matches `syndrome.py`'s two-ancilla scheme).

**Iceberg algebra (my own construction, k=2,4,6)** — VERIFIED.
```
k=2 n=4: stab_commute=True log_commute_stab=True symplectic=True first_undetected_weight=2 witness=((0,1),('X','X')) weight1_undetected=None
k=4 n=6: stab_commute=True log_commute_stab=True symplectic=True first_undetected_weight=2 witness=((0,1),('X','X')) weight1_undetected=None
k=6 n=8: stab_commute=True log_commute_stab=True symplectic=True first_undetected_weight=2 witness=((0,1),('X','X')) weight1_undetected=None
```
Stabilizers commute (even overlap on all n, n even), logicals lie in the normalizer,
symplectic pairing correct, NO weight-1 error is undetected, and first-undetected weight = 2
→ distance exactly 2. The weight-2 witness X_0X_1 = (X_tX_0)(X_tX_1) = Xbar_0·Xbar_1 is a
genuine weight-2 logical, consistent with d=2.

**Two-round syndrome circuit (my own build: reset→SZ,SX→prob-1 error channel→SZ,SX→
difference detectors)** — VERIFIED.
```
Iceberg k=2: clean_silent=True every_weight1_fires=True missed=[]
Iceberg k=4: clean_silent=True every_weight1_fires=True missed=[]
```
The two-round / difference-detector rationale in `syndrome.py` is correct: |0…0> is a +1
eigenstate of S_Z but not S_X, so the parity-of-two-rounds detector is the right
construction to make the clean run deterministically silent. The use of X_ERROR/Y_ERROR/
Z_ERROR probability-1 *channels* (not deterministic gates) is the correct way to make an
injected error visible to Stim's detector sampler — the docstring's justification is
accurate.

**5-qubit [[5,1,3]] and Steane [[7,1,3]] (my own PauliString lists)** — VERIFIED.
```
[[5,1,3]]: stab_commute=True log_commute_stab=True Xbar_Zbar_anticommute=True first_undetected_weight=3
[[7,1,3]] Steane: stab_commute=True log_commute_stab=True Xbar_Zbar_anticommute=True first_undetected_weight=3
```
The 5-qubit generators (XZZXI, IXZZX, XIXZZ, ZXIXZ) are the standard cyclic set; Steane's
X/Z generators are the standard Hamming [7,4,3]-derived CSS set. Both measure distance 3.
I further confirmed the distance-3 result is a *true logical* distance, not an artifact of
the probe: for the 5-qubit code there are 0 weight-1 and 0 weight-2 errors commuting with
all stabilizers, and all 30 weight-3 commuting errors genuinely anticommute with a logical
operator (e.g. XYX on qubits {0,1,2}).

**Verifier has real discriminating power (negative control)** — VERIFIED.
`verify_code` is not vacuously passing: on a deliberately broken symplectic input it returns
`logical_symplectic_ok=False`, and with a stabilizer removed it reports
`all_weight1_detected=False` with 4 undetected weight-1 errors. The confusingly-named
symplectic branch (`if commutes == want_anticommute: sympl=False`) is logically correct.

**Test suite** — VERIFIED. `pytest tests/test_qec.py -q` → 12 passed; full `pytest -q` →
37 passed in 0.54s. Matches the claimed 37/37.

**Handoff decision for concatenated d=4** — APPROPRIATE.
`handoff/01-concatenated-iceberg-d4.md` correctly identifies that single-level Iceberg is
fully literature-specified and implemented, whereas the explicit FT concatenated
syndrome-extraction gadget (ancilla scheduling, flag placement, cross-level discard logic)
is not pinned to a single equation set in the fetched sources. Routing it to Claude Code is
exactly what SCOPE §10/§14 mandates. Nothing is invented: `concatenated.py` builds no
concatenated group and asserts no d=4 — it only provides the distance *probe* to check such
a group on arrival. The done-check in the handoff ("`min_undetected_weight(...)==4` as the
MEASURED first-undetected weight, FT under circuit-level injection, post-selection rate from
a stated noise model with uncertainty") is sound and matches good practice. 2608.06187 is
correctly flagged as future-dated / not to be trusted.

**Feasibility doc asserts no unmeasured numbers** — VERIFIED.
`docs/qec_feasibility.md` reports only [[n,k,d]] parameters (definitional) and detection
distances (which I independently measured: 2, 2, 2, 3, 3). It explicitly defers the discard/
post-selection rate to a measured, noise-model-stated milestone ("must be MEASURED … not
assumed"). No performance number is invented.

---

## Findings

### Critical
None.

### Major
None.

### Minor

**M1 — `concatenated.py` module docstring overpromises relative to code.**
Location: `src/qec/concatenated.py` lines ~1–38 (module docstring).
Reason: the docstring says the module will "Build the concatenated code's STABILIZER GROUP
by the standard concatenation rule and measure the resulting detection distance" and
"concatenate the smallest Iceberg [[4,2,2]] with itself at the level of the stabilizer
generators and report the measured distance." No such concatenated group is actually
constructed — the module contains only `min_undetected_weight`, `_pauli_assignments`, and
the single-level `iceberg_detection_distance`. The deliberate omission (routed to Claude
Code) is correct, but the docstring describes behavior that is not present, which could
mislead a reader into thinking a concatenated construction exists here.
Concrete fix: trim the docstring to state what the module actually provides today (a generic
weight-enumeration distance probe + single-level Iceberg distance helper) and point to
`handoff/01-concatenated-iceberg-d4.md` for the not-yet-built group/gadget. No logic change.

**M2 — `min_undetected_weight` conflates "undetected" with "logical"; safe for current
codes but a latent trap for the concatenated case.**
Location: `src/qec/concatenated.py:39-62` (`min_undetected_weight`), used by
`iceberg_detection_distance` and the test asserting 5-qubit/Steane distance 3.
Reason: the probe returns the first weight at which *some* Pauli commutes with all
stabilizers. Such a Pauli could in principle be a non-trivial element of the stabilizer
group itself (a trivial "error"), which would understate the code distance. For every code
in this stage this is harmless and I verified it: Iceberg's only stabilizers are weight-n
(≥4) so no low-weight stabilizer element exists, and for 5-qubit/Steane all weight-3
commuting errors are genuine logicals (checked: anticommute with a logical). But for the
concatenated d=4 code (handoff 01), stabilizer generators may have weight ≤ 4, so a weight-w
*stabilizer element* could be reported as "undetected" and the probe could claim a distance
below the true one.
Concrete fix (for the reviewer-check of the Claude Code deliverable, not Stage 2): when
measuring the concatenated distance, exclude errors that are products of stabilizers (e.g.
require the undetected error to anticommute with at least one logical operator), i.e.
measure the true *code* distance, not just the first stabilizer-commuting weight. The
docstring claim "the first undetected weight equals d" holds only when the minimum
stabilizer weight exceeds d, which should be stated.

**M3 — `handoff/plan.md` referenced but absent.**
Location: SCOPE §10/§14 ("Recorded in `handoff/plan.md`") and
`handoff/01-concatenated-iceberg-d4.md` ("see handoff/plan.md for the 3.11 flag").
Reason: the handoff plan registry file does not exist in `handoff/`. This is a process/
traceability gap, not a code defect — the single handoff brief is well-formed on its own.
Concrete fix: create `handoff/plan.md` listing handoff 01 (and the Python-3.11-vs-3.12 note),
owned by qc-overseer. Outside this reviewer's edit remit (I do not edit); flagged for the
overseer.

**M4 — Environment is Python 3.12, SCOPE §7/§14 pins 3.11.**
Location: `.venv` (Python 3.12.14) vs SCOPE §7 "Python 3.11, hard-pinned requirements.txt".
Reason: Stage-2 Stim work is unaffected (stim 1.16.0 runs fine on 3.12 and all 37 tests
pass), and the handoff doc acknowledges the 3.11 flag, but the live interpreter does not
match the pinned version. This matters later for guppylang/pytket-quantinuum pinning.
Concrete fix: either rebuild `.venv` on 3.11 before the tooling stages, or record an explicit
approved deviation. Not a Stage-2 blocker.

---

## Open items (carry forward)
1. Concatenated Iceberg d=4 FT gadget: await Claude Code deliverable (handoff 01). On arrival,
   re-verify with the *true code distance* (M2), circuit-level fault injection for FT, and a
   measured post-selection rate under a stated noise model with uncertainty.
2. Discard / post-selection rate for Iceberg d=2 under a stated noise model: unmeasured by
   design — must be produced (with uncertainty) at the noisy-simulation milestone for SCOPE Q1/Q4.
3. `handoff/plan.md` registry (M3) and Python 3.11 environment alignment (M4) — overseer/scaffold.
4. Logical-vs-physical TFIM comparison (SCOPE Q1) and the ranking of the four codes (Q4) remain
   DATA questions for later stages; nothing in Stage 2 overclaims them — the feasibility doc
   correctly tags its rankings [inferred — to be backed by data].

---

## Commands run (reproducible)
```
. /home/opc/KiroTest-project/.venv/bin/activate
python -c "import stim; print(stim.__version__)"            # 1.16.0
# independent Iceberg algebra k=2,4,6 (own PauliStrings)      -> all pass, dist=2
# independent two-round syndrome circuit k=2,4 (own build)    -> clean_silent, every weight-1 fires
# independent 5-qubit & Steane (own PauliStrings)             -> dist=3, Xbar/Zbar anticommute
# witness check: 5-qubit weight-3 are genuine logicals (30/30), weight-1/2 none
# negative control on verify_code                             -> catches broken symplectic & missing stabilizer
python -m pytest tests/test_qec.py -q                         # 12 passed
python -m pytest -q                                           # 37 passed
```
Primary-source confirmation: https://arxiv.org/abs/2211.06703 (abstract) and
https://arxiv.org/html/2211.06703v2 (Fig. 1a text) — stabilizer/logical forms match the repo.
