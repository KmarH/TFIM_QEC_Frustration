# Review 04 — Stage 3 triangular-lattice GEOMETRY scaffold

**Reviewer:** qc-reviewer (independent milestone review)
**Date:** 2026-10-06
**Scope reviewed:** `src/lattice.py:triangular_bonds` (new) + updated docstring,
`src/backends.py:_bonds_for` (triangular dispatch), `tests/test_triangular.py` (6 tests).
Supporting reads: `research/03-stage3-triangular.md`, `handoff/02-triangular-dimer-gauss-law.md`,
`SCOPE.md §3/§4`, `src/operators.py`, `src/observables.py`, `config.py`.
**Rule:** I did not edit any src/ or tests/ file. All numbers below are from commands I ran myself.

**Verdict: APPROVE.** The triangular geometry is correct and independently reproduced;
the TFIM machinery is genuinely geometry-agnostic; the dimer/winding/Gauss-law scope
boundary is respected and correctly deferred to `handoff/02`. No invented numbers. Two
MINOR documentation-staleness items and one pre-existing environment note; none block the
milestone.

---

## Environment

```
$ . /home/opc/KiroTest-project/.venv/bin/activate
$ python -c "import numpy, scipy, stim; print(numpy.__version__, scipy.__version__, stim.__version__)"
numpy 2.5.3 scipy 1.18.1 stim 1.16.0
```
Serial, local. Python runtime is **3.12.14** (pytest banner), not the 3.11 named in SCOPE §7
(see Minor-3).

---

## What passes plainly (independently verified)

### 1. `triangular_bonds` — periodic torus, uniqueness, ordering, no self-loops, degenerate cases

I reconstructed the neighbour set independently (iterating over **all six** signed primitive
directions `±(1,0), ±(0,1), ±(1,1)` and de-duplicating as unordered pairs) and compared to the
repo output, rather than trusting the repo's forward-only `{(1,0),(0,1),(1,1)}` loop.

```
=== periodic torus, Lx,Ly>=3 ===
L=3x3 N=9:  nbonds=27 (3N=27) coord_set={6} unique=True order=True noself=True sorted=True matches_ref=True
L=4x3 N=12: nbonds=36 (3N=36) coord_set={6} unique=True order=True noself=True sorted=True matches_ref=True
L=4x4 N=16: nbonds=48 (3N=48) coord_set={6} unique=True order=True noself=True sorted=True matches_ref=True
L=5x4 N=20: nbonds=60 (3N=60) coord_set={6} unique=True order=True noself=True sorted=True matches_ref=True
L=3x5 N=15: nbonds=45 (3N=45) coord_set={6} unique=True order=True noself=True sorted=True matches_ref=True
L=6x5 N=30: nbonds=90 (3N=90) coord_set={6} unique=True order=True noself=True sorted=True matches_ref=True
```
- `len(bonds) == 3N` holds for every periodic torus with Lx,Ly>=3. **Confirmed.**
- Every site has coordination exactly 6 (`coord_set={6}`). **Confirmed.**
- Edges unique, ordered `i<j`, no self-loops, and the returned list is sorted. **Confirmed.**
- The repo bond set **equals** my independent ±6-direction reconstruction. **Confirmed.**

Degenerate `Lx` or `Ly <= 2` and wrap-degeneracy cases (periodic) — these are where the
forward-only loop could in principle double-count a wrap pair. It does not, because the final
`set()` collapses any coincident forward/wrap pair:
```
=== degenerate small cases Lx or Ly <= 2 (periodic) ===
L=2x2: nbonds=6  unique=True noself=True matches_ref=True deg=[3]
L=2x3: nbonds=15 unique=True noself=True matches_ref=True deg=[5]
L=3x2: nbonds=15 unique=True noself=True matches_ref=True deg=[5]
L=1x4: nbonds=4  unique=True noself=True matches_ref=True deg=[2]
L=4x1: nbonds=4  unique=True noself=True matches_ref=True deg=[2]
L=1x1: nbonds=0  unique=True noself=True matches_ref=True deg=[]
L=2x4: nbonds=20 unique=True noself=True matches_ref=True deg=[5]
L=2x5: nbonds=25 unique=True noself=True matches_ref=True deg=[5]
```
No double-counting; every case matches my independent reconstruction; self-loops (e.g. L=1x1)
are dropped. The reduced coordination at L<=2 (deg 3 or 5 instead of 6) is the physically
correct consequence of a direction's forward and backward wrap landing on the **same** neighbour
— the set correctly keeps it as one edge rather than two. **Confirmed.** Open boundaries also
match reference (5/9/16/33 bonds for 2x2/3x2/3x3/4x4). **Confirmed.**

### 2. Frustrated elementary triangle (3-cycle in the bond set)

Independent triangle search over the adjacency graph (not the hardcoded sites in the test):
```
triangle in 2x2 open:     (0, 1, 3)
triangle in 3x3 open:     (0, 1, 4)
triangle in 3x3 periodic: (0, 1, 2)
triangle in 4x4 periodic: (0, 1, 12)
```
A 3-cycle exists in every tested cluster, i.e. the frustrated elementary triangle is present.
The open-2x2 bond set is `[(0,1),(0,2),(0,3),(1,3),(2,3)]`, so the test's claimed triangle
`{0,1,3}` (edges 0-1, 1-3, 0-3) is genuinely closed. **Confirmed.**

### 3. TFIM machinery is geometry-agnostic (my own clusters, not the repo asserts)

**ED vs dense `eigh`** — I checked the **four** lowest eigenvalues (the repo test checks only
the ground state), on open and periodic clusters:
```
3x2 open     n=6: max|E_ED - E_dense|[:4] = 1.243e-14
3x3 open     n=9: max|E_ED - E_dense|[:4] = 7.816e-14
3x3 periodic n=9: max|E_ED - E_dense|[:4] = 1.137e-13
```

**2nd-order Trotter statevector vs exact `expm_multiply`** — I used the inhomogeneous **`neel`**
initial state (far from any eigenstate), unlike the repo test's `all_up`, so convergence is a
real test of the integrator rather than of a near-stationary state:
```
3x2 open     n=6 T=1.0 steps=200: ||trotter-exact|| = 2.398e-05
2x3 periodic n=6 T=1.0 steps=400: ||trotter-exact|| = 2.352e-06
3x3 open     n=9 T=0.5 steps=300: ||trotter-exact|| = 1.745e-06
```
Both backends run **unchanged** on triangular bond lists and reproduce exact references.
`_bonds_for` dispatches `geometry="triangular"` -> `triangular_bonds(Lx,Ly,boundary)`;
the operator/Trotter/observable code consumes only the bond list and never special-cases
geometry. **Geometry-agnosticism confirmed.**

### 4. Scope boundary — dimer/winding/Gauss-law NOT implemented, no invented physics

Repo-wide search for the deferred observables:
```
$ grep -rn "dimer|winding|gauss|constraint.?violation|flippable|monomer" --include=*.py
tests/test_triangular.py:5:  "...The dimer / Gauss-law observables are"   (docstring: NOT built)
```
The only hit is the comment stating they are deliberately absent. `src/observables.py` contains
only the Stage-1 geometry-agnostic observables (Z/X expectation, M_z/M_x, Var(M_z), two-point ZZ,
energy) — nothing frustration-specific. No frustration/degeneracy/Gauss-law numeric claim appears
in code, tests, or the Stage-3 research note. `handoff/02-triangular-dimer-gauss-law.md` correctly
routes the derivation to Claude Code and cites SCOPE §3's skeptical prior. `research/03` tags the
observable definitions `[BOUNDARY]` and does not hardcode any paper numbers. **Scope boundary
correct; no invented numbers.**

### 5. Full suite green

```
$ python -m pytest -q
...........................................................              [100%]
59 passed in 5.27s
```
```
$ python -m pytest tests/test_triangular.py -v
6 passed in 0.26s
```
**59/59 confirmed**, Stage-3 file 6/6.

---

## Findings

### Critical
None.

### Major
None.

### Minor

- **Minor-1 (stale docstring, `config.py` `LatticeConfig`).** The docstring still reads
  `geometry currently "square"; "triangular" is reserved for Stage 3 (not implemented in Stage 1)`.
  As of Stage 3 the triangular path *is* implemented and wired through `_bonds_for`. Reason: the
  comment now contradicts behavior and could mislead. Fix: update the docstring to note triangular
  is live as of Stage 3. (Documentation only; the `Literal["square","triangular"]` type already
  admits the value, so no behavioral bug.)

- **Minor-2 (narrow docstrings referencing `square_bonds`).** `src/operators.py:tfim_hamiltonian`
  says ``bonds`` is the edge list "from `src.lattice.square_bonds`", and
  `src/backends.py:_bonds_for` module docstring is tagged "Stage 1 module". Both are now also fed
  by `triangular_bonds`. Reason: minor accuracy drift. Fix: generalize the wording to "a
  nearest-neighbour bond list (square or triangular)". No functional impact — the builder is
  already geometry-agnostic, as verified in check 3.

- **Minor-3 (pre-existing, not Stage-3 specific) Python version.** SCOPE §7 pins Python 3.11, but
  the venv runs 3.12.14. This predates Stage 3 and does not affect correctness of this milestone;
  flagging for the record so the pin and environment are reconciled before freeze.

---

## Notes on design choices (not findings)

- Returning `sorted(edges)` gives deterministic, reproducible bond ordering — good for seedless
  determinism of downstream ED/Trotter inputs.
- Default `boundary="periodic"` for `triangular_bonds` matches the reproduction target
  (arXiv:2503.20870, triangular lattice with PBC) per `research/03`. Note `square_bonds` defaults
  to `"open"`; the asymmetry is intentional and documented, but callers that switch geometry via
  `cfg.lattice` must still set `boundary` explicitly (the config default is `"open"`), so the
  function default only applies to direct `triangular_bonds(...)` calls. Not a bug; worth keeping
  in mind when wiring Stage-3 runs.
- The "square grid + one diagonal" embedding is the standard coordination-6 realization and is the
  correct minimal choice for the frustrated-triangle structure. Confirmed it produces 3-cycles
  (check 2). Physical frustration *claims* are correctly NOT asserted yet (deferred to handoff/02).

---

## Open items

1. (Minor-1/2) Refresh the stale `config.py` and `operators.py`/`backends.py` docstrings to reflect
   that triangular geometry is live — route to qc-annotator (docstring-only; no logic change).
2. (Minor-3) Reconcile the Python 3.11 pin (SCOPE §7) with the 3.12 venv before any environment freeze.
3. (Carried, out of scope for this milestone) The dimer/winding/Gauss-law observables remain a
   Claude Code hand-off (`handoff/02`). When implemented, the reviewer must verify: dimer mapping
   against a cited source, winding-number conservation/sector-labelling on a cluster, measured (not
   assumed) Gauss-law violation scaling, and that any mitigation claim separates physics floor from
   noise signal under a stated noise model (SCOPE §3). Default prior remains "it may not work."

**Verdict: APPROVE** — Stage 3 geometry scaffold is correct, independently reproduced, and
respects the scope boundary. Minor items are documentation/environment hygiene and do not block.
