# KiroTest: peer review final report

> **Addendum, 2026-10-15 — what has happened since.** This report is kept as written, as the
> record of the review. Since then the findings were applied (`handoff/plan.md` §24), and **the
> triangular h/|J| question this report calls open has been resolved — against this report's
> premise.** The paper's Figure 4(e) states "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)", so
> **h/|J| = 0.3 is correct and the project's triangular configuration does match the reference's
> §V.** The `h/|J| = 2` finding below is a correct reading of the released quench4 circuit files,
> but those files carry the reference's *square*-quench field and are not the experiment's
> circuits. See `DECISIONS.md` RESOLVED-1 and `handoff/plan.md` §25–26.
>
> So where this report treats h/|J| = 2 as the reference's triangular field, read it as the value
> the released circuits imply — not the experiment's. The review's *other* conclusions are
> unaffected, including the ordering sign error and the Q1 qubit-budget finding, and its
> measurements at h/|J| = 2 remain valid as calculations; they simply describe a regime the
> reference never ran. The two remaining open items, randomized compiling and the Q1 lattice
> implementation, are still open.

> **Final.** R-Laptop's machine became unreachable during Round 3, so R-Oracle took over its four disputes (D1, D2, D3a, D11) in a Round 3b. R-Laptop's own Round 3 was recovered afterwards and **agrees with R-Oracle's Round 3b on all four**, independently: D1 minor, D2 dismissed, D3a split the same way, D11 upheld. So those four rulings carry two independent verdicts each.
>
> R-Laptop's Round 3 adds two facts used below: Q2's 3–5× weakening **also holds at the reference field h/|J| = 2** (ratio 4.98 on the matched 4×4 pair), and the in-sector weight at h = 2 **falls with system size** (0.55 at N = 9, 0.11 at N = 12), so on the reference's 7×8 torus Gauss-law post-selection would keep an exponentially small fraction of shots even with no noise.

**Project:** TFIM with logical vs physical qubits, aimed at Quantinuum H2. Commit `a146bae`, from `~/KiroTest-project` on the Oracle VM.

**Reviewers:** each is an independent instance of Claude Code with its own subagents.

| reviewer | machine | Python |
|---|---|---|
| R-Oracle | Oracle Cloud VM, Linux aarch64 (the project's reference platform) | 3.12 |
| R-Laptop | home server, Linux x86_64 | 3.14 |
| R-Main | Windows 11 laptop; also the orchestrator | 3.13 |

**Process:**
- Round 1: independent reviews, each with a different focus area.
- Round 2: each reviewer verified every finding of the other two.
- Round 3: disputed points were assigned to one reviewer each and settled with decisive checks.
- Every reviewer worked on a disposable copy. No project file and no `data/` file was changed.

---

## 1. Verdict in one paragraph

**The code is correct; several claims about what it describes are not.**
- Across three platforms and roughly 40 independent re-derivations, every number checked against independent code matched. Every reproduction that ran matched its committed data file, often byte for byte. No fabricated number and no meaningless test was found.
- The serious problems are about framing, not arithmetic:
  - The triangular studies use a field (h/|J| = 0.3) that the published circuits don't use (they use 2), and nobody in the project noticed the conflict.
  - Some Q3 statements about "the reference circuit" have the wrong sign, because the code orders its gates differently from that circuit.
  - The Q1 head-to-head against the released 7×8 data cannot fit on H2.
- **Q4 (Iceberg recommended) is solid.** If anything it is understated.
- **Not ready for hardware as-is.** Section 5 lists five fixes, in order.

---

## 2. Running the project

| | R-Oracle (Linux aarch64, Py 3.12) | R-Laptop (Linux x86_64, Py 3.14) | R-Main (Windows, Py 3.13) |
|---|---|---|---|
| pinned requirements | all installed as pinned | all installed as pinned, with wheels on 3.14 | all installed as pinned |
| `pytest tests/` | **231 / 231** (125 s) | **231 / 231** (159 s) | **229 / 231** (241 s); both failures are the encoding bug (m1) |
| `main.py` | runs; **`python -I main.py` fails** (m2) | runs | runs |
| `plot_q3.py` | runs | runs | **crashes** unless run with `-X utf8` (m1) |
| reproduced `data/` files | noise_sensitivity, concat_d4 (exact); frustration_compare | frustration_correlations (every physics number bit-identical) | stage1_validation (all physics identical); concat_d4 (byte-identical) |

Most expensive data regenerations needed the fast, closed-form or seeded scripts. The Selene-executed rows (`encoded_codes.txt` §4–5, `encoded_iceberg.txt`) were not regenerated, because they take hours.

---

## 3. Findings, after three rounds

### MAJOR

**M1. The triangular "reference" field is unreconciled: 0.3 in the code and docs, 2 in the published circuits.**
- **What the code and docs say:**
  - `config.py:146-158,286-290`, `report.tex:173-175`, `gauss_law_dimers.md:21-26` and `q3_thermalization.md:7` all use h/|J| = 0.3, "matching arXiv:2503.20870 §V" [established].
  - The paper's prose was read twice, independently, and gave 0.3 (journal Entry 6; `research/04` addendum).
- **What the data says:**
  - R-Oracle read the **signed angles in all 80 released QASM files**. Quench4 (triangular) is `rzz(0.5)` / `rx(0.5)`, which means **h/|J| = 2**, the same as the square quenches.
  - `research/05` found this on 2026-10-07 and called 0.3 "an error", but that finding never reached the Gauss-law and Q3 configuration.
- **Never reconciled:** the private journal (read-only, D15) shows the two research threads never cross-checked each other. This was not a deliberate choice of regime.
- **Starting state also missing:** the released quench4 circuits prepare `ry(0)` on all 54 qubits with no `x` gates. So the published data doesn't say which winding sector the experiment started in.
- **Impact:**
  - All Q2, Q3 and Gauss-law work is at h ≤ 0.5. It cannot be called "matched to the reference experiment".
  - At h = 2 the study's framework stops being valid (D11, confirmed independently by R-Oracle and R-Main):
    - On a noiseless run in circuit order, the probability of staying in the sector drops to 0.13–0.63 **within a single Trotter step**, and the defect density is 5–17%.
    - The sector-ETH / H_QDM / B_W0 machinery is first-order in h/|J|, so it isn't a controlled approximation at h/|J| = 2.
    - So the h ≤ 0.5 work can't be relabelled as "the h = 2 experiment" just by changing a config value.
- **Confirmed by:** all three reviewers. The QASM was read directly on the Oracle VM.

**M2. Docs claim the time-step bias "describes the reference circuit", with the wrong sign.**
- **Location:** `src/trotter.py` puts ZZ outside each step; the published circuits put X outside. `src/compare.py` already has the circuit-order step.
- **Where the wrong claim is made:** `q3_thermalization.md:234-243`, `findings_vs_questions.md:41` and `gauss_law_dimers.md:130` say the dt = 0.25 defect-density and P_out inflation "describes the reference experiment's circuit". Full-window defect density, ratio to exact:

| cluster | project's order | circuit's order |
|---|---|---|
| 3×6 | 1.39 | **0.60** |
| 3×4 | 1.18 | 0.75 |
| 3×3 | 1.48 | 0.54 |

  So the circuit actually *deflates* the defect density.
- **P_out has the same problem** (D3a). In circuit order it comes out **19–35% below** exact (3×3 and 3×4, h = 0.1 and 0.3), not "Trotter-inflated by 10–25%" as `q3_thermalization.md:234` says.
- **Confirmed by:** three independent reproductions, on three machines (D13).
- **What it does not affect** (D3b): the noisy-Q3 and Gauss-mitigation runs already used circuit order, so none of those conclusions changes sign. The only change there is magnitude: the noiseless post-selection floor is **≈ 0.009**, not the 0.013 quoted.
- **Survives:** §8's dt = 0.25 credibility brackets are unchanged in circuit order (D3a). Margins are 1.5–2.0×, the same or better than the docs; the two orderings share their quasienergies. So "dt = 0.25 is below the Trotter threshold at h ≤ 0.3" still holds.

**M3. The Q1 thesis can't be tested against the released data on H2.**
- **What it claims:** "encoding is the only axis that varies" against the released 7×8 data (`README.md:4-7`; `report.tex:86-89,123-126,665-667`; `handoff/05` G3).
- **Why it can't fit:**
  - Iceberg needs k + 4 physical qubits with k even (`encoded_tfim.py:5-6,58-59,64`), so 7×8 needs **60 > 56**.
  - The design is one block, and two blocks would need ≥ 62.
  - The largest fits are 4×13 (56), 5×10 (54), **6×8 (52)** and 6×6 (40). The project already plans a reduced lattice for Q3, but not for Q1.
- **Other gaps:**
  - The released data are ZNE+ZNR mitigated; a logical arm is post-selected.
  - `compare.Series` (`compare.py:53-63`) has no fields for shots, acceptance or estimator type.
- **Confirmed by:** all three reviewers (D12).

**Hardware-gating, already disclosed:** randomized compiling isn't implemented, and the "encoding helps" GO rests on it (`report.tex:101`, `handoff/11`).

### MINOR

**Severities settled by the disputes:**

| ID | finding | settled by |
|---|---|---|
| m3 | The step-1 gap is ≈ **2.0σ** (zne+znr) / 3.2σ (raw) against the exact N = 56 light-cone value 0.7503, not "≈3σ". "Size-independent" remains at `q1_compare.md:57`. It is internal-doc only, and `report.tex` makes no σ claim. | D4 |
| m4 | `verify_circuits` compares only magnitudes, so a non-gauge sign pattern passes. It is **dormant**: all 80 real QASMs have uniform signs. `report.tex:231-233` overstates the check. It came from an earlier fix (`q1_compare.md:76`). | D5 |
| m5 | "3–7× more two-qubit gates" mixes lattice sizes. At a matched 2×2: Iceberg 28, Steane 240, 5-qubit 192, concat 184, so **6.6–8.6×**. This favours Iceberg even more. | D9 |
| m6 | η* = 0.25 and ×0.60 come from the degenerate 2×2 ring. The 2×3 gives 0.36 / 0.49 and a true 4×4 torus 0.44 / 0.44. So **2×2 is the most pessimistic case**, and the caveat is disclosed in every conclusion document. | D10 |
| m7 | "One early point" where encoded is worse than bare: it is actually **7 of 24 cells**, including steps 4–5, though never more than 1σ in encoded−bare. "Within ≈2σ" is fair for step 6. | D7 |
| m8 | `[measured]` tags on first-order Stim numbers don't say "closed-form, no sampling error". The method itself is fine (see R2 below). | Round 2 |

**Other confirmed issues:**
- **m1. Windows breaks.** No file I/O passes `encoding=`: 23 calls, 0 with it. Windows fails 2 tests and `plot_q3.py` (`plot_q3.py:52`); writers produce cp1252 files.
- **m2. `python -I main.py` fails.** `main.py` has no `sys.path` insert.
- **m9. Gaussian error bar on 5 shots** (`run_encoded_codes.py:153-155`): "0.55 ± 0.18" should be a t or bootstrap interval for Z2, and Wilson for acceptance.
- **m10. The "Néel" state is column stripes** when Lx is even (`backends.py:104-109`). Low impact.
- **m11. Q1 test fixture problems.** The fixture is circular (written from the same spec as the loader). `run_compare.py` is untested (`is_synthetic`, the trusted gate, `verify_circuits`). The fixture QASM isn't under `circuits/`.
- **m12. Doc and data mismatches:**
  - "up to 13×" vs a data maximum of **32×**
  - "3–5×" acceptance cost vs 2.9–3.9× (2×3 only; 1.9–2.3× at 2×2)
  - slopes "2.00–2.04" vs 1.97–2.04
  - the Iceberg+Gauss cost is quoted against different baselines in different places
  - 0.63, |⟨Z_i⟩| 0.01–0.5 and 1.39–1.44 have no data file
- **m13. Stale numbers:**
  - memory figures in `config.py:96-103`; ED maxRSS is really the statevector peak
  - "169 tests" in CLAUDE.md (really 231)
  - an [inferred] tag at `q1_compare.md:55`
  - `encoded_tfim.md:202` still blames the first-order approximation for the Selene gap, which the same file at :314 rules out
- **m14. Test gaps:**
  - The sector-escape guard test only uses an invalid start state (R-Laptop-1). **MINOR** (D1): with an injected invalid flip from an in-sector 3×4 start, the guard fires, as shown independently by R-Oracle and R-Main. Add that injection as the real regression test.
  - `Targets.postselect` has no direct test.
  - There is no closed-form E0 assertion in `test_operators.py:31-42`.
- **m15. ARPACK slowness:** `spectral_gaps` (`frustration.py:90-96`) is 2.7–5.4× slower off-reference near degeneracy. Results are identical.
- **m16. Naming collision:** "63 distinct undetected Paulis" vs "42 undetected-logical mechanisms" are two correct metrics with confusingly similar names.
- **m17. Decisions live outside the repo.** The decision record (`Conversation history/`) is gitignored. The h/|J| question (M1) could only be investigated on the one machine that has it.
- **m18. `--skip-exec` truncates data.** `run_encoded_codes.py --skip-exec` truncates `data/encoded_codes.txt` §5.
- **m19. Small-lattice wording.** A periodic side of length 2 has degenerate bonds (tested and physically forced). `encoded_tfim.md:15` still calls 2×3 a "periodic square lattice".

### REFUTED (raised by a reviewer, then disproved)
- **R-Oracle-2, "first-order DEM breaks down at low acceptance".** Three independent Stim Monte Carlo runs agree with exp(−D) to ≤ 1.1e-3, even at 1% acceptance (Steane 2×3: 0.0097 vs 0.0096 ± 0.0002). The Selene gap is a noise-counting difference, already diagnosed in `data/selene_gap.txt`.
- **R-Main-11(d), "63 vs 42"** is not a mismatch (m16).
- **R-Main-9, "no triangular or circuit-order tests"** is mostly wrong: `test_triangular.py`, `test_compare.py:162-172` and `test_noisy_q3.py:51` exist.
- **R-Laptop-2, "the 3×4 noise drift is only 1.4σ"** divided by the curve's variation over time, which is not the uncertainty of the mean (D2).
  - Batch-means SE gives **z ≈ 11 (3×4) and 22 (3×3)**, with noisy below ideal in **20 of 20** batches.
  - So "noise can mimic thermalization" is clearly resolved at both sizes. A doc nit remains: quote a σ.

---

## 4. The project's questions: are the conclusions supported?

| question | verdict |
|---|---|
| **Q4: Iceberg recommended, d ≥ 3 buys only about 1.2×** | **Supported, and understated.** Distances, η* and the first-order accounting were all verified independently several times. The real gate penalty for d ≥ 3 is 6.6–8.6×, and the 2×2 headline lattice is the least favourable to Iceberg. |
| **Q1: encoding helps at η ≈ 0.05** | **Supported as a conditional classical prediction only.** The arithmetic is right. But η is an inferred prior, randomized compiling isn't built, and the planned test can't fit on H2 (M3). Re-scope it to encoded vs bare on about 6×8. |
| **Q2: triangular nearest-neighbour correlations 3–5× weaker** | **Supported.** Bit-identical from independent code, and the ratio also holds at the reference field h/|J| = 2 (4.98 on the matched 4×4 pair), so it survives M1 either way. It should be labelled as a ground-state exact-diagonalization result, not quench dynamics. |
| **Q3: thermalization** | **Internally sound, but not yet a description of the reference experiment.** The relaxation, MCMC baseline, noisy drift and Gauss gains survive the ordering fix. §8's dt = 0.25 threshold margins also survive. But §8's defect-density and P_out bias statements have the wrong sign for the circuit (M2). And at h/|J| = 2 the h ≤ 0.5 framework isn't valid, with no starting sector given in the released circuits (M1). |
| **Gauss law as mitigation** | **Supported as "a modest yes for bit-flip-type noise; no for dephasing and self-mitigation"**, at h ≤ 0.5. The noiseless floor is about 0.009 in circuit order, not 0.013. It inherits M1. |

---

## 5. Must fix before hardware (in order)

1. **Decide the triangular regime (M1).** This is a project-lead decision.
   - Either relabel Q2/Q3/Gauss as a deliberately chosen, self-contained study of the h ≤ 0.5 frustrated regime, and drop "matching §V" everywhere,
   - or build a genuine h/|J| = 2 study. That needs different machinery, because the first-order sector theory fails there (D11), and a starting state chosen on other grounds, because the released circuits give none.
   - Checking the paper's PDF or supplement for a second triangular run would settle which.
   - Then fix `config.py` and the docs, and record the decision in the repo (m17).
2. **Fix the ordering sign error (M2).**
   - Add a circuit-order option to `src/trotter.py` with a regression test.
   - Rerun §8's defect-density and P_out numbers and the Gauss floor in circuit order. The threshold brackets can stay.
   - Correct every "describes the reference circuit" statement.
3. **Re-scope Q1 (M3).**
   - Encoded vs bare at matched shots on one reduced torus that fits H2 (e.g. 6×8).
   - The released 7×8 data become an external reference: quantitative at step 1 via a light-cone finite-size correction, a trend after that.
   - Add shot, acceptance and estimator fields to `compare.Series`.
   - Update README, handoff/05 G3 and the report.
4. **Build randomized compiling.** The "encoding helps" GO depends on it.
5. **Make `verify_circuits` sign-aware (m4).** Cheap, and it stops a wrong-sign circuit from reaching hardware.

Everything else is cleanup that can follow: m1–m3 and m5–m19.

---

## 6. Where the evidence is

- **Reports**, all in [`review/14-three-machine-peer-review/`](14-three-machine-peer-review/):
  - `round{1,2,3}-R-{Oracle,Laptop,Main}.md` — the nine per-reviewer, per-round reports.
  - `round3b-R-Oracle.md` — R-Oracle's cover for R-Laptop's Round 3 disputes, written while that machine was off the network and before its own Round 3 was recovered. The two agree.
  - `round3-disputes.md` — the orchestrator's assignment of every disagreement to a reviewer, with the positions on each.
- **Scratch code and logs:** not committed. Each reviewer's re-derivations lived in a disposable review clone on its own machine (`~/KiroTest-review/peer-review/scratch/`). The numbers they produced are quoted in the reports above; `data/trotter_order_compare.txt` is the one result promoted into the repository, because it is the evidence for the ordering fix.
- **What was fixed in response:** see `DECISIONS.md` and the pull request that applied these findings.
- **Reviewer agreement:** every MAJOR finding was confirmed by all three reviewers. Every severity change and refutation above was made by at least two reviewers on independent evidence.
