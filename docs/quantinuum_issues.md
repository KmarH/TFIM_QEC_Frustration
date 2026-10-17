# Quantinuum software: issues, quirks and surprises found while building this project

**Why this file exists.** The project lead has Nexus access both to run this project and to help
troubleshoot Quantinuum's software. So every problem, surprise or undocumented behaviour we hit in
the Quantinuum stack (pytket-quantinuum, qnexus, pytket-pecos / the local emulator, Guppy / Selene,
TKET compilation) is logged here, whether or not it blocks us, in a form that can be sent upstream.
**Standing rule (CLAUDE.md): add an entry the moment a new one is found.** A bug report needs a
reproduction; where we have only read source, the entry says so.

Status tags: [measured] ran it · [established] read from the library's own source or docs ·
[inferred] · [unverified]. "Upstream" = reported to Quantinuum: `no` until the project lead sends it.

Versions in play (requirements.txt / requirements-le.txt): pytket 2.18.4, pytket-quantinuum 0.59.3,
qnexus 0.51.1, quantum-pecos 0.8.0.dev8, pytket-pecos 0.3.3, selene-sim 0.3.4 (main) / 0.2.18 (LE),
guppylang 1.1.2, hugr 0.18.8.

| id | kind | one line | upstream | status |
|---|---|---|---|---|
| QI-1 | install conflict | `pytket-quantinuum[pecos]` cannot co-install with selene-sim 0.3.x | no | worked around (2 venvs) |
| QI-2 | behaviour vs docs | the local emulator ignores `noisy_simulation` and is always noiseless | no | worked around |
| QI-3 | scope | qnexus HUGR client is Helios-typed; docs say H2 support is "limited" | no | design consequence, untested on H2 |
| QI-4 | deprecation | `hugr.cost()` deprecated for `cost_confidence()` | no | note |
| QI-5 | bug (source) | `circuits.cost` builds `"H2-1ESC"` from an E config (`strip` result discarded) | no | worked around |
| QI-6 | limitation | Selene's HUGR-QIS compiler rejects pytket `XXPhase` | no | worked around |
| QI-7 | behaviour | Selene's depolarizing model charges `p_1q` on every native rxy and rz | no | accounted |
| QI-8 | trap | TKET optimisation levels 1–2 cancel folded `ZZ(a)ZZ(-a)ZZ(a)` | no | worked around |
| QI-9 | convention | PECOS depolarizing parameters are *average* error, scaled ×3/2 (1q) and ×5/4 (2q), and charged per compiled *native* op | no | accounted |
| QI-10 | known upstream | pytket→PHIR drops classical bits no command touches | yes (cited in source) | worked around by them |
| QI-11 | behaviour | PECOS charges `p_init` only on explicit Init ops, not on the initial state | no | worked around |
| QI-13 | deprecation | latest qnexus warns an endpoint "will be deleted on 30 Nov 2025", a date already past; it still works | no | note |
| QI-14 | API/naming | `start_execute_job` takes uploaded refs; raw pytket circuits crash with `AttributeError: ... 'id'` despite the `accept_circuits_for_programs` decorator | no | worked around |
| QI-12 | docs | emulator pages disagree on the Nexus-hosted H2-Emulator width (26 vs 20); "LE" names two different things | no | note |

---

## QI-1 — `pytket-quantinuum[pecos]` conflicts with selene-sim 0.3.x
- **Component:** pytket-quantinuum 0.59.3 `[pecos]` extra → quantum-pecos 0.8.0.dev8.
- **Symptom [measured, 2026-10-17]:** `pip install -r requirements.txt "pytket-quantinuum[pecos]==0.59.3"`
  → `ResolutionImpossible`: *quantum-pecos 0.8.0.dev8 depends on selene-sim~=0.2.0* while this project's
  Guppy/Selene results (`data/selene_gap.txt`, `data/encoded_*.txt`) were produced and validated on
  `selene-sim==0.3.4`, so that pin is not moved to suit pecos [we did not test whether 0.2.x would also
  run them].
- **Reproduce:** fresh Python 3.12 venv; `pip install selene-sim==0.3.4 "pytket-quantinuum[pecos]==0.59.3"`.
- **Impact:** the H2 local emulator (H2-1LE / H2-2LE) cannot live in the same environment as the Selene
  runs. **Workaround:** a second environment, `requirements-le.txt` → `.venv-le`, used only for LE runs
  and the LE tests. The main environment is untouched.
- **Ask upstream:** relax or bump the pecos→selene pin, or document that the two stacks need separate
  environments.

## QI-2 — The local emulator ignores `noisy_simulation` and is always noiseless
- **Component:** pytket-quantinuum 0.59.3, `QuantinuumBackend("H2-1LE")` / `("H2-2LE")` with pytket-pecos.
- **Docs say [established]:** `noisy_simulation` — "boolean flag to specify whether the simulator should
  perform noisy simulation with an error model (default value is `True`)."
- **What happens [measured]:** 100 pairs of CX (identity) on H2-1LE returned 500/500 ideal outcomes with
  the default *and* with `noisy_simulation=False`. **[established, source]:** the LE branch builds
  `pytket_pecos.Emulator(circ, wasm=…, qsim="state-vector", seed=…)` with **no `error_model`**; the flag
  is stored in `_LocalEmulatorConfiguration` and never used. `qsim` is also hard-coded, so the stabilizer
  engine cannot be selected through the backend.
- **Impact:** an "H2 emulator" run done locally is silently an *ideal* state-vector run. A user who
  expects the documented default noise would draw wrong conclusions. **Workaround:**
  `src/h2_backend.run_le(noise=…)` drives the same `Emulator` with a PECOS `DepolarizingErrorModel`
  (see QI-9 for the parameter convention). Whether the *Nexus* H2-1E emulator applies the real H2 error
  model is separate and [unverified].
- **Also seen:** `quantum-pecos 0.8.0.dev8 does not provide the extra 'wasmtime'` warning on install of
  the `[pecos]` extra (cosmetic).

## QI-3 — Guppy/HUGR is typed for Helios in qnexus 0.51.1; the docs call H2 support "limited"
- **Component:** qnexus 0.51.1 (`qnexus.hugr`, `qnexus.models.HeliosConfig`); Quantinuum workflow page.
- **Observation [established, source and docs]:** `hugr.cost()` / `cost_confidence()` take
  `system_name: Literal["Helios-1", "Helios-2"]` and submit with `HeliosConfig`; the upload docstring
  says "HUGR support in Nexus is subject to change. Until full support is achieved any programs uploaded
  may not work in the future." The docs' workflow page says Guppy "is primarily designed for execution
  on Quantinuum Helios, but also has limited backwards compatibility on System Model H2", that pytket is
  "primarily used to program System Model H2", and that "Nexus does not support server-side tket
  compilation of hugr programs". H2 devices are reached through `QuantinuumConfig(device_name="H2-…")`.
- **Impact:** open item HW-3 is *not* a clean "no": the client is Helios-typed and the docs promise only
  limited H2 compatibility. The H2 path here is one pytket circuit with mid-circuit measure/reset and
  the discard applied afterwards (`src/h2_circuits.py`); for H2 the HQC is charged on all conditional
  branches regardless, so in-program discard saves no credits anyway. The in-program feedforward is not
  tested on H2.
- **[unverified]:** whether Nexus accepts our hugr for an H2 target. The free syntax checker can test it.
- **Ask upstream:** what "limited backwards compatibility" covers, and a typed H2 route in qnexus.

## QI-4 — `qnexus.hugr.cost()` is deprecated
- `hugr.cost()` emits a `DeprecationWarning` pointing to `cost_confidence()` [established, source].
  Note only; we do not use the HUGR route for H2.

## QI-5 — `qnexus.circuits.cost` builds a wrong device name from an E config
- **Component:** qnexus 0.51.1, `client/circuits.py::cost`.
- **Code [established]:**
  ```python
  if not syntax_checker_device_name.endswith("SC"):
      syntax_checker_device_name.strip("E")   # result discarded: str.strip returns a new string
      syntax_checker_device_name += "SC"
  ```
  The comment says costing for `H2-xE` is the same as for `H2-x`, so the intent is `H2-1E` → `H2-1SC`.
  As written, `H2-1E` → **`H2-1ESC`**, and `H2-1` → `H2-1SC` (correct only by accident).
- **Reproduce:** call `qnx.circuits.cost(ref, n_shots, QuantinuumConfig(device_name="H2-1E"))` with no
  `syntax_checker` [not run: needs a login; found by reading the source].
- **Workaround:** `syntax_check()` always passes `syntax_checker=<an SC name>` explicitly.
- **Fix:** `syntax_checker_device_name = syntax_checker_device_name.rstrip("E") + "SC"`
  (and handle names that already end in `SC`).

## QI-6 — Selene's HUGR-QIS compiler rejects pytket `XXPhase`
- [measured, earlier in this project] XX rotations must be authored as `H·ZZPhase·H` for Selene.
  `ZZPhase` is also H2's native entangler. `src/encoded_tfim.py::_pp` does this.

## QI-7 — Selene's depolarizing model charges `p_1q` on every native rxy *and* rz
- [measured, `data/selene_gap.txt`] About ×3.85 more one-qubit error exposure than pytket-level gate
  counts suggest, plus `p_init` on allocations. It lowers Selene's acceptance versus our Stim model.
  Whether a physical H2 charges its virtual rz is open item HW-4 [unverified].

## QI-8 — TKET optimisation levels 1–2 silently cancel folded gates
- [measured, offline H2-1 compile, `research/derivations/01`] `ZZ(a)ZZ(-a)ZZ(a)` becomes one gate at
  levels 1 and 2 (2 is the Quantinuum default): the 2-qubit count was 27/27 instead of 27/81, so the
  λ = 3 fold would silently run as λ = 1. **Workaround:** compile at level 0 and submit `no_opt=True`;
  `src/h2_circuits.compile_for_h2` asserts the two-qubit count is unchanged. A server-side
  optimisation pass is *not* visible to the client, so Nexus acceptance of `no_opt` is [unverified].

## QI-9 — PECOS depolarizing parameters are average error, rescaled internally
- **Component:** quantum-pecos 0.8.0.dev8, `DepolarizingErrorModel._scale`.
- **[established, source]:** `p1 *= 3/2` and `p2 *= 5/4` ("conversion from average error to total error").
  A user passing "the probability of a Pauli error after each gate" gets 1.5× / 1.25× more error.
- **Handling:** `src/h2_backend.pecos_error_params` pre-divides (p1·2/3, p2·4/5) so the per-gate
  error probability equals this project's `Noise`; checked numerically in `tests/test_h2_backend.py`.
- **Native-gate charging [measured, review A, 2026-10-17]:** the model charges `p1` on every
  *compiled native* one-qubit op, R1XY (PhasedX) and **Rz** alike. A twirled 2-site Iceberg circuit
  compiles to 272 native one-qubit ops (141 PhasedX + 131 Rz) against 52 authored H gates; at
  p1 = 0.002 the noisy LE accepted 0.381 vs local-sim's 0.804. So `Noise.p1` means "per native op"
  on the LE and "per authored H" in local-sim, and **randomized compiling is not a no-op on the noisy
  LE** (twirl Paulis are real native ops). p2 agrees because each CX compiles to exactly one ZZPhase
  [measured: acceptance 0.391 vs 0.377 at p2 = 0.01]. Whether real H2 charges its virtual Rz is open
  item HW-4 [unverified].

## QI-10 — pytket→PHIR drops unused classical bits
- Cited in pytket-quantinuum's own source as `Quantinuum/pytket-quantinuum#473` [established, source
  comment]; they add redundant `SetBits` as a workaround on their LE path. `run_le`'s noisy path
  (which builds the Emulator itself) repeats that workaround.

## QI-11 — PECOS does not charge `p_init` on the initial state
- **Component:** quantum-pecos 0.8.0.dev8, `DepolarizingErrorModel.process`.
- **[established, source; measured, review A]:** the bit-flip after initialisation is applied only to
  explicit `Init` ops (`op.name in {"init |0>", "Init", "Init +Z"}`), i.e. mid-circuit `Reset`s. A
  one-qubit test with `p_init = 0.5` gave a flip rate of 0.00 on the initial state and 0.49 after a
  Reset. The initial allocation of a circuit is therefore noiseless.
- **Impact:** local-sim and Selene charge initialisation, so at p_init = 0.02 the LE accepted 0.749 vs
  local-sim's 0.626 (ratio 0.851 = 0.98^8, the 8 initial qubits).
- **Workaround:** `src/h2_backend.run_le` prepends an explicit Reset on every qubit when
  `noise.p_init > 0` (`tests/test_h2_review_fixes.py`).
- **Ask upstream:** document it, or charge the initial allocation.

## QI-12 — Emulator documentation inconsistencies
- **Component:** docs.quantinuum.com, "Quantinuum Emulators" (H2 training page), read 2026-10-17.
- **Observation [established, docs]:** its table lists the Nexus-hosted `H2-Emulator` at **26** qubits
  (state-vector and stabilizer) in seconds, while the same page's text says "Nexus-hosted emulators are
  capped at 20-qubits" and "The Emulator targets with suffix Emulator or LE are hosted on nexus, but
  with the total number of qubits capped at 20-qubits". The same page also states the noise-free `…LE`
  targets are *hosted in Nexus*, whereas the `H2-1LE` that `pytket-quantinuum[pecos]` runs is a
  separate **offline** emulator on the user's machine (QI-2); both are called "LE".
- **Impact:** none on the plan (we use the cloud E emulators, 32 qubits, and the offline LE); it could
  mislead anyone choosing a target by width. **Ask upstream:** reconcile 26 vs 20, and name the offline
  and hosted noiseless emulators differently.

## QI-13 — qnexus 0.51.1 warns about an endpoint deletion date that has already passed
- **Component:** qnexus 0.51.1 (the latest on PyPI on 2026-10-17), `qnexus.quotas`.
- **Observation [measured, 2026-10-17]:** `qnx.quotas.get_all()` emits `DeprecationWarning: Your version
  of qnexus is using a deprecated API endpoint (/api/quotas/v1beta) that will be deleted on Sun, 30 Nov
  2025 ... After this date your current qnexus version may stop functioning. Please update to a later
  qnexus version`. Today is after that date, no newer qnexus exists on PyPI, and the call still works.
- **Impact:** none seen; the warning is misleading for the latest release. **Ask upstream:** update the
  endpoint or the warning text.

## QI-14 — `start_execute_job(programs=[Circuit])` crashes; the "accept circuits" decorator only renames a keyword
- **Component:** qnexus 0.51.1, `client/jobs/_execute.py::start_execute_job`, `client/utils.py::accept_circuits_for_programs`.
- **Observation [measured, 2026-10-17, free hosted H2-1LE]:** passing a raw pytket `Circuit` as `programs` raises
  `AttributeError: 'pytket._tket.circuit.Circuit' object has no attribute 'id'` (the function reads `p.id`
  for each program) before any job is created. The decorator `accept_circuits_for_programs`, despite its
  name, only maps the deprecated keyword `circuits=` to `programs=`; it does not upload.
- **Reproduce:** `qnx.start_execute_job(programs=[Circuit(1)...], n_shots=[5],
  backend_config=QuantinuumConfig(device_name="H2-1LE"), project=proj, name="x")`.
- **Impact:** the first version of `submit_nexus` passed raw circuits and would have failed at its first
  live call (found in review, reproduced here). **Workaround:** upload each circuit with
  `qnx.circuits.upload` and pass the returned `CircuitRef`s (`src/h2_backend._upload_circuits`).
- **Ask upstream:** upload raw circuits inside `start_execute_job` as the decorator's name suggests, or
  raise a clear `TypeError`; the signature type hint (`ExecutionProgram`) is right but the error is not.

---

## Template for new entries

```
## QI-n — one-line title
- **Component:** package + version
- **Symptom / observation [tag, date]:**
- **Reproduce:** minimal commands or code
- **Impact on this project:**
- **Workaround:**
- **Ask upstream:**
- **Upstream:** no / reported (link)   **Status:** open / worked around / fixed in <version>
```
