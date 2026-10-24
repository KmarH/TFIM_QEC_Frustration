# 02 — Post-selected estimator: effective sample, error bar, shot cost, re-run budget

*Written 2026-10-24 for DECIDED-10, BEFORE any re-score or re-run. Sources: `research/08-postselected-estimators.md` (S-numbers below). Spec: `tests/test_q3_rescore.py`, `tests/test_q3_rerun_budget.py`. Code: `src/q3_rescore.py`. Everything here is accounting for a classical prediction under the ASSUMED research/06 noise model.*

## 1. The estimator the simulation actually forms [derived]

The trajectory runners (`src/noisy_q3.py`) give trajectory *i* a weight

- **bare arm:** w_i = 1;
- **Iceberg arm:** w_i ∈ [0, 1], the probability mass of its exact readout distribution that passes the readout-parity detectors, set to 0 for good once any mid-circuit detector fires.

Each surviving trajectory also contributes its exact readout distribution p_i. The pooled curve at a recorded step is the self-normalised (ratio) estimator

  Ô = Σ_i w_i O(p̂_i) / Σ_i w_i ,   p̂_i = p_i / w_i ,

where O is linear in the distribution: flippable, defect and memory densities. This is Owen's self-normalised importance-sampling estimator (S3 ch. 9; its delta-method variance is S3 eqs. 9.8–9.9). For 0/1 weights it is his acceptance–rejection ratio form ΣA_iY_i / ΣA_i (S3 §9.5, ratio formula 2.29).

The Gauss-law conditioning (`cond`) is applied to each trajectory's *exact* distribution, but it **re-weights** the trajectories. The conditioned curve is the ratio Σ_i w_i p_in,i c_i / Σ_i w_i p_in,i, where p_in,i is the trajectory's weight in the defect-free W0 sector. Its effective sample is therefore its own, (Σ w p_in)² / Σ (w p_in)², and it is smaller than the raw one when p_in varies between trajectories. *Corrected 2026-10-24 after blind review A (finding 2): an earlier draft said the conditioning adds no sampling noise.* The runners now accumulate Σ w p_in and Σ (w p_in)² per batch. Cells that predate this use the lower bound acceptance × p_in × n_traj (by the argument of §2). On hardware the conditioning also discards shots.

## 2. Effective sample size [established S3 eq. 9.13; derived bound]

The Kish effective sample size is ESS = (Σw)² / Σw² (S3 eq. 9.13; equal to n / (1 + cv²), S3 eq. 9.15, which is Kish's design effect, S2 → S1). The runner now accumulates Σw² per batch (`NoisyRun.w2sum`).

For w ∈ [0, 1] we have Σw² ≤ Σw, hence **ESS ≥ Σw**. So the surviving weight n_eff = acceptance × n_traj is a **lower bound** on ESS. For cells written before 2026-10-24, which carry no Σw², a floor applied to n_eff is conservative. Also ESS ≤ the number of trajectories with w > 0.

**The (20, 0.5, 3) artifact explained.** At the last point Σw = 0.0416 × 24 ≈ 1, so ESS ≈ 1. One trajectory with weight ~1 survives, and it is the fault-free one. Every batch that holds weight agrees with it to floating point. The batch-means SE is therefore ~1e-17 and says nothing. Owen calls this kind of failure "a bad variance estimate that masks the problem" (S3); see also S9 and S17 on error bars that come out too small. ESS ≥ 1 always, so ESS alone cannot flag uselessness (S4). A floor has to be **declared**.

## 3. The floor [assumed convention]

No fetched source gives a numeric ESS floor. Owen: where ESS "becomes alarmingly small is hard to specify … application specific" (S3). The only number found is the particle-filter resampling trigger N/2 (S5), which is a resampling rule, not a reporting threshold. We therefore fix by convention:

> A mode has an estimate only if ESS ≥ **10** at **every** point of its window and its value and acceptance are finite and positive there. Otherwise it has **no estimate**: its window is never shortened to where it survived.

The value 10 is a plain convention. Schmeiser's batch-count guidance (S10, §4) concerns the number of independent batches, not effective samples, so it **does not** support this number; it only suggests the same order of magnitude. The value is recorded as `config.Q3ScalingConfig.ess_floor` before any rescoring. The floor applies to every mode, with the Gauss-conditioned modes using their own ESS.

## 4. The error bar: delete-one-batch jackknife [established S8 eq. 52, S7, S10; derived]

Group the trajectories into B independent batches. Write N_b(t) = Σ_{i∈b} w_i O_i(t) and D_b(t) = Σ_{i∈b} w_i, so the pooled estimate is R(t) = ΣN_b / ΣD_b. The scored statistic is the window-averaged residual r = mean_t |R(t) − O_ref(t)|.

For each batch b form the replicate r_(−b) with batch b removed, from both the numerator and the denominator, **taking the window average inside the replicate**. Then

  SE_jk² = (B − 1)/B · Σ_b (r_(−b) − r̄)²      (S8 eq. 52, grouped bins allowed).

Properties:

- Because the window average sits inside each replicate, the correlation between time points of the same batch is carried through. This fixes review/18 F10, where the old SE was the mean of the per-point SEs.
- A batch with zero weight at some point is a legitimate group; deleting it leaves the ratio unchanged.
- Hand check (test R5): with four equal-weight batches at constant offsets δ_b, all positive, |·| is linear and SE_jk = std(δ, ddof = 1)/√4, the classical standard error of the mean.
- The SE is over **fault trajectories**. Readout is exact, so there is no shot noise. This is a different currency from the shot cost of §5 (review/18 F5).

**How many batches.** Schmeiser (S10): with fewer than 10 batches the effect on the confidence interval is large, and above 30 it is small. Wolff (S7, eq. 46): the error-of-error is ≈ √(2/B). We pre-declare **at least 10** (`min_batches`) and use **20** for re-runs (`rerun_shards`), which gives an error-of-error of ≈ 32 %. Cells that have no per-batch detail fall back to the legacy mean per-point SE and are flagged `lg`.

**Batch minimum.** A jackknife over fewer than `min_batches` (= 10) batches is no estimate. So is any window point where deleting a single batch leaves no weight at all, because one batch carries everything there. Batches that are empty at some point are legitimate groups of independent trajectories and stay in the jackknife.

**The verdict metric (blind review A, finding 1).** The mean |O − O_ref| has a noise floor. For O ~ N(μ, σ²), E|O − O_ref| → σ√(2/π) as μ → 0. The floor grows as the effective sample shrinks, so it ranks the noisier (encoded) arm worse even when both arms are exact. Verdicts are therefore called on the bias-corrected mean square

  msd = mean_t [ (R(t) − O_ref(t))² − V(t) ],

where V(t) is the per-point delete-one-batch jackknife variance of R(t). This is unbiased for mean_t (E R − O_ref)² to the order of the jackknife. Its SE is a jackknife over batches, with V recomputed inside each replicate. Legacy cells use V = se_t² and the independent-point approximation SE(msd) = √(Σ_t 4 e_t² se_t² + 2 se_t⁴)/T, flagged. rms = sign(msd) √|msd| is reported for readability. The mean |·| is still reported as a descriptive number continuous with §9.2. Regression test: `tests/test_q3_rescore_review.py`.

**The verdict convention.** A winner is called when |gap| > k · σ with k = 1, as ruled (DECIDED-8). Under the null, about 32 % of pairs cross 1σ by chance. With 4 pairs per cell and 11 cells, several such crossings are expected, so every verdict is printed with gap/σ next to it.

## 5. Shot cost [derived]

To hold a target error ε at every window point t with acceptance a_t, point t needs S_t ∝ σ_t²/(ε² a_t) shots, where σ_t² is the per-shot variance. If σ_t is the same at every point and each point is a separate circuit (as it is: one circuit per Trotter depth), this is S_t ∝ 1/(ε² a_t). The total over the window is therefore ∝ Σ_t 1/a_t, and **cost = mean_t(1/a_t)**. By Jensen, mean(1/a) ≥ 1/mean(a). The legacy figure 1/mean(a) is the multiplier under a different allocation, a fixed number of shots per point with the error left free, and it understates the first (review/18 F4: acceptance [1, 0.01] gives 50.5 against 1.98). The v2 table reports mean(1/a) plus 1/a at the last point.

## 6. The re-run budget [derived accounting]

With K = 20 shards, each one batch of each arm, the expected surviving weight at the window end is K · batch_ice · s_pred. Here s_pred is the Stim first-order survival at the cell's fixed window under the canonical λ scope. It is a **design-time** quantity, not a measured outcome.

Σw at the end is a sum of many small independent survivals, so it is close to Poisson. Budgeting for an expectation equal to the floor misses it with probability P(Pois(10) < 10) = 0.46. A margin m gives P(Pois(10m) < 10) = 0.07 for m = 1.5 and 0.005 for m = 2. We pre-declare m = 2:

  batch_ice = max(⌈m · floor / (K · s_pred)⌉, ⌈per_size traj_ice / K⌉),  batch_bare = ⌈per_size traj_bare / K⌉.

| cell | window | s_pred (every-2q scope) | batch × K | expected ESS at end |
|---|---|---|---|---|
| (18, 0.1, 3) | 13 | 0.0484 | 21 × 20 = 420 | 20.3 |
| (18, 0.3, 1) | 36 | 0.0534 | 19 × 20 = 380 | 20.3 |
| (20, 0.3, 1) | 33 | 0.0511 | 20 × 20 = 400 | 20.4 |
| (20, 0.5, 3) | 12 | 0.0446 | 23 × 20 = 460 | 20.5 |

**The re-run rule, uniform for every cell (blind review A, finding 4).** A cell whose realised ESS meets the floor keeps its data. A cell that misses the floor gets **exactly one** re-run, at the margin-2 budget above, and whatever that re-run gives is **final**, including "no estimate". There is no optional stopping and no second re-run. The four cells above are the ones that missed the floor on 2026-10-23 (ESS at the window end ≈ 1–5). The N = 12 cells met it (end ESS 15–21) and are not re-run; they are replayed at their original seed only to add per-batch detail. Their pre-registered expected end ESS of ≥ 15.5 would have missed with probability ≈ 0.055, so the exemption rests on their realised pass, which is exactly what the uniform rule says.

**Placement caveat (DECIDED-9).** The trajectory runner and the pytket circuit insert the λ excess **before** each 2q gate. Stim's first-order rate table, which sets s_pred and hence the budget, scales the intrinsic fault **after** the gate. For ZZPhase the two are identical. For CX the excess is conjugated by the gate (CX (Z⊗Z) CX = I⊗Z, review/18 F7), so s_pred is a first-order design estimate, not an exact prediction, and the budget margin absorbs the difference. The CX error channel is also *assumed* equal to the rotation-learned channel [assumed].

The N = 12 cells hold 300 trajectories in 20 batches with s_pred ≥ 0.0516, so their expected end-ESS is ≥ 15.5. They are not re-budgeted. They are replayed at their original seed only to gain per-batch detail, which must reproduce their existing numbers. Each cell's window stays exactly as it was run (`cell_windows`), so nothing moves after the fact.

**Cross-check of the λ-scope fix (DECIDED-9).** Under the canonical scope the Stim prediction at λ > 1 drops, e.g. (20, 0.5, 3) from 0.0510 to 0.0446 (measured 0.0416 on 24 trajectories). The measured survivals at the current trajectory counts do **not** discriminate between the two scopes: they scatter on both sides of both predictions, within about one binomial error bar everywhere (`data/q3_sweep.txt` §4, figure `q3_sweep_survival`). The fix rests on the location count, not on survival data: the one-step N = 12 program has 196 two-qubit locations, of which the old Stim scope covered 124. The 72 it missed are the rotation-gadget CX of the state preparation, which occur once; each Trotter step adds 60 ZZPhase + 32 syndrome CX [measured, review B]. So the fix changes Stim's survival offset (and with it the predictions and budgets), not its per-step rates.
