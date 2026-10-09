# Handoff 02 — Triangular TFIM: dimer / winding / Gauss-law observables

**Route to:** Claude Code (SCOPE §10/§14 — new derivation with nothing in the literature
to check against; SCOPE §3 explicitly marks this thread "skeptical — do NOT assume it
works"). **Agents cannot launch it; the project lead runs it.** Written by qc-overseer.

## Why this is a hard stop (not invented)
The triangular-lattice TFIM is BUILT and verified in this repo for the solid, checkable part:
- `src/lattice.py:triangular_bonds` — 6-nn triangular geometry (square grid + one diagonal),
  periodic BC default, de-duplicated; periodic torus has 3N bonds, coordination 6
  (tests in `tests/test_triangular.py`).
- The Stage-1 TFIM operator/Trotter/ED/statevector machinery is geometry-agnostic and runs
  unchanged on triangular bonds — ED-vs-dense and statevector-vs-expm agree on small clusters.
- Standard observables (magnetization, energy, two-point ZZ correlations, relaxation) already
  work on the triangular lattice via the existing `src/observables.py`.

What is NOT built, and must not be invented here:
- **Dimer correlations, winding-number sectors, and constraint-violation observables** for the
  frustrated triangular Ising model. These rest on the quantum-dimer / emergent-Gauss-law
  mapping of the frustrated triangular TFIM. The precise operator definitions, the mapping from
  spin configurations to dimer coverings, the winding-number sector labels, and the Gauss-law
  constraint operator are a DERIVATION. The reproduction target (arXiv:2503.20870) states the
  physics ("emergent gauge and topological constraints resulting from lattice frustration") in
  its abstract but the operational definitions live in its supplement and are not pinned to a
  single checkable equation set here. Inventing them would violate SCOPE §3/§12.

## Goal
Produce, with correctness arguments and literature anchors:
1. The spin→dimer mapping for the frustrated triangular Ising model (which bonds/triangles map
   to dimers; the exact convention and the coupling-sign choice relative to our H = -J ΣZZ).
2. Explicit operator definitions (as functions of Pauli-Z/X on the existing site indexing) for:
   dimer–dimer correlation functions, winding numbers per direction, and the local
   constraint-violation (Gauss-law) operator.
3. The emergent Gauss law statement: the approximate conserved quantity, its order in the
   relevant small parameter, and what a violation means physically.
4. A skeptical assessment (SCOPE §3): whether this Gauss law can serve for error
   detection/correction/symmetry-based mitigation, on which platforms, benchmarked against
   exact-symmetry methods (GUESS, symmetry-adjusted shadows, Cai), ZNE, PEC — with explicit
   noise-model assumptions. This is a yes/no-and-where, defensible, not assumed positive.

## Inputs (already in repo)
- `src/lattice.py` (triangular geometry), `src/operators.py`, `src/observables.py`,
  `src/trotter.py`, `src/backends.py` — all geometry-agnostic and ready to consume new observables.
- `research/03-stage3-triangular.md` (geometry conventions + this scope boundary).
- `drafts/gauss_law_self_mitigation_assessment.md` — the user's UNVERIFIED draft; SCOPE §11
  flags several of its arXiv IDs as future-dated (GUESS 2603.13060, 2604.*, 2608.*). Treat its
  numbers/claims as unverified; qc-researcher must confirm every citation; report non-resolving
  IDs, never invent one.

## Constraints
- Observables must be functions on the existing row-major site index and the triangular bond list;
  plug into `src/observables.py` style (expectation values on a statevector or ED eigenvector).
- No invented citations/numbers; mark everything established/inferred/unverified.
- Local/ED/statevector only within SCOPE §5 ceilings; no hardware.
- The coupling-sign / frustration convention must be stated and justified against the reproduction
  target before any physics claim.

## Done-check
- Dimer/winding/constraint operators defined and implemented; on a small triangular cluster their
  values are cross-checked against ED (e.g. winding sectors are integer-valued and conserved under
  the appropriate dynamics; the Gauss-law violation is zero on the constrained subspace and grows
  as predicted off it).
- A written, benchmarked, skeptical yes/no-and-where for the Gauss-law mitigation thread.

## What the reviewer must verify
- That the dimer mapping and constraint operators match a cited source (or are a clearly-marked
  derivation with a proof), that winding numbers are genuinely conserved/sector-labelling on the
  cluster, that the Gauss-law violation scaling is measured not assumed, and that any mitigation
  claim separates the physics floor from the noise signal with a stated noise model and survives
  its uncertainty (SCOPE §3). Flag any overclaim; the default skeptical prior is "it may not work."
