# review/17 — H2 finish pass (hardening, run driver, Phase 2 Q3 circuits), 2026-10-17

**Scope.** `src/h2_driver.py`, `scripts/run_h2_nexus.py`, the hardening edits (`hqc_estimate`, `native_counts`,
`submit_hosted_le`), `src/h2_q3.py` and the Q3 groups. Two blind Opus reviewers in parallel (one sweep at the end, per
the project lead): **A — spend-gate safety**, **B — Q3 circuits / numerics / HQC**. Neither touched the repo or Nexus.

| reviewer | verdict | findings |
|---|---|---|
| A (spend gate) | **major** → fixed | 1 major, 3 minor, 1 informational |
| B (circuits, numerics, HQC) | **minor** (claim accepted) | 6 minor / nit |

## Findings and resolution
| # | sev | finding | resolution |
|---|---|---|---|
| A1 | **major** | `execute(tier="emulator")` overrode `hw.nexus_tier`; with config `dry-run` + `allow_hardware=True` + cap + token the emulator was reached (reproduced with a fake qnexus). The CLI was safe. The "config only" claim was not enforced. | `_emulator_gates` refuses unless `hw.nexus_tier == "emulator"`. Regression `test_explicit_emulator_tier_cannot_override_config` (3 cases) failed before, passes now. |
| A2 | minor | The number of SC quotes was never compared with the number of circuits; unquoted circuits could be submitted. | `_quote_all` refuses a short or long quote list. `test_short_quote_list_refused`. |
| A3 | minor | NaN/inf/None config limits silently disabled a gate; limits could be loosened above the documented hard limits. | `_limit()`: finite, > 0 and ≤ 32 qubits / 10,000 shots / 50 HQC per shot (also in `build_plan`). `test_bad_limits_refused` (15), `test_limits_above_documented_hard_limits_refused` (3), `test_build_plan_nan_shot_limit_refused`. |
| A4 | minor, design | Every job of a multi-shot-group plan gets `max_cost = the full cap`, so the server-side backstop is `n_groups × cap`. The pre-submit SC quote total is still checked against the cap. | **Not changed — needs the project lead's decision (D-MAXCOST).** The frozen happy-path test asserts `max_cost_hqc == cap` on every submit; changing it needs a decision card. Mitigation as built: server price equals the offline estimate to the cent, so the real charge is the quote. |
| A5 | info | The approval token is a constant in the repo, so "per run" is by convention. | Accepted: the token stops accidental and looped spends, not a deliberate edit. Stated in `docs/nexus_toggle.md`. |
| B1 | minor | `data/h2_sc_quotes.txt` has a stale `est(noRz)` column for Steane / concatenated (predates the conditional-gate fix); contradicts "to the cent". | Refreshed Q4 quotes with the fixed code → `data/h2_sc_quotes_q4.txt`; the old file is kept as the record of the first run, annotated in `docs/h2_budget.md`. |
| B2 | minor | Test gap: deleting the `W_y` condition in the Gauss mask was not caught. | `test_gauss_mask_needs_winding_y`. |
| B3 | minor | Test gap: ladder / Iceberg items built at 2× the steps were not caught. | `test_iceberg_items_are_the_named_circuits`, `test_ladder_step_counts_match_time`. |
| B4 | minor | Test gap: a constant insertion seed for every (λ, t) was not caught. | `test_insertion_seeds_differ_across_points`. |
| B5 | decision | `Q3-iceberg` has no randomized compiling, while D-RC says encoded H2 runs use it. | Left as built (matches the untwirled classical prediction `data/q3_noisy.txt`); recorded as an open question for the project lead (D-RC-Q3). |
| B6 | nit | `noise_scaled_circuits` on a mid-circuit-measured circuit gave an obscure error; `max(shots//k, 1)` could inflate shots; hosted footer said "~100 comparisons". | Clear `ValueError`; `Q3-ladder` refuses shots < instances; footer says 57. |

## Confirmed by the reviewers [measured]
- Dry-run never imports qnexus (held under a meta-path blocker); `allow_hardware` is checked by identity; bool/NaN/inf caps refused;
  device names must be exactly in `E_DEVICES`; real hardware is never selected by the driver; nothing in `scripts/` calls
  `submit_nexus`/`start_execute_job`; gates run before any quote.
- Rederivation: `exp(+i h dt/2 X) = Rx(−h·dt/π)`, `exp(+i J dt ZZ) = ZZPhase(−2J·dt/π)`; an independent `expm_multiply` evolution matches
  pytket's statevector (|overlap| = 1.0; wrong-J and wrong-h oracles 0.895). The hosted rows recomputed by hand agree; the offline HQC for
  Q3-bare t = 1 (171.10), t = 2 (324.70) and 3×6 t = 1 (254.00) equal the quotes. Mutation run (22 mutations): the frozen tests catch az/ax
  sign, halving, Lie instead of Strang, initial flip, reversed readout, dropped bond, insertion seeds, winding-x mask, fold time, shots split,
  conditional unwrap, Rz charging, prep count; the misses are the ones fixed above.

## Test counts after the fixes
See `handoff/14-h2-finish.md` (final counts and hashes are recorded there after the last full run).
