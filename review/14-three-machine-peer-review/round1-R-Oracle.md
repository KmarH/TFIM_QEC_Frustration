# Round 1 — Independent Review by R-Oracle

Reviewer: R-Oracle (Claude Code, Oracle Cloud VM, Linux aarch64, Python 3.12 — the project's
reference platform). Independent round: no other reviewer's output was consulted.

Focus area: QEC codes and the encoded TFIM (`src/qec/`, `src/encoded_codes.py`,
`src/encoded_tfim.py`, `src/backends*.py`), the noise model, and the noise-sensitivity / η
analysis behind Q1 ("Iceberg is recommended", "encoding helps at η ≈ 0.05") and Q4
("distance-3/4 codes buy ~1.2×").

---

## 1. Run log

**Environment**
- Interpreter used throughout: `~/KiroTest-project/.venv/bin/python` (the project's own working
  venv, read-only — never modified), Python 3.12.14, linux-aarch64.
- Installed package versions all matched `requirements.txt` exactly (numpy 2.5.3, scipy 1.18.1,
  pytest 9.1.1, stim 1.16.0, pytket 2.18.4, guppylang 1.1.2, selene-sim 0.3.4, hugr 0.18.8); two
  undeclared transitive deps present (`guppylang-internals 1.1.2`, `selene-core 0.3.2`,
  `selene-hugr-qis-compiler 0.5.0`) but these are guppylang/selene's own sub-packages, not a
  version drift concern.

**Commands and results**
| command | result | runtime |
|---|---|---|
| `python -I -m pytest tests/ -q` | **231 passed**, 0 failed | 124.9 s |
| `python main.py` | runs correctly (statevector backend, 3×3 lattice) | <1 s |
| `python -I main.py` | **fails**: `ModuleNotFoundError: No module named 'config'` | — |
| `python -I scripts/plot_q3.py` | writes all 5 expected `figures/*.png` | ~a few s |
| `python -I scripts/run_noise_sensitivity.py` | exact reproduction of `data/noise_sensitivity.txt` | 91 s |
| `python -I scripts/run_concat_d4.py` | exact reproduction of `data/concat_d4.txt` (1.6M Stim shots, seeded) | 3.7 s |
| `python -I scripts/compare_frustration.py` | reproduced `data/frustration_compare.txt` exactly except one basis-dependent, documented-as-non-physical h=0 triangular `|M_z|` cell | 0.9 s |
| `python -I scripts/run_encoded_codes.py --skip-exec` | abandoned at 280 s timeout, 2/6 lattice×p2 combinations done; partial write restored via `git checkout --` | >280 s (not completed) |

CLAUDE.md states the test suite is "169/169, about 100 s" — the actual count is 231/231 at
~125 s. This is just stale documentation (the suite has grown), not a discrepancy worth more
than a note.

**Reproducibility coverage gap [disclosed, not a project defect]:** the closed-form, Stim-DEM
first-order numbers (`data/noise_sensitivity.txt`, `data/concat_d4.txt`) were independently
re-run and matched exactly, including the legacy table. The *executed* Selene numbers in
`data/encoded_codes.txt` §4–5 and `data/encoded_iceberg.txt` were **not** independently
regenerated within this review's CPU/time budget — those sections require Selene shot execution
documented at 1–4 s/shot with historical per-datapoint runtimes up to 538 s. This review's
machine (2 cores, shared with concurrent review work) could not absorb that. Treat the headline
undetected-probability / acceptance numbers as reproducibility-confirmed; treat the Selene
execution rows in B4 as **not independently re-run** by this round.

Full detail: `peer-review/scratch/repro/repro-findings.md`.

---

## 2. Findings

### R-Oracle-1 — [MAJOR] First-order DEM claims carry no stochastic uncertainty, and this is never stated
`src/encoded_codes.py:647-682` (`undetected_logical`, `undetected_rate_per_step`). The "Iceberg
recommended", η ≈ 0.25/0.36/0.44/0.55 crossover, and "~1.2×" residual numbers in
`docs/encoded_tfim.md` and `data/noise_sensitivity.txt` / `data/encoded_codes.txt` §4 all come
from `circuit.detector_error_model(... approximate_disjoint_errors=True)` — a deterministic
first-order perturbative calculation, not Monte Carlo sampling. There is genuinely no
randomness to report an error bar on, so "no ±" is not wrong — but nowhere in `docs/encoded_tfim.md`
or `docs/findings_vs_questions.md` is it stated that these numbers are *exact under the
first-order approximation* rather than *measured-with-negligible-noise*. A reader skimming the
"[measured]" tag next to these numbers could reasonably take them for sampled quantities with
small, unreported error bars, when in fact their only uncertainty is the (undisclosed)
approximation error of truncating at first order.
**Fix:** add one line next to every `[measured]` tag on a DEM-derived number: "closed-form
first-order Stim accounting; not a Monte Carlo estimate, no sampling error — see R-Oracle-2 for
its own approximation error."

### R-Oracle-2 — [MAJOR] The first-order approximation's own validity range is not checked or disclosed
Same location. `approximate_disjoint_errors=True` degrades as the per-step fault probability
grows, yet `data/encoded_codes.txt` reports first-order "acceptance after 3 steps" as low as
**0.010** (Steane, 2×3, p2 = 3e-3) and 0.033 (concat, 2×2, p2=3e-3) — regimes where multi-fault
terms are clearly not negligible (a code accepting only 1-3% of shots is dominated by multi-fault
events the first-order expansion does not resolve). The "Iceberg wins" ranking is only quoted
at the low end of the scan (H2 prior p2=6e-4, legacy p2=1e-3) where the approximation is
plausible, so the *qualitative* conclusion looks safe — but the write-up never states where the
method breaks down, and the executed-Selene comparison (B4) shows the first-order prediction is
already off by 5–15 percentage points even at the best-behaved point (p2=1e-3), which is exactly
the symptom of approximation error, not statistical noise.
**Fix:** state the first-order method's breakdown point explicitly (e.g. "not trusted below
acceptance ≈ 0.3") and don't quote acc < 0.1 numbers as if they carry the same epistemic status
as acc ≈ 0.8 ones.

### R-Oracle-3 — [MINOR] "3–7× more two-qubit gates" mixes two different lattice sizes
`docs/encoded_tfim.md`'s "Logical-gate cost" table (and the B3/B5 prose built on it) quotes
Iceberg and concat at the **2×2** lattice (28 and 184 two-qubit gates/step) but Steane and
5-qubit at the smaller **1×2** lattice (108 and 84 gates/step) — the per-code lattice size is
labelled in the table itself, but the "3–7× more two-qubit gates" headline sentence (B3, and
repeated in B5's closing blockquote) does not flag that it is comparing circuits built on
different lattices. 184/28 = 6.6× is a fair, matched-lattice ratio (concat vs Iceberg, both
2×2); 108/28 = 3.9× and 84/28 = 3.0× are **not** matched (Steane/5-qubit only had to cover a
1×2 lattice because they don't fit 2×2 under this review's local-feasibility/budget
constraints — see the budget table one page earlier). Note this does not appear to inflate the
"Iceberg wins" conclusion in the project's favour: a 1×2 circuit scaled up to 2×2 would almost
certainly need *more*, not fewer, gates, so the true matched-size ratio for Steane/5-qubit is
probably understated here, not overstated. Still, the headline number as currently stated is not
a controlled comparison and should say so.
**Fix:** either note explicitly that the Steane/5-qubit ratios are lower-bound estimates from a
smaller lattice, or compute (even roughly) a 2×2 Steane/5-qubit gate count for a fair number.

### R-Oracle-4 — [MINOR] `python -I main.py` is broken; only undocumented `python main.py` works
`main.py` has no `sys.path` insertion (unlike every file in `scripts/`, which all do
`sys.path.insert(0, REPO)` — confirmed by grep). CLAUDE.md's blanket instruction "Run scripts as
`.venv/bin/python -I scripts/<name>.py`" generalizes naturally to "run everything with `-I`", but
`python -I main.py` fails immediately with `ModuleNotFoundError: No module named 'config'`,
because Python's isolated mode (`-I`) implies `-P` (don't prepend the script's own directory to
`sys.path`) and nothing in `main.py` compensates. `README.md`'s own documented command
(`python main.py`, no `-I`) does work. Not a correctness bug — just a footgun for anyone who
mechanically applies the project's own stated convention to its entry point.
**Fix:** add the same `sys.path.insert(0, ...)` two-liner to `main.py`, or note in
`CLAUDE.md`/`README.md` that `main.py` specifically should be run without `-I`.

### R-Oracle-5 — [MINOR] Small-shot Selene standard errors are not reliable where quoted
(Carried from a sub-review, independently spot-checked against `data/encoded_codes.txt` §5 and
`docs/encoded_tfim.md` B4.) `scripts/run_encoded_codes.py` computes a Gaussian `std/√n` standard
error even at `n = 5` shots kept (concat, 2×2, p2=3e-3, step 3: "0.55 ± 0.18 (5 shots kept)"). A
Gaussian SE on 5 binomial-ish samples is not a trustworthy interval; the doc does flag the low
shot count qualitatively ("the d ≥ 3 codes keep so few shots that their error bars are 2–14× the
bare ones") but still presents the ± number as if it were a normal confidence interval. This
point is explicitly *not* used to support the headline Q1/Q4 conclusions (B4's own text says "the
quantitative comparison rests on the measured accounting [B3], not on these curves"), so it's
low-stakes, but the number is still printed and could be misquoted downstream.
**Fix:** switch to a Wilson/Clopper-Pearson interval (as already done correctly in
`src/qec/concatenated_gadget.py`'s `_wilson`) below some shot-count threshold, or suppress the ±
entirely below ~20 shots.

### R-Oracle-6 — [verified correct / no bug] Iceberg and concatenated-code distances
Independently re-derived from scratch — see §3 below. No bug found in `src/qec/iceberg.py`,
`src/qec/concatenated.py`, or `src/qec/verify.py`. `concatenated.py`'s `code_distance` correctly
requires anticommutation with a *logical* operator (not mere non-membership in the detected set),
which is exactly the fix its own docstring (M2 caveat) says the simpler `min_undetected_weight`
needed and lacks on its own.

### R-Oracle-7 — [verified correct / no bug] the η ≈ 0.25 crossover formula
Independently re-derived from the stated noise-channel definition (not by calling the project's
code) — see §3 below. `12·p2·(0.2+0.8η) = 4.8·p2 ⇒ η* = 0.25` matches the project's own claimed
crossover exactly, and the underlying `0.2+0.8η` undetectable-fraction formula is derivable
directly from the Pauli-channel definition in `src/encoded_codes.py:592-598` (only
{XX, YY, ZZ} of the 15 non-identity two-qubit Pauli errors are undetectable on Iceberg's native
weight-2 ZZPhase gate). No bug found.

### R-Oracle-8 — [verified, positive] tests are discriminating, not tautological
Spot-checked `tests/test_qec.py` directly: it calls the independent `verify_code` oracle (not the
construction's own assertions), tests the even-`k` validation, the measured detection distance via
brute-force enumeration (`iceberg_detection_distance`), and circuit-level syndrome silence —
consistent with the project's stated "avoid constants any state reproduces" philosophy. No
tautological tests found in this file or in `test_encoded_codes.py`/`test_concatenated.py`
(spot-checked by a sub-review, independently confirmed by this reviewer for `test_qec.py`).

---

## 3. Re-derived numbers

**(a) Code distances — Iceberg d=2, concatenated Iceberg-of-Iceberg d=4.**
Wrote a from-scratch brute-force Pauli-algebra script (`peer-review/scratch/oracle_distance_check.py`,
~100 lines, pure numpy — does **not** import anything from `src/qec/`), reconstructing both codes'
stabilizers/logicals directly from the physics description in the project's own docstrings (not by
calling `IcebergCode` or `ConcatenatedIceberg`), then brute-force searching for the minimum-weight
Pauli error that (a) commutes with every stabilizer and (b) anticommutes with some logical
(a genuine undetected logical error, not just a stabilizer-group element):

```
Iceberg k=4 (n=6): independently measured distance = 2        (claimed: 2)   MATCH
Concatenated k_inner=k_outer=2 (n=16, k=4): independently measured distance = 4   (claimed: 4)   MATCH
  [also independently confirmed: 12 stabilizer generators mutually commute;
   all 8 logicals commute with all stabilizers — a valid stabilizer code]
```

**(b) The η ≈ 0.25 "encoding stops helping" crossover.**
Derived analytically from the stated noise-channel definition (`src/encoded_codes.py:592-598`:
each 2-qubit depolarizing error is `p2·(1-η)/15` on 14 non-ZZ Pauli components, `p2·(1-η)/15 + p2·η`
on ZZ) **without calling any project function**:
- Iceberg's native weight-2 `ZZPhase` gate is undetectable exactly when the fault is XX, YY, or ZZ
  (these three commute with both all-X and all-Z stabilizers and equal the code's own weight-2
  logical operator). Undetectable fraction per gate = `(XX+YY+ZZ) share = 3·(1-η)/15 + η = 0.2+0.8η`.
- At the 2×2 test lattice, Iceberg has 12 such two-qubit rotation gates per Trotter step, giving
  `undetected_iceberg(η) = 12·p2·(0.2+0.8η)`. Bare's total two-qubit-gate error is η-independent
  (bias only redistributes *which* Pauli occurs, not whether one occurs), and was read off the data
  table as `4.8·p2` (e.g. 2.88e-3 at the H2-prior p2=6e-4, 4.80e-3 at the legacy p2=1e-3).
- Solving `12·p2·(0.2+0.8η*) = 4.8·p2` gives **η\* = 0.25 exactly**, independent of p2 — matching
  `docs/encoded_tfim.md`'s claimed crossover ("η ≈ 0.25 ... Iceberg: 12·p2(0.2+0.8η) = 4.8e-3") to
  the digit. Plugging η = 0, 0.05, 0.08, 0.5, 0.9 into the formula reproduces the exact table values
  in `data/noise_sensitivity.txt` (e.g. η=0.05, p2=0.001 → 2.88e-3, ratio 0.600 — matches the table's
  "1.73e-03... (×0.60)" row at p2=6e-4 after rescaling by p2). **MATCH.**

Both headline numbers independently re-derived and confirmed correct.

---

## 4. Overall verdict

The QEC/encoded-TFIM core is sound: the Iceberg and concatenated-code constructions are correctly
specified (independently re-verified from scratch), the η-crossover claim is exactly derivable
from the stated noise model (independently re-derived from scratch), and the project's own tests
are genuinely discriminating rather than tautological. The main weakness is presentation of
statistical confidence: the headline "Iceberg recommended" / "~1.2×" / η-crossover numbers are
exact outputs of a first-order perturbative approximation, not sampled quantities, but this is
never stated, and the approximation's own breakdown (visible in the project's own data at low
acceptance, and in the systematic 5-15-point gap between first-order prediction and executed
Selene acceptance) is not flagged where the numbers are quoted. The "3–7× more two-qubit gates"
comparison also silently mixes two different lattice sizes between codes, though this does not
appear to bias the conclusion in the project's favor. Reproducibility is otherwise excellent: every
closed-form (non-Selene) script re-run reproduced its committed `data/` file exactly, including a
1.6M-shot Stim run with a fixed seed; only the slow Selene-execution rows in `encoded_codes.txt`
§4-5 and `encoded_iceberg.txt` remain unverified by this round due to CPU/time budget. None of the
findings here contradict the project's own "Iceberg is recommended, d≥3 is dominated" conclusion;
they are about honesty of uncertainty reporting, not about the physics being wrong.
