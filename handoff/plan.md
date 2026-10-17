# handoff/plan.md — hands-off BUILD run summary

**Run:** qc-overseer unattended BUILD under SCOPE §14. **Date:** 2026-10-06.
**Host:** Oracle Linux 9.8, aarch64, ~7.6 GB RAM free + 4 GB swap. Serial only.
**Status:** Stage 1 COMPLETE (reviewed, approved-with-conditions → conditions fixed).
Stage 2 single-level QEC COMPLETE (reviewed, approved). Concatenated Iceberg d=4 (handoff 01)
RETURNED from Claude Code, reviewed, APPROVED (conditions resolved — see §4 UPDATE). Next: Stage 3.

This file is the handoff registry (SCOPE §10/§14) and the end-of-run summary.

---

## 1. What was built

### Repo scaffold (SCOPE §8, §14) — DONE, NOT pushed
`git init` (branch `master`), directories `src/ src/qec/ tests/ data/ figures/ docs/
research/ notes/ review/ handoff/ scripts/`, `.gitignore`, pinned `requirements.txt`,
single `config.py`, `main.py`. **No `gh repo create`, no push** (SCOPE §8). A `.venv`
exists but is gitignored.

### Stage 1 — square lattice, unencoded (SCOPE §4.1) — DONE
- `config.py` — single `RunConfig` dataclass: backend switch (default `"statevector"`,
  local), lattice/model/trotter/ceiling/hardware sub-configs. Hardware is double-gated
  (`allow_hardware=False`, `max_shots=0`); nothing reaches network/hardware on import.
- `src/lattice.py` — row-major site indexing + square-lattice nearest-neighbour bonds
  (open/periodic, degenerate-wrap guard for L=2).
- `src/operators.py` — sparse Pauli operators and the TFIM Hamiltonian
  `H = -J Σ_<ij> Z_iZ_j - h Σ_i X_i`, built by **bit arithmetic** (diagonal ZZ + COO
  single-bit-flip X), not full-dimension kron products.
- `src/trotter.py` — 2nd-order Suzuki–Trotter (Strang) statevector evolution; O(2^N)
  memory (diagonal phase multiply + per-site moveaxis X-rotations).
- `src/observables.py` — M_z, M_x, Var(M_z), connected/raw two-point C_zz, energy
  (termwise and dense cross-check). (HANDOFF §3.)
- `src/backends.py` — `run_ed` (Lanczos `eigsh`), `run_statevector`, product-state
  builder (`all_up`/`all_down`/`neel`), ceiling guards, config-switch dispatch.
- `main.py` — thin driver reading `config.CONFIG`.
- `scripts/validate_stage1.py` — reproducible validation + memory probes.

### Stage 2 — square encoded / QEC gadgets (SCOPE §6) — single-level DONE
- `src/qec/iceberg.py` — Iceberg `[[k+2,k,2]]` code (arXiv:2211.06703): stabilizers
  `S_X = X^⊗n`, `S_Z = Z^⊗n`; logicals `Xbar_i = X_t X_i`, `Zbar_i = Z_b Z_i`.
- `src/qec/verify.py` — Stim stabilizer-algebra verifier: commutation, logical algebra,
  symplectic pairing, and distance-2 single-qubit-error detection.
- `src/qec/syndrome.py` — two-round Stim syndrome-extraction circuit with
  difference-detectors; errors injected as probability-1 Pauli channels so the clean
  run is deterministically silent and every weight-1 error fires a detector.
- `src/qec/concatenated.py` — detection-distance probe `min_undetected_weight` +
  `iceberg_detection_distance`, and (handoff 01, returned+approved) `ConcatenatedIceberg`
  **[[16,4,4]]** + M2-safe `code_distance`. The d=4 FT gadget lives in
  `src/qec/concatenated_gadget.py` (see §4 UPDATE).
- `src/qec/on_paper_codes.py` — 5-qubit `[[5,1,3]]` and Steane `[[7,1,3]]` standard
  stabilizers + logicals (SCOPE §6 on-paper path).
- `docs/qec_feasibility.md` — written feasibility analysis for the on-paper codes
  (SCOPE §6, Q4); no unmeasured numbers asserted.

### Research notes (in service of code, SCOPE §14)
`research/01-stage1-conventions.md` (TFIM conventions, Trotter, reproduction target
2503.20870 confirmed live), `research/02-stage2-iceberg.md` (Iceberg definition vs
2211.06703, status-tagged).

---

## 2. What was tested / verified (recorded, never invented)

- **Test suite: 37/37 pass** (`python -m pytest tests/ -q`, ~0.5 s). 25 Stage 1 +
  12 Stage 2.
- **Stage 1 validation** (`data/stage1_validation.txt`, reproducible):
  - ED Lanczos vs dense eigh (6 spins): `|diff| = 2.6e-14`.
  - Energy conservation (9 spins, T=2, 200 steps): `|dE| = 4.46e-04` (expected O(dt²)
    Trotter drift, not a bug).
  - Trotter convergence to exact `expm` (4 spins): clean **4.00× error reduction per
    step-doubling** → 2nd order confirmed.
  - **Probe-backed memory ceilings** (ru_maxrss, serial): statevector N=24 → ~1.5 GB
    (safe); ED build+Lanczos N=20 → ~1.9 GB (safe), N=22 → ~8 GB (near-OOM edge).
- **Stage 2** independently reproduced by qc-reviewer against arXiv:2211.06703:
  Iceberg stabilizers/logicals correct; distance exactly 2 (first undetected weight 2,
  witness X₀X₁ = Xbar₀·Xbar₁); two-round syndrome clean-silent and all weight-1 errors
  detected (k=2,4); 5-qubit and Steane measure distance 3.
- Both milestones **peer-reviewed** (`review/01-stage1.md`, `review/02-stage2.md`) and
  **annotated** (qc-annotator, comments/docstrings only, tests unaffected).

### Review outcomes
- **Stage 1: APPROVE WITH CONDITIONS → all conditions resolved.**
  - C1 (critical): old ED builder used full-D kron and OOMed at N=16 → **FIXED** (sparse
    bit-arithmetic builder; exact vs kron reference; now builds/diagonalizes to N=20).
    Regression-tested (`test_sparse_builder_*`).
  - M1/M2 (major): ceilings not probe-backed; tracemalloc undercounts → **FIXED**
    (validation uses `ru_maxrss`, probes at N=22/24 and ED N=16–20; ceilings frozen to
    probe-backed safe values: `ed_max_spins=20`, `statevector_max_spins=24`).
  - m2 (minor): missing `handoff/plan.md` → **this file**.
- **Stage 2: APPROVE** (no critical/major). Minors: M1 (concatenated.py docstring
  overpromise) → **FIXED** (trimmed); M2 (distance probe conflates undetected-vs-logical;
  harmless for current codes, matters for d=4) → **documented** in the probe docstring and
  in handoff 01's done-check; M3 (this file) → done; M4 (Python version) → §3 below.

---

## 3. FLAGS (require the project lead's decision — not silently resolved)

### FLAG A — Python 3.11 pinned, but 3.11 is unavailable on this host
SCOPE §7 pins **Python 3.11**. The host has only Python **3.9** and **3.12.14**; no
pyenv/conda to add 3.11 without a system change. **Stage 1 + Stage 2 were built and
tested on Python 3.12.14.** All 37 tests pass and the physics is verified on 3.12.
`requirements.txt` documents this and pins the versions actually tested
(`numpy==2.5.3`, `scipy==1.18.1`, `pytest==9.1.1`, `stim==1.16.0`).
**Decision for the project lead:** either (a) install Python 3.11 and rebuild `.venv` before the
tooling stages (guppylang/pytket-quantinuum pinning), or (b) accept 3.12 as the project
interpreter and amend SCOPE §7. This is a SCOPE change either way → yours to make.

### FLAG B — system packages installed to unblock Stim (medium-risk, reversible)
Stim has no prebuilt aarch64/cp312 wheel, so it builds from source and initially failed
(no `g++`, missing `Python.h`). To unblock Stage 2 I installed, via `sudo dnf` (NOPASSWD
was available):
- `gcc-c++` (11.5.0) and `libstdc++-devel`
- `python3.12-devel` (for `Python.h`)
Then `pip install stim` succeeded → **stim 1.16.0** (wheel cached in `~/.cache/pip`).
These are standard, reversible developer packages (`sudo dnf remove` to undo). Flagging
because it is a host system change, not a repo change. No hardware, network-exfil, or
production system was touched.

**Pragmatic relevance (added 2026-10-07, the project lead):** this build-deps step is **only needed when
`pip install stim` has no prebuilt wheel for the platform and must compile from source** —
which is what happened on this host (Linux **aarch64** + CPython **3.12**). **On an average local
machine — a mainstream OS/CPU (x86-64 Linux, macOS, Windows) with a standard Python — Stim ships
a prebuilt wheel on PyPI, so `pip install -r requirements.txt` installs a binary and NO system
packages (`gcc-c++`, `libstdc++-devel`, `python3.12-devel`) are required.** The other pinned
deps (numpy, scipy, pytket, guppylang, selene-sim, hugr) ship wheels on mainstream platforms too.
So someone cloning the repo on a typical computer will **not** hit this error; FLAG B bites only
on no-wheel combinations (ARM Linux being the common trigger). The fix in that case is the one-line
`sudo dnf install gcc-c++ libstdc++-devel python3.12-devel` (or the distro equivalent) before
`pip install`. *(Mechanism certain: wheel ⇒ no build deps; no wheel ⇒ build deps. The exact
per-platform wheel matrix for stim 1.16.0 was not re-queried against PyPI.)*

**Team note (2026-10-07):** the project runs on a virtual machine on an external server (Oracle Cloud, free tier) rather than a local laptop. *(Context: this is why the host is Linux aarch64 — a free Oracle cloud VM — exactly the no-wheel platform that triggered the build-from-source + FLAG B deps.)*

---

## 4. HARD STOP handed off (SCOPE §10/§14 — Claude Code; agents cannot launch it)

### handoff/01-concatenated-iceberg-d4.md — Concatenated Iceberg d=4 FT gadget
**Why stopped:** single-level Iceberg is fully literature-specified and is built+verified.
The **concatenated d=4** code needs an explicit fault-tolerant syndrome-extraction gadget
(ancilla scheduling, flag placement, cross-level discard) that is **not pinned to a single
literature target** in the fetched sources — i.e. a construction/dense-algorithm-design
task. Per SCOPE §10/§14 that routes to **Claude Code**; inventing it would violate "never
invent results." The brief has goal, physical context, inputs, constraints, objects to
produce, a done-check, and what the reviewer must verify. The distance-check machinery to
validate the deliverable on arrival is already in `src/qec/concatenated.py` (with the M2
caveat: measure *code* distance, excluding stabilizer elements).

**The project lead runs Claude Code on this brief; agents cannot.**

### UPDATE 2026-10-06 — handoff/01 RETURNED from Claude Code, reviewed, APPROVED
Claude Code delivered the concatenated Iceberg d=4 code. New/changed files:
`src/qec/concatenated.py` (`ConcatenatedIceberg`, default **[[16,4,4]]**, 18 qubits incl.
ancilla+flag; M2-safe `code_distance` that counts only genuine logical errors),
`src/qec/concatenated_gadget.py` (flagged FT syndrome gadget, cross-level any-detector discard
rule, `fault_distance`, `sample`), `config.py` (`QECConfig` under `RunConfig.qec`),
`scripts/run_concat_d4.py`, `tests/test_concatenated.py`, `docs/concatenated_iceberg_d4.md`.
**Full suite now 53/53.**

Review pipeline (reviewer → researcher → annotator, serial):
- **qc-reviewer `review/03-concatenated-d4.md`: APPROVE WITH CONDITIONS.** Independently
  reproduced both headline claims two ways each: code distance **4** (weight-4 witness, for
  (k_i,k_o) ∈ {(2,2),(2,4),(4,2)}); circuit fault distance **> 3** by exact ≤3-fault DEM search
  **and = 4** by Stim's search, **= 2** without flags (ablation genuinely not FT); Steane
  code-capacity validation returns 3. Clean run silent; all **16,248** weight-≤3 data errors
  detected in both bases; discard rates match an explicitly non-H2 model within CIs; logical
  rates reported as upper bounds; nothing invented.
- **qc-researcher `research/03-concat-citations.md`: both citations VERIFIED.** Knill C4/C6
  (Nature **434**, 39–44 (2005), doi:10.1038/nature03350, Fig. 1); Chao–Reichardt
  (arXiv:1705.02329 = PRL **121**, 050502 (2018); §V treats [[n,n−2,2]] Iceberg directly).
- **qc-annotator:** additive physics/intent comments on both modules; citations updated to the
  verified forms; 53/53 still pass.
- **Conditions resolved (overseer, docs only — no logic):** m1 error count 16,104 → **16,248**;
  m2 wording "fault distance 4" → "**> 3** (exact ≤3-fault search) and **= 4** (Stim search)" in
  doc §5/§7; m3 `[cite-unverified]` tags dropped everywhere (per researcher recommendation) with
  finalized locators. 53/53 pass after. → effectively a clean APPROVE.

Still open (per Claude Code / reviewer — not defects, feed SCOPE Q4 code-ranking):
- no correction mode for d=4 (detection-only at both levels; a d=4 code could correct 1 / detect 2);
- CX count per round not optimised (**88 CX/round**, drives the high discard rate);
- no comparison to the Iceberg-paper two-ancilla gadget;
- discard/logical numbers are under an **illustrative, non-H2** noise model — a hardware-regime
  number for Q1/Q4 needs a stated/justified noise model at the noisy-sim milestone.

---

## 5. NOT done (out of this run's scope / deferred by stage order)
- Stage 3 (triangular lattice — MAIN FOCUS): **geometry scaffold DONE** (reviewed APPROVE,
  review/04-stage3-triangular.md) — `triangular_bonds` (6-nn, periodic default, 3N-bond torus,
  coordination 6), wired through `_bonds_for`, TFIM machinery confirmed geometry-agnostic
  (ED-vs-dense, Trotter-vs-expm on triangular clusters), `tests/test_triangular.py` (6 tests,
  suite now 59/59). **Dimer correlations / winding sectors / Gauss-law constraint observables
  NOT built** — handed off to Claude Code (`handoff/02-triangular-dimer-gauss-law.md`) because
  they need the quantum-dimer / emergent-Gauss-law derivation that SCOPE §3 marks skeptical.
- Stage 4 (Guppy mid-circuit discard + 3D) — not started.
- Noisy-simulation milestone: Iceberg d=2 **post-selection/discard rate** and
  **logical-vs-physical** comparison (SCOPE Q1/Q4) are DATA questions, unmeasured by
  design, deferred with a stated noise model + uncertainties.
- Reproduction continuity: exercise the `neel`/`record_every` relaxation path and compare
  to Haghshenas (2503.20870) curves (SCOPE Q3) — machinery exists, comparison deferred.
- Full tooling stack (pytket, pytket-quantinuum, guppylang, qiskit, qermit, pandas,
  matplotlib) — commented in `requirements.txt`, add per their stages after FLAG A is
  resolved.
- Hardware / Nexus / H2 — stubbed and gated off; untouched (needs `allow_hardware` + the project lead).

---

## 6. How to reproduce
```bash
cd /home/opc/KiroTest-project
. .venv/bin/activate                 # Python 3.12.14 (see FLAG A)
python -m pytest tests/ -q           # 37 passed
python scripts/validate_stage1.py    # records data/stage1_validation.txt (~1 min)
python main.py                       # Stage 1 statevector run from config.py
```
Repo is prepared locally only. When the project lead approves, they create the GitHub repo and push
to a feature branch (SCOPE §8) — the agents do not.

---

## 7. Claude Code pass (2026-10-06) — handoff 01 RETURNED, awaiting qc-reviewer

**handoff/01 — Concatenated Iceberg d=4: IMPLEMENTED.** Write-up: `docs/concatenated_iceberg_d4.md`.
- `src/qec/concatenated.py`: `ConcatenatedIceberg(k_inner, k_outer)` (default [[16,4,4]]) and
  `code_distance` (M2-safe: counts only errors anticommuting with a logical). Old probes unchanged.
- `src/qec/concatenated_gadget.py`: flagged single-ancilla syndrome gadget (memory experiment, Z/X),
  discard predicate = any detector (flag / inner / outer), exact ≤3-fault DEM search, sampler w/ Wilson CIs.
- `config.py`: new `QECConfig` (sizes, rounds, flags, noise ratios, p scan, shots) under `RunConfig.qec`.
- `scripts/run_concat_d4.py` → `data/concat_d4.txt`; `tests/test_concatenated.py` (16 tests). Suite: **53/53 pass**.
- Measured: code distance 4; all weight≤3 data errors detected via the circuit; circuit fault distance
  **4** with flags (exact search + Stim's search agree), **2** without flags; discard rate 3.05% / 26.4% /
  59.9% at p = 1e-4 / 1e-3 / 3e-3 (illustrative noise, not H2-calibrated).
- For qc-researcher: confirm two citations tagged [cite-unverified] in the doc (Knill C4/C6, Chao–Reichardt flags).
- Not done: correction mode (d=4 → correct 1), CX-count optimisation, comparison to the 2211.06703 gadget.

---

## 8. Claude Code pass — handoff 02 RETURNED (triangular dimers / Gauss law), awaiting qc-reviewer

Write-up: `docs/gauss_law_dimers.md`.

**New or changed files**
- `src/dimers.py`: `TriangularDimers` with dimer n_b, defect D_t, charge, winding W_x/W_y, flippability, H_QDM, C_r by distance, and winding FCS.
- `src/gauss_mitigation.py`: exact noisy density matrix and Pauli trajectories, plus estimators: postselect, self-mitigation, ZNE, and the PEC γ.
- `config.py`: new `GaussLawConfig` (J = −1 AFM in our sign, h = 0.3, dt = 0.25, matching the reference §V).
  > **Superseded 2026-10-15 (section 25, `DECISIONS.md` DECIDED-1).** "matching the reference §V"
  > does not hold: the reference's released quench4 circuits are at h/|J| = 2. The value h = 0.3 is
  > unchanged and is now justified as a deliberate choice of the weak-field regime, where the
  > sector-restricted dimer description is valid. Kept as written, as the record of what was
  > believed at the time.
- `scripts/run_gauss_law.py` → `data/gauss_law_scaling.txt`, `data/gauss_law_mitigation.txt`.
- `tests/test_dimers.py` (34 tests). Suite: **93/93**.

**Measured**
- Exact identities hold over the whole basis:
  - Σn = N + ΣD;
  - #A-defects = #B-defects;
  - E_Ising = |J|(2ΣD − N);
  - W is a row/column-independent sector label on the constraint;
  - [H_QDM, D_t] = [H_QDM, W] = 0.
- Gauss-law violation ∝ (h/|J|)², with fitted slopes 1.96–2.05. The stripe prefactor matches the first-order (h/J)²/8 to 1.1%.

**Verdict**
- Correction: NO.
- Detection/postselection: a modest yes, only against X/Y-type noise (2–8× on spin correlators), floored by an O((h/J)²) physics bias. No against dephasing.
- Depolarizing self-mitigation from the defect density: NO as a general method (it can worsen observables up to 13×).
- Exact-symmetry methods: not applicable to Z-product quenches (⟨ΠX⟩ = 0).
- Platform ranking: undetermined. It is conditional on the residual channel's X/Y fraction, and no hardware data was used.

**Citations**: all 10 draft arXiv IDs resolve and match. Two draft characterizations remain unverified (doc §6). qc-researcher should check full texts, and confirm Moessner–Sondhi PRB 63, 224401 (2001).

---

## 9. Claude Code pass — handoff 03 RETURNED (Q1 comparison harness), awaiting qc-reviewer

Write-up: `docs/q1_compare.md`. **The harness is built; the real-data comparison has NOT been run, because the dataset is not on this host.**

**New or changed files**
- `src/compare.py`: `ZenodoData` loader, QASM reader, circuit-order Strang simulation, ceiling guard, and the Z2 comparison.
- `src/observables.py`: two functions added (`total_z_sq_normalized`, `nn_energy_density_x`); nothing above them changed.
- `config.py`: `CompareConfig` (J = 1, h = 2, dt = 0.25; θ = π/6 for quench1, −10° for quench2; periodic 4×4 and 4×5).
- `scripts/run_compare.py`, `tests/test_compare.py` (29 tests), and the synthetic fixture `tests/fixtures/zenodo_mini/`. Suite: **122/122**.

**Key results**
- Sign mapping (J, h) = (+1, +2) with the same θ is pinned by a literal gate replay, to 1e-12.
- The existing `trotter.py` splitting would have given a different Z2 at h·dt = 0.5 (0.63 vs 0.78). The harness uses the circuit order and leaves `trotter.py` unchanged.
- The circuit differs from continuous-H dynamics by up to 0.30 in Z2.
- The 4×4 vs 4×5 spread is 0.06 (quench1) and 0.33 (quench2), so the quench2 trend comparison is weak.

**Review**: an independent sub-agent found 3 major and 7 minor issues, no critical ones. All majors are fixed with regression tests; the status table is in the doc.

**To run**: `python scripts/run_compare.py --data /path/to/zenodo_data`. Then qc-reviewer on `data/q1_compare.txt`.

**UPDATE 2026-10-07: real-data run done.** The Zenodo dataset was downloaded (MD5 verified) to `/home/opc/zenodo_18487089/`, outside the repo, and `data/q1_compare.txt` written.
- The QASM check settles periodic BC and the row-major (x,y)→qubit map. This closes the research/05 §4 bond-list gap; research/05 itself was left untouched.
- The reduced lattice does not track the H2 decay: quench1 sim stays at 0.70–0.78 while H2 zne+znr falls 0.74 → 0.56; quench2 is dominated by finite-size revivals (spread 0.33).
- Hence no Q1 conclusion beyond "the harness and conventions are verified".
- Suggested next step: an exact N = 56 step-1 value from the one-bond light cone.

---

## 10. Claude Code pass — handoff 04 CHECKPOINT 1 (Part A, Iceberg) RETURNED; Part B awaits the project lead's go-ahead

Write-up: `docs/encoded_tfim.md`; Nexus plan: `docs/nexus_toggle.md`; data: `data/encoded_iceberg.txt`.

**New or changed files**
- `src/encoded_tfim.py`, `src/backends_qc.py` (local-sim | selene | nexus stub), `config.py: EncodedConfig`.
- `scripts/run_encoded.py`, `tests/test_encoded_tfim.py` (20 tests).
- `requirements.txt`: pytket 2.18.4, guppylang 1.1.2, selene-sim 0.3.4, hugr 0.18.8, plus **stim 1.16.0, now pinned** (it had been left commented out).
- Suite: **142/142**.

**Key results**
- **The FT done-check fails for Iceberg by construction.** The syndrome gadget is single-fault tolerant, but faults on the logical rotation gates leave XX/YY/ZZ on the gate support, which is undetectable and logical (63 Paulis = 21 gates × 3; 1/5 of each logical-gate fault).
- Transparency holds to ≤ 6e-15, and Stim, local-sim and Selene agree on a discriminating Clifford instance.
- Selene's real mid-circuit feedforward was verified.
- Limits: a modest reachable-time gain at p2 ≤ 3e-3 (1.3–3× shots); inefficient at 1e-2 (about 4–5% acceptance by step 6).
- Two backend quirks: the Selene compiler rejects XXPhase (H-ZZ-H used instead), and Selene's acceptance runs 3–8 points below local-sim.

---

## 11. Claude Code pass — handoff 04 PART B RETURNED (Steane, 5-qubit, concat d=4); awaiting qc-reviewer

The project lead's Part B choices: **standard B** (measured accounting, no FT pass/fail bar), **budget (ii)** (~55 H2 qubits; Stim at budget size; execution ≤ 24), and **measured** residual. Write-up: `docs/encoded_tfim.md` Part B. Data: `data/encoded_codes.txt`.

**New files**
- `src/encoded_codes.py`: a generic pipeline covering code specs, GF(2) pure errors, feedforward frame correction, minimum-weight representatives, flagged general-Pauli syndrome, parity-gadget rotations, a schedule → local-sim / Stim / generated-Guppy-on-Selene, measured accounting and the bare reference.
- `scripts/run_encoded_codes.py`; `tests/test_encoded_codes.py` (26 tests).

**Results**
- All four codes: `verify_code` passes, transparency holds to ≤ 6e-14, and Stim and execution agree over **all 4^k logical Pauli expectations** (≤ 6e-14). Selene runs with real feedforward.
- **The measured undetected residual per step is set by the rotation gadgets and is distance-independent:** at 2×3 and p2 = 1e-3, Iceberg 4.2e-3, Steane/5-qubit/concat 3.5e-3, bare 1.02e-2.
- First-order acceptance after 3 steps at 2×3: Iceberg 0.83, 5-qubit 0.28, concat 0.23, Steane 0.21. Executed acceptance ranks the same.

**Decisions**
- Iceberg is **built** and recommended.
- Steane, 5-qubit and concat d=4 are **built and not recommended**: each fits ~55 at 2×2 or more, but is dominated by Iceberg (1.2× lower residual for 3–5× lower acceptance).
- The handoff's expected 5-qubit discard is **not supported** by the measured gate cost.
- **The main open lever is active correction for the d ≥ 3 codes, which is not built.**

**UPDATE 2026-10-07: noise-sensitivity check** (the project lead asked whether Part B extrapolates to H2). Script `scripts/run_noise_sensitivity.py` → `data/noise_sensitivity.txt`; write-up in `docs/encoded_tfim.md`, final section.
- The code ranking (Iceberg ≥ Steane / 5-qubit / concat) is **robust** across ZZ bias, idle noise and over-rotation.
- **Whether encoding helps at all is NOT robust.** If more than about 25% of the native two-qubit gate error is ZZ-type (crossover η ≈ 0.25), every code's undetected residual exceeds bare's unprotected error. Coherent over-rotation erodes the gain toward ×1.
- Next measurement needed: H2's native two-qubit gate error composition (η) and its over-rotation.

---

## 12. 2026-10-07 — Selene gap resolved; handoff 05 created (DEFERRED, hardware-gated); new tracking files

- **Selene acceptance gap → resolved as a noise-model definition difference** (Claude Code; the project lead assigned it to Claude Code rather than Kiro).
  - Selene charges `p_1q` on every native one-qubit op: 724 `rxy` + `rz` vs the model's 188 pytket-level gates, ×3.85. It also charges `p_init` on allocations.
  - The two-qubit counts are identical (124).
  - Matching the counts explains ~60–80%; a 1–3σ residual stays open (T-1).
  - The ranking is unaffected and Iceberg's lead widens.
  - Script `scripts/diagnose_selene_gap.py` → `data/selene_gap.txt`; doc in `docs/encoded_tfim.md`.
- **The project lead deferred HW-1 (H2 gate-error composition η, ε) and HW-2 (active correction for the d ≥ 3 codes) until hardware access.** Briefed in **`handoff/05-hardware-gated-followups.md`** (status DEFERRED; goals G1 emulator calibration run → G2 measure η and ε → G3 encoded-vs-bare on H2 → G4 active correction).
- **New tracking files:**
  - `Conversation history/open-questions.md`: a living register of pending decisions and questions, companion to the journal.
  - `CLAUDE.md` (repo root): the working rules Claude Code follows in this project.

---

## 13. Claude Code pass — handoff 06 RETURNED (noise sensitivity at the H2 prior + review/08 doc fixes), 2026-10-07

Brief: `handoff/06-noise-sensitivity-h2-prior.md`. Inputs: `research/06-h2-noise-prior.md` §6 and `review/08` (m1, m2, m3, M1). Stim first-order accounting only; no execution, no hardware, no Nexus.

**Changed files**
- `config.py`: new **`SensitivityConfig`** block (`CONFIG.sensitivity`), additive. It holds the H2 prior (p2_prior = 6e-4, p1_ratio = 0.1, zz_bias_prior = 0.05, bracket (0.03, 0.08), overrot_scan (0, 1e-5, 1e-4, 1e-3)), the stress-test η (0.5, 0.9) and the original Part B rates, each with research/06's status tag.
- `scripts/run_noise_sensitivity.py`: reads `CONFIG.sensitivity` and has no hardcoded rates. Section 1 is the H2 prior. Section 2 is the original Part B table at p2 = 1e-3, kept for traceability. The η = 0.5 / 0.9 rows and the combined row are labelled "STRESS-TEST ~10x H2 prior, NOT representative".
- `data/noise_sensitivity.txt`: regenerated. Section 2 is cell-for-cell identical to the previous file. The header now carries the "classical prediction, NOT an H2 result" line.
- `docs/encoded_tfim.md`:
  - m1: 26 → 27 tests.
  - m3: −71σ → −70.6σ.
  - M1: the η-bias is exact for Iceberg's native `ZZPhase`; the d ≥ 3 frame is approximate.
  - The η rows in the old table are relabelled as stress-tests, and "plausible combined setting" → "combined stress-test setting".
  - New subsection **"Rerun at the researched H2 prior"**: table plus the predicted go/no-go paragraph, cross-referencing research/06.
- `data/selene_gap.txt` + `scripts/diagnose_selene_gap.py` (m2): the caveat line "classical simulators only (Stim / Selene / local-sim) under an ASSUMED noise model; NOT an H2 result" was added to the script's header output. The same line was inserted by hand into the existing data file as line 2. No number changed. Selene was not rerun, because a rerun would take minutes and draw new random shots.

**Results [measured, Stim first order; prediction-from-prior, NOT an H2 result]** (2×2, p2 = 6e-4, ratio = code undetected / bare unprotected per step)
- η = 0.05: Iceberg ×0.60, Steane ×0.53, 5-qubit ×0.52, concat ×0.53. Bracket η = 0.03 / 0.08: Iceberg ×0.56 / ×0.66, d ≥ 3 ×0.48 / ×0.59. **Below the η ≈ 0.25 crossover ⇒ encoding predicted to help.**
- ε scan at η = 0.05: sin²ε = 1e-5 / 1e-4 / 1e-3 → Iceberg ×0.62 / ×0.72 / ×0.92. Corner η = 0.08, sin²ε = 1e-3 → ×0.93.
  - In this twirled model ε adds the same 12·sin²ε per step to code and bare, so it erodes the ratio toward ×1 but cannot flip it [derived].
  - The flip risk is un-twirled coherent ε, which the model does not represent [inferred].
- First-order acceptance after 3 steps: Iceberg 0.92, d ≥ 3 0.56–0.64. The ranking is unchanged.
- The `zz_bias` mapping is conservative: total ZZ share = η + (1−η)/15 = 0.11 at η = 0.05, vs the ≈0.05 read-off [derived].

**Verification**
- An independent closed-form check (no Stim), with Iceberg = 12·p2(0.2+0.8η) + 12·sin²ε and bare = 4·p2 + 8·p1 + 12·sin²ε, reproduces all 10 section-1 rows (Iceberg, bare and ratio) to print precision.
- Section 2 matches the pre-rerun file exactly.
- Tests: full suite **169/169 pass** (99.7 s), including the 27 in `tests/test_encoded_codes.py`; unchanged.

**Open / next:** D-RC (randomized compiling on encoded H2 runs — the project lead, at handoff/05 time); T-10 (model cannot run the Fig. S3-shaped channel or un-twirled coherent ε; optional). Hardware half of HW-1 stays DEFERRED (handoff/05).

**UPDATE (the project lead, 2026-10-07): D-RC resolved — encoded H2 runs WILL use randomized compiling** (journal Entry 24, open-questions R-7). To be built in when handoff/05 is picked up.

---

## 14. handoff/07 WRITTEN (2026-10-07, qc-overseer) — sector-restricted MCMC ergodic baseline for Q3; DISPATCHED, awaiting Claude Code

**Brief:** `handoff/07-sector-restricted-mcmc-ergodic-baseline.md` (178 lines). **Status: DISPATCHED**
(written, not yet run — the project lead relays it to Claude Code; agents cannot launch it).

**Why a hard stop → Claude Code (SCOPE §10/§14).** Q3 (thermalization) is zero-progress
(`docs/findings_vs_questions.md` Q3 = NOT done): the relaxation machinery exists
(`src/trotter.evolve(..., record_every=…)`), but there is **no ergodic reference** to compare curves
against — the reference article takes its ergodic values from classical MCMC, and this project never
built that. Building it is **algorithm design** (a constrained within-winding-sector Markov-chain
sampler + a sector-leakage treatment) with **no single literature construction to copy** → routes to
Claude Code, not Kiro.

**The adjudicated design constraint (do not relitigate):** the baseline **must be per winding
sector** — ETH holds only within a topological sector in these dimer models (1706.02601, PRB 96,
115140 [established]; verified Entry 11, adjudicated review/06 / Entry 12). And because the winding
is only an *approximate* label under the TFIM, the baseline carries the project's **own measured**
O((h/|J|)²) leakage (`P(W≠W₀) ∝ h^2.08`, `docs/gauss_law_dimers.md §4`) as a drift band — not a
hard-conserved sector.

**What the brief asks for:** a sector-restricted classical MCMC sampler + per-sector ergodic
expectation values (reusing `src/dimers.py` operators) + a comparison harness overlaying a Trotter
relaxation curve on the W₀ baseline with the leakage band + a short write-up. **Suggested new files**
(all additive): `src/mcmc_baseline.py`, `tests/test_mcmc_baseline.py`, `scripts/run_q3_baseline.py`,
`data/mcmc_baseline.txt`, `docs/q3_thermalization.md`, plus a Q3/MCMC config block in `config.py`.

**Done-check (brief §Done-check):** MCMC per-sector averages match brute-force exact enumeration on a
small cluster within autocorrelation-aware errors; a sector-restriction test; identical observable
definitions between quantum curve and MCMC baseline; ceilings respected (ED ≤ 20, statevector ≤ 24);
no number presented as a quantum/H2 result.

**What the reviewer must verify (brief §What the reviewer must verify):** per-sector restriction is
correct AND necessary (a whole-space MCMC would mix disconnected sectors); convergence is real with
autocorrelation-aware errors; the leakage band uses the repo's own measured slope; observable
definitions match; nothing presented as hardware.

**Inputs cited (real APIs):** `src/dimers.py` (`winding_x/y`, `winding_distribution`, `defect`,
`total_defects`, `defect_density`, `dimer_densities`, `dimer_correlation_by_distance`,
`qdm_hamiltonian`, `three_sublattice_spins`, `stripe_spins`, `product_state_index`, `probabilities`,
`expval_diag`), `src/trotter.evolve(record_every)`, `src/backends.run_statevector/run_ed`,
`src/lattice.triangular_bonds`, `config.py:RunConfig.gauss`, `data/gauss_law_scaling.txt`.

**Pre-dispatch verification (Kiro, verify-don't-trust):** full suite **169/169** re-run green
(97.95 s) before writing; `SensitivityConfig` confirmed at `config.py:244`. Nothing committed/pushed.

**Resolves on return:** open-questions.md **T-6**. Also advances SCOPE Q3 and feeds the Q2 frustration
spine. **Not in scope:** the C_r metric fix (T-7), the Q1 matched comparison (T-9, hardware-gated).

---

## 15. Claude Code pass — handoff 07 RETURNED (sector-restricted MCMC ergodic baseline for Q3), 2026-10-07

Brief: `handoff/07-sector-restricted-mcmc-ergodic-baseline.md`. Classical and local only; no hardware, no Nexus. Write-up: `docs/q3_thermalization.md`. Journal Entry 26.

**New or changed files (all additive)**
- `config.py`: **`Q3BaselineConfig`** (`CONFIG.q3`): J, dt, h for the curves, window, cases, MCMC chains/sweeps/burn-in, the leak-table path.
- `src/mcmc_baseline.py`: per-configuration evaluator of the `src/dimers.py` observables (tested equal on every basis state); shared C(r); exact component/sector/global references; sector census; H_QDM diagonal ensemble; the sector-restricted MCMC; raw and sector-conditioned Trotter relaxation curves via `trotter.evolve(record_every)`; leak-table fit; verdict.
- `tests/test_mcmc_baseline.py` (**26 tests**); `scripts/run_q3_baseline.py` → **`data/mcmc_baseline.txt`**, **`data/q3_relaxation.txt`** (both with the "classical, NOT an H2 result" caveat line).
- `docs/q3_thermalization.md`; Q3 row of `docs/findings_vs_questions.md` → [measured], awaiting review.

**Design (brief's three questions)**
1. Ensemble: uniform (infinite-T) over the flip component of c₀ in its defect-free W₀ sector [derived: a product state sits at the H_QDM band centre]. Exact census N ≤ 20 [measured]: each sector is one component or all-frozen.
2. Sampler: random-site flippable flips (symmetric, so uniform on the component); sector re-checked every sweep; 32 independent chains from c₀; chain-mean SE + jackknife.
3. Leakage: exact bound |⟨O⟩ − ⟨O⟩_in| ≤ P_out·range(O); the conditioned curve is compared; the leak-table fit (h^2.08) predicts the measured leak to ≈1% (3×6) and 1–25% overall.

**Results [measured; classical, NOT an H2 result]**
- MCMC = exact on 3×3/3×4/3×6/4×5 within SE (max |z| 1.39, discriminating observables).
- Per-sector restriction necessary: 3×4 global vs sector flippable density 0.235 vs 0.267.
- Baselines to 9×6: flippable density 0.3026 ± 0.0002.
- 3×6 curves relax to the finite-cluster H_QDM diagonal ensemble (0.384 vs DE 0.388), not the infinite-T sector value (0.331). The cause is the finite-size energy-variance effect [derived qualitative, size trend inferred].
- Dressed O(h²) defect density predicted to 1–9%.

**Verification:** internal read-only reviewer sub-agent (own code, reproduced every number): ACCEPT-WITH-FIXES. M1 (C(r) window averaging), m1, m2 (curve guard at the ED ceiling), m3 and the nits all applied, with a regression test. Full suite **195/195**.

**Process note:** a second Claude Code session worked the same brief on the same files at the same time (Entry 26); the project lead assigned the build to this session. One Claude Code session per brief.

**Next:** qc-reviewer (independent; brief §"What the reviewer must verify") → qc-annotator → Kiro re-verifies → T-6 to Resolved, Q3 row status flip.


---

## 16. handoff/08 WRITTEN (2026-10-08, qc-overseer) — Q3 completion + K2 + figures; DISPATCHED, awaiting Claude Code

**Brief:** `handoff/08-q3-completion-trotter-threshold-curves-figures.md`. **Status: DISPATCHED** (written,
not run — the project lead relays it; one session per brief, T-13). **Larger two-part brief with a checkpoint** (PROC-1:
the project lead approved bigger briefs provided Part A lands as a reviewable unit before Part B).

**Scope.** Closes the biggest local, non-hardware loose end — Q3's "done when" (relaxation curves across
lattices/fields/encodings/noise + a size story) — and folds in two resolved decisions:
- **Part A (checkpoint):** the dt-convergence / Trotter-threshold study (**K2 = YES**, by the prior-hackathon
  precedent, Entry 30) + broadened ideal relaxation curves across more fields. Credibility anchor for every
  Q3 curve. Stop and get a Kiro review before Part B.
- **Part B:** noisy + Iceberg-encoded relaxation curves (stated assumed model; reuse the research/06 H2 prior
  for language parity), a reachable classical size story (no thermodynamic-limit claim), and the first
  **figures** (**FLAG C**): uncomment matplotlib, `scripts/plot_q3.py` reads `data/*.txt` → `figures/`.
- **K4 framing = YES** carried throughout (honest physics + QEC-methodology; no beyond-classical-dynamics claim).

**Explicitly excluded** (undecided, INCONCLUSIVE): K3 clock-order, K5 diffusion, K1, K6. The brief says not to
build them.

**Inputs cited (real APIs):** `src/mcmc_baseline.py` (`relaxation_curve`, `sample_sector`, `exact_references`,
`classify`, `qdm_diagonal_ensemble`, `ensemble_values`, `Shells`), `src/trotter.evolve`, `src/backends`
(`run_ed`/`run_statevector`), `src/dimers.py`, `src/gauss_mitigation.py`, `src/encoded_tfim.py` /
`src/encoded_codes.py`, `config.py:Q3BaselineConfig` (`CONFIG.q3`: J=−1, dt=0.25, h_curves, curve_cases,
exact_cases, mcmc_only_cases up to 9×6, n_chains=32…), `data/gauss_law_scaling.txt`, research/06 H2 prior.

**Done-checks + reviewer-must-verify:** in the brief (per part). Both parts: ceilings respected, cores additive
only, every noisy number tagged a classical prediction (not H2), figures reproducible from saved data.

**Resolves/advances on return:** more of SCOPE Q3 "done when"; K2 (built); FLAG C (figures). Nothing committed
or pushed. Pre-dispatch: full suite was 195/195 at handoff/07 acceptance.

---

## 17. Claude Code pass — handoff/08 PART A RETURNED (CHECKPOINT): Trotter threshold (K2) + field scan, 2026-10-08

(Numbering note: this file has two "§15" headings, Claude Code's handoff/07 return and Kiro's handoff/08 dispatch; this is §16.)

Brief: `handoff/08-q3-completion-trotter-threshold-curves-figures.md`, **Part A only. Stopped at the checkpoint; Part B not started.** Journal Entry 32. Write-up: `docs/q3_thermalization.md` §6 (field scan), §8 (threshold).

**New or changed files (additive)**
- `src/trotter_threshold.py`: Chebyshev exact propagator; Q3-identical observables; dt-error scan (every-step and shared-comparison modes); slope fit; threshold locator; Floquet resonances; late-window Trotter bias.
- `tests/test_trotter_threshold.py` (10 tests).
- `scripts/run_trotter_threshold.py` → **`data/trotter_threshold.txt`**.
- `config.py: Q3BaselineConfig`: `thr_*` fields; `h_curves` → (0.1, 0.2, 0.3, 0.5).
- `scripts/run_q3_baseline.py`: extrapolation label. **`data/q3_relaxation.txt`** regenerated (field scan); `data/mcmc_baseline.txt` byte-identical.
- `docs/q3_thermalization.md` §6/§8 + review/09 m1–m3 (T-14); `docs/findings_vs_questions.md`: new K2 row.

**Results [measured; classical, NOT an H2 result]**
- O(dt²) confirmed (slopes 2.00–2.04; infidelity dt⁴) on 3×3/3×4/3×6.
- Threshold dt ≈ 0.32–0.52 = the π/(6|J|) Floquet resonance [derived], broadened by h; the π/4 resonance is also seen.
- dt = 0.25 sits 1.3–2.0× below it for h ≤ 0.3 (absolute and relative criteria), but past the relative threshold at h = 0.5. Conditioned verdict quantities are Trotter-robust (≤ 0.12 × tolerance); P_out is inflated ≈10–25%.
- Defect density at dt = 0.25 is Trotter-inflated ≈40% (3×6).
- Field scan: verdicts stable for h ≤ 0.3; h = 0.5 is a weak-field-breakdown stress point.

**Verification:** 10 new tests; internal read-only review ACCEPT-WITH-FIXES, all M1–M5 and nits applied (Entry 32); full suite **205/205**.

**Next:** Kiro qc-reviewer on Part A (brief §"What the reviewer must verify", Part A) → then Part B.


### UPDATE 2026-10-08 — Part A reviewed (review/10, qc-reviewer): ACCEPT-WITH-FIXES → PART B RELEASED

Kiro's independent spot-checks + the independent qc-reviewer both confirmed Part A. The reviewer
re-derived every load-bearing claim with its OWN scipy-only code (dense `expm` / `expm_multiply`,
never the authors' Chebyshev, never by re-running their tests):
- the Chebyshev `ExactPropagator` is genuinely exact (≤3.6e-13 vs scipy even at T=20) — the reference
  everything is measured against;
- O(dt²) local / O(dt⁴) infidelity reproduced (slopes 2.025 / 4.043);
- threshold ≈ π/(|J| n_s) Floquet resonance — derivation sound, blow-up straddles 0.524 for n_s=6 and
  the stripe (n_s=2) stays smooth to ~π/2 (discriminating, not overreach);
- dt=0.25 placed honestly: safe (×1.3–2.0 below) for h≤0.3, correctly flagged PAST the relative
  threshold / stress point at h=0.5;
- sector-CONDITIONED Q3 verdict quantities Trotter-robust (≤0.12× tol); raw P_out +10–25% and raw
  defect density ~40% inflation correctly attributed to leakage, not the verdict signal;
- ceilings guarded, cores additive, classical/no-H2 tagging present, 205/205 (reviewer re-ran).

**No Critical/Major → PART B RELEASED.** Four minor doc/data items (m1–m4) are Claude Code's to apply
WITH Part B (not Kiro's files): m1 §8 "≤1e-10" understates achieved ~1e-13; m2/T-15 the defect-inflation
10%-vs-40% is start-dependent — bridge the two docs; m3 confirm `mcmc_baseline.txt` regenerated identically
(or leave untouched); m4 stripe "small error" framing already sound (no change).

**T-15 DECISION (Kiro, with reviewer concurrence): YES** — relay a one-line cross-reference from
`docs/gauss_law_dimers.md` (~line 130, the "~10%" defect line) to `docs/q3_thermalization.md §8`, since the
dt=0.25 defect-density Trotter inflation is start-dependent (≈40% 3-sublattice / ≈18% 3×4 flippable / ≈10%
stripe). Both docs are Claude Code's → relayed as a doc fix with Part B, not edited by Kiro. (open-questions
T-15.)

---

## 18. Claude Code pass — handoff/08 PART B RETURNED (noisy + Iceberg curves, size story, figures), 2026-10-08

Journal Entry 34. Write-up: `docs/q3_thermalization.md` §9. **Every noisy number is a classical prediction under the ASSUMED research/06 H2 prior, NOT an H2 result.**

**review/10 items:** m1 (§8 tolerance wording), m2/T-15 (`gauss_law_dimers.md` §4 cross-reference), m3 (`run_q3_baseline.py` provenance header; rerun IDENTICAL) applied; m4 no change.

**New or changed files (additive)**
- `src/noisy_q3.py`; `tests/test_noisy_q3.py` (8), `tests/test_plot_q3.py` (4).
- `scripts/run_q3_noisy.py` → **`data/q3_noisy.txt`**; `scripts/run_q3_size.py` → **`data/q3_size.txt`**; `scripts/plot_q3.py` → **`figures/` (5 PNGs, gitignored)**.
- `config.py` (`noisy_*`, `size_*`); `requirements.txt` (matplotlib 3.11.2 + pins).
- `docs/q3_thermalization.md` §9; `findings_vs_questions.md` Q3 rows.

**Results:** see Entry 34. Headline: Gauss-law post-selection of the bare circuit is the effective Q3 mitigation (≈6× on 3×3, ≈20–30× on 3×4, for ×1.2–4.8 shots); Iceberg + Gauss is at the statistical floor (not resolved as better) at ≈2.5–8× the shots and only reaches t ≈ 12; noise can mimic thermalization toward B_W₀; Iceberg 9×6 needs 58 > 56 H2 qubits; sector baseline to 12×12.

**Verification:** 12 new tests; internal read-only review ACCEPT-WITH-FIXES, M1–M6 + nits applied, data/figures regenerated; full suite **217/217**.

**Next:** Kiro qc-reviewer on Part B (brief §"What the reviewer must verify", Part B) → qc-annotator; FLAG C to Resolved on acceptance.


---

## 19. handoff/09 WRITTEN (2026-10-08, qc-overseer) — Q2 frustration thickening; DISPATCHED, awaiting Claude Code

**Brief:** `handoff/09-q2-frustration-thickening.md`. **Status: DISPATCHED.** Two-part with a checkpoint
(PROC-1). The project lead chose Q2 as the next focus (the main remaining local thread; least pre-empted novelty).

**Scope.** Closes the defensible part of Q2's "done when" (triangular-vs-square on frustration observables),
currently PARTLY done (only a 3×4 single-cluster ground-state table exists):
- **Part A (checkpoint):** the first like-for-like observable beyond energy/bond — distance-resolved
  **connected ⟨ZZ⟩_c = C(r)** for square vs triangular across h ∈ {0,0.1,0.3,0.6,1.0}, built on
  `observables.two_point_correlations_z` with a stated distance metric.
- **Part B:** a **size trend with honest error bars** across ceilings-reachable tori (ED ≤ 20), plus the
  triangular winding-sector/defect contrast framed as presence-vs-absence (square has no dimer description).

**Held firmly in the brief (framing discipline):** dimers/winding are triangular-only (not a false
like-for-like); the disorder-line / floating-phase guard (1303.0883) so a non-monotonic/incommensurate C(r)
is not misread as "frustration weakens order"; no thermodynamic-limit claim; **K3 clock-order and K5 diffusion
explicitly NOT built** (both INCONCLUSIVE — if the physics seems to call for clock order, STOP and flag, don't
build). Classical ED/exact only.

**Inputs cited (real APIs):** `observables.two_point_correlations_z`/`expval_zz`/`total_magnetization_z`/
`magnetization_variance_z`; `backends.run_ed`; `lattice.square_bonds`/`triangular_bonds`; `dimers`
(`defect_density`, winding, `torus_distance`); the existing `scripts/compare_frustration.py` to extend.

**Resolves/advances on return:** Q2 "done when" toward DONE-at-reachable-sizes. Pre-dispatch suite 217/217.
Nothing committed or pushed.

**DIRECTION NOTE (the project lead, 2026-10-08, PROC-2, journal Entry 39):** handoff/09 is the **last classical-depth brief**. After it, the next briefs are (1) the LaTeX report (SCOPE §13) and (2) hardware-path preparation, starting with HW-5 (handoff/05 G1, Iceberg H2-emulator calibration). Classical work only where a review, the report or the hardware path needs it.

---

## 20. Claude Code pass — handoff/09 PART A RETURNED (CHECKPOINT): distance-resolved C(r), square vs triangular, 2026-10-08

Journal Entry 40. Write-up: `docs/q2_frustration.md` (Part A). Classical ED only; [measured].

**New files:** `src/frustration.py`, `scripts/compare_frustration_correlations.py` → **`data/frustration_correlations.txt`**, `tests/test_frustration.py` (14), `docs/q2_frustration.md`; `config.py: Q2FrustrationConfig`; Q2 row in `findings_vs_questions.md`.

**Results:**
- Matched 4×4: square C(1) −0.94…−1.00 with no decay; triangular C(1) −0.20…−0.33, long-distance weak and field-fragile.
- The triangular pattern is torus-shape dependent (disorder-line caveat).
- **Correction:** the odd-length 3×4 square torus of the old Q2 table is itself frustrated (T-19).
- Clock-type correlations flagged for K3, not built (T-20).
- Only 4×4 is a clean square torus within ED ≤ 20 (T-21, affects Part B).

**Verification:** 14 tests; internal read-only review ACCEPT-WITH-FIXES (M1–M4 + nits applied, wording only); full suite **231/231**.

**Next:** Kiro qc-reviewer on Part A → then Part B. PROC-2: this is the last classical-depth brief.


---

## 21. handoff/10 WRITTEN (2026-10-08, qc-overseer) — ROLE TRANSFER to Claude Code; Kiro's final brief

**Brief:** `handoff/10-role-transfer-finish-project.md` (225 lines). **This is Kiro's last brief** — the project lead is out
of Kiro usage for the month, so Claude Code now runs the overseer/review/annotator functions too and finishes the
project solo (ideally one session, else Claude-Code-only sessions).

**Also:** handoff/09 **Part B CANCELLED** (the project lead, PROC-2) — a banner was added to the Part B section; do not build it.

**handoff/10 transfers:**
- the **state snapshot** (231/231; Q3 complete+reviewed 09/10/11; Q2 Part A complete+reviewed 12, Part B cancelled;
  Q4 Iceberg recommended; Gauss verdict recorded; report + hardware pending);
- the **ordered plan (PROC-2):** (1) LaTeX report (SCOPE §13) → (2) relay backlog → (3) hardware HW-5/G1–G4 on
  the project lead's approval → (4) parked items only if the project lead decides;
- the **SELF-REVIEW PROTOCOL** that replaces the independent qc-reviewer (re-derive load-bearing numbers with fresh
  code/method, re-run the suite, separate verified-vs-could-not, severity verdict, honesty audit, write review/13+);
- the **LaTeX report spec** (SCOPE §13; new `docs/report/report.tex`, English; explicitly NOT the gitignored Spanish
  `Conversation history/reporte-tecnico-equipo.tex`; findings-table centrepiece; honest tags; reuse `figures/`);
- the **relay backlog** (T-19; review/11 m1–m3; review/12 m1–m3; T-15 check);
- the **discipline** (verify-don't-trust, no-invented-numbers, classical-vs-H2 labelling, don't-touch-cores,
  ceilings, hardware/push/SCOPE = the project lead's, keep registers current);
- ordered **authoritative pointers**.

**Nothing committed or pushed.** Pre-transfer suite 231/231. Kiro is offline after this pass.

---

## 22. Claude Code (overseer, handoff/10) — JOB 1 DONE: SCOPE §13 LaTeX report + relay backlog; review/13; 2026-10-08

Journal Entry 43. The project lead's instructions for this pass: jobs 1–2 only, **hardware NOT approved** (stop and report).
Tectonic 0.15.0 installed in `~/.local/bin` (the project lead's choice) to test-compile.

**New:**
- `docs/report/report.tex`: the SCOPE §13 report (English, 16 pp.).
  - Contents: thesis + K4 framing; methods; Q1; Q4; Q2; Q3 with figures; the Gauss-law verdict; a findings-vs-questions longtable; the hardware plan; limitations; reproducibility; bibliography.
  - Figures load from `../../figures/` or `./figures/`, with a placeholder if absent.
- `review/13-latex-report-selfreview.md`: the self-review plus an independent read-only sub-agent. ACCEPT-WITH-FIXES → fixes applied.
- `Conversation history/team-report-en.tex` (gitignored): a plain-language English team report in the structure of the project lead's Spanish team doc. Requested by the project lead; not a deliverable.

**Relay backlog (handoff/10 §6):** all applied or confirmed (open-questions R-13).
- `scripts/compare_frustration.py` + `data/frustration_compare.txt`: T-19 caveat, data regenerated.
- `scripts/run_q3_baseline.py` + `data/mcmc_baseline.txt`: content-sha256 line; the rerun is IDENTICAL.
- `docs/q2_frustration.md`: worst ΔE; h_c tag; Part B cancelled.
- `docs/q3_thermalization.md`: C1 = C(0.866).
- `scripts/run_q3_noisy.py`: comment only.
- T-15 and review/10 m1 confirmed already applied.

**Correction found by the review (M1):** the FLAG-0 crossover η ≈ 0.25 (and ×0.60) is the **2×2-lattice** value, the most pessimistic case. It is ≈0.36–0.55 on larger square and triangular tori.
- Now stated in `docs/encoded_tfim.md`, the findings Q1 row and the FLAG-0 banner.
- This runs in the favourable direction; the conditional GO stands.

**Also:** `docs/findings_vs_questions.md` stale statuses are refreshed (Q2/Q3 Part A reviewed; Q2 done at reachable sizes).

**Verification:**
- Every load-bearing number was re-derived in fresh code with zero differences (review/13 §1).
- The figures are byte-identical on regeneration.
- The suite is **231/231**.

**Next:** JOB 3, the hardware path (handoff/05 HW-5 → G1–G4), **only on the project lead's approval**. Otherwise the project is complete at classically reachable sizes. Push/commit only on the project lead's request.


---

## 23. 2026-10-08/09 — the project lead's decisions, repo cleanup, first GitHub push, STANDSTILL brief (handoff/11)

Journal Entries 44–47.

**Decisions (the project lead):**
- **T-18 → R-15:** the encoded H2 Q3 run uses 6×6 plus the minimal relevant 3×4.
- **T-17 → R-14:** H2 Q3 curves are always compared with the noise, so 6×6 needs a noise-scaling arm.
- Both are recorded in `handoff/05` (a decisions block) and in both reports.

**Cleanup:**
- Deleted: `notes/` (empty), `docs/.gitkeep` and the caches.
- `drafts/gauss_law_self_mitigation_assessment.md` moved to the gitignored `Conversation history/dump/`.
- A superseded banner added to `docs/qec_feasibility.md`.
- `README.md` written. `requirements.txt` header and a stray character in `KIRO.md` fixed.

**Published (one-time permission):** `github.com/KmarH/TFIM_QEC_Frustation`, branch `initial-import`, commit `37e6879`, 171 files. Pushed with a single-repo deploy key; author is the KmarH noreply address.

**Standstill:** `handoff/11-standstill-awaiting-hardware.md` is the snapshot to resume from. It covers state, decisions in force, the ordered hardware steps with their local prerequisites, open items and environment.

**Pre-access prerequisites, not built:**
- randomized compiling in the encoded programs (D-RC);
- the 6×6 noise-scaling arm;
- the Quantinuum client install;
- the `nexus` backend.

**Published:** section 23 and handoff/11 were pushed with the peer-review fixes (2026-10-14). See section 24 for the current state: default branch `main`, the pre-review state preserved as `alpha`, suite 274/274 on three platforms.

## 24. Three-machine peer review and the fixes it produced, 2026-10-12/14

**Pass type:** independent review, then repair. Not a build pass; no new physics.

**Reviewers.** Three Claude Code instances, each on its own machine, each with its own
subagents: **R-Oracle** (Oracle Cloud VM, Linux aarch64, Python 3.12 — the reference platform,
and the only host with the Zenodo dataset and the private journal), **R-Laptop** (home server,
Linux x86_64, Python 3.14), **R-Main** (Windows 11, Python 3.13, also orchestrator). Three
rounds: independent review with separate focus areas, mutual cross-verification of every
finding, then adjudication of each disagreement with a decisive check. About 40 numbers were
re-derived from code that does not import this project. Reports: `review/14-three-machine-peer-review.md`
(consolidated). The nine per-round reports, the Round-3b cover and the dispute
assignments were later removed from the working tree to keep the repository lean; they remain in
git history at commit 88c8c2a.

**Headline.** No fabricated number and no arithmetic error. Every independent re-derivation
matched; every reproduction that ran matched its committed data file, often byte for byte. The
real problems were about which experiment the numbers describe.

**Three MAJOR findings, each confirmed by all three reviewers.**
1. The triangular reference field is unreconciled: `h/|J| = 0.3` here, **2** in the reference's
   own released quench4 QASM (signed angles read from all 80 files). `research/05` found this and
   it never reached `GaussLawConfig`/`Q3BaselineConfig`; `research/04` independently confirmed 0.3
   from the paper's prose, whose §V body was never read. At `h/|J| = 2` the sector framework is
   not a controlled approximation at all. **No constant was changed** — recorded as `DECISIONS.md`
   DECIDED-1 (formerly OPEN-1); resolved 2026-10-15, see section 25.
2. The dt = 0.25 defect-density and `P_out` "Trotter inflation" figures were attributed to the
   reference circuit; in that circuit's own ordering the bias has the **opposite sign** (3×6
   defect density 1.390 ZZ-outside vs 0.604 circuit-order). Fixed additively:
   `src/trotter.circuit_trotter2_step`, a regression test, and
   `scripts/run_trotter_order_compare.py` → `data/trotter_order_compare.txt`.
   The threshold brackets, O(dt²), the π/6 resonance and the sector-conditioned verdicts survive
   and are ordering-invariant.
3. Q1's "encoding is the only axis that varies" against the released data is infeasible: Iceberg
   needs k+4 physical qubits, so 7×8 needs 60 > 56. Reframed to encoded vs bare on one reduced
   lattice (6×8 = 52 physical), released data as external reference; `compare.Series` gained
   shot/acceptance/estimator fields. `DECISIONS.md` OPEN-2.

**Also fixed.** The project did not run on Windows (28 file-I/O sites had no explicit encoding;
`python -I main.py` was broken). `verify_circuits` was sign-blind while `report.tex` claimed
otherwise — now checks the signed triple against the gauge set. `--skip-exec` truncated
`data/encoded_codes.txt` §5. A 5-shot Gaussian error bar became a labelled t-interval, and
acceptance a Wilson interval. The "Néel" state was column stripes for even `Lx`. Three test gaps
closed, including a sector-escape guard test that passed with the mover stubbed out. A dozen
documented numbers corrected against the data (6.6–8.6× not 3–7×; 32× not 13×; ≈2.0σ not ≈3σ;
7 of 24 cells not "one early point"; slopes 1.97–2.04).

**Two reviewer findings were refuted** by the other reviewers and withdrawn: that the first-order
Stim accounting breaks down at low acceptance (exact Monte Carlo agrees to ≤1.1e-3 even at 1%
acceptance, confirmed three times), and a "63 vs 42" doc/data mismatch (two different, both
correct metrics with similar names — now disambiguated in the docs).

**Suite:** 231 → **274 passing**, identical count on all three platforms. No test removed or
weakened. No existing `data/` file modified; one added. No physics constant changed — every
`config.py` edit is inside its comment block and the enforced ceilings are untouched.

**Still not built (hardware prerequisites, unchanged by this pass):** randomized compiling
(D-RC, `DECISIONS.md` OPEN-3) — the Q1 "encoding helps" GO rests on it; the 6×6 noise-scaling
arm; the Quantinuum client; the `nexus` backend. **Not regenerated:**
`data/encoded_codes.txt` §5 (hours of Selene) and `data/q1_compare.txt` (needs the dataset).

## 25. DECIDED-1: the triangular field stays at h/|J| = 0.3, as a weak-field study, 2026-10-15

> **SUPERSEDED the same day by section 26.** The premise below — that the reference's triangular
> field is h/|J| = 2 — is **wrong**. The paper's Figure 4(e) states "All data taken at
> (h/|J|, dt|J|)=(0.3, 0.25)", so this project's configuration *does* match the reference. The
> h/|J| = 2 figure came from the released quench4 circuit files, which carry the square quench's
> field. Read this section as the record of a decision taken on incomplete evidence; section 26
> has the resolution. The value h = 0.3 was never changed at any point.

**Pass type:** scope decision and the documentation change it implies. **No code, no constant and
no number changed.** Suite unchanged at 274/274 on three platforms.

**The decision.** Of the two options recorded in `DECISIONS.md` DECIDED-1, the project lead chose
**(a)**: keep `h ≤ 0.5` and state the triangular thread as a deliberately chosen, self-contained
study of the weak-field frustrated regime. It does **not** reproduce the reference's triangular
quench, whose released quench4 circuits are at `h/|J| = 2`. Option (b), building a genuine
`h/|J| = 2` study, was not taken: it needs different machinery (the sector theory is first order
in `h/|J|`) and an initial state the data release does not contain, so it is new research rather
than a correction.

**The justification now cited in the docs is physics, not the reference.** `h/|J| = 0.3` is where
the sector-restricted quantum-dimer description holds: it is a first-order-in-`h/|J|` effective
theory, leakage out of the defect-free sector goes as about `h²` (measured exponent 2.08), and
this project's own field scan finds the in-sector verdicts stable at `h ≤ 0.3` and straining at
`h = 0.5` (26% of the weight out of sector). At `h/|J| = 2` the in-sector probability collapses to
0.13–0.63 within a single Trotter step and the in-sector weight falls with system size (0.55 at
N = 9, 0.11 at N = 12), so the constraint the thread tests barely exists there.

**What changed.** Every claim tying the triangular field to the reference was withdrawn and
replaced with the scope statement plus that justification: `README.md`, `docs/report/report.tex`
§Model, `docs/findings_vs_questions.md` (plus a frame qualifier on the Gauss-law floor, which is
≈0.0092 in circuit order and ≈0.0135 in this repo's ordering), `docs/q3_thermalization.md`,
`docs/gauss_law_dimers.md`, `docs/q2_frustration.md`, `config.py`'s triangular blocks (comments
only), and the Q3/Gauss scripts' and modules' docstrings. `DECISIONS.md` DECIDED-1 became DECIDED-1.

**Q2 is unaffected** and is now labelled as what it is: a **ground-state** exact-diagonalization
result, reported at `h ≤ 1`. Its 3–5× weakening also holds at `h/|J| = 2` (4.98 on the matched
4×4 pair, against 4.59 at `h = 1`), so it does not depend on this decision at all.

**The historical record was annotated, not rewritten.** `research/04`, `research/05`,
`research/scout/sweeps/01`, and `handoff/03`, `handoff/09`, `handoff/11` keep their original
wording and carry a dated note pointing at `DECISIONS.md`. Rewriting them would destroy the audit
trail that made this conflict findable — `research/05` had the right answer in October 2026 and it
simply never propagated to the config.

**Still open, unchanged by this decision:** the factual question of what the paper's §V body
actually says (its HTML truncates; the PDF or Supplemental Material would settle whether more than
one triangular run exists), randomized compiling (`DECISIONS.md` OPEN-3), and the Q1 lattice
implementation (OPEN-2). Independently of the field: the released quench4 circuits prepare
`ry(0)` with no `x` gates, so they fix neither winding sector, which confirms T-5 by inspection.

## 26. RESOLVED-1: the triangular field IS the reference's 0.3 — section 25 reversed, 2026-10-15

**Pass type:** evidence, and the reversal of the previous section. **No code, no constant and no
number changed** — again. Suite unchanged at 274/274 on three platforms.

**What happened.** Section 25 reframed the triangular thread as a self-contained weak-field study
on the belief that the reference's triangular field was `h/|J| = 2`. The paper's full text was
then retrieved and **that belief was wrong**. The reframing is withdrawn.

**The evidence** (arXiv:2503.20870v3, read in full):
- **Figure 4(e), verbatim: "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)."** [established]
- §V, "Emergent gauge theory on a frustrated lattice", sets the regime: "For weak transverse field
  (0 < h ≪ J)". [established]
- The triangular lattice is **9×6** (§V, and Methods §VII.1). One triangular run, one field; the
  max/min winding sectors are two initial states within it. The paper states the *square* quenches
  use h = 2|J|, explicitly a different system. [established]
- Earlier fetches failed only because the HTML is 244,452 characters and truncated before Figure 4.
  `research/04`'s caveat that §V's body was never reached is now closed — and it had been right.

**Why the circuits said otherwise, and why they are wrong.** `quench4_step1.qasm` holds
162 × `rzz(0.5)`, 108 × `rx(0.5)`, 54 × `ry(0)` on `qreg q[54]`. The counts are correct for 9×6
(162 = 3N bonds, 108 = two half-layers), so the geometry is genuinely triangular — but the angles
are **quench1's**, i.e. the square quench's field. At `dt|J| = 0.25` that is `h/|J| = 2`; the
paper's 0.3 would need `rx(0.0375)`, about 13× smaller. The dataset's gauge identities only flip
signs and cannot bridge a magnitude. The release separately documents that the quench4 circuits are
initialized to `|0…0>` while the experiments used two winding bitstrings, so the field is a second
instance of the same defect — in files the README offers "to cross-check against the gate angles
and circuit geometry we used". [measured]

**The physics was the tell.** §V reports dimer correlations relaxing toward Markov-chain Monte
Carlo values inside winding sectors. That cannot happen at `h/|J| = 2`, where this project's own
reviewers measured the in-sector probability collapsing to 0.13–0.63 within a single Trotter step.
That argument identified which source had to be wrong before the text was ever retrieved, and it
is the generalisable lesson: when a released artefact and the publication disagree, check which one
the physics can support.

**What changed in the repo.** The reference citation for the triangular field is restored, now
sourced to Figure 4(e) and tagged [established], in `README.md`, `docs/report/report.tex` §Model,
`docs/findings_vs_questions.md`, `docs/q3_thermalization.md`, `docs/gauss_law_dimers.md`,
`config.py` (comments only) and `scripts/run_gauss_law.py`. `DECISIONS.md` DECIDED-1 became
**RESOLVED-1**, keeping the full OPEN → DECIDED → RESOLVED sequence on purpose. The weak-field
argument from section 25 is **kept**, reframed as corroboration. The new finding about the quench4
circuits is recorded in `research/05-zenodo-dataset-map.md`, the dataset map, which is where a
future reader would look.

**Kept from section 25, independent of the reversal:** Q2's relabelling as a **ground-state**
exact-diagonalization result, and its h/|J| = 2 robustness check (ratio 4.98 on the matched 4×4
pair). Both stand on their own.

**T-5 narrows.** The two winding sectors **are** identified in the release, as the
`quench4_min_winding_*` and `quench4_max_winding_*` data files. Only the explicit initial
bitstrings and matching circuits are absent.

**Still open:** randomized compiling (`DECISIONS.md` OPEN-3) and the Q1 lattice implementation
(OPEN-2). Nothing in this pass touches either.

## 27. DECIDED-5: the 6×6 noise-scaling arm (T-17 / R-14), designed and classically validated, 2026-10-16

**Pass type:** research-flow, through all stages: KB → derive → decisions D1–D7 → frozen tests → implement → blind review → handoff.
**Classical predictions under the ASSUMED prior; nothing ran on H2.**

**Built.**
- `src/noise_scaling.py` (new, additive):
  - Pauli insertion and folding (both pytket circuits and the `run_bare_scaled` trajectories);
  - first-order Stim scaling, which reuses `encoded_codes` through a restored `to_stim` wrapper;
  - the weighted slope test, the fixed-asymptote exponential fit, and the HQC formula.
- `config.py`: `NoiseScalingConfig`.
- `scripts/run_noise_scaling.py` → `data/noise_scaling.txt`.
- Docs: `docs/q3_noise_scaling.md`, a `report.tex` §Q3 paragraph, and `DECISIONS.md` DECIDED-5.
- KB: `research/07-noise-scaling.md`, `research/sources.md` (new index), and `research/derivations/01-noise-scaling-arm{,-testspec}.md`.

**Decisions (the project lead):**
- D1 diagnostic first;
- D2 insertion + one fold;
- D3 bare + Gauss only;
- D4 λ = {1, 2, 3};
- D5 B fixed at infinite T;
- D6 compile level 0, T4/T5 on 3×3, new T17;
- D7 t ≤ 3 at slope 0.005, ≈ 8.3×10⁴ HQC.

**Key findings.**
- [measured] An offline H2-1 compile at TKET levels 1–2 cancels the fold (27/27 two-qubit gates instead of 27/81). Unguarded, the λ = 3 point would have run as λ = 1.
- [measured, 3×4] Gauss post-selection already removes most of the noise effect on the conditioned flippable density (0.0002–0.0027 from ideal at λ = 1). The diagnostic still resolves ≈ 0.001–0.003 slopes when the SE is small.
- [derived] Late-time 6×6 λ = 3 points lose about 98% of shots to post-selection, so no late-time 6×6 thermalization claim is possible within any modest budget.

**Tests.**
- Frozen file SHA-256 `FED386D4…5EF8`.
- Suite (397 = 372 + 25): local 397/397 (Win, Py 3.13, 432 s); OLP 397/397 (review B); OVM 397/397 (aarch64, Py 3.12.14, 342 s).

**Review:** `review/15`. Both minor; no open major.
**Handoff:** `handoff/12`. **Still open:** OPEN-2, the OPEN-3 submission path, G2. O-NS1 is a tighter T14 (needs approval).

## 28. H2 submission path built and validated on the local emulator; no HQC spent, 2026-10-17

**Pass type:** research-flow (spec → blind frozen tests → implement → verify). Kiro did not brief this pass; the project lead asked for it directly. **Classical predictions and H2-*local*-emulator runs; nothing ran on Nexus.**

**Built (all additive; verified cores untouched).**
- `src/h2_circuits.py`: the Iceberg program, bare reference and the Steane / 5-qubit / concatenated programs as one pytket circuit each (mid-circuit syndrome measure+reset into registers, round-0 feedforward as real conditional gates, RC frame corrections applied in `shot_records`), O0 compile with a 2-qubit-count guard, native counts, HQC estimate.
- `src/h2_backend.py`: `run_le` (offline H2-1LE; noisy through PECOS directly), `syntax_check` (free SC tier, refuses every non-SC device), `submit_nexus` (HQC tier, gated; **never called**), `fetch_nexus`, a ledger, `offline_compile_backend`.
- `config.py` `HardwareConfig` fields; `requirements-le.txt` (+ `qnexus` pin in `requirements.txt`); `.gitignore` (`.venv-le/`, `runs/`).
- `scripts/run_h2_le.py` → `data/h2_le_validation.txt`; `scripts/h2_hqc_budget.py` → `data/h2_hqc_budget.txt`.
- Docs: `docs/nexus_toggle.md` rewritten, `docs/h2_budget.md`, **`docs/quantinuum_issues.md` (new, ongoing: Quantinuum software issues, 10 entries)**, `DECISIONS.md` OPEN-4, `CLAUDE.md` rules.

**Findings that change the plan.**
- [established, source] qnexus 0.51.1's Guppy/HUGR route is **Helios-only**; H2 takes pytket/QIR. The Guppy feedforward-discard program cannot be the H2 submission (HW-3, answered "no" pending the SC). The discard is applied classically instead; HQC is on static gate counts, so cost is unaffected. (QI-3)
- [established, docs excerpt] the Nexus **H2 emulator is ≤ 32 qubits state-vector (56 stabilizer, Clifford only)**. The 6×8 Q1 lattice (52 q) and the 6×6 noise-scaling arm (36/40 q) cannot run on it. Recommended Q1 headline lattice moves to **4×5** (24 qubits; also runs locally). DECISIONS.md OPEN-4 holds the options. [unverified: page itself was blocked in this container]
- [measured] the LE ignores `noisy_simulation` and is always an ideal state vector (QI-2); PECOS rescales p1/p2 by 3/2 and 5/4 (QI-9); `pytket-quantinuum[pecos]` cannot co-install with selene-sim 0.3.4 (QI-1); a qnexus cost-device bug (QI-5, from source).

**Results** (`data/h2_le_validation.txt`, 4000 shots, [measured]): noiseless Iceberg 2×2 and 2×3, steps 1–3, plain and randomized-compiled, acceptance 1.000 and Z2 within 2.1σ of the exact value in every row; bare likewise; five-qubit 1×2 Clifford and generic cases agree within 2.6σ (one point at +2.6σ, rechecked below). Noisy LE accepts fewer shots than local-sim at the same rates (e.g. 0.639 vs 0.703 at p2 = 0.003, step 3) as expected from native-gate charging.

**HQC plan** (`docs/h2_budget.md`): G1 2.1k, Q1 4×5 13.2k, Q4 11.7k = 27.0k of 50k (54%); Q3 3×4 rows are formula estimates. All offline; the free SC quotes will replace them.

**Tests.** New frozen files, written blind to the implementation (it was moved aside while they were written; they errored on import): `tests/test_h2_circuits.py`, `tests/test_h2_backend.py`. **Deviation from test-first: the implementation was written before the tests, then hidden from the test writer.** After the first run, two assertions were wrong in the *tests* (measurement order compared in `get_commands()` order; and my spec's "Clifford Z2 is 1/k or 1", which is false at 2×2); the project lead approved correcting them and re-freezing. Old `test_h2_circuits.py` SHA-256 `7155f2c8…7155`, new `dceab7c3…ed80`; `test_h2_backend.py` unchanged `6e38b8fe…fb80`. Counts: `.venv` 69 pass + 22 skip (emulator); `.venv-le` 91 pass.

**Not done / open.** The free SC check (this container's network policy blocks Nexus; needs `nexus.quantinuum.com` allowed and a `NEXUS_REFRESH_TOKEN`). Q3 circuits (Phase 2). OVM/OLS cross-platform runs and the slow Steane/concatenated LE validations (no session reachable from here). The 4×5 Q1 lattice and the 50k allocation are the project lead's decisions.
