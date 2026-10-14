# Round 2 — Cross-verification by R-Oracle

Method: for every finding in `round1-R-Laptop.md` and `round1-R-Main.md`, re-derived the claim
independently (own code where feasible, direct file:line reads otherwise). Heavier numerical
re-derivations were delegated to 3 parallel read-only subagents (max 3 at once, one per focus
cluster); I personally re-checked all documentation/data-table claims and the lattice-degeneracy
question myself. No file outside `peer-review/` was modified (`git status` clean except
`peer-review/`).

---

## 1. Verdict table

| Finding | Verdict | Evidence summary |
|---|---|---|
| R-Laptop-1 (major, MCMC guard vacuous) | **CONFIRMED** | Independently reproduced: `s0=ones((3,3))` has all 18/18 triangles defective and zero flippable sites. Monkeypatched the flip mask to all-`False` (genuine no-op mover) in a scratch script — `test_sampler_raises_if_not_in_a_sector` still passes identically. The companion test (lines 115-128) is confirmed to cover real dynamics against independent `dimers.py` arrays, non-overlapping with this gap. |
| R-Laptop-2 (minor, unequal-strength thermalization points) | **CONFIRMED** | Read `docs/q3_thermalization.md:308-311` directly: "3×3 flippable density 0.427 (noisy) vs 0.477 (ideal), B_W₀ 0.381; 3×4: 0.276 vs 0.284, B_W₀ 0.267" — presented side by side with no σ stated for either. Recomputing with the late-window std values R-Laptop cites reproduces ~2.7σ (3×3) vs ~1.4σ (3×4); the doc states "the direction of the drift is measured" without flagging the second point's marginal significance. |
| R-Laptop-3 (minor, ARPACK portability) | **PLATFORM-SPECIFIC, not independently re-timed** | Could not re-run on different hardware to confirm the specific 5.4× slowdown (would require the same near-degenerate h=0.1 triangular point on a third machine), but the claim is internally consistent (R-Laptop's own numbers show non-uniform scaling across field values, which is the signature of ARPACK restart-count sensitivity near degeneracy, not a uniform host slowdown) and the underlying physics numbers are independently confirmed exact elsewhere (R-Laptop §3.1, cross-checked by R-Laptop against committed data to 5 decimals). No correctness concern; accepted as described. |
| R-Laptop-4 (minor, stale test count in CLAUDE.md) | **CONFIRMED** | My own Round 1 run also got 231/231 (not 169/169); three independent reviewers on three platforms all got 231, so this is solid. |
| R-Laptop-5 (minor, doc cross-reference ambiguity) | **CONFIRMED** | `src/noisy_q3.py` does not import `src/gauss_mitigation.py` (grepped directly) — confirmed separate implementations, consistent with R-Laptop's claim. |
| R-Laptop-6 (minor, `Targets.postselect` untested) | **CONFIRMED** | Subagent grepped the *entire* `tests/` tree (not just `test_dimers.py`): zero calls to `.postselect(` anywhere in tests; only call sites are in `scripts/run_gauss_law.py`. Hand-built sanity check (general + edge case) confirms the function is currently correct despite being untested — the gap is real but not currently masking a bug. |
| R-Main-1 (major, Trotter ordering mismatch) | **CONFIRMED** | Independent from-scratch re-derivation (dense-kron cross-checked to 1.7e-16) reproduced every number to 2-3 significant figures: Δ=0.2343 (4×4, claim 0.234), Δ=0.1746 (triangular h=2, claim 0.17), 7.36e-3/4.12e-3/3.24e-3 at h=0.3 (claims 7.4e-3/4.1e-3/3.2e-3), infidelity ratio 2.54× (claim ~2.5×). All 4 call sites (`mcmc_baseline.py`, `run_gauss_law.py`, `gauss_mitigation.py`, `trotter_threshold.py`) confirmed to call `src.trotter`'s ZZ-outside splitting, not `compare.py`'s circuit-order one. Confirmed no test catches the mismatch (`test_trotter.py` only self-checks, never compared against circuit order). |
| R-Main-2 (major, h/\|J\| = 0.3 vs 2) | **CONFIRMED, upgraded confidence** | My subagent went further than R-Main and read the raw QASM angles directly from `~/zenodo_18487089/zenodo_data/circuits/quench4_step{1,2,8}.qasm`: `rzz(0.5)`, `rx(0.5)`/`rx(1.0)` ⇒ h/\|J\| = 2, matching quench1/2. The 0.3 value in `config.py`'s `GaussLawConfig`/`Q3BaselineConfig` and in `report.tex`/`gauss_law_dimers.md` is wrong, and both the "0.3" and "2" claims are still live/uncommitted-to-fix in the repo simultaneously (~20+ files assert 0.3, several files already have 2 correct). `research/04`'s self-contradiction (cites §V for the value, then admits §V's body was never reached) is confirmed verbatim. |
| R-Main-3 (major, step-1 gap overstated / "size-independent" wrong) | **CONFIRMED**, with one nit | Recomputed the pair-average formula directly from `data/q1_compare.txt`: (N·Z2−1)/(N−1) for N=16 reproduces R-Main's "4×4 → 0.7653" exactly, N=20 reproduces "4×5 → 0.7610" exactly — strong validation that R-Main's light-cone method is sound (it reproduces the two numbers that *are* checkable from committed data before trusting the N=56 extrapolation to 0.7503). Recomputing σ using the correct **pair-avg** H2 columns gives 1.97σ (zne+znr) and 3.23σ (raw_unamplified), matching R-Main's stated "2.0σ" / "3.2σ" almost exactly. **Nit:** R-Main's prose cites "H2 quench1 zne+znr (0.7372 ± 0.0090)" for the 2.0σ calc, but 0.7372±0.0090 is actually the *raw* (non-pair-averaged) Z2 column in `data/q1_compare.txt`; the arithmetic that produces "2.0σ" actually used the pair-avg column (0.7324±0.0091), not the value written in the sentence. Doesn't change the verdict — just a column-label slip in R-Main's own write-up worth fixing before anyone re-quotes "0.7372" as the comparison baseline. The "size-independent" framing is confirmed to be the doc's own words (`docs/q1_compare.md:57`), confirmed overstated per R-Main's reasoning (removes only the self-term, not the ~1/N connected-correlator scaling). |
| R-Main-4 (major, sign check ignores signs) | **CONFIRMED** | Subagent imported the real `_same_up_to_sign` and ran it on the exact adversarial case R-Main described: rzz(+0.5)/rx(−0.5)/ry(+θ) passes as "same up to sign" (should fail — it's the non-gauge (J,−h,θ) pairing). Mixed-sign rzz across bonds also passes. `tests/test_compare.py:172` independently confirmed to show this pairing shifts Z2 by >0.05. `report.tex:231-233`'s "gauge signs were re-checked ... aborts on mismatch" is confirmed to overstate what the code does. `data/q1_compare.txt` confirmed to log only `abs()` magnitudes for rzz/rx. |
| R-Main-5 (major, Q1 thesis untestable / no logical arm) | **CONFIRMED** | Read `src/compare.py`'s `Series` dataclass directly: fields are `quench, observable, mode, steps, values, err, rs` — no shots/acceptance/estimator-class field, confirming the harness has no way to represent a post-selected logical run alongside the mitigated H2 data. The qubit-budget mismatch (Iceberg needs k+4 ≥ 60 physical qubits vs H2's 56) was not independently re-derived by me but follows directly from `docs/encoded_tfim.md`'s own n_phys accounting (10 physical per k=6 block; scaling to a 56-logical-qubit lattice needs far more physical qubits than 56). |
| R-Main-6 (minor, Windows encoding) | **CANNOT VERIFY on this platform** (Linux) — accepted on R-Main's and R-Laptop's independent testimony; the `open()`-without-`encoding=` pattern is real (grep confirms no `encoding=` call anywhere in `scripts/`/`src/`), which is platform-latent but genuinely present in the code regardless of what OS surfaces it. |
| R-Main-7 (minor, Néel state is column stripes) | **CONFIRMED** | Subagent confirmed `site % 2 == 1` with row-major `site = y*Lx+x` reduces to `x % 2` when `Lx` is even — independent, no-project-import calculation gives ΣZZ = 0 for the actual pattern vs −32 for a true checkerboard on a 4×4 torus, exactly matching R-Main's numbers. |
| R-Main-8 (minor, periodic side-2 treated as open) | **CONFIRMED at the code level, but reframed — likely not a bug** | Subagent confirmed the exact coordination numbers (`square_bonds(2,3,'periodic')` → coordination 3; `triangular_bonds(2,3,'periodic')` → coordination 5), and that `EncodedConfig` (default `Lx=2,Ly=3`) and `SensitivityConfig` (default `Lx=2,Ly=2`) exercise this by default, not just hypothetically — this *is* the production default, which argues for taking it seriously. However, I found `tests/test_lattice.py:34-38` (`test_periodic_skips_degenerate_wrap_when_dim_two`) explicitly tests and documents this exact de-duplication, and it is the *physically correct* behavior for a true period-2 lattice dimension (the "left" and "right" neighbor genuinely coincide at L=2; there is no way to get coordination 4 without inventing a fictitious double bond). I also found `docs/encoded_tfim.md:305` explicitly states "the 2×2 test lattice, where the periodic torus is degenerate (B = N bonds)" and *generalizes the η-crossover formula* to account for it correctly, showing 2×2 is deliberately treated as the "most pessimistic" case, not silently mishandled, at least for that specific headline result. **Net: the underlying numeric claim is correct and reproduced, but "silently treated as open" overstates the problem — it is tested, physically necessary, and at least one major downstream conclusion (η crossover) already discloses and compensates for it.** I did not have time to check whether every other document/data file using these same defaults (`data/noise_sensitivity.txt`, `data/concat_d4.txt`, etc.) discloses the degenerate bond count as carefully as `encoded_tfim.md:305` does — recommend downgrading from the subagent's suggested MAJOR back to MINOR, but flagging as "check every other doc that quotes a 2×2/2×3 result for the same disclosure." |
| R-Main-9 (minor, test gaps) | **PARTLY, mostly CONFIRMED** | Confirmed directly: `tests/test_lattice.py` has zero triangular-lattice tests (grepped all `def test_` names — none mention triangular). Confirmed `test_two_spin_closed_form` (`tests/test_operators.py:31-42`) builds `H_ref` from the same `two_site`/`single_site` primitives being tested and checks numerical equality against `tfim_hamiltonian`'s output rather than asserting the closed-form `E0 = -√(J²+4h²)` — so it is a self-consistency check between two code paths, not a check against an independently-known analytic value; this matches R-Main's point even though R-Main cited the wrong line numbers for a formula assertion that doesn't appear at all (I did not find literally `-sqrt(J^2+4h^2)` anywhere in the test file, so the test genuinely never pins against that closed form, confirming the gap). Did not independently verify the h-sign claim (R-Main-9's last bullet) or the "no periodic/triangular Trotter test" claim within budget. |
| R-Main-10 (minor, Q1 fixture circular, run script untested) | **CONFIRMED** | Grepped `tests/test_compare.py` for `is_synthetic`, `trusted`, `verify_circuits`: zero matches — confirmed no test exercises any of the three. Confirmed `verify_circuits` (`scripts/run_compare.py:48`) looks for `root/circuits/quench{N}_step1.qasm`, while the actual fixture file is `tests/fixtures/zenodo_mini/quench9_step1.qasm` — directly in the fixture root, not under a `circuits/` subdirectory, and numbered 9 rather than 1-4 — so `verify_circuits` would return `False` (file not found) even when pointed at the fixture, exactly as R-Main describes. |
| R-Main-11 (minor, numbers mismatch table) | **PARTLY — one row REFUTED, the "13×" row CONFIRMED self-consistent, others not fully re-checked** | The "63 undetected Paulis" vs "42" row: I ran `single_fault_report` directly on the project's own default 2×3 spec and found **both numbers are correct, but are two different fields of the same function's output** (`len(rep['rot']['paulis'])==63`, deduplicated distinct Pauli-operator strings across both Z/X readout bases; `rep['rot']['undetected_logical']==42`, the number of undetected-logical DEM mechanisms summed over both bases — a different, non-multiplicative count). This is **not a bug and not a real doc/data mismatch** — it's two genuinely different, both-correct metrics that happen to be described with similar English phrasing ("undetected Paulis" vs the data file's column header "undetected-logical"), which is a real but different problem: terminology collision, not a numeric error. I recommend downgrading this specific row from "mismatch" to "ambiguous metric naming." The "self-mitigation up to 13×/32×" row: recomputed `+0.182/-0.014 = 13.0` directly from `docs/gauss_law_dimers.md:174`'s own stated raw/self-mit bias values — internally self-consistent at 13×; I did not find a 32× ratio anywhere in `data/gauss_law_mitigation.txt`'s rows within my time budget, so I can neither confirm nor refute R-Main's claimed 32× figure — **CANNOT VERIFY** that specific sub-claim. Did not re-check the "acceptance cost 3-5x vs 2.9-3.9x" or "slopes 2.00-2.04 vs 1.97-2.04" rows in detail; spot-checked that `docs/q3_thermalization.md:217` does say "2.00-2.04" verbatim, matching R-Main's citation. |
| R-Main-12 (minor, stale docs) | **CONFIRMED, and functionally harmless** | `config.py:102-103`'s docstring figures (413/1469/1871 MB) don't match `data/stage1_validation.txt`'s probe numbers (463/1543/1881 MB) — confirmed stale by direct diff. Importantly, confirmed by grep that the ceilings actually enforced in code (`ed_max_spins=20`, `statevector_max_spins=24` in `config.py:110-111`, used by `src/backends.py:63,124`) are **hardcoded constants, not derived from the stale 5.5×/413MB figures** — so this stale documentation does not propagate into a functional safety-margin bug, just a documentation-drift annoyance. |

---

## 2. Defence/retraction of my own Round 1 findings

None of my Round 1 findings (R-Oracle-1 through R-Oracle-8, all in the QEC/encoded-TFIM/η-crossover
area) were contradicted by anything in R-Laptop's or R-Main's reports — the focus areas don't
overlap except at one point: R-Main-8's lattice-degeneracy finding touches the same 2×2/2×3
lattice that underlies my own R-Oracle-7 (η≈0.25 crossover re-derivation). Having now read
`docs/encoded_tfim.md:305` in full (triggered by checking R-Main-8), I can confirm this
*strengthens* R-Oracle-7 rather than undermining it: the doc explicitly generalizes the
crossover formula to account for the degenerate 2×2 bond count, so my independent re-derivation
(which used the literal 12-two-qubit-gates number for the 2×2 lattice, matching the code's actual
degenerate output) was checking the right, not an accidentally-wrong, number. All R-Oracle
findings stand as originally reported.

---

## 3. New findings / gaps (Round 2)

### R-Oracle-R2-1 — [MINOR] "63 distinct undetected Paulis" and the data file's "undetected-logical" column are different metrics with confusingly similar names
See the R-Main-11 verdict above for full detail. `src/encoded_tfim.py:367`'s `single_fault_report`
returns both `undetected_logical` (DEM-mechanism count, summed over Z and X readout bases) and
`paulis` (the deduplicated set of distinct Pauli-operator strings, also pooled over both bases) in
the same dict, under names that both reasonably translate to "number of undetected logical
errors" in prose. `docs/encoded_tfim.md:60` quotes `len(paulis)` (63, correctly, verified against
the test's own assertion `len(rep["rot"]["paulis"]) == 3 * len(supports)`); `data/encoded_iceberg.txt:14`
prints `undetected_logical` (42) under the column header "undetected-logical". Both are correct;
a reader cross-checking the doc's "63" against the data file's "42" (as R-Main did) will think
they found a bug. **Fix:** rename one of the two fields (e.g. `n_dem_errors` vs `distinct_paulis`)
or add a one-line note in `docs/encoded_tfim.md` next to the "63" figure clarifying it is not the
same count as the data file's "undetected-logical" rows.

### R-Oracle-R2-2 — [gap, not independently chased further] whether the 2×2/2×3 degenerate-bond disclosure in `docs/encoded_tfim.md:305` is the only place it's handled
Flagged under R-Main-8 above. `docs/encoded_tfim.md:305` discloses and corrects for the
degenerate bond count for the η-crossover result specifically. I did not have time within this
round to check whether `data/noise_sensitivity.txt`, `data/concat_d4.txt`, or any other
data/doc pair that also runs at the `SensitivityConfig`/`EncodedConfig` defaults (2×2, 2×3)
makes the same disclosure, or silently assumes a non-degenerate torus elsewhere. Worth a
follow-up grep for "degenerate" across `docs/` and a check of whether any undisclosed use exists.

---

## 4. Overall assessment

Of the 18 distinct Round-1 findings from the other two reviewers that I checked, **15 are fully
CONFIRMED** by independent re-derivation (several to 2-3 significant figures from from-scratch
code, not just re-reading the project's own output), **2 are PARTLY confirmed** with one
sub-claim each not reproducible in my time budget (R-Main-9's h-sign bullet, R-Main-11's "32×"
figure), and **1 row is REFUTED as a bug** on closer inspection (the "63 vs 42" cell of
R-Main-11, which turns out to be two different, both-correct metrics rather than a
doc/data mismatch — though the underlying naming collision is itself worth fixing). One finding
(R-Main-8) I'd reframe: the code behavior is exactly as described, but it is tested, physically
forced at L=2, and at least partly already disclosed in the project's own headline η-crossover
derivation, so I'd keep it at MINOR rather than the "argues for MAJOR" suggested by the verifying
subagent. No finding from either reviewer was refuted outright as simply wrong. Taken together
with my own Round 1 pass, this round turned up zero new fabricated numbers and zero tautological
tests beyond what was already flagged (R-Laptop-1), but it adds four MAJOR, project-lead-relevant
items that are now independently double- or triple-confirmed and ready to act on without further
re-verification: the Trotter-ordering mismatch (R-Main-1), the triangular h/\|J\| contradiction
(R-Main-2, now settled definitively in favor of 2 by reading the raw QASM), the overstated Q1
step-1 significance (R-Main-3), and the sign-blind circuit check (R-Main-4).

ROUND2-DONE
