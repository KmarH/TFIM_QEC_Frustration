# Research Note 05 — Zenodo dataset map for arXiv:2503.20870 (Q1 harness input spec)

**Purpose.** Pin down the EXACT data conventions of the published dataset so the Q1
logical-vs-physical comparison harness (handoff/03) can load the H2 reference curves and
match them against our simulated observables. Input spec only — no project code here.

**Source dataset.** "Data for Digital quantum magnetism on a trapped-ion quantum
computer", Chertkov (Quantinuum), Zenodo DOI 10.5281/zenodo.18487089, v1
(published April 2026), CC-BY-4.0, 12.5 MB zip `digital_quantum_magnetism_data.zip`.
**Provenance of this note [established]:** I downloaded the zip to a scratch dir and
verified `md5 = 7f388525390eebfdb791b23aeae059d0`, matching the Zenodo record page. The
dataset's own `zenodo_data/README.md` (6.9 kB) and representative `.txt` files were read
directly; all shapes/values below are from that read, not from the file tree alone. The
Zenodo landing page has no description text and the previewer renders only the file tree,
so the README had to be extracted from the archive.

**Paper cross-ref [established]:** arXiv:2503.20870 v3 = Nature 653, 56–62 (2026), "7 pages
+ Supplemental material". Abstract confirms: digitized (Trotter) quantum Ising dynamics on
H2; square-lattice thermalization + emergent hydrodynamics (diffusion constant); triangular
lattice with periodic BC showing frustration-driven emergent gauge/topological constraints.
Per-quench lattice sizes, dt, and initial states live in the main text + SI, which are
**not** fetched in this note (see §3 status tags).

Status tags: [established] read from the dataset/README or verified live; [inferred] my
reasoning from the data; [unverified] second-hand / from the task brief, not yet checked
against the paper SI.

---

## (1) Quench → experiment → observable map

README states verbatim [established]:
- `quench1` = "low-temperature quench"
- `quench2` = "intermediate-temperature quench"
- `quench3` = "hydrodynamics quench"
- `quench4` = "triangular lattice quench"

| Quench | Experiment (task label) | Lattice (Lx×Ly, N) | Primary observable file family | README definition of the observable |
|---|---|---|---|---|
| quench1 | low-T square | **7×8, N=56** [established] | `quench1_Z2_*` | `Z2 = <Z_tot^2> = <sum_ij Z_i Z_j / N^2>` for N qubits [established] |
| quench2 | intermediate-T square | **7×8, N=56** [established] | `quench2_Z2_*` | same `Z2` observable [established] |
| quench3 | hydrodynamics | **14×4, N=56** [established] | `quench3_ZZnn_*`, `..._fft_*`, `..._fft_decayrates_*` | `ZZnn = E(x) = <sum_y (Z(x,y)Z(x±1,y) + Z(x,y)Z(x,y±1))/4>` (nn energy density profile along x); `fft` = 1D FT `Ẽ(q)` of `E(x)`; `fft_decayrates` = exp. decay rate `Γ_q` from fitting `Ẽ(q)` [established] |
| quench4 | triangular | **6×9, N=54** [established] | `quench4_{min,max}_winding_dimercorrs_*`, `quench4_rs.txt` | `dimercorrs = C_r(s)`, connected dimer–dimer correlation function [established] |

Notes:
- **Lattice dimensions are now RESOLVED from the dataset itself** [established, 2026-10-06]:
  I extracted one Z-basis snapshot per quench (`snapshots/*_snapshotN_amplified.txt`), which
  the README stores as an `Lx × Ly` matrix of 0/1. Measured (rows × cols = Lx × Ly):
  quench1 = 7×8 (56), quench2 = 7×8 (56), quench3 = 14×4 (56), quench4 = **6×9 (54)**.
  Independently cross-checked: the `ZZnn` matrix is 10 steps × **14** columns, and 14 = Lx
  for quench3 — consistent, confirming the x-axis is the length-14 direction.
- **quench4 orientation correction:** the task brief said "9×6". The stored snapshot matrix
  is **6 rows × 9 cols** (Lx=6, Ly=9), N=54 — the transpose of the brief's wording. The qubit
  count 54 (not 56) is confirmed by the QASM `qreg q[54]` and the 54 `ry`/`measure` lines.
  The harness must use Lx=6, Ly=9 and index the (x,y)→qubit map with x the 6-direction.
- `Z2` is **normalized by N²** (per README formula `/N^2`), so it is bounded in [0,1], not an
  extensive variance. Observed quench1 values run 0.73→0.39, quench2 0.54→0.15 — consistent
  with a normalized `<Z_tot^2>`. [established] The task brief calls this "Z_tot^2 variance";
  **the README defines it as the normalized second moment `<Z_tot^2>/N^2`, NOT a connected
  variance** `<Z_tot^2> - <Z_tot>^2`. Harness must use the second-moment definition. [established]
- quench4 has TWO initial states → extra filename field: `quenchN_INITSTATE_OBSERVABLE_MODE.txt`
  with `INITSTATE ∈ {min_winding, max_winding}` (minimal / maximal winding-number sector).
  [established]

---

## (2) File formats, units, column layout (exact, from reading the files)

### Axis / index files
- `quench{1,2,3,4}_steps.txt` — one value per line = **Trotter step index** for that quench
  (dimensionless integer step count, written as float `%.18e`). These are NON-uniform /
  thinned, not `1..M`. Observed [established]:
  - quench1: `1,2,3,4,5,6,7,8,10,12,16,20` → **M = 12**
  - quench2: `1..20` → **M = 20**
  - quench3: `1,2,3,4,5,6,8,10,12,14` → **M = 10**
  - quench4: `2,4,6,8,10,12,14,16` → **M = 8**
  **The task brief's "20 steps" is the QASM circuit count, not the data-row count.** The
  `circuits/` folder lists `stepX` for X=1..20 for every quench, but the README explicitly
  says "we list X=1,...,20 in the folder, even though those were not all run"; the actual
  measured steps are the ones in `*_steps.txt`. The harness MUST key rows off `*_steps.txt`,
  not assume 20. [established]
- `quench4_rs.txt` — distances `r` used in `C_r(s)`: `1,2,3,4` → **4 distances**. [established]

### Value files — general rule (README, verbatim) [established]
> "scalar observables are stored as vector of size M … vector observables are stored as
> matrices of size M × L, where L is the size of the vector." (M = # Trotter steps.)

Numbers are whitespace-separated, `%.18e` scientific, newline-separated rows. No header,
no index column, no units string. `np.loadtxt` loads them directly.

### Per-family exact shapes (measured) [established]
| File family | Shape (rows × cols) | Row axis | Col axis | Value |
|---|---|---|---|---|
| `quench1_Z2_*` | 12 × 1 (vector) | Trotter step | — | `<Z_tot^2>/N^2`, dimensionless, ∈[0,1] |
| `quench2_Z2_*` | 20 × 1 | Trotter step | — | same |
| `quench3_ZZnn_*` | **10 × 14** | Trotter step (M=10) | x-position (L=14 = Lx) | nn energy density `E(x)`, dimensionless |
| `quench3_ZZnn_fft_*` | **10 × 8** | Trotter step | FT mode q | `Ẽ(q)`; 8 = `14//2 + 1` ⇒ **real-input FFT (rfft) of the length-14 x-profile** [inferred] |
| `quench3_ZZnn_fft_decayrates_*` | **4 × 1** | FT mode q (smallest few) | — | decay rate `Γ_q`; README: "only computed for few smallest modes". First value is 0.0 (q=0, conserved) [established] |
| `quench4_{min,max}_winding_dimercorrs_*` | **4 × 8** | **distance r (len rs = 4)** | **Trotter step (M = 8)** | connected `C_r(s)`, dimensionless |

**AMBIGUITY TO FLAG (reviewer + harness):** the `dimercorrs` files are **4 × 8**, i.e.
`[r × step]` — the **TRANSPOSE** of the README's stated "M × L (rows = Trotter steps)" rule.
Here rows = len(`quench4_rs.txt`)=4 and cols = len(`quench4_steps.txt`)=8. Either the generic
rule does not apply to this family or the README wording is loose for quench4. The harness
must orient `dimercorrs` as `C[r_index, step_index]` (rows=r, cols=step), confirmed by the
4=len(rs), 8=len(steps) match. [established that the file is 4×8; inferred which axis is which
from the rs/steps lengths — do NOT silently apply the generic MxL rule here.]

For ZZnn the generic rule DOES hold: rows=10=len(steps), cols=14=Lx. [established]

### Error-bar files [established]
Any observable `X` has a sibling `X_err` with the **same shape**, holding the bootstrap-
resampled error bar (1σ, assumed — README says "error bar … obtained by bootstrap
resampling"; it does not state 1σ vs CI, so treat as a bootstrap stderr unless the SI says
otherwise [inferred]). Present for Z2, ZZnn, ZZnn_fft, ZZnn_fft_decayrates, dimercorrs.
Note quench4 dimercorrs provides `_err_*` only for `raw_amplified`, `raw_unamplified`, `zne`
(no `_err` for `znr*`/`zne+znr`, because quench4 uses post-selection not ZNR — see modes).

### Mitigation MODE suffixes [established, verbatim from README]
`MODE ∈ {raw_unamplified, raw_amplified, znr_unamplified, znr_amplified, zne, zne+znr}`:
- `raw_unamplified` — raw shots, no Pauli errors inserted (ZNE "λ=1" point).
- `raw_amplified` — raw shots WITH Pauli errors inserted (ZNE amplified point).
- `znr_unamplified` / `znr_amplified` — zero-noise regression (ZNR) via leakage-detection
  gadget applied to the unamplified / amplified shots.
- `zne` — ZNE WITHOUT ZNR. (For **quench4**, `zne` = ZNE with leakage **post-selection**.)
- `zne+znr` — ZNE WITH ZNR; labelled "ZNE & ZNR H2 data" in Fig. 3 of the paper.
- quench4: leakage **post-selection** replaces ZNR; hence no `znr*` dimercorr files, and the
  dimercorr set is `{raw_unamplified, raw_amplified, zne}` (+ matching `_err`). [established]

**For the Q1 harness:** the primary "best physical result" column to compare against the
simulation is almost certainly `zne+znr` (square/hydro) and `zne` (triangular, = ZNE+post-
selection). `raw_unamplified` is the closest to "bare device, no mitigation". [inferred]

---

## (3) Trotter params & initial states per quench

### From the dataset [established]
- Trotter step indices per quench: see `*_steps.txt` listed in §2. The files store step
  INDEX, not physical time; physical time = `step × dt`.
- `circuits/quenchN_stepX.qasm` (X=1..20) give the exact gate angles / geometry actually used
  (OpenQASM 2.0), WITHOUT dynamical decoupling, randomized compiling, leakage detection, or
  ZNE Pauli insertion. The Ising coupling is in `rzz`, the field in `rx`, the initial-state
  angle in `ry`.

### Trotter parameters — RESOLVED from the QASM gate angles [established, 2026-10-06]
I parsed `quench{1,2,3,4}_step{1,2}.qasm` (and quench4_step8). Gate conventions:
`rzz(φ) = exp(−i φ/2 · Z⊗Z)`, `rx(φ) = exp(−i φ/2 · X)`. A 2nd-order (Strang) Trotter step
of `H = −J Σ ZZ − h Σ X` is `rx(h·dt)` half-layer → `rzz(2·J·dt)` → `rx(h·dt)` half-layer,
with interior half-layers merging into `rx(2·h·dt)` between consecutive steps.

**Observed, IDENTICAL across all four quenches:**
- `rzz(0.5)` ⇒ `2·J·dt = 0.5` ⇒ **J·dt = 0.25**
- `rx(0.5)` (half-layer) ⇒ **h·dt = 0.5**; the interior merged `rx(1.0) = rx(2·h·dt)` seen from
  step2 onward confirms the symmetric 2nd-order split.
- ⇒ **h/|J| = 2** and **dt·|J| = 0.25 for ALL quenches, including quench4 (triangular).**
- Only one `rzz` angle and one `rx` angle appear anywhere (checked quench4 step1/step8 and
  quench2 step1 — no second coupling, no bond-dependent angle). Gate inventory per step:
  `ry` (prep, once), `rx`, `rzz`, `measure`. quench4 has 162 `rzz`/step vs 112 for the square
  quenches — more bonds (triangular + PBC), same angle.

**CONTRADICTION WITH THE TASK BRIEF — resolved in favour of the QASM [established]:**
- Square (quench1/2): brief said `(h/|J|, dt·|J|) = (2, 0.25)` → **both confirmed.**
- Triangular (quench4): brief said `(h/|J|, dt·|J|) = (0.3, 0.25)` → **dt·|J|=0.25 confirmed,
  but h/|J| is NOT 0.3 — the circuits show h/|J| = 2, the same as the square quenches.** The
  `0.3` appears to be an error in the brief. The README's two gauge identities
  `(J,h,θ)→(−J,−h,θ)` and `(J,h,θ)→(J,−h,−θ)` are SIGN-only and cannot rescale a ratio from 2
  to 0.3, so they do not explain the discrepancy. **The harness must use h/|J| = 2 for all
  quenches** unless the paper SI explicitly states a different triangular value (in which case
  the published circuits, not the SI prose, are the executable ground truth). [established from
  circuits; SI prose not independently read]

  > **Note added 2026-10-15 — see [`DECISIONS.md`](../DECISIONS.md) OPEN-1.** This finding was
  > **correct**: the reference's triangular quench is at h/|J| = 2, and the three-machine peer
  > review re-derived it independently from all 80 QASM files (`review/14-three-machine-peer-review.md`). It did **not propagate** at the time, though. `GaussLawConfig` / `Q3BaselineConfig` kept
  > h/|J| = 0.3, and later documents kept calling 0.3 "the reference's value". The reason is that
  > `research/04-gauss-law-citations.md` read 0.3 from the paper's prose, and the two threads never
  > cross-checked. On 2026-10-15 the project lead chose option (a). The triangular work stays at
  > h/|J| = 0.3 as a deliberately chosen weak-field study, **not** a reproduction of quench4. So
  > "the harness must use h/|J| = 2" still holds for the Q1 harness against the released data.
  > It does not apply to the self-contained triangular study.

### Initial states — RESOLVED from the `ry` prep layer [established, 2026-10-06]
The one-time `ry(θ)` layer at the top of each circuit sets the initial product state
(`ry(θ)|0> = cos(θ/2)|0> + sin(θ/2)|1>`), applied once (not repeated per step — verified by
comparing step1 vs step2):
- **quench1 (low-T):** `ry(π/6) = ry(+30°)` on all 56 qubits — uniform tilted state.
- **quench2 (intermediate-T):** `ry(−10°) = ry(−0.17453)` on all 56 qubits — uniform, smaller
  tilt. ⇒ **low-T vs intermediate-T differ ONLY in the initial-state angle θ** (π/6 vs −10°),
  at identical J·dt and h·dt. This resolves the earlier open question. (The "temperature"
  labels refer to the effective energy density of these initial states under the target
  Hamiltonian, not to any thermal-state preparation.) [established from circuits; the
  temperature interpretation is [inferred].]
- **quench3 (hydro):** `ry(−10°)` on 52 qubits + **`ry(π)` (full flip) on 4 qubits:
  q[7], q[21], q[35], q[49]**. These indices are spaced by exactly 14 = Lx, i.e. one flipped
  column of the 14×4 grid — the **inhomogeneous initial state** whose relaxation produces the
  emergent hydrodynamics. [established]
- **quench4 (triangular):** `ry(0)` on all 54 qubits ⇒ the reference circuits start from
  `|0…0>`. Per the README the real experiment instead initialized to two bitstring states in
  the minimal / maximal winding-number sectors; those bitstrings are NOT in the reference QASM
  and must be supplied to the harness as the actual initial product states. [established]

### Gauge/angle identities (README, important for matching) [established]
The circuits may use angles differing from the paper via two exact symmetries that leave all
measurement outcomes invariant: `(J,h,θ) → (−J,−h,θ)` and `(J,h,θ) → (J,−h,−θ)`. A sign
mismatch between our convention and the QASM angles is therefore expected and physically
irrelevant; the harness must not treat it as an error. (These are sign-only and do NOT rescale
magnitudes — see the h/|J| discussion above.)

---

## (4) What is NOT in the dataset (gaps the harness must handle)

[established unless noted]
1. **No `dt`, `J`, `h`, `theta` values as data fields.** They are only implicit in the QASM
   gate angles (and partially in the task brief, unverified). Physical time axis = step×dt
   must be reconstructed; the raw files give step index only.
2. **No explicit lattice bond list / adjacency.** The ZZnn formula implies a square grid with
   open-x / (y±1) neighbours, and quench4 is a triangular lattice with PBC (per the paper),
   but **no file enumerates the bonds or the (x,y)→qubit map.** The grid SHAPES are now
   resolved from the snapshot matrix dimensions (§1: 7×8, 7×8, 14×4, 6×9), but the explicit
   bond list and the exact (x,y)→qubit index convention still have to be reconstructed — most
   reliably by reading the `rzz` qubit-pair arguments directly out of `circuits/*.qasm`
   (the `rzz q[a],q[b];` lines ARE the bond list actually executed). [established that shapes
   are known; bond-list extraction from QASM is a remaining mechanical step not done here]
3. **No raw per-shot count tables as aggregated CSVs.** Shot-level data IS present but only as
   the `snapshots/` bitstring files (per-shot `Lx×Ly` 0/1 matrices for Z-basis `snapshot*` and
   leakage-gadget `leakage_snapshot*`), per step, per mode (`amplified`/`unamplified`). The
   processed observables are already reduced; re-deriving them needs the snapshot reduction
   described in the README. Only `quench1_step1` snapshots appear in the preview sample I read
   (hundreds of files); full per-step snapshot coverage not verified here. [inferred]
4. **Leakage snapshot caveats:** qubit (x,y)=(0,0) is reused as the first leakage ancilla so
   its leakage is never detected → always 0 in `leakage_snapshot`. The stored leakage snapshots
   are the raw ancilla measurements, NOT the "inferred leakage" used in ZNR (which required BOTH
   the Z-basis bit and the gadget bit to be 1). For quench4 (post-selection) only leakage-free
   snapshots are provided. [established]
5. **No simulator / exact reference curves.** The dataset is device data + circuits only; the
   logical/exact baseline for Q1 must come from OUR simulation. [established]
6. **No covariance / full bootstrap distribution** — only the point estimate and a single
   `_err` bar per entry. [established]
7. **ZNE/ZNR fit internals** (noise-scaling factors λ, regression coefficients) are not given;
   only the pre- and post-mitigation observable values. [established]

---

## Harness consumption checklist (hand to handoff/03)

1. Load `quenchN_steps.txt` → integer step vector; physical time = `step * dt` (dt from QASM /
   SI). Never assume 20 rows.
2. `Z2` → shape (M,), compare to simulated `<Z_tot^2>/N^2` (SECOND MOMENT, normalized by N²,
   NOT connected variance).
3. `ZZnn` → shape (M, Lx=14); row=step, col=x. Compare to simulated nn energy-density profile
   `E(x)` with the exact `/4` averaging in the README.
4. `ZZnn_fft` → (M, 8) = rfft over x of `E(x)`; `fft_decayrates` → (4,) over smallest q modes,
   `Γ_{q=0}=0`.
5. `dimercorrs` → shape (4, 8) = `[r, step]` (TRANSPOSE of the generic rule — orient by
   len(rs)=4 rows, len(steps)=8 cols); two sectors `min_winding`/`max_winding`.
6. For every observable `X` there is `X_err` of identical shape (bootstrap error; quench4 lacks
   `znr*`/`zne+znr` errs). Pick the mitigation column deliberately: `zne+znr` (square/hydro),
   `zne` (triangular = ZNE+post-select), `raw_unamplified` for bare device.
7. Expect gate-angle sign flips vs our convention from the two README gauge identities — treat
   as equivalent, not as a bug.
8. Override the quench4 `|0…0>` QASM init with the correct min/max-winding product state.

## Open questions for overseer / user

**RESOLVED 2026-10-06 (from the dataset itself):**
- ✅ **Lx,Ly per quench** — from snapshot matrix dims: 7×8, 7×8, 14×4, **6×9** (N=56,56,56,54).
  quench4 is 6×9 (N=54), the transpose of the brief's "9×6"; qubit count 54 confirmed by
  `qreg q[54]`.
- ✅ **dt, J, h, θ** — from QASM angles: `J·dt=0.25`, `h·dt=0.5` ⇒ **h/|J|=2, dt·|J|=0.25 for
  ALL quenches.** Brief's triangular `h/|J|=0.3` is contradicted by the circuits (should be 2);
  square `(2,0.25)` confirmed.

  > **2026-10-15:** correct as a reading of the reference, but it did not reach the config at the
  > time. Resolved by [`DECISIONS.md`](../DECISIONS.md) OPEN-1, option (a): the triangular study
  > keeps h/|J| = 0.3 as its own weak-field choice and no longer claims to match quench4. See the
  > fuller note under "CONTRADICTION WITH THE TASK BRIEF" above.
- ✅ **low-T vs intermediate-T** — differ ONLY in the initial `ry` angle: quench1 `ry(+30°)`
  vs quench2 `ry(−10°)`, at identical J·dt, h·dt.
- ✅ **hydro inhomogeneous state** — quench3 preps `ry(−10°)` everywhere except `ry(π)` on
  q[7],q[21],q[35],q[49] (one flipped column, spacing 14=Lx).

**STILL OPEN:**
- **Absolute dt and |J| separately** (only the products J·dt=0.25, h·dt=0.5 are fixed by the
  gate angles; the overall time unit is a convention). Fine for comparing dimensionless curves
  vs Trotter step, but needed if the harness wants a physical-time axis. Resolve from SI if a
  physical-time comparison is wanted.
- **The two quench4 winding-sector initial bitstrings** — the reference QASM uses `|0…0>`; the
  actual min/max-winding product states are not in the dataset and must come from the SI /
  paper to reproduce the dimer-correlation data.
- **Is the `_err` a 1σ bootstrap stderr or a CI half-width?** README only says "bootstrap
  resampling". Needed for χ²/agreement scoring in the harness.
- **The explicit (x,y)→qubit map and bond list** — recoverable from the `rzz q[a],q[b]` lines
  in the QASM (mechanical; not extracted in this pass).
