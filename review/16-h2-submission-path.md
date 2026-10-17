# review/16 — H2 submission path (handoff/13)

**Two blind reviewers (Opus), run in parallel on the committed state; each saw only the artifact paths, the claim and CLAUDE.md, not the author's results.** Adjudicated by the author; the major was reproduced by the author with a command before acting. Everything reviewed is classical or local-emulator; nothing touched Nexus.

| reviewer | scope | verdict |
|---|---|---|
| A, theory | classical frame correction, circuit layout, PECOS noise mapping, HQC formula | **minor** for circuits and post-processing; **major** for the claim that the noisy LE reproduces local-sim at p_init > 0 or p1 > 0 |
| B, code/numerics | tests, independent Z2 cross-check, fault injection, attacks on the spend gate | **major** (spend gate) |

## What held
- A rederived the twirl correction (round flips = X-component of the frame after each A/F readout, final bits XOR `final_flip`, round 0 flip always 0) **before** reading the code; `shot_records` matches it, and omitting the correction gives acceptance 0.0 (discriminating) [measured].
- A: circuit order and register layout identical to `_local_shot_twirled`; mid-circuit Measure/Reset lowers to PHIR `Measure`/`Init`, legitimate on H2 [measured]. HQC formula and the Nm convention match `research/07` [established].
- B: an independent dense-NumPy 2×3 Z2 (no repo code) agrees with the encoded LE run, 12000 shots, steps 1–4 within 0.23–1.31 se, acceptance 12000/12000 [measured]. A mid-program X/Z/Y fault on each of 8 data qubits, with twirling and no syndrome round right after, was detected in all 24 cases (0/60 accepted; control 60/60) [measured]. Device-name attacks (case, spaces, int, None, list) and approval-token variants (NBSP, trailing space) were all refused; qnexus is not imported at module load.

## Findings and resolution
| # | sev | finding | resolution |
|---|---|---|---|
| B1 | **major** | `submit_nexus` gate passed with `max_cost_hqc` NaN or inf, `estimated_hqc` NaN or negative: NaN compares False, so `not nan`, `nan <= 0`, `est > nan` are all False. Reproduced by the author with a fake qnexus: all four reached `start_execute_job`. | fixed: positive tests `isfinite(x) and x > 0` for cap and estimate, in `submit_nexus` and in the shared `backends_qc._nexus_preflight` (a 2-line additive change). Regression: `tests/test_h2_review_fixes.py` (parametrized NaN/inf/negative/zero, asserting the fake qnexus is never even logged into). |
| B2 | minor | `allow_hardware` was truthy-tested ("no" and 1 passed); `shots` 0, −3 passed | fixed: `allow_hardware is True`; shots must be an int ≥ 1 (bool refused); tests added |
| B2b | minor | `estimated_hqc` is caller-supplied and never recomputed (an estimate of 0 passed) | estimate must now be finite and > 0. **Residual, by design:** recomputing it inside would break the frozen tests' arbitrary numbers; the estimate comes from `scripts/h2_hqc_budget.py` and the SC quote, and the server enforces `max_cost` regardless |
| B3 | minor | `run_le` refused only above 30 qubits; SCOPE §5 says 24 | fixed: ceiling from `CONFIG.ceilings.statevector_max_spins`; `LEWidthError` is both a `MemoryCeilingError` and a `MemoryError` (keeps the frozen test); test added |
| B4 | minor | `offline_compile_backend` swallowed every exception; ledger path was cwd-relative; ledger written only after the job started | fixed: catches `DeviceNotAvailable` only; ledger anchored to the repo root; writability checked before submitting; a failed post-submit write prints the job id to stderr and re-raises; test added |
| A4 | **major** | PECOS charges `p_init` only on explicit Init ops, so the LE never charged the initial state while local-sim and Selene do (acceptance 0.749 vs 0.626 at p_init = 0.02; ratio 0.851 = 0.98^8) | fixed: `run_le` prepends a Reset on every qubit when `p_init > 0`; test (P(1) = p_init for one qubit, 4σ) fails before the fix, passes after; QI-11 logged |
| A5 | **major (disclosure)** | PECOS charges `p1` on every compiled native one-qubit op, Rz included (272 native ops vs 52 authored H; acceptance 0.381 vs 0.804 at p1 = 0.002); RC is therefore not a no-op on the noisy LE | **not changed, documented:** it is how the emulator works, not a bug in our code; stated in `run_le`'s docstring, QI-9, and the validation output header. p2 and pm agree with local-sim (0.391 vs 0.377; 0.647 vs 0.632) |
| A7 | minor | the +5 HQC is per circuit, so RC pays it per instance | already so: `scripts/h2_hqc_budget.py` sums per instance |
| B9 | minor | ruff: 20 issues | source and scripts clean; the frozen test files keep their 21 nits (not edited) |

## Not reviewed / not claimed
- Nothing about the live Nexus API: `syntax_check`, `submit_nexus`, `fetch_nexus` were exercised only against a fake qnexus. Their request shapes are from the qnexus 0.51.1 source and [unverified] until the first free SC run.
- Not tested: Steane and concatenated on the LE beyond one step (they take ~0.25 and ~1.2 s per shot); queued for OVM/OLS.
