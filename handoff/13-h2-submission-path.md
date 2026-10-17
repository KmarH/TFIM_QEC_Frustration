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
