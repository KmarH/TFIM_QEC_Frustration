# Review 01 — Stage 1 (square lattice, unencoded TFIM)

**Reviewer:** qc-reviewer (independent). **Date:** 2026-10-06.
**Scope of this review:** physics conventions, Trotter correctness, limits, backend/ED/statevector
agreement, observables, config-driven behavior, hardware gating, and size-ceiling guards for
Stage 1 of the project at `/home/opc/KiroTest-project`.
**Method:** read all Stage 1 code and docs; reconstructed independent references from scratch
(dense Kronecker Hamiltonian, exact `expm_multiply` propagator, analytic limits) and compared to
`src/`; ran empirical memory probes. I did **not** edit any file under `src/`, `tests/`, `config.py`,
or `main.py`. A temporary reviewer-only script was created under `review/` and deleted afterward.

Status tags: **[verified]** I confirmed it myself numerically/analytically; **[plausible]** consistent
and reasonable but not independently proven here; **[unverifiable]** cannot be checked at this stage.

---

## Environment and commands run (exact)

```
$ free -h
               total        used        free      shared  buff/cache   available
Mem:            10Gi       3.5Gi       113Mi        23Mi       7.2Gi       7.1Gi
Swap:          4.0Gi          0B       4.0Gi

$ . /home/opc/KiroTest-project/.venv/bin/activate && python --version
Python 3.12.14
$ python -c "import numpy,scipy;print(numpy.__version__,scipy.__version__)"
numpy 2.5.3  scipy 1.18.1

$ cd /home/opc/KiroTest-project && python -m pytest -q
.......................                                                  [100%]
23 passed in 0.38s
```

Independent physics/code checks (reviewer-only script, PYTHONPATH=. python review/_review_checks.py):

```
[PASS] H matches dense Kron 2x2 open  max|diff|=0.0e+00
[PASS] H matches dense Kron 3x2 open  max|diff|=0.0e+00
[PASS] H matches dense Kron 2x3 periodic  max|diff|=0.0e+00
[PASS] H matches dense Kron 3x3 periodic  max|diff|=0.0e+00
[PASS] all-up energy at h=0 == -J*nbonds  E=-4.0, nbonds=4
[PASS] h->0 E0 == -J*nbonds (classical ferro)  E0=-7.00000000, -nbonds=-7
[PASS] h->0 two-fold near-degeneracy  gap=7.99e-15
[PASS] h->inf E0 == -h*N (paramagnet)  E0=-6.00000000, -N=-6
[PASS] h->inf M_x ~ +N  M_x=6.000000
[PASS] statevector(2000 steps) vs exact expm  ||diff||=2.95e-07
[PASS] energy conserved under evolution  dE=4.44e-07
[PASS] Trotter O(dt^2): ~4x per doubling  ratios=['4.01','4.00','4.00']
[PASS] M_z vs dense
[PASS] Var(M_z) vs dense  got=3.243885, ref=3.243885
[PASS] energy termwise vs dense H
[PASS] ED E0 vs independent dense eigh  ED=-7.6730915064 dense=-7.6730915064
[PASS] single spin <Z(t)>=cos(2ht)  got=-0.826234, ref=-0.826234
[PASS] periodic bond count = 2N (4x4)  n=32
[PASS] open bond count (3x3)=12  n=12
SUMMARY: 19 / 19 passed
```

Config / gating / PBC-edge checks:

```
default backend: statevector
allow_hardware default: False
device: H2-emulator max_shots: 0
stim  -> NotImplementedError OK
nexus -> NotImplementedError OK
grep requests|urllib|socket|pytket|nexus|http in src/,config.py,main.py -> only comments/dispatch strings
2x3 periodic bonds: [(0,1),(0,2),(0,4),(1,3),(1,5),(2,3),(2,4),(3,5),(4,5)] count 9   # horiz wrap (Lx=2) skipped, vert wrap kept, no duplicates
```

Memory probes (statevector Trotter, 2 steps; ru_maxrss):

```
N=20 (5x4): maxRSS=157 MB,  theo state=17 MB,  norm=1.000000, t=0.8s
N=22 (11x2): maxRSS=421 MB, theo state=67 MB,  norm=1.000000, t=4.8s
N=24 (6x4): maxRSS=1477 MB, theo state=268 MB, norm=1.000000, t=20.8s
```

ED Hamiltonian-builder probes (ceiling temporarily raised to 30 to test the builder, J=h=1):

```
ED N=4 ... N=12: OK (maxRSS 62->727 MB; N=12 took ~10 s)
ED N=16 (4x4): FAIL MemoryError: Unable to allocate 16.0 GiB for shape (1073741824,) complex128
```

---

## What passes plainly (verified)

- **TFIM Hamiltonian convention, signs, ordering, boundary conditions.** `H = -J Σ_<ij> Z_iZ_j - h Σ_i X_i`
  with site 0 = MSB. Matches an independent dense Kron build to machine precision for 2x2, 3x2 open and
  2x3, 3x3 periodic. Ferromagnetic sign confirmed (all-up at h=0 gives -J·nbonds). **[verified]**
- **PBC bond enumeration**, including the degenerate-wrap guard: Lx=2 (and Ly=2) correctly skip the wrap
  so no bond is double-counted; 4x4 periodic gives exactly 2N=32 bonds, all unique. **[verified]**
- **Second-order Suzuki–Trotter.** Strang step is correctly symmetric; global error scales as O(dt²)
  (clean 4.00–4.01x error reduction per step doubling); statevector agrees with exact `expm_multiply`
  to ~3e-7 at 2000 steps on a 6-spin PBC cluster. **[verified]**
- **Limits.** h→0: E0 = -J·nbonds with a 2-fold degeneracy (gap ~8e-15). h→∞: E0 = -hN and M_x → +N
  (paramagnet). Both reproduced. **[verified]**
- **Energy conservation** under exact Trotter unitary: |dE| ~ 4e-7 over T=0.8, 2000 steps (6 spins);
  the recorded data/stage1_validation.txt value |dE|=4.46e-4 at 9 spins/200 steps is consistent with
  O(dt²) Trotter drift, not a bug. **[verified]**
- **ED vs independent dense eigh:** E0 agrees to <1e-13 (6 spins). **[verified]**
- **Observable definitions and normalization:** `expval_z/x/zz`, `total_magnetization_z/x`,
  `magnetization_variance_z` (incl. the <M_z²> cross terms), connected `two_point_correlations_z`
  (connected C_zz = 1 on a Bell state; 0 on product states), and termwise `energy` all match dense
  operators to ~1e-10. **[verified]**
- **Single-spin analytic dynamics:** <Z(t)> = cos(2ht) reproduced to <1e-4. **[verified]**
- **config.py drives behavior; local-first; hardware double-gated.** Backend defaults to
  `"statevector"`; `allow_hardware=False`, `max_shots=0` by default; `stim`/`nexus` raise
  `NotImplementedError` in Stage 1 dispatch; no network/pytket/nexus imports anywhere in `src/`,
  `config.py`, `main.py` (only comment/dispatch strings). Hardware is unreachable without the explicit
  flag, as required by SCOPE §5. **[verified]**
- **Statevector ceiling guard** (`statevector_max_spins`) and **ED ceiling guard** (`ed_max_spins`)
  both raise `MemoryCeilingError` when exceeded (covered by tests and re-confirmed). **[verified]**
- **23/23 unit tests pass** under the venv (Python 3.12.14). **[verified]**

---

## Findings

### CRITICAL

**C1 — The ED backend cannot reach anywhere near its declared `ed_max_spins=22` ceiling; it OOMs at N≈16.**
- **Location:** `src/operators.py` — `kron_list` / `single_site` / `two_site` / `tfim_hamiltonian`;
  ceiling in `config.py:CeilingConfig.ed_max_spins = 22`; policy in SCOPE §5 ("Sparse ED (Lanczos):
  toward ≤~22–24 spins").
- **Reason:** The Hamiltonian is assembled by building each term as a **full 2^N-dimensional** operator
  via repeated `scipy.sparse.kron`, then summing. `sp.kron` internally does
  `A.data.repeat(B.size).reshape(...)`, which allocates arrays scaling with the full dimension. Empirically
  the builder succeeds only through **N=12** (727 MB, ~10 s) and **fails at N=16** attempting a single
  **16 GiB** allocation. N=22 would need ~1000x more Hilbert space than N=12 — utterly infeasible with this
  construction. The guard rail at 22 therefore advertises a capability the code does not have; a user who
  sets a 16–22-spin lattice and selects `backend="ed"` gets a hard `MemoryError` crash, not a clean guard.
- **Why it matters:** SCOPE §5/§14 require Stage 1 ED validation "within the section-5 ceilings," and the
  reproduction target (Haghshenas) needs ED/exact cross-checks at non-trivial sizes. The current builder
  blocks that.
- **Concrete fix (do not apply — reviewer does not edit):** Build the TFIM Hamiltonian as a true sparse
  operator without materializing per-term full-D kron products — e.g. construct the diagonal ZZ part
  directly from bit arithmetic (as `trotter.ising_diagonal` already does) wrapped in `sp.diags`, and build
  the X part as a sum of sparse single-bit-flip permutation matrices via `scipy.sparse` COO index math.
  Then re-run an empirical ED memory probe at the target N **before** any ceiling is frozen. Until then,
  `ed_max_spins` should be set to a value the builder can actually reach (verified here through N=12;
  N=13–15 untested).

### MAJOR

**M1 — Size ceilings are declared but not backed by a passing empirical probe at the ceiling value; the recorded probe only reaches N=20, and statevector RSS overhead is ~5.5x the theoretical state size.**
- **Location:** `config.py:CeilingConfig` (`statevector_max_spins=24`, `ed_max_spins=22`);
  `scripts/validate_stage1.py:probe_statevector_memory` (probes **N=20 only**);
  `data/stage1_validation.txt` ([4] N=20).
- **Reason:** SCOPE §5/§14 explicitly state the ceilings are proposals "not frozen until qc-reviewer
  confirms an empirical memory probe **at the chosen size**," and that raising a ceiling requires a probe
  first. The committed probe is at N=20 (peak 109–157 MB), not at the 24-spin statevector ceiling. My probe
  at **N=24 peaks at ~1.48 GB maxRSS** vs the 268 MB theoretical state size — a ~5.5x overhead arising from
  `apply_x_rotations` (`np.moveaxis` + two half-state `.copy()` slabs + reshaped output per site) and the
  diagonal multiply allocating new arrays. 1.48 GB fits comfortably in the 7.1 GB free for a single serial
  run, so **N=24 statevector is safe on this host [verified]**, but the headline "16 bytes·2^N" accounting
  in the docstrings understates real peak by ~5x and should not be used to justify a ceiling.
- **Concrete fix:** Add probes at N=22 and N=24 (statevector) and at the real ED limit to
  `validate_stage1.py`, record maxRSS (not just tracemalloc, which misses NumPy-internal/BLAS allocations —
  tracemalloc reported 109 MB at N=20 while ru_maxrss was 157 MB), and only then freeze the ceilings.
  Note the ~5x statevector overhead factor next to the ceiling in `config.py`.

**M2 — `scripts/validate_stage1.py` uses `tracemalloc`, which undercounts real peak memory used to justify ceilings.**
- **Location:** `scripts/validate_stage1.py:probe_statevector_memory`.
- **Reason:** `tracemalloc` only tracks Python-level allocations and misses NumPy C-level / BLAS buffers.
  Recorded probe: `peak_traced=109.1 MB` at N=20; actual `ru_maxrss` I measured was 157 MB (and the
  overhead ratio grows with N: 1.48 GB at N=24). Using the smaller tracemalloc number to argue a 24-spin
  ceiling is safe would be optimistic.
- **Concrete fix:** report `resource.getrusage(RUSAGE_SELF).ru_maxrss` (or `/proc/self/status` VmHWM)
  alongside tracemalloc; use the larger figure for ceiling decisions.

### MINOR

**m1 — Python version mismatch vs SCOPE §7 (flagged, not resolved).** `requirements.txt` documents this
clearly: SCOPE pins Python 3.11, but the host has only 3.9/3.12 and Stage 1 was built/tested on 3.12.14.
This is correctly surfaced and is a project-lead decision, not a defect. No action by the build agents required
beyond the existing note. **[verified as flagged]**

**m2 — Dangling reference to `handoff/plan.md`.** `requirements.txt` and SCOPE repeatedly point to
`handoff/plan.md` for the environment-mismatch and stim-toolchain notes, but `handoff/` is empty. Either
create the plan file or adjust the pointers so the flagged items are actually recorded where promised.

**m3 — `product_state` is imported into `main.py` but unused there.** `main.py` imports `product_state`
from `src.backends` but never calls it (the `init_spec` string path is used instead). Harmless; a linter
would flag it. **[verified]**

**m4 — `run_statevector` default initial state is `all_up`, which is an eigenstate of the Ising term and
has M_x=0; fine for a smoke test but not an interesting relaxation probe.** `main.py` runs `all_up`. For
the Haghshenas-style relaxation observables (SCOPE Q3) an inhomogeneous/`neel` initial state will be needed;
the machinery (`record_every`, `neel`) exists but is not exercised by `main.py` or the validation script.
Not a Stage 1 defect; noting for Stage 1→reproduction continuity. **[plausible]**

**m5 — `energy` free function and `energy_dense` cross-check exist and agree, but `main.py`/validation use
only the termwise `energy`.** The dense cross-check (`energy_dense`) is only exercised in tests. Good that
it exists; consider having the validation report print both once at small N as a self-check. Optional.

---

## Answers to the specific verification asks

- **TFIM conventions/signs/BC:** correct. **[verified]**
- **Trotter order & dt-error scaling:** 2nd-order, O(dt²), clean 4x per doubling. **[verified]**
- **Limits h→0 and h→∞:** both correct (classical ferro 2-fold degenerate; paramagnet -hN, M_x=N). **[verified]**
- **Small-cluster statevector-vs-ED/exact agreement:** ~3e-7. **[verified]**
- **Energy conservation:** holds to Trotter order; recorded 4.46e-4 at 9 spins/200 steps is expected drift, not a bug. **[verified]**
- **Observable definitions & normalization:** all match dense operators. **[verified]**
- **config.py drives behavior; local default; hardware gated:** yes; no network/hardware reachable without the flag. **[verified]**
- **Ceiling guards:** present and raise `MemoryCeilingError` — but the **ED ceiling value is wrong/unsafe (C1)** and the statevector ceiling value is **not probed at the ceiling (M1)**. **[verified that guards fire; ceiling *values* not validated]**

---

## Verdict: APPROVE WITH CONDITIONS

Stage 1 physics is correct and well-tested: Hamiltonian conventions, Trotter order and error scaling,
the h→0/h→∞ limits, statevector-vs-exact agreement, energy conservation, and all observables reproduce
independent references to machine/float precision, and the config-driven local-first design with
double-gated hardware is implemented as specified. The code is clean and the comments are theory-focused.

The conditions are about the **size ceilings**, which SCOPE §5/§14 explicitly say must be probe-backed
before they are frozen:

1. **(Critical) Fix the ED Hamiltonian builder** so it is genuinely sparse, or lower `ed_max_spins` to a
   value the current builder can reach (verified ≤12 here). As written, `ed_max_spins=22` promises a
   capability that OOMs at N≈16.
2. **(Major) Probe statevector memory at the actual ceiling (N=22 and N=24)** using `ru_maxrss`, record it,
   and only then freeze `statevector_max_spins`. N=24 is empirically safe on this host (~1.48 GB), but the
   docstring's 2^N·16-byte accounting understates real peak by ~5x.
3. **(Minor) Create `handoff/plan.md`** (referenced but missing) so the flagged Python-3.11 and stim
   toolchain items live where the docs point.

None of these block Stage 2 scaffolding / Stim QEC work from proceeding in parallel, since that path does
not use the ED builder.

### Open items
- ED builder sparsity fix + re-probe before freezing `ed_max_spins` (C1).
- Statevector probe at N=22/24 with maxRSS; freeze `statevector_max_spins` (M1, M2).
- Create `handoff/plan.md`; resolve the dangling references (m2).
- Python 3.11 vs 3.12 interpreter decision — the project lead (m1).
- Reproduction continuity: exercise `neel`/`record_every` relaxation path and compare to Haghshenas
  curves at a later milestone (m4) — deferred, out of Stage 1 scope.
