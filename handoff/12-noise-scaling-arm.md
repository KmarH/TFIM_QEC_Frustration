# handoff/12 — the 6×6 noise-scaling arm (T-17 / R-14): designed, validated, reviewed

**Classical predictions under the ASSUMED research/06 prior; nothing has run on H2.**

**State**
- Built [measured]:
  - `src/noise_scaling.py` (additive): insertion, folding, Stim scaling, `run_bare_scaled`, slope test, fixed-asymptote fit, HQC;
  - `config.py` `NoiseScalingConfig`;
  - `scripts/run_noise_scaling.py` → `data/noise_scaling.txt`;
  - `docs/q3_noise_scaling.md`, a `report.tex` §Q3 paragraph, and `DECISIONS.md` DECIDED-5 (D-NS1…7).
- Verified cores untouched. No physics constant moved. No committed `data/` file changed; the only new one is `data/noise_scaling.txt`.
- Tests: frozen `tests/test_noise_scaling.py`, 25 tests, SHA-256 `FED386D4A1BE6B509713E3E1C728288AB91CC8F13C7481D5C31A8C3AE6665EF8`. The original was `BAC907FA…26FC`, re-frozen after D6.
- Suite: 397 pass, local (Win, Py 3.13) and OLP (x86_64, Py 3.14); OVM (aarch64, Py 3.12.14) 397/397.
- Review: `review/15`. Both blind reviewers returned minor; no open major.

**Results** (`data/noise_scaling.txt`, seeds fixed in the script; 3×4, 400 trajectories × 20 batches)
- Raw flippable density: the slope is resolved at every t (z −4.9 … −11.8). Where χ² passes (7/8), the extrapolation cuts the λ = 1 error from 0.014–0.066 to 0.0005–0.010.
- Gauss-conditioned: the λ = 1 error is 0.0002–0.0027. Slopes ≈ 0.001–0.003 per unit λ are resolved at 3 of 8 times. The O0 se can understate the error (4 se at t = 4).
- 6×6: λ = 3 gives λ_eff 2.88. Gauss 10% survival at t ≈ 4.7 (f_G = 0.617 measured at 3×4, applied at 6×6 [inferred]). σ₁ = 0.086 (MCMC × the 3×6 ratio [assumed]).
- 6×6 plan (D7): ≈ 8.3×10⁴ HQC. A t ≤ 8 plan would be ≈ 1.7×10⁶.
- [measured] The offline H2-1 compile cancels the fold at TKET levels 1–2, so folded circuits use level 0 (T17).

**Open decisions**
- **O-NS1:** tighten frozen T14 with |O0 − ideal| < 3 se on raw values (passes today)? Rec: yes. It is a test change, so it needs your approval.
- **O-NS2 (hardware):** server-side optimisation must be off for folded jobs. Record it in `docs/nexus_toggle.md` when the submission path is built.

**Next**
1. Kiro: qc-reviewer on `review/15` + this brief → qc-researcher (does an H2 learned noise model exist? That is G2) → qc-annotator.
2. When G2 lands: rerun `scripts/run_noise_scaling.py` with the real p2/η and recompute the plan.
3. H2 submission stays behind SCOPE §5. The arm needs the `nexus` path (handoff/11 §4 step 5).

**Failures and mistakes**
- The first 2-qubit check used uniform depolarizing, which cannot discriminate; it was replaced by an X⊗I case.
- The derivation first gave Richardson's cost as 49× instead of 57×.
- σ₁'s √N scaling failed its own check and was replaced.
- The blind test writer used 12 qubits, above pytket's 11-qubit statevector cap (D6).
- Reviewer B's first run hit the usage limit.
- The dispatch failed silently on the `~` repo path; it is passed as `C:/…` now.
