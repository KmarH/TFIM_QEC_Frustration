# Round 1 — Independent Review by R-Laptop

Reviewer: R-Laptop (Claude Code, home server, Linux x86_64, Python 3.14)
Focus: Frustration, thermalization and the Gauss law — `src/frustration.py`, `src/dimers.py`,
`src/mcmc_baseline.py`, `src/noisy_q3.py`, `src/trotter_threshold.py`, `src/gauss_mitigation.py`
(Q2 "triangular NN correlations 3–5× weaker than square", the per-winding-sector MCMC baseline,
relaxation to the finite-cluster value, the Trotter threshold, Gauss-law post-selection as
mitigation, "noise can mimic thermalization").

This round was done independently: no other reviewer's output was consulted. Two read-only
sub-agents handled `src/mcmc_baseline.py`+`src/dimers.py` and `src/trotter_threshold.py`+
`src/noisy_q3.py`+`src/gauss_mitigation.py` respectively, each running its own tests and
from-scratch re-derivations in `peer-review/scratch/`; I reviewed their evidence, re-checked
file:line citations myself, and did my own independent code (not sub-agent-sourced) for §3.1–3.2
and the full-script reproducibility run (§1).

---

## 1. Run log

**Environment.**
- Host: Linux x86_64, 4 cores, 9.1 GiB RAM.
- `python3` on the host is 3.14.4. Created `.venv` with `python3 -m venv .venv`; installed
  `requirements.txt` as pinned.
- **No version deviations were needed.** Every pin in `requirements.txt` (numpy 2.5.3, scipy
  1.18.1, pytest 9.1.1, stim 1.16.0, pytket 2.18.4, guppylang 1.1.2, selene-sim 0.3.4, hugr 0.18.8,
  matplotlib 3.11.2 and the rest) installed from a wheel on Python 3.14, confirmed by `pip list`
  after install matching the pins exactly. Worth noting positively: the project's CLAUDE.md treats
  the Python-version pin (3.11→3.12, FLAG A) as an open risk, but the whole stack — including
  stim, pytket, guppylang and selene, the packages most likely to lag CPython releases — already
  has wheels for 3.14, two versions ahead of the pin.
- `numpy.show_config()`: OpenBLAS 0.3.34 (Haswell dynamic-arch); relevant to R-Laptop-3 below.

**Commands run.**
| command | result |
|---|---|
| `python -m pytest tests/ -q` | **231 passed**, 4 warnings (deprecation warnings from `selene_helios_qis_plugin`, unrelated to this review's focus), **159.33 s** |
| `python main.py` | ran cleanly, default 3×3 statevector backend, printed observables |
| `python -I scripts/plot_q3.py` | ran cleanly, wrote all 5 figures to `figures/` |
| `python -I scripts/compare_frustration_correlations.py` (regenerates `data/frustration_correlations.txt`) | ran to completion in 520 s; diffed against the committed file — see §3.1 and R-Laptop-3 |
| `tests/test_mcmc_baseline.py tests/test_dimers.py` (sub-agent) | 60/60 passed, 64.15 s |
| `tests/test_trotter_threshold.py tests/test_noisy_q3.py` (sub-agent) | 18/18 passed, 83.15 s |

**Reproducibility diff.** `scripts/compare_frustration_correlations.py` → `data/frustration_correlations.txt`:
every physically meaningful number (`E/site`, `E/bond`, every `C(r)` mean at h > 0) reproduced
**bit-for-bit** against the committed file. Full detail in R-Laptop-3. The committed
`data/frustration_correlations.txt` was restored byte-for-byte after this check (temporary diff
only; `git status` shows no changes outside `peer-review/`).

**Test-count note.** `CLAUDE.md`'s "Environment" section states tests are "currently 169/169,
about 100 s" — stale; actual is 231/231 in ~159 s on this host, matching `README.md`'s own figure.
Not a code defect, but `CLAUDE.md` is specifically the doc reviewers are told to trust for what to
expect.

---

## 2. Findings

### R-Laptop-1 — major — sector-escape guard test is vacuous w.r.t. actual sampler dynamics
**Location:** `tests/test_mcmc_baseline.py:131-136` (`test_sampler_raises_if_not_in_a_sector`), guard
code at `src/mcmc_baseline.py:453-456`.

**Evidence.** The test feeds `s0 = np.ones((3, 3))` (all spins up) as the starting configuration.
This configuration already has 18/18 possible defects (every triangle violates the Gauss law) and
**zero flippable sites**, confirmed independently (`peer-review/scratch/check_guard_vacuous.py`):
with no site flippable, the sampler's move loop (`src/mcmc_baseline.py:443-451`) performs **zero
actual flips** for the whole run. The `RuntimeError` at line 456 fires because the *initial* state
already fails `np.any(ev.defects(z) != 0)` — not because any dynamics the mover performed caused a
departure from the sector. The test would pass identically if the flip-application code (lines
448-450) were completely broken (e.g. a no-op), since the exception is raised before the mover's
correctness is ever exercised in a sector-violating way.

The complementary test (`test_sampler_never_leaves_the_sector_checked_against_dimers_arrays`, same
file, lines 115-128) does run many real sweeps from a genuine in-sector start and checks every
visited state against independent `dimers.py` arrays, so the *positive* claim ("valid moves
preserve the sector") is well covered elsewhere. Only the *negative* claim ("the guard would catch
a real escape caused by a mover bug") is untested.

**Failure scenario this would miss:** a future change to the flip/acceptance logic that
occasionally performs an invalid flip (e.g. an off-by-one in the hexagon-neighbour indexing, or a
masking bug in the vectorized `rows[flip]` update) would not be caught by either test if it
produces a transition that happens to still satisfy the aggregate per-sweep checks on *most*
sweeps, and the "raises" test gives false confidence that such a bug would be caught.

**Suggested fix:** start from a genuine defect-free, correct-winding configuration and inject a
single artificial invalid flip between sweeps (e.g. monkeypatch the flip mask for one site, or
directly corrupt `z` after a sweep) to confirm the guard fires on an actual in→out transition
produced through the code path under test, not only on a bad initial condition.

### R-Laptop-2 — minor — the two "noise can mimic thermalization" data points are of very different statistical strength, reported as equally-weighted evidence
**Location:** `docs/q3_thermalization.md:308-311`, `data/q3_noisy.txt` (late-window rows for 3×3 and 3×4).

**Evidence.** The doc's drift-toward-`B_W0` claim is illustrated with two clusters:
- 3×3: noisy conditioned 0.4274 vs ideal conditioned 0.4768, gap 0.050 against a late-window
  temporal std of 0.0186 → **~2.7σ**, clearly resolved.
- 3×4: noisy conditioned 0.2762 vs ideal conditioned 0.2841, gap 0.0079 against std 0.0056 →
  **~1.4σ**, marginal.

The doc presents both side by side as supporting the same qualitative conclusion without flagging
that the 3×4 point is much weaker evidence (and arguably consistent with noise at that
significance). The underlying physical mechanism description is fine and already labelled
`[inferred, not measured]`; this is purely about not quietly mixing a well-resolved and a marginal
data point in the same sentence. Suggest reporting an explicit significance (σ or SE) for the
drift itself alongside each cluster's number, not just the raw/ideal values.

### R-Laptop-3 — minor (portability, not correctness) — one ARPACK eigensolve in `compare_frustration_correlations.py` is ~5× slower on this platform, unevenly across points
**Location:** `src/frustration.py:74-87` (`even_sector_ground_state`, `scipy.sparse.linalg.eigsh`
with `tol=1e-12`), exercised by `scripts/compare_frustration_correlations.py`.

**Evidence.** I reran the full script end to end (both the 4×4 and 3×4 cluster pairs, all 5 field
values) and diffed it against the committed `data/frustration_correlations.txt`
(`peer-review/scratch/frustration_regen.log`). The run completed in 520 s wall-clock, but the
per-point timings diverge unevenly from the reference (aarch64, Python 3.12.14) annotations
already baked into the committed file:

| point | reference time | this host | ratio |
|---|---|---|---|
| square 4×4, h=0.1 | 3.1 s | 8.5 s | 2.7× |
| triangular 4×4, h=0.1 (full-space gap 4.65e-05, smallest in the scan) | 84.5 s | **455.2 s** | **5.4×** |
| triangular 4×4, h=0.3 | 50.8 s | 29.2 s | **0.6× (faster)** |
| triangular 4×4, h=0.6 / h=1.0 | 10.5 s / 3.4 s | 11.0 s / 3.5 s | ~1× |

Only the near-degenerate h=0.1 triangular point blows up; nearby points with larger gaps are
unaffected or even faster on this host. This points to ARPACK's Lanczos restart count for that
specific near-degenerate matrix being sensitive to the default starting vector / BLAS kernel on
this platform, not a uniform slowdown of this host.

**Every physically meaningful number reproduced exactly.** All `E/site`, `E/bond` and `C(r)` means
at h > 0 are bit-identical to the committed file. The only non-timing differences are (a) the
`dE_ED` column, moving between ~1e-13 and ~1e-14 on both platforms — noise at a level both runs
already call "0" — and (b) the shell `[lo, hi]` spread at **h = 0** on both lattices, which differs
between runs because the h=0 ground state is degenerate and ARPACK returns an arbitrary vector in
the degenerate subspace on each run. This second point is not a bug: it is exactly what
`src/frustration.py`'s own docstring and `docs/q2_frustration.md` §A.1 warn about ("h = 0 ...
recorded but NOT interpreted"), and no conclusion in the docs relies on h=0 shell spreads. This
cross-platform rerun is, if anything, independent confirmation that the h=0 caveat is necessary,
not just defensive writing.

**Net assessment:** not a correctness problem — re-derived independently in §3.1 to 5 decimal
places. Worth a note that this script's wall-clock time is not tightly bounded across platforms
(the slow point alone took >5× longer here), so a reviewer or CI job on a differently-configured
machine than the Oracle reference should budget generously. Pinning ARPACK's `v0`/`ncv` would make
convergence behaviour more platform-independent if reproducible timing matters.

### R-Laptop-4 — minor — `CLAUDE.md` test-suite count/runtime is stale
**Location:** `CLAUDE.md` ("Environment" section: "currently 169/169, about 100 s").

**Evidence:** `python -m pytest tests/ -q` on this host: **231 passed in 159.33 s**. `README.md`
already states 231 ("231 tests, about 2-3 minutes"), so the drift is isolated to `CLAUDE.md`. Not a
code defect; a one-line fix keeps the two docs consistent.

### R-Laptop-5 — minor — `docs/q3_thermalization.md`'s phrase "the handoff/02 detection-only mitigation" can read as implying shared code with §9's Gauss-law post-selection; it is a separate implementation
**Location:** `docs/q3_thermalization.md:277`; `src/gauss_mitigation.py` (`Targets.postselect`,
lines 171-174) vs. `src/noisy_q3.py:414-461` (`run_observables`'s own conditioning logic).

**Evidence.** `src/noisy_q3.py` does not import or call anything from `src/gauss_mitigation.py`.
Section 9's Gauss-law post-selection (the "×30/×21" numbers) is computed by an independent
implementation inside `noisy_q3.run_observables`/`evaluate`, operating on the Pauli-trajectory
Monte Carlo mixture rather than `gauss_mitigation.py`'s exact-density-matrix/trajectory machinery.
This is a correct and probably deliberate separation (different noise representations, different
scale), but the doc's cross-reference reads as if one test suite or one code path covers both,
which it does not — `gauss_mitigation.py` has no dedicated test file; it is covered only via
`tests/test_dimers.py` (6 tests), while `noisy_q3.py`'s own post-selection logic is covered by
`tests/test_noisy_q3.py`. Purely a documentation clarity point; no evidence either implementation
is wrong (see R-Laptop re-derivations, §3).

### R-Laptop-6 — minor (test-coverage gap) — `Targets.postselect` has no direct unit test
**Location:** `src/gauss_mitigation.py:171-174`.

**Evidence:** grepping `tests/test_dimers.py` for `.postselect(` and `.raw(` finds only one call
to `.raw(` (inside `test_estimators_are_exact_on_ideal_global_depolarizing`, which tests `selfmit`)
and zero direct calls to `.postselect`. The function is simple (boolean-mask filter + renormalise),
so the risk is low, but it is the estimator `docs/gauss_law_dimers.md` §5.3's whole "qualified yes"
verdict rests on, and it has no test exercising it in isolation (e.g. against a hand-constructed
distribution with a known post-selected mean).

---

## 3. Re-derived numbers

**3.1 Q2 headline correlation numbers (matched 4×4 pair, h = 0.3; `docs/q2_frustration.md` §A.3).**
`peer-review/scratch/rederive_frustration.py`, written from scratch (own bit-level Hamiltonian
construction, own bond enumeration for the square/triangular 4×4 periodic torus, own P-even
projection), **not calling** `src/frustration.py`, `src/operators.py`, or `src/lattice.py`:

| | my independent result | doc's claim (`data/frustration_correlations.txt`) |
|---|---|---|
| square 4×4, h=0.3, C(1) | **−0.99437** | −0.99437 |
| triangular 4×4, h=0.3, C(1) | **−0.32455** | −0.32455 |
| square 4×4, h=0.3, E/bond | −1.005628 | −1.00563 |
| triangular 4×4, h=0.3, E/bond | −0.341228 | −0.34123 |
| max\|⟨Z_i⟩\| (both) | ~1e-16 | ~1e-16 |

Exact match via a completely independent code path — strong evidence the "3–5× weaker
nearest-neighbour correlation" headline (`README.md`, `docs/q2_frustration.md`) is correctly
computed, not an artifact of a bug shared between the production code and its own tests.

**3.2 Q3 stripe dressing continuum limit, (h/|J|)²/8 (`docs/q3_thermalization.md` §6).** Re-derived
analytically and cross-checked numerically, no project code called: for the frozen stripe sector
every site has `n_s = 2` and is its own single-state "sector" (so the sector-average term `⟨g⟩_W0`
and the own-configuration term `g(c0)` are identical), giving
`ρ_D(h) ≈ 2h²·(n_s=2)·(dt/2)²/sin²(2|J|dt)/2 → h²/(8J²)` as dt→0:

| dt | my ρ_D/h² | continuum target 1/8 |
|---|---|---|
| 0.25 | 0.135959 | 0.125 |
| 0.10 | 0.126680 | 0.125 |
| 0.01 | 0.125017 | 0.125 |
| 0.001 | 0.125000 | 0.125 |

Confirms both the continuum limit and the magnitude of the dt=0.25 Floquet excess the doc quotes
(≈1.088×, matching `0.135959/0.125 = 1.088`).

**3.3 Sub-agent re-derivations** (I reviewed the evidence and file:line citations rather than
re-running the CPU-bound parts myself, to avoid duplicating work):
- **MCMC detailed balance**, built from scratch (`peer-review/scratch/check_detailed_balance.py`):
  the 3×3 per-attempt transition kernel is symmetric to machine precision, the 42-state defect-free
  component is closed under it, and the stationary distribution is uniform to 1.1e-15 — an
  independent confirmation of "symmetric kernel ⇒ uniform on the component", not a re-read of the
  docstring's proof.
- **Trotter-threshold dense scan** (3×3, 3-sublattice, h=0.1), rebuilt independently
  (`peer-review/scratch/check_trotter.py`) via the project's own `trotter_error_scan` (this one
  *does* call project code, so it's a regression/reproduction check rather than an independent
  derivation): slope 2.0319, threshold bracket (0.46, 0.48], and per-dt errors bit-identical to
  `data/trotter_threshold.txt` and `docs/q3_thermalization.md` §8 Table row 1.
- **Noisy-trajectory SE scaling** (`peer-review/scratch/check_noisy_se.py`): re-ran the 3×4 bare
  noise simulation at n_traj=100 and 400, got batch SE 0.00095 → 0.00040, matching the doc's
  quoted ±0.0004 at n_traj=400 and scaling correctly as ~1/√n — concrete evidence the quoted error
  bars are not an artifact of an SE-computation bug, and are achievable with the stated trajectory
  counts.
- `data/gauss_law_scaling.txt` leak-exponent fit (slope=2.08 for 3×6) matches the prose in
  `docs/q3_thermalization.md` §5 exactly (checked directly from the data file).
- `data/trotter_threshold.txt` threshold brackets for 3×3/3×4 (absolute and relative, all four
  field values) match `docs/q3_thermalization.md` §8's table exactly (checked directly from the
  data file).

---

## 4. Overall verdict

The code in this focus area (frustration ED, the sector-restricted MCMC baseline, the Trotter
threshold study, and the noisy/Iceberg Q3 pipeline) is **sound and the headline numbers are
real**: three independent re-derivations (two mine, from scratch; one a sub-agent's from-scratch
detailed-balance check) all reproduced the project's own numbers exactly, and a full,
independent re-run of the Q2 correlation script reproduced every physically meaningful value
bit-for-bit on a different OS/CPU architecture/Python version. The statistics (MCMC jackknife and
chain SE, noisy-trajectory batch-means SE) check out against the formulas they claim to implement
and against independent reproduction at varied sample sizes. The test suites in this area are
overwhelmingly cross-checked against independent methods (exact enumeration, `expm_multiply`,
dense diagonalization, brute-force readout) rather than tautological, with one concrete exception
(R-Laptop-1): the sector-escape guard's own "it raises" test doesn't exercise a genuine
mover-caused escape, only a bad starting configuration, which is worth fixing since it is the
project's main defense against a silent MCMC correctness bug. The remaining findings are minor
documentation/coverage/portability notes, not numerical errors. I found no evidence of fabricated
numbers, no tautological test masquerading as validation beyond R-Laptop-1, and no statistically
unsound error-bar claim in this focus area.
