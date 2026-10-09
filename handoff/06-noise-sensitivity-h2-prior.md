# Handoff 06 — Noise sensitivity at the researched H2 prior + review/08 doc fixes

**Route to:** Claude Code. Small, well-scoped follow-up (a rerun at researched values + doc
nits), not a build. **Agents cannot launch it; the project lead runs it.** Written by qc-overseer.

## Why this exists
★ FLAG-0 / HW-1 (`Conversation history/open-questions.md`) is the project's headline go/no-go:
does encoding help *at all* on H2? It flips on H2's native-2Q **ZZ fraction η** (crossover
η ≈ 0.25) and coherent **over-rotation ε**. Those were unknown; the current
`data/noise_sensitivity.txt` only has an η = 0.5 / 0.9 straw-man that is **~10× H2's real value**.

`research/06-h2-noise-prior.md` (qc-researcher, 2026-10-07) now supplies a published prior:
- H2's native 2Q gate is exactly our arbitrary-angle `U_ZZ` = `ZZPhase` [established]. So the
  η-crossover is **exact for Iceberg** (no CNOT-frame approximation there).
- **η ≈ 0.04–0.05 (bracket 0.03–0.08)** [inferred, read off Fig. S3 of 2503.20870] — **well below
  0.25**. Dominant 2Q error is IZ+ZI dephasing, not ZZ.
- **ε (coherent 2Q over-rotation) is NOT published** [established as a gap]; the reference
  experiment twirls it away with randomized compiling. ⇒ **scan ε, do not fix it.**
- Predicted **conditional GO**: encoding predicted to still help on H2's stochastic 2Q noise.

This brief makes the sensitivity output reflect that prior, so the doc states a realistic-η
predicted go/no-go instead of a straw-man reversal.

## Goal
1. **Rerun `scripts/run_noise_sensitivity.py` at the researched H2 prior** and record the result.
2. **Apply the four review/08 doc fixes** (small, listed below).
Everything stays a **prediction-from-prior**, never an H2 result (CLAUDE.md hard rule).

## Part 1 — sensitivity at the H2 prior
The script currently hardcodes `P2, P1` and a `SCENARIOS` list and reads J/h/dt/θ from
`CONFIG.encoded`. Change the parameters to the researched prior (keep the old straw-man rows too,
clearly relabelled as stress-tests, so nothing is lost):
- `p2 ≈ 6e-4` (the researcher's mildly-pessimistic 2Q rate; state it `[inferred from published
  2Q infidelity]`), `p1 = pm = p_init = p2/10`.
- An **H2-prior ZZ-bias row at `zz_bias = 0.05`**, plus bracket rows at `0.03` and `0.08`
  `[inferred, Fig. S3 read-off]`.
- An **ε scan** at `overrot ∈ {0, 1e-5, 1e-4, 1e-3}` `[assumed; ε unpublished — scanned]`.
- Keep the existing `η = 0.5 / 0.9` rows but **relabel them explicitly as "stress-test, ≈10× the
  H2 prior (research/06), NOT representative"**, so a reader cannot mistake them for H2.
- The parameterization lives in `config.py` (`EncodedConfig`/a new sensitivity block) or in the
  script's constants in the existing style — do not scatter new constants (CLAUDE.md).

**Output + interpretation.** Regenerate `data/noise_sensitivity.txt`, then add a short paragraph
to `docs/encoded_tfim.md` ("Noise-model sensitivity") stating, as a **prediction-from-prior**:
at η ≈ 0.05 the project is **below** the crossover ⇒ encoding predicted to still help; the only
flip risk in range is coherent ε on **un-twirled** encoded circuits; and the η = 0.5 rows are a
stress-test, not H2. Cross-reference `research/06`.

## Part 2 — review/08 doc fixes (traceability only, no result changes)
- **m1:** `docs/encoded_tfim.md` says Part B has "26 tests"; it is **27** (`tests/test_encoded_codes.py`
  collects 27 — Kiro confirmed `27 passed`). Fix the count.
- **m2:** add the standard caveat line to `data/selene_gap.txt` header — "classical simulators only
  (Stim/Selene); not an H2 result" — matching the caveat already in the other data files.
- **m3:** `docs/encoded_tfim.md` "−71σ" → **−70.6σ** to match `data/selene_gap.txt` (cosmetic).
- **M1 (optional but recommended):** one sentence in the sensitivity section noting the η-bias is
  **exact for Iceberg's native `ZZPhase`** (so the η ≈ 0.25 crossover is exact there), and that the
  CNOT-frame application for the d≥3 parity-gadget gates remains an approximation `[inferred]` —
  which research/06 now sharpens (H2's native gate *is* `ZZPhase`).

## Inputs (already in repo)
- `scripts/run_noise_sensitivity.py`, `src/encoded_codes.py` (`NoiseRates` with `zz_bias`,
  `overrot`, `p_idle`; `undetected_rate_per_step`, `detected_total`), `config.py` (`EncodedConfig`).
- `research/06-h2-noise-prior.md` (the prior + the recommended inputs, verbatim).
- `review/08-encoded-codes-partB.md` (the four fixes), `docs/encoded_tfim.md`,
  `data/noise_sensitivity.txt`, `data/selene_gap.txt`.
- `Conversation history/open-questions.md` ★ FLAG-0 / HW-1 (keep in sync: this closes the
  near-term half of HW-1).

## Constraints
- No invented numbers. Carry research/06's status tags through: η value `[inferred]`, p2
  `[inferred]`, ε `[assumed, scanned]`. Every noisy number is a classical prediction under an
  assumed model — say so.
- Stim first-order accounting only (the script does no execution); no hardware, no Nexus.
- Don't modify the verified cores beyond the sensitivity script + its config block + the named docs.
- Keep the η = 0.5/0.9 rows; relabel, don't delete (traceability).

## Done-check
- `data/noise_sensitivity.txt` regenerated with H2-prior rows (η = 0.05 + 0.03/0.08 bracket,
  p2 = 6e-4, ε scan) and the old η = 0.5/0.9 rows relabelled as stress-tests.
- `docs/encoded_tfim.md` has the prediction-from-prior paragraph (below crossover ⇒ predicted GO;
  ε the residual risk) cross-referencing research/06, plus the m1/m3/M1 fixes; `data/selene_gap.txt`
  has the m2 caveat.
- Tests still pass (the four-code accounting tests should be unaffected — they test formulas, not
  these specific rates; confirm `tests/test_encoded_codes.py` green and the full suite unchanged).
- A journal entry + `open-questions.md` update noting HW-1's near-term half is now closed (prior
  obtained + sensitivity rerun), with the hardware-confirmation half still deferred to handoff/05.

## What the reviewer must verify (light — Kiro may self-review given the size)
- The rerun used the research/06 prior values (η ≈ 0.05, p2 ≈ 6e-4, ε scanned), not invented ones,
  and the η = 0.5 rows are clearly relabelled as non-representative stress-tests.
- The doc states the result as a prediction-from-prior, never an H2 measurement, and the predicted
  go/no-go follows from the regenerated numbers.
- The four review/08 fixes are applied and nothing else in those docs/data changed.
