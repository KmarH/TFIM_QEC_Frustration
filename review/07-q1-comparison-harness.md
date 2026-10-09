# Review 07 — Q1 comparison harness (logical-vs-physical vs Haghshenas et al., arXiv:2503.20870)

**Reviewer:** qc-reviewer (independent). **Milestone:** SCOPE Q1 — quantitative square-lattice
comparison with error bars. **Artifacts:** `src/compare.py`, `src/observables.py`,
`scripts/run_compare.py`, `data/q1_compare.txt`, `tests/test_compare.py`,
`tests/fixtures/zenodo_mini/`, `config.py` (CompareConfig), supporting `docs/q1_compare.md`.
**Environment used:** `.venv/bin/python` (3.12), real dataset present at
`/home/opc/zenodo_18487089/zenodo_data` (used for independent checks).
This review wrote no project code; all independent checks were run from `/tmp`.

---

## Verdict: **ACCEPT**

The harness is correct on every load-bearing claim I could independently reproduce, honest
about the N=56-vs-ceiling mismatch, reproducible (not hardcoded), and the stated Q1 conclusion
does **not** overclaim. The one previously-worrying item (does it present a finite-size result
as a fidelity number?) is explicitly and repeatedly disclaimed in both the output and
`docs/q1_compare.md`. No critical or major defects found. A short list of minor nits and
optional improvements follows; none block acceptance.

I am recording this as ACCEPT rather than accept-with-fixes because every required-verify item
in `handoff/03` passed under independent re-execution, and the remaining items are nits or
scope-limited open questions already flagged by the authors themselves.

---

## What I independently ran

All of the following were executed by me (not read from comments):

1. **Full suite:** `.venv/bin/python -m pytest -q` → **122 passed**;
   `-q tests/test_compare.py` → **28 passed**. (~18 s / ~8 s.)
2. **Observable brute-force** (`/tmp/rev_check.py`): dense `(Σ Z_i)²/N²` operator vs
   `total_z_sq_normalized` on random complex states, N=2..5.
3. **Gauge/sign mapping** (`/tmp/rev_check.py`): my own literal gate-level replay of the
   *published* QASM semantics (`rzz(0.5)=e^{-i0.25 ZZ}`, `rx(0.5)`, `ry(θ)` prep) vs
   `simulate_z2` at `(J,h)=(+1,+2)`.
4. **Geometry** (`/tmp/rev_check.py`): extracted the real `quench1/2_step1.qasm` bond sets and
   compared to `square_bonds(7,8,·)` under row-major and under `x*Ly+y`, and under open BC.
5. **Spec fidelity on the real data** (`/tmp/rev_spec.py`): step vectors, Z2/ZZnn/fft/
   decayrates/dimercorrs shapes and the `[r,step]` orientation straight from the dataset.
6. **No-hardcoding / reproducibility**: re-ran `scripts/run_compare.py` on the real dataset to
   a temp file and `diff`ed against committed `data/q1_compare.txt` (minus the timestamp line).
7. **Trust-gate behaviour**: ran the harness on (a) the synthetic fixture and (b) a real-README-
   but-no-circuits copy, checking whether `data/q1_compare.txt` was written.
8. **Ceiling refusal timing/allocation** (`/tmp/rev_ceiling.py`): timed the N=56 refusal and
   watched peak RSS; verified `pair_average_from_z2` against its closed form.

---

## VERIFIED CORRECT

**[C-class claims, all pass]**

- **Observable = normalized second moment, not connected variance.**
  `src/observables.py:total_z_sq_normalized` (lines ~119–131) returns `<(ΣZ)²>/N²` with **no
  mean subtraction**. Independent dense-operator check: diff ≤ 5.6e-17 for N=2..5. The sibling
  `magnetization_variance_z` (connected) is left intact and is *not* used by the harness.
  `test_z2_is_second_moment_not_connected_variance` pins the distinction (all-up: Z2=1,
  variance=0). **Verified.**

- **Sign/gauge mapping (the load-bearing physics claim).** My from-scratch replay of the
  published QASM gate semantics on a 3×3 torus equals `simulate_z2(...,J=+1,h=+2,...)` to
  **≤ 8.7e-15** for both θ=+π/6 and θ=−10°. This confirms, independently of the repo's own
  test, that `H_circ=+J ZZ + h X` with `rzz(0.5)/rx(0.5)` run under the README identity
  `(J,h,θ)→(−J,−h,θ)` gives *identical* Z2 to running `(J,h)=(+1,+2)` at the same θ.
  `src/compare.py:circuit_trotter_states` (the half-X / ZZ-phase / half-X Strang order with
  `half_x = -h·dt/2`) is the right implementation; the repo's own
  `test_harness_reproduces_literal_qasm_gates` additionally pins both gauge identities and
  shows the non-gauge pairing `(J,−h,θ)` differs by >0.05. **Verified.** Note the authors
  correctly did **not** reuse `src/trotter.py` (ZZ-outside splitting), which gives a different
  Z2 at this coarse `h·dt=0.5` (0.63 vs 0.78 on 4×4 step1) — a real second-order-splitting
  distinction, documented in `docs/q1_compare.md`.

- **Geometry settled from the executed circuits, not assumed.** Real `quench1_step1.qasm` and
  `quench2_step1.qasm` each have **112 distinct rzz pairs = 2N for 7×8**, and the bond set
  equals `square_bonds(7,8,"periodic")` under row-major `q=y·Lx+x` (`True`), and is **not**
  equal under `q=x·Ly+y` (`False`) nor open-BC row-major (`False`). The run script
  (`scripts/run_compare.py:verify_circuits`, ~lines 74–82) re-derives and logs exactly this on
  every run, and aborts (`SystemExit`) on an angle/θ mismatch. **Verified against the real
  circuits.** This upgrades research/05 §4's `[inferred]` boundary/map to `[established]`.

- **Spec fidelity.** From the real dataset: step-vector lengths `[12,20,10,8]`, quench1 steps
  non-uniform `[1..8,10,12,16,20]` (loader keys off `quenchN_steps.txt`, never 20 — enforced by
  the `(M,)` shape check in `ZenodoData.load` and `test_steps_are_nonuniform_and_never_assumed_20`);
  Z2 shape `(12,)`+err `(12,)`; ZZnn `(10,14)`; ZZnn_fft `(10,8)`; decayrates `(4,)`;
  **dimercorrs `(4,8)=[r,step]`, equal to the raw file with no transposition**
  (`test_dimercorrs_are_r_by_step`). The `_err` siblings load with identical shape and are
  shape-checked (regression `test_transposed_error_file_is_rejected`). **Verified.**

- **Honesty / SCOPE §3,§12.**
  - (a) Over-ceiling refusal is real and *pre-allocation*: `check_ceiling` is called at the top
    of `ry_product_state` and `circuit_trotter_states`, and `compare_z2` checks every requested
    size up front. N=56 refusal returns in **0.03 ms** with peak RSS unchanged (~495 MB, the
    bare numpy import) — no 2^56 allocation attempted. (`test_over_ceiling_is_refused_before_allocation`,
    `test_compare_refuses_whole_run_if_any_size_over_ceiling`.) **Verified.**
  - (b) No same-system fidelity claim: the `CAVEAT` string, the per-run header, and
    `docs/q1_compare.md` all state this is a finite-size TREND comparison and give **no**
    logical-vs-physical number. **Verified.**
  - (c) Finite-size spread and a Trotter-vs-exact internal error are both reported per quench
    (`finite-size spread …` and `internal check … max|Z2_Trotter-circuit − Z2_exact-H|`).
    **Verified.**
  - (d) **Not hardcoded.** Re-running the harness on the real dataset reproduces
    `data/q1_compare.txt` byte-for-byte except the timestamp (`diff` → IDENTICAL). The numbers
    are computed from the loaded `.txt` files. **Verified.**
  - (e) `data/` is written only for a *trusted* source — positive check `not synthetic and
    isfile(README) and verify_circuits(...)==True for every quench`. I confirmed: synthetic
    fixture → **not written**, every line tagged `[SYNTHETIC FIXTURE]`; real-README-but-no-
    circuits dir → **not written** (`verify_circuits` returns `False`). **Verified.**

- **Supporting correctness:** `nn_energy_density_x` matches a direct per-bond `expval_zz` sum
  for open and periodic BC (`test_nn_energy_density_matches_per_bond_sum`); `pair_average_from_z2`
  = `(N·Z2−1)/(N−1)` is algebraically the mean off-diagonal `<Z_iZ_j>` (I re-derived it from
  `<(ΣZ)²>=N+Σ_{i≠j}<Z_iZ_j>`) and matches on the all-aligned (→1) and uncorrelated (Z2=1/N→0)
  limits; yielded states are copies, not aliased (`test_yielded_states_are_not_aliased`); the
  QASM parser fails loudly on malformed lines (`test_qasm_parser_fails_loudly`).

**Tests are not vacuous.** They exercise the actual claims: a dense-operator cross-check for the
observable, a *scipy-matrix-exponential* gate replay for the sign mapping (independent of the
code path under test), real shape/orientation checks, a deliberately-malformed fixture file for
the shape guard, and genuine `MemoryCeilingError` assertions. Every C-class correctness claim
has a backing test.

---

## COULD NOT VERIFY / OUT OF SCOPE THIS PASS

- **Whether the dataset `_err` is a 1σ bootstrap stderr or a CI half-width.** The README does
  not say; the harness marks it `[unverified]` in the output and in `docs`. I did not read the
  paper SI. This matters if a χ²/σ agreement score is ever computed (it is not, here). **Correctly
  flagged, not a defect.**
- **The `nn_energy_density_x` "no extra 1/Ly" reading of E(x).** `[inferred]` by the authors;
  only used by the not-yet-built quench3/Q3 path. I did not compare against the real quench3
  magnitudes. Already tracked as open item m5. Not in the Q1 critical path.
- **Absolute `dt`,`|J|` separately.** Only the products `J·dt=0.25`, `h·dt=0.5` are fixed by the
  gates; the `t|J|` axis uses the `|J|=1` convention. Stated. Fine for dimensionless curves.
- **decayrates[0] (q=0) value.** research/05 asserted `Γ_{q=0}=0`; the real file's first entry
  is 0.0175, not 0.0. This is a dataset fact, lives in the quench3 family, is **not** used by
  the Q1 harness, and does not affect this milestone — but it contradicts a research/05
  `[established]` note and should be reconciled before the Q3 pass. (Flagged for the Q3
  reviewer, not against this harness.)

---

## DEFECTS

None at C or M severity.

### Minor / nits (m)

- **m1 — `verify_circuits` short-circuit ordering.** `scripts/run_compare.py` line ~128:
  `trusted = verify_circuits(args.data, q, theta, log) and trusted`. Because Python evaluates
  the left operand first, `verify_circuits` always runs (good), but if a later quench's circuits
  are missing while an earlier one verified, `trusted` correctly degrades to `False`. This is
  the intended behaviour, but the mixed-operand ordering (`call() and trusted`) is easy to
  misread; consider `trusted = trusted and verify_circuits(...)` for clarity. No functional bug
  — the write gate is conjunctive over all quenches, which I confirmed empirically.

- **m2 — `BrokenPipeError` on truncated stdout.** When stdout is closed early (e.g. piped to
  `head`), `log()`'s `print(..., flush=True)` raises `BrokenPipeError` and the script exits
  non-zero. This is cosmetic (full runs and the `data/` write path are unaffected; I confirmed a
  complete run exits 0), but wrapping the final flush or ignoring `SIGPIPE` would make the CLI
  friendlier. Not a correctness issue.

- **m3 — Re-running on the real dataset silently rewrites `data/q1_compare.txt`.** This is by
  design (trusted source) and the content is identical, but there is no "unchanged, skipping"
  guard; a future accidental run with a different `CompareConfig` would overwrite the committed
  artifact without a diff prompt. Low risk given the config is the single source of truth.

- **m4 — `_err` filename is `[inferred]`.** `_err_name` tries `<stem>_err_<mode>.txt` then
  `<stem>_<mode>_err.txt`. On the real data the first form exists (confirmed), so this is fine,
  but the ordering assumption is documented only in a comment. The regression test
  `test_missing_error_file_is_an_error_not_nan` covers the raise path. Acceptable.

- **m5 — E(x) periodic-side-of-2 double-count.** Documented in the docstring; does not affect
  the 14×4 data lattice. Carried as a known limitation, not a defect.

---

## Scientific reading of `data/q1_compare.txt` (is the Q1 conclusion defensible?)

**Yes — because the harness explicitly declines to draw the overclaiming conclusion.**

The numbers I confirmed: quench1 reduced-lattice Z2 sits at 0.70–0.78 while H2 `zne+znr` falls
0.737→0.562 and `raw_unamplified` falls to 0.390; quench2 reduced lattice oscillates 0.22–0.65
with a **finite-size spread of 0.331** and a **Trotter-circuit-vs-exact-H gap of 0.298**. These
two numbers are the same order as, or larger than, the entire H2 signal. Any sim-vs-data
"agreement" statement for quench2 would be meaningless, and the harness says exactly that:
*"This reduced-lattice comparison cannot separate residual device noise from finite-size
effects … not evidence of agreement or disagreement … gives no logical-vs-physical number."*

I agree with the reviewer-relevant judgement in the task brief: the **usable Q1 signal is the
physical-side `zne+znr`-vs-`raw_unamplified` gap** (e.g. quench1 step20: 0.562±0.039 mitigated
vs 0.390±0.015 raw — a clear, several-σ mitigation effect), **not** sim-vs-data agreement. The
harness surfaces both physical-side columns side-by-side, which supports that reading, and
`docs/q1_compare.md` frames the only genuine same-system quantitative check as the (not-yet-done)
step-1 light-cone cluster calculation. The output does **not** overclaim. The milestone correctly
establishes the *plumbing* (loader, conventions, geometry, parameters, honest caveats) that a
real logical-vs-physical answer will later sit on top of; it does not pretend to be that answer.

One caveat the authors should keep visible: the current deliverable answers *none* of Q1's
substantive "what changes with logical qubits" question — there is no logical/encoded-side
simulation yet (noted in `docs` "Not done"). That is correct scoping, but Q1's SCOPE §2
"done" condition (a quantitative logical-vs-physical comparison with error bars) is **not met by
this harness alone**; it is a prerequisite built honestly. The verdict ACCEPT is for the harness
as specified in `handoff/03`, not a sign-off that Q1 is answered.

---

## Required fixes

None.

## Recommended (optional) improvements

1. Reconcile the real decayrates[0]=0.0175 against research/05's `Γ_{q=0}=0` `[established]`
   note **before** the Q3 pass (dataset-note correction, not a harness change).
2. Resolve the `_err` 1σ-vs-CI ambiguity from the paper SI before any quantitative χ²/σ scoring.
3. Confirm the E(x) `1/Ly` reading against one real quench3 magnitude before building Q3.
4. Cosmetic: tidy the `verify_circuits` short-circuit ordering (m1) and suppress the stdout
   `BrokenPipeError` (m2); add an "unchanged, not rewritten" guard on the `data/` write (m3).
5. Pursue the step-1 light-cone exact-N=56 cluster value — it would convert the earliest step
   from a trend point into a genuine same-system quantitative check, as the authors note.

---

**Open items (for the project log):** logical/encoded-side simulation still owed for Q1 §2;
decayrates q=0 reconciliation; `_err` statistical meaning; E(x) normalization; optional light-
cone exact step-1 check. None block this milestone.
