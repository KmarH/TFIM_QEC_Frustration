# Review 11 — handoff/08 Part B (Q3 noisy + Iceberg-encoded curves, size story, figures; FLAG C)

**Verdict: ACCEPT-WITH-FIXES. No Critical or Major finding.** The overseer may proceed to
annotation and resolve FLAG C. All fixes below are minor (doc/data wording) and are Claude Code's
to apply — the reviewer edits nothing.

**T-17 (one line, → Kevin):** honestly stated as a *caveat*, not a finding — the sector-conditioned
late noisy values drift toward B_W₀ (3×3 0.427 vs ideal 0.477, B_W₀ 0.381; 3×4 0.276 vs 0.284, B_W₀
0.267), direction/size are in the data, and the doc says plainly "a noisy hardware curve landing on
B_W₀ is not, by itself, evidence of thermalization". **Accept the framing.**

**T-18 (one line, → Kevin):** independently confirmed — Iceberg physical register is 16 / 22 / 40 /
**58** for 3×4 / 3×6 / 6×6 / **9×6**, so the reference 9×6 Q3 lattice needs 58 > 56 H2 qubits and does
not fit; a smaller torus (6×6 = 40, 6×8 = 52) is required. **Decision is Kevin's (scope at hardware).**

Reviewer: qc-reviewer (independent). Environment: `.venv`, Python 3.12.14. Full suite re-run by me
(not reported): **217 passed in 123.35 s**; the 12 Part B tests (`tests/test_noisy_q3.py` 8 +
`tests/test_plot_q3.py` 4) pass in isolation. Every discriminating number below was re-derived with my
own code (fresh `stim` DEM accounting, independent `np.polyfit`, direct `make_iceberg(...).n_phys`),
not by re-reading the write-up or re-running the authors' scripts. Scratch script deleted after use.

Scope reviewed: `src/noisy_q3.py`, `tests/test_noisy_q3.py`, `tests/test_plot_q3.py`,
`scripts/run_q3_noisy.py` → `data/q3_noisy.txt`, `scripts/run_q3_size.py` → `data/q3_size.txt`,
`scripts/plot_q3.py` → `figures/*.png`, `config.py` (`Q3*`/`SensitivityConfig`), `requirements.txt`,
`docs/q3_thermalization.md` §9, `docs/findings_vs_questions.md` Q3 rows, journal Entry 34, plan.md §18,
open-questions FLAG C / T-17 / T-18, and the review/10 m1–m3 + T-15 follow-ups.

---

## (A) Independently verified correct — with evidence

**A1. Noise model stated + classical tagging everywhere (checklist 1).** [verified]
- The model is stated identically in the data header (`data/q3_noisy.txt` lines 3–4), the doc (§9.1)
  and the figure caption (`plot_q3.py:ASSUMED`): p2 = 6e-4 with η = 0.05 extra Z⊗Z on a uniform 1/15
  share; p1 = pm = p_init = 6e-5; idle/coherent/leakage/crosstalk assumed absent.
- The "**classical prediction under an ASSUMED noise model, NOT an H2 result**" line is present in
  `data/q3_noisy.txt:2`, `data/q3_size.txt:2`, §9 Status blockquote, the `q3_noisy.png` and `q3_size.png`
  captions, and the findings/journal rows. No number is tagged as an H2 result.
- **The sampled fault channel matches `encoded_codes.to_stim`.** `_fault_2q` (`src/noisy_q3.py:60-67`)
  draws ZZ with prob η + (1−η)/15 and every other 2q Pauli with (1−η)/15 — exactly the
  `PAULI_CHANNEL_2` weights `[u]*14 + [u + p2·η]`, `u = p2(1−η)/15`, in `encoded_codes.py:620-623`.
  `test_two_qubit_fault_distribution_mirrors_the_stim_channel` asserts this to ±0.01 on 60 000 draws;
  I confirm the arithmetic by inspection.
- **`_check_supported` refuses, does not drop.** `src/noisy_q3.py:122-127` raises `NotImplementedError`
  for `p_idle`/`overrot`; `test_unsupported_noise_and_memory_are_refused` exercises both arms. So
  "assumed absent" cannot silently become "silently wrong". [verified]

**A2. Observable definitions identical across arms (checklist 2).** [verified]
`run_observables` (`src/noisy_q3.py:…`) evaluates every arm's mixture through
`trotter_threshold.observable_function`, whose docstring states it uses the `src/dimers.py` arrays with
"exactly the formulas of `src/mcmc_baseline.relaxation_curve` (tested equal)" — the same object the
handoff/07 ideal curves use. The encoded logical readout is decoded to the *same* `dimers.py` basis:
`lidx` is built from the `readout_z(l)` Z-parities with logical site 0 = MSB (`run_iceberg`,
matching `dimers.py`), and `zdet` post-selects on the final pure-Z detectors. `test_iceberg_is_transparent_at_zero_noise`
pins the encoded logical distribution to the bare circuit's to < 1e-12 at every step boundary, which is
the strongest possible like-for-like check. The circuit-order (encoded-pipeline) vs trotter.py-order
ideal difference is **measured, not assumed away** (4–8e-3 flippable, ≤1.5e-3 C1 — below the
late-window verdict tolerance), per the data file and §9.1.

**A3. Local-sim survival = Stim first order to ~2σ (checklist 3).** [verified, re-derived]
I rebuilt the Stim first-order prediction from scratch: `exp(−detected_total(prog, PRIOR, steps))` with
steps = round(t/dt), on the actual `make_iceberg(3,4,flippable)` program. My values:

| t | steps | my exp(−detected_total) | data-file "vs" | measured ± SE | Δ/σ |
|---|---|---|---|---|---|
| 2 | 8 | **0.607** | 0.607 | 0.550 ± 0.029 | 2.0 |
| 4 | 16 | **0.393** | 0.393 | 0.333 ± 0.027 | 2.2 |
| 8 | 32 | **0.165** | 0.165 | 0.157 ± 0.021 | 0.4 |
| 12 | 48 | **0.069** | 0.069 | 0.083 ± 0.016 | 0.9 |

The predictions reproduce the data file to 3 digits. The measured–predicted residual is ≤ ~2.2σ, with
a small, physically-sensible sign structure (first order slightly *under*-counts detection early, so it
*over*-predicts survival; local-sim also carries the ≈6% conservative prep loss at t=0), consistent
with "higher-order effects". The "~2σ" claim is honest; I would not call it tighter than that. The
"×2.7 = 0.0230/0.0086 per-step bare/undetected" consistency note in §9.2 also checks out against
`data/q3_size.txt` row 3×4.

**A4. Size story B2 — no thermodynamic-limit overclaim (checklist 4).** [verified]
- a+b/N fit reproduced to the digit with my own weighted `polyfit` on N ≥ 36:
  **a(N→∞) = 0.2900, b = 0.680** (flippable), matching `data/q3_size.txt` §1 and the §9.3 doc. The limit
  is tagged **[assumed fit form; inferred extrapolation]** in both the data file and the doc.
- The Stim budget at 9×6: my `size_row(9,6,…)` gives bare P(fault)/step = 0.1037 → **16.59 faults over
  the 160-step window** ≈ "~17 faults/window". Confirmed.
- The doc's "**Not claimed**" paragraph (§9.3) states "No thermodynamic-limit statement about
  thermalization. The fit is an extrapolation of the infinite-T baseline only." The quantum curve is
  explicitly said to stop at N = 18. **No overclaim.**

**A5. T-18 qubit count (checklist 5).** [verified] `make_iceberg(...).n_phys` directly:
3×4 → 16, 3×6 → 22, 6×6 → 40, **9×6 → 58** (> 56). Matches the data file's "fits H2" column
(yes/yes/yes/**NO**) and §9.3 ("Iceberg on 9×6 needs 58 physical qubits, more than H2's 56 … Smaller
tori fit, e.g. 6×6 (40) or 6×8 (52)"). The 3×4/3×6/6×6 figures (16/22/40) also match the brief.

**A6. T-17 — scientific-integrity caveat (checklist 6).** [verified, this is the subtle one]
The claim is confined to §9.2 under a heading literally reading "**Caveat that matters for H2: noise can
mimic thermalization**". It is handled correctly:
- The **direction and size are measured** and reproduce the data file's "Late-window Q3 comparison"
  block: 3×3 cond flippable 0.4274 (noisy) between 0.477 (ideal) and 0.381 (B_W₀); 3×4 0.2762 between
  0.2841 and 0.2667. The drift is monotonically *toward* B_W₀ in both cases — the claimed direction.
- The **mechanism is explicitly tagged `[inferred, not measured]`** ("faults that stay inside the sector
  … randomize within the sector"); the doc separates "the direction of the drift is measured; the
  mechanism is reasoning".
- The payload sentence is the honest one: "**A noisy hardware curve landing on B_W₀ is therefore not,
  by itself, evidence of thermalization.**" This is sold as a confound/caveat, not as a thermalization
  finding, and T-17 in open-questions carries the same framing. This would not mislead a referee.

**A7. Figures reproducible from saved data (checklist 7, FLAG C).** [verified]
- `plot_q3.py` reads only `data/*.txt`; the sole recomputation (disclosed in the module docstring and
  §9.4) is the a+b/N fit *line* on the size panel, which is the same weighted fit `run_q3_size.py`
  prints. I grepped the script: there are **no hardcoded physics numbers** — every literal is an axis
  label, limit, caption, or a value pulled from `CONFIG.q3` (dt, thr_eps, qdm_times/noisy_h). B_W₀/DE
  are parsed from the data files.
- I re-ran `python -I scripts/plot_q3.py`: `figures/q3_size.png` is **byte-identical** across runs
  (md5 `929d7a18…` before and after), confirming deterministic regeneration from the data alone.
- 5 PNGs produced (`q3_relaxation`, `q3_field_scan`, `trotter_threshold`, `q3_noisy`, `q3_size`);
  `figures/*.png` is gitignored. `matplotlib==3.11.2` is pinned (uncommented) in `requirements.txt:39`.
  The 4 parser tests tie the parsers to the file contents.

**A8. Ceilings / memory / additivity (checklist 8).** [verified]
- `check_memory` (`src/noisy_q3.py:130-135`) refuses an allocation whose estimated
  `n_batches × n_rec × 2^N × 8` (+ working buffers) exceeds the budget *before* allocating — exactly
  review M5. `test_unsupported_noise_and_memory_are_refused` drives it with n_batches = 1000 →
  `MemoryCeilingError`.
- The Iceberg arm is guarded on the **physical** register: `check_physical_ceiling(prog.n_phys, …)` in
  `run_iceberg`, and `test_ceilings_refuse_before_allocating` shows 4×6 (28 physical) is refused while
  3×4 (16) is allowed. `check_exact_ceiling` guards the logical 2^N observable tables.
- **Cores touched only additively.** `noisy_q3.py` *imports/subclasses* `BareTFIM`, `EncodedTFIM`,
  `iceberg_code`, the rate accountants, `trotter_threshold.observable_function`, and the
  `mcmc_baseline`/`dimers` APIs; it defines no physics inside the verified cores. Core-file mtimes all
  predate the Part B window. (No git history exists to diff; verified by reuse, per KIRO.md.)

**A9. Review/10 m1–m3 + T-15 applied (docs).** [verified]
- **m1:** `docs/q3_thermalization.md:185` now reads "tests assert < 1e-10, and the achieved agreement is
  ~1e-13 (review/10 reproduced ≤ 3.6e-13 at T = 20)". Fixed.
- **m2/T-15:** `docs/gauss_law_dimers.md:~130` now carries the cross-reference: "(That ≈10% is specific
  to the stripe start. … ≈40% for the 3-sublattice start on 3×6, ≈18% for 3×4 flippable, ≈9% stripe …
  see `docs/q3_thermalization.md` §8.)". Fixed.
- **m3:** `data/mcmc_baseline.txt:3` provenance line: "numeric content IDENTICAL to the file it replaced
  … only timestamp/timings differ". The claim is *stated* as asked. See (B) for what I can and cannot
  confirm about it.

**A10. Done-check register items present.** findings_vs_questions Q3 rows updated (lines 41–42, Part B
"awaiting qc-reviewer"); journal Entry 34 (line 1353) + status-board row; plan.md §18 (line 563, "PART B
RETURNED"); open-questions FLAG C marked "move to Resolved on Kiro's acceptance", T-17 and T-18 recorded
with the correct numbers. `config.py` `noisy_*` / `size_*` fields present (lines 324–341).

---

## (B) Could not verify (stated plainly)

- **`mcmc_baseline.txt` content is byte-identical to its predecessor.** The provenance header *claims*
  an identical-content rerun (m3), and the baseline is field-independent so a change would be physically
  surprising. But there is no git history to diff and the previous file was overwritten, so I cannot
  byte-confirm it. mtime ≠ content (KIRO.md). Low-risk; left as m3 below for Claude to assert via a
  content hash if it wants this closed.
- **9×6 Iceberg survival / 54-spin curves.** Above the state-vector and ED ceilings; the budget there is
  Stim first-order accounting only (correctly, and the doc says so). The quantum curve at 9×6 is not
  claimed and not checkable here.
- **Iceberg higher-order survival.** The ~2σ gap between local-sim and the first-order prediction (A3) is
  attributed to higher-order effects; plausible and sign-consistent, but I did not compute the
  second-order term to confirm the magnitude. Not load-bearing for any claim.

---

## (C) Findings by severity

**Critical:** none. **Major:** none.

**minor (Claude Code's to apply — reviewer does not edit the work):**

- **m1 — Iceberg code label nuance (doc, cosmetic).** open-questions T-18 writes "9×6 → [[56,54,2]] + 2
  ancillas = 58". The [[56,54,2]] already includes the 2 Iceberg checks (54 data + 2 = 56); the extra
  qubits to reach 58 are the **syndrome/flag ancillas**, not a second "+2 ancillas". The *count* (58) is
  correct and `n_phys` confirms it; only the phrasing double-reads the "+2". Suggest "9×6 →
  [[56,54,2]] + flag/syndrome ancillas = 58". Cosmetic.
- **m2 — "C(0.866)" vs "C1" naming across data files (cosmetic).** `q3_noisy.txt` labels the shell-1
  correlation `C1`; `q3_size.txt`/`q3_relaxation.txt` label the same quantity `C(r=0.866)`/`C(0.866)`.
  Both are parsed correctly by `plot_q3.py` (the parsers special-case each file), and the doc uses
  C(0.866) consistently, so this is harmless — noted only so the overseer sees it was checked. No change
  required unless a single label is wanted.
- **m3 — `mcmc_baseline.txt` identical-rerun claim unverifiable from the repo (housekeeping).** As in (B):
  either have `run_q3_baseline.py` leave the file untouched when only the field scan changed, or add a
  content hash to the provenance header so the "identical content" claim is checkable without git. Not a
  correctness issue.

---

## Bottom line

Re-derived independently: the sampled 2q channel equals `to_stim`'s biased `PAULI_CHANNEL_2`; the
Iceberg survival reproduces Stim's first-order `exp(−detected_total)` to 3 digits and agrees with
local-sim to ~2σ; the a+b/N limit is 0.2900/0.680 to the digit; the 9×6 budget is ≈17 faults/window; the
Iceberg physical count is 58 > 56 at 9×6; and the size PNG regenerates byte-identically from the saved
data. Every noisy number is tagged a classical prediction under the assumed H2 prior, the T-17 "noise can
mimic thermalization" point is honestly flagged as a caveat (not a result), the thermodynamic limit is
explicitly *not* claimed, observables are like-for-like across arms, ceilings/memory guards and core
additivity hold, and review/10 m1–m3 + T-15 are applied. The 12 Part B tests and the full 217-test suite
are green on my own run.

**ACCEPT-WITH-FIXES — no Critical/Major; proceed to annotation and resolve FLAG C.** The three minor
items are Claude Code's to apply and do not gate release. T-17 and T-18 are decisions for Kevin (one-line
notes at the top).
