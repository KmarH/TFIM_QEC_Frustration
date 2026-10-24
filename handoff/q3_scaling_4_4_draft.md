# DRAFT — docs/q3_scaling.md 4.3/4.4 size-axis text (NOT published)

**Why this is a draft.** The project lead decided (RESUME.md, 2026-10-23 17:40): *4.4 is drafted
now, published only when all four size-axis cells are in.* Three are in; **(20, 0.5, 3) is still
running**. `docs/q3_scaling.md` 4.3/4.4 are therefore left exactly as they were, and this file holds
the text ready to paste once the fourth cell lands and its row is added.

It supersedes the earlier one-row draft (`.../ab444dc3-.../scratchpad/q3_scaling_4_4_draft.md`):
this one carries all three landed cells, and every number in it was verified against
`data/q3_sweep.txt` by `check_doc_44.py` (9 triples + the verdict, window and physical-qubit
columns per cell, **0 mismatches**, 2026-10-23 20:02).

## Rows to add to 4.3's survival cross-check table

The table's header note becomes
`[measured; binomial SE ~ 0.014 at 300 trajectories, 0.024 at 100, 0.068 at 24]. N = 12 unless the
row says otherwise:` and these rows are appended:

| h = 0.5, λ = 3 | 19 | 0.0533 | 0.0558 | −0.2σ |
| **N = 18**, h = 0.3, λ = 1 | 36 | 0.0599 (6/100) | 0.0533 | +0.3σ |
| **N = 18**, h = 0.1, λ = 3 | 13 | 0.0499 (5/100) | 0.0545 | −0.2σ |
| **N = 20**, h = 0.3, λ = 1 | 33 | 0.1248 (3/24) | 0.0511 | +1.1σ |

and this paragraph follows the existing closing paragraph:

The three size-axis cells agree within **1.1σ** on the same accounting at 22 and 24 physical
qubits, which is the cross-check that matters most for them: their windows were set from the Stim
prediction at a size where no published survival number exists. The N = 20 cell's survival rests
on **3 surviving trajectories of 24** (SE 0.068), so it constrains the prediction only loosely and
is reported as a consistency check, not a measurement of the rate.


## 4.4 as drafted

### 4.4 Size axis (N = 18, 20): the verdict survives, but its margin does not

Three of the four size-axis cells have landed; **(20, 0.5, 3) is still running** at the time of
writing and no statement is made about it. Early-window residuals, same metric as §4.2
[measured; classical prediction under the ASSUMED prior, not an H2 result]:

| cell | phys | window | bare + Gauss | Iceberg | Iceberg + Gauss | verdict |
|---|---|---|---|---|---|---|
| N = 18, h = 0.3, λ = 1 | 22 | 36 | 0.0032 ± 0.0005 ×1.41 | 0.0241 ± 0.0144 ×2.80 | 0.0012 ± 0.0019 ×3.04 | bare + Gauss better by 0.0209 |
| N = 20, h = 0.3, λ = 1 | 24 | 33 | 0.0006 ± 0.0005 ×1.42 | 0.0066 ± 0.0046 ×2.63 | 0.0020 ± 0.0013 ×2.85 | bare + Gauss better by 0.0060 |
| N = 18, h = 0.1, λ = 3 | 22 | 13 | 0.0185 ± 0.0030 ×1.24 | 0.0163 ± 0.0079 ×3.11 | 0.0024 ± 0.0022 ×3.25 | **unresolved (within combined SE)** |

**1. At the published field and noise scale, size does not overturn §9.2.** At h = 0.3, λ = 1 the
bare + Gauss arm beats Iceberg at N = 18 and N = 20 as it does at N = 12, with the same shape of
cost: ×1.4 shots against ×2.6–2.8. Across the three sizes the gap is 0.0205, 0.0209, 0.0060.

**2. The N = 20 numbers are not a precision measurement and must not be read as one.** That cell
ran at **reduced counts** (60 bare / 24 Iceberg trajectories, 6 batches, `record_every` 6) under the
approved budget option, and its early window holds **6–7 points against 25 at N = 12**. Both arms'
residuals are smaller there than at N = 12, which reflects a shorter, easier window and coarser
sampling rather than a method that improves with size. Its survival also came out at 3/24 = 0.125
against the 0.051 the window was matched to, i.e. the window it actually measured was easier than
intended. Treat the row as a consistency check.

**3. The extreme corner is the first cell in the whole study where bare + Gauss does not win.** At
(18, 0.1, 3) the two arms are a statistical tie: the gap is 0.0022 against a combined SE of 0.0085
[derived]. Two things drive it, and both are structural rather than statistical:

- bare + Gauss's residual there is **0.0185**, about ten times its value in every N = 12 cell
  (0.0010–0.0026). Post-selection is no longer cleaning the curve.
- the bare window at h = 0.1 is **480 steps carrying 47.69 faults per shot** at λ = 3
  (§3.3) — so almost nothing survives the constraint. The late-window shot cost in that cell is
  **×303.9**, against ×37.0 at (12, 0.1, 1) and ×3.1 at (12, 0.5, 1).

**So the honest size statement is conditional.** Gauss-law post-selection of the bare circuit beats
Iceberg wherever the bare circuit's fault load per shot stays modest, and that condition weakens
with every axis pushed at once: larger N, smaller field (longer window) and larger λ all raise
faults per shot, and at the corner where all three are unfavourable the advantage is gone. This is
a boundary of the §9.2 result, not a contradiction of it — and it is a boundary the single published
cell could not have revealed.

**4. Iceberg + Gauss remains at the statistical floor** in the two N = 18 cells and barely above it
at N = 20 (0.0020 ± 0.0013): combining the two mechanisms buys no resolvable accuracy at any size
tested, while paying both costs (×2.9–3.3).



---

# FOURTH CELL LANDED 2026-10-23 23:09:54, exit 0, 20,302 s — AND IT IS NOT A MEASUREMENT

**DO NOT PUBLISH THIS ROW.** The rows below were generated from `data/q3_sweep.txt` +
`data/q3_scaling.txt` by `scratchpad/gen_rows.py` (self-tested 6/6 against the three published
rows), so they are faithful transcriptions. The *cell* is the problem, not the transcription.

Machine-generated rows, for the record:

| **N = 20**, h = 0.5, λ = 3 | 12 | 0.0416 (1/24) | 0.0510 | -0.2σ |

| N = 20, h = 0.5, λ = 3 | 24 | 12 | 0.0008 ± 0.0005 ×1.59 | 0.0000 ± 0.0000 ×3.28 | 0.0000 ± 0.0000 ×3.44 | **Iceberg better by 0.0008** |

**Why it cannot be published [measured, this session, from the cell JSON directly]:**

- the encoded arm rests on **ONE surviving trajectory of 24** (detector survival 0.0416 at the
  12-step window; `ice["acceptance"] = [0.749, 0.125, 0.0416]`);
- its early window holds **3 time points** (t = 0, 1.5, 3.0) against 25 at N = 12;
- `Iceberg` residual = **1.01e-07**, SE = **3.28e-17**; `Iceberg + Gauss` residual = **5.78e-09**,
  SE = 1.13e-17. The encoded curve reproduces the **ideal** curve to 7-8 digits
  (|diff| = 1.5e-07, 7.6e-08, 8.0e-08 on `flippable_density` vs the ideal raw curve);
- the mechanism: at 4 % survival the detector-accepted ensemble is essentially the **fault-free
  trajectory**, and because the simulator computes the readout distribution **exactly** (no shot
  sampling - review/18 **F5**), a fault-free trajectory *is* the ideal curve. So the residual
  collapses to floating-point noise and `resolved=True` passes on ~1e-17;
- the last point's batch SE is `None` (NaN) in the JSON, and the runner logged
  `RuntimeWarning: Degrees of freedom <= 0 for slice` - the batch variance is degenerate
  (6 batches, ~1 surviving trajectory), which is review/18 **F9** realised for the first time:
  before this cell it was latent with 0 occurrences in 10 cells.

**So this cell is a measured demonstration of the metric defect the reviewers predicted**, not
evidence about Iceberg. Published as a verdict row it would read as the study's first "Iceberg
wins" - produced by one trajectory and an exactly-computed readout. It belongs in the write-up as
a **boundary-of-the-metric** result: the §9.2 score rewards aggressive post-selection with a
perfect residual at vanishing acceptance, because it carries no shot-noise term. On hardware the
same cell would be dominated by sampling error at 4 % acceptance, which this metric does not model.

**Consequence for the (20, 0.5, 3) corner:** the cell tells us the encoded window at
N = 20, h = 0.5, λ = 3 is too short and the trajectory count too low to measure anything. Getting a
real number there needs far more trajectories (so that the accepted ensemble is not a single path)
or a shot-noise-aware metric - the project lead's call, and it is a re-cut, not a re-run.
