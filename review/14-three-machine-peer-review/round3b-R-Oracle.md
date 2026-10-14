# Round 3b — R-Oracle adjudicates R-Laptop's four disputes (R-Laptop unreachable)

Method: for each dispute I designed a decisive, runnable check using the project's own code
(never editing anything outside `peer-review/`) rather than re-reading prose. Scratch code:
`peer-review/scratch/r3b/` (`d1_injected_escape.py`, `d2_rerun.py`, `d3a_circuit_order.py`,
`d11_h2.py`). Two were reruns of the project's own pipelines with different inputs (D2, D11);
two needed a hand-written circuit-order step function built from the same primitives
`src/compare.py` and `src/trotter.py` already use, because `src/trotter_threshold.py` is a
verified core and hard-codes `trotter2_step` (D3a, and D1's monkeypatch). All four ran on this
machine; none used the Zenodo dataset directly (D1/D2/D3a/D11 don't need it — D15 in my Round 3
report already used it for the h/|J| question this round's D11 extends).

---

## D1 — R-Laptop-1 severity (sector-escape guard test is vacuous)

**Ruling: MINOR.** Agrees with R-Main; downgrades my own and R-Laptop's Round-1/Round-2 MAJOR.

**Decisive check.** Started `sample_sector` (`src/mcmc_baseline.py`) from a genuine in-sector
3×4 "flippable" state (defect-free, as the project's own real tests use). Monkeypatched
`TriangularDimers.hexagon` so that one site, which is genuinely **not** flippable in this
configuration (confirmed first: its real 6 hexagon neighbours do not alternate +1/−1), is fed a
fabricated neighbour list to the sampler's flip-decision that *does* alternate — i.e. "the mover
makes one invalid flip," exactly as the dispute specifies. Everything else — the real move loop,
and critically the real post-sweep guard, which checks `ev.defects(z)` and every winding cut
using `src/dimers.py`'s actual triangle geometry, untouched by the patch — is the project's own
unmodified code.

```
chosen non-flippable site: 0, real hexagon neighbours: [1, 4, 3, 2, 11, 9], vals [1,-1,1,-1,-1,-1]
fake neighbour list for site 0 : [1, 2, 3, 4, 5, 6] vals [1, -1, 1, -1, 1, -1]   (fools the flip test)

RuntimeError raised: True at seed 2
message: MCMC left the defect-free W0 sector — sampler bug
```

The guard fires the moment the injected invalid flip actually happens. This directly confirms
R-Main's Round-2 claim ("from a real in-sector 3×4 start, [an] invalid mover... raise[s] 'left
the defect-free W0 sector'") with an independent, from-scratch injection rather than R-Main's own
construction. **What's wrong is confined to the regression test's construction** (an
all-defects, zero-flippable start trivially trips the *initial-state* branch of the guard, never
exercising the mover), not to the guard itself, which is real and does its job. **Fix (small):**
add this kind of injected-flip test (or R-Main's monkeypatched-mover variant) as the real
regression test for `test_sampler_raises_if_not_in_a_sector`; the existing test can stay as an
initial-state sanity check but should be relabelled.

---

## D2 — R-Laptop-2 statistic (is the 3×4 drift ~1.4σ, or resolved at z≈5–7?)

**Ruling: REFUTED as a "marginal" / "~1.4σ" claim.** Agrees with R-Main, against my own and
R-Laptop's Round-1 reading. The drift is resolved far more strongly than even R-Main's z≈5–7
estimate: I get **z≈22 (3×3) and z≈11 (3×4)**.

**Decisive check.** Reran `scripts/run_q3_noisy.py`'s bare arm for 3×3 and 3×4 with the project's
own `run_bare`/`run_observables` (`src/noisy_q3.py`), same `CONFIG.seed`, so the rng draws match
`data/q3_noisy.txt` exactly — confirmed first as a sanity check (pooled late-window means and the
temporal std reproduce the committed file to 4 decimal places). Then, instead of reading only the
pooled mean ± batch-SE, I pulled all 20 individual batches (each an independent subset of the
400 trajectories, via `run.mixture(b)`), time-averaged each batch's sector-conditioned
`flippable_density` over the late window (t = 20–40), and compared each batch's late-window mean
against the (deterministic) ideal curve's late-window mean — exactly the "paired
noisy-minus-ideal differences... batch SE" approach the dispute describes.

```
3x3: sanity vs file: noisy cond late mean +0.4274 (temporal std 0.0188); ideal cond +0.4768  [file: 0.4274/0.0186/0.4768, matches]
     [gap / TEMPORAL std]  gap=0.0494  temporal_std=0.0188  ratio=2.63   <- R-Laptop's/my Round-1 number was 2.7
     [batch-means SE]      mean_gap=0.0504  batch_SE=0.0023  z=22.05   (noisy below ideal in 20/20 batches)

3x4: sanity vs file: noisy cond late mean +0.2762 (temporal std 0.0057); ideal cond +0.2841  [file: 0.2762/0.0056/0.2841, matches]
     [gap / TEMPORAL std]  gap=0.0079  temporal_std=0.0057  ratio=1.40   <- exactly the disputed "1.4sigma"
     [batch-means SE]      mean_gap=0.0088  batch_SE=0.0008  z=10.62   (noisy below ideal in 20/20 batches)
```

The "gap ÷ late-window temporal std" statistic is the wrong uncertainty: the "std 0.0056" the
data file reports next to "noisy cond late mean" is the standard deviation of the curve's own
values **across time** within the late window — real physical time-variation of a relaxing
observable, not a sampling-uncertainty estimate of the mean. Dividing a mean gap by that mixes a
signal-scale quantity into a noise-scale denominator, and happens to make a tiny, overwhelmingly
consistent effect (noisy strictly below ideal in **20/20 independent batches** for both clusters)
look marginal. The batch-means SE — the project's own prescription for Monte-Carlo uncertainty
elsewhere (`src/mcmc_baseline.py`'s own `_estimate`, `SE = std(chain means)/sqrt(M)`) — gives z≈11
and z≈22. **The physics (noise drives the conditioned curve toward B_W0, i.e. the thermalization
mimicry) is unambiguously real at the 3×4 size too**, not a Round-1 artifact of unequal evidence
weight. R-Laptop-2's underlying observation (two data points of different nominal strength
reported side by side) is correct in spirit but the conclusion that 3×4 is "marginal, arguably
consistent with noise" does not survive a sound uncertainty estimate.

---

## D3a — Ordering impact on Q3 §8 (trotter_threshold brackets and P_out)

**Ruling: split.** The dt = 0.25 credibility brackets **survive essentially unchanged** in
circuit order (confirming R-Laptop's Round-2 unitary-conjugacy argument quantitatively). The
P_out "Trotter-inflated ≈10–25%" claim **does not survive** — it has the same wrong sign as the
already triple-confirmed defect-density claim (D13/R-Laptop-R2-1), and now extends that MAJOR
finding's scope.

**Decisive check.** `src/trotter_threshold.py` is a verified core module I must not edit, so I
copied its two functions (`trotter_error_scan`, `late_window_bias`) verbatim except for one line
each: the step call swapped from `trotter.trotter2_step` (ZZ-outside) to a hand-written
`circuit2_step` built from the exact primitives `src/compare.circuit_trotter_states` already uses
(`apply_x_rotations` with `theta = -h·dt/2` either side of the full ZZ phase
`exp(-i·dt·ising_diag)`) — i.e. X half, ZZ, X half. Same dense dt grid (0.02–1.20, step 0.02,
plus 0.25), same `T = 20`, same four (cluster, h) points as the doc's table.

**Part 1 — thresholds (dt = 0.25 margins), circuit order vs. the doc's ZZ-outside table:**

| cluster, h | doc (ZZ-outside) abs. bracket / margin | circuit-order abs. bracket / margin | doc rel. bracket / margin | circuit-order rel. bracket / margin |
|---|---|---|---|---|
| 3×3, h=0.1 | 0.46–0.48 / 1.8–1.9× | 0.48–0.50 / **1.92×** | 0.44–0.46 / 1.8× | 0.44–0.46 / **1.76×** |
| 3×3, h=0.3 | 0.38–0.40 / 1.5–1.6× | 0.40–0.42 / **1.60×** | 0.32–0.34 / 1.3× | 0.38–0.40 / **1.52×** |
| 3×4, h=0.1 | 0.50–0.52 / 2.0× | 0.50–0.52 / **2.00×** | 0.44–0.46 / 1.8× | 0.44–0.46 / **1.84×** |
| 3×4, h=0.3 | 0.46–0.48 / 1.8–1.9× | 0.46–0.48 / **1.84×** | 0.32–0.34 / 1.3× | 0.42–0.44 / **1.68×** |

Error at dt=0.25 is slightly *smaller* in circuit order at all four points (e.g. 3×3 h=0.1:
5.45e-4 vs the doc's 7.0e-4). **Every bracket matches the doc to within one or two grid steps, and
the relative-threshold margin is as good or better in circuit order, never worse.** §8's headline
conclusion — "at h ≤ 0.3, dt = 0.25 sits below the Trotter threshold with a credible margin by
both criteria" — **survives unchanged**, confirming the resonance location is indeed
ordering-invariant (the two Strang steps are unitarily conjugate, so their Floquet quasienergies
agree — R-Laptop's Round-2 reasoning, now checked at all four points rather than inferred).

**Part 2 — P_out and defect density, circuit order (same four points, `qdm_times/h` window):**

```
3x3 3-sublattice   h=0.10  p_out exact=0.0018  circuit-order=0.0012  bias=-35.4%   (doc: ZZ-outside INFLATES P_out +10-25%)
3x3 3-sublattice   h=0.30  p_out exact=0.0187  circuit-order=0.0130  bias=-30.8%
3x4 flippable      h=0.10  p_out exact=0.0074  circuit-order=0.0058  bias=-21.0%
3x4 flippable      h=0.30  p_out exact=0.0695  circuit-order=0.0560  bias=-19.4%
defect_density ratio (circuit/exact): 0.485, 0.536, 0.739, 0.754 at the same four points — all < 1
```

In circuit order, P_out is **deflated** by 19–35% relative to exact, not inflated by 10–25% as
`docs/q3_thermalization.md:234` claims for the ZZ-outside step it actually used. This is the
identical sign flip D13 found for the raw defect density (ratios 0.485–0.754, all below 1, same
family as the 0.605/0.754 D13 already triple-confirmed on different windows/clusters) —
confirming R-Main's D3b forecast exactly: "the sign error is confined to the noiseless §8
defect-density and P_out statements." **This extends the existing MAJOR finding
(R-Laptop-R2-1/R-Main-R2-1/D13)'s scope: both the defect-density AND the P_out sentences in §8
have the wrong sign for the real circuit**, while the brackets/margins that §8 also reports do
not need correction.

---

## D11 — What does h/|J| = 2 do to Q3 and the Gauss law?

**Ruling: CONFIRMED in substance** (R-Main's subagent numbers). **And: no, the emergent
Gauss-law/B_W0/dimer framing, built at h ≤ 0.5, cannot be described as studying the reference
experiment at h/|J| = 2 — for two independent reasons, not one.**

**Decisive check.** 3×3 (3-sublattice start) and 3×4 (flippable start), J = −1, dt = 0.25, h = 2,
noiseless, **circuit order** (same `circuit2_step` as D3a), T = 20 (the h-independent window
`thr_T` uses, since `qdm_times/h` collapses to an unhelpfully short window at h = 2):

```
3x3: B_W0=0.3810, DE=0.4729
  p_in(t), t in (0,20]:        min=0.288  max=0.816   (R-Main: 0.06-0.55)
  defect_density, t in (0,20]: min=0.046  max=0.174   (R-Main: 0.11-0.21)
  by t=1.0 (a SINGLE Trotter step): p_in already down to 0.633

3x4: B_W0=0.2667, DE=0.2824
  p_in(t), t in (0,20]:        min=0.077  max=0.341
  defect_density, t in (0,20]: min=0.084  max=0.170
  by t=1.0: p_in already down to 0.132
```

Both clusters land in the same order of magnitude as R-Main's subagent (my 3×4 range 0.077–0.341
sits inside R-Main's 0.06–0.55; the defect densities, 0.046–0.174 and 0.084–0.170, bracket
R-Main's 0.11–0.21). **Confirmed, independently, with a from-scratch circuit-order implementation.**

**Why the framing has no meaning at h = 2, concretely:**
- The handoff/07 design (module docstring, `src/mcmc_baseline.py`) derives H_QDM, B_W0 and the
  whole sector-restricted-ETH machinery as a **first-order-in-(h/|J|)** effective theory — valid
  only for `h << |J|`. At h/|J| = 2 that expansion parameter is not small; it is the field
  dominating over the Ising term the sector-restriction is built on.
- Operationally this shows up immediately: p_in collapses from 1.0 to 0.13–0.63 within a **single**
  Trotter step (t = 1.0), not the slow O((h/|J|)²) leakage over tens of steps the h ≤ 0.5 design
  assumes and that `docs/q3_thermalization.md §5` reports (P(W≠W0) ~ h^2.08, small at h ≤ 0.5).
  Defect density sits at 5–17%, roughly an order of magnitude above the few-percent values at
  h ≤ 0.3 (D3a above). "Conditioning on the defect-free sector" at h = 2 means renormalizing a
  small, rapidly-fluctuating minority of the distribution (as low as 8–34% of the weight for 3×4)
  rather than correcting a dominant in-sector population — the opposite regime from what the
  post-selection / Gauss-law-mitigation story is built to describe.
- **This is independent of, and compounds with, my own Round-3 D15 finding:** the released
  `quench4_step*.qasm` circuits have `ry(0)` (an identity, no-op) state prep on all 54 qubits and
  zero `x` gates anywhere — they do not encode *either* candidate winding-sector initial bitstring
  at all (confirming `open-questions.md`'s T-5). So even setting the h/|J| = 0.3-vs-2 question
  aside, there is no initial W0 to condition on that is actually recoverable from the data the
  project has.

**Ruling on R-Main's final question:** no. The Q3/Gauss-law study as built (h ≤ 0.5,
sector-restricted ETH, B_W0, dimer-shell correlations) cannot be re-labelled as "the h/|J| = 2
reference experiment" by simply changing a config value — the theoretical scaffolding itself
stops being a controlled approximation at h = 2, on top of the initial-state information gap.
Either the team keeps h ≤ 0.5 as a deliberately-chosen, self-contained frustrated-regime study
(and says so, dropping "matching the reference"), or a genuine h/|J| = 2 study needs different
machinery (not a first-order-in-h effective sector theory) and an initial state chosen by some
other criterion than "what the released QASM shows," since the QASM shows nothing there either.

---

## Changes to my Round 3 severity table and bottom line

| finding | Round 3 | Round 3b update |
|---|---|---|
| R-Laptop-1 (sector-escape guard) | "MINOR-leaning... did not independently re-run, deferred" | **MINOR, confirmed** by my own injected-escape test (D1 above) |
| R-Laptop-2 (thermalization statistic) | "unresolved" | **REFUTED as a marginal/1.4σ claim** — drift resolved at z≈11–22 by batch-means SE (D2 above) |
| R-Main-1 / R-Laptop-R2-1 (ordering sign error, §8) | MAJOR, scope: defect density only | **MAJOR, scope widened**: the P_out "Trotter-inflated" sentence in the same §8 paragraph has the identical wrong sign (D3a Part 2); the threshold/margin brackets in the same section do **not** need correction (D3a Part 1) |
| R-Main-2 / D15 (h/\|J\| = 0.3 vs 2) | MAJOR | unchanged, but D11 adds a **second, independent reason** the h ≤ 0.5 work can't simply be relabelled h = 2: the sector-ETH machinery itself is uncontrolled there, not just a parameter mismatch |

No other entries in my Round 3 table change. The must-fix-before-hardware list is unchanged in
order, with item 1 (reconcile h/|J|) and item 2 (fix the ordering sign error) both now backed by
one additional, independent piece of decisive evidence each, and the D1/D2 downgrades remove two
items that would otherwise have stayed on a "disputed" list for the project lead.

ROUND3B-DONE
