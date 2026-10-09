# Handoff 07 — Sector-restricted (per-winding) MCMC ergodic baseline for Q3

**Route to:** Claude Code. This is **algorithm design** (a constrained Markov-chain sampler plus a
sector-leakage treatment) with **no single literature target to copy** — SCOPE §10/§14 routes it
here, not to Kiro, which would otherwise have to invent the construction. **Agents cannot launch
Claude Code; the project lead runs it.** Written by qc-overseer.

## Why this exists (Q3 is currently zero-progress)
SCOPE Q3 (thermalization) is **NOT done** (`docs/findings_vs_questions.md` Q3 row): the relaxation
machinery exists (`src/trotter.evolve(..., record_every=…)` emits time-resolved snapshots), but
there is **no ergodic reference** to compare the relaxation curves against. The reference article
(2503.20870) takes its ergodic/long-time values from **classical Markov-chain Monte Carlo (MCMC)**,
and this project has not built that baseline. Without it, "did the observable thermalize?" has no
yardstick and Q3 cannot reach "done."

**The non-obvious design constraint (already adjudicated, do not relitigate):** the ergodic baseline
**must be computed per winding sector**, not over the whole configuration space. In quantum dimer
models on both square and triangular lattices, **ETH holds only within a topological (winding)
sector**; globally it breaks down (Lan & Powell, PRB 96, 115140, arXiv:1706.02601 — **[established]**,
overseer-verified in journal Entry 11, reviewer-adjudicated in review/06 / Entry 12). A
whole-space MCMC would average over sectors the dynamics cannot connect and would **manufacture a
spurious "non-thermalization."**

**The subtlety that makes it algorithm design, not a lookup:** under the *physical* TFIM quench the
winding is only an **approximate / emergent** label — the bare `-h Σ X` term creates defects and
changes W. The project has **measured** this leakage: `P(W ≠ W₀) ∝ h^2.08`, i.e. **O((h/|J|)²)**
(`docs/gauss_law_dimers.md §4`; `data/gauss_law_scaling.txt`). So the baseline is **not** a
hard-conserved-sector object: it is a within-sector ergodic value **plus** a slow, quantified
residual approach toward the global value over a finite window. The sampler and the comparison must
represent that honestly. Nothing in the fetched sources pins this exact construction → design it.

## Goal
Produce, as reusable repo code with tests, a **classical sector-restricted MCMC ergodic baseline**
for the frustrated triangular TFIM's Q3 observables, so a Trotter relaxation curve can be compared
against the correct (per-winding-sector) ergodic reference, with the O((h/|J|)²) sector-leakage
qualifier made explicit.

Concretely:
1. **A constrained-configuration MCMC sampler** that draws classical spin configurations and
   restricts to a target winding sector (W_x, W_y), reproducing the sector structure the quantum
   dynamics sees.
2. **Per-sector ergodic expectation values** for the Q3 observables (at minimum: defect density
   `⟨Σ_t D_t⟩/(2N)`, dimer densities, and a staggered/clock magnetization or dimer-correlation
   summary — reuse `src/dimers.py` operators; do not reinvent observables).
3. **A comparison harness** that overlays a Trotter relaxation curve (from
   `run_statevector(..., record_every=…)` on a triangular config) against the sector-restricted
   ergodic baseline for the **initial** sector W₀, and reports the measured O((h/|J|)²) leakage as
   the band within which the curve is expected to drift toward the global value over the window.
4. A short write-up stating what counts as "thermalized to the sector baseline" vs "leaking."

This is a **classical baseline** (statistical reference values), not a dynamics claim and not a
hardware claim.

## Physical / math context (status-tagged — carry these tags, invent nothing)
- **Ergodic value within a sector = microcanonical/infinite-T average over the configurations the
  constrained dynamics can reach** [established, standard ETH statement]; the per-sector restriction
  is required because ETH fails globally in these dimer models (1706.02601, PRB 96, 115140)
  **[established]**.
- **Winding is the sector label**: `W_x(y) = 3·#(frustrated horizontal bonds in row y) − Lx`,
  `W_y(x) = 3·#(frustrated vertical bonds in column x) − Ly` (`src/dimers.py`, **[derived]**). On the
  defect-free subspace W is cut-independent and conserved under `H_QDM`; under the full TFIM it is
  only approximately conserved.
- **Sector leakage is O((h/|J|)²)**, measured `P(W≠W₀) ∝ h^2.08`, stripe prefactor matches the
  first-order `(h/J)²/8` to 1.1% (`docs/gauss_law_dimers.md §4`) **[measured]**. Use the repo's own
  measured scaling, not a textbook constant.
- **Convention [established, 2503.20870 §V]:** the frustrated model is **J < 0** in our sign
  (`H = −J ΣZZ − h ΣX`); AFM. The sign of h is a gauge choice. `src/dimers.py` only applies for J<0.
- **Q3 expected-results theory anchors** (already in `docs/findings_vs_questions.md`, cite, import no
  numbers): sharp Trotter-step threshold below which local observables stay faithful (Heyl–Hauke–
  Zoller, Sci. Adv. 5, eaau8342 **[established]**); 2nd-order Trotter prethermalizes to the target
  Hamiltonian's thermal values before slow heating (Yang et al., PRX Quantum 4, 030320
  **[established]**); an *inexact* constraint predicts anomalously slow / sector-bottlenecked
  relaxation (arXiv:2401.11294 **[fetched]**).

## Inputs (real repo paths / APIs — use these, do not rebuild them)
- `src/dimers.py` → `TriangularDimers(Lx, Ly)` (needs periodic torus, Lx,Ly ≥ 3). Provides:
  - winding: `winding_x(y=0)`, `winding_y(x=0)` (diagonal eigenvalue arrays over the 2^N basis);
    `winding_distribution(state, direction, line)` → `P(W)`.
  - defects: `defect(t)`, `total_defects(sublattice="AB")`, `defect_density(state)`.
  - dimers: `dimer(b)`, `dimer_densities(state)`, `dimer_correlation_by_distance(state)`.
  - dynamics generator (constraint-preserving): `qdm_hamiltonian(h)` (CSR).
  - sector-labelled product states: `three_sublattice_spins()` (W=(0,0)), `stripe_spins()`
    (W=(2Lx,−Ly), maximal |W_x|), `product_state_index(spins)` (an (Ly,Lx) ±1 array → basis index).
  - helpers: `probabilities(state)`, `expval_diag(state, diag)`, `s(x,y)`, `triangles`,
    `hexagon(site)`, `flippable(site)`.
- `src/trotter.py` → `evolve(state, n_sites, bonds, J, h, total_time, n_steps, record_every=0)` →
  `(final_state, [(t, state_copy), …])`. `record_every>0` gives the relaxation snapshots.
- `src/backends.py` → `run_statevector(cfg, initial_state=None, init_spec="all_up", record_every=0)`
  (ceiling-guarded, `statevector_max_spins=24`), `run_ed(cfg, k)`, `product_state(n, spec)`,
  `_bonds_for(cfg)`.
- `src/lattice.py` → `triangular_bonds(Lx, Ly, "periodic")` (6-nn, 3N-bond torus), `site_index`,
  `coord`.
- `config.py` → `RunConfig` with `GaussLawConfig` under `RunConfig.gauss` (J=−1, h=0.3, dt=0.25,
  reference §V values). Add a Q3/MCMC sub-config here in the existing dataclass style; **do not
  scatter new constants** (CLAUDE.md).
- Validation reference data: `data/gauss_law_scaling.txt` (the measured leakage slope),
  `data/frustration_compare.txt` (Q2 ground-state signatures).
- `Conversation history/open-questions.md` T-6 (this item), T-7 (winding sign/axis conventions —
  do not depend on the still-[inferred] C_r graph-vs-Euclidean metric for the baseline itself).

## Constraints (hard)
- **Classical, local, within ceilings.** The MCMC is classical and cheap; the *exact* cross-check
  stays within SCOPE §5 ceilings (ED ≤ 20 spins, statevector ≤ 24). Validate on a small periodic
  cluster (e.g. 3×4, 3×6, within ceilings) where you can enumerate the sector by brute force and
  check the MCMC converges to the exact per-sector average. Refuse (don't silently truncate) above
  the ceilings.
- **No hardware, no Nexus, no git push, no SCOPE change.**
- **Never invent numbers.** Every reported value is a classical statistical estimate; tag it
  [measured] with the file that produced it, and give MCMC uncertainties (block/batch-mean or
  bootstrap standard errors, autocorrelation-aware — do not report a naive 1/√N on correlated
  samples).
- **Sector restriction must be real, not cosmetic.** The sampler must only move within the target
  (W_x,W_y) sector (or sample all sectors and bin by W, then condition) — demonstrate it with a
  test that the sampled W is fixed (defect-free generator) or distributed as expected.
- **Do not modify the verified cores** (`src/dimers.py`, `src/trotter.py`, `src/observables.py`,
  `src/backends.py`) except additively. Put the baseline in a **new module** (suggested
  `src/mcmc_baseline.py`) and a **new test file** (`tests/test_mcmc_baseline.py`).
- Reuse `src/dimers.py` operators for every observable — the baseline and the quantum curve MUST use
  the identical observable definitions, or the comparison is meaningless.

## Design questions you must decide and state (this is the algorithm-design part)
1. **What ensemble is the right ergodic reference?** Infinite-temperature uniform over the
   sector-constrained configuration space is the natural first choice (matches an ETH long-time
   average). State the choice and why; if you also offer a finite-T Metropolis at the model's energy
   scale, keep it separate and labelled.
2. **How to sample within a fixed winding sector.** Candidate: local flippable-plaquette moves
   (the `flippable`/`qdm_hamiltonian` support) that preserve every triangle's Gauss law and hence W;
   plus an ergodicity argument (or an honest statement of which sector-internal states are reachable).
   Non-local worm/directed-loop moves are an alternative — justify whatever you pick, and **test
   that the chain is sector-preserving and mixes** (compare to brute-force enumeration on a small
   cluster).
3. **How to present the leakage.** The quantum curve will drift *out* of W₀ at rate O((h/|J|)²).
   Represent the baseline as the within-W₀ ergodic value with an explicit drift band toward the
   global (all-sector) average, using the repo's measured `P(W≠W₀) ∝ h^2.08`. Do not claim a
   hard-conserved sector.

## Done-check (what makes this reviewable and complete)
- `src/mcmc_baseline.py` + `tests/test_mcmc_baseline.py` added; a Q3/MCMC config block added to
  `config.py` additively; full suite green (state the new count).
- **Convergence test [measured]:** on a small cluster (within ceilings), the MCMC per-sector average
  of defect density (and one more observable) agrees with the **brute-force exact** per-sector
  average to within the reported MCMC standard error. Record it in a data file
  (suggested `data/mcmc_baseline.txt`) with the "classical statistical reference, not an H2 result,
  not quantum dynamics" caveat line.
- **Sector-restriction test:** the sampler provably stays in (or correctly bins by) the target
  (W_x,W_y); a test asserts the sampled winding matches.
- **Comparison harness:** a script (suggested `scripts/run_q3_baseline.py`) that, for a chosen
  triangular config and initial sector-labelled state (`three_sublattice_spins` / `stripe_spins`),
  produces a Trotter relaxation curve via `record_every` and overlays the sector-restricted ergodic
  baseline for W₀, with the O((h/|J|)²) leakage band annotated. Output to `data/`.
- A short write-up (suggested `docs/q3_thermalization.md`) stating: the ensemble choice; why
  per-sector (1706.02601); the leakage treatment (measured h^2.08); and the operational definition
  of "thermalized to the sector baseline vs leaking." Cite the Q3 theory anchors; import no numbers
  from them.
- `docs/findings_vs_questions.md` Q3 row updated from [pending] to the measured state (Kiro will
  re-verify before accepting); a journal Entry; `open-questions.md` T-6 moved to Resolved on
  acceptance.

## What the reviewer (qc-reviewer) must independently verify
- **The per-sector restriction is correct and necessary**: re-derive or re-confirm that a
  whole-space MCMC would mix disconnected sectors, and that the sampler stays within W₀ (or bins
  correctly). Reproduce the sector on a small cluster by brute-force enumeration independently.
- **Convergence is real**: MCMC per-sector averages match the exact enumeration within quoted
  errors, and the errors are autocorrelation-aware (not naive 1/√N).
- **The leakage band uses the repo's own measured O((h/|J|)²) slope**, not a borrowed constant, and
  the write-up does **not** claim a hard-conserved sector.
- **Observable definitions are identical** between the quantum curve and the MCMC baseline (same
  `src/dimers.py` operators) — otherwise the comparison is void.
- **No number is presented as a quantum/H2 result**; every value is a classical statistical estimate
  under a stated ensemble, tagged accordingly.
- **Ceilings respected**; the exact cross-check stayed ≤ 20 spins (ED) / ≤ 24 (statevector).

## Not in scope for this brief (keep it bounded)
- No hardware/Nexus run (Q3 on H2 is part of the deferred campaign).
- No new quantum observable; reuse `src/dimers.py`.
- The C_r graph-vs-Euclidean metric fix (T-7, journal Entry 9/14) is a *separate* minor follow-up —
  the baseline does not depend on it; don't fold it in here.
- The Q1 matched logical-vs-physical comparison (T-9) is the hardware-gated article spine; unrelated.
