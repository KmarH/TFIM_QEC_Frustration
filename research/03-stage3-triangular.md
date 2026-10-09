# Research Note 03 — Stage 3 (triangular lattice) conventions and scope boundary

**Purpose:** minimal literature pass to build the triangular-lattice TFIM geometry
correctly (SCOPE §4 stage 3, the MAIN scientific focus). In service of code.
Status tags: [established] standard, [inferred] reasonable, [unverified] not checked
against a primary source, [BOUNDARY] route to Claude Code if a derivation is needed.

## Reproduction target geometry [established]
Haghshenas et al. arXiv:2503.20870 (Nature 653, 56–62 (2026)), abstract re-fetched
2026-10-06: "By reprogramming our simulations to take place on a **triangular lattice
with periodic boundary conditions**, we observe thermalization consistent with emergent
gauge and topological constraints resulting from lattice frustration." So Stage 3 uses a
**triangular lattice, periodic BC**. The exact lattice dimensions, the specific
inhomogeneous initial states, and the dimer/Gauss-law observable definitions are in the
paper's supplement — NOT extracted here; do not hardcode their numbers. [unverified]

## Triangular lattice geometry [established]
A triangular lattice is a 2D Bravais lattice where each interior site has **6 nearest
neighbours** (coordination number 6). A common coordinate realization places sites on an
Lx×Ly grid (row-major n = y*Lx + x) with three primitive bond directions:
  d1 = (+1, 0)      horizontal
  d2 = (0, +1)      vertical
  d3 = (+1, +1)     one diagonal   (choice of diagonal sets the orientation)
The three directions give each site 6 neighbours (±d1, ±d2, ±d3). Periodic BC wrap each
direction modulo Lx / Ly. This is the standard "square grid + one diagonal" embedding of
the triangular lattice; it is the simplest geometry that reproduces coordination 6 and
the frustrated elementary triangles. [established]

Why it frustrates (TFIM, antiferromagnetic reading): on a single triangle with
antiferromagnetic ZZ, the three bonds cannot be simultaneously satisfied — the hallmark
of geometric frustration. In OUR convention H = -J Σ ZZ with J>0 (ferromagnetic), the
frustration appears instead in the field/dynamics and in the degeneracy structure; the
TFIM sign convention is kept consistent with Stage 1, and frustration is probed through
observables (dimer/constraint language) rather than by flipping the coupling sign without
reason. The coupling sign to use for the frustrated comparison is a modelling choice to
confirm against the reproduction target's convention before any physics claim. [inferred]

## Observables added in Stage 3 (HANDOFF §3 triangular additions)
- **Dimer correlations**, **winding-number sectors**, **constraint violations.**
  [BOUNDARY] Their precise operator definitions come from the quantum-dimer / emergent
  Gauss-law mapping of the frustrated triangular Ising model. SCOPE §3 explicitly flags
  this thread as "skeptical — do NOT assume it works," and HANDOFF warns against inventing
  derivations. Therefore:
    * The triangular GEOMETRY, Hamiltonian, standard observables (magnetization, energy,
      two-point ZZ correlations, relaxation) — reuse Stage-1 infra, BUILD now, testable
      against ED on small clusters.
    * The DIMER-CONSTRAINT / GAUSS-LAW observable definitions and any claim that the
      emergent Gauss law can serve for error detection/mitigation — if these require a
      derivation with nothing in the literature to check against, that is a Claude Code
      hand-off (write handoff/NN-task.md), NOT invented here.

## Build plan for Stage 3 scaffold (this step) [plan]
1. Extend `src/lattice.py` with `triangular_bonds(Lx, Ly, boundary)` returning the 6-nn
   edge list (unique, ordered), with the degenerate-wrap guards (as the square case).
2. Wire `geometry="triangular"` through `src/backends.py:_bonds_for` so ED/statevector
   run on the triangular lattice with ZERO change to the TFIM operator/Trotter/observable
   code (they are geometry-agnostic — they take a bond list).
3. Tests: triangular bond counts (interior coordination 6; periodic torus = 3N bonds),
   frustrated-triangle check, and statevector-vs-ED agreement on a small triangular cluster
   (reusing the Stage-1 validation pattern) — confirming the TFIM machinery is correctly
   geometry-general.
4. STOP before dimer/Gauss-law observable definitions; write a handoff brief for that part.

## Literature anchors (added from qc-scout sweep 02, graduated by review/06)

- **Phase diagram [established]:** Isakov & Moessner, PRB 68, 104409 (arXiv:cond-mat/0302105)
  — the canonical triangular-TFIM phase diagram: an extended BKT critical phase separating the
  paramagnet from a quantum-fluctuation-driven three-sublattice (clock) ordered phase, with a
  3d-XY-universality quantum critical point. Explicit clock-order pattern (M, −M/2, −M/2), M<1 by
  order-by-disorder: Humeniuk, PRB 93, 104412 (arXiv:1602.02979 [fetched]). NOTE: the project does
  not yet compute a 3-sublattice order parameter, so no clock-order claim is graduated as [measured]
  (building that observable is a scope decision — review/06 K3).

- **Floating-phase / disorder-line interpretation guard [established]:** the "square + one diagonal"
  embedding used here is exactly the J′=J point of the anisotropic model of Iglovikov et al.,
  PRB 87, 214415 (arXiv:1303.0883), which hosts a Stephenson disorder line (Néel→incommensurate) and
  an incommensurate floating phase at larger J′. The square-vs-triangular ⟨ZZ⟩ contrast may therefore
  be incommensurate / non-monotonic and finite-size-sensitive — do not read a clean "frustration
  monotonically weakens order" story into it.
