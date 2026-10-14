# TFIM with logical vs physical qubits, aimed at Quantinuum H2

A classical groundwork for an article that will compute the **same physical observables of the
transverse-field Ising model (TFIM)** with **logical (error-detected) qubits** on Quantinuum H2,
against **bare (unencoded) qubits run on the same lattice at matched shots**, using the released
physical-qubit data of Haghshenas *et al.*, *Digital quantum magnetism on a trapped-ion quantum
computer*, Nature 653, 56 (2026), [arXiv:2503.20870](https://arxiv.org/abs/2503.20870) as an
external reference.

Priorities: (1) logical vs physical on physical observables, (2) frustration on the triangular lattice,
(3) thermalization, plus a smaller, skeptical thread on the emergent Gauss law as a mitigation tool.

> **Status (October 2026).** Everything that can be done without hardware is built, tested and
> reviewed. **No experiment on H2 (hardware or emulator) has been run.** Every noisy number in this
> repository is a *classical prediction under an assumed noise model*, never an H2 result. The
> headline logical-vs-physical comparison waits for H2 access.
>
> **Two scope corrections from the October 2026 peer review** ([`DECISIONS.md`](DECISIONS.md)):
> 1. The encoded arm **cannot be run on the reference experiment's own 7×8 lattice**. Iceberg needs
>    k+4 physical qubits, so 7×8 would need 60 and H2 has 56. The comparison is therefore
>    encoded-vs-bare on a reduced lattice that fits (6×8 = 52 physical qubits is the closest), with
>    the released 7×8 data as context rather than as the bare arm. Lattice size, calibration and
>    mitigation all differ from the released run, so encoding is *not* the only axis that varies
>    with respect to it — only with respect to this project's own bare arm.
> 2. The triangular-lattice work (Q2, Q3, Gauss law) runs at h/|J| = 0.3. The reference
>    experiment's own released circuits are at **h/|J| = 2**. This is an **open decision**, not a
>    settled match; see [`DECISIONS.md`](DECISIONS.md). Nothing in this repository should be read as
>    reproducing the reference's triangular quench.

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
  randomized compiling (which is **not yet implemented**, see [`DECISIONS.md`](DECISIONS.md)). This is a
  prediction, not a measurement: in the executed simulations encoded minus bare is within 1σ in every
  cell, so no run here yet *shows* encoding helping.
- **Frustration (Q2).** A **ground-state** (exact-diagonalization) result, not quench dynamics: on a
  matched 4×4 pair, triangular nearest-neighbour correlations are 3–5× weaker than on the square lattice.
  Reproduced bit-for-bit on three platforms, and the ratio also holds at the reference field h/|J| = 2
  (4.98 on 4×4), so it does not depend on the open h/|J| decision.
- **Thermalization (Q3).** A classical study of the **weak-field regime h ≤ 0.5**, not of the reference
  experiment (see scope correction 2 above): a Monte Carlo baseline per winding sector; the ideal curves
  relax to the finite-cluster value rather than the infinite-temperature one; the time step sits below a
  measured Trotter threshold. Under assumed noise, Gauss-law post-selection is the cheap mitigation that
  works, and noise can mimic thermalization.
- **Gauss law as mitigation.** Mostly no; a modest yes for detection against bit-flip-type noise only.
  Like Q3, this holds in the weak-field regime h ≤ 0.5 under the assumed noise model. At the
  reference's h/|J| = 2 the dimer picture does not apply at all: even with *no* noise, 45–95% of the
  weight sits outside the defect-free sector on 9–12 sites, and that fraction falls with system size.

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
| `review/` | Numbered independent reviews of each milestone. A reviewer re-derived the key numbers with its own code and graded findings critical / major / minor; several real errors were caught this way. `review/14-three-machine-peer-review.md` is the broadest: three independent reviewers on three machines, operating systems and Python versions, over three rounds, with every disagreement adjudicated by a decisive check. |
| `DECISIONS.md` | The decisions that are the project lead's to make and are still open, plus the scope corrections already applied. Read it before trusting any claim that this work matches the reference experiment. |
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

0. **Resolve the two open decisions in [`DECISIONS.md`](DECISIONS.md)** (the triangular h/|J|, and
   the Q1 lattice) and **implement randomized compiling**, which the Q1 prediction is conditional on.
1. Calibration run on the H2 emulator (Iceberg 2×2, one Trotter step) against the local predictions.
2. Measure H2's two-qubit error composition and rerun the sensitivity analysis.
3. The decisive test: encoded vs bare on H2 at matched shots, **on one reduced lattice that fits both
   arms in 56 qubits** (6×8 = 52 physical is the closest to the reference's 7×8), with the published
   physical data as an external reference — at step 1 quantitatively, via an exact light-cone
   finite-size correction, and as a trend thereafter.
4. Active error correction for the distance-3/4 codes.

Details: [`handoff/05-hardware-gated-followups.md`](handoff/05-hardware-gated-followups.md) and
[`docs/nexus_toggle.md`](docs/nexus_toggle.md).
