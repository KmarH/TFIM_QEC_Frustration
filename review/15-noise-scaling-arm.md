# Review 15 — the 6×6 noise-scaling arm (T-17), 2026-10-16

Two blind reviewers, each on its own machine, each given only artefact paths, a one-sentence
claim and the KB. Author reasoning was withheld.

| reviewer | host | brief | verdict |
|---|---|---|---|
| A — theory | OVM (aarch64, 2 cores) | rederive folding / insertion / Richardson / HQC, then compare; physics of the fixed asymptote; data consistency | **minor** |
| B — code/numerics | OLP (x86_64, Python 3.14.4) | full suite; a new independent cross-check; tests passing by construction | **minor** |

B's first launch hit the shared account's usage limit and was relaunched after the reset. The
report is from the second run.

## Independent results [measured]

- **A:** reproduced every arithmetic chain in the derivation and data file to the printed precision:
  Richardson Σc² = 19 (≈ 57× shots); linear {1, 3} Σc² = 2.5; HQC worked example 1.680e4 / 4.79e4;
  λ_eff, Sxx = 1.758, n_acc = 1528, plan totals. Sampled KB citations match their rows.
- **B:** 397/397 on OLP. Its dense density-matrix cross-check (3 qubits, p2 = 0.03, η = 0.3) shares no
  code with the module:
  - λ = 1: `run_bare_scaled` equals `noisy_q3.run_bare` bit for bit, for both methods;
  - λ = 3: insertion and folding Monte Carlo against the exact ρ give max z = 1.26 and 1.82;
  - the exact insert/fold p₀ differ by 0.0014 (0.6656 vs 0.6670), the expected second-order gap.

## Findings and resolution

| # | sev | finding | resolution |
|---|---|---|---|
| A1 | major | D6 (compile level 0) cited `research/derivations/01`, which had no D6 record | Stale tarball: D6 was written to the derivation after dispatch. Now also recorded in the test spec as the "Amendment D6", with the measured 2Q counts (27, 81) at level 0 and (27, 27) at levels 1–2. **Resolved.** |
| A2 | minor | §(a)'s cos²θ / sin²θ mixing is invisible to Stim's rotation = identity, which affects the trivial-vs-logical split of the Iceberg undetected rate under folding | Stated as a limit in the derivation §(c). Dormant under D3 (Iceberg runs at λ = 1). |
| A3 | minor | derivation said ×2.87; the exact value is ×2.864 | Fixed. |
| A4 | note | fixed B is exact for raw observables; for conditioned ones it is [inferred] | Added to `docs/q3_noise_scaling.md` limits. The χ² gate is the guard. |
| B2 | minor | two versions of `data/noise_scaling.txt` | The file is written only by the script and has been regenerated for D7. |
| B4 | minor | `scaled_stim_rates` silently left `overrot` / `p_idle` unscaled | It now raises `NotImplementedError` (same pattern as `noisy_q3._check_supported`). No regression test added: the frozen file is unchanged; see open item. |
| B5 | ok | RNG identical to `run_bare` at λ = 1; streams diverge by design for λ > 1 | — |
| B6 | minor | T14 "closer ≥ 3 of 4" has no magnitude bound | Checked against the data: raw |O0 − ideal| < 1 se everywhere, but conditioned t = 4 is **4 se** off (0.0012 vs se 0.0003, χ² p = 0.43) [measured]. Recorded in the doc: the O0 se is a lower bound. Tightening the frozen test is the project lead's call (open item). |

No major remains open.
