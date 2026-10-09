# SCOPE.md — TFIM Logical-Qubit Simulation on Quantinuum H2

**Status:** APPROVED by Kevin 2026-10-06. Autonomy policy in section 14 applies. **§1/§2 amended 2026-10-08 with Kevin's explicit permission (SCOPE-1) to match the article thesis (journal Entries 14/16); the four questions and their "done when" criteria are unchanged in substance — only framing, priority order, and current status were added.**
**Project root (box):** `/home/opc/KiroTest-project`  **Origin (laptop):** `C:\Users\kevin\OneDrive\KiroTest`
**Authoritative inputs:** `HANDOFF.md`, the Guppy application PDF (primary scope statement — tooling/QEC/observables/sizes), `drafts/gauss_law_self_mitigation_assessment.md` (UNVERIFIED — to be checked, not trusted).

---

## 1. Goals
A reproduction-and-extension quantum simulation of the transverse-field Ising model (TFIM) with logical qubits / error detection on Quantinuum H2 tooling. The deliverable is **evidence answering scientific questions**, not plots alone.

**★ Article thesis / north star (Kevin, journal Entries 14/16; this §1/§2 rewritten to match it, SCOPE-1, 2026-10-08).**
The headline contribution is to **compute the *same* physical TFIM observables with LOGICAL (encoded) qubits on
Quantinuum H2 and compare, head-to-head, against the PHYSICAL-qubit baseline** — closing a named gap in the
literature: a Nature paper (reproduction target **arXiv:2503.20870**) computes these TFIM observables on
*physical* qubits and released its raw data (Zenodo); separate work runs *logical*-qubit simulation but does
not compute these physical observables. **The comparison is against 2503.20870's own released raw physical-qubit
data** — same Hamiltonian, same observables, same conventions, encoding as the single varied axis. No
cross-platform comparison.

**Priority order (Kevin's):** (1) logical-vs-physical on physical observables > (2) **frustration on the
triangular lattice** > (3) thermalization and the emergent Gauss law. The **frustration spine (2) carries the
least-contested novelty** and is a primary scientific focus alongside (1).

**Framing (K4, resolved 2026-10-08).** The contribution is **logical-vs-physical advantage on real hardware
observables + frustration physics + QEC methodology**, NOT beyond-classical dynamics — local Trotterized 2D-Ising
observables at these sizes are classically reachable today (arXiv:2308.05077). Do not frame the paper as quantum
advantage from the dynamics. Every noisy curve is a classical prediction under an assumed noise model until it is
an H2 result.

**Realization.** The classical/local infrastructure (QEC codes, FT gadgets, observables, the Q2 and Q3 baselines,
the matched-comparison harness) is built and independently reviewed; the headline logical-vs-physical result and
the matched H2 comparisons are **gated on H2 hardware access** (deferred by Kevin; see `handoff/05`).

## 2. The four questions (definition of done = evidence, with uncertainties, compared to the reference article)
*Priority per §1: Q1 and Q2 are the spine; Q3 and the §3 Gauss thread are lower-priority. "Done when" criteria below are unchanged; current status is annotated.*

1. **Logical vs physical qubits** — vs Haghshenas et al. (arXiv:2503.20870) physical-qubit results: what changes in fidelity, accessible evolution time, observables, and cost (qubits/gates/post-selection) when logical qubits are used? *Done when:* a quantitative comparison on the non-frustrated lattice with error bars, **against 2503.20870's released raw physical-qubit data**. *Status:* encoded machinery, the comparison harness, and a noise-sensitivity prior are built and reviewed; the matched head-to-head is **hardware-gated** (the article spine, `handoff/05`).
2. **Frustration** — what it does (constrained dynamics, dimer correlations, winding sectors, constraint violations, ground-state degeneracy) vs the square lattice. *Done when:* triangular-vs-square comparison on the above observables. *Status:* dimer/winding/defect observables built and reviewed; ground-state frustration signature measured; dimer-correlation/winding-vs-square contrasts and larger sizes still thin.
3. **Thermalization** — behavior across lattices, fields, encodings, noise, vs ergodic reference values. *Done when:* relaxation/observable curves with ergodic baselines and uncertainties. *Status:* **DONE at classically reachable sizes** (sector-restricted MCMC baseline, Trotter-threshold study, ideal/noisy/encoded curves, size story; reviews 09–11); the matched H2 curves remain hardware-gated; no thermodynamic-limit claim.
4. **QEC choice** — Iceberg d=2, concatenated Iceberg d=4, 5-qubit d=3, Steane d=3: which are used, why each can/can't be used (qubit count, gate set, logical-gate availability, post-selection rate), which works best and why. *Done when:* implemented path has data + the on-paper codes have a written feasibility analysis. *Status:* all four built, verified, run end-to-end; **Iceberg recommended** (the undetectable residual sits at the arbitrary-angle rotation gadgets, not the code distance, so d≥3 is dominated); the H2-calibrated ranking is hardware-gated.

## 3. Extra thread (skeptical — do NOT assume it works)
Whether the triangular lattice's **emergent (approximate) Gauss law** (quantum-dimer picture) can serve for error detection / correction / symmetry-based mitigation, and on which platforms (trapped ion, neutral atom, superconducting) it is viable. *Done when:* a defensible yes/no-and-where, with explicit noise-model assumptions, benchmarked against exact-symmetry methods (GUESS, symmetry-adjusted shadows, Cai), ZNE, PEC. Empirical test is gated on triangular dimer data.

## 4. Stage order (bottom-up; each stage validates the next)
1. Square lattice, **unencoded** (physical) — reproduction baseline
2. Square lattice, **encoded** (logical / error detection)
3. **Triangular lattice — MAIN FOCUS** (frustration, dimer physics)
4. **Guppy mid-circuit discard + 3D** — dynamic logical circuits, 3D extension

Physical-vs-logical comparison is on the **non-frustrated** lattice.

## 5. Backends and size ceilings
- **Single `config.py`** holds ALL settings, with a **backend switch defaulting to local**.
- **Hardware gated** behind `allow_hardware=True` **plus** explicit per-run user approval (credits). Nexus/H2 emulator stubbed behind that flag. Local emulators are fine.
- **Size ceilings (RAISED from the old ~1 GB host — box has ~8 GB available):**
  - Sparse ED (Lanczos): raise from <=16 spins toward **<=~22-24 spins** (validate memory empirically before committing).
  - Statevector Trotter: raise from <=20 toward **<=~24 spins** (2nd-order Suzuki-Trotter), confirmed by a quick memory probe at the chosen size.
  - **Stim: unbounded** (stabilizer, circuit-level FT-gadget verification).
  - <26-site H2-emulator runs remain stubbed behind `allow_hardware`/Nexus.
  - *Note:* ceilings above are proposals; qc-reviewer confirms real memory headroom at the chosen sizes before they are frozen.

## 6. QEC implementation policy
- **Implemented path:** Iceberg d=2 and concatenated Iceberg d=4.
- **On-paper path:** 5-qubit d=3 and Steane d=3 get **Stim-level implementation + written feasibility analysis** (why each can/can't fit a non-trivial lattice), not full lattice sims unless tractable. Steane's qubit cost on a non-trivial lattice is a flagged open risk.

## 7. Tooling stack (behind the config backend switch)
pytket (+pytket-quantinuum), Stim, Guppy/guppylang ("Concept Only" -> verify current API before use), Nexus (stubbed), Qiskit (cross-validation), qermit (mitigation on unencoded reference), NumPy/SciPy, pandas, bootstrap, Matplotlib, Git. **Python 3.12 (3.12.14 on the host), hard-pinned `requirements.txt`** (qc-researcher confirms live versions of guppylang / pytket-quantinuum / selene-emulator before pinning). *(FLAG A resolved by Kevin 2026-10-07: the original 3.11 pin was dropped — the project interpreter need not match the reference sources; 3.11 is unavailable on the host and all code is built/tested on 3.12. See journal Entry 28 / open-questions FLAG A.)*

## 8. Repository policy (NON-NEGOTIABLE)
- New GitHub repo on Kevin's account, unrelated to `challenge3-hackathon`. **NEVER push.** Prepare locally -> Kevin reviews -> Kevin pushes, on a **feature branch, not main**.
- Prepare scaffold locally (git init, structure: src/, one config.py, main.py, data/, figures/, docs/, `.gitignore`, pinned `requirements.txt`); hand Kevin the exact `gh repo create` command when approved. Nothing leaves the machine.

## 9. Agent roles (the multi-agent workflow is the explicit focus)
- **qc-overseer** — scopes/triages, owns the Claude Code hand-off decision, writes `handoff/` briefs + `handoff/plan.md`, notifies the user. Cannot launch Claude Code.
- **qc-researcher** — verifies the given/seed sources: reads the section-11 papers, checks the draft's claims and arXiv IDs, confirms live tool APIs, derives key relations. Writes to `research/`; writes no project code.
- **qc-scout** — WIDE independent literature discovery (added 2026-10-06 at Kevin's request): finds and triages sources *beyond* the seed citations, actively hunting corroborating AND contradicting/reframing work so the project does not become self-contained in its initial sources. Writes status-tagged notes to `research/scout/` (never edits qc-researcher's notes); surfaces/recommends only — the overseer/reviewer decide what graduates into project claims. Writes no project code. Same no-invented-citations discipline.
- **qc-reviewer** — independent physics-and-code review at each milestone; writes `review/NN-*.md` with critical/major/minor findings; never edits the work.
- **qc-annotator** — theory-/intent-focused comments and docstrings only, after an implementation; never changes logic/config.

## 10. Claude Code hand-off boundaries (prevent scope creep)
Hand to Claude Code ONLY: new derivations with nothing in the literature to check against, and dense algorithm design (e.g. a modified error-detection scheme). Format: `handoff/NN-task.md` with goal, physical context, inputs, constraints, equations, a done-check, and a pointer to what the reviewer must verify. Recorded in `handoff/plan.md`; agents cannot launch Claude Code — Kevin runs it.

## 11. Sources to fetch (qc-researcher; Kevin does not have them)
1. Haghshenas et al., arXiv:2503.20870 (Nature 653, 56, 2026) — reproduction target.
2. Chertkov et al., arXiv:2509.25326 (+ supplement).
3. Quantinuum, arXiv:2602.22211 (beyond break-even).
4. The draft in `drafts/` — UNVERIFIED. Verify every citation; several arXiv IDs are 2026-dated/future-relative (GUESS 2603.13060, plus 2604.*, 2608.*). **Report any ID that does not resolve; never invent one.** Treat the draft's unreplicated numbers (per-Pauli epsilon, Cai Eq. 40 numerics, calibration transfer) as unverified until checked.

## 12. Hard rules (carried from HANDOFF)
Local-first; single config.py; hardware double-gated + ask first; never push to GitHub; never invent citations/numbers/results (mark established/inferred/unverified); report failures faithfully; milestones get independent review; comments theory-focused not excessive.

## 13. Definition of done (project level)
Each of the four questions in section 2 and the Gauss thread in section 3 has: evidence (data with uncertainties), interpretation, and a fair comparison to the reference article. Code is complete and reproducible from `config.py`; LaTeX report compiles on Overleaf; a "Findings vs questions" table maps each conclusion to the stage/experiment and the result that counts as its answer.

## 14. Autonomy policy (hands-off BUILD run)
Goal of unattended runs: **build as much working, local code as possible**, bottom-up, without waiting for the user. Research is in service of code, not the end product.

The agents MAY, without asking:
- read any file; fetch and read the section-11 papers; write to `research/`, `notes/`, `review/`, `handoff/`, and **write and run code under `src/`, `tests/`, and a single `config.py`**.
- **Scaffold the repo** locally: `git init`, directory structure (`src/`, `config.py`, `main.py`, `data/`, `figures/`, `docs/`, `tests/`), `.gitignore`, pinned `requirements.txt` (Python 3.12). Do NOT `gh repo create` or push.
- **Build Stage 1 (square lattice, unencoded) end to end**: TFIM Hamiltonian builder, 2nd-order Suzuki-Trotter evolution, sparse ED (Lanczos) and statevector backends behind the `config.py` switch, the observables in HANDOFF section 3 (magnetization, variance, two-point correlations, energy, relaxation), with unit tests and small-size validation **within the section-5 ceilings**.
- Begin **Stage 2 (square encoded)** scaffolding and **Stim-based QEC gadgets** (Iceberg d=2, concatenated d=4) with verification, as far as the literature supports without new derivations.
- Run local simulations/tests **serially, one agent at a time** (memory), within section-5 ceilings.
- Call `qc-reviewer` after each milestone and `qc-annotator` after each implementation, per the scaffold.

The agents MUST stop and write a brief in `handoff/NN-task.md` + note it in `handoff/plan.md` (do NOT attempt it) for:
- **new derivations with nothing in the literature to check against, or dense algorithm design** (e.g. a modified error-detection scheme) → these route to **Claude Code**, which the agents cannot launch; Kevin runs them.
- anything needing `allow_hardware` / Nexus / H2 credits.
- any `git push` or `gh repo create`.
- raising a size ceiling beyond section 5 without a memory probe first.
- any change to this SCOPE.

**Build priority order:** repo scaffold + config.py → Stage 1 code + tests (fully working) → Stage 1 small-size validation vs ED → Stage 2 scaffold + Stim QEC gadgets → stop at the first point requiring a Claude Code hand-off and continue on any other unblocked stage. Never invent numbers/results; mark everything established/inferred/unverified. If blocked on one item, note it and CONTINUE building elsewhere — never wait idle.

---
**APPROVED — section 14 is a hands-off BUILD mandate. Build maximal local code; route hard derivations to Claude Code (brief only); hardware, GitHub push, and SCOPE changes still require Kevin.**
