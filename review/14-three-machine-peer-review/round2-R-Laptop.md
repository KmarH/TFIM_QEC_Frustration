# Round 2 — Cross-verification by R-Laptop

Reviewer: R-Laptop (Linux x86_64, Python 3.14.4, all pins installed unchanged — see Round 1 §1).
Method: three read-only verification sub-agents (physics, Q1 harness/docs, QEC). I re-checked every
surprising result myself, and re-ran the most consequential one, R-Laptop-R2-1, through a second
code path. Scratch code and logs are in `peer-review/scratch/r2/`. Nothing outside `peer-review/` was
modified (`git status`: only `?? peer-review/`).

---

## 1. Verdict table

### R-Main

| ID | Verdict | Evidence summary |
|---|---|---|
| R-Main-1 (Strang ordering) | **CONFIRMED, re-scoped. MAJOR stays, for a different reason** | I reproduced every number with independent code (`scratch/r2/physics/ordering.py`). 4×4 torus: Z2 max |Δ| over steps 1–8 is **0.2343**. 3×3 triangular, J=−1: NN ⟨ZZ⟩ |Δ| is **0.1746** at h=2 and **7.36e-3** at h=0.3, against errors vs exact of 3.24e-3 (circuit order) and 4.12e-3 (ZZ outside). Infidelity at dt=0.25, h=0.1 is **1.294e-4 / 3.289e-4**. The call sites are as cited (`mcmc_baseline.py:521`, `run_gauss_law.py:70,103`, `gauss_mitigation.py:43-49`, `trotter_threshold.py:182,261`). **Overstated:** Q3 and Gauss-law are self-contained classical studies, checked against exact evolution and MCMC and never against H2 data. Q1, the only paper comparison, already uses circuit order (`compare.py:225-246`). The ordering difference is acknowledged at `q1_compare.md:50`, `noisy_q3.py:10` and `q3_thermalization.md:263`. The two step operators are exactly unitarily conjugate, so their Floquet quasienergies (and hence the resonance *location*) agree. **Why MAJOR still holds:** the docs make an explicit claim that the ZZ-outside defect numbers "describe the reference experiment's circuit", and that claim is wrong in sign. See R-Laptop-R2-1. |
| R-Main-2 (h/\|J\| = 0.3 vs 2) | **CONFIRMED (MAJOR)** | Both sides are present as cited. 0.3 [established]: `report.tex:173-175`, `gauss_law_dimers.md:21-26`, `config.py:146-158,286-290`, `q3_thermalization.md:7`. 2: `research/05:152-171` (quench4 `rzz(0.5)`, `rx(0.5)`, "only one rzz/rx angle anywhere"), `handoff/03:45-46` ("WRONG; use 2"). `research/04` contradicts itself: lines 136-138 call 0.3 "confirmed in … §V", while lines 140-142 say the §V body was never read. Nothing in `docs/`, `review/` or `handoff/plan.md` reconciles them. I could not read the QASM myself (Zenodo is not on this host). Whether a later journal entry resolved it is unknown, because the journal is not in the repo (R-Laptop-R2-2). |
| R-Main-3 (step-1 gap) | **CONFIRMED, SEVERITY CHANGE → MINOR** | Light-cone exact pair averages, from independent code: 4×4 **0.7653**, 4×5 **0.7610** (both equal the full state vector), 7×8 **0.7503**, full Z2 **0.7548**. Against H2 quench1 zne+znr: **1.97σ** at 7×8 vs 3.14σ at 4×5; raw_unamplified **3.23σ**. Quench2: H2 sits 1.36σ above. "≈3 bootstrap σ" is at `q1_compare.md:29`, and "size-independent" survives at `:57` even though `:81` says it was fixed. Why minor: `report.tex:236-257` makes no σ claim and presents the comparison as trend-only, and the 1σ reading of `_err` is already tagged [unverified]. |
| R-Main-4 (sign check) | **CONFIRMED, SEVERITY CHANGE → MINOR** | `run_compare.py:40-42,61-63` compares \|rzz\| and \|rx\|; only ry keeps its sign. Reproduced with 7×8 QASMs through the real `verify_circuits`. All of these pass with no abort: the published signs, `rzz(+) rx(−) ry(+)`, alternating rzz signs, and all signs flipped. Literal replay shows the non-gauge pattern shifting Z2 by up to 0.548. So `report.tex:232-233` and `q1_compare.md:44` overstate the guard. Why minor: the only independent record of the real files (`research/05:152-153`) gives the positive (+,+) pattern that `test_compare.py:162-172` pins. The guard is weak, but nothing shows a wrong comparison. It becomes MAJOR only if the real QASM signs turn out to differ. |
| R-Main-5 (Q1 can't fit 7×8 encoded) | **CONFIRMED (MAJOR)** | Iceberg uses k+2 code qubits (`qec/iceberg.py:4,68-69`) plus a syndrome ancilla and a flag (`encoded_tfim.py:5`), so 7×8 needs 60 > 56. The same arithmetic is done for Q3 at 9×6 (`report.tex:559,647,671`) but never for Q1. `README.md:4-7` and `report.tex:86-89,123-126` keep the "single varied axis vs released data" framing. `Series` (`compare.py:54-63`) has no shots, acceptance or estimator fields. The ZNE/ZNR vs post-selection estimator mismatch is never reconciled. |
| R-Main-6 (no `encoding=`) | **CONFIRMED (MINOR). A real project bug; only its *trigger* is platform-specific** | Reproduced on Linux by forcing cp1252 as the default text encoding (`scratch/r2/cp1252_plot.py`). The parsers return **silently** with garbled arrays, then `fig_size` crashes with the same `IndexError` at `plot_q3.py:314` that R-Main saw. 23 `open`/`read_text`/`write_text` calls in `src/`, `scripts/`, `main.py` and `config.py` lack `encoding=`; 0 have it. `data/q3_noisy.txt` has 84 non-ASCII lines. |
| R-Main-7 ("Néel" = stripes) | **CONFIRMED (MINOR, low impact)** | `backends.py:104-109` uses `site % 2`. On 4×4 that gives ΣZZ over the 32 bonds = 0 (Néel would be −32). Only `test_observables.py:33` uses it, and any product state works there. No script or config uses "neel". |
| R-Main-8 (length-2 periodic = open) | **CONFIRMED (MINOR); "silently" is too strong** | `square_bonds(2,3,'periodic')` gives coordination 3 (9 bonds), and triangular 2×3 gives 5. The skip is deliberate and documented in `lattice.py:33-37`. `encoded_tfim.md:305` notes 2×2 is degenerate, but `encoded_tfim.md:15` still calls 2×3 a "periodic square lattice". Cross-link: the headline η* = 0.25 and ×0.60 numbers are computed on this 4-site ring. |
| R-Main-9 (core test gaps) | **PARTLY (mostly refuted)** | Holds: `test_operators.py:31-42` never asserts E0 = −√(J²+4h²), and the single-spin tests are even in h. Refuted: "no triangular test" (`tests/test_triangular.py` covers bond count, coordination 6, frustration, ED, and Trotter vs expm). Also refuted: "no test of periodic/triangular Trotter or circuit ordering". `test_compare.py:162-172` replays the circuit order on a 3×3 torus, `test_noisy_q3.py:51` compares the two orderings, and `test_trotter_threshold.py` runs periodic triangular 3×3 against exact evolution. The sign of h is pinned by `test_operators.py:38-58` and `test_compare.py:172`. |
| R-Main-10 (Q1 fixture circular) | **CONFIRMED (MINOR)** | The fixture README says it "mirrors … research/05", the same spec the loader implements. No test imports `run_compare` (`is_synthetic`, the trusted gate, `verify_circuits`). The fixture QASM is at `tests/fixtures/zenodo_mini/quench9_step1.qasm`, not under `circuits/`. The ZZnn and dimercorr loaders have only ever run on the fixture. |
| R-Main-11 (doc ≠ data) | **PARTLY** | (a) "one early point": confirmed in substance, with different numbers. I count **7** distinct (p2, step) cells (4 local-sim, 4 Selene, one shared), including steps 4–5, so they are not all early. The "2.8σ" is encoded vs *ideal*; encoded minus bare is ≤ 1.0σ in every cell. (b) "up to 13× worse": confirmed, the data max is **32.3×** (bitflip 1e-2, t = 3.25). (c) "3–5×": confirmed, the data gives 2.9–3.9× at 2×3, p2 = 1e-3. (d) "63 vs 42": **REFUTED**. They count different things: 63 distinct undetected Paulis (21 gates × 3) vs 42 mechanisms. Both are documented (`encoded_tfim.md:56,60`) and both reproduce. The cited `encoded_iceberg.txt:14` is a *measurement* row with 0 undetected. (e) slopes: confirmed, the data spans 1.97–2.04. (f) confirmed: 0.63, "\|⟨Z_i⟩\| 0.01–0.5" and "1.39–1.44" have no data file (0.78 does, `q1_compare.txt:12`). |
| R-Main-12 (stale docs) | **CONFIRMED (MINOR/trivial)** | `config.py:96-103` gives 413/1469/1871 MB, 5.5×; `stage1_validation.txt` gives 463/1543/1881, 5.7×. ED N=16/18 both report exactly 1543 MB = the statevector peak, because `ru_maxrss` is a process-lifetime peak (`validate_stage1.py:93,105,133,146-147`). `q1_compare.md:55` still says [inferred]. 169 vs 231 tests: agrees with my R-Laptop-4. |

### R-Oracle

| ID | Verdict | Evidence summary |
|---|---|---|
| R-Oracle-1 (DEM numbers not called first-order) | **PARTLY, SEVERITY CHANGE → MINOR** | The method is indeed deterministic (`encoded_codes.py:647-700`, `approximate_disjoint_errors=True`). But "nowhere stated" is wrong: "first order"/"first-order" appears 13× in `encoded_tfim.md`, including the B3 header "[Stim, first order]" (`:164`) and "first-order acceptance" (`:172,174`), 6× in `report.tex` and 2× in `findings_vs_questions.md`. `data/noise_sensitivity.txt:1` says "Stim first-order accounting". What survives: the [measured] tag is not glossed as "closed-form, no sampling error". |
| R-Oracle-2 (first-order breaks down at low acceptance; explains 5–15 pt Selene gap) | **REFUTED** | Exact Stim Monte Carlo (100k shots per case, `scratch/r2/qec/mc_vs_dem.py`, `mc_out.txt`) against the project's exp(−D) acceptance: Iceberg 2×2 1e-3 **0.8751 vs 0.8755±0.0007**; concat 2×2 3e-3 **0.1050 vs 0.1062±0.0007**; Steane 2×3 3e-3 (the 0.010 R-Oracle singles out) **0.0097 vs 0.0097±0.0002**; 5-qubit 2×3 3e-3 **0.0229 vs 0.0232±0.0003**. exp(−D) equals ∏(1−p_i) to 4 digits; it is not a 1−D truncation, so it does not degrade at low acceptance. The Selene gap is already diagnosed in the project's own `data/selene_gap.txt` §1–4. There, exp(−D) 0.6700 vs Stim-sampled 0.6730, labelled "neither". The gap comes from Selene charging p_1q on ×3.85 more native 1q ops (rxy+rz) and more init events. Stim with native-matched counts gives 0.834 vs Selene 0.807±0.009, closing most of it. Residual point (minor, informational): the first-order *undetected* rate sits 2–11% below the sampled P(logical flip \| accept) (Iceberg 6.00e-3 vs 6.28e-3; Steane 2×3 2.10e-2 vs 2.27e-2; concat 2×2 3e-3 1.40e-2 vs 1.56e-2). The shift is similar across codes, so the ranking is unaffected. |
| R-Oracle-3 (3–7× gates mixes lattices) | **CONFIRMED (MINOR)** | `encoded_tfim.md:155-162`: Iceberg 2×2 has 28 2q ops/step and concat 2×2 has 184, while Steane and 5-qubit are given at 1×2 (108, 84). The "3–7×" headline at `:181,218`, `findings_vs_questions.md:53` and `report.tex:366` does not say the lattices differ. I agree it is probably a lower bound for Steane/5-qubit. |
| R-Oracle-4 (`python -I main.py`) | **CONFIRMED (MINOR)** | On this host: `-I main.py` raises `ModuleNotFoundError: No module named 'config'`; `python main.py` runs. |
| R-Oracle-5 (Gaussian SE at n = 5) | **CONFIRMED (MINOR)** | `run_encoded_codes.py:153-155` uses `std(ddof=1)/√n` whenever n ≥ 2. `data/encoded_codes.txt:63` has concat 2×2 3e-3 step 3 with acceptance 0.033 of n=150, i.e. 5 kept, giving Z2 0.5500±0.1837. That row is quoted at `encoded_tfim.md:198`. The acceptance ± is also a Wald interval (`:164`), which is weak at p = 0.033. |
| R-Oracle-6 (distances 2 / 4) | **CONFIRMED** (no conflict) | Consistent with R-Main's re-derivation and with the `test_qec.py` oracle. I did not re-run my own brute force. |
| R-Oracle-7 (η* = 0.25) | **CONFIRMED** | Checked against `data/noise_sensitivity.txt` rows. 12·6e-4·(0.2+0.8·0.05) = 1.728e-3 (table 1.73e-3); η=0.5 gives 4.32e-3 (table 4.32e-3); bare = 4.8·p2 = 2.88e-3, which is 4 ZZ·p2 + 8 X·p1 with p1 = 0.1·p2. The crossover is exactly 0.25. R-Main independently gets 0.25 / 0.357 / 0.4375 / 0.55, so the reviewers agree. Caveat: this is the 4-site ring (R-Main-8). |
| R-Oracle-8 (tests discriminating) | **CONFIRMED** for the files I read; consistent with my Round 1 view of my own area. | — |

---

## 2. My own Round 1 findings: defences and qualifications

- **R-Laptop-1 to R-Laptop-6:** no other reviewer contradicts any of them. R-Laptop-4 (stale 169-test
  count) is independently confirmed by R-Oracle and R-Main. All three of us measured 231 tests.
- **Qualification of my Round 1 §3.2 and §4 ("Q3 area is sound").** §3.2 confirmed the doc's
  dt = 0.25 Floquet excess for the stripe (1.088×), but that factor belongs to the project's
  ZZ-outside splitting. In circuit order the stripe defect density is **0.845×** exact, not 1.08×
  (see R-Laptop-R2-1). The arithmetic I re-derived is correct; the doc's attribution of it to the
  reference circuit is not. I missed this in Round 1 even though it sits in my focus area. R-Main-1
  pointed at the ordering, but neither of us drew the consequence in Round 1.
- **Round 1 §3.3 (Trotter threshold):** my reproduction of `data/trotter_threshold.txt` stands. But
  those brackets use the ZZ-outside frame. The resonance location is ordering-invariant, because the
  quasienergies are identical. The observable-error thresholds can move, because the infidelity at
  dt = 0.25, h = 0.1 is 2.5× larger in circuit order. I have not re-run the threshold scan in
  circuit order.

---

## 3. New findings (gaps)

### R-Laptop-R2-1 — MAJOR — "Trotter-inflated defect density describes the reference circuit" is wrong in sign: the circuit order *deflates* it
**Location:** `docs/q3_thermalization.md:237-243` ("Consequence: absolute defect densities quoted at
dt = 0.25 describe the reference experiment's **circuit**"), `docs/findings_vs_questions.md:41`
("circuit, not continuous-time"), `docs/gauss_law_dimers.md:130` (stripe "about 10% higher at the
reference's dt = 0.25").
**Evidence.** I computed the full-window (T = 20) time-averaged defect density per triangle at
J = −1, dt = 0.25 using the project's own primitives (`scratch/r2/defect_order_projectcode.py`,
log alongside). "ZZout" is `src.trotter.trotter2_step`; "circuit" is the X-half/ZZ/X-half order of
`src.compare.circuit_trotter_states`; "exact" is `expm_multiply` of `src.operators.tfim_hamiltonian`.
The sub-agent's from-scratch code (`scratch/r2/physics/defects.py`) gives the same values.

| cluster, start | h | ZZout / exact (project, doc) | circuit order / exact |
|---|---|---|---|
| 3×6, 3-sublattice | 0.3 | **1.389** (doc "≈40%", 1.39–1.43) | **0.605** |
| 3×6, 3-sublattice | 0.1 | 1.419 | 0.574 |
| 3×4, flippable | 0.3 | 1.176 (doc 1.16–1.19) | 0.754 |
| 3×4, stripe | 0.3 | 1.082 (doc 1.08–1.10) | 0.845 |
| 3×3, 3-sublattice | 0.3 | 1.483 | 0.541 |

The ZZout column reproduces every doc figure, so the code is right. But the doc's Floquet-factor
explanation applies to the ZZ-outside frame only. In the reference circuit's frame, populations are
read after an X half-rotation, and the defect density comes out 15–45% *below* exact, not 8–40%
above. The `noisy_q3`/Gauss-law conclusions that use sector-conditioned quantities are probably less
affected, but I have not checked that. The ordering dependence of P_out ("Trotter-inflated ≈10–25%")
and of the noiseless P(zero defects) floor (`run_gauss_law.py:103`) is also unchecked.
**Fix:** rerun the §8 and `gauss_law_dimers` defect and P_out numbers with circuit order (`compare.py`'s step).
Either quote both frames, or drop "describes the reference circuit".

### R-Laptop-R2-2 — MINOR — the decision record that CLAUDE.md and the docs depend on is not in the repository
`CLAUDE.md` says to read `Conversation history/project-journal.md` and `open-questions.md` first in
every session. The docs and handoffs cite decisions stored only there ("D-RC (journal Entry 24)",
"★ FLAG-0", "open-questions R-7"; `handoff/plan.md:390`, `handoff/11`). But `.gitignore` excludes
`Conversation history/`, `git ls-files` shows it was never tracked, and it is absent from this
checkout. Consequence: a reader of the public repo cannot check whether the R-Main-2 h/|J| conflict,
or any other open item, was resolved later. **Fix:** commit a sanitised decisions log, or move the
decisions into `handoff/plan.md`.

(Checked and not raised: randomized compiling, which the "encoding helps" GO depends on, is not
implemented in `src/` (no twirling code). But this is disclosed as "not built yet" in
`handoff/11:52-53` and stated as a condition in `report.tex:101,630`, so it is a known open item,
not a gap.)

---

## 4. Cross-checked numbers where reviewers differ

| quantity | R-Main | R-Oracle | R-Laptop (this round) |
|---|---|---|---|
| test count | 231 (229+2 Windows fails) | 231 | 231 |
| η crossovers | 0.25 / 0.357 / 0.4375 / 0.55 | 0.25 | 0.25 (from data rows); the others are not re-derived |
| "encoded worse than bare" cells | 6, up to 2.8σ | — | **7**; 2.8σ is vs ideal; encoded−bare ≤ 1.0σ |
| step-1 7×8 pair average | 0.7503 | — | 0.7503 (independent light cone) |
| first-order acceptance validity | — | "not trusted at low acc." | matches exact MC to ≤ 1.1e-3 down to acc = 0.0097 |

---

## 5. Overall assessment

The Round 1 reports hold up well. Their numerical re-derivations agree across all three platforms
(aarch64/3.12, x86_64/3.14, Windows/3.13), and every reproduction that finished matched. Of the 20
foreign findings:
- 13 are confirmed;
- 3 are confirmed with lowered severity (R-Main-3, R-Main-4, R-Oracle-1);
- 2 are partly right (R-Main-9, R-Main-11);
- 1 is confirmed but re-scoped (R-Main-1);
- 1 is refuted outright (R-Oracle-2: the exp(−D) acceptance is effectively exact, and the
  Selene gap is a noise-counting difference the project had already diagnosed);
- within R-Main-11, which counts as partly right, sub-row (d) is refuted.

The serious issues are about framing, not arithmetic:
- Q1's "single varied axis vs released data" design does not fit on H2 (R-Main-5).
- The triangular field is disputed inside the project (R-Main-2).
- The circuit-ordering issue turns out to matter most where the docs claim to describe the
  reference circuit: those defect-density statements have the wrong sign (R-Laptop-R2-1).

No fabricated numbers were found. The QEC accounting and the Q2/Q3 core computations are correct as
computed.
