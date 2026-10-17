# TFIM with logical vs physical qubits, aimed at Quantinuum H2

A classical groundwork, and a tested submission path to Quantinuum H2, for an article that computes the
**same physical observables of the transverse-field Ising model (TFIM)** with **logical (error-detected)
qubits** and with **bare (unencoded) qubits** at matched shots, using the released physical-qubit data of
Haghshenas *et al.*, *Digital quantum magnetism on a trapped-ion quantum computer*, Nature 653, 56 (2026),
[arXiv:2503.20870](https://arxiv.org/abs/2503.20870), as an external reference.

Priorities: (1) logical vs physical on physical observables, (2) frustration on the triangular lattice,
(3) thermalization, plus a smaller, skeptical thread on the emergent Gauss law as a mitigation tool.
The framing is physics plus QEC methodology, **not** quantum advantage: local observables of Trotterized 2D
Ising dynamics at these sizes are classically reachable ([arXiv:2308.05077](https://arxiv.org/abs/2308.05077)).

> **Status (October 2026).** Everything that does not spend Quantinuum credits is built, tested and
> independently reviewed, **including the path to H2**: circuits are accepted and priced by Quantinuum's free
> syntax checker and run end to end on its free hosted emulator. **No experiment has been run on the H2
> emulator (which costs HQC credits) or on hardware.** Every noisy number in this repository is a *classical
> prediction under an assumed noise model*, never an H2 result. The headline logical-vs-physical comparison
> waits for the H2 emulator runs.

## Quick start (about 10 minutes, no account needed)

You need **Python 3.12** (or [`uv`](https://docs.astral.sh/uv/), which can fetch it) and git.

```bash
git clone https://github.com/KmarH/TFIM_QEC_Frustration.git
cd TFIM_QEC_Frustration
bash scripts/setup_env.sh          # builds .venv (main) and .venv-le (H2 local emulator)

.venv/bin/python -m pytest tests/ -q                          # main test suite
.venv-le/bin/python -m pytest tests/test_h2_*.py -q           # H2 emulator tests (skipped in .venv)
.venv/bin/python -I scripts/run_h2_nexus.py --group bare-2x2-step1   # DRY RUN: prints circuits and cost, sends nothing
.venv/bin/python -I scripts/plot_q3.py                        # regenerates figures/ from data/
```

Why two environments: the H2 local emulator (`pytket-quantinuum[pecos]`) cannot be installed next to
`selene-sim 0.3.x`, which the encoded-circuit results were produced with
([`docs/quantinuum_issues.md`](docs/quantinuum_issues.md), QI-1). The main suite skips the emulator tests;
`.venv-le` runs them.

The suites take about 7 minutes (main) and 4 minutes (emulator) on 4 cores. The counts are large because many
tests are parametrized cases of one check (for example one test runs 21 times over a table of ways to break a
spending gate).

**Nothing here spends credits unless you deliberately switch it on** (next section).

## Running on H2 (what costs what)

`scripts/run_h2_nexus.py` turns a named run group (`G1`, `Q1`, `Q4`, `Q3-bare`, `Q3-iceberg`, `Q3-ladder`,
`Q3-bare-3x6`, or the cheapest check `bare-2x2-step1`) into compiled H2 circuits with an offline cost estimate,
and runs them at the tier set in `config.py` (`HardwareConfig.nexus_tier`):

| tier | what it does | cost | needs |
|---|---|---|---|
| `dry-run` (default) | builds, compiles and prices circuits offline | free | nothing |
| local emulator | `src/h2_backend.run_le`, noiseless unless a noise model is passed | free | `.venv-le` |
| `sc` | Quantinuum **syntax checker** (H2-1SC): validates and returns the exact HQC price | free | a Nexus login |
| `hosted-le` | Nexus-hosted **noiseless** emulator (H2-1LE), at most 20 qubits | free (cost verified 0.0) | a Nexus login |
| `emulator` | H2-1E / H2-2E emulator | **spends HQC** | login, config edit **and** a per-run approval phrase |

- **Free tiers need a Quantinuum Nexus account.** In Python: `import qnexus as qnx; qnx.auth.login()` (a device code
  you approve in the browser). Set `HardwareConfig.nexus_project` in `config.py` to a project name you own.
- **The `emulator` tier is double-gated by design.** It needs `nexus_tier = "emulator"`, `allow_hardware = True` and
  `max_cost_hqc > 0` in `config.py`, **plus** `--approval "<phrase>"` on the command line (the phrase is
  `NEXUS_APPROVAL` in `src/backends_qc.py`). The driver then re-quotes every circuit on the free syntax checker and
  refuses if the quote exceeds your cap; it also refuses more than 32 qubits, 10,000 shots per job and 50 HQC per
  shot. The command line cannot select the emulator tier on its own, and real hardware (H2-1/H2-2) is never selectable.
- **HQC credits belong to the project lead.** Please do not run the `emulator` tier without their go. Plan: the full
  set of runs costs **39,853 of 50,000 HQC** (server-quoted), see [`docs/h2_budget.md`](docs/h2_budget.md).
- Full details and the exact switch-on steps: [`docs/nexus_toggle.md`](docs/nexus_toggle.md). Problems found in the
  Quantinuum software (Guppy/Selene, qnexus, pytket-quantinuum, PECOS, TKET), each with a reproduction:
  [`docs/quantinuum_issues.md`](docs/quantinuum_issues.md).

## Main results (classical, at reachable sizes)

- **QEC choice (Q4).** Four codes were built and run end to end: Iceberg `[[k+2,k,2]]`, concatenated
  Iceberg `[[16,4,4]]`, the 5-qubit `[[5,1,3]]` and Steane `[[7,1,3]]` codes. In all of them the error the
  code cannot detect comes from the arbitrary-angle rotation gates, not from the code distance, so the
  distance-3/4 codes buy about 1.2× at a large cost in discarded shots. **Iceberg is recommended.**
- **Does encoding help (Q1)?** It depends on the ZZ fraction η of H2's native two-qubit gate error. At a
  prior read from the reference experiment (η ≈ 0.05) encoding is *predicted* to help, conditional on
  randomized compiling (implemented in `src/twirl.py`, [`DECISIONS.md`](DECISIONS.md) OPEN-3). This is a
  prediction, not a measurement: in the executed simulations encoded minus bare is within 1σ in every cell,
  so no run here yet *shows* encoding helping. The headline lattice is **4×5** (the emulator is limited to
  32 qubits; [`DECISIONS.md`](DECISIONS.md) DECIDED-6).
- **Frustration (Q2).** A **ground-state** (exact-diagonalization) result, not quench dynamics: on a
  matched 4×4 pair, triangular nearest-neighbour correlations are 3–5× weaker than on the square lattice.
  Reproduced bit-for-bit on three platforms, and the ratio also holds at the reference field h/|J| = 2
  (4.98 on 4×4).
- **Thermalization (Q3).** A classical study at the reference's own triangular parameters
  (h/|J| = 0.3, dt|J| = 0.25): a Monte Carlo baseline per winding sector; the ideal curves relax to the
  finite-cluster value rather than the infinite-temperature one; the time step sits below a measured Trotter
  threshold. Under assumed noise, Gauss-law post-selection is the cheap mitigation that works, and noise can
  mimic thermalization, which is why the noise-scaling ladder (λ = 1, 2, 3) is part of the H2 plan.
- **Gauss law as mitigation.** Mostly no; a modest yes for detection against bit-flip-type noise only,
  under the assumed noise model.
- **The H2 path (this pass).** 121 circuits accepted and quoted by the free syntax checker; the offline cost
  estimate equals the server quote to the cent; the Q3 circuits on the hosted noiseless emulator match an
  independent NumPy evolution (19 points × 3 observables, worst |z| = 2.5, cost 0.0). One blind review found and
  fixed one real bug in the run driver ([`review/17-h2-finish.md`](review/17-h2-finish.md)).

The formal write-up is [`docs/report/report.tex`](docs/report/report.tex) (LaTeX, compiles on Overleaf), and
[`docs/findings_vs_questions.md`](docs/findings_vs_questions.md) maps each conclusion to its evidence.

## Repository layout

| path | what it is |
|---|---|
| `SCOPE.md` | The project's constitution: the four questions, size limits, what may be done without asking and what may not. When in doubt about what the project is supposed to do, this document rules. |
| `DECISIONS.md` | The decisions that are the project lead's to make (open and decided) and the scope corrections already applied. Read it before trusting any claim that this work matches the reference experiment. |
| `handoff/plan.md`, `handoff/NN-*.md` | The numbered journal of what each pass delivered (newest last) and the briefs/reports per task. `handoff/14-h2-finish.md` is the latest. |
| `config.py`, `main.py` | One config file for every setting (sizes, fields, noise, backend switch, H2 tier), and a simple entry point. |
| `requirements.txt`, `requirements-le.txt` | Exact pinned versions for the two environments (see Quick start). |
| `src/` | The code: TFIM core (Hamiltonian, Trotter, observables), codes in `src/qec/`, the encoded TFIM and execution backends, the frustration / thermalization / Gauss-law modules, and the H2 path: `h2_circuits.py`, `h2_q3.py`, `h2_backend.py`, `h2_hosted.py`, `h2_driver.py`. |
| `scripts/` | The scripts that produce every file in `data/` and every figure, so every number can be regenerated; also `setup_env.sh`, `run_h2_nexus.py` (the run driver) and `cross_platform_check.sh`. |
| `tests/` | The automated tests. Files named `test_h2_*` cover the H2 path; some are *frozen* (written before the code, pinned by SHA-256 in `handoff/13` and `handoff/14`). `tests/fixtures/zenodo_mini/` is a tiny synthetic stand-in for the reference dataset. |
| `data/` | Results as plain text, each with a header naming the script that wrote it and whether it is a classical prediction under assumed noise, a server quote, or a free-tier run. Written only by scripts. |
| `figures/` | Generated figures (not committed; run `scripts/plot_q3.py`). |
| `docs/` | One write-up per result, the H2 docs (`nexus_toggle.md`, `h2_budget.md`, `quantinuum_issues.md`) and the formal report in `docs/report/`. |
| `review/` | Numbered independent reviews of each milestone: a reviewer re-derived the key numbers with its own code and graded findings critical / major / minor. `review/14-three-machine-peer-review.md` is the broadest; `review/17-h2-finish.md` covers the H2 path. |
| `research/` | Source and citation checks, the map of the reference dataset, the H2 noise prior, and a wide literature sweep in `research/scout/` that also looked for work contradicting this one. |
| `CLAUDE.md`, `KIRO.md`, `.kiro/` | The rules and configurations of the AI agents used (see below). |
| `Guppy on Quantinuum Systems Application.pdf` | The application sent to Quantinuum; the original source of the scope. |

Some documents mention `Conversation history/` (the project journal and open-questions register). That folder is the
private working diary of the project lead and is intentionally not in this repository.

## Scope notes worth knowing before you compare with the reference experiment

- The encoded arm **cannot run on the reference experiment's own 7×8 lattice**: Iceberg needs k+4 physical qubits
  (60 > H2's 56). Encoded-vs-bare is therefore compared on a reduced lattice that fits (now 4×5, because the Nexus
  emulator stops at 32 qubits), with the released 7×8 data as context, not as the bare arm. Encoding is only the
  varied axis with respect to this project's own bare arm ([`DECISIONS.md`](DECISIONS.md)).
- The triangular-lattice work matches the reference's §V (h/|J| = 0.3, dt|J| = 0.25, 9×6 torus), per its Figure 4(e).
  **Do not infer the triangular parameters from the released `quench4` circuit files**: they carry the *square*-quench
  field (`rx(0.5)`, h/|J| = 2; h/|J| = 0.3 needs `rx(0.0375)`) and start from |0…0>, not the winding bitstrings
  ([`research/05-zenodo-dataset-map.md`](research/05-zenodo-dataset-map.md)).

## Ground rules for anyone working in this repository

- **Never spend HQC without the project lead's explicit go** (the `emulator` tier, and anything beyond it).
- **Every noisy curve is a classical prediction under an assumed noise model**; label it as such everywhere.
- **One `config.py`** holds all settings; add a dataclass block in the existing style rather than scattering constants.
- **`data/` is written only by reproducible scripts**; test fixtures must never write there.
- **Do not edit the frozen tests** (`tests/test_h2_circuits.py`, `test_h2_backend.py`, `test_h2_driver.py`,
  `test_h2_hardening.py`, `test_h2_q3.py`) to make code pass; if one looks wrong, say so with the oracle, then re-freeze
  with the new hash recorded.
- **Tag claims**: [established] checked source, [derived] proved and tested here, [measured] output of this code,
  [inferred] reasoned but not tested, [assumed] modelling choice, [unverified] not checked.
- Size ceilings (SCOPE §5): state vector at most 24 spins, exact diagonalization at most 20. The code refuses before
  allocating. The Nexus emulator itself is limited to 32 qubits.

## Troubleshooting

- **`python3.12` not found**: install it, or install `uv` and rerun `scripts/setup_env.sh`.
- **Stim fails to build on ARM Linux**: you need a C++ compiler and Python headers (for example `gcc-c++`,
  `python3.12-devel`); on most machines it installs from a wheel.
- **Emulator tests are skipped**: you ran them in `.venv`; use `.venv-le/bin/python -m pytest tests/test_h2_*.py`.
- **`scripts/run_compare.py` needs the reference dataset** (Zenodo record
  [10.5281/zenodo.18487089](https://doi.org/10.5281/zenodo.18487089)), downloaded separately:
  `python -I scripts/run_compare.py --data <path to zenodo_data>`. The test suite does not need it.
- **Nexus errors about login or project**: run `qnx.auth.login()` again (it is per machine/container) and check
  `HardwareConfig.nexus_project`.

## How it was built

The work used a multi-agent workflow. **Kiro** (agents in `.kiro/`) planned, researched, reviewed and wrote the early
briefs in `handoff/`; **Claude Code** built from those briefs. Since 8 October 2026 Claude Code is the only agent: it
also plans, researches and reviews (independent blind reviewer sub-agents are the check), and the project lead
supervises and decides. `CLAUDE.md` holds the rules the agent follows.

## What is next (needs the project lead's go and HQC)

1. Cheapest end-to-end check on the H2 emulator: `bare-2x2-step1` (about 23.40 HQC), then `G1` (1,901 HQC), compared with
   the local emulator, Selene and Stim before spending more.
2. Q1 on 4×5 (11,636 HQC), Q4 (9,817 HQC), then the Q3 groups (16,499 HQC).
3. Measure H2's two-qubit error composition and rerun the sensitivity analysis; active error correction for the
   distance-3/4 codes.

Open decisions (Q3 size and the 50,000 HQC allocation, the per-job cost cap, randomized compiling for the Q3 Iceberg
arm) are listed in [`handoff/14-h2-finish.md`](handoff/14-h2-finish.md).
