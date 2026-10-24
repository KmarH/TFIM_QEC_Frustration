# review/18 — Q3 generalization machinery, blind code-half peer review (2026-10-23)

**Scope.** The code committed in `b022a17`: `src/q3_scaling.py`, `src/noise_scaling.run_iceberg_scaled`
/ `run_bare_scaled`, `src/noisy_q3.py`'s additive `apply_u` hook, `src/noisy_q3_sweep.score_cell`,
`scripts/run_q3_sweep.py`'s merge path, and the four frozen spec tests read as specifications.
**Deliberately excluded:** `docs/q3_scaling.md` §4.3/§4.4, which were mid-publication.

**Method.** Two Opus reviewers, blind and in parallel, each given only the artifact paths, the claim
in one sentence, the KB paths and `CLAUDE.md` — never the author's reasoning, the expected verdict,
or each other's output. Reviewer A (theory) wrote its own derivation of the correct accounting
*before* reading any scoring code. Reviewer B (code) wrote an independent re-scoring in pure stdlib,
with its own interpolation, and compared against `data/q3_sweep.txt`. Both were barred from the full
suite, from 16-qubit-and-larger work and from Selene, because a 24-qubit cell held the box.

**Verdicts: A major, B major.** Neither reviewer modified any repository file.

## Findings that stand (raised independently by both reviewers)

| # | severity | location | finding | status |
|---|---|---|---|---|
| F1 | **major** | `src/noisy_q3_sweep.py:160,218,234`; `scripts/run_q3_sweep.py:214-236` | The headline `residual` scores each mode against **its own** target (raw for bare-raw and Iceberg, conditioned for the Gauss modes). The section-3 verdict then *subtracts* across that diagonal, so the "better by" gap mixes estimator error with the `ref_cond - ref_raw` offset (approx. 0.005-0.007 per section 9.2). A calls the symmetric object 4 modes x 2 references = 8 cells, of which `residual` + `residual_vs_raw` fill only 6: **bare-raw-vs-cond and Iceberg-raw-vs-cond are never computed**, so "is Iceberg more accurate than bare+Gauss" has no common-estimand answer. | **CONFIRMED** [measured, this session] |
| F2 | **major** | `src/noisy_q3_sweep.py:212` vs `:233` | The bare mask carries a window term (`t_bare <= t_ice[-1]`); the encoded mask is `isfinite(v) & (acc>0)` with **no window term**. An explicit `early_t` therefore bounds only the bare arm while both rows stay labelled `window="early"`. [measured] N=12 h0.3 lam3: bare 10 points to t=4.50, Iceberg 11 to t=4.75; N=18 h0.1 lam3: 4 vs 5. `tests/test_q3_score_cell.py:104` only ever exercises a *wider* `early_t`, so it cannot catch this. | **CONFIRMED** |
| F3 | **major** | three-way, see resolution below | lambda is not one knob. The simulator, the Stim rate table and the pytket circuit each amplify a **different** set of 2q gates. | **CONFIRMED, direction resolved here** |
| F4 | minor | `src/noisy_q3_sweep.py:224` | `cost = 1/mean(acc)`, but the shots needed to hold a target error at *every* window point scale as `mean(1/acc)`, and `1/mean(a) <= mean(1/a)` (Jensen). With survival falling exponentially the headline multiplier understates: B's example `acceptance [1, 0.01]` gives `mean(1/a) = 50.5` against a reported 1.98; section 9.2's own "x3.1 mean" vs "x12 at t=12" is the same effect. `cost_final` partly mitigates and is reported alongside. | **CONFIRMED** |

## F3 resolution — the reviewers disagreed on direction, so this session verified it

B read the encoded runner as over-amplifying (196 locations against the 124 named by
`_NAMED_SCOPES["2q"]`, x1.58). A read it as correct. **A is right** [verified, this session,
`src/noisy_q3.py:103-107`]: the intrinsic fault is charged at **every** two-qubit command —

    if len(qs) == 2:
        f = _fault_2q(rng, noise)

— with no gate-class filter. So in the simulator the 2q channel lives at every 2q location, and
"scale the 2q error by lambda" correctly means inserting at every one of them.
`run_iceberg_scaled` (`src/noise_scaling.py:315-324`) matches the model it amplifies. B's location
count was right; its assignment of which side is wrong was not.

**The real defect is three coexisting lambda scopes** [verified, this session]:

| where | scope | what it governs |
|---|---|---|
| `src/noisy_q3.py:103` + `run_*_scaled` | **every 2q gate** | the trajectory simulation — the source of every published number |
| `src/q3_scaling.py:58` `_NAMED_SCOPES["2q"]` | `("rot-zz","syn-cx")` — excludes `rot-cx` | the Stim rate table, hence the **survival-matched encoded windows** |
| `src/noise_scaling.insert_paulis:88-100`; `config.py:449 fold_scope` | **ZZPhase / `rot-zz` only** | the **pytket circuit** that is compiled, HQC-costed and would be submitted |

The third row is the one that bites hardest: **the circuit we would actually send to H2 is amplified
on a narrower scope than the simulation that predicts its behaviour**, so a lambda-ladder comparison
between this project's classical prediction and an emulator run would not be comparing the same
ladder. Nothing has been submitted, so nothing is spent on it — but it must be fixed before any
lambda point goes to the emulator.

A also measured the arm asymmetry [measured, A, `stim_rate_table`, N=12, scope "2q"]: at nominal
lambda = 3 the effective factors are **2.875** on the bare fault rate, **2.702** on the Iceberg
*detect* (cost) rate and **3.000** on the Iceberg *undetected* (accuracy) rate — the encoded arm's
accuracy and cost scale by different factors and the two arms sit about 6 % apart. The label
"lambda = 3" is nominal. **Not re-measured by anyone:** a Stim rate for `rot-cx` alone.

## Single-reviewer findings carried forward

| # | from | severity | location | finding |
|---|---|---|---|---|
| F5 | A7 | **major, structural** | `src/noisy_q3.py:130`; `src/noisy_q3_sweep.py` | `se` is the batch spread over Pauli **trajectories**, with the readout distribution computed exactly (a linear map, no sampling). It therefore carries **no shot noise and no 1/sqrt(acceptance) inflation**. So `resolved` tests the residual against a *simulation-effort* floor while `cost` is denominated in *hardware shots*: the two cannot be combined into "resolved at this shot cost", and no field carries the per-accepted-shot variance the cost comparison needs. Affects the meaning of every `resolved` flag in section 4. |
| F6 | A11 | **major, citation** | `src/noise_scaling.py:11` | The KB (`research/07-noise-scaling.md`) supports Pauli insertion only before the 2q **rotations** (2503.20870 S1.4), and its PEA row records that such a model "is valid only when combined with random Pauli twirls". `run_iceberg_scaled` extends it to syndrome CX with the rotation-learned channel in an **untwirled** trajectory simulation, so the tag `[derived; the 2503.20870 method]` over-claims KB support on the encoded arm. `hqc_cost`, the folding citation (2005.10921) and `prior_noise()` all check out term for term. |
| F7 | A5 | minor | `src/noise_scaling.py:319` vs `src/noisy_q3.py:104-107` | The inserted Pauli lands **before** the gate, the intrinsic fault **after**. Exact for ZZPhase (depolarizing is unitarily covariant; ZZ commutes with the rotation) but **not** for CX: `CX (Z x Z) CX = I x Z`, so the eta-biased excess weight arrives as a weight-1 Z in a *different* Iceberg detection class than the channel it is meant to scale. Compounds with F6. |
| F8 | A2 | major, **latent** | `src/noisy_q3_sweep.py:112-114` | Nothing enforces `n_ice <= n_bare`. `n_bare = (qdm_times/h)/dt` shrinks with h while `n_ice` defaults to 48, so at h above about 1 the encoded residual would cover times the bare arm never reaches. **Not triggered**: this sweep has h <= 0.5. |
| F9 | B4, A9 | minor, **latent** | `src/noisy_q3_sweep.py:217,233` | Points with zero acceptance or NaN batch SE are dropped, so a mode whose acceptance collapses mid-window is scored only where it survived and can post a *smaller* residual than a mode scored on the full window; a NaN SE also biases `resolved` toward True. **0 occurrences across the 10 landed cells** [measured, B], so latent. Only `n_points` exposes it. |
| F10 | A8 | minor, **inherited** | `src/noisy_q3_sweep.py:223` | The error on a window-*averaged* residual is taken as mean(per-point SE), but per-time points share batches and are strongly correlated; the right statistic is the batch spread of the per-batch window-averaged residual, which `score_cell` cannot form from the `(value, SE)` pair it is handed. This is section 9.2's stated convention, so it is inherited, not introduced here. |
| F11 | A10 | minor, **latent** | `src/q3_scaling.py:212-242` | `prefilter_grid` takes no `scope`, so `GridCell.keep`/`survival` are computed under scope `"all"` while the runners amplify 2q only (N=12, 48 steps: 0.0048/0.00033 "all" vs 0.0074/0.00079 "2q" at lambda=2/3). `scripts/run_q3_scaling.py:150-152` recomputes the verdict with the 2q scope, so the exposed `keep` is a trap, not a live error. |
| F13 | this session, 2026-10-24 | **major, provenance** | `runs/q3_sweep/cell_N20_*.json` `settings`; `scripts/run_q3_sweep.py:80-83,122-124`; `config.py:522` | **Both N = 20 cells ran at half the declared budget** (60 bare / 24 Iceberg / 6 batches against `config.py:526`'s 120 / 48 / 8) and **no cell file says so**. Cause [established, `handoff/RESUME.md:349-353`]: on 2026-10-23 07:00 four parallel cells contended for memory bandwidth and were restarted by a serial runner with CLI overrides (`--traj-bare 60 --traj-ice 24 --batches 6`), under the approved "reduced counts, honest error bars" option. The overrides beat `per_size` silently, `provenance` records only host/platform/python/timings, and the argv survives only in another session's temp scratchpad. `config.py:522`'s "Filled from the D5 probe" is untrue: the probe never produced output (`RESUME.md:293`). N = 12 and N = 18 cells match config exactly. Consequence: at survival 0.0416 the (20, 0.5, 3) encoded arm kept 1 trajectory (2 at the declared 48 [derived]) - neither is a measurement. Fix: provenance records argv, git hash, seed sequence and the source of each setting; a budget below config refuses without `--allow-reduced "<reason>"`; both N = 20 cells re-run at a pre-declared, acceptance-solved budget (DECIDED-10). |
| F12 | B6 | minor | `scripts/run_q3_sweep.py:252-263` | `data/q3_sweep.txt` section 4 is headed "Measured Iceberg survival **vs the Stim first-order prediction** [independent cross-check]" but the merge prints measured columns only. B did the comparison by hand and it passes (about 15 %); the file just does not contain it. |

## Checks that passed

[measured, B, independent re-scoring in pure stdlib with its own interpolation]
`cell_N12_h0.5_lam1.json` gave bare raw 0.0508 / SE 0.0030 / x1.00 / 25 pts, bare+Gauss 0.0026 /
0.0004 / x1.66, Iceberg 0.0152 / 0.0047 / x2.82, Iceberg+Gauss 0.0009 / 0.0006 / x3.57;
`cell_N18_h0.1_lam3.json` gave 0.0742 / 0.0185 / 0.0163 / 0.0024 with 4/4/5/5 points.
**Identical to `data/q3_sweep.txt` to 4 dp.** The merge path is verbatim JSON apart from section 3's
computed gap; NaN survives as a JSON `NaN` literal and prints as `"nan"`, never as a plausible
number.

[derived/measured, A] `surv * p_in` is the correct **joint** acceptance (`p_in` is computed on the
already-detector-accepted, renormalised mixture, `src/noisy_q3.py:467`, not as a marginal).
lambda = 1 is genuinely bitwise identical on both arms (`_draw` returns before touching the rng).
`_OneCommand` per-command dispatch is behaviourally identical to per-segment. Empty window to NaN
and single batch to `resolved=False` are both handled explicitly. Batch SE uses `ddof=1` over finite
batches only.

## Resolution

1. **Sections 4.3/4.4 publication is HELD** (`handoff/RESUME.md`, 22:45). F1 makes the verdict
   column's "better by" phrasing unsupported as written; F3 means the lambda > 1 cells — 5 of 11,
   including (18, 0.1, 3), the cell behind the "statistical tie" finding, and the running
   (20, 0.5, 3) — carry a scope caveat; F5 means every `resolved` flag means less than it appears
   to.
2. **Two decision cards go to the project lead** (F1's framing, F3's canonical scope). Both are
   physics/presentation calls, not bug fixes, so they are not this session's to make.
3. **F2, F4, F12 are fixable without a ruling** and get regression tests through `test-first` part A,
   in a **new** test file — the four frozen spec files are not touched.
4. **F6 is a doc correction** owed regardless: `src/noise_scaling.py:11`'s tag must stop claiming
   2503.20870 supports the untwirled encoded extension.
5. **F8, F9, F11 are latent**: not triggered by any landed cell. Guard tests, no renumbering of
   results.
6. Reviewer A was interrupted by an API session limit mid-derivation and resumed from its own
   transcript; its derivation (`scratchpad/revA/derivation.md`) was written before it read the
   scoring code, as its brief required.

**Nothing in this review is an H2 result.** Every number it touches is a classical prediction under
the ASSUMED `research/06` noise prior.
