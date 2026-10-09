# Handoff 10 — ROLE TRANSFER: Claude Code takes over the overseer function and finishes the project

**Written by:** Kiro (qc-overseer), 2026-10-08 — **this is Kiro's last brief for now.** Kevin is out of Kiro
usage for the month, so from here **Claude Code runs everything**, including the scoping/review/annotation
functions Kiro used to perform. This brief transfers that role. Read it in full before doing anything.

**One-line goal:** finish the project — ideally in a single Claude Code session, otherwise across Claude Code
sessions only — by (1) writing the LaTeX report (SCOPE §13), then (2) preparing and, when Kevin approves hardware,
running the H2 path (handoff/05), while **carrying Kiro's discipline and self-reviewing in place of the independent
reviewer.** Do not wait for Kiro; Kiro will not respond.

---

## 0. Your new responsibilities (what Kiro did that you now do)
Kiro ran as several roles (`.kiro/agents/`): **overseer** (scope, plan, write briefs, decide what's done),
**reviewer** (independent milestone review), **researcher** (verify literature), **annotator** (comments only).
You now do all of these yourself. The hard part is **review**: there is no longer a separate agent to check your
work, so you must run the **self-review protocol in §4** on every milestone before calling it done. Treat it as a
real gate, not a formality — it is the only thing standing in for the independent check that caught real errors
this project (e.g. the 16,248 count, the C_r metric, the T-19 frustrated-reference bug).

**Kevin's role is unchanged:** he approves hardware spend and scope/physics-direction decisions, and runs you. When
a decision is his (marked below and in `open-questions.md §B`), STOP and ask him — do not make it yourself.

---

## 1. Where the project stands (verified state, 2026-10-08)

**Test suite: 231/231** (`. .venv/bin/activate && python -m pytest -q`, ~130 s, Python 3.12.14). Keep it green;
re-run and quote the count in every pass. Nothing is committed or pushed (SCOPE §8; stays that way until Kevin asks).

**The thesis (SCOPE §1, journal ★ box):** compute the *same* TFIM observables with LOGICAL qubits on H2 and
compare head-to-head against 2503.20870's *released physical-qubit data*; priority Q1 > Q2 (frustration) > Q3/Gauss;
framing is physics + QEC-methodology, **not** beyond-classical dynamics (K4).

**What is DONE and independently reviewed:**
- **Stage 1/2** (square TFIM, Iceberg d=2, concat d=4, 5-qubit, Steane): built, verified (reviews 01–03).
- **Q4 (QEC choice):** all four codes run end-to-end; **Iceberg recommended** (the undetectable residual sits at the
  arbitrary-angle rotation gadgets, not the code distance; d≥3 dominated). H2-calibrated ranking is hardware-gated.
  (reviews 02/03/08.)
- **Gauss-law thread (SCOPE §3):** verdict recorded — mostly NO; narrow conditional YES for post-selection vs X/Y
  noise only, floored at O((h/J)²). (review/05, `docs/gauss_law_dimers.md`, `docs/findings_vs_questions.md`.)
- **Q3 (thermalization): COMPLETE at classically reachable sizes** — sector-restricted MCMC baseline, Trotter-
  threshold study (K2), ideal + noisy + Iceberg-encoded curves, size story to 12×12, 5 figures. (reviews 09/10/11;
  `docs/q3_thermalization.md`, `src/mcmc_baseline.py`, `src/trotter_threshold.py`, `src/noisy_q3.py`.)
- **Q2 (frustration): Part A done + reviewed** (review/12) — distance-resolved connected C(r), square vs triangular;
  matched 4×4 shows triangular C(1) 3–5× weaker than bipartite-square (the frustration signature); long-distance
  triangular correlations field-fragile + torus-shape-sign-dependent (disorder-line caveat). (`docs/q2_frustration.md`,
  `src/frustration.py`.) **Q2 Part B is CANCELLED (PROC-2); do not build it.**

**What is PENDING:**
- **The LaTeX report (SCOPE §13) — NOT started. This is your first job (§3).**
- **The hardware path (handoff/05, DEFERRED) — HW-5 calibration first, then G1–G4.** Gated on Kevin's hardware
  approval + `allow_hardware=True` (SCOPE §5). Your second job, when Kevin green-lights it (§5).
- **Q1 matched comparison (T-9):** the article spine; needs H2 data. Hardware-gated.

**Parked (Kevin's optional calls — do NOT build without his yes):** K1 (active gauge protection), K3 (clock-order
observable), K5 (diffusion observable), K6 (Z₂-vs-U(1) wording), T-10. PROC-2 says no new classical depth unless the
report or hardware path needs it.

**Resolved flags:** FLAG A (Python 3.12), FLAG B (build-deps, Kevin's ARM VM only), FLAG C (figures built). K2
(dt-study, done in Q3), K4 (honest framing, adopted).

---

## 2. The order of remaining work (PROC-2, Kevin's)
1. **LaTeX report** (SCOPE §13) — §3 below. Do this first; it needs no hardware and consolidates everything done.
2. **Relay backlog** — §6 below, small doc fixes; fold them in as you touch the relevant files (do them before or
   during the report so the docs you cite are correct).
3. **Hardware path** — §5 below (HW-5 → G1–G4), **only after Kevin approves hardware**. Until then it stays stubbed.
4. **Parked items** — only if Kevin decides them.

Do as much as possible in one go. If you must split, split at these numbered boundaries, and update the registers
(§7) at each boundary so the next session can resume.

---

## 3. JOB 1 — the LaTeX report (SCOPE §13)
**Goal:** a LaTeX document that **compiles on Overleaf** (pdfLaTeX, self-contained preamble, standard packages only)
and is the project's scientific report: the "Findings vs questions" story with evidence, uncertainties, and the
honest framing. SCOPE §13: "LaTeX report compiles on Overleaf; a 'Findings vs questions' table maps each conclusion
to the stage/experiment and the result that counts as its answer."

**IMPORTANT — do not confuse two documents:**
- `Conversation history/reporte-tecnico-equipo.tex` is **Kevin's team-update doc** (Spanish, gitignored, NOT part of
  the project, must never be pushed). You may read it for continuity but it is **not** the SCOPE §13 report.
- The SCOPE §13 report is a **new** file in the tracked tree — put it in `docs/` (e.g. `docs/report/report.tex`), in
  **English**, as the formal deliverable.

**Suggested structure (adapt as needed):**
1. **Abstract / intro** — the thesis (§1), the named gap vs 2503.20870, the honest framing (K4: contribution is
   logical-vs-physical advantage on real observables + frustration physics + QEC methodology, not beyond-classical
   dynamics; cite the classical-frontier caveat 2308.05077).
2. **Methods** — TFIM conventions (H = −J ΣZZ − h ΣX, J=−1 AFM for frustration; dt=0.25; row-major index); the
   codes (Iceberg [[k+2,k,2]], concat [[16,4,4]], 5-qubit, Steane); the backends (local-sim / Stim verifier / Selene;
   Nexus stub); the MCMC baseline and the Trotter-threshold method. Pull from the module docstrings — they are
   written to be quotable.
3. **Q4 — QEC choice:** Iceberg recommended; the rotation-gadget residual finding; the η≈0.25 crossover and the
   research/06 prior (predicted conditional GO); every noisy number labelled a classical prediction.
4. **Q2 — frustration:** the C(r) square-vs-triangular result (Part A); energy/bond; the T-19 bipartite-reference
   correction; the disorder-line caveat; **no clock-order claim (K3 not built)**.
5. **Q3 — thermalization:** the sector-restricted MCMC baseline, the Trotter-threshold justification, the
   noisy/encoded curves, the size story, the finite-size offset (T-12), the T-17 "noise can mimic thermalization"
   caveat; **no thermodynamic-limit claim.**
6. **Gauss-law thread:** the mostly-NO verdict.
7. **Findings vs questions table** — lift `docs/findings_vs_questions.md` into a LaTeX table; this is the SCOPE §13
   centrepiece. Mark what is DONE-classical vs hardware-gated.
8. **What is hardware-gated** — the Q1 spine and the matched H2 comparisons; the go/no-go on η/ε; HW-5→G1–G4.
9. **Figures** — reuse `figures/*.png` (regenerate with `scripts/plot_q3.py`; add Q2 figures from
   `data/frustration_correlations.txt` if useful). `figures/*.png` is gitignored, so the report must either embed
   them from local paths for the Overleaf upload, or you note that the figures are generated by the scripts.

**Status tags in the report:** carry the project convention — [established]/[derived]/[measured]/[inferred]/
[unverified]. Every curve under noise is "a classical prediction under an assumed model, NOT an H2 result." Cite
sources from `Conversation history/sources.md` (the tracked bibliography lives there; the key refs are also in
`docs/findings_vs_questions.md`).

**Done-check (report):** compiles with pdfLaTeX from a clean dir (test it: `pdflatex` twice); the findings table is
present and every row maps a conclusion to its evidence file; no number is invented or presented as hardware; the
honest framing is intact; it does not depend on `Conversation history/` (gitignored) for any tracked content.

---

## 4. THE SELF-REVIEW PROTOCOL (you replace the independent reviewer)
Kiro's reviews caught real errors because they were **independent and re-derived from scratch**. You cannot be truly
independent of yourself, but you MUST approximate it. **After each milestone (the report; each hardware goal), before
calling it done, run this protocol and write the result to `review/NN-*.md` (continue the numbering; next is
review/13):**

1. **Re-derive, don't restate.** Recompute each load-bearing number with a *different method or fresh code* than the
   one that produced it (e.g. check a Stim accounting number with a direct `expm`/enumeration; check a fit with an
   independent `polyfit`; check a qubit count with a direct `.n_phys`). Quote the two numbers and their difference.
   This is exactly how reviews 09–12 worked — see them as templates.
2. **Re-run the suite** and quote the count. If you added tests, state what they discriminate (a test that can't fail
   is not evidence).
3. **Separate "verified correct" from "could not verify."** List each explicitly. "mtime ≠ content/authorship";
   if you can't check something, say so, don't assume it.
4. **Severity-tag findings** C(ritical)/M(ajor)/m(inor). If you find a Critical or Major in your own work, FIX it
   before proceeding, then re-review.
5. **Honesty audit:** does any sentence overclaim? Is every noisy number labelled classical-not-H2? Is any
   hardware-gated result implied to be done? Is a degenerate single-vector quantity being interpreted?
6. **Verdict line** at the top: ACCEPT / ACCEPT-WITH-FIXES / REJECT. Only ACCEPT (or ACCEPT-WITH-FIXES after applying
   the fixes) lets you call the milestone done.

A self-review that just agrees with the work is worthless and worse than none (false confidence). Be adversarial.

---

## 5. JOB 2 — the hardware path (handoff/05), ONLY on Kevin's approval
Everything here is **gated**: nothing contacts Quantinuum without `allow_hardware=True` **and** Kevin's explicit
per-run approval, with the HQC cost estimate recorded first (SCOPE §5). The `nexus` backend raises by design until
then. Do NOT flip it on your own.

- Read `handoff/05-hardware-gated-followups.md` (goals G1–G4) and `docs/nexus_toggle.md` (the 7 integration steps:
  gate → deps `qnexus`/`pytket-quantinuum` → auth/project → device → compile/submit path (b) keeps feedforward →
  HQC cost → map results to `ShotRecord`).
- **Order:** G1/HW-5 (Iceberg 2×2, 1 step, H2 **emulator**, vs the Selene+Stim predictions) → G2 (measure η, ε;
  rerun `scripts/run_noise_sensitivity.py` at them) → G3 (encoded-vs-bare on H2, matched shots — the decisive Q1
  test) → G4 (active correction for d≥3, design in Stim+Selene first).
- **Labelling rule (non-negotiable):** every number states classical-prediction vs H2-*emulator* vs H2-*hardware*;
  never mix. Stim proves fault-tolerance; hardware does not. Randomized compiling is ON for encoded H2 runs (R-7).
- Self-review each goal (§4) and record it; update `docs/findings_vs_questions.md` Q1/Q4 and the journal.

---

## 6. Relay backlog — small doc/data fixes to fold in (do these; they were Kiro-recorded for Claude Code)
- **T-19:** add a one-line caveat to `data/frustration_compare.txt` and `scripts/compare_frustration.py` — the 3×4
  square torus is odd-length-frustrated (not a clean reference); only 4×4 is bipartite/unfrustrated. See
  `docs/q2_frustration.md` A.2. (These are your own old files.)
- **review/11 minors (Q3 Part B):** m1 the §8 "≤1e-10" wording vs achieved ~1e-13; m2 `C1` vs `C(0.866)` label
  consistency across data files; m3 add a content-hash or "regenerated identically" note so `mcmc_baseline.txt`'s
  identical-rerun claim is checkable.
- **review/12 minors (Q2 Part A):** m1 pin the "14 tests" count in the three places; m2 state the worst ΔE (2.6e-12)
  consistently; m3 tag the square h_c value [unverified] for symmetry with the triangular tag.
- **T-15 (check):** the `docs/gauss_law_dimers.md` → `docs/q3_thermalization.md §8` cross-reference for the
  start-dependent defect-density Trotter inflation — confirm it was applied (review/11 said m2/T-15 done); if not, add it.
- Confirm the full suite stays green after any doc/data edit (docs shouldn't move it, but check).

---

## 7. Discipline you must self-enforce (from KIRO.md — these are why the project is trustworthy)
- **Verify, don't trust.** Re-run claims with the actual tool before acting on them. "Reported ≠ verified."
- **Never invent numbers, citations, or results.** Tag everything [established]/[derived]/[measured]/[inferred]/
  [unverified]/[assumed]. Report failures and your own mistakes plainly.
- **Every noisy curve is a classical prediction under an assumed model, never an H2 result** — until it is one, and
  then label it emulator vs hardware.
- **Don't modify the verified cores** except additively (`src/operators.py`, `trotter.py`, `observables.py`,
  `src/qec/*`, `compare.py`, `encoded_tfim.py`, `encoded_codes.py`, `dimers.py`, `mcmc_baseline.py`,
  `trotter_threshold.py`, `noisy_q3.py`, `frustration.py`). Comments-only when annotating.
- **Ceilings (SCOPE §5):** ED ≤ 20 spins, statevector ≤ 24; the physical register is what counts; Stim unbounded.
  Refuse before allocating.
- **Hardware/push/repo/SCOPE changes are Kevin's** — gate on his explicit approval.
- **Keep the registers current** (this is how a session with no memory resumes): after each pass update
  `handoff/plan.md` (registry), `Conversation history/open-questions.md` (add/resolve/move, keep tags),
  `docs/findings_vs_questions.md` (when a Q row changes), and append a `## Entry N` to
  `Conversation history/project-journal.md` (check the last number first — this brief's pass is Entry 42; yours start
  at 43). The `Conversation history/` folder is gitignored — never pushed.

---

## 8. Authoritative pointers (read these, in this order, at the start of a session)
1. `SCOPE.md` — the contract (§1/§2 now carry the thesis; §5 ceilings; §13 report; §14 autonomy).
2. `CLAUDE.md` — your working rules in this repo.
3. `Conversation history/project-journal.md` — the ★ thesis box, the status board, and the latest entries (up to
   Entry 42, this transfer).
4. `Conversation history/open-questions.md` — the ★ FLAG-0 banner (the Q1 go/no-go), §A hardware-gated, §B Kevin's
   decisions, §C technical, Resolved (R-1…R-12).
5. `handoff/plan.md` — the handoff registry (§1–§20).
6. `docs/findings_vs_questions.md` — the Q1–Q4 + Gauss map; the report's backbone.
7. The deliverable docs: `docs/encoded_tfim.md`, `docs/gauss_law_dimers.md`, `docs/q3_thermalization.md`,
   `docs/q2_frustration.md`, `docs/qec_feasibility.md`, `docs/concatenated_iceberg_d4.md`, `docs/q1_compare.md`,
   `docs/nexus_toggle.md`; `handoff/05`.
8. `Conversation history/sources.md` — the tracked bibliography (status-tagged).

## 9. Done-check for this transfer (how Kevin knows the project is finished)
- The SCOPE §13 LaTeX report exists in `docs/`, compiles on Overleaf, has the findings table, and is honest
  (self-reviewed, review file written).
- The relay backlog (§6) is applied; suite green.
- The hardware path is either run (with Kevin's approvals + labels + self-reviews) or clearly left as the
  documented, gated next step if Kevin has not green-lit hardware.
- The registers reflect final state; a journal entry records the project's completion status.
- Nothing invented; classical vs hardware never mixed; nothing pushed without Kevin.

**That is the whole job. Work through §2 in order, self-review each milestone (§4), keep the registers current, and
ask Kevin for the decisions marked his. Kiro is offline — you are the overseer now.**
