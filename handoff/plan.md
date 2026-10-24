# handoff/plan.md - pass registry

The numbered journal of this project, one section per pass. **Sections 24 onward are live and
below.** Sections 1-23 (2026-10-06 to 2026-10-09, the Kiro-era run and the role transfer) were
moved verbatim to `handoff/plan-archive-01-23.md` on 2026-10-23 to cut per-session context;
they are superseded and are **not** session reading. Index of what is in the archive:

- **1.** (orig. L13) What was built
- **2.** (orig. L63) What was tested / verified
- **3.** (orig. L98) FLAGS requiring the project lead's decision
- **4.** (orig. L138) HARD STOP handed off (SCOPE 10/14)
- **5.** (orig. L189) NOT done / deferred by stage order
- **6.** (orig. L210) How to reproduce
- **7.** (orig. L223) handoff 01 RETURNED (concatenated Iceberg d=4)
- **8.** (orig. L240) handoff 02 RETURNED (triangular dimers / Gauss law)
- **9.** (orig. L276) handoff 03 RETURNED (Q1 comparison harness)
- **10.** (orig. L304) handoff 04 CHECKPOINT 1 RETURNED (Part A, Iceberg)
- **11.** (orig. L323) handoff 04 PART B RETURNED (Steane, 5-qubit, concat d=4)
- **12.** (orig. L349) Selene gap resolved; handoff 05 created (DEFERRED)
- **13.** (orig. L364) handoff 06 RETURNED (noise sensitivity at the H2 prior)
- **14.** (orig. L399) handoff 07 WRITTEN (sector-restricted MCMC baseline)
- **15.** (orig. L449) handoff 07 RETURNED (sector-restricted MCMC baseline)
- **16.** (orig. L480) handoff 08 WRITTEN (Q3 completion + K2 + figures)
- **17.** (orig. L513) handoff 08 PART A RETURNED (Trotter threshold K2 + field scan)
- **18.** (orig. L568) handoff 08 PART B RETURNED (noisy + Iceberg curves, figures)
- **19.** (orig. L589) handoff 09 WRITTEN (Q2 frustration thickening)
- **20.** (orig. L619) handoff 09 PART A RETURNED (distance-resolved C(r))
- **21.** (orig. L639) handoff 10 WRITTEN (ROLE TRANSFER to Claude Code)
- **22.** (orig. L665) handoff 10 JOB 1 DONE (SCOPE 13 LaTeX report; review/13)
- **23.** (orig. L701) Project lead's decisions, repo cleanup, first GitHub push

Numbering continues from 24; do not renumber.

---

## 24. Three-machine peer review and the fixes it produced, 2026-10-12/14

**Pass type:** independent review, then repair. Not a build pass; no new physics.

**Reviewers.** Three Claude Code instances, each on its own machine, each with its own
subagents: **R-Oracle** (Oracle Cloud VM, Linux aarch64, Python 3.12 — the reference platform,
and the only host with the Zenodo dataset and the private journal), **R-Laptop** (home server,
Linux x86_64, Python 3.14), **R-Main** (Windows 11, Python 3.13, also orchestrator). Three
rounds: independent review with separate focus areas, mutual cross-verification of every
finding, then adjudication of each disagreement with a decisive check. About 40 numbers were
re-derived from code that does not import this project. Reports: `review/14-three-machine-peer-review.md`
(consolidated). The nine per-round reports, the Round-3b cover and the dispute
assignments were later removed from the working tree to keep the repository lean; they remain in
git history at commit 88c8c2a.

**Headline.** No fabricated number and no arithmetic error. Every independent re-derivation
matched; every reproduction that ran matched its committed data file, often byte for byte. The
real problems were about which experiment the numbers describe.

**Three MAJOR findings, each confirmed by all three reviewers.**
1. The triangular reference field is unreconciled: `h/|J| = 0.3` here, **2** in the reference's
   own released quench4 QASM (signed angles read from all 80 files). `research/05` found this and
   it never reached `GaussLawConfig`/`Q3BaselineConfig`; `research/04` independently confirmed 0.3
   from the paper's prose, whose §V body was never read. At `h/|J| = 2` the sector framework is
   not a controlled approximation at all. **No constant was changed** — recorded as `DECISIONS.md`
   DECIDED-1 (formerly OPEN-1); resolved 2026-10-15, see section 25.
2. The dt = 0.25 defect-density and `P_out` "Trotter inflation" figures were attributed to the
   reference circuit; in that circuit's own ordering the bias has the **opposite sign** (3×6
   defect density 1.390 ZZ-outside vs 0.604 circuit-order). Fixed additively:
   `src/trotter.circuit_trotter2_step`, a regression test, and
   `scripts/run_trotter_order_compare.py` → `data/trotter_order_compare.txt`.
   The threshold brackets, O(dt²), the π/6 resonance and the sector-conditioned verdicts survive
   and are ordering-invariant.
3. Q1's "encoding is the only axis that varies" against the released data is infeasible: Iceberg
   needs k+4 physical qubits, so 7×8 needs 60 > 56. Reframed to encoded vs bare on one reduced
   lattice (6×8 = 52 physical), released data as external reference; `compare.Series` gained
   shot/acceptance/estimator fields. `DECISIONS.md` OPEN-2.

**Also fixed.** The project did not run on Windows (28 file-I/O sites had no explicit encoding;
`python -I main.py` was broken). `verify_circuits` was sign-blind while `report.tex` claimed
otherwise — now checks the signed triple against the gauge set. `--skip-exec` truncated
`data/encoded_codes.txt` §5. A 5-shot Gaussian error bar became a labelled t-interval, and
acceptance a Wilson interval. The "Néel" state was column stripes for even `Lx`. Three test gaps
closed, including a sector-escape guard test that passed with the mover stubbed out. A dozen
documented numbers corrected against the data (6.6–8.6× not 3–7×; 32× not 13×; ≈2.0σ not ≈3σ;
7 of 24 cells not "one early point"; slopes 1.97–2.04).

**Two reviewer findings were refuted** by the other reviewers and withdrawn: that the first-order
Stim accounting breaks down at low acceptance (exact Monte Carlo agrees to ≤1.1e-3 even at 1%
acceptance, confirmed three times), and a "63 vs 42" doc/data mismatch (two different, both
correct metrics with similar names — now disambiguated in the docs).

**Suite:** 231 → **274 passing**, identical count on all three platforms. No test removed or
weakened. No existing `data/` file modified; one added. No physics constant changed — every
`config.py` edit is inside its comment block and the enforced ceilings are untouched.

**Still not built (hardware prerequisites, unchanged by this pass):** randomized compiling
(D-RC, `DECISIONS.md` OPEN-3) — the Q1 "encoding helps" GO rests on it; the 6×6 noise-scaling
arm; the Quantinuum client; the `nexus` backend. **Not regenerated:**
`data/encoded_codes.txt` §5 (hours of Selene) and `data/q1_compare.txt` (needs the dataset).

## 25. DECIDED-1: the triangular field stays at h/|J| = 0.3, as a weak-field study, 2026-10-15

> **SUPERSEDED the same day by section 26.** The premise below — that the reference's triangular
> field is h/|J| = 2 — is **wrong**. The paper's Figure 4(e) states "All data taken at
> (h/|J|, dt|J|)=(0.3, 0.25)", so this project's configuration *does* match the reference. The
> h/|J| = 2 figure came from the released quench4 circuit files, which carry the square quench's
> field. Read this section as the record of a decision taken on incomplete evidence; section 26
> has the resolution. The value h = 0.3 was never changed at any point.

**Pass type:** scope decision and the documentation change it implies. **No code, no constant and
no number changed.** Suite unchanged at 274/274 on three platforms.

**The decision.** Of the two options recorded in `DECISIONS.md` DECIDED-1, the project lead chose
**(a)**: keep `h ≤ 0.5` and state the triangular thread as a deliberately chosen, self-contained
study of the weak-field frustrated regime. It does **not** reproduce the reference's triangular
quench, whose released quench4 circuits are at `h/|J| = 2`. Option (b), building a genuine
`h/|J| = 2` study, was not taken: it needs different machinery (the sector theory is first order
in `h/|J|`) and an initial state the data release does not contain, so it is new research rather
than a correction.

**The justification now cited in the docs is physics, not the reference.** `h/|J| = 0.3` is where
the sector-restricted quantum-dimer description holds: it is a first-order-in-`h/|J|` effective
theory, leakage out of the defect-free sector goes as about `h²` (measured exponent 2.08), and
this project's own field scan finds the in-sector verdicts stable at `h ≤ 0.3` and straining at
`h = 0.5` (26% of the weight out of sector). At `h/|J| = 2` the in-sector probability collapses to
0.13–0.63 within a single Trotter step and the in-sector weight falls with system size (0.55 at
N = 9, 0.11 at N = 12), so the constraint the thread tests barely exists there.

**What changed.** Every claim tying the triangular field to the reference was withdrawn and
replaced with the scope statement plus that justification: `README.md`, `docs/report/report.tex`
§Model, `docs/findings_vs_questions.md` (plus a frame qualifier on the Gauss-law floor, which is
≈0.0092 in circuit order and ≈0.0135 in this repo's ordering), `docs/q3_thermalization.md`,
`docs/gauss_law_dimers.md`, `docs/q2_frustration.md`, `config.py`'s triangular blocks (comments
only), and the Q3/Gauss scripts' and modules' docstrings. `DECISIONS.md` DECIDED-1 became DECIDED-1.

**Q2 is unaffected** and is now labelled as what it is: a **ground-state** exact-diagonalization
result, reported at `h ≤ 1`. Its 3–5× weakening also holds at `h/|J| = 2` (4.98 on the matched
4×4 pair, against 4.59 at `h = 1`), so it does not depend on this decision at all.

**The historical record was annotated, not rewritten.** `research/04`, `research/05`,
`research/scout/sweeps/01`, and `handoff/03`, `handoff/09`, `handoff/11` keep their original
wording and carry a dated note pointing at `DECISIONS.md`. Rewriting them would destroy the audit
trail that made this conflict findable — `research/05` had the right answer in October 2026 and it
simply never propagated to the config.

**Still open, unchanged by this decision:** the factual question of what the paper's §V body
actually says (its HTML truncates; the PDF or Supplemental Material would settle whether more than
one triangular run exists), randomized compiling (`DECISIONS.md` OPEN-3), and the Q1 lattice
implementation (OPEN-2). Independently of the field: the released quench4 circuits prepare
`ry(0)` with no `x` gates, so they fix neither winding sector, which confirms T-5 by inspection.

## 26. RESOLVED-1: the triangular field IS the reference's 0.3 — section 25 reversed, 2026-10-15

**Pass type:** evidence, and the reversal of the previous section. **No code, no constant and no
number changed** — again. Suite unchanged at 274/274 on three platforms.

**What happened.** Section 25 reframed the triangular thread as a self-contained weak-field study
on the belief that the reference's triangular field was `h/|J| = 2`. The paper's full text was
then retrieved and **that belief was wrong**. The reframing is withdrawn.

**The evidence** (arXiv:2503.20870v3, read in full):
- **Figure 4(e), verbatim: "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)."** [established]
- §V, "Emergent gauge theory on a frustrated lattice", sets the regime: "For weak transverse field
  (0 < h ≪ J)". [established]
- The triangular lattice is **9×6** (§V, and Methods §VII.1). One triangular run, one field; the
  max/min winding sectors are two initial states within it. The paper states the *square* quenches
  use h = 2|J|, explicitly a different system. [established]
- Earlier fetches failed only because the HTML is 244,452 characters and truncated before Figure 4.
  `research/04`'s caveat that §V's body was never reached is now closed — and it had been right.

**Why the circuits said otherwise, and why they are wrong.** `quench4_step1.qasm` holds
162 × `rzz(0.5)`, 108 × `rx(0.5)`, 54 × `ry(0)` on `qreg q[54]`. The counts are correct for 9×6
(162 = 3N bonds, 108 = two half-layers), so the geometry is genuinely triangular — but the angles
are **quench1's**, i.e. the square quench's field. At `dt|J| = 0.25` that is `h/|J| = 2`; the
paper's 0.3 would need `rx(0.0375)`, about 13× smaller. The dataset's gauge identities only flip
signs and cannot bridge a magnitude. The release separately documents that the quench4 circuits are
initialized to `|0…0>` while the experiments used two winding bitstrings, so the field is a second
instance of the same defect — in files the README offers "to cross-check against the gate angles
and circuit geometry we used". [measured]

**The physics was the tell.** §V reports dimer correlations relaxing toward Markov-chain Monte
Carlo values inside winding sectors. That cannot happen at `h/|J| = 2`, where this project's own
reviewers measured the in-sector probability collapsing to 0.13–0.63 within a single Trotter step.
That argument identified which source had to be wrong before the text was ever retrieved, and it
is the generalisable lesson: when a released artefact and the publication disagree, check which one
the physics can support.

**What changed in the repo.** The reference citation for the triangular field is restored, now
sourced to Figure 4(e) and tagged [established], in `README.md`, `docs/report/report.tex` §Model,
`docs/findings_vs_questions.md`, `docs/q3_thermalization.md`, `docs/gauss_law_dimers.md`,
`config.py` (comments only) and `scripts/run_gauss_law.py`. `DECISIONS.md` DECIDED-1 became
**RESOLVED-1**, keeping the full OPEN → DECIDED → RESOLVED sequence on purpose. The weak-field
argument from section 25 is **kept**, reframed as corroboration. The new finding about the quench4
circuits is recorded in `research/05-zenodo-dataset-map.md`, the dataset map, which is where a
future reader would look.

**Kept from section 25, independent of the reversal:** Q2's relabelling as a **ground-state**
exact-diagonalization result, and its h/|J| = 2 robustness check (ratio 4.98 on the matched 4×4
pair). Both stand on their own.

**T-5 narrows.** The two winding sectors **are** identified in the release, as the
`quench4_min_winding_*` and `quench4_max_winding_*` data files. Only the explicit initial
bitstrings and matching circuits are absent.

**Still open:** randomized compiling (`DECISIONS.md` OPEN-3) and the Q1 lattice implementation
(OPEN-2). Nothing in this pass touches either.

## 27. DECIDED-5: the 6×6 noise-scaling arm (T-17 / R-14), designed and classically validated, 2026-10-16

**Pass type:** research-flow, through all stages: KB → derive → decisions D1–D7 → frozen tests → implement → blind review → handoff.
**Classical predictions under the ASSUMED prior; nothing ran on H2.**

**Built.**
- `src/noise_scaling.py` (new, additive):
  - Pauli insertion and folding (both pytket circuits and the `run_bare_scaled` trajectories);
  - first-order Stim scaling, which reuses `encoded_codes` through a restored `to_stim` wrapper;
  - the weighted slope test, the fixed-asymptote exponential fit, and the HQC formula.
- `config.py`: `NoiseScalingConfig`.
- `scripts/run_noise_scaling.py` → `data/noise_scaling.txt`.
- Docs: `docs/q3_noise_scaling.md`, a `report.tex` §Q3 paragraph, and `DECISIONS.md` DECIDED-5.
- KB: `research/07-noise-scaling.md`, `research/sources.md` (new index), and `research/derivations/01-noise-scaling-arm{,-testspec}.md`.

**Decisions (the project lead):**
- D1 diagnostic first;
- D2 insertion + one fold;
- D3 bare + Gauss only;
- D4 λ = {1, 2, 3};
- D5 B fixed at infinite T;
- D6 compile level 0, T4/T5 on 3×3, new T17;
- D7 t ≤ 3 at slope 0.005, ≈ 8.3×10⁴ HQC.

**Key findings.**
- [measured] An offline H2-1 compile at TKET levels 1–2 cancels the fold (27/27 two-qubit gates instead of 27/81). Unguarded, the λ = 3 point would have run as λ = 1.
- [measured, 3×4] Gauss post-selection already removes most of the noise effect on the conditioned flippable density (0.0002–0.0027 from ideal at λ = 1). The diagnostic still resolves ≈ 0.001–0.003 slopes when the SE is small.
- [derived] Late-time 6×6 λ = 3 points lose about 98% of shots to post-selection, so no late-time 6×6 thermalization claim is possible within any modest budget.

**Tests.**
- Frozen file SHA-256 `FED386D4…5EF8`.
- Suite (397 = 372 + 25): local 397/397 (Win, Py 3.13, 432 s); OLP 397/397 (review B); OVM 397/397 (aarch64, Py 3.12.14, 342 s).

**Review:** `review/15`. Both minor; no open major.
**Handoff:** `handoff/12`. **Still open:** OPEN-2, the OPEN-3 submission path, G2. O-NS1 is a tighter T14 (needs approval).

## 28. H2 submission path built and validated on the local emulator; no HQC spent, 2026-10-17

**Pass type:** research-flow (spec → blind frozen tests → implement → verify). Kiro did not brief this pass; the project lead asked for it directly. **Classical predictions and H2-*local*-emulator runs; nothing ran on Nexus.**

**Built (all additive; verified cores untouched).**
- `src/h2_circuits.py`: the Iceberg program, bare reference and the Steane / 5-qubit / concatenated programs as one pytket circuit each (mid-circuit syndrome measure+reset into registers, round-0 feedforward as real conditional gates, RC frame corrections applied in `shot_records`), O0 compile with a 2-qubit-count guard, native counts, HQC estimate.
- `src/h2_backend.py`: `run_le` (offline H2-1LE; noisy through PECOS directly), `syntax_check` (free SC tier, refuses every non-SC device), `submit_nexus` (HQC tier, gated; **never called**), `fetch_nexus`, a ledger, `offline_compile_backend`.
- `config.py` `HardwareConfig` fields; `requirements-le.txt` (+ `qnexus` pin in `requirements.txt`); `.gitignore` (`.venv-le/`, `runs/`).
- `scripts/run_h2_le.py` → `data/h2_le_validation.txt`; `scripts/h2_hqc_budget.py` → `data/h2_hqc_budget.txt`.
- Docs: `docs/nexus_toggle.md` rewritten, `docs/h2_budget.md`, **`docs/quantinuum_issues.md` (new, ongoing: Quantinuum software issues, 10 entries)**, `DECISIONS.md` OPEN-4, `CLAUDE.md` rules.

**Findings that change the plan.**
- [established, source and docs] qnexus 0.51.1's HUGR client is typed for **Helios**; Quantinuum's docs call Guppy-on-H2 "limited backwards compatibility" and say Nexus does not server-side-compile hugr. H2 takes pytket/QIR, so the Guppy feedforward-discard program is not the H2 submission here (HW-3: not a clean "no"; the free SC can test it). The discard is applied classically instead; HQC is on static gate counts, so cost is unaffected. (QI-3)
- [established: Quantinuum emulator pages, read in full 2026-10-17] the Nexus **H2 emulator is ≤ 32 qubits state-vector (56 stabilizer, Clifford-only)**; its default noise is not a Pauli model (coherent dephasing, leakage, angle-dependent ZZ error). The 6×8 Q1 lattice (52 q) and the 6×6 noise-scaling arm (36/40 q) cannot run on it. Recommended Q1 headline lattice moves to **4×5** (24 qubits; also runs locally). DECISIONS.md OPEN-4 holds the options. [unverified: page itself was blocked in this container]
- [measured] the LE ignores `noisy_simulation` and is always an ideal state vector (QI-2); PECOS rescales p1/p2 by 3/2 and 5/4 (QI-9); `pytket-quantinuum[pecos]` cannot co-install with selene-sim 0.3.4 (QI-1); a qnexus cost-device bug (QI-5, from source).

**Results** (`data/h2_le_validation.txt`, 4000 shots, [measured]): noiseless Iceberg 2×2 and 2×3, steps 1–3, plain and randomized-compiled, acceptance 1.000 and Z2 within 2.1σ of the exact value in every row; bare likewise; five-qubit 1×2 Clifford and generic cases agree within 2.6σ (one point at +2.6σ, rechecked with 4000 shots at two seeds: −1.1σ, +1.3σ). Noisy LE (after the `p_init` fix) accepts fewer shots than local-sim at the same rates (e.g. 0.632 vs 0.703 at p2 = 0.003, step 3), as expected from per-native-gate charging.

**HQC plan** (`docs/h2_budget.md`): G1 2.1k, Q1 4×5 13.2k, Q4 11.7k = 27.0k of 50k (54%); Q3 3×4 rows are formula estimates. All offline; the free SC quotes will replace them.

**Tests.** New frozen files, written blind to the implementation (it was moved aside while they were written; they errored on import): `tests/test_h2_circuits.py`, `tests/test_h2_backend.py`. **Deviation from test-first: the implementation was written before the tests, then hidden from the test writer.** After the first run, two assertions were wrong in the *tests* (measurement order compared in `get_commands()` order; and my spec's "Clifford Z2 is 1/k or 1", which is false at 2×2); the project lead approved correcting them and re-freezing. Old `test_h2_circuits.py` SHA-256 `7155f2c8…7155`, new `dceab7c3…ed80`; `test_h2_backend.py` unchanged `6e38b8fe…fb80`. Counts after review fixes: `.venv` full suite **483 pass + 23 skip** (emulator tests); `.venv-le` H2 files **109 pass** (adds author-written `tests/test_h2_review_fixes.py`, 18 tests). **Review `review/16`: two majors found and fixed** (spend gate accepted NaN/inf; noisy LE omitted initial-state `p_init`); the `p1`-per-native-op charge is documented, not changed.

**Not done / open.** The free SC check (this container's network policy blocks Nexus; needs `nexus.quantinuum.com` allowed and a `NEXUS_REFRESH_TOKEN`). Q3 circuits (Phase 2). OVM/OLS cross-platform runs and the slow Steane/concatenated LE validations (no session reachable from here). The 4×5 Q1 lattice and the 50k allocation are the project lead's decisions.

**Update 2026-10-17 (late).** The free tiers were proven live on Nexus: 42 circuits quoted and accepted on the free H2-1SC (Rz is **not** charged, quotes equal the Rz-free estimate), and 8 real circuits ran end to end on the Nexus-hosted noiseless H2-1LE (acceptance 1.000, Z2 within 1.5σ of exact, cost 0.0). This found and fixed a real bug: `submit_nexus` passed raw circuits where qnexus needs uploaded references (QI-14, `review/16` C1). New: `src/h2_hosted.py`, `scripts/h2_sc_quotes.py`, `scripts/h2_hosted_check.py`, `tests/test_h2_hosted.py`. Budget from server quotes: G1 1,901 + Q1 (4×5) 11,636 + Q4 9,817 = 23,354 HQC. **The H2-1E test is kept in the plan and not run (project lead).** Brief and next steps: `handoff/13` (UPDATE section).

## 29. H2 finish: run driver, hardening, Q3 circuits, single review sweep; no HQC spent, 2026-10-17

**Pass type:** research-flow (spec → blind frozen tests → implement → one blind review sweep at the end, per the project lead). Claude Code is now the only agent (Kiro out since 2026-10-08). **Decisions:** DECIDED-6 (Q1 4×5; 6×6 arm → 3×4 / 3×6) and D-HQC (Rz-free default).
**Built:** `src/h2_driver.py`, `scripts/run_h2_nexus.py` (tiers dry-run / sc / hosted-le / emulator from `CONFIG.hardware.nexus_tier`; emulator = config + token + SC re-quote ≤ cap), `src/h2_q3.py` and the `Q3-*` groups, hardening of `hqc_estimate` / `native_counts` / `submit_hosted_le`, cross-platform script.
**Results [measured]:** Q3 quoted on the free SC, estimate = quote to the cent, 16,499.2 HQC (79 circuits); full plan 39,853 of 50,000; hosted noiseless H2-1LE vs independent NumPy: 19 points × 3 observables, worst |z| 2.52, cost 0.0; Q4 estimate = quote after the conditional-gate fix. Tests: 662 pass + 23 skip (main), 288 (LE).
**Review:** `review/17`; 1 major fixed (explicit tier could bypass config), minors fixed. **Handoff:** `handoff/14`. **Open:** D-MAXCOST, D-RC-Q3, Q3 trims / 50k allocation, OVM/OLP runs, and the H2-1E runs themselves (config switch + per-run go).

## 30. Q3 generalization study: the §9.2 verdict across size, field and noise (IN PROGRESS), 2026-10-22/23

**Pass type:** research-flow (KB → decisions D1–D6 → frozen tests → implement → results → review →
handoff), Claude Code as the only agent. **Classical predictions under the ASSUMED research/06 H2
prior; nothing ran on H2, no HQC spent, nothing committed or pushed.**
**Status: field and noise axes COMPLETE; size axis still computing; peer review not started.**

**Why.** The Iceberg-vs-Gauss-law conclusion of `docs/q3_thermalization.md` §9.2 rested on a single
cell (N = 12, h = 0.3, λ = 1), and the project's Q3 recommendation rests on that conclusion.
Write-up: `docs/q3_scaling.md`. Decisions: `DECISIONS.md` **DECIDED-7**. Live state:
`handoff/RESUME.md`.

**Built (all additive).**
- `src/q3_scaling.py` — Stim first-order rate table, survival curve, (N, h, λ) prefilter.
- `src/noisy_q3_sweep.py` — the sweep over cases × fields × λ, and `score_cell`, which lifts the
  §9.2 metric verbatim from `scripts/run_q3_noisy.py` so generalized cells stay comparable.
- `src/noise_scaling.run_iceberg_scaled` (**D6**) — the λ-amplified **encoded** runner the project
  never had, plus an additive `apply_u` hook in `src/noisy_q3.run_iceberg` so no trajectory logic
  is duplicated.
- `config.py: Q3ScalingConfig`; `scripts/run_q3_scaling.py`, `scripts/run_q3_sweep.py`
  (one cell per process, `--merge`), `scripts/run_q3_hqc.py`, `scripts/probe_q3_scaling_timing.py`.
- Data: `data/q3_scaling.txt`, `data/q3_sweep.txt` (7 of 11 cells so far), `data/q3_hqc.txt`.

**Tests.** Four files, **38 tests**, every one **frozen before the code existed** (the D6 spec was
verified failing on import first): `test_q3_scaling.py` `2ade0fc4…667f`, `test_noisy_q3_sweep.py`
`31866c3c…41f1`, `test_probe_q3_scaling_timing.py` `f2a5de13…6961`, `test_iceberg_scaled.py`
`30837339…8f99`; all four hashes re-verified unchanged at the end of the pass. Full suite on the
OVM: **700 passed, 23 skipped** (662 baseline + 38).

**Results so far [measured; classical prediction under the assumed model].**
- **Continuity.** The published cell, re-run on OLP (Python 3.14.4, x86-64, not the machine that
  produced `data/q3_noisy.txt`): bare + Gauss **0.0017 ± 0.0004 at ×1.43**, the published value to
  the printed digit; Iceberg within 0.4σ.
- **The verdict generalizes.** In all seven N = 12 cells (h ∈ {0.1, 0.2, 0.3, 0.5}, λ ∈ {1, 2, 3})
  bare + Gauss beats Iceberg by 0.013–0.027, every gap above the combined SE, at about half the
  shot cost. bare + Gauss is flat (0.0010–0.0026) across both axes; Iceberg degrades with λ
  (0.0222 → 0.0291 → 0.0288) **on windows that favour it** (see below); Iceberg + Gauss is at the
  statistical floor in six of seven cells at ×3.1–4.6 shots.
- **"Cheap" needs qualifying.** Late-window Gauss shot cost is ×3.1 at h = 0.5 but **×37.0 at
  h = 0.1** (480-step window), and ×33.9 at λ = 3 — more than Iceberg's early-window ×2.8–3.7. The
  recommendation holds on accuracy and reach, not on being cheap.
- **Survival-matched windows.** The published 48-step encoded window is reachable only at N = 12,
  λ = 1 (survival 0.069; 0.021 at N = 18, 0.014 at N = 20). Each cell states its own window; the
  λ rows therefore cover shorter, easier windows, so Iceberg's λ degradation is understated.
- **HQC [offline estimate, nothing submitted].** The study is **155,164 HQC = 3.1× the whole 50k
  allowance**, so it is classical by necessity. At matched window Iceberg costs ×2.94–3.06 the HQC
  of the bare circuit *before* its shot cost, i.e. ≈6× the total resource of bare + Gauss for the
  worse residual. One affordable validation exists: a single N = 12 matched-window pair, ≈7,559 HQC.
- **Classical cost finding** (`docs/q3_scaling.md` §5.4): cost is per-trajectory and scales as
  2^(physical qubits); ~68 % of it is `numpy.tensordot` in the gate appliers, where non-contiguous
  reshapes copy the whole state ~3× per gate. Four cells in parallel on one host ran ~28× slower
  **each** than the published baseline implies (memory-bandwidth bound). **Run such cells serially,
  threads pinned.** An in-place gate applier is the obvious optimisation and was deliberately not
  attempted — `src/backends_qc.py` underpins the encoded pipeline.

**Open on return.**
- The **size axis** (N = 18 on OLP, N = 20 serial locally at reduced counts — larger SE, to be
  reported with the numbers); `docs/q3_scaling.md` §4.3 states nothing until they land.
- **Blind peer review** (not started by design: reviewing a half-finished result set wastes it).
- Free **H2-1SC server quotes** (need a `NEXUS_REFRESH_TOKEN`, absent on this machine).
- `method="fold"` on the encoded arm stays unbuilt and recorded as a separate design question.
- The private journal and `open-questions.md` do not exist on this machine, so they were **not**
  updated — nothing was invented in their place.

---

## 31. Context-size reduction pass (token diet), 2026-10-23

**Not a physics pass.** No file under `data/`, `src/` or `tests/` was read or modified; no graph,
table, physics constant or result changed. `git diff -- data/ src/ tests/` is empty. [measured]

**Why.** `rtk cc-economics` showed the project's spend is dominated by **567.1M cache reads** and
15.0M cache writes against only 5.1K input tokens — i.e. by how large the context is on *every
turn*, not by CLI output volume. The "read first, every session" set totalled 173,882 B (~43k
tokens) before any code was opened. [measured]

**What moved** (nothing deleted; superseded records archived with dated pointers, per the project's
own rule):

| file | before | after |
|---|---|---|
| `handoff/plan.md` | 80,353 B | 28,592 B |
| `DECISIONS.md` | 38,654 B | 26,762 B |
| `CLAUDE.md` | 8,379 B | 8,741 B |
| **read-first total** | **173,882 B** | **110,701 B** (−36%, ≈ 15.8k tokens/turn) |

- Sections 1–23 of `handoff/plan.md` (2026-10-06 → 2026-10-09, the Kiro-era run and the role
  transfer) → `handoff/plan-archive-01-23.md`, verbatim. An index of the 23 sections stays here.
  Verified by round-trip: archive + live sections == the original file, byte for byte. [measured]
- The RESOLVED-1 evidence trail (paper quotations, Zenodo QASM gate-count table, cross-checks)
  → `docs/resolved-1-triangular-field.md`, verbatim. The verdict (h/|J| = 0.3) stays in
  `DECISIONS.md`. All 8 decision headings still present. [measured]

**Corrections made to the documentation.** The test count disagreed in two places — `CLAUDE.md`
said "about 660 passed + 23 skipped", the `tfim-qec` skill said "372 tests". Both are replaced by
the measured **728 tests collected** [measured 2026-10-23, `pytest --collect-only`]. `CLAUDE.md`'s
Environment block described only the OVM; it now names both the OVM and the Windows laptop
invocations.

**Tooling.** `rtk` (WinGet `rtk-ai.rtk`, v0.50.0) was already wired as a PreToolUse Bash hook;
`rtk init -g` added `~/.claude/RTK.md` (460 B) so the agent actively uses `rtk read/grep/find/test`
rather than only benefiting passively. `~/claude-config` was **not** touched. The
`claude-md-management` plugin (official marketplace) was installed for its `claude-md-improver`
skill. The `tfim-qec` skill was trimmed 4,872 → 4,092 B, removing the blocks that duplicated and
contradicted `CLAUDE.md`.

**Gate.** 728 tests collected before and after; full suite run. Not committed.

## 32. Q3 sweep: rulings, pre-declared estimator rules, the re-run program and the article (2026-10-24)

**Why.** The 11th sweep cell (20, 0.5, 3) rested on one surviving Iceberg trajectory of 24. Its
3e-17 batch SE made it read as "Iceberg better by 0.0008". Blind review/18 had already found that
the §3 verdict mixed reference curves (F1) and that three λ scopes coexisted (F3). This pass found
that both N = 20 cells had run at half their declared budget with no record (F13).

**Rulings (project lead, in session):**
- DECIDED-8: 4 modes × 2 references, winners only within one reference beyond 1σ.
- DECIDED-9: λ amplifies every 2-qubit gate (simulator = Stim = pytket).
- DECIDED-10: the four estimator steps. No estimate below a pre-declared ESS floor; jackknife over
  batches; cost = mean(1/acceptance); a re-run budget solved from the Stim survival with margin 2,
  20 shards per cell, one re-run then final.
- Git commit/push allowed on this branch, never main.
- A local-only technical article (never committed or pushed).

**Built** [all classical, ASSUMED noise; 0 HQC, nothing submitted]:
- Literature and statistics write-ups:
  - `research/08-postselected-estimators.md` (lit-sweep, S1–S18; no source gives a numeric ESS floor);
  - `research/derivations/02-postselected-estimator.md`.
- Scoring, pooling and re-run code:
  - `src/q3_rescore.py` (v2 scorer: msd verdicts, own Kish ESS for the Gauss modes, min_batches, grid guards);
  - `src/q3_shards.py` (exact shard pooling);
  - `scripts/q3_queue.py` (resumable multi-host job queue);
  - `scripts/check_q3_replay.py`;
  - `scripts/gen_q3_doc_tables.py` (the v2 block of docs/q3_scaling.md §4.0 and its `--check`);
  - `scripts/plot_q3_sweep.py`, `plot_q3_schematics.py`, `gen_q3_article_tables.py`, `le_q3_encoded_lambda.py`.
- Runner and provenance changes:
  - `src/noisy_q3.py`: additive w2sum / wpsum / wp2sum accumulators, ess, ess_cond, sector_mask;
  - `run_q3_sweep.py`: provenance (argv, git commit, setting sources), a budget guard (`--allow-reduced`), shards, `--merge-shards`, data-file §4 Stim column (F12) and §§5–6.
- λ scope everywhere:
  - `CANONICAL_2Q_SCOPE`; `insert_paulis` covers every 2q gate and preserves registers;
  - `iceberg_noise_scaled_circuits` builds encoded λ > 1 H2 circuits, which were impossible before.

**Tests.**
- Frozen specs: `test_q3_rescore` (R7 amended after review A, documented), `test_q3_shards`, `test_lambda_scope`, `test_q3_rerun_budget`.
- Review regressions: `test_q3_rescore_review`, `test_h2_q3_encoded_lambda`.
- 52 passed + 6 expected strict xfails locally. OVM gate on commit 1 (`0888caf`): 706 / 23 / 6 / 0 failed.

**Reviews.** Both blind reviewers returned **minor**, and every finding was fixed with a test:
- A (theory): the |·| residual's noise-floor bias, a separate conditioned ESS, min_batches, the one-batch guard, the window-start guard, the re-run rule, wording;
- B (code): queue claim races, duplicate shards, partial merge without the ideal, tmp-name collision.
- B also found that the 72 rotation-gadget CX are the **state preparation** (once), not per step. The scope fix therefore moves Stim's survival offset, not its per-step rates. Every document was corrected.

**Results so far** [measured, legacy error bars, PRELIMINARY]:
- At N = 12, bare + Gauss beats Iceberg alone in all 7 cells against the conditioned target.
- Iceberg + Gauss beats bare + Gauss against the conditioned target in 5 of the 6 cells that have
  an estimate, at 4–7× the shots by mean(1/acceptance).
- N = 18 and 20 have no encoded estimate (end ESS 1–6); their pre-declared re-runs are queued.
- Local-emulator construction check of the exact encoded λ = 3 circuits: acceptance 0.700 ± 0.073
  against Stim's 0.742 (−0.6σ); λ = 1 gives 1.000.

**Blocked.** `git push` was refused by the Claude Code auto-mode permission classifier, despite the
lead's permission. It was not worked around, and commits are local. SC quotes need
`NEXUS_REFRESH_TOKEN`.

**Running.** The re-run program: 80 shards + 7 replays over local / OVM / OLP. See RESUME.md.
