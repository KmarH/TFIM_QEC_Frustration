# Round 3: Adjudication and final verdict by R-Laptop

- **Reviewer:** R-Laptop, on Linux x86_64 with Python 3.14.4 and the existing `.venv`. All pins installed unchanged (Round 1 §1), so there are no version deviations.
- **Scratch work:** `peer-review/scratch/r3/`. Every number below comes from a script and log there.
- **Nothing outside `peer-review/` was modified.**
- **Code paths:** each check uses the project's own primitives. Where a result carries a ruling, a second, independent code path cross-checks it.

---

## 1. Rulings on the disputes assigned to me

### D1. R-Laptop-1 severity: UPHELD as a finding, final severity MINOR (I withdraw MAJOR)

**Decisive check** (`scratch/r3/d1_injected_escape.py`, `.log`). The run starts from the genuine in-sector 3×4 "flippable" configuration (0 defects, 4 flippable sites; 4 chains, 200 sweeps). I then broke the mover in three ways:

| mover | guard result |
|---|---|
| unpatched | no raise (correct) |
| A: hexagon-neighbour table off by one site (`ev.hex` rolled by 1) | **RAISED** "left the defect-free W0 sector" |
| B: rare invalid flips, 1e-3 per attempt (patched flip mask) | **RAISED** |
| B: rare invalid flips, 1e-4 per attempt | **RAISED** |

I also ran an exhaustive structural check. From each of the 60 states in the W0 sector I flipped every non-flippable site. That is **528 invalid single flips, and 528/528 create a defect.** The per-sweep guard checks the sector definition itself: defects plus every winding cut. So any escape that survives to the end of a sweep is caught by construction.

(A first version of this script reported 192 "invalid flips without a defect". That was my own bug: `~` applied to an int8 0/1 mask. The log shows the corrected run.)

**Ruling.**
- R-Main is right that the guard works.
- R-Laptop-1's factual content stands: the only "raises" test (`tests/test_mcmc_baseline.py:131-136`) starts out of sector and never exercises the mover.
- That makes it a missing regression test, not a missing safety net. **Final: MINOR (test coverage).**
- **Fix:** add mutant A or B above as a test.

### D2. R-Laptop-2 statistic: DISMISSED (my Round 1 statistic was wrong; R-Main is right)

**Decisive check** (`scratch/r3/d2_gap_stat.py`, `.log`). Both arms come from the same file, `data/q3_noisy.txt`. The "ideal" arm is the same circuit-order circuit without noise, so there is no ordering confound. It is deterministic. The noisy arm carries a per-time-point trajectory SE (batch means, 20 batches).

My Round 1 statistic divided the gap by the temporal standard deviation of the curve. That measures the oscillation of the signal, which both arms share and which cancels in the paired difference. It is not the uncertainty of the gap.

Late window t = 20–40 (21 points), paired noisy-cond minus ideal-cond:

| cluster | gap | noisy < ideal | z, window mean, SEs fully correlated (most conservative) | 3 time-block means of the gap |
|---|---|---|---|---|
| 3×3 | −0.0497 | 21/21 | **17** | −0.040, −0.052, −0.057 |
| 3×4 | −0.0078 | 18/21 | **7.0** | −0.0076, −0.0051, −0.0106 |

Even treating the three time blocks as the only independent samples, 3×4 gives z ≈ 4.9.

**Ruling.**
- Both drifts are resolved. The paired difference with the trajectory SE is the right statistic for "is the drift resolved?", and the temporal std is not.
- R-Laptop-2 is **DISMISSED**.
- A doc nit remains: quote the SE next to each number.
- **Caveat:** this concerns h = 0.3 only (see D11).

### D3a. Effect of ordering on Q3 §8: partly UPHELD

**Decisive check** (`scratch/r3/d3a_threshold_order.py`, `.log`).
- **Method:** I swap the step function used by `src/trotter_threshold.py` and change nothing else. The swap is from `trotter2_step` (ZZ outside) to the circuit-order step: X half, ZZ, X half, as in `compare.py:240-242`.
- **Grid and exact reference:** I rerun `trotter_error_scan` (dense dt = 0.02–0.60) and `late_window_bias` against the same Chebyshev exact evolution.
- **Sanity check:** the ZZ-outside rows reproduce the committed `data/trotter_threshold.txt` brackets and dt = 0.24 errors exactly.

**Threshold brackets.** These use the time-max flippable-density error, with ε = 0.05 for the absolute criterion and 0.1 × signal for the relative one.

| case | h | absolute, ZZ-out → circuit | relative, ZZ-out → circuit |
|---|---|---|---|
| 3×3, 3-sublattice | 0.1 | (0.46, 0.48] → (0.48, 0.50] | (0.44, 0.46] → (0.44, 0.46] |
| 3×3, 3-sublattice | 0.3 | (0.38, 0.40] → (0.40, 0.42] | (0.32, 0.34] → (0.38, 0.40] |
| 3×4, flippable | 0.1 | (0.50, 0.52] → (0.50, 0.52] | (0.44, 0.46] → (0.46, 0.48] |
| 3×4, flippable | 0.3 | (0.46, 0.48] → (0.46, 0.48] | (0.32, 0.34] → (0.42, 0.44] |

**Late-window Trotter bias at dt = 0.25** (window = last 50% of 12/h, as in the committed data). Ratios are Trotter ÷ exact; "std" is the late temporal std, the project's tolerance scale.

| case | h | P_out, ZZ-out | P_out, circuit | raw defect density, ZZ-out | raw defect density, circuit | max \|cond bias\|/std, either order |
|---|---|---|---|---|---|---|
| 3×3 | 0.1 | ×1.32 | **×0.65** | ×1.53 | **×0.49** | ≤ 0.001 |
| 3×3 | 0.3 | ×1.31 | **×0.69** | ×1.54 | **×0.54** | ≤ 0.027 |
| 3×4 | 0.1 | ×1.13 | **×0.79** | ×1.19 | **×0.74** | ≤ 0.008 |
| 3×4 | 0.3 | ×1.12 | **×0.81** | ×1.18 | **×0.75** | ≤ 0.028 |

**What survives from §8.**
- **Survives:** O(dt²) convergence and the π/6 resonance as the threshold.
  - The resonance location is ordering-invariant, because the two step operators are unitarily conjugate.
  - In circuit order every bracket is the same or *higher*. So "dt = 0.25 sits below threshold for h ≤ 0.3" holds, with margins 1.5–2.0×, or more.
- **Survives:** "the verdict quantities are Trotter-robust". The sector-conditioned bias is ≤ 0.03 std in both orders.
  - The raw-curve bias grows somewhat in circuit order: C1 is 0.28 std on 3×4 at h = 0.3, vs 0.18 std with ZZ outside. Still small.
- **Does not survive as a statement about the circuit:**
  - "P_out is Trotter-inflated ≈10–25%". In circuit order P_out is *deflated* by 19–35%.
  - "defect density Trotter-inflated ≈18–40%". In circuit order it is deflated by 25–51%.
  - "Absolute defect densities at dt = 0.25 describe the reference experiment's circuit" (`q3_thermalization.md:242-243`) has the wrong sign.
  - These statements are correct only for the project's own ZZ-outside splitting.
- **Not run:** 3×6 (the "40%" headline cluster) and h = 0.5. My Round 2 full-window 3×6 numbers (×1.39 ZZ-out vs ×0.605 circuit) show the same reversal.

**Ruling.** UPHELD for the P_out and defect-density statements. **MAJOR**, folded into R-Main-1 / R-Laptop-R2-1 / R-Main-R2-1. Dismissed for the threshold location and the sector-conditioned verdicts.

### D11. What h/|J| = 2 does to Q3 and the Gauss law: UPHELD (R-Main's numbers confirmed)

**Decisive check** (`scratch/r3/d11_h2.py`, `.log`).
- **Setup:** J = −1, dt = 0.25, noiseless, circuit order, 160 steps (t = 40).
- **Path 1:** a numpy step built on `src/trotter` primitives.
- **Path 2:** `src/noisy_q3.run_bare` noiseless, the gate-by-gate local-sim.
- The two paths agree to ≤ 5e-13. Exact continuous time is shown for reference.
- "Uniform" is the infinite-temperature value over all 2^N states.

| cluster, start | h | p_in range (late mean) | defect density / triangle, range (late mean) | exact-time late p_in / defect | uniform p_in / defect |
|---|---|---|---|---|---|
| 3×3, 3-sublattice | 0.3 | 0.973–1.000 (0.987) | 0.000–0.003 (0.0016) | 0.981 / 0.0030 | 0.082 / 0.25 |
| 3×3, 3-sublattice | **2** | **0.288–0.819 (0.552)** | **0.044–0.174 (0.107)** | 0.532 / 0.114 | 0.082 / 0.25 |
| 3×4, flippable | 0.3 | 0.910–0.975 (0.944) | 0.002–0.008 (0.0049) | 0.931 / 0.0066 | 0.015 / 0.25 |
| 3×4, flippable | **2** | **0.071–0.341 (0.107)** | **0.084–0.179 (0.172)** | 0.121 / 0.152 | 0.015 / 0.25 |
| 3×4, stripe | **2** | **0.002–0.162 (0.047)** | **0.108–0.192 (0.173)** | 0.054 / 0.145 | 0.0005 / 0.25 |

**Reading.**
- **R-Main's subagent is confirmed:** p_in 0.06–0.55 and defect density 0.11–0.21. My late means are 0.05–0.55 and 0.11–0.17; the time ranges are wider.
- **The dimer picture does not hold at h = 2.**
  - Without any noise, 45–95% of the weight is outside the defect-free sector.
  - On 3×4 the defect density reaches 69% of the infinite-temperature value.
  - The weight that is in-sector shrinks with N: 0.55 at N = 9 and 0.11 at N = 12.
  - On the experiment's 7×8 torus, Gauss-law post-selection would keep an exponentially small fraction of shots even at zero noise.
- **The QDM / B_W0 / "emergent Gauss law" framing needs a low-energy constraint that h = 2 does not provide.** At h/|J| = 2 the transverse field dominates the constraint scale. I believe this is above the triangular TFIM's ordering transition (h_c ≈ 1.6|J|) [unverified: I recall this from the literature and did not compute it here].
- **The ordering effect is also larger at h = 2.** On 3×4 flippable, the late defect density is 0.172 in circuit order vs 0.152 in exact time.

**Ruling.**
- Q3 (the relaxation verdicts against B_W0 and DE) and the Gauss-law mitigation study are **internally sound studies of the weak-field regime h ≤ 0.5**.
- They **cannot be described as studying the reference experiment (quench4)**, whose circuits encode h/|J| = 2 (settled, R-Main-2).
- Any text that ties them to "the reference" or to quench4 must be withdrawn or re-scoped. One example is `q3_thermalization.md:242-243`, "describe the reference experiment's circuit".
- If D15 shows the team *deliberately* chose h = 0.3 as a different regime, R-Main-2 changes character: from "wrong parameter" to "undisclosed departure from the reference". The scientific consequence above is unchanged.
- **Final severity: MAJOR** for the framing. The code is not at fault.

**Side check for Q2** (`scratch/r3/q2_h2.py`). Q2 is a ground-state ED statement, computed only for h ≤ 1. I extended it to the reference field on the matched 4×4 pair (connected NN C(1), even sector):
- **h = 1:** square −0.9365, triangular −0.2040, ratio 4.59. This reproduces the committed file.
- **h = 2:** square −0.7285, triangular −0.1463, ratio **4.98**.

So the "3–5× weaker" claim also survives at h = 2.

### Opinions on disputes assigned to others (with evidence I hold)

- **D13 (third check of R-Laptop-R2-1).**
  - D11 gives an independent partial check. On 3×4 flippable at h = 0.3, the late-half mean defect density is 0.0049 (circuit) vs 0.0066 (exact), a ratio of 0.74.
  - Committed late-window ZZ-outside: 0.0077, ratio 1.17.
  - These are consistent with my full-window 0.754 / 1.176 (different window).
  - The D3a P_out results show the same sign flip.
  - R-Oracle should still give the formal third reproduction.
- **D9 (gate counts).** I have no new run. I accept R-Main's 6.6–8.6× at matched 2×2 pending R-Oracle's confirmation. Either way "3–7×" is wrong as stated, and the finding stays MINOR.
- **D10 (degenerate lattices).** I have no new run. The η* = 0.25 formula is exact for the 4-site ring. Whether the crossover moves on a 3×3 torus decides whether "η ~ 0.05 is safely below crossover" generalizes. This bears on Q1 (see §3).
- **D4 / D5 (R-Main-3, R-Main-4).** I keep MINOR, conditional:
  - **R-Main-4** becomes MAJOR if R-Oracle's signed QASM extraction finds a non-(+,+) or bond-non-uniform pattern.
  - **R-Main-3** becomes MAJOR if R-Oracle finds a σ / "significant" claim in any doc that is meant for readers, or finds that `_err` is not 1σ.
- **D7.** I keep 7 cells. Whatever the count, the 2.8σ is encoded vs ideal, and encoded minus bare is ≤ 1.0σ in every cell (Round 2). The doc's "one early point" is wrong.
- **R-Oracle-2.** This stays REFUTED unless R-Oracle brings new evidence. Three Monte Carlo runs agree with exp(−D) down to an acceptance of 0.0097.

---

## 2. Final severity table (findings I consider real, after all rounds)

| ID | Final severity | One line |
|---|---|---|
| R-Main-2 + D11 | **MAJOR** | The triangular field: the reference is h/\|J\| = 2. Q3 and the Gauss-law study are at 0.3 and lose their dimer meaning at 2 (noiseless p_in ≈ 0.05–0.55, shrinking with N). |
| R-Main-5 | **MAJOR** | The Q1 encoded-vs-bare design does not fit on H2 at 7×8 (needs 60 qubits, H2 has 56). The harness has no shots, acceptance or estimator fields. The ZNE/ZNR vs post-selection mismatch is unreconciled. |
| R-Main-1 + R-Laptop-R2-1 + R-Main-R2-1 (+ D3a) | **MAJOR** | The defect density and P_out "Trotter inflation" claims describe the project's ZZ-outside splitting, not the reference circuit. In circuit order the bias reverses sign. The sector-conditioned verdicts and the threshold location survive. |
| (Q1 premise) randomized compiling not implemented | **MAJOR for hardware readiness** | The "encoding helps" GO rests on D-RC/FLAG-0, which `src/` does not implement. It is disclosed (`handoff/11:52-53`), but it is a precondition. |
| R-Main-4 | MINOR (→ MAJOR if D5 finds non-gauge signs) | The sign check compares magnitudes only, and `report.tex:232-233` overstates it. |
| R-Main-3 | MINOR (→ MAJOR per D4) | The step-1 gap is ≈2σ at 7×8, not ≈3σ. "Size-independent" is wrong. |
| R-Main-8 / R-Oracle-R2-2 / D10 | MINOR (→ MAJOR if the crossover moves materially) | The headline η* and ×0.60 come from a 4-site ring. |
| R-Oracle-3 / D9 | MINOR | The gate-count ratio mixes lattices; the matched ratio is ≈6.6–8.6×. |
| R-Laptop-1 (D1) | MINOR | The guard works; its test doesn't exercise the mover. |
| R-Laptop-R2-2 | MINOR | The decision record (journal, open questions) is not in the repo. |
| R-Oracle-1 | MINOR | The first-order label is present; "no sampling error" is not glossed. |
| R-Oracle-4, R-Oracle-5, R-Main-6, -7, -9 (residual), -10, -11 (a,b,c,e,f), -12, R-Main-R2-2/-3/-4, R-Oracle-R2-1, R-Laptop-3/-4/-5/-6 | MINOR / nit | Docs, tests, portability and naming. None changes a conclusion. |
| **Dismissed** | — | R-Laptop-2 (D2, wrong statistic). R-Oracle-2 (first-order validity). R-Main-11(d) (63 vs 42). Most of R-Main-9. |

---

## 3. Bottom line

The project's code is careful and its numbers reproduce on three platforms. No fabricated number was found by any reviewer. The problems are about **which experiment the numbers describe**.

| conclusion | supported? | reason |
|---|---|---|
| **Q1**: encoding helps at η ≈ 0.05 | **Only as a model statement, not as a plan** | η* = 0.25 is exact arithmetic, but on a degenerate 4-site ring (D10 open). The GO assumes randomized compiling, which is not built. The planned "only encoding varies vs the released 7×8 data" comparison does not fit on 56 qubits (R-Main-5). Encoded minus bare is ≤ 1σ in every executed cell, so no executed simulation yet *shows* encoding helping. |
| **Q2**: triangular correlations 3–5× weaker | **Yes** | Reproduced bit-for-bit (Round 1). It also holds at the reference h = 2 (ratio 4.98 on 4×4, this round). It is a ground-state ED statement and should be labelled as such, not as quench dynamics. |
| **Q3**: thermalization results | **Yes for h ≤ 0.5 as a classical model study; no as a description of the reference** | The sector-conditioned verdicts are robust to Trotter ordering and Trotter step (D3a) and to noise statistics (D2). But the reference field is h = 2, where the sector picture does not apply (D11). The circuit-frame defect and P_out statements have the wrong sign. |
| **Q4**: Iceberg recommended | **Yes, and if anything stronger** | Distances are confirmed, first-order acceptance matches Monte Carlo, and the gate overhead of the alternatives is larger than the docs say (≈6.6–8.6×). The 2×2 vs 2×3 acceptance-ratio caveat (R-Main-R2-3) is wording only. |
| **Gauss-law mitigation** | **Yes at h ≤ 0.5 in the assumed noise model; no at the reference h = 2** | At h = 2, noiseless post-selection would already discard ≈45–95% on 9–12 sites, falling exponentially with N. |

**Ready for hardware as-is? No.** Here is the smallest ordered list of fixes before any H2 run:

1. **Decide the triangular field (team decision, D15).**
   - Either run Q3/Gauss-law at h/|J| = 2 to match quench4, accepting that the dimer/Gauss-law observables do not apply.
   - Or state openly that the hardware run is a *new* weak-field experiment (h = 0.3) with no published counterpart.
   - Then fix `config.py`, the docs and `report.tex` to a single value.
2. **Make Q1 fit and be like-for-like.**
   - Choose a lattice where bare and Iceberg-encoded both fit in 56 qubits.
   - Recompute η* on a non-degenerate torus at that lattice (D10).
   - Add shots, acceptance and estimator fields to the comparison harness, so the post-selected logical arm and the mitigated bare arm are compared at equal cost.
3. **Implement and test randomized compiling (D-RC)**, which the GO depends on. Re-verify transparency (encoded == bare at zero noise) with twirling on.
4. **Move every Q3/Gauss-law simulation that claims to predict the circuit to circuit order** (`compare.py`'s step). Re-issue the defect-density / P_out statements in that frame.
5. **Make `verify_circuits` sign-aware**, comparing signed rzz / rx / ry against the gauge-allowed set, and test it on the real QASM. This is cheap, and it guards the only paper comparison.

Everything else in §2 can wait until after hardware.
