# Handoff 11 — STANDSTILL: classical work complete, waiting for H2 access

**Written by:** Claude Code (overseer since handoff/10), 2026-10-09, at the project lead's request.
**Status:** nothing is in progress and nothing is half-built. This brief is a snapshot of the project while it
waits for Quantinuum H2 / Nexus access, so that any future session (Claude Code, Kiro or a person) can resume
without reconstructing context. **Do not start work from it without the project lead's go-ahead**; the next step is
hardware and needs their explicit approval.

---

## 1. One-paragraph state

Everything that can be done without hardware is done, tested (**231/231**) and reviewed (`review/01`–`13`). The
SCOPE §13 report is `docs/report/report.tex`. PROC-2 (the project lead) stopped new classical work. The article's headline,
logical-vs-physical on H2 against 2503.20870's released data, has not been run; no H2 experiment of any kind
(hardware or emulator) has been done. Every noisy number in the repo is a classical prediction under an assumed
noise model.

## 2. Answers so far (details: `docs/findings_vs_questions.md`, `docs/report/report.tex`)

| question | answer at classically reachable sizes | what still needs H2 |
|---|---|---|
| Q1 logical vs physical | Harness reproduces the published circuits exactly. Encoding is **predicted** to help at the H2 prior (Iceberg ×0.60 of bare on the 2×2 test lattice, ×0.38–0.49 on larger lattices), conditional on randomized compiling | The matched comparison against the released data (T-9); η and ε of H2's gate (HW-1) |
| Q4 QEC choice | Four codes built and executed. The residual sits at the rotation gadgets, not the distance. **Iceberg recommended** | H2-calibrated ranking; active correction for d ≥ 3 (HW-2) |
| Q2 frustration | Matched 4×4: triangular C(1) 3–5× weaker than square. The old 3×4 reference was itself frustrated (corrected). No clock-order claim | Matched H2 frustration data |
| Q3 thermalization | Per-sector MCMC baseline; relaxation to the finite-cluster value; dt = 0.25 below the Trotter threshold for h ≤ 0.3; Gauss post-selection is the effective mitigation; noise can mimic thermalization | Matched H2 curves |
| Gauss-law thread | Mostly no; modest yes for detection against X/Y noise only, floored at O((h/J)²) | — (verdict closed) |

> **Note added 2026-10-15 — see [`DECISIONS.md`](../DECISIONS.md) DECIDED-1.** This table was written while the
> project still described the triangular field h/|J| = 0.3 as the reference's. It is not: the released quench4 circuits are
> at h/|J| = 2 (`research/05-zenodo-dataset-map.md`).
> - **Q1 row:** "reproduces the published circuits" refers to the released circuits at h/|J| = 2. That reproduction
>   does not extend to the triangular Q2 / Q3 / Gauss-law work, which runs at a different field.
> - **Q3 and Gauss-law rows:** "h ≤ 0.3" and the O((h/J)²) floor describe the project's own weak-field study. Under
>   decision (a), that study stays at h/|J| = 0.3 deliberately. It has no counterpart in the reference, so "Matched
>   H2 curves" means a new H2 run at that field, not a comparison with quench4.
> - **Q2 row:** a ground-state ED result. It holds at h/|J| = 2 too (ratio 4.98), so it is unaffected.

## 3. Decisions in force (all the project lead's; registers: `Conversation history/open-questions.md`)

- **D-RC (R-7):** every encoded H2 run uses randomized compiling (Pauli twirling, as 2503.20870 does).
- **T-18 (R-15):** the encoded Q3 run uses **6×6** (40 physical qubits) and the minimal relevant lattice **3×4**
  (16 physical). 9×6 does not fit Iceberg on 56 qubits.
- **T-17 (R-14):** an H2 Q3 curve is never called thermalization without comparing it with the noise. 6×6 is
  beyond classical noisy simulation (36 > 24 spins), so the 6×6 run needs a **noise-scaling arm**.
- **PROC-2:** no new classical depth. **Q2 Part B cancelled.**
- **Parked (not built; the project lead's call):** K1 active gauge protection, K3 clock-order observable, K5 diffusion
  observable, K6 Z₂ vs U(1) wording.
- **Hardware gate (SCOPE §5):** nothing reaches Quantinuum without `allow_hardware=True`, the project lead's explicit
  per-run approval and a recorded HQC cost estimate. The `nexus` backend is a stub that raises.
- **Git:**
  - Published at `github.com/KmarH/TFIM_QEC_Frustation`, branch `initial-import`, commit `37e6879` (2026-10-09). That push was a one-time permission.
  - **Every future commit or push needs the project lead's explicit request.**
  - Changes made after `37e6879` (this brief, `plan.md` §23) are local only.

## 4. How to resume when H2 access arrives (order; each step gated)

**Before the first run (local, no credits):**
1. Get the project lead's approval for the step, and record it.
2. Install and pin the Quantinuum client (`qnexus` and/or `pytket-quantinuum`); confirm the live versions on
   Python 3.12. The project lead logs in themself; credentials never go in the repo.
3. **Build randomized compiling into the encoded programs.** It is not built yet; D-RC requires it and the
   "encoding helps" prediction rests on it. Verify locally that twirled and untwirled agree at zero noise.
4. Design the **6×6 noise-scaling arm** (T-17), for example by gate folding at 1×/2×/3×. Not designed yet.
5. Replace the `nexus` stub following `docs/nexus_toggle.md` (steps 1–7). Path (b) submits the Guppy/HUGR
   program so feed-forward runs on the device. Whether Nexus accepts it is open (HW-3).

**Then (`handoff/05`, G1 → G4):**
- **G1 / HW-5:** Iceberg 2×2, one Trotter step, on the H2 **emulator**. Compare acceptance and Z2 with the Selene
  and Stim predictions (`data/encoded_iceberg.txt`, `data/encoded_codes.txt`) before any hardware cost.
- **G2:** obtain η and ε of H2's native gate from a labelled source; rerun `scripts/run_noise_sensitivity.py`.
- **G3:** encoded (Iceberg, randomized-compiled) vs bare at matched shots, lattice, steps and observable. This
  gives a yes / no / inconclusive verdict on "encoding helps"; it is also the article's Q1 run against the
  released data.
- **G4:** active correction for d ≥ 3, designed and verified in Stim and Selene first.
- **Q3 on H2:** 3×4 (compare with `data/q3_noisy.txt`) and 6×6 (with the noise-scaling arm). Under the assumed
  prior the 6×6 Iceberg arm reaches only early times (survival 10% at t ≈ 3.8; `data/q3_size.txt`).

**Labelling rule:** every new number states *classical prediction*, *H2 emulator* or *H2 hardware*; never mix
them. Stim proves fault-tolerance facts; hardware does not. Self-review each goal (`handoff/10` §4), write
`review/14+`, and update the registers.

## 5. Open technical items (not blocking; `open-questions.md` §A/§C)

- **HW-1:** H2's ZZ fraction and over-rotation.
- **HW-3:** does Nexus accept the Guppy programs?
- **HW-4:** is a native rz noisy?
- **T-3:** are the dataset error bars 1σ?
- **T-7:** graph vs Euclidean C_r.
- **T-10:** un-twirled coherent ε cannot be modelled.
- **T-1:** Selene 1–3σ residual.
- **T-16:** Trotter threshold at 9×6 is inferred.
- **T-20/T-21:** clock correlations, square size limit.

## 6. Environment facts a resuming session needs

- Python 3.12.14 in `.venv`; run scripts as `.venv/bin/python -I scripts/<name>.py`. Suite:
  `python -m pytest tests/ -q` (≈130 s, 231 tests).
- Ceilings: state vector ≤ 24 spins, ED ≤ 20, counting the full physical register; Stim and the MCMC are unbounded.
- LaTeX: no `pdflatex` on the host. Tectonic 0.15.0 (XeTeX engine) is in `~/.local/bin` for test compiles;
  Overleaf is the real pdfLaTeX check.
- Figures are gitignored; regenerate with `scripts/plot_q3.py`. The Zenodo dataset lives outside the repo
  (`docs/q1_compare.md`).
- Read order for a new session: `SCOPE.md` → `CLAUDE.md` → this brief → `Conversation history/project-journal.md`
  (★ box, status board, latest entries) → `open-questions.md` → `handoff/plan.md` → `handoff/05`.
