# TFIM with logical vs physical qubits, aimed at Quantinuum H2

A classical groundwork for an article that will compute the **same physical observables of the
transverse-field Ising model (TFIM)** with **logical (error-detected) qubits** on Quantinuum H2 and
compare them head to head with the **released physical-qubit data** of Haghshenas *et al.*,
*Digital quantum magnetism on a trapped-ion quantum computer*, Nature 653, 56 (2026),
[arXiv:2503.20870](https://arxiv.org/abs/2503.20870). Encoding is the only axis that varies.

Priorities: (1) logical vs physical on physical observables, (2) frustration on the triangular lattice,
(3) thermalization, plus a smaller, skeptical thread on the emergent Gauss law as a mitigation tool.

> **Status (October 2026).** Everything that can be done without hardware is built, tested and
> reviewed. **No experiment on H2 (hardware or emulator) has been run.** Every noisy number in this
> repository is a *classical prediction under an assumed noise model*, never an H2 result. The
> headline logical-vs-physical comparison waits for H2 access.

The framing is physics plus QEC methodology, **not** quantum advantage: local observables of
Trotterized 2D Ising dynamics at these sizes are classically reachable
([arXiv:2308.05077](https://arxiv.org/abs/2308.05077)).

## Main results (classical, at reachable sizes)

- **QEC choice (Q4).** Four codes were built and run end to end: Iceberg `[[k+2,k,2]]`, concatenated
  Iceberg `[[16,4,4]]`, the 5-qubit `[[5,1,3]]` and Steane `[[7,1,3]]` codes. In all of them the error the
  code cannot detect comes from the arbitrary-angle rotation gates, not from the code distance, so the
  distance-3/4 codes buy about 1.2× at a large cost in discarded shots. **Iceberg is recommended.**
- **Does encoding help (Q1)?** It depends on the ZZ fraction η of H2's native two-qubit gate error. At a
  prior read from the reference experiment (η ≈ 0.05) encoding is *predicted* to help, conditional on
  randomized compiling. This is a prediction, not a measurement.
- **Frustration (Q2).** On a matched 4×4 pair, triangular nearest-neighbour correlations are 3–5× weaker
  than on the square lattice.
- **Thermalization (Q3).** A Monte Carlo baseline per winding sector; the ideal curves relax to the
  finite-cluster value rather than the infinite-temperature one; the time step sits below a measured Trotter
  threshold. Under assumed noise, Gauss-law post-selection is the cheap mitigation that works, and noise can
  mimic thermalization.
- **Gauss law as mitigation.** Mostly no; a modest yes for detection against bit-flip-type noise only.

The full write-up is [`docs/report/report.tex`](docs/report/report.tex) (LaTeX, compiles on Overleaf), and
[`docs/findings_vs_questions.md`](docs/findings_vs_questions.md) maps each conclusion to its evidence.

## Quick start

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -q                     # 231 tests, about 2-3 minutes
python main.py                                  # small TFIM run from config.py
python -I scripts/plot_q3.py                    # regenerates figures/ from data/
```

- Tested on Python 3.12.14 (Linux aarch64). On most machines every package installs from wheels; on ARM
  Linux without a Stim wheel you need a C++ compiler and Python headers first (e.g. `gcc-c++`,
  `python3.12-devel`).
- All settings live in a single [`config.py`](config.py). The execution backend defaults to local
  simulation; the `nexus` (Quantinuum) backend is a stub that raises by design and is gated behind
  `allow_hardware=True` plus explicit per-run approval.
- `scripts/run_compare.py` needs the reference dataset (Zenodo record 18487089), downloaded separately:
  `python -I scripts/run_compare.py --data <path to zenodo_data>`.

## Repository layout

| path | what it is |
|---|---|
| `SCOPE.md` | The project's constitution: the four questions, size limits, what may be done without asking and what may not. When in doubt about what the project is supposed to do, this document rules. |
| `HANDOFF.md` | The original document the project started from, written so a session with no context could understand it. Superseded by `SCOPE.md`, kept as the starting point. |
| `config.py`, `main.py`, `requirements.txt` | One config file for every setting (sizes, fields, noise, backend switch), a simple entry point, and exact pinned versions. |
| `src/` | The code: TFIM core (Hamiltonian, Trotter, observables), codes in `src/qec/`, the encoded TFIM and execution backends, and the frustration, thermalization and Gauss-law modules. |
| `tests/` | 231 automated tests; `tests/fixtures/zenodo_mini/` is a tiny synthetic stand-in for the dataset. |
| `scripts/` | The scripts that produce every file in `data/` and every figure, so every number can be regenerated. |
| `data/` | Results as plain text, each with a header naming the script that wrote it and whether it is a classical prediction under assumed noise. |
| `figures/` | Generated figures (not committed; run `scripts/plot_q3.py`). |
| `docs/` | One write-up per result (what was done, how it was verified, what it means, with status tags), the findings map, and the LaTeX report in `docs/report/`. |
| `review/` | Numbered independent reviews of each milestone. A reviewer re-derived the key numbers with its own code and graded findings critical / major / minor; several real errors were caught this way. |
| `research/` | Research notes: source and citation checks, the map of the reference dataset, the H2 noise prior, and a wide literature sweep in `research/scout/` that also looked for work contradicting this one. |
| `handoff/` | The briefs that drove the work, one per task, plus `handoff/plan.md`, the registry of what each pass delivered. |
| `CLAUDE.md`, `KIRO.md`, `.kiro/` | The rules and agent configurations of the two AI agents used (see below). |
| `Guppy on Quantinuum Systems Application.pdf` | The application sent to Quantinuum; the original source of the scope. |

Some documents mention `Conversation history/` (the project journal, the open-questions register and the
bibliography index). That folder is the private working diary and is intentionally not in this repository.

## How it was built

The work used a multi-agent workflow. **Kiro** (agents in `.kiro/`) planned, researched, reviewed and wrote
the briefs in `handoff/`; **Claude Code** built from those briefs and, from October 2026, also took over the
planning and review role; a human supervised the decisions and relayed between the two. `CLAUDE.md` and
`KIRO.md` are the rules each agent followed, so that neither changed what it should not or decided what was
not its call. Claims carry status tags: [established] checked source, [derived] proved and tested here,
[measured] output of this code, [inferred] reasoned but not tested, [assumed] modelling choice,
[unverified] not checked.

## What is next (hardware-gated)

1. Calibration run on the H2 emulator (Iceberg 2×2, one Trotter step) against the local predictions.
2. Measure H2's two-qubit error composition and rerun the sensitivity analysis.
3. The decisive test: encoded vs bare on H2 at matched shots, against the published physical data.
4. Active error correction for the distance-3/4 codes.

Details: [`handoff/05-hardware-gated-followups.md`](handoff/05-hardware-gated-followups.md) and
[`docs/nexus_toggle.md`](docs/nexus_toggle.md).
