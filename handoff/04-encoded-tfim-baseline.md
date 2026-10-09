# Handoff 04 — Classical encoded-TFIM baseline across QEC codes (logical side of Q1, emulator stage)

**Route to:** Claude Code (SCOPE §10/§14 — multi-file build on verified QEC primitives, no
single literature target for the composed circuit). **Agents cannot launch it; the user runs
it.** Written by qc-overseer.

## Where this sits in the project (full purpose vs current scope)
The project's full aim (Q-Net/Guppy-on-H2 application) is to test whether **encoding the TFIM
Trotter evolution into logical qubits extends the reachable evolution time** beyond the
bare-physical-qubit runs of Haghshenas et al. (arXiv:2503.20870), on square → frustrated
triangular → 3D lattices, eventually executed on H2 via **Nexus** with circuits in
**pytket/Guppy**. That hardware path is OUT of current scope and gated on Nexus access.

This brief builds the **classical, local** piece that the application calls emulator-stage
milestone (2) "understand the limits of the QEC codes" and milestone (3) "a full implementation
that can be toggled into H2 hardware." Concretely: the **logical side of Q1** as a classical
artifact — encoded square-TFIM Trotter circuits across the project's four QEC codes (Iceberg as
the reference build; Steane, 5-qubit, concatenated-d4 built-or-discarded), **authored in
pytket/Guppy and executed through a config-selected backend toggle**, each either verified with
a measured **discard rate, logical infidelity, and reachable Trotter depth** under a stated
noise model, or rejected with a quantitative argument.

**The toggle is the point (application milestone 3).** The SAME pytket/Guppy circuit objects run
on any backend chosen in config:
- `local-sim` — pytket local simulator (noiseless + configurable noise). Default; runs anywhere.
- `selene` — the Guppy program on the **Selene** local emulator, exercising real mid-circuit
  measurement + reset + classical feedforward/branching (the QEC syndrome + QED discard logic)
  WITHOUT hardware or Nexus.
- `nexus` — `QuantinuumBackend` via Nexus → H2 emulator / hardware. This backend is a
  clearly-marked STUB that raises `NotImplementedError` until credentials/credits exist; flipping
  the toggle to it later is a config change, not a rewrite.
This was verified installable+importable on this venv (py3.12): `pytket==2.18.4`,
`guppylang==1.1.2`, `selene-sim==0.3.4`, `hugr==0.18.8` (add pinned to `requirements.txt`).

## Why this is the right next piece (and not invented)
- The repo already compares our **bare** classical sim to the **physical** H2 data (Q1 harness,
  `src/compare.py`, reviewed in `review/07`). The reviewer correctly noted that does NOT yet
  satisfy SCOPE Q1, because **there is no logical/encoded side**. This brief adds it.
- The Iceberg [[k+2,k,2]] code and the concatenated-d=4 construction are BUILT and VERIFIED
  here: `src/qec/iceberg.py` (`IcebergCode`, stabilizers `S_X,S_Z`, logicals
  `Xbar_i=X_tX_i`, `Zbar_i=Z_bZ_i`), `src/qec/verify.py:verify_code`,
  `src/qec/concatenated.py` (`min_undetected_weight`, `code_distance`, interleaving),
  `src/qec/syndrome.py` (two-round Stim syndrome extraction). What is NOT built is the
  **composition**: encoding the TFIM Trotter *logical gates* (the `rzz`/`rx` layers from the
  Q1 physics) into these code blocks and running the whole thing under noise. That composition
  is the deliverable.
- **Division of labor (keep both tools, do not conflate):** **Stim VERIFIES** — stabilizer
  fault injection proves detection distance and fault-tolerance (this is how correctness is
  established; it stays). **pytket/Guppy EXECUTE** — they are the authored, runnable circuits
  that produce the noisy discard/`Z2` curves and that later submit to H2. A pytket/Guppy local
  sim is state-based execution, NOT an FT proof; it does not replace Stim. The encoded circuit
  therefore exists in two linked forms: a Stim representation for verification and a pytket/Guppy
  representation for execution, and the brief must check they agree (same clean-run logical
  action — see Done-check).

## Goal
Establish, with correctness arguments and Stim verification, the **encoding → compose-Trotter →
verify → noisy-assess** pipeline for the TFIM, and apply it across the project's four QEC codes.
**Iceberg is the REFERENCE implementation** (its primitives are already verified, so it proves
the method); the other three codes each get either a working implementation of the same pipeline
**or** an explicit discard backed by a strong theoretical argument. The codes will permeate the
whole project, so this brief either makes each one work or kills it with evidence now.

### Part A — Iceberg [[k+2,k,2]] reference implementation (full build, no discard option)
1. An **encoded square-TFIM Trotter circuit authored in pytket**, with the mid-circuit syndrome
   measurement + reset + classical feedforward/discard expressed in **Guppy** (run on Selene):
   the logical operations implementing one 2nd-order Trotter step (`exp(-iθ Zbar_iZbar_j)` on
   logical bonds, `exp(-iφ Xbar_i)` logical field rotations) on the physical register, with the
   QED discard (post-selection) rule at the cadence you justify.
2. **Verification = Stim; execution = pytket/Guppy.** A **Stim circuit-level verification**:
   clean run silent (no detector fires, nothing discarded); every weight-1 physical fault
   detected; and for the COMPOSED Trotter step, one physical fault cannot produce an undetected
   logical error (Stim-measured by error injection — NOT inherited from the bare code's
   distance). Plus a **consistency check** that the pytket/Guppy circuit and the Stim circuit
   implement the same clean-run logical action (e.g. identical logical `Z2` at zero noise).
3. A **noisy-sim measurement** run through the backend toggle (`local-sim` and/or `selene`)
   under a stated parameterized depolarizing model (per-2q-gate, per-measurement, per-idle as
   defined): the **discard/post-selection rate** and the logical observable
   (`Z2 = <(ΣZ)²>/N²`, same as the Q1 harness) on post-selected logical outcomes, vs Trotter
   step, for a small logical lattice within ceilings.
4. A written **limits assessment** (the application's open risks): at what noise rate / Trotter
   depth does the discard rate make the encoded run inefficient, and does encoded `Z2(step)`
   track the ideal longer than the bare run at matched physical noise — the yes/no-and-where of
   "does encoding buy reachable time," skeptically framed (SCOPE §3).

### Part B — Steane [[7,1,3]], 5-qubit [[5,1,3]], concatenated Iceberg d=4 (build-or-discard)
For EACH of these three codes, produce ONE of:
- **(build)** the same four artifacts as Part A (encoded Trotter step + Stim FT verification +
  noisy discard/`Z2` curve + limits paragraph), reusing the Part-A pipeline; OR
- **(discard)** a written, evidence-backed rejection: a `code_distance`/budget/logical-gate-cost
  argument showing why this code cannot carry the TFIM Trotter evolution usefully at H2 scale
  (≈55 physical qubits, partial-FT + post-selection, no magic-state distillation). The discard
  MUST be quantitative, not hand-waved (see "Per-code guidance").

The decision (build vs discard) is itself a deliverable: state it explicitly per code with the
reason. A code is only discarded if the argument is strong; "harder to implement" is not enough.

### Per-code guidance (what makes each viable or not — verify, don't assume)
- **Iceberg [[k+2,k,2]]** — CSS, primitives verified in repo; MUST build (Part A).
- **Steane [[7,1,3]]** — CSS, distance 3 (corrects 1 error). Repo marks it "on-paper path"
  (`src/qec/__init__.py`, `src/qec/on_paper_codes.py`): its Stim-level code definition likely
  needs building first. Viability hinges on the logical `rzz`/`rx` TFIM gates: transversal
  Clifford is available; the non-Clifford `rzz(θ)`/`rx(φ)` rotations are the crux — state how
  they are realized (e.g. small-angle synthesis / post-selected gadget) or why that is
  prohibitive. 7 data + ancillas per logical qubit drives the budget argument for a non-trivial
  lattice.
- **5-qubit [[5,1,3]]** — NON-CSS perfect code, distance 3. Build its Stim definition, then the
  honest crux: its logical gate set is awkward (no clean transversal non-Clifford; even Clifford
  logicals are costlier than CSS). This is the most likely **discard** candidate — if so, the
  argument is "clean d=3 but the logical TFIM step cost / lack of a cheap `rzz(θ)` makes it
  non-viable under partial-FT+post-selection at this scale," shown with the explicit gate
  construction cost, not asserted.
- **Concatenated Iceberg d=4** — construction already in `src/qec/concatenated.py` (verified
  `code_distance == 4`). The crux is **qubit budget**: a d=4 block is ≈ (k+2)² physical qubits
  before syndrome ancillas. Compute the physical-qubit cost for the smallest non-trivial logical
  lattice and compare to the ~55-qubit ceiling; that budget number largely decides build vs
  discard. If buildable within ceilings for a tiny lattice, build; else discard with the budget
  table.

## Scope decisions already made (do not reopen without asking)
- **Codes: all four** — Iceberg [[k+2,k,2]] (reference build), Steane [[7,1,3]], 5-qubit
  [[5,1,3]], concatenated Iceberg d=4 — each either built on the Part-A pipeline or discarded
  with a quantitative argument (see Goal Part B). Build Iceberg FIRST and get it reviewed-quality
  before replicating the pattern, so a bad pattern is not copied across codes.
- **Noise model: generic parameterized depolarizing** (circuit-level, Stim). Do NOT fit a
  hardware-faithful H2 model — that is gated on real device calibration (Nexus era) and would
  overclaim now (SCOPE §3). Expose the rates as config so a future calibrated model drops in.
- **Observable: `Z2` second moment** (matches the Q1 harness exactly) for the first logical
  curve on every code. Other observables are later.
- **Lattice: small, within SCOPE §5 ceilings.** The encoded register is larger than the logical
  lattice (n_phys per logical qubit: Iceberg k+2 amortized, Steane 7, 5-qubit 5, concat ≈(k+2)²,
  plus syndrome ancillas); the **physical** qubit count drives the Stim/statevector cost and the
  ceiling check, not the logical count. This is also the core of the per-code budget argument.

## Inputs (already in repo)
- QEC primitives (consume, do not reinvent): `src/qec/iceberg.py`, `src/qec/verify.py`,
  `src/qec/syndrome.py`, `src/qec/concatenated.py` (`code_distance`), and
  `src/qec/on_paper_codes.py` (the Stim-level starting point for Steane / 5-qubit — extend as
  needed). Stim 1.16.0 in `.venv`.
- Physics + observable: `src/compare.py` (the circuit-order Strang step, `total_z_sq_normalized`,
  the (J,h,dt,θ) convention — J·dt=0.25, h·dt=0.5, h/|J|=2, θ per quench), `src/observables.py`,
  `src/lattice.py` (`square_bonds`), `src/trotter.py`.
- Specs: `research/05-zenodo-dataset-map.md` (frozen data spec), `research/01-stage1-conventions.md`
  (Hamiltonian/Trotter/observable conventions), `review/07-q1-comparison-harness.md` (what the
  Q1 harness already does and its honesty constraints — mirror them).
- `config.py` (`CompareConfig`, `CeilingConfig`) — add an encoded-run config block in the same style.

## Constraints
- **No Nexus, no hardware.** pytket, Guppy, and the Selene emulator ARE in scope (all local).
  Only the `nexus` backend is stubbed (see Backend toggle).
- **New pinned dependencies** added to `requirements.txt`: `pytket==2.18.4`, `guppylang==1.1.2`,
  `selene-sim==0.3.4`, `hugr==0.18.8` (verified installable+importable on this py3.12 venv). Keep
  Stim (`1.16.0`) — it remains the verification oracle.
- **Stim stays the FT verifier.** Do not try to prove fault-tolerance with pytket/Guppy state
  sims; use Stim fault injection for distance/FT claims and pytket/Guppy for execution.
- Refuse over-ceiling **physical** register sizes BEFORE allocating (reuse the Q1 harness's
  `check_ceiling` pattern against `CeilingConfig`); the physical count includes code + syndrome
  ancilla qubits.
- No invented numbers/citations; status-tag everything (established/inferred/unverified). The
  noise rates are declared assumptions, not measurements; say so in every output.
- Match the existing code style, the row-major/MSB index convention, and the Q1 harness's
  honesty discipline: a `local-sim`/`selene` noisy curve is a **classical prediction under a
  stated noise model**, never an H2 hardware result.
- Do not modify the verified QEC primitives or the Q1 harness beyond additive composition
  (new modules, e.g. `src/encoded_tfim.py`, `src/backends_qc.py` for the toggle,
  `scripts/run_encoded.py` + tests).

## Backend toggle (build the seam; only Nexus is stubbed)
The application's milestone (3) is a "full implementation that can be toggled into H2 hardware."
Build a thin executor interface, e.g. `run(circuit, shots, noise, backend) -> results`, selected
by a config field, with THREE backends:
- `local-sim` — pytket local simulator (noiseless + configurable noise). **Implemented.** Default.
- `selene` — the Guppy program on the Selene emulator, exercising mid-circuit measurement +
  reset + classical feedforward/discard. **Implemented.** This is the honest local proxy for the
  dynamic-circuit behavior H2 will run.
- `nexus` — `QuantinuumBackend` via Nexus (H2 emulator / hardware). **STUB ONLY**: raises
  `NotImplementedError("Nexus backend: requires Quantinuum credentials/credits; flip toggle when access is granted")`.
  Do NOT implement submission/auth against an API we have no access to; the point is that the
  toggle *exists* and the circuit objects are already Nexus-ready.
- Add a one-paragraph `docs/` note stating exactly what flipping to `nexus` will require
  (pytket-quantinuum backend construction, Nexus project/auth, H2 emulator vs hardware target,
  HQC budget) so the future switch is documented, not rediscovered.

## Done-check
- **Iceberg (Part A):** `verify_code` still passes for the block; the COMPOSED encoded Trotter
  step passes a Stim fault-injection check (clean run silent; every weight-1 physical fault
  detected; no single-fault undetected logical error at the step level). The pytket/Guppy
  circuit agrees with the Stim circuit on the clean-run logical action (same zero-noise logical
  `Z2`). A run script emits encoded `Z2(step)` on post-selected logical outcomes + discard rate
  per step through the backend toggle (`local-sim` and `selene` both runnable; `nexus` raises
  `NotImplementedError`), under a configurable noise rate, refusing over-ceiling physical sizes.
  Encoded `Z2` at **zero noise** equals the bare logical-equivalent `simulate_z2` curve
  (encoding transparency). The Guppy/Selene path actually exercises mid-circuit measurement +
  feedforward/discard (not a measurement-free stand-in). A written limits paragraph answers the
  three application risks.
- **Steane, 5-qubit, concatenated-d4 (Part B):** for each, EITHER the same artifacts as Iceberg
  (incl. the zero-noise transparency check, the pytket/Guppy↔Stim consistency check, and a
  `verify_code`-level algebra check on its stabilizers/logicals), OR a written discard with a
  quantitative argument — a physical-qubit **budget table** for the smallest non-trivial logical
  lattice vs the ~55-qubit ceiling, and/or the explicit logical `rzz(θ)`/`rx(φ)` gate
  construction cost showing non-viability. The build/discard decision is stated per code.
- Tests green; existing QEC and compare tests still pass unchanged. `requirements.txt` updated
  with the pinned pytket/guppylang/selene-sim/hugr versions. The `nexus` backend is a documented
  stub.

## What the reviewer must verify
- **Per built code:** that the encoded Trotter step is the correct logical operation (zero-noise
  encoded `Z2` equals the unencoded logical `Z2` — encoding transparency), that the
  fault-tolerance claim is Stim-MEASURED by error injection on the composed circuit (not
  inherited from the bare code's distance), that stabilizer/logical algebra passes a
  `verify_code`-style check, and that the discard rate and logical infidelity come from a STATED
  noise model with rates surfaced as assumptions.
- **Per discarded code:** that the rejection is quantitative and strong — a real budget table or
  explicit logical-gate-cost construction — not "harder to implement." A weak discard must be
  sent back.
- **Across all:** that no `local-sim`/`selene` noisy curve is presented as an H2 hardware
  result; that the backend toggle works (`local-sim` + `selene` run, `nexus` raises
  `NotImplementedError`); that the Guppy/Selene path genuinely exercises mid-circuit measurement
  + feedforward/discard rather than faking it; and that the pytket/Guppy circuit agrees with the
  Stim verification circuit on the clean-run logical action. Default skeptical prior: "encoding
  may not buy reachable time at these noise rates, and some of these codes may not be viable at
  all" — the deliverable must show, with evidence, where each code works and where it does not.
