# handoff/13 — H2 submission path built and validated locally; waiting for the project lead's go on the first Nexus step

**Local-emulator and classical results only. Nothing ran on Nexus. No HQC spent.**

**State**
- Built [measured]:
  - `src/h2_circuits.py`, `src/h2_backend.py`, the `HardwareConfig` fields, `requirements-le.txt`, `scripts/run_h2_le.py`, `scripts/h2_hqc_budget.py`;
  - docs: `docs/nexus_toggle.md` (rewritten), `docs/h2_budget.md`, `docs/quantinuum_issues.md` (new, ongoing), `DECISIONS.md` OPEN-4;
  - `CLAUDE.md` rules for the H2 tiers and the issue log.
- Verified cores untouched; no physics constant moved.
- Tests: new frozen `tests/test_h2_circuits.py` (SHA-256 `dceab7c37f6c110463c1f0f3e07e87f7f7c29af350294444ac2308cdc5e2ed80`) and `tests/test_h2_backend.py` (`6e38b8fea5ae0c5defd5d0e7c493b74e4ea38dde2a56598238e0d8903d33fb80`).
  - Added after review: `tests/test_h2_review_fixes.py` (18 tests, author-written, not blind).
  - Main suite **483 pass + 23 skip** (the emulator ones); `.venv-le` H2 files **109 pass**.
- Review: `review/16`, two blind reviewers. Both found a **major**: (B) `submit_nexus` gate passed NaN/inf cost caps and NaN/negative estimates (reproduced; fixed with finite-positive tests, here and in the shared preflight); (A) the noisy local emulator never charged `p_init` on the initial state (fixed) and charges `p1` per compiled native op including Rz (documented: RC is not a no-op on the noisy LE, QI-9, QI-11). Everything else held, including an independent dense-NumPy Z2 cross-check and 24 mid-program fault injections, all detected.
  - Test-first deviation: implementation first, then hidden from the blind test writer (the tests errored on import). Two *test* assertions were wrong and the project lead approved fixing them (old circuits hash `7155f2c8…7155`).

**What was found [established/measured; details in `docs/quantinuum_issues.md`]**
- The qnexus 0.51.1 HUGR client is Helios-typed and Quantinuum's docs call Guppy-on-H2 "limited backwards compatibility", so H2 gets one pytket circuit with mid-circuit measure/reset and a classical discard (HW-3: not a clean "no"; the free SC can test it).
- The Nexus H2 emulator is ≤ 32 qubits state-vector, 56 stabilizer for Clifford-only circuits [established: Quantinuum emulator pages, read in full 2026-10-17]. The 6×6 arm and the 6×8 Q1 lattice cannot run on it (OPEN-4); Q1 headline recommended at 4×5.
- The local emulator is always ideal (QI-2); `pytket-quantinuum[pecos]` conflicts with selene-sim 0.3.4 (QI-1, hence `.venv-le`); a qnexus cost-device bug (QI-5).

**Results (`data/h2_le_validation.txt`)**
- Noiseless Iceberg 2×2 / 2×3, steps 1–3, plain and RC: acceptance 1.000, Z2 within 2.1σ of exact in every row. Bare likewise. Five-qubit 1×2 Clifford and generic agree; one point at +2.6σ rechecked with 4000 shots at two seeds: −1.1σ, +1.3σ.
- Noisy LE accepts fewer shots than local-sim (0.632 vs 0.703 at p2 = 0.003, step 3), as expected from per-native-gate charging.

**HQC (`docs/h2_budget.md`)**: G1 2.1k, Q1 4×5 13.2k, Q4 11.7k = 27.0k of 50k; Q3 3×4 about 11.5k (formula estimate). Recommended order: SC quotes → G1 → Q1 → Q4 → Q3.

**Open decisions (the project lead)**
1. **OPEN-4:** Q1 headline lattice 4×5 instead of 6×8; what to do with the 6×6 noise-scaling arm (shrink, real hardware, MPS, drop).
2. The 50k allocation in `docs/h2_budget.md`.
3. First Nexus step: the free SC check needs `nexus.quantinuum.com` and `docs.quantinuum.com` allowed in the cloud environment's network policy and a `NEXUS_REFRESH_TOKEN` secret (or run it on your machine). Then G1 on H2-1E (≈ 2.1k HQC) only on your explicit go.
4. Sonnet runs on OVM/OLS: no session was reachable from here. Still to run there: `.venv-le` build, the full and LE suites (cross-platform check), `scripts/run_h2_le.py --slow` (Steane, concatenated).

**Next**
1. Kiro: qc-reviewer on `review/16` + this brief → qc-researcher: the emulator pages are now read (limits; default noise p2 = 1.05e-3 H2-1E, 1.29e-3 H2-2E; HQC formula): check whether the emulator's p2 and its angle-dependent ZZ error feed G2 (HW-1) and the η/ε prior in `research/06` → qc-annotator.
2. Phase 2 (Q3): translate the triangular bare/Gauss circuits and the noise-scaling ladder with `h2_circuits`; compile at level 0, `no_opt`.
3. Report new Quantinuum-stack problems in `docs/quantinuum_issues.md` as found.

**Failures and mistakes**
- My spec said Clifford Z2 "alternates 1/k, 1"; false at 2×2 (it is 0.5, 1.0, 0.5). I copied a `config.py` comment without checking.
- My first HQC table assumed 52-qubit runs on the emulator; it caps at 32 qubits. Corrected before any spend.
- My first `offline_compile_backend` caught the wrong place (device lookup is lazy); found by running the budget script.
- A draft said 6×8 needs "7×10⁷ TB"; it is ≈ 72 PB.

## UPDATE 2026-10-17 (late): free tiers proven live on Nexus; H2-1E test deliberately NOT run, kept in the plan

**What now holds [measured, live]**
- Login works via `qnx.auth.login()` (device code you approve in a browser; per container, so a new cloud session must log in again). The environment's network access was opened, so `nexus.quantinuum.com` and `docs.quantinuum.com` are reachable.
- **Free SC (H2-1SC):** 42 circuits quoted and accepted (`data/h2_sc_quotes.txt`, `data/h2_sc_quotes_q1.txt`), including mid-circuit measure+reset and conditional gates. **Rz is not charged**; the Rz-free estimate equals the quote to the cent for Iceberg and bare, within 0.5% for Steane/concatenated.
- **Hosted noiseless H2-1LE (no HQC, cost verified 0.0):** `src/h2_hosted.py` + `scripts/h2_hosted_check.py` ran 8 real circuits through upload → execute → fetch → decode: acceptance 1.000, Z2 within 1.5σ of exact, RC and conditional gates included, 12-register ordering exact (`data/h2_hosted_check.txt`).
- Bug found and fixed: `submit_nexus` passed raw circuits; qnexus needs uploaded refs (QI-14, review finding C1). The emulator docs were read in full; `docs/h2_budget.md` now uses the server quotes: **G1 1,901 + Q1 (4×5) 11,636 + Q4 9,817 = 23,354 HQC**.
- Tests: `.venv` 102 H2-related pass; `.venv-le` 125 pass (frozen hashes unchanged: circuits `dceab7c3…`, backend `6e38b8fe…`).

**Still untested without HQC:** `submit_nexus` on H2-1E (live), the server-side `max_cost` cap, the noisy emulator's behaviour, anything above 20 qubits on a hosted target.

**The H2-1E test stays in the plan (project lead: not now).** Order when you say go: re-login → SC re-quote the exact circuits → **bare 2×2 step 1** (≈ 23 HQC per 1000 shots, cheapest end-to-end test) → G1 (1,901) → compare with the local emulator, Selene and Stim before anything larger → Q1 4×5 → Q4 → Q3. Each step needs the per-run approval token and your explicit go.

**Next (no HQC), in this order**
1. A short hardening pass on the spend path (see the new session's brief): a run driver `scripts/run_h2_nexus.py` with a dry-run mode, `hqc_estimate` default to Rz-free (needs a frozen-test change: decision card), count conditional gates correctly, read the HQC per-shot / per-job limits page, add `no_opt` to `submit_hosted_le`, then an independent blind review of the driver.
2. Phase 2 (Q3): triangular bare / Gauss circuits and the noise-scaling ladder via `h2_circuits`, compiled at level 0, quoted on the SC; ≤ 20 qubits fully checkable on the hosted LE, ≤ 24 on the offline LE.
3. Decisions waiting on the project lead: OPEN-4 (4×5 for Q1; what to do with 6×6), the 50k allocation.
4. OVM/OLS cross-platform runs and the slow Steane / concatenated LE validations (`scripts/run_h2_le.py --slow`).
