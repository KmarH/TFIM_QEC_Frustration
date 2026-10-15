# Handoff 09 — Q2 thickening: triangular-vs-square frustration on shared observables, with a size trend and error bars

**Route to:** Claude Code. Multi-observable comparison build on top of existing machinery; larger brief
allowed (PROC-1) — if it grows, land the distance-resolved correlation comparison (Part A) as a reviewable
checkpoint before the size trend (Part B). Agents cannot launch Claude Code; the project lead runs it. Written by qc-overseer.

## Why this exists
Q2 (frustration) is the **least pre-empted novelty** (journal Entry 15) and, with Q3 now complete at reachable
sizes, the main remaining **local, non-hardware** scientific thread. Its "done when" is a *triangular-vs-square
comparison on the frustration observables*; today only a single-cluster (3×4) ground-state table exists
(`data/frustration_compare.txt`: energy/bond, |M_z|, mean ⟨ZZ⟩, triangular defect density). The findings table
(`docs/findings_vs_questions.md`, Q2 row) marks it **PARTLY done**, with these gaps named: "dimer-correlation
and winding-distribution contrasts triangular *vs* square, and larger sizes, are not yet tabulated."

This brief closes the defensible part of that gap. **It does NOT build a 3-sublattice / clock-order parameter**
— that is K3, which the project lead has left INCONCLUSIVE. Do not build clock order here.

## The honest framing to hold throughout (do not overclaim)
- **Dimers, winding, and defects are triangular constructs** (from the frustrated-triangular Gauss-law/dimer
  mapping). The square lattice is unfrustrated and has **no dimer/defect description** (`frustration_compare.txt`
  says this). So the comparison is NOT "run the same dimer observable on both lattices." The honest contrast is:
  (a) **shared observables that genuinely exist on both** (energy/bond, distance-resolved connected ⟨ZZ⟩,
  magnetization and its fluctuation), compared like-for-like; plus (b) the **presence on triangular vs
  absence/triviality on square** of the frustration-specific structure (winding sectors, defect density).
- **Disorder-line / floating-phase guard [established].** The repo's triangular embedding ("square + one
  diagonal") sits at the J′=J point of Iglovikov et al. (PRB 87, 214415, arXiv:1303.0883), near a Stephenson
  disorder line / incommensurate floating phase. So the square-vs-triangular ⟨ZZ⟩ contrast may be
  **incommensurate / non-monotonic / finite-size-sensitive** — do NOT read a clean "frustration monotonically
  weakens order" story into it. State this caveat where the correlations are reported (it is already in
  `docs/findings_vs_questions.md` Q2).
- **Classical ED/exact only.** No noise, no encoding, no hardware here (those are Q1/Q4/hardware threads). Every
  number is [measured] (exact) with its uncertainty where sampling enters.

## Part A — distance-resolved connected correlations, square vs triangular (CHECKPOINT)
**Goal:** the first genuinely like-for-like Q2 observable beyond energy/bond — the **connected ⟨Z_iZ_j⟩_c binned
by lattice distance**, C(r), for square and triangular at matched size/field, as a function of h.

- Build C(r) from the existing `src/observables.two_point_correlations_z(psi, n, connected=True)` (it returns all
  connected pairs) by binning pairs by their **lattice graph/torus distance** on each geometry. For triangular,
  reuse the distance convention already in `src/dimers.py` (`torus_distance` / `bond_position`) so the metric is
  consistent with the repo; for square, bin by the periodic Manhattan/Euclidean site distance. State the metric.
  (The C_r graph-vs-Euclidean subtlety is T-7 and concerns the *dimer* C_r vs 2503.20870; here it is site-spin
  ⟨ZZ⟩_c and the metric choice just needs to be stated and identical in spirit across the two lattices.)
- Report C(r) vs r for both lattices at h ∈ {0, 0.1, 0.3, 0.6, 1.0} (match `frustration_compare.txt`), ground
  state by ED (`run_ed`). At h=0 the ground state is degenerate — handle exactly as the existing script does:
  do not interpret single-vector ⟨ZZ⟩/M_z at h=0 (basis-dependent); the h>0 correlations are the signal.

  > **Note added 2026-10-15, corrected the same day.** This field grid (h ∈ {0, 0.1, 0.3, 0.6,
  > 1.0}) is the project's own choice, and that part stands. But the earlier version of this note
  > went on to say 0.3 is "not the reference's triangular field" — **that is wrong.** The paper's
  > Figure 4(e) states verbatim "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)", and §V's body sets
  > a weak transverse field on a 9×6 lattice, so **h/|J| = 0.3 *is* the reference's triangular
  > field** and the project's triangular dynamics work matches §V. The h/|J| = 2 reading came from
  > the released `quench4_*.qasm` files, which carry the square quench's field angle and are
  > defective (`research/05-zenodo-dataset-map.md` §3). [established]
  >
  > Q2 itself is untouched either way: it is a **ground-state ED** result, not quench dynamics, and
  > its 3–5× weakening also holds at h/|J| = 2 (ratio 4.98 on the matched 4×4 pair;
  > `docs/q2_frustration.md` A.3). This brief's result is unchanged.
- **Interpretation to record (honestly):** on the unfrustrated square lattice C(r) should show the stronger /
  more ordered AFM correlation; on triangular, frustration should weaken/modify it — but flag the
  disorder-line/floating-phase caveat so a non-monotonic or incommensurate C(r) is not misread.

**Part A done-check (checkpoint — stop and report):**
- A comparison script (suggested `scripts/compare_frustration_correlations.py`) → a data file
  (`data/frustration_correlations.txt`), C(r) for both lattices across the field list, with the metric stated
  and the disorder-line caveat in the header.
- Tests (extend `tests/test_triangular.py` or a new file) pinning: C(r) uses the connected form; the binning is
  correct on a known small case; square C(r) is more negative/ordered than triangular at a representative h>0
  (the frustration signature) — or, if that fails because of the floating-phase physics, the test asserts the
  *measured* relation and the doc explains it (do not force a story the data doesn't support).
- Full suite green (state the new count). All [measured], classical, no H2.
- **STOP for a Kiro (qc-reviewer) checkpoint review before Part B.**

## Part B — size trend and error bars  — ❌ CANCELLED (the project lead, 2026-10-08, PROC-2)

> **DO NOT BUILD PART B.** The project lead cancelled it under PROC-2 (no new classical depth after handoff/09; next work is
> the LaTeX report, then HW-5). Part A is reviewed and accepted (review/12) and already answers Q2's core
> like-for-like gap (the nearest-neighbour frustration signature in correlation form). A square size trend would
> anyway have only one clean bipartite point within the ED ceiling (4×4; T-21), so its added value is limited.
> This section is kept for traceability only — the goal/observables below describe what was *not* built.

**Goal (NOT built):** turn the single-cluster snapshot into a **size trend with uncertainties**, the other named gap.

- Repeat the Q2 observables (energy/bond; C(r) at a representative h; triangular defect density and winding-sector
  structure) across the sizes reachable within SCOPE §5 ceilings (ED ≤ 20 spins; e.g. square and triangular at
  3×3, 3×4, 4×4, 4×5, and any other torus ≤ 20 that gives a fair square↔triangular pair). State which sizes are
  honest for each lattice (triangular needs Lx,Ly ≥ 3 for the dimer mapping).
- **Error bars:** where a quantity is an exact ED expectation, it has no sampling error — say so. Where you report
  a *degeneracy-sensitive* quantity at or near h=0, quantify the ambiguity honestly (e.g. ground-state degeneracy
  / gap) rather than quoting a single-vector artifact. If any Monte Carlo / sampling enters, use
  autocorrelation-aware or bootstrap errors (as handoff/07 did), not naive 1/√N.
- **Winding-sector contrast (triangular only, honest):** tabulate the winding-sector structure (number of
  sectors, defect density vs h) across sizes using `src/dimers.py`, and state plainly that the square lattice has
  no such structure — this is the presence-vs-absence contrast, not a like-for-like number.
- **Size story, no overclaim:** report the trend across reachable N; do NOT claim a thermodynamic-limit phase
  statement (same discipline as Q3 §7). The canonical phase diagram (Isakov–Moessner, Humeniuk) is a cited
  *anchor* for what the trend is consistent with, not a result to reproduce — import no numbers from it, and
  **do not build the clock-order parameter (K3)**.

**Part B done-check:**
- The size-trend data (suggested `data/frustration_size.txt`) + any new figure via the existing `scripts/plot_q3.py`
  pattern (optional; matplotlib is now available) — reproducible from saved data if a figure is made.
- `docs/` write-up (extend the Q2 section of `docs/findings_vs_questions.md`, or a short `docs/q2_frustration.md`)
  stating the shared-observable contrast, the frustration-specific presence/absence contrast, the size trend, the
  disorder-line caveat, and the explicit non-claims (no thermodynamic limit, no clock-order parameter).
- Full suite green; `docs/findings_vs_questions.md` Q2 row advanced from PARTLY toward DONE-at-reachable-sizes.
- A journal entry + `open-questions.md` update.

## Inputs (real repo APIs — use these)
- `src/observables.py`: `two_point_correlations_z(psi, n, connected=True)`, `expval_zz`, `total_magnetization_z`,
  `magnetization_variance_z`.
- `src/backends.py`: `run_ed(cfg, k)` (ceiling-guarded ED ground state).
- `src/lattice.py`: `square_bonds(Lx, Ly, boundary)`, `triangular_bonds(Lx, Ly, "periodic")`, `site_index`, `coord`.
- `src/dimers.py`: `TriangularDimers` (`defect_density`, winding, `torus_distance`, `bond_position`) — triangular
  frustration-specific observables and the distance metric.
- `scripts/compare_frustration.py` → `data/frustration_compare.txt` (the existing single-cluster table to extend,
  not duplicate), `config.py` (`RunConfig`, ceilings).
- `docs/findings_vs_questions.md` Q2 row + its phase-diagram anchor and disorder-line/floating-phase caveats
  (already written — carry them, don't re-derive).

## Constraints (hard)
- Classical ED/exact only; within ceilings (ED ≤ 20, statevector ≤ 24; refuse, don't truncate). No noise, no
  encoding, no hardware, no Nexus, no push, no SCOPE change.
- Additive only; do not modify the verified cores except additively (new scripts/tests/docs + optional additive
  observable helpers).
- **Do NOT build the 3-sublattice / clock-order parameter (K3) or the diffusion observable (K5)** — both are
  undecided (INCONCLUSIVE). If the physics seems to call for clock order, STOP and flag it for the project lead, don't build it.
- Never invent numbers; tag [measured]/[derived]; state the distance metric and the degeneracy handling.
- One Claude Code session; land Part A before Part B (PROC-1 checkpoint).

## What the reviewer (qc-reviewer) must verify
- **Part A:** C(r) is the connected correlator, binned by a stated consistent distance metric on each lattice;
  the square-vs-triangular contrast is reported honestly with the disorder-line caveat (no forced
  "frustration-weakens-order" story); h=0 degenerate single-vector artifacts are NOT interpreted; reproducible
  from `run_ed`.
- **Part B:** the size trend is within ceilings; uncertainties are honest (exact = no sampling error stated;
  degeneracy quantified; any MC error autocorrelation-aware); the winding/defect contrast is framed as
  presence-vs-absence, not a false like-for-like; no thermodynamic-limit or clock-order claim; figures (if any)
  reproducible from saved data.
- Across both: ceilings respected, cores additive, everything classical/[measured], K3/K5 not built.

---

## Note appended by Claude Code at the project lead's request (2026-10-08, PROC-2, journal Entry 39)
**This is the last classical-depth brief.** The project lead decided to stop adding classical depth after handoff/09. The next
briefs are (1) the LaTeX report (SCOPE §13) and (2) hardware-path preparation, starting with HW-5 (handoff/05 G1).
Within this brief, keep to the stated scope: no extra classical studies beyond Parts A and B.

