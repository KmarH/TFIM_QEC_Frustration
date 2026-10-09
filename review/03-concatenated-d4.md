# Review 03 — Concatenated Iceberg d=4 FT gadget (handoff 01)

**Reviewer:** qc-reviewer (independent milestone review)
**Date:** 2026-10-06
**Scope reviewed:** `src/qec/concatenated.py` (ConcatenatedIceberg + M2-safe `code_distance`),
`src/qec/concatenated_gadget.py` (flagged FT gadget, discard, `fault_distance`, `sample`),
`config.py` (QECConfig), `scripts/run_concat_d4.py`, `tests/test_concatenated.py`,
`docs/concatenated_iceberg_d4.md`; against `handoff/01-concatenated-iceberg-d4.md`,
`review/02-stage2.md` (finding M2), SCOPE §6/§10/§12.
**Deliverable:** concatenated Iceberg [[16,4,4]] default (18 qubits incl. ancilla+flag), returned
from Claude Code.
**Environment:** `. .venv/bin/activate`, stim 1.16.0, Python 3.12.14. Serial.

Every claim below was re-derived or re-measured with my OWN objects/circuits where cheap. The
repo's own asserts were NOT trusted; I reconstructed the stabilizer group and logicals from the
prose in `docs/concatenated_iceberg_d4.md` and ran independent brute-force searches.

---

## Summary verdict: APPROVE WITH CONDITIONS

The construction is correct and the two headline claims — **measured code distance 4** and
**circuit fault distance 4 with flags / 2 without** — are independently reproduced two ways each.
The gadget's clean run is silent, all weight ≤ 3 data errors are detected in both bases, the
discard rates match an explicitly non-H2 noise model with CIs, and logical rates are reported as
upper bounds. Nothing is invented; the two citations carry `[cite-unverified]`. The conditions are
documentation/numeric-hygiene items (one wrong error count in the write-up, one untagged citation
in a docstring, and tightening the "fault distance = 4" wording to match what the exact search
actually proves). None blocks the science; all are minor.

---

## What passes (verified independently)

**R1 — Code distance 4 is MEASURED (not assumed from "2×2"), with a genuine weight-4 witness.**
VERIFIED. I rebuilt the [[16,4,4]] stabilizers and logicals from scratch (own `stim.PauliString`
lists, from the doc's layout: `phys(j,q)=j*(k_i+2)+q`, inner `X̄_a=X_tX_a`, `Z̄_a=Z_bZ_a`, outer
lifts, logicals on blocks `t_o/b_o` and `i`) and brute-force enumerated every Pauli of weight ≤ 4,
counting only those that commute with all stabilizers AND anticommute with a logical:
```
ki=2 ko=2: n=16 k=4 ngen=12 (n-k=12) rank=12 dist=4 wit_wt=4 wit=+XX__XX__________
ki=2 ko=4: n=24 k=8 ngen=16 (n-k=16) rank=16 dist=4 wit_wt=4 wit=+XX__XX__________________
ki=4 ko=2: n=24 k=8 ngen=16 (n-k=16) rank=16 dist=4 wit_wt=4 wit=+XX____XX________________
```
Distance = 4 for all three (k_i,k_o) ∈ {(2,2),(2,4),(4,2)}; no undetected logical of weight ≤ 3
exists. The repo's `code_distance` reproduces the same values and witnesses, and I confirmed the
witness is a genuine logical, not a stabilizer element:
```
ki=2 ko=2: repo_dist=4 wit_wt=4 wit_is_logical=True wit_commutes_all_stabs=True any_wt<=3_logical=None
ki=2 ko=4: repo_dist=4 wit_wt=4 wit_is_logical=True wit_commutes_all_stabs=True any_wt<=3_logical=None
ki=4 ko=2: repo_dist=4 wit_wt=4 wit_is_logical=True wit_commutes_all_stabs=True any_wt<=3_logical=None
```
This closes review/02 **M2**: `code_distance` enumerates errors and keeps only those that
anticommute with a logical, so a weight-4 inner stabilizer (`XXXX`) is correctly NOT counted as an
undetected error. `tests/test_concatenated.py::test_code_distance_probe_excludes_stabilizers`
exercises exactly this and passes. The witness `XX__XX__` = inner `X̄_0` on blocks 0 and 1 is a
weight-4 logical, consistent with the d=4 claim and with the proof sketch in §3 of the doc.

**R2 — verify_code passes; generator count = n−k and generators independent.** VERIFIED. My own
GF(2) rank of the symplectic matrix of the reconstructed generators gives rank = n−k for all three
sizes (12, 16, 16 above). `verify_code` on the repo objects:
```
[PASS] cat | stab commute: True | logicals commute w/ stabs: True | logical symplectic ok: True | all weight-1 detected: True
```
for (2,2), (2,4), (4,2). Stabilizers mutually commute, logicals lie in the normalizer, the
X̄/Z̄ symplectic pairing is correct.

**R3 — Circuit fault distance is 4 with flags and 2 without, by BOTH methods, which agree; the
search is validated.** VERIFIED. I wrote my OWN exact 1–3-fault DEM search and compared it with the
repo's `fault_distance` and with `stim.search_for_undetectable_logical_errors`, for rounds ∈ {1,2,3}
and both bases:
```
flags=True  rounds=1 Z/X: repo=None mine=None stim_search=4
flags=True  rounds=2 Z/X: repo=None mine=None stim_search=4
flags=True  rounds=3 Z/X: repo=None mine=None stim_search=4
flags=False rounds=1 Z/X: repo=2    mine=2    stim_search=2
flags=False rounds=2 Z/X: repo=2    mine=2    stim_search=2
flags=False rounds=3 Z/X: repo=2    mine=2    stim_search=2
Steane code-capacity:     repo_fd=3 mine=3    stim_search=3
```
With flags, no combination of ≤ 3 circuit faults produces a silent logical error (`fault_distance`
returns None = ">3"), and Stim's independent search puts the exact distance at 4 — the two agree.
Without flags, both give 2 (the ablation is genuinely not FT to d=4). The search is validated: it
returns 3 for the Steane code under code-capacity noise, by all three methods. The repo's
`fault_distance` is an honest exact search (I reproduced its logic independently and got identical
results).

**R4 — Clean run silent; ALL weight ≤ 3 data errors detected in both bases.** VERIFIED. Clean runs:
```
basis=Z: clean det.any=False obs.any=False ndet=48 labels=48
basis=X: clean det.any=False obs.any=False ndet=48 labels=48   (4096 shots each)
```
I then independently injected EVERY nonidentity data Pauli of weight ≤ 3 as a probability-1 channel
into the real circuit (not the XOR shortcut) and counted how many fire no detector in either basis:
```
independent brute-force inject: 0 undetected of 16248 nonidentity weight<=3 data errors (both bases)
repo undetected_low_weight_errors count: 0
```
Zero undetected, matching the repo. Negative control: every weight-1 X/Y/Z on representative qubits
fires a detector, so the silence is real, not a vacuous detector set. The weight-4 inner logical
`X0 X1 X4 X5` is silent and flips all four observables (`det.any=False, obs=[True,True,True,True]`),
as expected for a d=4 logical.

**R5 — Discard rates from a stated, illustrative, NON-H2 noise model, with CIs; logical rates as
upper bounds.** VERIFIED. The noise header in `data/concat_d4.txt`, `config.py:QECConfig`, and
`scripts/run_concat_d4.py` all read "[illustrative, NOT H2-calibrated]". My independent 20k-shot
sample agrees with the committed 200k-shot table within CIs:
```
                 my 20k           committed 200k (Z/X)
p=1e-4  discard  0.0318 / 0.0320  0.0305 / 0.0306
p=1e-3  discard  0.2651 / 0.2663  0.2638 / 0.2657
p=3e-3  discard  0.5982 / 0.6080  0.5994 / 0.6061
```
Wilson 95% CIs are reported per point; logical errors are 0 among kept at every p and are written as
`0/kept` with a 95% upper bound (≈2e-5…5e-5), never as an invented rate. No H2 performance number is
asserted anywhere in the deliverable.

**R6 — Nothing invented; `[cite-unverified]` tags present on both citations.** VERIFIED.
`docs/concatenated_iceberg_d4.md` tags Knill C4/C6 (Nature 434, 39 (2005)) and Chao–Reichardt
(arXiv:1705.02329) `[cite-unverified]`, and `handoff/plan.md` carries both forward for
qc-researcher. The construction is tagged `[derived]` with a proof sketch; measured quantities are
tagged `[measured]`. No numbers are asserted beyond what the code produces.

**Test suite.** `pytest -q` → 53 passed in 5.08s; `pytest tests/test_concatenated.py -q` → 16 passed.
Matches the claimed 53/53.

---

## Findings

### Critical
None.

### Major
None.

### Minor

**m1 — Write-up states the wrong total error count ("16,104").**
Location: `docs/concatenated_iceberg_d4.md` §3, last line ("detects all 16,104 nonidentity data
errors of weight ≤ 3").
Reason: the true number of nonidentity Pauli errors of weight ≤ 3 on 16 qubits is
C(16,1)·3 + C(16,2)·9 + C(16,3)·27 = 48 + 1080 + 15120 = **16,248**, which I confirmed by direct
enumeration. The repo's own `undetected_low_weight_errors` and my injection sweep both iterate the
full set and report 0 undetected, so the *claim* (all detected) is correct — only the stated count is
off by 144. Likely an earlier count that excluded something (e.g. the 144 = 48·3 weight-pattern?).
Concrete fix: change 16,104 → 16,248 in the doc, or state exactly what subset 16,104 refers to.
No code change; the detection result is unaffected.

**m2 — "Fault distance 4" is asserted but the exact in-repo search only proves ">3".**
Location: `docs/concatenated_iceberg_d4.md` §5 table / §7 ("Fault distance 4 is measured two
independent ways"); `tests/test_concatenated.py::test_flagged_gadget_fault_distance_four`.
Reason: `fault_distance(..., max_faults=3)` returns None, which means strictly "no undetected
logical with ≤ 3 faults" (i.e. fault distance > 3), not "= 4". The exact value 4 comes only from
`stim.search_for_undetectable_logical_errors` (which returns 4). The doc's own §5 table is accurate
("exact search ≤3 faults → no undetected logical"; stim search → 4), but the §7 summary phrasing
"measured two independent ways" slightly overstates what the exact ≤3 search alone establishes. The
two methods are consistent (>3 and =4 agree), so this is wording, not a defect.
Concrete fix: in §7 say "fault distance > 3 by exact ≤3-fault search AND exactly 4 by Stim's
undetectable-logical-error search; the two are consistent." Optionally rename the test to
`...fault_distance_exceeds_three` to match its actual assertion (`fault_distance is None` plus
`len(stim search) == 4`).

**m3 — Chao–Reichardt citation in a source docstring is not `[cite-unverified]`-tagged.**
Location: `src/qec/concatenated_gadget.py:11` (module docstring: "Chao–Reichardt single-flag
pattern, arXiv:1705.02329").
Reason: the write-up (`docs/`) correctly tags this `[cite-unverified]`, but the inline docstring
cites it without the tag. The module header does say "[derived construction — verified numerically
below]", so a reader is not told the construction is literature-proven; still, for consistency the
unverified reference should be marked in the code too.
Concrete fix: append `[cite-unverified]` to the arXiv:1705.02329 mention in the docstring (and the
Knill C4/C6 line in `src/qec/concatenated.py:9`, which likewise references the pattern without a
tag). Comment-only; no logic change.

**m4 — Open items from Claude Code are legitimate scope limits, not defects (restated for the record).**
Location: `docs/concatenated_iceberg_d4.md` §7; handoff open items.
Reason: (i) no correction mode (detection-only at both levels) — a d=4 code *could* correct 1 and
detect 2; this is explicitly flagged as a possible extension, not built. Acceptable: SCOPE §6 names
the implemented path as detection-based Iceberg concatenation, and the gadget's discard predicate is
pure post-selection. (ii) 88 CX/round not optimised — I confirmed the count is exactly 88 CX pairs
per round (inner 8×6 + outer 4×10). This drives the high discard rate and belongs in the Q4
cost comparison, as the doc says. (iii) no comparison to the Iceberg-paper two-ancilla gadget —
correctly deferred. None of these are correctness problems.

**m5 — Environment is Python 3.12, SCOPE §7 pins 3.11 (carried from review/02 M4).**
Location: `.venv` (3.12.14) vs SCOPE §7. Unchanged from Stage 2; the Stim work is unaffected (all
53 tests pass on 3.12). Still relevant for the later guppylang/pytket-quantinuum pinning. Not a
blocker for this milestone.

---

## Open items (carry forward)
1. **m1/m2/m3** are the conditions for upgrading to a clean APPROVE: fix the 16,104→16,248 count,
   tighten the "fault distance 4" wording to "> 3 (exact ≤3-fault) and = 4 (Stim search)", and add
   the `[cite-unverified]` tag to the two in-code citations. All documentation/wording; no logic.
2. **qc-researcher** must confirm the two `[cite-unverified]` citations (Knill C4/C6 scheme, Nature
   434, 39 (2005); Chao–Reichardt single-flag, arXiv:1705.02329) before either enters the report.
3. **Correction-mode extension** (correct 1 / detect 2 at d=4) and the **CX-count optimisation** are
   deferred; both feed the SCOPE Q4 code-ranking stage, where the ~88 CX/round and the discard rates
   above (3%–60% over p∈[1e-4,3e-3], illustrative noise) are the cost evidence.
4. **Comparison to the Iceberg-paper two-ancilla gadget** remains open (Q4).
5. **Python 3.11 environment alignment** (m5 / review/02 M4) — overseer/scaffold, before the tooling
   stages.
6. The discard/logical rates here are under an **illustrative, non-H2** model; a hardware-regime
   number for Q1/Q4 still requires a stated-and-justified noise model at the noisy-simulation
   milestone (not these numbers).

---

## Commands run (reproducible)
```
. /home/opc/KiroTest-project/.venv/bin/activate
python -c "import stim,sys; print(stim.__version__, sys.version.split()[0])"   # 1.16.0 3.12.14
python -m pytest -q                                   # 53 passed in 5.08s
python -m pytest tests/test_concatenated.py -q        # 16 passed

# R1: own PauliString rebuild of [[16,4,4]]/[[24,8,4]]x2, brute-force code distance (exclude stabs),
#     GF(2) rank of generators                        -> dist=4, wit_wt=4, rank=n-k, all three sizes
# R1/R2: repo code_distance + verify_code vs mine; witness is a genuine logical; no wt<=3 logical
# R3: own exact 1-3 fault DEM search vs repo fault_distance vs stim search, rounds {1,2,3}, Z/X,
#     flagged (None/None/4) and unflagged (2/2/2); Steane code-capacity validation (3/3/3)
# R4: clean run silent (4096 shots, both bases); own prob-1 injection of all 16248 nonidentity
#     weight<=3 data errors -> 0 undetected both bases; weight-4 logical silent & flips 4 observables;
#     negative control: weight-1 errors fire detectors
# R5: own 20k-shot sample vs committed 200k table -> discard rates agree within CI; logical 0/kept UBs
# R6: grep [cite-unverified]/H2/calibrat across repo -> both citations tagged; noise 'NOT H2-calibrated'
# CX count: 88 CX pairs per round (inner 8*6 + outer 4*10), confirmed
```
No `src/`, `tests/`, or `config.py` file was edited (reviewer remit).
