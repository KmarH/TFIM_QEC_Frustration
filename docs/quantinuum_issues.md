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
| QI-3 | scope | Nexus HUGR/Guppy is Helios-only in qnexus 0.51.1; H2 takes pytket/QIR | no | design consequence |
| QI-4 | deprecation | `hugr.cost()` deprecated for `cost_confidence()` | no | note |
| QI-5 | bug (source) | `circuits.cost` builds `"H2-1ESC"` from an E config (`strip` result discarded) | no | worked around |
| QI-6 | limitation | Selene's HUGR-QIS compiler rejects pytket `XXPhase` | no | worked around |
| QI-7 | behaviour | Selene's depolarizing model charges `p_1q` on every native rxy and rz | no | accounted |
| QI-8 | trap | TKET optimisation levels 1–2 cancel folded `ZZ(a)ZZ(-a)ZZ(a)` | no | worked around |
| QI-9 | convention | PECOS depolarizing parameters are *average* error, scaled ×3/2 (1q) and ×5/4 (2q) | no | accounted |
| QI-10 | known upstream | pytket→PHIR drops classical bits no command touches | yes (cited in source) | worked around by them |

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

## QI-3 — Guppy/HUGR programs run on Helios, not H2, in qnexus 0.51.1
- **Component:** qnexus 0.51.1 (`qnexus.hugr`, `qnexus.models.HeliosConfig`).
- **Observation [established, source]:** `hugr.cost()` / `cost_confidence()` take
  `system_name: Literal["Helios-1", "Helios-2"]` and submit with `HeliosConfig`; the HUGR upload docstring
  says "HUGR support in Nexus is subject to change. Until full support is achieved any programs uploaded
  may not work in the future." H2 devices are reached through `QuantinuumConfig(device_name="H2-…")`,
  which takes pytket circuits / QIR.
- **Impact:** answers open item HW-3 in the direction "no": our Guppy program (mid-circuit measure,
  reset, *feedforward discard*) cannot be the H2 submission. The H2 path is one pytket circuit with
  mid-circuit measure/reset and the discard applied classically afterwards (`src/h2_circuits.py`). HQC is
  charged on gate counts, so nothing is lost on cost. The in-program feedforward is not tested on H2.
- **[unverified]:** that Nexus really rejects HUGR for an H2 target; only the client source was read.
  The free syntax checker can confirm.

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

## QI-10 — pytket→PHIR drops unused classical bits
- Cited in pytket-quantinuum's own source as `Quantinuum/pytket-quantinuum#473` [established, source
  comment]; they add redundant `SetBits` as a workaround on their LE path. `run_le`'s noisy path
  (which builds the Emulator itself) repeats that workaround.

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
