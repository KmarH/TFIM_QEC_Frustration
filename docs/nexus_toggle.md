# Running on Quantinuum H2 — the submission path (rewritten 2026-10-17, handoff/13)

**Status: built and tested against the H2 *local* emulator; the Nexus tiers are written and unit-tested
with a mocked client but have never been called against the live server.** Nothing in this repo calls
a spending function; that needs the project lead's go, per run.

Every noisy number from the local emulator or Selene is a classical prediction under an ASSUMED noise
model. A number from Nexus H2-1E is an *H2 emulator* result and must be labelled so; real hardware, if
ever used, is a third label. Never mix them.

## The tiers (what each costs, what gates it)

| tier | devices | cost | how | gate |
|---|---|---|---|---|
| LE | H2-1LE, H2-2LE | free, offline, no login | `src.h2_backend.run_le` | none; ≤ 30 qubits (host memory) |
| SC | H2-1SC, H2-2SC | free, unlimited | `src.h2_backend.syntax_check` | **pre-approved by the project lead**; refuses any other device name |
| E | H2-1E, H2-2E | **HQC** | `src.h2_backend.submit_nexus` | `allow_hardware=True` **and** the per-run approval token **and** `max_cost_hqc > 0` **and** estimate ≤ cap |
| HW | H2-1, H2-2 | **HQC** | same | all of the above **and** `allow_real_hardware=True` |

The Nexus usage page (2026-10-17) shows SC unlimited and **50,000 HQC on H2-1E/H2-2E**; it shows no
real-hardware allowance [established from the screenshot].

## What the emulators can run [from Quantinuum's docs, via search excerpts; re-read the page]
- **H2-1E / H2-2E: 32 qubits state-vector, 56 stabilizer (Clifford only)**; state-vector runs below 28
  qubits are recommended. So **non-Clifford circuits above 32 qubits cannot run on the emulator at
  all**. See DECISIONS.md OPEN-4 for what that does to the 6×6 arm and the 6×8 Q1 lattice.
- The local emulator (H2-1LE) is an ideal state vector here (QI-2), limited by this host's memory.

## Why one pytket circuit, not the Guppy program
H2 is reached through `QuantinuumConfig` with pytket circuits / QIR. Nexus's Guppy/HUGR route is
**Helios-only** in qnexus 0.51.1 (`docs/quantinuum_issues.md` QI-3), so the Guppy program's in-program
feedforward discard does not run on H2. `src/h2_circuits.py` authors the same programs as a single
circuit: syndrome bits measured **mid-circuit** into registers (measure + reset on ancilla and flag),
every shot run to the end, the discard applied afterwards by the same `accepted()` predicate. HQC is
charged on static gate counts, so nothing is lost on cost. Randomized compiling (D-RC) is a classical
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

## What is still [unverified] (to be settled by the first SC run, then logged in quantinuum_issues.md)
- That Nexus accepts the circuits as authored (mid-circuit reset, conditional gates, `no_opt`).
- Whether Rz counts toward HQC on H2 (the estimate counts it, conservatively), and the exact emulator
  charge (the estimate is the standard formula, not an emulator-specific one).
- The H2-1E width limits above, and its default noise model (the docs excerpt lists p2 = 0.00128,
  p1 = 2.9×10⁻⁵ [unverified]).
