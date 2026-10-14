# Round 1: Independent review by R-Main

**Reviewer:** R-Main, Claude Code on a Windows 11 laptop, Python 3.13. This reviewer also orchestrates the review.

**Focus:**
- Core TFIM physics: `src/lattice.py`, `operators.py`, `trotter.py`, `observables.py`, `config.py`, `main.py`.
- The Q1 comparison harness: `src/compare.py`, `scripts/run_compare.py`.
- A check of every claim in the docs against the data.
- Windows portability.

The work was split across three local subagents. I reviewed their output and spot-checked their citations. Their full working notes are in `peer-review/scratch/{physics,docs-audit,winrun}/` on R-Main's copy.

---

## 1. Run log

**Environment**
- Windows 11, Python 3.13.15.
- Every pin in `requirements.txt` installed from a wheel, with no version changes. That includes stim, pytket, guppylang, selene-sim and hugr.
- The venv had to be recreated at a short path (`%TEMP%\tfimv`). The review folder's path is very long and hits Windows path-length limits during install and test collection.

**Commands**

| command | result |
|---|---|
| `python -m pytest tests/ -q` | **229 passed, 2 failed** in 241 s. Failures: `test_plot_q3.py::test_size_parser` and `::test_noisy_parser`. |
| `python -X utf8 -m pytest tests/test_plot_q3.py` | passes |
| `python main.py` | runs; matches the observables printed on Linux. The console shows the em dash as `�`. |
| `python -I scripts/plot_q3.py` | **crashes**: `IndexError` in `fig_size` at `plot_q3.py:314` |
| `python -I -X utf8 scripts/plot_q3.py` | writes all 5 figures |
| `validate_stage1` (Windows wrapper) | every physics number identical. Only maxRSS and the `\|diff\|` round-off (1.2e-14 vs 2.6e-14) differ. |
| `scripts/run_concat_d4.py` | `data/concat_d4.txt` reproduced **byte-identical** |
| `scripts/run_trotter_threshold.py` | stopped before finishing, so not verified on Windows. It is covered by R-Laptop's rerun and by R-Main's independent re-derivation in §3. |

The committed `data/` was verified identical to commit a146bae after the runs.

---

## 2. Findings

### R-Main-1 [MAJOR] The Strang splitting in `src/trotter.py` does not match the published H2 circuits, yet it is used for runs compared with the paper
**Location:** `src/trotter.py:1-17,72-89`.
- `trotter.py` puts ZZ on the outside of each step.
- The reference QASM puts X on the outside: `research/05-zenodo-dataset-map.md:148-155`.
- `src/compare.py` has the circuit-order step. CLAUDE.md even says to use it when comparing with the published circuits.
- But the Stage‑3 and Q3 code calls `trotter.py` at the paper's dt:
  - `src/mcmc_baseline.py:521`
  - `scripts/run_gauss_law.py:70,103`
  - `src/gauss_mitigation.py:44`
  - `src/trotter_threshold.py`

**Evidence** (own code, not the project's):
- At J·dt = 0.25, h·dt = 0.5 on a 4×4 torus with θ = π/6, Z2 differs between the two orderings by up to **0.234** within 8 steps. The whole published quench1 signal runs from 0.73 to 0.39.
- On a 3×3 triangular torus with J = −1, dt = 0.25, the nearest-neighbour ⟨ZZ⟩ differs by 0.17 at h = 2.
- At h = 0.3 the difference is 7.4e‑3. That is larger than each ordering's own error against exact evolution (4.1e‑3 and 3.2e‑3).
- The trotter_threshold infidelity at dt = 0.25 (3×3 triangular, h = 0.1) is 1.29e‑4 with the project's ordering and 3.29e‑4 with the circuit ordering, about 2.5× higher.
- No test can catch this mismatch.

**Fix:** add a circuit-order option to `src/trotter.py`, use it for every run whose numbers are compared with the paper or with H2, and add a regression test.

### R-Main-2 [MAJOR] The project contradicts itself on the triangular parameter: h/|J| = 0.3 or 2?
- **Says 0.3:** `docs/report/report.tex:173-175` and `docs/gauss_law_dimers.md:21-26` say h/|J| = 0.3 "as in the reference §V", tagged [established]. `config.py:146-158,286-290` uses 0.3.
- **Says 2:** `research/05:152-171` and `handoff/03:45-46` say the quench4 QASM implies h/|J| = 2, and call 0.3 "WRONG".
- `research/04:139-141` admits the §V body text was never read.
- All Q2, Q3 and Gauss-law work runs at h ≤ 0.5, so the "matched to the reference" framing depends on which value is right. The report never mentions the conflict.

**Fix:** read the rx and rzz angles in `quench4_step*.qasm`. The dataset is on the Oracle VM at `~/zenodo_18487089`. Then downgrade whichever claim loses.

### R-Main-3 [MAJOR] The step-1 gap between H2 and the simulation is overstated, and the docs call a finite-size quantity size-independent
**Location:** `docs/q1_compare.md:29,57`; `report.tex:236-257`; `src/compare.py:257-261`.
- The pair average removes only the 1/N self term. The connected nearest- and next-nearest-neighbour terms still scale roughly as 1/N.
- A light-cone exact step-1 calculation gives these pair averages: 4×4 → 0.7653, 4×5 → 0.7610, the real **7×8 torus → 0.7503**. The method reproduces the harness's own 4×4 and 4×5 values exactly.
- Against H2 quench1 `zne+znr` (0.7372 ± 0.0090), the gap is **2.0σ, not ≈3σ**. For `raw_unamplified` it is 3.2σ. On quench2, H2 sits above the simulation by 1.4σ.
- The 4×4 to 4×5 spread (0.007) understates the 4×5 to N = 56 gap (0.018) by about 2.5×.

**Fix:** use the light-cone exact value at N = 56, restate the significance, state that `_err` is assumed to be 1σ, and drop "size-independent".

### R-Main-4 [MAJOR] The circuit check ignores signs, though the report says it checks them
**Location:**
- `scripts/run_compare.py:40-42,61-66`: `_same_up_to_sign` compares only |angle| for each gate type.
- `report.tex:232-233` claims "gauge signs were re-checked … aborts on mismatch".
- `docs/q1_compare.md:44`.

**Evidence:**
- A QASM with rzz(+0.5), rx(−0.5), ry(+θ) passes the check. That is the non-gauge pairing (J, −h, θ).
- The project's own `test_compare.py:172` shows that pairing shifts Z2 by more than 0.05.
- Mixed-sign rzz gates across bonds also pass.
- `data/q1_compare.txt` logs only magnitudes.

**Fix:** check the signed (rzz, rx, ry) triple against the gauge-equivalent set {(J,h,θ), (−J,−h,θ), (J,−h,−θ), (−J,h,−θ)}, and log the signs.

### R-Main-5 [MAJOR] The Q1 thesis ("encoding is the only axis that varies") can't be tested against the released data, and the harness has no logical arm
**Location:** `README.md:4-7`; `report.tex:86-89,123-126,665-667`; `compare.py:53-63` (`Series` has no fields for shots, acceptance or estimator type).
- **Too many qubits:** Iceberg needs k+4 physical qubits, so the released 7×8 lattice needs 60, more than H2's 56. The project flags exactly this for Q3 at 9×6, but never for Q1.
- **Different estimators:** the released data are ZNE+ZNR mitigated, with randomized compiling and dynamical decoupling. A logical result is a post-selected estimate.
- **No shot accounting:** the harness tracks no shots or post-selection. The classical encoded runs do handle this correctly.

**Fix:** make the Q1 head-to-head an encoded-vs-bare run on H2 at the same reduced lattice, with the released data as context only. Add n_shots, n_accepted and estimator-class fields, and compare against the `raw_unamplified` class of data.

### R-Main-6 [MINOR] Windows: no file I/O specifies an encoding, so the plotting script and two tests fail
**Location:** `scripts/plot_q3.py:52` (`open(...)` with no `encoding`).
- None of the 18 files in `scripts/` and `src/` that read or write files ever passes `encoding=`.
- The `data/*.txt` files are UTF-8 with non-ASCII characters (84 lines in `q3_noisy.txt`). On Windows, Python decodes them as cp1252, so the parser silently produces a 1-D array.
- Writers have the same problem in reverse: regenerating `stage1_validation.txt` without `-X utf8` produced a cp1252-encoded file.
- Everything passes under `-X utf8`.

**Fix:** add `encoding="utf-8"` to every `open`, `read_text` and `write_text` call. Optionally run CI on Windows.

### R-Main-7 [MINOR] The "Néel" initial state is really column stripes when Lx is even
**Location:** `src/backends.py:104-109`. On 4×4, ΣZZ over the bonds is 0, not −32. **Fix:** use `(x+y)%2`.

### R-Main-8 [MINOR] A periodic side of length 2 is silently treated as open
**Location:** `src/lattice.py:53,59`, plus the triangular de-duplication.
- `square_bonds(2,3,'periodic')` gives coordination 3, and triangular 2×3 gives 5.
- So EncodedConfig 2×3 and Sensitivity 2×2 are ladders or rings, not tori.

**Fix:** raise an error, or document it and label those runs accordingly.

### R-Main-9 [MINOR] Test gaps in the core physics
- `test_lattice` checks only bond counts and uniqueness, and has no triangular test.
- The "closed form" test at `test_operators.py:31-42` never asserts E0 = −√(J²+4h²).
- The single-spin tests are even in h, so the sign of h is never pinned down.
- No test covers periodic or triangular Trotter evolution, or the circuit ordering.

### R-Main-10 [MINOR] The Q1 test fixture is circular, and the run script is untested
- The fixture was written from the same inferred spec the loader implements: the `_err_<mode>` naming, dimercorrs stored as [r, step], decayrates of shape (4,).
- Only the quench1/2 Z2 loaders have been run on real files.
- `run_compare.py` has no tests: none for `is_synthetic`, the `trusted` gate or `verify_circuits`.
- The fixture QASM isn't under `circuits/`, so `verify_circuits` never runs even on the fixture.

### R-Main-11 [MINOR] Numbers in the docs that don't match the data
| claim | source | data |
|---|---|---|
| encoded worse than bare at "one early point" | `report.tex:267-270` | 6 (p2, step) cells, up to 2.8σ |
| self-mitigation "up to 13× worse" | `findings:73`, `report:601`, `gauss_law_dimers:194` | up to 32× |
| acceptance cost "3–5×" | `findings:53` | 2.9–3.9× (the report says 3–4×) |
| "63 undetected Paulis" | `report:276` | `encoded_iceberg.txt:14` shows 42 |
| slopes "2.00–2.04" | `report:501` | 1.97–2.04 |

Other mismatches:
- The Iceberg+Gauss shot cost is quoted relative to different baselines in different documents.
- Some numbers have no data file at all: 0.63 vs 0.78, |⟨Z_i⟩| 0.01–0.5, and "predicted 1.39–1.44".

### R-Main-12 [MINOR] Stale documentation
- The memory figures in `config.py:96-103` (413/1469/1871 MB, 5.5×) disagree with `data/stage1_validation.txt` (463/1543/1881 MB, 5.7×).
- The ED maxRSS values at N = 16/18 are the peak carried over from the earlier statevector run in the same process, not ED measurements.
- `q1_compare.md:55` still tags the periodic boundary as [inferred], though it is settled from the QASM a few lines earlier.
- CLAUDE.md says "169/169 tests"; the real count is 231.

**Checked and found sound:**
- loader and error-bar shape checks
- ceiling guards
- the N/(N−1) error scaling
- the gate-replay sign test
- the circuit-order step in `compare.py`
- the gauge identity (J,h) → (−J,−h), exact here because the initial state is real (ΔZ2 = 0.0)
- no noisy number is presented as an H2 result

---

## 3. Re-derived numbers (own code, importing nothing from the project)
- **Bonds, H, evolution:** my bond lists and H are identical for square and triangular lattices, open and periodic, Lx 3–6 × Ly 3–5 (max diff 0.0). `evolve` is identical (max diff 0.0), and energies agree to ≤ 3e‑17.
- **stage1 [1]:** 3×2 open ground-state energy E0 = −7.6730915064. ✓
- **stage1 [2]:** E(0) = −12.00000000, E(T) = −11.99955402. ✓
- **stage1 [3]:** Trotter errors 8.560e‑3, 2.133e‑3, 5.329e‑4, 1.332e‑4, each 4.0× smaller. ✓
- **stage1 [5]:** Lanczos E0 for 4×4, 6×3, 5×4 = −26.860505, −30.198962, −34.448537. ✓
- **trotter_threshold** (3×3 triangular, h = 0.1): infidelity at dt = 0.02 / 0.1 / 0.25 / 0.5 is 3.697e‑9 / 2.419e‑6 / 1.294e‑4 / 1.900e‑1. ✓ This matches only with the project's own ordering; see R-Main-1.
- **η crossovers:** 0.25, 0.357, 0.4375, 0.55. ✓
- **Exact step-1 Z2 on the 7×8 torus:** 0.7548, pair average 0.7503. This is a new number; see R-Main-3.
- **Claims audit:** 58 quantitative claims traced to `data/`. About 45 match exactly, 6 match with a caveat, and 7 do not match (R-Main-2, -3, -4, -5, -11).

---

## 4. Overall verdict
The numerical core is correct. Lattices, Hamiltonians, evolution, ED and the Stage‑1 validation all reproduce to every printed digit from independent code. Every reproducibility run that finished matched exactly on Windows and Python 3.13, except for the encoding bug.

The serious problems are about which experiment the code models, not about arithmetic:
- The Q3 and Gauss-law work uses a Trotter ordering that the H2 circuits don't use.
- The triangular field value is disputed inside the project itself.
- The Q1 "logical vs physical against released data" design can't fit on H2 at the released size, and has no shot or estimator accounting.
- The harness's sign check doesn't do what the report says, and the headline step-1 discrepancy is overstated.

None of these show the conclusions are false, but Q1's framing and the "matched to reference" status of Q2 and Q3 need fixing before hardware time is spent.
