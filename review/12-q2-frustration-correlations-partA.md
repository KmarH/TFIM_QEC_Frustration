# Review 12 — Q2 frustration, handoff/09 **Part A** (distance-resolved connected C(r), square vs triangular)

**Reviewer:** qc-reviewer (independent checkpoint). **Date:** 2026-10-08.
**Scope:** Part A ONLY (checkpoint before Part B). Per PROC-2 (open-questions §B, journal Entry 39)
Kevin stopped new classical depth after handoff/09; whether Part B (size trend) is released is the
overseer's call with Kevin, not mine. This review judges Part A on its merits.
**Deliverables reviewed:** `src/frustration.py`, `tests/test_frustration.py` (14), `scripts/compare_frustration_correlations.py`
→ `data/frustration_correlations.txt`, `docs/q2_frustration.md` (Part A), `config.py:Q2FrustrationConfig`,
`docs/findings_vs_questions.md` Q2 row, journal Entry 40, `handoff/plan.md` §20, open-questions T-19/T-20/T-21.
**Method:** re-derived and re-ran the load-bearing claims with my OWN code (full-space Lanczos +
my own connected correlator, independent of their even-sector path), plus the full pytest suite.

---

## VERDICT: **ACCEPT-WITH-FIXES** — no Critical, no Major. Three minor items (doc/data wording), all Claude Code's to apply.

Everything load-bearing is **verified correct with independent evidence**: the P-even construction is
correct AND necessary (the symmetry-broken-Lanczos artifact is real and is removed), C(r) is the
connected correlator binned by the stated metric, the frustration signature reproduces to the 5th
decimal under my own ED, the T-19 correction is **sound**, and the disorder-line / torus-shape honesty
holds (no overclaim). K3/K5 not built; ceilings respected; everything classical/[measured]; cores
touched additively only. Full suite **231/231** (independently run, 129 s). The minor items are
cosmetic and do not block the checkpoint.

- **T-19 (one line):** the correction is **SOUND and verified** — square 3×4 h=0 E/bond = −2/3, 4×4 = −1
  (my own ED), so the old table's "3×4 unfrustrated square reference" is genuinely wrong; and it is
  **honestly flagged** (raised as T-19, NOT silently edited into Claude's prior `frustration_compare.txt`).
- **T-21 (one line):** **correct** — within ED≤20 the only even×even square torus with both lengths ≥ 3
  is 4×4 (I enumerated: 4×6=24, 6×6=36 both exceed the ceiling), so "only 4×4 is a clean square reference
  within the ceiling" is right, and it correctly bounds what a Part B square size-trend could use.

---

## (A) Verified correct — with evidence

### A1 — P-even ground state is correct AND necessary (checklist item 1) ✓✓✓
**(1a) Even-sector energy == full ED.** My independent full-space Lanczos (`scipy.eigsh` on the raw
`tfim_hamiltonian`, no even-sector trick) vs `even_sector_ground_state`:

| geom | size | h | E_even | E_full(mine) | ΔE |
|---|---|---|---|---|---|
| square | 4×4 | 0.3 | −32.180084494788 | −32.180084494788 | −3.6e-14 |
| square | 4×4 | 0.6 | −32.721357886853 | −32.721357886853 | −7.1e-15 |
| triangular | 4×4 | 0.6 | −17.906631022497 | −17.906631022497 | −3.2e-13 |
| triangular | 3×4 | 0.3 | −13.243885412150 | −13.243885412150 | −1.6e-13 |
| square | 3×4 | 1.0 | −18.913856283923 | −18.913856283923 | +7.1e-15 |

Agreement 1e-13…1e-15 on both lattices at several (size,h) — matches the claim ("≤3e-12", Kiro's "~1e-13").
The data file's own `dE_ED` column (`−7.1e-15` … `−2.6e-12`) is consistent. `src/frustration.py:72-83`.

**(1b) Perron–Frobenius sanity.** For h>0 I confirmed every off-diagonal element of H in the Z basis
equals −h (max off-diag real part = −0.600 at h=0.6, −0.300 at h=0.3; all ≤ 0), and the off-diagonal
graph is **irreducible** (`scipy.csgraph.connected_components` → **1 component** on square 4×4 and
triangular 3×4). Off-diag ≤ 0 + irreducible ⇒ by Perron–Frobenius the (shifted) matrix has a unique
dominant eigenvector with constant-sign amplitudes ⇒ the ground state is unique, nodeless, and P-even
⇒ ⟨Z_i⟩ = 0 exactly. The argument in the module docstring (`src/frustration.py:9-16`) is correct.
*(Note: the PF uniqueness is proved on the FULL 2^N basis; the even-sector construction is then just the
efficient/clean representation of that unique state. The code builds the even block as
`H[:half,:half] + H[:half,half:][:,::-1]` — correct for the P=+1 symmetric combination.)*

**(1c) Artifact is real and is removed.** In the even sector I measured max|⟨Z_i⟩| = 1.1e-16 (square
4×4, h=0.3 and 0.6) and 3.5e-17 (triangular 4×4, h=0.6) — i.e. zero. I then **reproduced the artifact**:
an unrestricted full-space Lanczos vector on the near-degenerate 4×4 square at h=0.3 gave max|⟨Z_i⟩| =
**0.58, 0.32, 0.07, 0.18** across repeated calls — exactly the "~0.01 to ~0.5, arbitrary" behaviour the
doc describes, confirming the P-even restriction is *necessary*, not cosmetic. The gaps I measured —
E1−E0 = 9.9e-14 (h=0.3), 1.8e-10 (h=0.6), 5.5e-7 (h=1.0); E2−E0 ≈ 7.3–7.9 — match the doc's quoted
values and justify "below numerical resolution." `test_square_neel_pair_is_quasi_degenerate` pins this.

### A2 — Connected C(r) and the distance metric (checklist item 2) ✓
- C(r) uses `src.observables.two_point_correlations_z(psi, n, connected=True)` = ⟨Z_iZ_j⟩ − ⟨Z_i⟩⟨Z_j⟩
  (`src/observables.py:106-119`; `src/frustration.py:118-124`). Connected form verified to vanish on a
  product state (`test_connected_form_vanishes_on_a_product_state`).
- **r=1 shell == bond list on BOTH lattices**, re-derived independently (my own distance scan vs the bond
  sets): square 4×4 32/32, triangular 4×4 48/48, square 3×4 24/24, triangular 3×4 36/36 — all exact
  matches, and shell pair-counts sum to N(N−1)/2.
- Distance metric is the stated minimal-image Euclidean: square (x,y); triangular via `TriangularDimers._pos`
  (`src/dimers.py:139-140`, `(x−y/2, √3·y/2)`). Spot-checks: triangular (0,0)-(1,2) = √3 (next-nearest,
  same sublattice), square (0,0)-(1,1) = √2. Both reproduce. `test_triangular_metric_matches_the_dimers_embedding`.

### A3 — Frustration signature, reproduced with my own ED (checklist item 3) ✓
Using even-sector ψ + **my own** connected correlator (independent of their `correlation_by_distance`):
- square 4×4 h=0.6 **C(1) = −0.97737** (doc/data: −0.97737)
- triangular 4×4 h=0.6 **C(1) = −0.26788** (doc/data: −0.26788)
- ratio ≈ 3.6× — inside the claimed "3–5× weaker on triangular." Matched-pair summary (`data/frustration_correlations.txt`):
  sq C(1) −0.9994…−0.9365 vs tri C(1) −0.3325…−0.2040 across h ∈ {0.1,0.3,0.6,1.0}. ✓
- **⟨Z⟩=0 ⇒ C(1) = raw ⟨ZZ⟩/bond identity** verified: square mean raw ⟨ZZ⟩/bond = −0.97737 = C(1);
  triangular = −0.26788 = C(1) (equal to <1e-9). So C(1) restates the ZZ part of E/bond, as the doc states
  (A.3 "Reading"). Correctly framed as *not* independent new information.
- `test_frustration_contrast_is_measured_not_assumed` asserts the MEASURED relation (sq < −0.95, −0.35 <
  tri < −0.2, sq more AFM), not a forced story — good discipline.

### A4 — T-19 correction (checklist item 4) ✓ SOUND and HONESTLY FLAGGED
My own ED, h=0: square **4×4 E/bond = −1.00000** (bipartite, every AFM bond satisfied); square **3×4
E/bond = −0.66667 = −2/3**; square **4×5 = −0.80000**. An odd periodic length makes the torus
non-bipartite, so the AFM is itself frustrated — the correction is correct. `is_bipartite_torus`
returns the right truth table (`test_odd_square_torus_is_frustrated`). **Honesty:** the doc (A.2) raises
this as **T-19** and states explicitly "This was not silently changed in the existing files (they are
not this brief's files)" — I confirmed `data/frustration_compare.txt` and `scripts/compare_frustration.py`
are untouched by this pass, and T-19 in open-questions.md routes the fix to Kiro. Correct handling per
the KIRO.md "distinguish Kiro's files from Claude's" rule.

### A5 — Disorder-line / torus-shape honesty (checklist item 5) ✓
I reproduced the sign flip: triangular h=0.3, √3 shell = **+0.458 (3×4)** vs **−0.045 (4×4)**; r=2 shell =
**−0.688 (3×4)** vs **+0.413 (4×4)** — opposite signs, torus-shape dependent, exactly as A.3 reports.
The doc attributes this to the Iglovikov et al. (PRB 87, 214415, arXiv:1303.0883) J′=J disorder-line /
floating-phase caveat and explicitly refuses the "frustration monotonically weakens order" reading (A.3
bullet 3, A.5). "Same h ≠ same distance from criticality" **is** flagged (A.3: square h_c≈3.04|J| vs
triangular ≈1.6|J|, with the triangular value tagged "[unverified — recalled, not re-read]"). No overclaim.

### A6 — K3 / K5 not built (checklist item 6) ✓
No clock/3-sublattice order parameter and no diffusion observable exist in `src/frustration.py` (I read
the full module — only energy, gaps, C(r), max|⟨Z_i⟩|, bipartite check). A.4 flags where clock order
*would* be needed and defers it to Kevin via **T-20**; h=0 degenerate single-vector correlators are
printed in the data file but explicitly "NOT interpreted" (data header + A.1 + the `[h=0: ... NOT
interpreted]` tags in every h=0 row). Correct.

### A7 — Ceilings, classical, additive, cores (checklist item 7) ✓
- `check_ed_ceiling` refuses N>20 before allocating (`test_ceiling_refused_before_allocating`; 3×7=21 raises).
- Everything is classical ED; data file header and the doc banner say "[measured], NOT an H2/hardware
  result" — no H2 claim anywhere.
- `src/frustration.py` is a NEW module; it imports the verified cores (`operators`, `observables`,
  `lattice`, `dimers`, `backends`) without modifying them. No core file is edited (mtimes of
  `operators.py`/`observables.py`/`dimers.py` predate this pass). Additive-only honored.

### A8 — Suite & bookkeeping ✓
- **231/231** passed (my own run, 129 s). `tests/test_frustration.py` = **14** tests (my run).
- `config.py:Q2FrustrationConfig` present (J, fields, partA_clusters=((4,4),(3,4)), distance_decimals).
- journal **Entry 40** present; `handoff/plan.md` **§20** present; findings_vs_questions Q2 row updated;
  open-questions **T-19/T-20/T-21** present and correctly routed.

---

## (B) Could not verify (and why)
- **h_c values** (square ≈3.04|J|, triangular ≈1.6|J|): not computed here; the doc already tags the
  triangular one "[unverified — recalled, not re-read]." The verdict does not depend on them. (Not a defect
  — correctly flagged.)
- **Physical interpretation of the triangular long-distance signs** beyond "torus-shape dependent": the doc
  deliberately does NOT interpret these (disorder-line caveat), and the K3 observable that would settle it
  is not built (T-20). Agreeing with that non-claim; nothing to verify.
- The repeated-run |⟨Z_i⟩| 0.01–0.5 figures are "[measured, internal pre-review]"; I reproduced the
  *phenomenon* (0.07–0.58 across my runs) but the exact 0.01 lower end is run-dependent by nature. Immaterial.

---

## (C) Findings by severity

**Critical:** none.
**Major:** none.

**minor (all Claude Code's to apply — doc/data wording, not logic):**

- **m1 — "(14)" count is correct but worth a guard.** `docs/q2_frustration.md` header and the module/test
  docstrings all say "14"; the file has 14 test functions-worth after parametrization resolves to 14
  collected items (verified). No action needed unless tests are added — just noting the count is pinned in
  three places (header, `test_frustration.py` docstring, findings row) so a future edit must touch all three.
- **m2 — A.1 wording "equals ... to ≤ 3e-12".** My worst Δ was −2.6e-12 (triangular 4×4 h=0.1 in the data
  file) and −3.2e-13 in my own run; the "≤3e-12" bound is honest but the prose elsewhere says "~1e-13" —
  harmless, but Claude could state the actual max (2.6e-12) once rather than two different figures.
- **m3 — A.3 h_c sentence.** The square h_c≈3.04|J| is given without a tag while the triangular one is
  "[unverified]"; for symmetry the square value (standard QMC) could also carry a tag ([established] with a
  citation, or [unverified-recalled]). Cosmetic consistency only.

None of m1–m3 affects correctness or the checkpoint decision; record them in open-questions for Claude
Code's doc pass, per KIRO.md (review nits in Claude's files are Claude's to apply).

---

## Checklist roll-up (handoff/09 "What the reviewer must verify — Part A")
1. P-even GS correct & necessary — **VERIFIED** (A1): energy=ED to 1e-13…1e-15; PF off-diag≤0 + irreducible;
   max|⟨Z_i⟩|~1e-16 in-sector vs 0.07–0.58 for raw Lanczos.
2. Connected C(r), metric, r=1==bonds — **VERIFIED** (A2).
3. Frustration signature, independent reproduction, ⟨Z⟩=0 ⇒ C(1)=ZZ/bond identity — **VERIFIED** (A3).
4. T-19 correction sound & honestly flagged — **VERIFIED** (A4): 3×4 −2/3 vs 4×4 −1; raised not silently edited.
5. Disorder-line / torus-shape honesty, "same h ≠ same criticality" — **VERIFIED** (A5): sign flip reproduced,
   no monotonic-weakening story.
6. K3/K5 not built; h=0 recorded not interpreted — **VERIFIED** (A6).
7. Ceilings ≤20, classical/[measured], no H2, cores additive — **VERIFIED** (A7).
Suite **231/231** — **VERIFIED** (A8).

## Open items for the overseer / Claude Code
- Relay **m1–m3** (doc/data cosmetics) to Claude Code's next doc pass; none blocks the checkpoint.
- **T-19 fix** (`data/frustration_compare.txt` / `scripts/compare_frustration.py` "unfrustrated 3×4" wording)
  is open and routed to **Kiro** in open-questions — Part A correctly did not touch those files.
- **Part B / T-21:** 4×4 is the only clean square point ≤20; a square size-trend cannot be assembled from
  square tori within the ceiling without mixing in odd-length-frustrated tori. This materially constrains
  Part B — but whether Part B runs at all is the overseer's call with Kevin per PROC-2, not mine.

**Checkpoint result: ACCEPT-WITH-FIXES. Part A is a correct, honest, independently reproduced checkpoint;
the three minor items are Claude Code's to apply and do not block proceeding.**
