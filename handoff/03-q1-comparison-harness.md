# Handoff 03 — Q1 comparison harness: logical-vs-physical vs Haghshenas et al. (2503.20870)

**Route to:** Claude Code (SCOPE §10/§14 — multi-file build against a fixed, external data
spec). **Agents cannot launch it; the user runs it.** Written by qc-overseer from the
researcher's verified dataset map.

## Goal (SCOPE Q1)
Build a comparison harness that loads the published Quantinuum H2 reference data for
arXiv:2503.20870 and compares it, with error bars, against this repo's own Trotter-simulated
observables — the quantitative "what changes with logical qubits vs bare physical qubits"
comparison on the **non-frustrated (square) lattice** that SCOPE Q1 requires. The harness is a
new module (e.g. `src/compare.py` + `scripts/run_compare.py`) plus tests; it must not alter the
verified simulation core.

## The data spec is FROZEN — read it first
`research/05-zenodo-dataset-map.md` is the authoritative input spec. It was produced by
downloading the dataset (md5 `7f388525390eebfdb791b23aeae059d0`), reading its README, and
extracting ground truth from the snapshot matrices and the QASM gate angles. **Do not
re-derive conventions from guesses; follow that note.** The load-bearing facts:

- **Dataset:** Zenodo DOI 10.5281/zenodo.18487089, zip `digital_quantum_magnetism_data.zip`.
  The harness must NOT hardcode a copy of the numbers; it loads the `.txt` files. Assume the
  unzipped `zenodo_data/` dir is provided at a configurable path (do not commit the 12.5 MB
  dataset into the repo; add a loader that points at a local path, and a tiny fixture subset
  under `tests/` for CI — see Done-check).
- **Quench → experiment:** quench1 = low-T square (7×8, N=56), quench2 = intermediate-T square
  (7×8, N=56), quench3 = hydrodynamics (14×4, N=56), quench4 = triangular (6×9, N=54).
  **Q1 is the square lattice ⇒ quench1 and quench2 are the primary targets.** quench3/quench4
  are in scope for later (Q3/Q4) but the harness loader should handle all four uniformly.
- **Observables / file shapes (exact):**
  - `Z2` → vector (M,), value = `<Z_tot^2>/N^2` — the **normalized second moment**, NOT a
    connected variance. (See the gap vs our code below.)
  - `ZZnn` → (M, 14) step×x nn energy density `E(x)`; `ZZnn_fft` → (M, 8) = rfft of `E(x)`;
    `ZZnn_fft_decayrates` → (4,) `Γ_q`, `Γ_{q=0}=0`.
  - `dimercorrs` → **(4, 8) = [r, step]**, the TRANSPOSE of the README's generic rule; orient
    by `len(rs)=4` rows, `len(steps)=8` cols. Two sectors: `min_winding`, `max_winding`.
  - Every `X` has a same-shape `X_err` (bootstrap error bar). quench4 has `_err` only for
    `raw_amplified`, `raw_unamplified`, `zne`.
  - Rows are keyed by `quenchN_steps.txt` (NON-uniform, thinned step indices; M=12/20/10/8).
    **Never assume 20 rows.**
  - MODE suffix ∈ {raw_unamplified, raw_amplified, znr_unamplified, znr_amplified, zne,
    zne+znr}. Best mitigated physical result = `zne+znr` (square/hydro) / `zne` (triangular =
    ZNE+post-selection); `raw_unamplified` = bare device.
- **Simulation parameters (from the QASM, [established]):** `J·dt = 0.25`, `h·dt = 0.5` ⇒
  **h/|J| = 2, dt·|J| = 0.25 for all quenches.** The brief's old triangular value `h/|J|=0.3`
  was WRONG; use 2. Initial states (one-time `ry(θ)` layer): quench1 `ry(+π/6)` all sites;
  quench2 `ry(−10°)` all sites; quench3 `ry(−10°)` except `ry(π)` on the flipped column
  q[7],q[21],q[35],q[49]; quench4 reference = `|0…0>` (real winding bitstrings not in dataset).
  **Only the products J·dt, h·dt are fixed by the gates** — pick a convention (e.g. |J|=1,
  dt=0.25, h=2) and state it.

  > **Note added 2026-10-15 — see [`DECISIONS.md`](../DECISIONS.md) OPEN-1.** "The brief's old
  > triangular value 0.3 was WRONG; use 2" is right **for this harness**: the released quench4
  > circuits are at h/|J| = 2 (`research/05-zenodo-dataset-map.md`). The correction never
  > propagated to the triangular Gauss-law / Q3 work. That work kept h/|J| = 0.3 and called it the
  > reference's value, because `research/04-gauss-law-citations.md` had read 0.3 from the paper's
  > prose. Under decision (a), 0.3 stays, but only as a deliberately chosen weak-field study. It
  > is not a reproduction of quench4. Nothing in this brief changes.

## The hard constraint you must confront (do not paper over)
The dataset's square experiments are **N=56 qubits**. This repo's exact backends (ED /
statevector) top out at **~22–24 spins** (SCOPE §5). **You cannot exactly simulate the 56-qubit
reference state.** The harness is therefore NOT "simulate 56 qubits and subtract." You must
choose and clearly document a defensible comparison strategy. Acceptable options (pick one,
justify it, make it configurable):
  1. **Reduced-lattice comparison at matched (h/|J|, dt·|J|, θ):** simulate the largest square
     lattice within the ceiling (e.g. up to ~4×5 or 4×6) under the *same* dimensionless
     parameters and initial-state angle, and compare the *shape/trend* of `Z2(step)` and
     short-distance `ZZnn` against the H2 curves — explicitly a finite-size, qualitative-trend
     comparison, with size stated. State clearly this is NOT a same-N comparison.
  2. **Trotter-vs-exact-dynamics internal check** on the tractable lattice (our 2nd-order
     Trotter vs `scipy expm` short-time), to quantify our own simulation error, which bounds
     what any comparison to H2 can claim.
  3. If a credible approximate large-N method is in-repo or trivially addable (e.g. a provided
     MPS/TN path) — only if it already exists; do NOT invent one here.
Whatever you pick, the harness must **not present a finite-size or approximate result as a
same-system logical-vs-physical fidelity number.** The honest deliverable may be "trend
agreement + a stated finite-size caveat," which is acceptable for a first Q1 pass.

## Observable gap to close (plug into existing code, match conventions)
`src/observables.py` is geometry-agnostic (site-indexed Pauli-Z/X expectation values on a
statevector; `H = −J Σ_<ij> Z_iZ_j − h Σ_i X_i`, row-major index `n = y*Lx + x`, site 0 = MSB).
It does NOT yet expose what the dataset needs:
- **`Z2` normalized second moment** `<(Σ_i Z_i)^2>/N^2`. The repo has `magnetization_variance_z`
  = `<M_z^2> − <M_z>^2` (CONNECTED), which is the wrong quantity for this comparison. Add a
  `total_z_sq_normalized(psi, n_sites)` returning `<M_z^2>/N^2` and use THAT. (Note `<M_z^2> =
  N + Σ_{i≠j}<Z_iZ_j>`; the existing variance helper already computes `<M_z^2>` internally, so
  reuse that path, just skip the mean subtraction and divide by N².)
- **`ZZnn` nn energy density `E(x)`** with the README's exact averaging
  `E(x) = <Σ_y (Z(x,y)Z(x±1,y) + Z(x,y)Z(x,y±1))/4>` on the square grid. Build it from the
  existing `expval_zz` and the `src/lattice.py` square geometry; respect the grid's boundary
  conditions actually used by the data (recover x/y adjacency from the QASM `rzz q[a],q[b]`
  pairs rather than assuming — see the dataset note's remaining-gap item).
- **rfft of `E(x)`** → `Ẽ(q)` (8 modes for Lx=14; general `Lx//2+1`), and an exponential-decay
  fit for the smallest modes to reproduce `Γ_q`. Only needed for the quench3 (Q3) path; stub it
  behind the loader but it is not required for the Q1 square deliverable.
Dimer correlations for quench4 already live in `src/dimers.py` (`TriangularDimers`); do not
duplicate — the Q1 harness does not need them.

## Inputs (already in repo)
- Sim core (do NOT modify beyond adding the new observable fns): `src/operators.py`,
  `src/trotter.py` (`evolve(state, n_sites, bonds, J, h, total_time, n_steps, record_every)`),
  `src/observables.py`, `src/lattice.py` (`square_bonds(Lx, Ly, bc)`, `site_index`, `coord`),
  `src/backends.py`, `config.py`.
- `research/05-zenodo-dataset-map.md` — the frozen data spec (READ FIRST).
- `research/01-stage1-conventions.md` — Hamiltonian/Trotter/observable conventions.
- SCOPE.md §1 (Q1 definition: "quantitative comparison on the non-frustrated lattice with
  error bars"), §5 (size ceilings), §3 (skeptical prior), §12 (never invent).

## Constraints
- No invented numbers or citations; status-tag any assumption. The dataset's own `_err` bars
  are the physical-side error; the simulation-side "error" is finite-size + Trotter error,
  which must be stated, not fabricated.
- Load data from a configurable local path; add a small checked-in fixture (a few `.txt`
  files, or synthetic same-shape stand-ins) so tests run without the 12.5 MB download.
- Match existing code style and the row-major/MSB index convention exactly.
- Local only; stay within SCOPE §5 ceilings — the harness must refuse (clear error) to attempt
  an exact N>~24 simulation rather than OOM the host.
- Expect gate-angle SIGN differences vs our convention (README gauge identities
  `(J,h,θ)→(−J,−h,θ)` and `(J,h,θ)→(J,−h,−θ)`); treat sign-flipped angles as equivalent.

## Done-check
- A loader that, given the `zenodo_data/` path, returns for any (quench, observable, mode) the
  array + its `_err` + the step vector, with the correct shapes from `research/05` (incl. the
  `dimercorrs` [r,step] transpose and non-uniform step vectors). Unit-tested on the fixture.
- `total_z_sq_normalized` added and cross-checked on small N against a brute-force
  `<(Σ Z_i)^2>/N^2` (dense operator) — exact agreement.
- `ZZnn` `E(x)` builder cross-checked against a direct per-bond `expval_zz` sum on a small grid.
- A Q1 run script that: simulates the square lattice (within the ceiling) at (|J|=1, dt=0.25,
  h=2, θ=π/6 for quench1 / θ=−10° for quench2), produces `Z2(step)` at the dataset's step
  indices, and emits a comparison (table + optional plot) vs the H2 `zne+znr` and
  `raw_unamplified` curves with both sides' error/caveat bars. The finite-size nature is stated
  in the output.
- Tests green; the simulation core's existing tests still pass unchanged.

## What the reviewer must verify
- That `Z2` is the normalized second moment (not the connected variance), that step indexing
  comes from `*_steps.txt` (not assumed 20), that the `dimercorrs` orientation is [r,step], and
  that the parameters are J·dt=0.25 / h·dt=0.5 (h/|J|=2) — i.e. the frozen spec was followed.
- That the N-mismatch is handled honestly: no same-system fidelity claim is made from a
  finite-size or approximate simulation; the comparison's status (trend vs quantitative) and
  the size used are explicit.
- That no dataset numbers are hardcoded and the host cannot be OOM'd by an over-ceiling run.
