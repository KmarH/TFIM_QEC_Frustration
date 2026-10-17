# CLAUDE.md — working rules for Claude Code in this project

TFIM simulation with logical (encoded) vs physical qubits, aimed at Quantinuum H2 (a team project). Claude Code is one agent in a multi-agent workflow. **Kiro** (qc-overseer, qc-researcher, qc-reviewer, qc-annotator, qc-scout) scopes, researches and reviews, and writes briefs for Claude Code in `handoff/NN-*.md`. The project lead runs Claude Code on those briefs and relays messages between the two.

## Read first, every session
1. `SCOPE.md`: the contract. §5 backends/ceilings, §10 what Claude Code does, §12 hard rules, §14 autonomy.
2. `Conversation history/project-journal.md`: start with the **★ ARTICLE THESIS box** (the governing framing), then the status board and the latest entries.
3. `Conversation history/open-questions.md`: pending decisions and questions.
4. `handoff/plan.md` (the registry) and the brief you were given.

## Hard rules (non-negotiable)
- **Never push, never `gh repo create`, never commit** unless the project lead explicitly asks. If so, use a feature branch, not main.
- **No hardware / Nexus.** Nothing may reach Quantinuum without `allow_hardware=True` **and** the project lead's explicit per-run approval, with the HQC cost recorded. The `nexus` backend is a stub that raises `NotImplementedError` (`docs/nexus_toggle.md`).
- **A single `config.py`** holds all settings. Add a dataclass block in the existing style; don't scatter constants.
- **Never invent numbers, citations or results.** Tag claims **[established] / [derived] / [measured] / [inferred] / [unverified] / [assumed]**. Report failures and your own mistakes plainly.
- **Every noisy curve is a classical prediction under an ASSUMED noise model**, never an H2 result. Say so in every output and doc.
- **Ceilings (SCOPE §5):** state vector ≤ 24 spins, ED ≤ 20. **Refuse before allocating**, using `check_ceiling` / `check_physical_ceiling`. The *physical* register (code + ancillas) is what counts. Stim is unbounded.
- **Don't modify verified cores** (`src/operators.py`, `src/trotter.py`, `src/observables.py`, `src/qec/*`, `src/compare.py`) except by additive functions. New work goes in new modules.
- **Stim proves fault-tolerance facts; pytket / Guppy / Selene / local-sim execute.** Never conflate the two.
- `data/` is written only by reproducible scripts from trusted inputs. Synthetic fixtures must never write there.
- **H2 tiers (`src/h2_backend.py`, `docs/nexus_toggle.md`):** LE (local emulator), SC (Nexus syntax checker, H2-1SC/2SC) and the Nexus-hosted noiseless H2-1LE (`src/h2_hosted.py`, no HQC, cost verified to be 0) are free and **pre-approved by the project lead**; anything that spends HQC (H2-1E/2E emulators, hardware) is **never** run without the project lead's per-run go. The 50k HQC are emulator credits. The Nexus emulator is ≤ 32 qubits state-vector (DECISIONS.md OPEN-4).
- **Log every Quantinuum-stack problem** (pytket-quantinuum, qnexus, pecos/LE, Guppy/Selene, TKET) in `docs/quantinuum_issues.md` the moment it is found, with a reproduction, even if we work around it. The project lead has Nexus access partly to help troubleshoot Quantinuum's software.
- **Ask the project lead** for decisions that are theirs to make: scope, physics direction, FT standard, which budget, anything outward-facing. Give a recommendation with the question, and explain jargon briefly, for a non-specialist reader on mobile.

## Environment
- `.venv`, **Python 3.12.14** (SCOPE pins 3.11, unavailable; FLAG A open). Host: aarch64, **2 cores**, ~6–7 GB free.
- Pinned: numpy 2.5.3, scipy 1.18.1, pytest 9.1.1, stim 1.16.0, pytket 2.18.4, guppylang 1.1.2, selene-sim 0.3.4, hugr 0.18.8.
- Tests: `. .venv/bin/activate && python -m pytest tests/ -q` (currently 231/231; about 125 s on this host, 125–240 s across the three platforms measured). Run the full suite before reporting.
- **H2 local emulator needs its own environment** (`requirements-le.txt` → `.venv-le`; `pytket-quantinuum[pecos]` conflicts with the pinned selene-sim, `docs/quantinuum_issues.md` QI-1). LE tests: `.venv-le/bin/python -m pytest tests/test_h2_*.py -q` (about 3 min); in `.venv` they skip. Nexus client `qnexus==0.51.1` is in `requirements.txt` and imported only inside `src/h2_backend.py`'s SC/E functions.
- Run scripts as `.venv/bin/python -I scripts/<name>.py`. Scripts insert the repo root into `sys.path`.
- Zenodo dataset for 2503.20870: `/home/opc/zenodo_18487089/zenodo_data` (outside the repo, MD5-verified; never copy it in).

## Physics / code conventions [established in this repo]
- H = −J Σ Z_iZ_j − h Σ X_i; row-major site index n = y·Lx + x; **qubit 0 = most significant bit**.
- Reference circuits (2503.20870): J·dt = 0.25, h·dt = 0.5 → in our convention **(J, h) = (+1, +2)**, dt = 0.25; ry(θ) prep, θ = π/6 (quench1) and −10° (quench2). Square lattices are a periodic 7×8 torus, row-major (QASM-verified).
- **Use the circuit-order Strang step** (`src/compare.py`: X half, ZZ, X half) when comparing to the published circuits. `src/trotter.py`'s ZZ-outside splitting gives different results at h·dt = 0.5.
- Z2 = ⟨(ΣZ)²⟩/N² (the second moment, *not* the connected variance).
- The frustrated triangular model needs **J < 0** in our convention.
- pytket angles are half-turns: `ZZPhase(α) = exp(−iπα/2 ZZ)`.
- **Encoded H2 runs use randomized compiling** (Pauli twirling, as 2503.20870 does every two Trotter layers). This is the team's decision D-RC (journal Entry 24), and the predicted "encoding helps" GO rests on it (★ FLAG-0).

## Tool facts learned the hard way
- **pytket core has no shot simulator**: `get_statevector()` rejects mid-circuit Measure/Reset. local-sim (`src/backends_qc.py`, `src/encoded_codes.py`) interprets pytket commands itself and is cross-checked against `get_statevector`.
- **Selene / Guppy 1.1.2:**
  - the HUGR-QIS compiler **rejects pytket `XXPhase`** (author it as H·ZZPhase·H);
  - `measure` / `project_z` return lazy values, so use `.read()`;
  - array elements can't be consumed, so use `project_z` and `reset`;
  - `.metrics()` is a *method*;
  - variable programs are generated into a temp module (`guppy_program`) because Guppy needs inspectable source.
- **Selene's `DepolarizingErrorModel` charges `p_1q` on every native rxy *and* rz** (×3.85 vs pytket-level counts) and `p_init` on allocations. Expect lower acceptance than the Stim model (`data/selene_gap.txt`).
- Selene runs at 16–18 qubits are slow (about 1–4 s per shot). Use `n_processes=2` and modest shot counts.
- In Stim fault analysis, Pauli rotations act as identity (exact for Pauli-fault propagation). Use the `clifford` mode at Clifford angles for consistency checks. Noise tags `cls:item:cmd` let error locations be matched across the Z and X images.
- **Background watchers:** `pgrep -f "<pattern>"` matches its own command line if the pattern appears in it, so a watcher can wait on itself forever. Match on a PID or an output file instead. Prefer `run_in_background` with notification over polling.

## Workflow
- Summarize the brief back to the project lead first. If a brief is underspecified, state the assumption and proceed. Stop at requested checkpoints.
- Verify before claiming:
  - transparency checks (encoded == bare at zero noise);
  - independent cross-checks (a second method, not the same code path);
  - discriminating test instances (avoid constants that any state reproduces).
- For larger builds, an independent read-only reviewer sub-agent is worth it. Fix its majors with regression tests.
- **After every pass:**
  - update `handoff/plan.md` (new numbered section);
  - add a journal entry (`## Entry N`, plus the status board, timeline and key-decisions table). Kiro also appends entries, so check the last number first;
  - update `open-questions.md` (add, resolve, move);
  - give the project lead a short paste-ready message for Kiro: what changed, files, results, what to run next (reviewer → researcher → annotator), and open items and FLAGs.
- Keep writing plain: for the project lead, lead with the answer; for files, put status tags on every claim.
