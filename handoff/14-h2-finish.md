# handoff/14 — H2 path finished except the HQC runs: hardening, run driver, Q3 circuits, one blind review sweep

**No HQC spent. Nothing ran on H2-1E/2E or hardware.** Free tiers only (offline LE, H2-1SC quotes, hosted noiseless H2-1LE).
Decisions taken this session (the project lead): **OPEN-4 → DECIDED-6** (Q1 lattice 4×5; 6×6 arm shrunk to 3×4 / 3×6),
**D-HQC (a)** (`hqc_estimate` Rz-free by default). Branch `claude/awesome-lamport-wun6jh`; no PR.

## What changed
- `src/h2_driver.py` + `scripts/run_h2_nexus.py`: the run driver. Tier from `CONFIG.hardware.nexus_tier` (`dry-run` default, `sc`,
  `hosted-le`, `emulator`). Emulator needs config (`nexus_tier`, `allow_hardware`, `max_cost_hqc`, `nexus_project`) **and** the approval
  token on the command line; it re-quotes every circuit on the free SC and refuses if the quote exceeds the cap; limits 32 qubits /
  10,000 shots / 50 HQC per shot (config may tighten, never loosen); real hardware never selectable. Switch-on box in `docs/nexus_toggle.md`.
- `src/h2_q3.py`: triangular bare / Iceberg circuits as one pytket circuit, `bits_to_distribution`, `q3_observables` (classical Gauss
  post-selection), `noise_scaled_circuits` (Pauli insertion, fold; final measurements carried over). Driver groups `Q3-bare`, `Q3-iceberg`,
  `Q3-ladder`, `Q3-bare-3x6` (config `noise_scaling.h2_*`, `insert_instances`).
- Hardening: `hqc_estimate` Rz-free default; `native_counts` counts a conditional gate by the gate it wraps; `submit_hosted_le` sends
  `no_opt=True` (server accepted it live); `HardwareConfig` fields `nexus_tier`, `emulator_max_qubits`, `max_shots_per_job`, `max_hqc_per_shot`.
- `scripts/h2_sc_quotes_q3.py`, `scripts/h2_hosted_q3.py`, `scripts/cross_platform_check.sh`, `run_h2_le.py --out`.
- Docs: `docs/h2_budget.md` (Q3 quoted, limits), `docs/nexus_toggle.md`, `docs/quantinuum_issues.md` (QI-15), `DECISIONS.md` (DECIDED-6),
  `CLAUDE.md` (Claude Code is the only agent), `review/17-h2-finish.md`, and the Spanish team report (shared separately as a PDF; not in the repository).

## Results [measured, all free tier]
- **Q3 SC quotes** (`data/h2_sc_quotes_q3.txt`, 500 shots/point): Q3-bare 5,669.6 · Q3-iceberg 5,283.2 · Q3-ladder 4,093.2 · Q3-bare-3x6 1,453.2 =
  **16,499.2 HQC**, offline estimate = quote to the cent (79 circuits, all accepted). Full plan G1 + Q1 + Q4 + Q3 = **39,853 HQC of 50,000**.
- **Conditional-gate fix** closes the old ≤ 0.5% gap: Q4 offline estimate = quote for all 9 circuits (`data/h2_sc_quotes_q4.txt`, 9,817 = 9,817).
- **Hosted noiseless H2-1LE, Q3** (`data/h2_hosted_q3.txt`, cost 0.0, vs an independent dense NumPy Strang): 19 comparable points × 3
  observables, worst |z| = 2.52; Iceberg acceptance 1.000; fold λ = 3 point equals the ideal (identity); insertion points are marked info-only.
- **Slow offline LE** (`data/h2_le_validation_slow.txt`): Steane 1×2 steps 1–2 and concatenated 2×2 step 1 within 1.25σ of exact, acceptance 1.000.
- **Cross-platform script** ran here (Linux x86_64, Py 3.12.3, 4 cores): `data/xplat_vm.txt`. OVM / OLP not reachable from this container.

## Tests and hashes
Main suite **662 pass + 23 skip** (baseline at the start of this pass: 499 + 23; handoff/13 had said 483 + 23). `.venv-le` H2 files **288 pass**.
Frozen / new test files (SHA-256):
- ab1eaf63632a51171e71abebf8997cbaf752766d9d55e81c74880744eb02b147  tests/test_h2_circuits.py
- 6e38b8fea5ae0c5defd5d0e7c493b74e4ea38dde2a56598238e0d8903d33fb80  tests/test_h2_backend.py
- 761e55b78ffdb7544bb2cd77a1d490747f4fba2d3c559b1b74859cf32d18a784  tests/test_h2_driver.py
- b6da6477984ff6e3866ca3f15e9680d7f0e46bf790b38c78d218a82ca91237d7  tests/test_h2_hardening.py
- d95a605ea2e7a3ebee4706c199f892cb6cf85ddd00db8c2c11385cd76898d9cc  tests/test_h2_q3.py
- 07698ad4e11172e09a11da3f364c9fb1c4b150f58f9fb3a8438c9f1e67a75c4d  tests/test_h2_review_fixes2.py
- `tests/test_h2_circuits.py`: ONE assertion changed (5.74 → 5.72), approved (D-HQC); old hash `dceab7c37f6c110463c1f0f3e07e87f7f7c29af350294444ac2308cdc5e2ed80`.
- `tests/test_h2_q3.py`: written blind as `9076d6a8…82ca91237d7`; ONE assertion corrected (pytket stores Rx angles mod 4 half-turns, so −0.0239 is stored as 3.976), re-frozen as above. **Test error, mine to flag: the blind writer compared the raw value.**
- `tests/test_h2_hosted.py`: one assertion updated for `no_opt=True` (not a frozen file).
- `tests/test_h2_review_fixes2.py`: author-written after the review (not blind).

## Review (`review/17-h2-finish.md`)
One sweep, two blind Opus reviewers. A (spend gate): **1 major fixed** (explicit `tier="emulator"` bypassed `nexus_tier`), 3 minor (2 fixed, 1 design → D-MAXCOST).
B (circuits / numerics / HQC): accept, minors fixed (3 test gaps, 1 error message, shots split). Regression tests added; majors none open.

## Open decisions for the project lead
**D-MAXCOST** — when a group splits into several jobs (G1, Q3-ladder), each job gets the full cap as server-side `max_cost`, so the server backstop is
n_jobs × cap. The pre-submit check (quote total ≤ cap) is in place and price = quote to the cent. Options: (a) leave (rec. for the first runs: cheapest step is one job);
(b) per-job cap = that job's quote + 1% (needs one frozen-test edit, `test_emulator_happy_path…`: it asserts `max_cost_hqc == cap`).
**D-RC-Q3** — `Q3-iceberg` has no randomized compiling (matches the untwirled classical prediction); D-RC says encoded H2 runs use it. Rec.: keep for the first pass.
**Q3 size** — 16.5k HQC vs the old ~10k guess; trims: bare t ≤ 6 (−2,339), Iceberg t ≤ 3 (−2,012), or half the shots.
**50k allocation** still the lead's. **OVM/OLP cross-platform runs**: `bash scripts/cross_platform_check.sh` on each, or `claude remote-control` there.

## Next (needs the lead's explicit per-run go and HQC)
Re-login (`qnx.auth.login()`, per container) → set the config box (`docs/nexus_toggle.md`) → `bare-2x2-step1` (~23.40 HQC) → G1 (1,901) → compare with local emulator, Selene, Stim → Q1 4×5 → Q4 → Q3.

## Failures and mistakes (plain)
- My first Q3 quote script ran as one sequential process and was killed by the 30-minute background cap (no data lost, nothing spent); rewritten per group and run in parallel.
- A `pkill -f` matched my own shell twice while restarting the Nexus login (cost minutes, nothing else).
- I first reported a `Q3` trimming saving as "−1.4k" from memory; the quote files give −2,339 (corrected before it was used).
- The earlier "≈ 10k" Q3 estimate in `docs/h2_budget.md` was low by 6.5k (formula guess, now replaced by quotes).
- Review A's major was a real bug in my driver (explicit tier could override config); caught only by the review, because every frozen emulator test used a config already set to `emulator`.
