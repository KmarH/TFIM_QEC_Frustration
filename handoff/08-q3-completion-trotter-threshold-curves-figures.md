# Handoff 08 — Q3 completion: Trotter-threshold study (K2), relaxation curves across the SCOPE axes, size story, and the first figures (FLAG C)

**Route to:** Claude Code. A **larger, two-part brief** (Kevin approved bigger briefs with an explicit
checkpoint — PROC-1). **Land Part A as a reviewable checkpoint before starting Part B.** Agents cannot
launch Claude Code; Kevin runs it, one session per brief (T-13). Written by qc-overseer.

## Why this exists
Q3 (thermalization) is the biggest **local, non-hardware** loose end. The sector-restricted ergodic
baseline is built and reviewed (handoff/07, review/09, ACCEPT), but the *comparison* is thin: the only
relaxation curves are ideal (noiseless, unencoded), at two fields, on 3×4 / 3×6. SCOPE Q3's "done when"
asks for relaxation curves **across lattices, fields, encodings, noise**, with a size story. This brief
closes that gap, and folds in two resolved decisions:
- **K2 (RESOLVED YES, Entry 30):** add a **dt-convergence / Trotter-threshold study**. Precedent: Kevin's
  prior hackathon built exactly this. It is also what *justifies trusting* every Q3 relaxation curve — a
  curve is only meaningful at a dt below the Trotter threshold.
- **FLAG C (Entry 29):** produce the **first figures** from the existing data (no plotting layer exists yet).
- **K4 framing (RESOLVED YES, Entry 30):** write every conclusion in the honest physics + QEC-methodology
  frame; never imply beyond-classical advantage from the dynamics.

**Not in this brief (kept out deliberately):** K3 (clock-order observable) and K5 (diffusion) are
INCONCLUSIVE — Kevin has not decided them — so do NOT build them here. K1/K6 likewise out.

## Status tags / discipline (non-negotiable)
Everything here is **classical**: exact diagonalization, state-vector Trotter, and the classical MCMC
baseline. **No number is an H2 / hardware result.** Noisy curves are classical predictions under an
**assumed** noise model — label them so, in every data header and figure caption. Never invent numbers;
tag [measured]/[derived]/[assumed]. Within SCOPE §5 ceilings (ED ≤ 20, state-vector ≤ 24; the 2^N×3N
observable tables are guarded at the **ED** ceiling, as in handoff/07). Additive only; do not modify the
verified cores except additively.

---

## PART A — Trotter-threshold study (K2) + ideal relaxation curves across fields  ·  CHECKPOINT

**Goal.** (1) A dt-convergence / Trotter-threshold study for the frustrated triangular TFIM, and
(2) the ideal (noiseless, unencoded) Q3 relaxation curves broadened across more fields and the existing
lattices, both compared to the sector baseline from handoff/07.

**A1 — Trotter-threshold study (K2).**
- Vary dt at fixed total physical time and measure the deviation of the Trotter relaxation curve from the
  exact (`expm` or ED time-evolution) reference, for the triangular TFIM on a cluster within ceilings
  (e.g. 3×4, 3×6). Confirm the second-order O(dt²) convergence (the repo's `trotter.py` is 2nd-order Strang),
  and **locate the dt threshold** above which local observables stop tracking the exact dynamics.
- Report where the project's working dt = 0.25 sits relative to that threshold — this is the credibility
  anchor for every Q3 curve. Cite the threshold theory **[established]**: Heyl–Hauke–Zoller (Sci. Adv. 5,
  eaau8342); Trotter prethermalization Yang et al. (PRX Quantum 4, 030320). Import no numbers from them.
- This is the SAME study type Kevin's prior hackathon built (`run_dt_convergence.py`), adapted from 1D
  ferromagnetic to the triangular frustrated model.

**A2 — Ideal relaxation curves across more fields.**
- Broaden `CONFIG.q3.h_curves` beyond (0.1, 0.3) to a small field scan (e.g. 0.1, 0.2, 0.3, 0.5) on the
  existing `curve_cases`, still noiseless/unencoded, still conditioned on the defect-free W₀ sector, still
  overlaid with the sector baseline and the measured O((h/|J|)²) leak band. Reuse the handoff/07 machinery
  verbatim: `relaxation_curve`, `classify`, `sample_sector`, `exact_references` in `src/mcmc_baseline.py`;
  the field/size/dt knobs live in `config.py:Q3BaselineConfig` (`CONFIG.q3`) — extend that block, do not
  scatter constants.
- Confirm the Q3 verdict labels (thermalized-in-sector / finite-size-DE-offset / etc.) behave sensibly
  across the field scan.

**Part A inputs (real APIs).** `src/mcmc_baseline.py` (`relaxation_curve`, `sample_sector`,
`exact_references`, `classify`, `qdm_diagonal_ensemble`, `ensemble_values`, `Shells`); `src/trotter.py`
(`evolve`, 2nd-order Strang); `src/backends.py` (`run_ed`, `run_statevector`, ceiling guards);
`src/dimers.py` (observables); `config.py:Q3BaselineConfig` and `GaussLawConfig`;
`data/gauss_law_scaling.txt` (the measured h^2.08 leak table).

**Part A done-check (the CHECKPOINT — stop and report here).**
- A dt-convergence/Trotter-threshold script + data file (suggested `scripts/run_trotter_threshold.py` →
  `data/trotter_threshold.txt`), showing O(dt²) and the located threshold, with dt = 0.25 placed relative
  to it. Tests for the convergence (e.g. error halves 4× per dt-halving) in a new or extended test file.
- The broadened ideal field-scan curves regenerated into the Q3 data files, with the sector baseline and
  leak band, verdict labels sane.
- Full suite green (state the new count). Everything tagged classical, no H2 claim.
- **STOP. Report to Kevin for a Kiro review (qc-reviewer) of Part A before starting Part B.** This is the
  checkpoint: the noisy/encoded machinery in Part B must not be built on an unreviewed Part-A pattern.

---

## PART B — Noisy + encoded relaxation curves, size story, and figures (after Part A is reviewed)

**B1 — Noisy and encoded relaxation curves.** Extend the Q3 comparison to the remaining SCOPE axes:
- **Noise:** add a classical noise model to the relaxation curves (the project already has Pauli-trajectory
  / density-matrix noise machinery in `src/gauss_mitigation.py`, and the encoded noise accounting in
  `src/encoded_codes.py` / `src/mcmc_baseline.py`'s dressing). Use a **stated, assumed** model; where
  possible reuse the H2 prior already researched (research/06: p2≈6e-4, η≈0.05) so the noisy Q3 curves and
  the Q1/Q4 sensitivity work speak the same language. Label as a classical prediction, not H2.
- **Encoding:** show the relaxation observables computed through at least the Iceberg-encoded path (the
  recommended code) alongside the bare curve, reusing `src/encoded_tfim.py` / `src/encoded_codes.py`.
  Keep it within ceilings; a reduced size + a stated finite-size caveat is fine (as in Q1).
- The point is the SCOPE Q3 phrase "across … encodings, noise", not a hardware claim.

**B2 — Size story.** The ideal curves stop at 3×6 (state-vector ceiling), where the finite-size DE-offset
(T-12) dominates. Give whatever size trend is reachable **classically**: the MCMC baseline already runs to
9×6; add a Stim-only or MCMC-only extrapolation of the relevant quantities toward larger N where honest,
and state plainly where the quantum curve cannot follow. Do not overclaim a thermodynamic-limit statement
(review/09 B2; docs/q3_thermalization.md §7).

**B3 — Figures (FLAG C).** Build the plotting layer. Uncomment `matplotlib` in `requirements.txt` (it is
pinned-but-commented) and add a figures script (suggested `scripts/plot_q3.py`) that reads the existing
`data/*.txt` (q3_relaxation, mcmc_baseline, trotter_threshold) and writes to `figures/`. First figures:
the relaxation curve vs the sector baseline with the leak band; the dt-threshold plot; and the field scan.
`figures/*.png` is gitignored, so outputs stay local. Match the house discipline: every caption carries the
"classical prediction under an assumed noise model, not an H2 result" line where noise is involved.

**Part B done-check.**
- Noisy + encoded relaxation curves in the Q3 data files under a stated assumed model (the H2 prior where
  reused), tagged classical; Iceberg-encoded vs bare shown.
- A reachable classical size story, with the thermodynamic-limit non-claim stated.
- `scripts/plot_q3.py` produces the figures from saved data; `matplotlib` pinned in `requirements.txt`.
- Full suite green (state count). `docs/q3_thermalization.md` extended with the threshold study, the
  broadened curves, the noisy/encoded curves, the size story, and figure references — all in the K4 honest
  physics+methodology frame.
- A journal entry + `open-questions.md` update (T-6 already resolved; this closes more of Q3's "done when",
  resolves FLAG C, and records K2 as built).

## What the reviewer (qc-reviewer) must verify — both parts
- **Part A, independently:** O(dt²) convergence reproduced; the located Trotter threshold is real (deviation
  from exact grows above it) and dt = 0.25 is correctly placed relative to it; the broadened field curves
  reuse the handoff/07 machinery unchanged and the verdict labels are sound.
- **Part B:** the noise model is explicitly stated and every noisy number is tagged a classical prediction,
  not H2; the encoded curve uses the same observable definitions as the bare one; the size story does not
  overclaim a thermodynamic limit; the figures are generated from the saved data (reproducible), not drawn
  by hand or from invented numbers.
- Across both: ceilings respected; cores touched only additively; the K4 honest framing is used (no
  beyond-classical-dynamics claim).

## Constraints (hard)
- Classical/local only; no hardware, no Nexus, no git push, no SCOPE change, no new derivation that needs a
  literature target not in hand.
- Do NOT build K3 (clock order) or K5 (diffusion) — they are undecided (INCONCLUSIVE).
- One Claude Code session on this brief (T-13). Land Part A before Part B (PROC-1 checkpoint).
