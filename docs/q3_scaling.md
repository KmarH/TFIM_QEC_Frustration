# Q3 generalization study: does the Iceberg-vs-Gauss-law verdict survive size, field and noise?

> **Status line, true of every number in this document.** These are **classical predictions under
> an ASSUMED noise model** (the research/06 H2 prior: Pauli-trajectory Monte Carlo for the curves,
> Stim first-order fault accounting for the rates). **None is an H2 or hardware result.** Nothing
> in this study was submitted to Nexus or to hardware, and no HQC was spent.

**Code:** `src/q3_scaling.py` (cheap Stim stage), `src/noisy_q3_sweep.py` (expensive stage and the
scoring), `src/noise_scaling.run_iceberg_scaled` (D6) ·
**tests:** `tests/test_q3_scaling.py`, `tests/test_noisy_q3_sweep.py`,
`tests/test_probe_q3_scaling_timing.py`, `tests/test_iceberg_scaled.py` (all frozen before
implementation; hashes in `handoff/RESUME.md`), plus `tests/test_q3_score_cell.py` (5 regression
tests for the scorer, written after it and labelled as such). **43 new tests; the full suite is
green at 705 passed / 23 skipped on the Oracle VM, Python 3.12.14 aarch64** — 662 baseline + 43,
reconciling exactly ·
**scripts:** `scripts/run_q3_scaling.py` → `data/q3_scaling.txt`;
`scripts/probe_q3_scaling_timing.py` (D5 timing); `scripts/run_q3_sweep.py` → `data/q3_sweep.txt` ·
**settings:** `CONFIG.q3_scaling`, with the noise from `CONFIG.sensitivity`.

## 1. The question, and why it needed asking

`docs/q3_thermalization.md` §9.2 concluded that for Q3-type diagonal observables, **Gauss-law
post-selection of the bare circuit is the effective mitigation and Iceberg encoding adds at most
modest value at a substantially higher shot cost**: residual 0.0017 ± 0.0004 at ×1.43 shots
(bare + Gauss) against 0.019 ± 0.008 at ×3.1 shots (Iceberg), with Iceberg + Gauss at the
statistical floor [measured, under the assumed model].

That conclusion rested on **one grid cell**: N = 12 logical sites (3×4, flippable start), h = 0.3,
noise scale λ = 1. A single cell cannot distinguish a general statement about the two mitigations
from an accident of one lattice at one field at one noise strength — and the project's Q3
recommendation, and the encoded-vs-bare framing of the report, rest on it. This study varies the
three axes the cell fixed.

**Axes (decision cards D1–D3, project lead, 2026-10-22).**

| axis | values | note |
|---|---|---|
| D1 size | N = 12 (3×4 flippable), 18 (3×6 3-sublattice), 20 (4×5 flippable) | plus N = 36, 54 in the Stim stage only (beyond the state-vector ceiling) |
| D2 field | h = 0.1, 0.2, 0.3, 0.5 | `Q3BaselineConfig.h_curves`; no new field value is introduced |
| D3 noise | λ = 1, 2, 3 | the `NoiseScalingConfig` insertion ladder, now on **both** arms (D6) |

Every size maps to an **already validated** (Lx, Ly, initial state) of `Q3BaselineConfig`
(`src/q3_scaling.SIZE_TO_CASE`): no new lattice or initial-state design enters here. Iceberg needs
an even number of logical qubits, so every size is even.

**Design decisions that shape what can be concluded.**

- **D4 — cheap prefilter first.** The axes are varied one at a time around the published cell, plus
  three extreme combinations, and only after a Stim-only prefilter has said which cells can resolve
  anything. The full 36-cell cross product is priced in `data/q3_scaling.txt` §6 but is not run:
  the expensive stage costs 2^(N+4) per encoded trajectory-step.
- **D5 — measure the cost before committing it.** A wall-clock probe
  (`scripts/probe_q3_scaling_timing.py`) sizes the trajectory budget per cell instead of inheriting
  the published counts, which were measured on a 16-physical-qubit cell.
- **D6 — build the encoded λ runner.** Until this pass the repository could amplify noise only on
  the bare arm (`src/noise_scaling.run_bare_scaled`); decision D-NS3 had run Iceberg at λ = 1 and
  the exclusion was never revisited in code. Reporting a λ = 1 Iceberg number under a λ > 1 label
  would have been the easy error, so the sweep **raised** instead. The project lead chose to build
  the runner (`run_iceberg_scaled`), so both arms of the ladder are now amplified by the same
  mechanism on the same channel. §2.2 states what that costs in comparability.
- **Survival-matched windows.** At the prior, Iceberg's detector survival falls with both N and λ.
  Comparing every cell over the published 48-step window would mean comparing ~2 %-survival noise
  at N = 20 against 7 % at N = 12. Instead each cell's encoded arm runs out to the largest window
  whose **predicted** survival still clears 5 %, and every cell states its own window: the
  comparison is at matched survival, and the shrinking encoded reach is reported as a result rather
  than hidden in the error bars.

## 2. Method

### 2.1 The two stages

**Cheap stage (Stim, unbounded in N).** `src/q3_scaling.stim_rate_table` returns the first-order
per-Trotter-step fault probabilities of the bare and Iceberg programs — reusing
`src/noisy_q3.size_row` and `src/encoded_codes.detected_total`, with no fault-counting logic
reimplemented. Iceberg survival is `exp(-(prep offset + detect rate × steps))`, where the
step-independent prep/readout offset is solved from the affine form of `detected_total` at two step
counts and **raises** if that affinity does not hold, rather than averaging a nonlinearity away.

Because Stim treats Pauli rotations as the identity (exact for Pauli-fault propagation), the
per-step rates are **h-independent**: the field enters only through the window length
(`qdm_times / h`). This is stated in the module docstring and is why §3's tables are flat in h.

**Expensive stage (exact circuit trajectories).** `src/noisy_q3_sweep.run_noisy_sweep` runs the
bare and Iceberg arms gate by gate with the assumed Pauli channel, post-selecting the encoded arm
on every detector, and `score_cell` scores the result. Each cell is a separate process, so cells
run in parallel across the project's three machines and a cell that dies costs one cell.

### 2.2 Two λ scopes, and why they are not the same experiment

> **2026-10-24, DECIDED-9:** a single scope now, **every two-qubit gate**, used by the simulator,
> the Stim table and the pytket circuit alike. The old Stim "2q" scope left out the 72 CX of the
> encoded state preparation (they occur once), so the change moves the survival offset, not the
> per-step rates. The discussion below is the record of the earlier two-scope design.

The trajectory runners amplify noise by **Pauli insertion before two-qubit gates**, which scales
the 2q channel and nothing else — 1q, SPAM and idle noise stay at λ = 1 (the contract
`insert_paulis` already documented for the bare arm). The Stim stage can scale either the same 2q
classes (`("rot-zz", "syn-cx")`) or every class present (the "all gates" row of
`research/derivations/01-noise-scaling-arm.md`). `data/q3_scaling.txt` prints both and the keep
verdict uses the **2q** scope, because that is what the expensive stage actually runs. At λ = 1 the
two coincide exactly, which is the consistency check that the scopes are wired as described
[measured: both columns read 0.0692 at N = 12, λ = 1].

**What `run_iceberg_scaled` guarantees** (spec frozen in `tests/test_iceberg_scaled.py` before it
existed, all 13 cases passing):

- at λ = 1 it is **bitwise identical** to `run_iceberg` at the same seed, so the ladder's λ = 1
  rung stays comparable to the published `data/q3_noisy.txt` cell [tested];
- amplifying an all-zero channel is still the ideal circuit, to 1e-8 (transparency) [tested];
- a weight-1 insertion model drives post-selection down, as a distance-2 code must [tested];
- measured survival at λ = 2, 3 agrees with the **independent** Stim first-order prediction
  (a different code path: fault propagation, not trajectories) [tested];
- `method="fold"` is **refused**: folding the encoded circuit would fold its syndrome-extraction CX
  gates too, changing the code's detection structure and not only its error rate. That is a
  separate design question and is not silently assumed here.

### 2.3 The metric

`score_cell` is lifted from `scripts/run_q3_noisy.py`, the script that produced the published
table, so a generalized cell is comparable to the published one by construction:

- residual = mean |O_noisy − O_ideal| over the window, for the flippable density;
- raw modes are scored against the ideal **raw** curve; Gauss-post-selected modes against the ideal
  **sector-conditioned** curve (the quantity they estimate), with the raw score reported alongside;
- the Iceberg arm is scored on its own shorter grid with the ideal curve interpolated onto it;
- shot cost = 1/mean(acceptance) over the window, plus the cost at the last point; Iceberg + Gauss
  pays detector survival **times** Gauss acceptance;
- **SE** is the mean per-point batch SE, and a residual at or below it is reported as **not
  resolved** — the statistical floor, not a win for either arm.

## 3. Cheap-stage results [derived accounting; ASSUMED noise; not an H2 result]

> **2026-10-24 (DECIDED-9).** `data/q3_scaling.txt` was regenerated under the every-2q-gate scope. The per-step rates are unchanged; the survival offset (the 72 state-preparation CX) moved, so the survival-matched windows would now be one step shorter at (18, -, 3) (13 -> 12) and (20, -, 3) (12 -> 11). The sweep cells KEEP the windows they were run with (`config.Q3ScalingConfig.cell_windows`); the numbers quoted in this section are the pre-2026-10-24 ones, kept as the record.

Full tables: `data/q3_scaling.txt`.

### 3.1 Rates and survival

Per-step rates are exactly linear in N for the bare fault rate and the Iceberg undetected-logical
rate, and λ multiplies both exactly, as first order requires [measured, and frozen-tested]:

| N | bare fault / step | Iceberg detect / step | Iceberg undetected / step | prep offset | survival at 48 steps |
|---|---|---|---|---|---|
| 12 | 2.30e-2 | 5.43e-2 | 8.64e-3 | 0.065 | **0.0692** |
| 18 | 3.46e-2 | 7.88e-2 | 1.30e-2 | 0.096 | 0.0207 |
| 20 | 3.84e-2 | 8.69e-2 | 1.44e-2 | 0.106 | 0.0139 |

(λ = 1, 2q scope. The N = 12 survival **0.0692** reproduces the 0.069 of `data/q3_noisy.txt` line
56 — the continuity check that this module measures the same quantity as the published cell.)

### 3.2 Survival-matched encoded windows

Largest window (Trotter steps, and t in units of 1/|J|) whose predicted survival clears 5 %:

| N | λ = 1 | λ = 2 | λ = 3 |
|---|---|---|---|
| 12 | 48 (t = 12) | 28 (t = 7) | 19 (t = 4.75) |
| 18 | 36 (t = 9) | 19 (t = 4.75) | 13 (t = 3.25) |
| 20 | 33 (t = 8.25) | 17 (t = 4.25) | 12 (t = 3) |

**The published 48-step encoded window is reachable only at N = 12, λ = 1.** Every larger size and
every amplified-noise cell must be compared on a shorter window — which is why matched survival,
not a matched window, is the comparison rule. Each λ step roughly halves the encoded reach, and the
reach also shrinks with size; both follow from rates that grow linearly in N and λ while the
tolerable total detection probability is fixed.

### 3.3 The bare arm's fault budget

Expected bare faults per shot over each field's physics window (`qdm_times / h`) [derived]:
the window is 480 steps at h = 0.1 and 96 at h = 0.5, so the weak-field cells are the expensive
ones in both compute and noise. At N = 18, h = 0.1, λ = 3 the bare circuit carries **47.7 faults
per shot**; even at N = 20, h = 0.5, λ = 3 it carries 10.6. Unmitigated bare curves are therefore
not Q3 measurements anywhere in this grid at the prior, which is the §9.2 finding reproduced across
the whole study rather than at one cell.

## 4. Expensive-stage results

Full tables: `data/q3_sweep.txt` (sections 5 and 6 carry the v2 scores).

### 4.0 The v2 reading (DECIDED-8, DECIDED-10, 2026-10-24) — PRELIMINARY

**Read this first; §4.2's verdict column is superseded.** Blind review (review/18) found three
problems: the old verdict subtracted residuals measured against **different** reference curves (F1);
the 11th cell rested on **one** surviving trajectory, whose 3e-17 error bar made it read as a win
(F5, F9); and both N = 20 cells had run at half their declared budget without a record (F13). The
project lead then ruled (DECISIONS.md DECIDED-8 to DECIDED-10):

- every mode is scored against **both** ideal curves, and modes are compared within one;
- a mode has an estimate only above a **pre-declared** effective-sample floor;
- the error bars are a jackknife over batches;
- verdicts are called on the bias-corrected mean square;
- every cell that misses the floor gets **one** re-run at a budget solved in advance
  (research/derivations/02-postselected-estimator.md).

The table below applies those rules to the cells as run on 2026-10-22/23 [measured; classical
prediction under the ASSUMED model].

**What it says, in one paragraph** [inferred, with the qualification]: at N = 12, **bare + Gauss beats
Iceberg alone** in all 7 cells against the conditioned target (+1.5σ to +5.4σ), so that half of §9.2
survives. However, **Iceberg + Gauss beats bare + Gauss** against the conditioned target, the quantity
both Gauss-filtered modes estimate, in 6 of the 7 cells (−1.4σ to −3.1σ; unresolved at h = 0.1). It
does so at 4–7× the shots by the mean(1/acceptance) measure. Against the raw target the order is
reversed in 6 of 7 cells. The N = 12 error bars are **jackknife** errors: all seven cells were
replayed at their original seeds, each replay reproduced its stored cell to rtol 1e-10, and the
replays were adopted on 2026-10-24. **N = 18 and 20 have no encoded estimate yet** (end-of-window
effective sample 1–6 on the 10-23 runs); their pre-declared re-runs are running. **Preliminary
until those land.**

<!-- v2-tables:begin -->
*Generated by `scripts/gen_q3_doc_tables.py` from `runs/q3_sweep/` - do not edit by hand. Classical prediction under the ASSUMED research/06 noise model; not an H2 result.*

Rules (DECIDED-8, DECIDED-10, fixed before rescoring): Kish ESS >= 10 at every window point or **no estimate (n.e.)**; bias-corrected rms `sign(msd) sqrt|msd|`, msd = mean[(O - O_ref)^2 - Var O]; winner only when |gap| > 1 x combined SE of the msd's, within one reference.
**Error bars are LEGACY** (per-point batch SE) for cells without per-batch data; the jackknife replaces them as the replays land.

**rms distance from each ideal curve, over the common encoded window**

| N | h | λ | bare raw (raw) | bare + Gauss (raw) | Iceberg (raw) | Iceberg + Gauss (raw) | bare raw (cond) | bare + Gauss (cond) | Iceberg (cond) | Iceberg + Gauss (cond) |
|---|---|---|---|---|---|---|---|---|---|---|
| 12 | 0.1 | 1 | 0.0551 | 0.0011 | 0.0144 | ≲0.0017 | 0.0557 | 0.0010 | 0.0151 | ≲0.0013 |
| 12 | 0.2 | 1 | 0.0613 | 0.0023 | 0.0191 | 0.0033 | 0.0640 | 0.0020 | 0.0217 | ≲0.0006 |
| 12 | 0.3 | 1 | 0.0597 | 0.0061 | 0.0259 | 0.0071 | 0.0660 | 0.0025 | 0.0323 | 0.0013 |
| 12 | 0.3 | 2 | 0.0625 | 0.0056 | 0.0306 | 0.0063 | 0.0685 | 0.0025 | 0.0374 | ≲0.0013 |
| 12 | 0.3 | 3 | 0.0586 | 0.0059 | 0.0344 | 0.0071 | 0.0648 | 0.0019 | 0.0405 | ≲0.0009 |
| 12 | 0.5 | 1 | 0.0586 | 0.0227 | 0.0177 | 0.0243 | 0.0820 | 0.0035 | 0.0418 | 0.0015 |
| 12 | 0.5 | 3 | 0.0565 | 0.0230 | 0.0248 | 0.0236 | 0.0793 | 0.0024 | 0.0488 | 0.0016 |
| 18 | 0.1 | 3 | 0.0993 | 0.0220 | n.e. | n.e. | 0.0998 | 0.0225 | n.e. | n.e. |
| 18 | 0.3 | 1 | 0.0738 | 0.0052 | n.e. | n.e. | 0.0789 | 0.0045 | n.e. | n.e. |
| 20 | 0.3 | 1 | 0.0497 | 0.0067 | n.e. | n.e. | 0.0566 | 0.0009 | n.e. | n.e. |
| 20 | 0.5 | 3 | 0.0432 | 0.0237 | n.e. | n.e. | 0.0657 | ≲0.0011 | n.e. | n.e. |

**Head to head within each reference** (gap/σ of the msd's; negative = the second mode is closer)

| N | h | λ | ref | pair | gap/σ | verdict |
|---|---|---|---|---|---|---|
| 12 | 0.1 | 1 | raw | bare + Gauss vs Iceberg | +1.5 | bare + Gauss better: rms 0.0011 vs 0.0144 |
| 12 | 0.1 | 1 | raw | bare + Gauss vs Iceberg + Gauss | +0.2 | unresolved |
| 12 | 0.1 | 1 | cond | bare + Gauss vs Iceberg | +1.6 | bare + Gauss better: rms 0.0010 vs 0.0151 |
| 12 | 0.1 | 1 | cond | bare + Gauss vs Iceberg + Gauss | -0.5 | unresolved |
| 12 | 0.2 | 1 | raw | bare + Gauss vs Iceberg | +1.3 | bare + Gauss better: rms 0.0023 vs 0.0191 |
| 12 | 0.2 | 1 | raw | bare + Gauss vs Iceberg + Gauss | +3.1 | bare + Gauss better: rms 0.0023 vs 0.0033 |
| 12 | 0.2 | 1 | cond | bare + Gauss vs Iceberg | +1.5 | bare + Gauss better: rms 0.0020 vs 0.0217 |
| 12 | 0.2 | 1 | cond | bare + Gauss vs Iceberg + Gauss | -3.1 | Iceberg + Gauss better: rms 0.0000 vs 0.0020 |
| 12 | 0.3 | 1 | raw | bare + Gauss vs Iceberg | +2.1 | bare + Gauss better: rms 0.0061 vs 0.0259 |
| 12 | 0.3 | 1 | raw | bare + Gauss vs Iceberg + Gauss | +3.8 | bare + Gauss better: rms 0.0061 vs 0.0071 |
| 12 | 0.3 | 1 | cond | bare + Gauss vs Iceberg | +2.9 | bare + Gauss better: rms 0.0025 vs 0.0323 |
| 12 | 0.3 | 1 | cond | bare + Gauss vs Iceberg + Gauss | -2.4 | Iceberg + Gauss better: rms 0.0013 vs 0.0025 |
| 12 | 0.3 | 2 | raw | bare + Gauss vs Iceberg | +1.2 | bare + Gauss better: rms 0.0056 vs 0.0306 |
| 12 | 0.3 | 2 | raw | bare + Gauss vs Iceberg + Gauss | +1.5 | bare + Gauss better: rms 0.0056 vs 0.0063 |
| 12 | 0.3 | 2 | cond | bare + Gauss vs Iceberg | +1.5 | bare + Gauss better: rms 0.0025 vs 0.0374 |
| 12 | 0.3 | 2 | cond | bare + Gauss vs Iceberg + Gauss | -1.6 | Iceberg + Gauss better: rms 0.0012 vs 0.0025 |
| 12 | 0.3 | 3 | raw | bare + Gauss vs Iceberg | +1.5 | bare + Gauss better: rms 0.0059 vs 0.0344 |
| 12 | 0.3 | 3 | raw | bare + Gauss vs Iceberg + Gauss | +2.0 | bare + Gauss better: rms 0.0059 vs 0.0071 |
| 12 | 0.3 | 3 | cond | bare + Gauss vs Iceberg | +1.9 | bare + Gauss better: rms 0.0019 vs 0.0405 |
| 12 | 0.3 | 3 | cond | bare + Gauss vs Iceberg + Gauss | -2.0 | Iceberg + Gauss better: rms <noise vs 0.0019 |
| 12 | 0.5 | 1 | raw | bare + Gauss vs Iceberg | -1.3 | Iceberg better: rms 0.0177 vs 0.0227 |
| 12 | 0.5 | 1 | raw | bare + Gauss vs Iceberg + Gauss | +3.6 | bare + Gauss better: rms 0.0227 vs 0.0243 |
| 12 | 0.5 | 1 | cond | bare + Gauss vs Iceberg | +5.4 | bare + Gauss better: rms 0.0035 vs 0.0418 |
| 12 | 0.5 | 1 | cond | bare + Gauss vs Iceberg + Gauss | -2.8 | Iceberg + Gauss better: rms 0.0015 vs 0.0035 |
| 12 | 0.5 | 3 | raw | bare + Gauss vs Iceberg | +0.2 | unresolved |
| 12 | 0.5 | 3 | raw | bare + Gauss vs Iceberg + Gauss | +1.3 | bare + Gauss better: rms 0.0230 vs 0.0236 |
| 12 | 0.5 | 3 | cond | bare + Gauss vs Iceberg | +3.2 | bare + Gauss better: rms 0.0024 vs 0.0488 |
| 12 | 0.5 | 3 | cond | bare + Gauss vs Iceberg + Gauss | -1.4 | Iceberg + Gauss better: rms 0.0016 vs 0.0024 |
| 18 | 0.1 | 3 | raw | bare + Gauss vs Iceberg | - | no estimate |
| 18 | 0.1 | 3 | raw | bare + Gauss vs Iceberg + Gauss | - | no estimate |
| 18 | 0.1 | 3 | cond | bare + Gauss vs Iceberg | - | no estimate |
| 18 | 0.1 | 3 | cond | bare + Gauss vs Iceberg + Gauss | - | no estimate |
| 18 | 0.3 | 1 | raw | bare + Gauss vs Iceberg | - | no estimate |
| 18 | 0.3 | 1 | raw | bare + Gauss vs Iceberg + Gauss | - | no estimate |
| 18 | 0.3 | 1 | cond | bare + Gauss vs Iceberg | - | no estimate |
| 18 | 0.3 | 1 | cond | bare + Gauss vs Iceberg + Gauss | - | no estimate |
| 20 | 0.3 | 1 | raw | bare + Gauss vs Iceberg | - | no estimate |
| 20 | 0.3 | 1 | raw | bare + Gauss vs Iceberg + Gauss | - | no estimate |
| 20 | 0.3 | 1 | cond | bare + Gauss vs Iceberg | - | no estimate |
| 20 | 0.3 | 1 | cond | bare + Gauss vs Iceberg + Gauss | - | no estimate |
| 20 | 0.5 | 3 | raw | bare + Gauss vs Iceberg | - | no estimate |
| 20 | 0.5 | 3 | raw | bare + Gauss vs Iceberg + Gauss | - | no estimate |
| 20 | 0.5 | 3 | cond | bare + Gauss vs Iceberg | - | no estimate |
| 20 | 0.5 | 3 | cond | bare + Gauss vs Iceberg + Gauss | - | no estimate |
<!-- v2-tables:end -->

### 4.1 Continuity: the published cell reproduces, on a different machine

The (N = 12, h = 0.3, λ = 1) cell was run on the home server (Python 3.14.4, x86-64 Linux), not on
the machine that produced `data/q3_noisy.txt` (Python 3.12, aarch64):

| mode | this study | published §9.2 |
|---|---|---|
| bare + Gauss | **0.0017 ± 0.0004 at ×1.43** | 0.0017 ± 0.0004 at ×1.43 |
| Iceberg | 0.0222 ± 0.0076 at ×3.03 | 0.019 ± 0.008 at ×3.1 |

[measured] The bare + Gauss row agrees to the printed digit and the Iceberg row to 0.4σ, from
independent trajectory draws on a different interpreter and architecture. The generalized numbers
below therefore measure the same quantity as the published cell, and the scoring path is not
platform-dependent.

### 4.2 The verdict holds across the field axis and the whole λ ladder

> **SUPERSEDED 2026-10-24 by §4.0** (DECIDED-8): the verdict column below subtracts residuals
> against different reference curves (review/18 F1). The rows are kept as the record of the §9.2
> convention and are still checked by `scripts/check_q3_doc_table_42.py`.

Early-window residual of the flippable density, with the shot-cost factor; N = 12, encoded window
survival-matched per λ (48 / 28 / 19 steps at λ = 1 / 2 / 3)
[measured; classical prediction under the assumed model]:

| h | λ | bare + Gauss | Iceberg | Iceberg + Gauss | verdict |
|---|---|---|---|---|---|
| 0.1 | 1 | 0.0010 ± 0.0007 ×1.35 | 0.0139 ± 0.0060 ×2.89 | 0.0012 ± 0.0013 ×3.06 | bare + Gauss by 0.0129 |
| 0.2 | 1 | 0.0015 ± 0.0005 ×1.40 | 0.0159 ± 0.0080 ×3.06 | 0.0007 ± 0.0013 ×3.28 | bare + Gauss by 0.0143 |
| 0.3 | 1 | 0.0017 ± 0.0004 ×1.43 | 0.0222 ± 0.0076 ×3.03 | 0.0011 ± 0.0008 ×3.42 | bare + Gauss by 0.0205 |
| 0.3 | 2 | 0.0018 ± 0.0005 ×1.45 | 0.0291 ± 0.0118 ×3.03 | 0.0012 ± 0.0014 ×3.51 | bare + Gauss by 0.0273 |
| 0.3 | 3 | 0.0015 ± 0.0007 ×1.41 | 0.0288 ± 0.0090 ×3.17 | 0.0005 ± 0.0019 ×3.62 | bare + Gauss by 0.0273 |
| 0.5 | 1 | 0.0026 ± 0.0004 ×1.66 | 0.0152 ± 0.0047 ×2.82 | 0.0009 ± 0.0006 ×3.57 | bare + Gauss by 0.0126 |
| 0.5 | 3 | 0.0018 ± 0.0004 ×1.58 | 0.0224 ± 0.0111 ×3.70 | 0.0012 ± 0.0012 ×4.58 | bare + Gauss by 0.0206 |

**Readings.**

1. **The §9.2 verdict is not an accident of one field or one noise strength.** In all seven cells
   bare + Gauss is better than Iceberg by 0.013–0.027, every gap larger than the combined SE, at
   roughly half the shot cost (×1.35–1.66 against ×2.8–3.7).
2. **bare + Gauss is remarkably flat**: 0.0010–0.0026 over a fivefold change in field and a
   threefold change in noise, with the cost creeping up only mildly (×1.35 → ×1.66 as h grows,
   because the Gauss acceptance falls with the field). The mitigation that wins is also the one
   that is insensitive to where in the grid it is applied.
3. **Iceberg degrades with λ while bare + Gauss does not** (0.0222 → 0.0291 → 0.0288 against
   0.0017 → 0.0018 → 0.0015 at h = 0.3). **Caveat that matters:** the λ > 1 cells run shorter
   survival-matched windows (28 and 19 steps against 48), and shorter windows are the *easier*
   ones — residuals grow with time. The λ degradation is therefore measured against a handicap in
   its own favour and is, if anything, understated; it is not a clean pure-noise comparison, and a
   matched-window λ comparison would need encoded survival the code does not have at the prior.
4. **"Cheap" needs qualifying: the late-window shot cost of Gauss post-selection scales steeply
   with the window.** Late-window bare + Gauss, same cells [measured]:

   | h | λ | window (steps) | residual | shot cost (mean / final) |
   |---|---|---|---|---|
   | 0.1 | 1 | 480 | 0.0156 ± 0.0010 | **×37.0** / ×54.8 |
   | 0.2 | 1 | 240 | 0.0116 ± 0.0012 | ×9.3 / ×17.3 |
   | 0.3 | 1 | 160 | 0.0109 ± 0.0012 | ×5.3 / ×8.9 |
   | 0.5 | 1 | 96 | 0.0073 ± 0.0008 | ×3.1 / ×4.0 |
   | 0.3 | 2 | 160 | 0.0141 ± 0.0013 | ×15.7 / ×29.4 |
   | 0.3 | 3 | 160 | 0.0159 ± 0.0010 | ×33.9 / ×53.1 |

   The Gauss acceptance is the weight remaining in the defect-free sector, which decays roughly
   exponentially in (steps × N × λ) [derived], and the physics window is `qdm_times / h`, so the
   weak-field cells pay for their long windows: ×37 at h = 0.1 against the ×5.3 of the published
   h = 0.3 cell (consistent with its reported ×4.8). Amplified noise does the same at fixed window
   (×5.3 → ×33.9 from λ = 1 to 3). **The §9.2 recommendation therefore holds on accuracy
   everywhere measured, but its "cheap" half is an early-window, moderate-field, λ = 1 statement:
   in the late window at weak field or amplified noise, Gauss post-selection costs ×12–37 shots,
   more than Iceberg's early-window ×2.8–3.7.** Neither arm is cheap there; what differs is that
   Gauss still delivers a usable residual while Iceberg has no reach at all (§3.2).
5. **Iceberg + Gauss sits at the statistical floor in six of the seven cells** (residual 0.0005 to
   0.0012 against SE 0.0006 to 0.0019, reported `resolved=False`): it is not resolved as better
   than Gauss alone while costing ×3.1–4.6 the shots. This reproduces the published cell's reading
   at every point of the grid rather than at one.

### 4.3 Independent cross-check: measured survival vs Stim first-order accounting

The trajectory Monte Carlo and the Stim stage share a noise model but not a code path (gate-by-gate
state-vector simulation with sampled faults, against first-order Pauli-fault propagation). Measured
Iceberg detector survival at the end of each cell's own window, against
`exp(-(prep offset + detect rate × steps))` from `data/q3_scaling.txt`
[measured; binomial SE ≈ 0.014 at 300 trajectories]:

| cell | window | measured | Stim predicted | deviation |
|---|---|---|---|---|
| h = 0.1, λ = 1 | 48 | 0.0566 | 0.0692 | −0.9σ |
| h = 0.2, λ = 1 | 48 | 0.0500 | 0.0692 | −1.4σ |
| h = 0.3, λ = 1 | 48 | 0.0699 | 0.0692 | +0.05σ |
| h = 0.5, λ = 1 | 48 | 0.0699 | 0.0692 | +0.05σ |
| h = 0.3, λ = 2 | 28 | 0.0633 | 0.0553 | +0.6σ |
| h = 0.3, λ = 3 | 19 | 0.0633 | 0.0558 | +0.5σ |
| h = 0.5, λ = 3 | 19 | 0.0533 | 0.0558 | −0.2σ |

**Every cell agrees within 1.4σ, with no systematic sign**, which is what makes the λ ladder
credible: the amplified cells' shorter windows were chosen from the Stim prediction, and the
trajectories then land on that prediction independently. It also confirms the h-independence the
Stim stage asserts (Pauli rotations act as identity, so survival depends on the window, not the
field): the λ = 1 spread 0.050–0.070 across a fivefold field change is consistent with binomial
noise about a constant, and the surviving-trajectory counts are the integers 15, 17, 21, 21.

### 4.4 Size axis (N = 18, 20)

> **2026-10-24.** Under the pre-declared rules of DECIDED-10 none of the four size cells has an
> encoded estimate: their effective sample at the window end is 1-6, below the floor of 10
> (§4.0). Rows in the legacy §9.2 convention are **deliberately not published** for them.
> Their re-runs, 20 independently seeded shards each with a budget solved in advance
> (config.Q3ScalingConfig.rerun), are running. The paragraph below is the original placeholder,
> kept as the record.

**PENDING.** Four cells — (18, 0.3, 1), (18, 0.1, 3), (20, 0.3, 1), (20, 0.5, 3) — are running at
the time of writing (22- and 24-physical-qubit state vectors, at 2^(N+4) per trajectory-step). The
size axis is the one axis on which §9.2's conclusion could plausibly turn, because the encoded
reach shrinks with N (§3.2) while the Gauss acceptance does not, so no size statement is made here
until those cells land.

## 5. HQC cost of the study's cells [offline estimate; nothing submitted, no HQC spent]

Full table: `data/q3_hqc.txt`, from `scripts/run_q3_hqc.py`. The circuits are the same programs the
sweep simulates (`src/h2_q3`), compiled at TKET level 0 against the **offline** backend, counted by
`native_counts` and priced Rz-free per `DECISIONS.md` D-HQC (the free H2-1SC quotes equalled the
Rz-free estimate to the cent). **No job was submitted, no login was used, and every HQC-spending
run would still need the project lead's per-run approval.** 500 shots per circuit [assumed].

### 5.1 The study as a whole does not fit on H2

| what | HQC at 500 shots |
|---|---|
| bare arm over its full physics windows, 11 cells | **106,922** |
| Iceberg arm over its survival-matched windows, 11 cells | 48,242 |
| both arms | **155,164** |
| for scale: the whole allowance | 50,000 (39,853 already planned, `docs/h2_budget.md`) |

[derived from measured gate counts] The generalization study is **3.1× the entire allowance**, and
the bare arm alone is 2.1×. The cost is driven by window length: one bare circuit at h = 0.1 costs
18,450 HQC at N = 12 and **27,672** at N = 18, because the physics window is `qdm_times / h` =
480 steps. **This study is classical by necessity, not by preference** — the axes it varies are
exactly the ones that make an H2 version unaffordable, and no subset of it was ever a hardware
candidate at these windows.

### 5.2 Like-for-like, Iceberg costs ≈3× the HQC *before* its shot cost

Pricing the bare circuit over the **encoded** window (the only matched comparison; otherwise the
encoded arm looks cheap merely for stopping early) [measured gate counts]:

| N | window | bare @ encoded window | Iceberg | ratio |
|---|---|---|---|---|
| 12 | 48 steps | 1,861 | 5,698 | **×3.06** |
| 18 | 36 steps | 2,097 | 6,204 | ×2.96 |
| 20 | 33 steps | 2,138 | 6,286 | ×2.94 |

That ratio is **gates only, at equal shots**. The measured shot-cost factors of §4.2 then multiply
it: bare + Gauss needs ×1.35–1.66 the shots, Iceberg ×2.8–3.7. For equal statistics on the same
window, Iceberg therefore costs roughly **6× the total H2 resource of bare + Gauss while delivering
the worse residual** (§4.2) — the §9.2 verdict restated in the currency that actually constrains a
hardware run. (The matched-window bare price is field-independent: h changes rotation angles, not
gate counts.)

### 5.3 What would fit

The one affordable validation is a **single N = 12 matched-window pair** — the bare circuit and the
Iceberg circuit over the same 48-step window, 500 shots each: **≈7,559 HQC**, inside the ~10,147
unplanned remainder of the allowance [derived]. That buys a check of the encoded-vs-bare
*mechanism* at one point, not the generalization; the field, size and noise axes stay classical.
**This is a costing, not a proposal:** it is the project lead's decision whether any of it runs,
and `nexus` remains a stub.

### 5.4 Classical cost, and how to re-run this without wasting a night

Not a physics result, but the thing most likely to waste someone's time next
[measured 2026-10-23; profile and timings in `handoff/RESUME.md`].

The expensive stage's cost is **per trajectory and scales as 2^(physical qubits)**: one 4-step
Iceberg trajectory took 4.3 s at N = 12 (16 physical) and 282.5 s at N = 18 (22 physical) — a
factor 65 for 64× the amplitudes. Fixed setup is negligible (0.2 s and 7 s). A cProfile run puts
**~68 % of the time in `numpy.tensordot` reached from the gate appliers**, with 245,354 `reshape`
calls accounting for 344 s of it: each gate does `moveaxis` → `reshape` → `tensordot`, and the
non-contiguous reshape copies the whole state (~67 MB at 22 qubits) about three times per gate, so
one Trotter step moves tens of GB. A further ~24 % is the observable evaluation, which scales as
(1 + `n_batches`) × `n_records`.

Two consequences, both acted on here:

1. **Run heavy cells serially, one per host, with `OMP_NUM_THREADS=1`.** Four concurrent cells on
   one laptop ran ~28× slower per cell than the published single-cell baseline implies, because
   they saturated one memory bus (and each spawned BLAS threads onto elementwise work). Free memory
   went from 0.6 GB to 6 GB the moment they were stopped. The N = 20 cells were relaunched serially
   at reduced trajectory counts (60 bare / 24 Iceberg, 6 batches, `record_every` 6), so **their SE
   is roughly √2 larger than the N = 12 cells' — stated with their numbers rather than averaged
   away**.
2. **An in-place, reshape-free gate application is the obvious optimisation** and is deliberately
   **not** attempted here: `src/backends_qc.py` is load-bearing for the whole encoded pipeline, so
   changing it needs the transparency and Stim cross-checks re-run, and that is a separate decision.

### 5.5 Still owed
The free H2-1SC **server quotes**, which would replace these offline numbers at zero HQC and have
previously matched them to the cent. They need a `NEXUS_REFRESH_TOKEN`, which is not present on the
machine this study ran on.
