# Q1 comparison harness — H2 reference data vs reduced-lattice simulation

Deliverable for `handoff/03-q1-comparison-harness.md`.
- Spec followed: `research/05-zenodo-dataset-map.md` (frozen).
- Code: `src/compare.py`, plus two additive functions in `src/observables.py`, `CompareConfig` in `config.py`, and `scripts/run_compare.py`.
- Tests: `tests/test_compare.py`, using the synthetic fixture `tests/fixtures/zenodo_mini/`.

Status tags: **[established]** from the dataset spec; **[derived]** proved and checked in tests; **[measured]** output of this repo's code; **[inferred]** reasoned, not tested; **[unverified]** not checked.

## Status of this pass
**Real-data run DONE (2026-10-07)** → `data/q1_compare.txt`.

**Dataset.** Downloaded from the Zenodo API record 18487089 to `/home/opc/zenodo_18487089/` (outside the repo, never committed). MD5 `7f388525390eebfdb791b23aeae059d0`, which matches both the Zenodo record and research/05. The archive has 52,407 entries, none with unsafe paths. To reproduce:

```bash
. .venv/bin/activate
python -I scripts/run_compare.py --data /home/opc/zenodo_18487089/zenodo_data
```

**Circuit check [established, from the published QASM].** For quench1 and quench2, step 1:
- 112 distinct rzz pairs, **equal to `square_bonds(7, 8, "periodic")` under the row-major map q = y·Lx + x**. They do not match the q = x·Ly + y map.
- This settles both the periodic boundary (previously [inferred]) and the (x,y)→qubit map (previously open in research/05 §4).
- Angles: |rzz| = 0.5, |rx| = 0.5, ry = +0.523599 (quench1) and −0.174533 (quench2). All match `CompareConfig`.

**Result: what the table does and does not show [measured; interpretation inferred].**
- **quench1 (θ = 30°).**
  - H2 `zne+znr` Z2 falls from 0.737 ± 0.009 (step 1) to 0.562 ± 0.039 (step 20). `raw_unamplified` falls to 0.390 ± 0.015.
  - The reduced-lattice simulation stays in 0.70–0.78 on both 4×4 and 4×5, with a size spread of 0.061.
  - At step 1 the pair averages are 0.761 (sim, 4×5) and 0.732 ± 0.009 (H2 zne+znr), about 3 bootstrap σ apart.
  - The gap widens with time. Mitigation narrows it relative to raw, but does not close it.
- **quench2 (θ = −10°).**
  - H2 Z2 drops to about 0.10–0.23.
  - The reduced lattice oscillates in 0.22–0.65, with a **size spread of 0.33**. Finite-size revivals dominate.
- **This reduced-lattice comparison cannot separate residual device noise from finite-size effects.** It is **not** evidence of agreement or disagreement with the ideal 56-qubit dynamics, and it gives **no logical-vs-physical number**. What it does establish: the loader, conventions, geometry and parameters are consistent with the published circuits.
- **Possible next step (not done).** One Trotter step has a light cone of one bond, so the **exact N = 56 value of Z2 at step 1** follows from small local clusters, using factorization outside the light cone. That would give a genuine same-system quantitative check at the earliest step. Later steps would need an approximate large-N method, which is out of scope until one is approved.

## What was built
- **Loader `ZenodoData(root)`:** `load(quench, observable, mode, initstate=None)` returns the values, the `_err` sibling, and the step vector.
  - Rows are keyed by `quenchN_steps.txt` and shape-checked against M (12/20/10/8). A mismatch raises; it is never padded or assumed to be 20.
  - `dimercorrs` is returned as **[r, step] = (4, 8)** exactly as stored, checked against `rs` and `steps`.
  - The `_err` file name `<stem>_err_<mode>.txt` is **[inferred]** from the spec's "X_err". `<stem>_<mode>_err.txt` is also accepted, so a naming surprise surfaces instead of passing silently.
- **`total_z_sq_normalized`:** Z2 = ⟨(ΣZ)²⟩/N², the second moment, not the connected variance. It matches the dense operator exactly.
- **`nn_energy_density_x`:** E(x) = ⟨Σ_y Σ_{nn j} Z(x,y)Z_j / 4⟩ from the bond list. It matches a direct per-bond sum for open and periodic boundaries. Reading the README formula as having **no extra 1/Ly is [inferred]**; check it against the quench3 values once the data is present. It is only needed for the Q3 path.
- **QASM reader:** `read_qasm` and `qasm_step_bonds` parse `rzz/rx/ry` with a strict angle parser (no expression evaluation). The run script uses them to re-check angles, θ and the bond count against `circuits/quenchN_step1.qasm`, and **aborts on any mismatch**.
- **Ceiling guard:** every simulation entry point calls `check_ceiling` *before* allocating, so a 7×8 (N=56) request raises `MemoryCeilingError` at once. `compare_z2` checks every requested size up front.

## Convention, and why the core integrator is not reused
- **[established, research/05]** Per step, the circuits apply rx(h·dt) half-layer → rzz(2J·dt) on each bond → rx half-layer, with rzz(0.5) and rx(0.5). The ry(θ) preparation is applied once.
- **[derived, tested to 1e-12]** A literal gate-by-gate replay on a 3×3 torus equals our evolution with H = −J ΣZZ − h ΣX at **(J, h) = (+1, +2), dt = 0.25, the same θ**. Both README gauge identities also reproduce it: (−J, −h, θ) and (J, −h, −θ). The non-gauge pairing (J, −h, θ) is off by more than 0.05 (0.24–0.55 in a probe). The signs matter, and the test pins them.
- **[measured]** The existing `src/trotter.py` step puts ZZ on the outside, which is a different 2nd-order splitting. At this coarse step (h·dt = 0.5), starting from a tilted state, it gives a different answer. On 4×4 at step 1, Z2 is **0.63 with the core ordering vs 0.78 with the circuit ordering** for θ = π/6. The harness therefore implements the circuit order itself, using the core's primitives (`apply_x_rotations`, `ising_diagonal`), and leaves `trotter.py` unchanged.
- **[measured]** The Trotter circuit is also far from exact continuous-H dynamics at this step size. Over the dataset's step indices on 4×4, the Z2 gap is up to **0.066** (quench1, θ = π/6) and **0.298** (quench2, θ = −10°). **The reference is the circuit H2 ran, not continuous-time H.** The run script reports this gap (option 2 of the brief).

## Comparison strategy (option 1, plus option 2 as an internal check)
- **Reduced lattice at matched dimensionless parameters:** periodic 4×4 and 4×5 (configurable, ≤ 24 spins), with the same J·dt, h·dt and θ, evaluated at the dataset's own step indices.
- **Periodic boundary is [inferred]:** 112 rzz pairs per step = 2N for 7×8, which only a torus gives. The run script re-checks this from the QASM.
- **The output states plainly that this is a finite-size TREND comparison, not a same-system fidelity or logical-vs-physical number.** The simulation side claims no error bar beyond the stated finite-size spread (|Z2(4×4) − Z2(4×5)|) and the Trotter-vs-exact gap.
- **Pair average** (N·Z2 − 1)/(N − 1) = mean_{i≠j}⟨Z_iZ_j⟩ **[derived]**. Z2 carries a 1/N self-term (0.05 at N=20 vs 0.018 at N=56), so the table also shows this size-independent version for *both* sides. The H2 error bar is scaled by N/(N−1).
- **[measured] Finite-size spread, max |Z2(4×4) − Z2(4×5)| over the dataset steps:** 0.061 (quench1) and **0.331 (quench2)**. The quench2 reduced-lattice curve is strongly size-dependent. A trend comparison there is weak evidence either way, and the output must not be read as more.
- H2 error bars are the dataset's bootstrap `_err`. Whether they are 1σ or a CI half-width is **[unverified]**.

## Not done / open
- **qc-reviewer** on `data/q1_compare.txt`.
- Physical time axis: only J·dt and h·dt are fixed by the gates, so the table's t|J| uses the |J| = 1 convention.
- quench3 (E(x), FFT, Γ_q) and quench4 (dimer correlations) are loadable but not compared. They belong to Q3 and Q2, and quench4 also needs the winding-sector initial bitstrings, which are not in the dataset.
- Nothing here is a logical-qubit result. Q1's encoded side still needs the noisy logical simulation (`concatenated_gadget`) under a justified noise model.

## Independent review during this pass (Claude Code sub-agent, read-only) and fixes
A separate agent independently confirmed four claims with its own code: Z2 is the second moment; row keying and the [r, step] orientation; the **sign/gate-order mapping, against its own literal device circuits including the merged interior rx(1.0)** (Z2 agrees to 9e-15); and the E(x) formula. It found no critical issues. Its findings and their status:

| finding | status |
|---|---|
| M1: `_err` reshaped without a shape check (a silent transpose) | **fixed**: same layout rules as the values plus a shape check; regression test |
| M2: a missing or misnamed `_err` gave NaN silently | **fixed**: `require_err=True` raises; regression test |
| M3: `ry_product_state` had no ceiling guard | **fixed**: `max_spins` is now required; regression test |
| m1: yielded states aliased by in-place updates | **fixed**: yields copies; regression test |
| m2: QASM check used exact equality and rejected gauge signs | **fixed**: \|angle\| with a tolerance |
| m3: only the bond *count* was checked | **fixed**: the bond *set* is compared under both candidate (x,y)→q maps; a mismatch is logged as unanchored |
| m4: E(x) with a periodic side of 2 | **documented** (does not affect 14×4) |
| m5: the "no 1/Ly" reading of E(x) | **open**: check one quench3 magnitude before Q3 work (literal reading: \|E\| near Ly scale) |
| m6: QASM parser skipped or crashed on odd forms | **fixed**: raises on any unparsed gate line or wrong arity; tests |
| m7: wording overclaims (pair average "size-independent"; spread "indicates" finite-size error) | **fixed**: softened in code and caveat |
| guard: the synthetic check depended only on a README; output path relative to cwd | **fixed**: data/ is written only for a source with the dataset README *and* verified circuits; repo-relative output |

While testing the last fix, a README-stripped copy of the fixture *did* write synthetic numbers to `data/q1_compare.txt` under the old rule. That file was deleted at once, and the rule was inverted to the positive check above. Suite: **122/122**.
