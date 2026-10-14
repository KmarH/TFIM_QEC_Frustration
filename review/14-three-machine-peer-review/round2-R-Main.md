# Round 2: Cross-verification by R-Main

**Platform:** Windows 11, Python 3.13 (venv at `%TEMP%\tfimv`, always run with `-X utf8`).

**Method:** two local subagents re-derived the other reviewers' claims, one for R-Oracle and one for R-Laptop. I then read R-Oracle's Round 2 report and settled my own findings against it.

**Scratch work:** `peer-review/scratch/r2-oracle/` and `peer-review/scratch/r2-laptop/` on the R-Main copy. No project files were modified.

---

## 1. Verdicts on R-Oracle's Round 1

| ID | Verdict | Evidence |
|---|---|---|
| R-Oracle-1 (major) | **PARTLY. Lowered to MINOR** | The docs already label these numbers first-order: `docs/encoded_tfim.md:164` ("[Stim, first order]"), and again at :187, :232, :267. Only the explicit "no sampling error" sentence is missing. The Monte Carlo check (next row) shows the approximation error is a few percent at most. |
| R-Oracle-2 (major) | **REFUTED** | Stim Monte Carlo after 3 steps, first-order exp(−Σp) acceptance vs sampled, is in the table below. For the undetected-logical first-order sum vs MC P(flip\|accept): Iceberg 6.00e-3 vs 6.11e-3; concat 1.40e-2 vs 1.50e-2 (+7%); Steane 1.40e-2 vs 1.45e-2. So the method holds to ≤7% even at acceptance ≈ 0.01. The finding also has two factual errors: (a) the "0.033 (concat 2×2, 3e-3)" it quotes is the **executed Selene** value, not first-order (first-order is 0.105, `data/encoded_codes.txt` §4 vs §5); (b) the 5–15-point Selene gap is not approximation error. `data/selene_gap.txt` shows exp(−D) 0.670 vs Stim-sampled 0.673, and traces the gap to Selene's one-qubit channel. |
| R-Oracle-3 | **CONFIRMED. The understatement is bigger than stated** | At a matched 2×2 lattice, two-qubit gates per step: Iceberg 28, Steane **240 (8.6×)**, 5-qubit **192 (6.9×)**, concat 184 (6.6×). The true range is about 6.6–8.6×, not "3–7×". Feasibility doesn't explain the smaller lattice for 5-qubit: at 2×2 it needs 22 qubits, which the budget table marks as local (L). |
| R-Oracle-4 | **CONFIRMED** | `python -I main.py` gives `ModuleNotFoundError: config` (`main.py:16`) on Windows too. |
| R-Oracle-5 | **CONFIRMED, but the fix is wrong** | The 5 kept-shot Z2 values are {1, 1, .25, .25, .25}, giving mean 0.55 ± 0.184 as quoted. The correct t₄ 95% half-width is 0.51, against 0.36 from the normal approximation. But Z2 per shot is not a binomial proportion, so Wilson/Clopper-Pearson suits the acceptance column only. For Z2 use t-intervals or a bootstrap, or suppress the ±. |
| R-Oracle-6 | **CONFIRMED** | Brute force on the codes as built by `make_code`: Iceberg d=2, Steane d=3, 5-qubit d=3, concat (n=16) d=4. |
| R-Oracle-7 | **CONFIRMED** | 12 = B + 2N rotations at 2×2. Undetectable share is 0.2 + 0.8η; bare cost is 4.8·p2, independent of η. Solving gives η* = 0.25, and the table values at p2 = 6e-4 come out exact. |
| R-Oracle-8 | **NOT RE-VERIFIED** | No conflicting evidence. |

R-Oracle-2: first-order vs Monte Carlo acceptance after 3 steps:

| code, lattice, p2 | first-order | Monte Carlo |
|---|---|---|
| Iceberg 2×2, 1e-3 | 0.8751 | 0.8748 ± 0.0007 |
| concat 2×2, 3e-3 | 0.1050 | 0.1047 ± 0.0007 |
| Steane 2×2, 3e-3 | 0.0563 | 0.0563 ± 0.0005 |
| Steane 2×3, 3e-3 | 0.0097 | 0.0097 ± 0.0002 |

## 2. Verdicts on R-Laptop's Round 1

| ID | Verdict | Evidence |
|---|---|---|
| R-Laptop-1 (major) | **CONFIRMED. Lowered to MINOR** | The test does pass with a no-op mover, an always-flip mover, or a mover with rare (1e-3) invalid flips, so it is vacuous about the mover. But the **guard itself works**: from a real in-sector 3×4 start, both invalid movers raise "left the defect-free W0 sector". The no-op mover is also caught by `len(v)==60` (`test_mcmc_baseline.py:128`). What's missing is a regression test, not a safety net. |
| R-Laptop-2 | **REFUTED: wrong statistic** | Dividing the gap by the temporal std of an *oscillating* curve does not give the uncertainty of the gap. Paired noisy-minus-ideal differences over t = 20–40: 3×3 gap −0.0497, z ≈ 9 (naive SE) or 17 (batch SE), noisy below ideal at 21/21 points. 3×4 gap −0.0078, z ≈ 5–7, noisy below ideal at 18/21. Both drifts are resolved and each covers about 45–51% of the distance to B_W0. A remaining doc nit: quote a σ. |
| R-Laptop-3 | **PARTLY / PLATFORM-SPECIFIC** | The slowness reproduces: 228 s on Windows vs 84.5 s on the reference machine. But the slow call is `spectral_gaps` (`frustration.py:90-96`, full-space eigsh with k=3, gap 4.65e-5), which takes 214 s. `even_sector_ground_state` takes only 0.4 s. Values agree. |
| R-Laptop-4 | CONFIRMED (nit) | |
| R-Laptop-5 | CONFIRMED (nit) | Also, `noisy_q3` cuts on winding plus defects while `Targets.postselect` cuts on defects only, so they are not even the same estimator. |
| R-Laptop-6 | CONFIRMED | No test calls `.postselect`. The only callers are `run_gauss_law.py:133,154,199`. |
| §3.1 | CONFIRMED on Windows | C(1) = −0.99437 / −0.32455; E/bond = −1.005628 / −0.341228. |

### How R-Main-1 and R-Main-2 affect R-Laptop's "sound" verdict

**Ordering (R-Main-1), at J = −1, dt = 0.25:**
- The sector-conditioned headlines (flippable density, C(0.866)) move by ≤ 4e-4.
- Defect density and P_out change by 1.5–3×, and the sign of the bias flips:

| quantity | ZZ outside (project) | X outside (circuits) | continuous time |
|---|---|---|---|
| 3×3 defect density | 0.0044 | 0.0016 | 0.0029 |
| 3×4 defect density | 0.0077 | 0.0049 | 0.0066 |

**h/|J| = 2 (R-Main-2), noiseless ideal circuits:**
- 3×3: p_in 0.41–0.55; 3×4: p_in 0.06–0.11; defect density 0.11–0.21.
- So Gauss post-selection would discard 45–94% of shots even with no noise.
- The H_QDM / B_W0 framing would not describe quench4, and the ordering matters about 10× more at h = 2 (Δp_in = 0.14).

**Net:** R-Laptop's "sound" verdict holds for the internal computations, but it is **conditional for Q3** as a description of the experiment.

## 3. Defending and retracting my own Round 1 findings, against R-Oracle Round 2

- **R-Main-1, -2, -4, -5:** R-Oracle confirmed all four independently. For R-Main-2 it read the raw quench4 QASM (`rzz(0.5)`, `rx(0.5)` / `rx(1.0)`), which gives **h/|J| = 2**. So 0.3 in `config.py` and the docs is wrong. **Upheld; now settled.**
- **R-Main-3: upheld, with a correction.** R-Oracle is right that I mislabelled the column. The 2.0σ / 3.2σ figures were computed from the **pair-average** H2 column, **0.7324 ± 0.0091**, not 0.7372 ± 0.0090 (the raw Z2 column). The conclusion is unchanged.
- **R-Main-8:** I accept R-Oracle's reframing. The behaviour is tested (`test_lattice.py:34-38`), physically forced at L = 2, and disclosed for the η crossover (`encoded_tfim.md:305`). **Stays MINOR.** The fix becomes "state the degenerate bond count wherever a 2×2 / 2×3 result is quoted".
- **R-Main-11, "63 vs 42" row: RETRACTED.** These are two correct metrics, `len(paulis)` and `undetected_logical`. The real issue is ambiguous naming (R-Oracle-R2-1).
- **R-Main-11, "13× vs 32×" row: defended, pending Round 3.** R-Oracle showed 13× is self-consistent with one row of `gauss_law_dimers.md:174`. My claim is that other rows of `data/gauss_law_mitigation.txt` reach 32× (bitflip p = 1e-2, t = 3.25, dimer-dimer). R-Oracle could not find it, so this goes to Round 3.

## 4. New findings

- **R-Main-R2-1 [MAJOR] Q3 §8's Trotter-bias numbers don't describe the circuits.** `docs/q3_thermalization.md:234-237` says "dt = 0.25 inflates P_out ≈10–25% and defect density ≈40%". That holds only for the ZZ-outside ordering. With the circuits' X-outside ordering, the sign of the bias **reverses** on 3×3 and 3×4 (table in §2). The ordering caveat at :263 covers only flippable density and C1. 3×6 was not run.
- **R-Main-R2-2 [MINOR] B4 contradicts itself about the Selene gap.** `encoded_tfim.md:202` still blames "the first-order exp approximation [inferred]". The same document at :314 and `data/selene_gap.txt` §1 rule that out. This probably misled R-Oracle-2.
- **R-Main-R2-3 [MINOR] The acceptance-penalty ratio depends on lattice size.** "3–4×" (`encoded_tfim.md:181`) and "3–5×" (:218) hold only at 2×3. At 2×2, p2 = 1e-3, the ratio is 1.9–2.3×: Iceberg 0.875 vs 0.383 / 0.469 / 0.472. State the lattice.
- **R-Main-R2-4 [NIT] `--skip-exec` truncates data.** `scripts/run_encoded_codes.py --skip-exec` opens `data/encoded_codes.txt` with "w" and truncates the Selene rows (§5). This is undocumented, and it is what forced R-Oracle's `git checkout`.
- **R-Main-R2-5 [MINOR] Test fixes.** Add a monkeypatched mover-escape test for R-Laptop-1. Any `v0` / `tol` pin for R-Laptop-3 belongs in `frustration.py:90-96`.

## 5. Overall assessment

| finding | status | evidence |
|---|---|---|
| R-Main-1 (ordering) | double-confirmed | |
| R-Main-2 (h/\|J\| = 2) | settled | raw QASM |
| R-Main-3 (step-1 gap ~2σ) | double-confirmed | |
| R-Main-4 (sign-blind check) | double-confirmed | |
| R-Main-5 (Q1 design: 60 > 56 qubits, no shot/estimator accounting) | double-confirmed | |
| R-Main-R2-1 (Q3 Trotter-bias sign) | new major | |

Several earlier "majors" came down on evidence:
- **R-Oracle-1 and R-Laptop-1** are now minor.
- **R-Oracle-2 and R-Laptop-2** are refuted.

The QEC side holds up well: distances, η*, and the first-order method itself, which is better than R-Oracle feared. The open disputes for Round 3 are:
1. the severities of R-Laptop-1 and R-Oracle-1/-2
2. the R-Laptop-2 statistic
3. the 32× claim
4. what fixing the ordering and h/|J| does to Q3's conclusions
