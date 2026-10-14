# Round 3: Adjudication by R-Main

**Platform:** Windows 11, Python 3.13.

**Disputes assigned to R-Main:** D3b, D7 and D12.

**Scratch work:** `peer-review/scratch/r3-d3b/` and `peer-review/scratch/r3-d7-d12/` on the R-Main copy. No project files were modified, and nothing was written to `data/`.

---

## 1. Rulings on the assigned disputes

### D3b: does the Trotter ordering change the noisy-Q3 and Gauss-law mitigation conclusions? Mostly no: nothing changes sign, and one floor shrinks.

**Decisive check.** I reran each pipeline with only the step operator swapped, using identical random numbers for both orderings.
- The circuit-order rerun of `run_q3_noisy` (3×3, 400 trajectories) reproduces `data/q3_noisy.txt` exactly.
- The ZZ-outside rerun of the Gauss-law density-matrix pipeline reproduces `data/gauss_law_mitigation.txt` exactly.
- An independent dense-kron cross-check matches the noiseless floor.

**Noisy Q3 is already in circuit order.**
- `noisy_q3.run_bare` applies Rx-half, ZZ, Rx-half, and the Iceberg arm uses EncodedTFIM's circuit step. So R-Main-1 never reached these numbers.
- Gauss post-selection gain:

| case | circuit order | ZZ outside | docs |
|---|---|---|---|
| 3×3 early | 5.5× | 5.9× | 5.5× |
| 3×3 late | 6.1× | 5.9× | 6× |
| 3×4 early | 32.5× | 28.2× | ≈30× |
| 3×4 late | 16.9× | 17.4× | ≈21× |

  The 3×4 runs used 240 trajectories, against 400 for the docs. The gap from the docs' ≈21× is Monte-Carlo noise, about 2 SE, and it appears in both orderings.
- The "noise mimics thermalization" drift is unchanged. 3×3: noisy-conditioned 0.4274 vs ideal 0.4768, with B_W0 = 0.381. 3×4: 0.2743 vs 0.2841. Both orderings give the same.

**Gauss-law noiseless floor** (3×3, t = 10):

| | ZZ outside (docs) | circuit | exact |
|---|---|---|---|
| NNN ⟨ZZ⟩ post-selection floor bias | +0.0135 | **+0.0092** | +0.0115 |
| defect per triangle | 3.64e-3 | 1.50e-3 | 2.48e-3 |
| keep fraction | 0.979 | 0.988 | 0.983 |
| 3×6 min P(zero defects) | 0.908 | 0.937 | 0.920 |

Mitigation gains move by ≤ 20% and keep their order: depol 1e-3 4.9 → 4.2×, bit-flip 1e-3 7.8 → 6.4×, dephasing 1.5 → 1.3×. The cost stays 1.0–1.75×.

**Ruling.**
- **Survive unchanged:**
  - every noisy-Q3 number
  - the 3×3 5.5–6× gain
  - the thermalization-mimicry drift
  - "Gauss 2–8× at 1.1–1.8× cost", "dephasing: no help" and "self-mitigation fails"
- **Change magnitude:**
  - The "≈0.013 floor" is 0.009 in circuit order (0.0115 in continuous time).
  - The noiseless defect density in the docs is about 2.4× too high for the circuit.
  - Quote the 3×4 gains as roughly 20–30×.
- **Change sign:** none in the noisy/mitigation layer. The sign error is confined to the noiseless §8 defect-density and P_out statements (R-Main-R2-1 / R-Laptop-R2-1).

### D7: how many cells have encoded further from ideal than bare? 7 backend-cells (6 distinct (p2, step) pairs). "One early point" is misleading.

Using `data/encoded_iceberg.txt` §3, 7 of 24 cells have |enc−ideal| > |bare−ideal|: 3 local-sim and 4 Selene. Two of them are late (steps 4 and 5 at p2 = 3e-3). One is a tie to 1e-4.
- The 2.8σ figure is encoded vs **ideal**. Encoded−bare is never more than 1.02σ.
- Encoded beats bare by ≥ 2.5σ only at step 6.
- R-Main's 6 counted (p2, step) pairs; R-Laptop's 7 counted backend-cells. Both are right, but R-Laptop's "4 + 4" split is wrong (it is 3 + 4).
- Suggested wording: "In 7 of 24 cells at p2 ≤ 3e-3, encoded is further from ideal than bare, never by more than 1σ in encoded−bare. Encoded beats bare at ≥ 2.5σ only at step 6."

### D12: what fits for Q1 on H2?
- The project's own formula is n_phys = k + 4 with k even (`encoded_tfim.py:5-6,58-59,64`).
- On 56 qubits the options are 4×13 (56), 5×10 (54), **6×8 (52, closest to 7×8)** and 6×6 (40). The released **7×8 needs 60**.
- The design is a single block (`encoded_tfim.py:3`), and two blocks would need ≥ 62. So 7×8 can't be encoded on H2 in any variant.
- A reduced lattice is planned only for Q3 (`handoff/05:28`, `report.tex:670-672`). For Q1, G3 still says "same lattice … against the released physical data" (`handoff/05:20,60`, `report.tex:665-667`).

**Ruling.**
- "Encoding is the only axis that varies" (`README.md:4-7`) **cannot hold against the released data**, because the lattice, the run, the calibration and the mitigation all differ.
- **Honest reframing:** encoded vs bare, at matched shots, on the same reduced torus (e.g. 6×8) on H2. The released 7×8 data become an external reference: quantitative at step 1 through an exact light-cone finite-size correction (shift ≈ few e-3), and a trend after that.

---

## 2. Final severities (R-Main's view after three rounds)

| finding | final | basis |
|---|---|---|
| R-Main-2: triangular h/\|J\| is 2, not 0.3 | **MAJOR** | settled by the raw QASM (R-Oracle) |
| R-Main-5: Q1 can't fit 7×8 encoded; no shot or estimator accounting | **MAJOR** | 3 reviewers; D12 |
| R-Main-R2-1 / R-Laptop-R2-1: defect density and P_out "describe the reference circuit" with the wrong sign | **MAJOR** | 2 independent reproductions; D3b confines it to the noiseless §8 statements |
| R-Main-1: `trotter.py` ordering ≠ circuits | **MAJOR → its real effect is R2-1 above** | Accepting R-Laptop's re-scoping: the noisy layers already use circuit order. The ordering bug's consequences are the doc statements in R2-1 plus the 30% floor shift (D3b). |
| R-Main-3: step-1 gap ~2σ, not 3σ; "size-independent" | MINOR–MAJOR | Defer to R-Oracle's D4 ruling. It is MAJOR if any doc claims significance. |
| R-Main-4: sign-blind circuit check | MINOR (MAJOR if the real QASM signs are non-gauge) | Defer to R-Oracle's D5 ruling. |
| R-Main-6: no `encoding=` (Windows breaks) | MINOR | 3 reviewers |
| R-Main-7, -8, -10, -12; the -9 remnant; -11 (a, b, c, e, f) | MINOR | as confirmed in Round 2. "One early point" becomes 7 cells (D7). |
| R-Oracle-1 | MINOR | the docs already say "first order" |
| R-Oracle-2 | **REFUTED** | 2 independent Monte Carlo checks |
| R-Oracle-3 | MINOR | the true matched-lattice range is 6.6–8.6× (R-Oracle confirms in D9) |
| R-Oracle-4, -5 | MINOR | for -5 use t / bootstrap intervals for Z2, Wilson for acceptance |
| R-Laptop-1 | MINOR | the guard works; add the injection test (R-Laptop's D1) |
| R-Laptop-2 | **REFUTED** as a significance claim | both drifts are resolved (D3b confirms the drift magnitudes); only a doc nit remains |
| R-Laptop-3 | MINOR / platform-specific | the slow call is `spectral_gaps` |
| R-Laptop-4, -5, -6; R-Laptop-R2-2; R-Oracle-R2-1 | MINOR | |

---

## 3. Bottom line

**Is the code correct?** Yes. Every quantity re-derived from independent code across three platforms matched, and every reproduction that ran matched its committed data file. No fabricated numbers were found.

**Do the main conclusions hold?**
- **Q4, Iceberg recommended: SUPPORTED.**
  - Distances, η* = 0.25 and the first-order accounting were all verified; Monte Carlo agrees to ≤ 7%.
  - The d ≥ 3 codes cost even more two-qubit gates than stated (6.6–8.6× instead of 3–7×), which strengthens the conclusion.
  - Caveat: η* comes from the degenerate 2×2 ring (R-Oracle's D10).
- **Q1, encoding helps at η ≈ 0.05: SUPPORTED AS A PREDICTION, BUT THE TEST DESIGN MUST CHANGE.**
  - The arithmetic is right, and the result is conditional on randomized compiling, which isn't built yet.
  - The head-to-head against the released 7×8 data is impossible on H2. It must become an encoded-vs-bare run at 6×8 or smaller.
- **Q2, triangular correlations 3–5× weaker: NUMERICALLY CORRECT, BUT NOT ANCHORED TO THE EXPERIMENT.** The reference uses h/|J| = 2, while the study is at 0.3.
- **Q3, thermalization: INTERNALLY SOUND, BUT IT DOES NOT DESCRIBE QUENCH4.**
  - The relaxation, MCMC, noisy drift and Gauss gains survive the ordering fix.
  - The noiseless defect-density and P_out "Trotter inflation" statements have the wrong sign for the circuit.
  - The whole h ≤ 0.5 framing is not the published h/|J| = 2 experiment (R-Laptop's D11).
- **Gauss law as mitigation: SUPPORTED as "modest yes for bit-flip-type noise".** The floor is ≈ 0.009 in circuit order, not 0.013.

**Ready for hardware as-is? No. Must fix first, in order:**
1. **Decide and document the triangular regime.**
   - Either rerun Q2/Q3/Gauss at h/|J| = 2 in circuit order,
   - or state explicitly that they study a different, frustrated regime chosen on purpose, not the reference experiment.
   - Then fix `config.py` and every doc that says "0.3 as in the reference".
2. **Re-scope Q1.**
   - Make it encoded vs bare at matched shots on one reduced torus (e.g. 6×8).
   - Add n_shots, n_accepted and estimator-class fields to `compare.Series`.
   - Update README, handoff/05 G3 and the report.
3. **Use circuit order (or report both orders) for every number that claims to describe the H2 circuit.**
   - Add a circuit-order option to `src/trotter.py`.
   - Fix `q3_thermalization.md:234-243`, `findings_vs_questions.md:41` and `gauss_law_dimers.md:130`, and the 0.013 floor.
   - Add a regression test.
4. **Make `verify_circuits` sign-aware,** checking signed angles against the gauge set, so a wrong-sign circuit aborts before any hardware run.
5. **Build randomized compiling.** The "encoding helps" prediction depends on it.

Everything else (encoding=, stale counts, the n=5 error bars, test gaps, wording such as "one early point", "13×" and "3–5×") is cleanup that can follow.
