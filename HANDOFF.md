# Project Handoff -- TFIM Logical-Qubit Simulation on Quantinuum H2

**For a fresh chat/agent session on the Oracle server. Assumes zero prior context. Read fully before acting.**

## 0. What this project is
A **quantum simulation of the transverse-field Ising model (TFIM)** with logical qubits / error detection on **Quantinuum H2 tooling** (Guppy, pytket, Nexus). The **frustrated triangular lattice is the main scientific focus**. It is a reproduction-and-extension study, built bottom-up, that must *answer scientific questions*, not just produce plots.

**The four questions the project must answer (not just produce data for):**
1. What changes with **logical vs physical qubits**, vs the reference article?
2. What does **frustration** do overall?
3. How does **thermalization** behave overall?
4. **Which QEC codes** are used, why can/can't each be used, which works best and why?

**Extra research thread (skeptical -- do not assume it works):** whether the **emergent Gauss law** of the triangular lattice (quantum dimer picture) can be used for **error detection, correction, or symmetry-based mitigation**, and on **which platforms** (trapped ion, neutral atom, superconducting) that is viable, if at all.

## 1. Confirmed stage order (bottom-up)
1. Square lattice, **unencoded** (physical) -- reproduction baseline
2. Square lattice, **encoded** (logical / error detection)
3. **Triangular lattice -- MAIN FOCUS** (frustration, dimer physics)
4. **Guppy mid-circuit discard + 3D** -- dynamic logical circuits, 3D extension

Physical-vs-logical comparison is on the **non-frustrated** lattice. Triangular additions: dimer correlations, winding-number sectors, constraint violations.

## 2. Hard constraints (NON-NEGOTIABLE)
- **Python, local-first.** No Quantinuum hardware / Nexus access yet.
- **`config.py` holds ALL settings**, with a **backend switch defaulting to local**.
- **Hardware needs an explicit flag (`allow_hardware=True`) PLUS the user's explicit approval** (jobs cost credits). Local emulators are fine.
- **New GitHub repo on the user's account**, unrelated to their `challenge3-hackathon` repo. **NEVER upload/push.** Prepare locally -> user reviews -> user pushes. **Feature branch, not main.**
- **Deliverables:** complete code (several parts) + a **LaTeX report that compiles on Overleaf**.
- Start with a **long literature sweep and full physics understanding** before coding.
- **Comments:** theory-/intent-focused, not excessive.
- **Milestones get an independent physics-and-code review.**
- **Python 3.11, hard-pinned `requirements.txt`** unless a better proposal is approved.
- Keep a **single `config.py`**.

**Claude Code hand-off (manual, user-run -- agents cannot launch it):** the hardest parts go to Claude Code -- **new derivations with nothing in the literature to check against**, and **dense algorithm design** (e.g. modified error-detection schemes). Hand-off format: a `handoff/NN-task.md` file with *goal, physical context, inputs, constraints, equations, a done-check, and a pointer to what the reviewer must verify*. The overseer records it in `handoff/plan.md`, writes the brief, and tells the user when it does so.

## 3. Confirmed tooling stack (from the Guppy application PDF)
Behind the `config.py` backend switch:
- **pytket** (primary build/compile), **pytket-quantinuum** (H2 interface)
- **Stim** (circuit-level stabilizer sim for FT gadget verification, unbounded)
- **Guppy/guppylang** (dynamic logical circuits, mid-circuit discard/reset + branching) -- readiness **"Concept Only"** -> *verify-current-API-then-use*
- **Nexus** (job mgmt + H2 **emulator** + hardware) -- no access -> stubbed behind `allow_hardware`
- **Qiskit** (cross-validation), **qermit** (mitigation on unencoded reference)
- **NumPy/SciPy** (sparse ED + Lanczos, MCMC), **pandas**, **bootstrap resampling**, **Matplotlib**, **Git** with pinned envs
- **Trotter:** second-order Suzuki-Trotter
- **QEC codes (all four in scope):** Iceberg d=2, concatenated Iceberg d=4, 5-qubit d=3, Steane d=3 (Steane's qubit cost on a non-trivial lattice is an **open risk**)
- **Observables:** total magnetization, variance, two-point correlations, energy + relaxation; triangular: dimer correlations, winding-number sectors, constraint violations

## 4. Decisions already settled in intake (defaults -- user may override)
1. **Local ED/statevector ceiling** (was memory-tight on the old host): sparse ED <= ~16 spins (Lanczos, <2 GB), statevector Trotter <= ~20 spins, **Stim unbounded**. **The Oracle server likely has far more RAM -- check `free -h` first and propose raising these.**
2. **Local vs emulator split:** locally validate physics on small lattices (<=20) and verify QEC gadgets with Stim at full code size; <26-site H2-emulator runs stay stubbed behind `allow_hardware`/Nexus.
3. **5-qubit & Steane:** Iceberg d=2 and concatenated d=4 are the *implemented* path; 5-qubit d=3 and Steane d=3 get **Stim-level implementation + written feasibility analysis** ("why can/can't it fit a non-trivial lattice"), not full lattice sims unless tractable.
4. **Repo scaffold:** prepare locally (git init, structure, `.gitignore`, pinned `requirements.txt`); hand the user the exact `gh repo create` command when approved. Nothing leaves the machine.
5. **Pins:** `requirements.txt` hard pins.
6. **Gauss-law thread:** literature/claim verification from the start; empirical test gated on triangular dimer data.

## 5. Sources to find and download (agent fetches these; user does not have them)
1. **Haghshenas et al.**, "Digital quantum magnetism on a trapped-ion quantum computer," **arXiv:2503.20870** (Nature 653, 56, 2026). **Reproduction target.**
2. **Chertkov et al.**, "Error detection without post-selection in adaptive quantum circuits," **arXiv:2509.25326** + supplement.
3. **Quantinuum**, "Computing with many encoded logical qubits beyond break-even," **arXiv:2602.22211**.
4. User's draft `drafts/gauss_law_self_mitigation_assessment.md` (on disk) -- **unverified**; check its citations/claims. Several arXiv IDs are 2026-dated/future-relative (GUESS `2603.13060`, plus `2604.*`, `2608.*`). Report any ID that does not resolve; never invent one.

## 6. Agent scaffold (on disk under `.kiro/agents` -- lean on these heavily; the multi-agent workflow is the user's explicit focus)
- **`qc-overseer`** -- scopes/triages, owns the Claude Code hand-off decision, writes `handoff/` briefs, notifies the user. Cannot launch Claude Code.
- **`qc-researcher`** -- downloads papers, lit sweep, verifies the draft's claims and arXiv IDs, confirms live `guppylang`/`pytket-quantinuum`/`selene`-emulator versions before pinning.
- **`qc-reviewer`** -- independent physics-and-code review at each milestone.
- **`qc-annotator`** -- theory-/intent-focused comments, not excessive.

Files: `.kiro/agents/qc-*.json` and `.kiro/agents/prompts/qc-*.md` (overseer, researcher, reviewer, annotator).

## 7. What to do FIRST in the new session (exact order)
1. **Set the active project** to the repo directory on the Oracle server (equivalent of `C:\Users\kevin\OneDrive\KiroTest`). If `set_project` fails, proceed with the directory as cwd.
2. **Confirm available RAM** (`free -h`). Re-propose the ceilings in section 4.1 if there's much more memory.
3. **Read the agent files** under `.kiro/agents` and the draft under `drafts/`.
4. **Write `SCOPE.md`** -- the frozen contract (stage order, four questions, Gauss thread, QEC codes implemented-vs-on-paper, backend switch defaulting local, size ceilings, pin strategy, repo-local-only, Claude Code hand-off boundaries + `handoff/` format, and a "definition of done" per question). **Then WAIT for user approval before any planning or code.**
5. After approval: Phase 1 literature sweep via `qc-researcher`, then build bottom-up through the stage order, `qc-reviewer` gating each milestone.

**Do NOT** plan or code before `SCOPE.md` is approved. **Do NOT** push to GitHub. **Do NOT** submit hardware jobs.

## 8. SCOPE.md -- purpose
The written contract agreed *before* planning/code. It (1) freezes the agreement, (2) steers the four agents so they don't drift, (3) names the Claude Code hand-off boundaries to prevent scope creep, (4) defines "done" as *evidence answering each of the four questions and the Gauss thread* -- not just plots.

## 9. User profile & working style
Software developer / physicist (TUM), writes code daily, full technical depth. Wants the multi-agent workflow as the focus, working optimally. Prefers: single `config.py`; comment appropriately without over-commenting; peer review at major milestones; Claude Code for the hardest theory/derivations and dense algorithm work while KiroCrew handles research/orchestration; never push to GitHub without review and approval, on a feature branch.
