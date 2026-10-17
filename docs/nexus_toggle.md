# Running on Quantinuum H2 — the submission path (rewritten 2026-10-17, handoff/13)

**Status (2026-10-17): built and tested on the H2 local emulator; the free tiers have run on the live
Nexus platform.** Free SC: 18+ circuits accepted and quoted (`data/h2_sc_quotes*.txt`). Hosted noiseless
H2-1LE: upload → execute → fetch → decode proven on 8 real circuits, cost reported 0.0
(`data/h2_hosted_check.txt`). **Only the HQC tier (`submit_nexus` on H2-1E, with `max_cost` and the
noisy emulator) is untested live.** Nothing in this repo calls a spending function; that needs the
project lead's go, per run.

Every noisy number from the local emulator or Selene is a classical prediction under an ASSUMED noise
model. A number from Nexus H2-1E is an *H2 emulator* result and must be labelled so; real hardware, if
ever used, is a third label. Never mix them.

## How to switch the emulator on (the only step left once everything else is validated)

The run driver (`scripts/run_h2_nexus.py`, `src/h2_driver.py`) reads its tier from `config.py`
(`CONFIG.hardware.nexus_tier`: `"dry-run"` default, `"sc"`, `"hosted-le"`, `"emulator"`). To run a group
on **H2-1E** (this spends HQC, so only on the project lead's per-run go):

1. In `config.py`, `HardwareConfig`: `nexus_tier = "emulator"`, `allow_hardware = True`,
   `max_cost_hqc = <cap in HQC>` (the free SC quote of the group must fit under it), `nexus_project = "<name>"`.
2. Log in on this container: `qnx.auth.login()` (device code approved in the browser).
3. Run it with the per-run token, which a config edit alone can never replace:
   `.venv/bin/python -I scripts/run_h2_nexus.py --group bare-2x2-step1 --approval "I approve spending HQC on this run"`.
4. The driver builds and compiles the circuits, **re-quotes them on the free SC**, refuses if the quote is
   above the cap, and only then submits with `estimated_hqc` = the server quote. It also refuses a width
   above `emulator_max_qubits` (32), shots above `max_shots_per_job` (10,000) and a per-shot cost above
   `max_hqc_per_shot` (50) [established: docs.quantinuum.com "H2 Operation", 2026-10-17; the page does not
   say whether emulators share these limits, so they are applied to them]. Every job is recorded in
   `runs/nexus_ledger.jsonl`.
5. The CLI cannot select the emulator tier itself (`--tier` takes only `dry-run`, `sc`, `hosted-le`), and
   real hardware (H2-1/H2-2) is refused by this driver outright.

Recommended order, each step its own go: bare 2x2 step 1 (about 23 HQC) → G1 → compare with the local
emulator, Selene and Stim → Q1 (4x5) → Q4 → Q3.

## The tiers (what each costs, what gates it)

| tier | devices | cost | how | gate |
|---|---|---|---|---|
| LE | H2-1LE, H2-2LE | free, offline, no login | `src.h2_backend.run_le` | none; ≤ 30 qubits (host memory) |
| SC | H2-1SC, H2-2SC | free, unlimited | `src.h2_backend.syntax_check` | **pre-approved by the project lead**; refuses any other device name |
| hosted LE | H2-1LE on Nexus | no HQC (Simulation quota, seconds) | `src.h2_hosted.submit_hosted_le` + `check_hosted_cost` | refuses any non-LE device; ≤ 20 qubits; aborts if the server reports a cost. Proves the submit / fetch path on the real platform |
| E | H2-1E, H2-2E | **HQC** | `src.h2_backend.submit_nexus` | `allow_hardware=True` **and** the per-run approval token **and** `max_cost_hqc > 0` **and** estimate ≤ cap |
| HW | H2-1, H2-2 | **HQC** | same | all of the above **and** `allow_real_hardware=True` |

The Nexus usage page (2026-10-17) shows SC unlimited and **50,000 HQC on H2-1E/H2-2E**; it shows no
real-hardware allowance [established from the screenshot].

## What the emulators can run [established: docs.quantinuum.com, "System Model H2 Emulators" and "Quantinuum Emulators", read in full 2026-10-17]
- **H2-1E / H2-2E: 32 qubits state-vector, 56 stabilizer.** The stabilizer emulator is "for circuits
  involving only Clifford operations" (`QuantinuumConfig(simulator="stabilizer")`; cloud E emulators
  only). State vector is the default; Quantinuum recommends **fewer than 28 qubits** (slowdown from 25).
  So **non-Clifford circuits above 32 qubits cannot run on the emulator at all**. See DECISIONS.md
  OPEN-4 for what that does to the 6×6 arm and the 6×8 Q1 lattice.
- The Nexus-*hosted* emulators (H2-Emulator, and the noiseless `…LE` targets) are capped at 20 qubits
  per the text (26 per the table: QI-12), bill in seconds, not HQC, and are a different thing from the
  offline pecos "LE" this repo runs locally (QI-12).
- **The emulator's noise is not this repo's Pauli model.** H2-1E defaults (2025-07-16 table): p1 =
  1.89×10⁻⁵, p2 = 1.05×10⁻³, p_meas = 6×10⁻⁴ / 1.39×10⁻³ (0 / 1 outcome), p_init = 4×10⁻⁵, plus
  crosstalk, spontaneous emission / leakage, linear and (in state-vector mode) **coherent quadratic
  dephasing**, and a two-qubit error that is *asymmetric depolarizing* with an **angle-dependent**
  probability for arbitrary-angle ZZ gates (the `przz` scaling). H2-2E: p1 = 7.3×10⁻⁵,
  p2 = 1.29×10⁻³. These are Quantinuum's emulator model, not measurements of ours; the noise can be
  overridden with `error_params` or turned off with `noisy_simulation=False`. This is why randomized
  compiling matters on the emulator and why a Pauli-channel prediction from this repo is a different
  model, not a forecast [derived].
- The local emulator (H2-1LE) is an ideal state vector here (QI-2), limited by this host's memory.

## Why one pytket circuit, not the Guppy program
H2 is reached through `QuantinuumConfig` with pytket circuits / QIR, and pytket is "primarily used to
program System Model H2". The qnexus 0.51.1 HUGR client is typed for Helios only, and Quantinuum's
workflow page says Guppy has "limited backwards compatibility on System Model H2" and that Nexus does
not server-side-compile hugr (QI-3). So the Guppy program's in-program feedforward discard is not the
H2 route here [unverified whether H2 would accept it; the free SC can test]. `src/h2_circuits.py` authors the same programs as a single
circuit: syndrome bits measured **mid-circuit** into registers (measure + reset on ancilla and flag),
every shot run to the end, the discard applied afterwards by the same `accepted()` predicate. HQC is
charged on gate counts across ALL conditional branches regardless of which run [established: Quantinuum
workflow page], so skipping work after a detection would not have saved credits either. Randomized compiling (D-RC) is a classical
frame correction applied in `shot_records`, exactly as `backends_qc._local_shot_twirled`. The other
codes' round-0 feedforward is emitted as real conditional gates.

## Compilation: level 0, no_opt
TKET levels 1–2 cancel folded `ZZ(a)ZZ(-a)ZZ(a)` (QI-8, D-NS6). `compile_for_h2` compiles at level 0
and asserts the two-qubit count is unchanged; submissions carry `no_opt=True`. (This also records the
O-NS2 item from handoff/12: server-side optimisation off for folded jobs.)

## Cost before every run
`hqc_estimate` (offline, from compiled counts) and the SC quote (`syntax_check`, free) are both put on
the record before any HQC run: `runs/nexus_ledger.jsonl` (gitignored) keeps job id, device, shots,
estimate, cap and the approval token used. The full plan and per-run budget: `docs/h2_budget.md`.

## Login
Nexus needs a login. In a cloud session set a **refresh token** as the environment variable
`NEXUS_REFRESH_TOKEN` (never in the repo; it logs in for that process only), or run `qnx.login()`
once interactively on your own machine. The container's network policy must allow
`nexus.quantinuum.com` (and `docs.quantinuum.com` to read the docs).

## What was [unverified] and what the first free SC runs settled
- That Nexus accepts the circuits as authored (mid-circuit reset, conditional gates, `no_opt`).
- (Settled by the first free SC runs, 2026-10-17, `data/h2_sc_quotes.txt`: **Rz is not charged**. The
  Rz-free estimate equals the server quote exactly for 15 of 18 circuits and is within 0.5% for the
  3 with conditional gates, while counting Rz would be 15–20% high [measured]. The page itself does not
  say. The HQC formula and Nm convention are [established] from the docs.)
- The SC accepted every circuit as authored, including mid-circuit measure + reset and classically
  conditioned X/Y/Z gates [measured, 18 circuits]. That is a syntax check, not a run.
