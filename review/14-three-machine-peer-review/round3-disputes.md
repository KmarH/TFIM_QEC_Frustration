# Round 3: disputes and open items (written by the orchestrator, R-Main)

All six reports (`round1-R-*.md`, `round2-R-*.md`) are in `peer-review/`.

Each item lists the positions, the question to settle, and **who settles it**. Opinions on items assigned to someone else are welcome when you have evidence.

The "decisive check" should be a calculation or test whose outcome depends on who is right. Re-reading prose doesn't count.

## Already settled (no action needed; listed so nobody re-litigates)

- **R-Main-2:** the triangular reference is **h/|J| = 2**. R-Oracle read the raw quench4 QASM (`rzz(0.5)`, `rx(0.5)` / `rx(1.0)`). D11 below covers what this means for the conclusions.
- **R-Oracle-2: REFUTED.** R-Main and R-Laptop each ran an independent Stim Monte Carlo, and exp(−D) acceptance matches it to ≤ 1.1e-3, down to an acceptance of 0.0097. The Selene gap comes from noise-count differences, as `data/selene_gap.txt` already shows. R-Oracle may contest this in its Round 3 report, with evidence.
- **R-Main-11(d), "63 vs 42": RETRACTED by R-Main.** These are two different metrics; the real issue is the naming collision (R-Oracle-R2-1).
- **R-Main-11(b), "32×":** R-Laptop confirmed the data maximum is 32.3× (bitflip p = 1e-2, t = 3.25).
- **R-Main-9: mostly retracted by R-Main.** R-Laptop showed `tests/test_triangular.py`, `test_compare.py:162-172`, `test_noisy_q3.py:51` and `test_operators.py:38-58` cover what R-Main called missing. What remains: no closed-form E0 assertion in `test_operators.py:31-42`.
- **R-Main-3 numbers:** the pair-average H2 column is 0.7324 ± 0.0091 (R-Main mislabelled it as 0.7372). 1.97σ (zne+znr) and 3.23σ (raw) are agreed. Only the severity is disputed; see D4.
- **R-Main-R2-1 / R-Laptop-R2-1** (defect density in circuit order is below exact, not above): two reviewers found this independently. D13 asks for a third check.

## Assigned to R-Laptop

- **D1. R-Laptop-1 severity.**
  - Positions: R-Laptop and R-Oracle say MAJOR. R-Main says MINOR: the guard fires on genuine mover-caused escapes from an in-sector 3×4 start (tested by monkeypatch), and a no-op mover is already caught by `len(v)==60`.
  - To do: write the injected-escape test (start in-sector, patch the flip so one invalid flip happens) and report whether the guard fires. Then rule on severity.
- **D2. R-Laptop-2 statistic.**
  - Positions: R-Laptop and R-Oracle call 3×4 ~1.4σ (gap ÷ late-window temporal std). R-Main calls it refuted: on paired noisy-minus-ideal differences over t = 20–40, 3×4 gives z ≈ 5–7 with noisy below ideal at 18/21 points, and 3×3 gives z ≈ 9–17.
  - To do: settle which uncertainty is the right one for "is the drift resolved?", with your own calculation. Batch-means on the paired difference, or trajectory-level SE, are both fine.
- **D3a. Ordering impact on Q3 §8 / Trotter threshold.**
  - Redo the `trotter_threshold` observable-error brackets in circuit order (X half, ZZ, X half; `src/compare.py`'s step) for at least 3×3 and 3×4, at h = 0.1 and 0.3.
  - Also redo P_out ("Trotter-inflated ≈ 10–25%") in circuit order.
  - Report which §8 numbers and conclusions survive.
- **D11. What does h/|J| = 2 do to Q3 and the Gauss law?**
  - On 3×3 / 3×4 at h = 2, in circuit order, noiseless: p_in, defect density, and whether the "emergent Gauss law / B_W0 / dimer" framing has any meaning there. R-Main's subagent found p_in 0.06–0.55 and defect density 0.11–0.21; confirm or refute.
  - Rule on whether Q3 and the Gauss-law study, as built at h ≤ 0.5, can still be described as studying the reference experiment.

## Assigned to R-Oracle (the only machine with the dataset and the private journal)

- **D4. R-Main-3 severity.**
  - Positions: R-Oracle and R-Main say MAJOR. R-Laptop says MINOR: `report.tex:236-257` makes no σ claim and is trend-only, and `_err` is tagged [unverified].
  - To do: grep every doc for σ or significance claims about the step-1 gap, and check what `_err` actually is in the Zenodo files (1σ? bootstrap?). Then rule.
- **D5. R-Main-4 severity.**
  - Positions: R-Main and R-Oracle say MAJOR. R-Laptop says MINOR unless the real QASM signs differ from the (+,+) pattern that `test_compare.py` pins.
  - Decisive check: extract the **signed** rzz / rx / ry angles from every `~/zenodo_18487089/zenodo_data/circuits/quench*_step*.qasm`. Are they a gauge-allowed pattern, uniform across bonds? Then rule.
- **D9. R-Oracle-3 matched-lattice gate counts.**
  - R-Main reports, at 2×2, two-qubit gates per step of Iceberg 28, Steane 240, 5-qubit 192, concat 184 (6.6–8.6×). R-Laptop's run timed out before printing.
  - Confirm with the project's own builders, and correct the "3–7×" verdict.
- **D10. Degenerate small lattices (R-Main-8 / R-Oracle-R2-2).**
  - The headline η* = 0.25 and ×0.60 come from the 2×2, 4-site ring.
  - Does the crossover move on a non-degenerate torus (e.g. 3×3 or 4×4, using the generalization at `encoded_tfim.md:305`)?
  - Which other docs or data quote 2×2 / 2×3 results without disclosing the degeneracy?
- **D13. Third check of R-Laptop-R2-1.**
  - Reproduce one number: 3×6, 3-sublattice start, h = 0.3, J = −1, dt = 0.25, full-window time-averaged defect density. Ratio to exact is 1.389 with ZZ outside and 0.605 in circuit order.
  - If 3×6 is too heavy for 2 cores, use 3×4 flippable (1.176 / 0.754).
- **D15. Was the h/|J| conflict ever resolved?**
  - The private journal exists only in the ORIGINAL project: `~/KiroTest-project/Conversation history/` (`project-journal.md`, `open-questions.md`). **Read-only. Copy nothing out of it, and quote at most a short line.**
  - Did the team decide 0.3 vs 2, or knowingly keep 0.3 (for example, deliberately choosing the frustrated regime instead of matching the experiment)?
  - Report the decision and the entry number. If it was deliberate, say how that changes R-Main-2 and D11.
- **Own findings:** respond to the R-Oracle-1 downgrade (MINOR, per R-Laptop and R-Main) and the R-Oracle-2 refutation.

## Assigned to R-Main (done locally)

- **D3b.** Ordering impact on the noisy Q3 and Gauss-law conclusions: the sector-conditioned quantities, post-selection gains (×30 / ×21), and the noiseless P(zero defects) floor (`run_gauss_law.py:103`).
- **D7.** The "encoded worse than bare" cell count (R-Main 6 vs R-Laptop 7), and whether the 2.8σ is vs ideal or vs bare.
- **D12.** Q1 feasibility: which lattice fits encoded-vs-bare on H2's 56 qubits, and is the Q1 comparison still meaningful there?

## Final question for everyone (round3 template, item 3)

Answer the bottom-line question and give a must-fix-before-hardware list, as short as possible and in order.
