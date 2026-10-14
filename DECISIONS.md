# Open decisions and scope corrections

This file records decisions that belong to the project lead and that the repository cannot settle
on its own, plus the scope corrections already applied. It exists because the working decision
record (`Conversation history/project-journal.md` and `open-questions.md`) is intentionally not in
this repository, so a reader of the public repo previously had no way to tell an open question from
a settled one. Peer review, October 2026, finding R-Laptop-R2-2.

Status tags follow the project convention: [established] [derived] [measured] [inferred] [assumed]
[unverified].

---

## OPEN-1 — The triangular field: h/|J| = 0.3 or 2?

**Status: OPEN. This blocks any claim that the triangular work matches the reference experiment.**

Q2, Q3 and the Gauss-law thread all run at h/|J| = 0.3, described in several places as "matching
arXiv:2503.20870 §V". That description is not currently supportable, because the project's own two
research threads independently derived **opposite** values from the same paper and never
cross-checked each other:

| source | value | basis |
|---|---|---|
| the paper's own prose (abstract, intro, §V), read twice independently | h/\|J\| = 0.3 | `research/04-gauss-law-citations.md` item 3 [established] |
| the paper's own **released quench4 circuits** | **h/\|J\| = 2** | `research/05-zenodo-dataset-map.md`; `rzz(0.5)`, `rx(0.5)`/`rx(1.0)`, identical to the square quenches, in all 80 QASM files [established] |

`research/04` additionally states that §V's body text was never actually reached, which weakens
the prose reading. `research/05` concluded "the 0.3 appears to be an error in the brief" but that
finding never propagated to `GaussLawConfig` / `Q3BaselineConfig`, and every later entry kept both
the 0.3 value and the "matching the reference" framing.

**What the review established about the consequences** (two reviewers, independently, in circuit
order, noiseless):

- At h/|J| = 2 the dimer / emergent-Gauss-law / B_W₀ framework **does not apply**. The
  sector-restricted effective theory is first order in h/|J|, so it is not a controlled
  approximation when the field dominates. Operationally, the probability of remaining in the
  defect-free sector collapses from 1.0 to 0.13–0.63 within a *single* Trotter step, against the
  slow O((h/|J|)²) leakage the h ≤ 0.5 design assumes. [measured]
- Noiseless in-sector weight: 0.55 at N = 9, 0.11 at N = 12 — i.e. falling with system size, so on
  the reference's 7×8 torus Gauss-law post-selection would keep an exponentially small fraction of
  shots even at zero noise. [measured]
- Defect density per triangle at h = 2 reaches 0.11–0.18, up to ~69% of the infinite-temperature
  value 0.25. [measured]
- **Q2 is unaffected either way:** it is a ground-state ED statement, and the 3–5× weakening holds
  at h = 2 as well (ratio 4.98 on the matched 4×4 pair). [measured]
- The released quench4 circuits also prepare `ry(0)` on all 54 qubits with **zero** `x` gates, so
  they encode *neither* candidate winding-sector initial state. The "which sector does the
  experiment start in" question is therefore not answerable from the data release at all,
  independently of the field value. This confirms open question T-5 by direct inspection. [measured]

**The decision.** Either:

- **(a)** Keep h ≤ 0.5 and relabel this work as a deliberately chosen, self-contained study of the
  weak-field frustrated regime, with no published counterpart. Drop every "matching §V" and
  "describes the reference experiment" claim. This is cheap and is what the repository text has
  been corrected to say in the interim.
- **(b)** Build a genuine h/|J| = 2 study. This needs different machinery — not a
  first-order-in-h effective sector theory — and an initial state chosen on some basis other than
  "what the released QASM shows", since the QASM shows nothing there.

**What would settle the underlying factual question:** checking the paper's PDF or Supplemental
Material (not the HTML mirror, which both research threads note truncates parts of §V and the
Methods) for whether it describes *multiple* triangular runs at different field strengths, one of
which could genuinely be h/|J| = 0.3 while the released quench4 represents another at h/|J| = 2.
Until then, treat 0.3 as **unconfirmed against the dataset the project actually has**.

**Interim handling (applied):** no physics constant was changed. The documentation no longer claims
the triangular work matches the reference.

---

## OPEN-2 — The Q1 lattice

**Status: DECIDED in principle, implementation pending.**

The original Q1 design was "the same physical observables, encoded vs the released physical-qubit
data, with encoding as the only axis that varies". That cannot be run:

- Iceberg uses k+2 code qubits plus a syndrome ancilla and a flag, i.e. **k+4 physical** with k
  even. The reference's 7×8 lattice (56 logical) therefore needs **60 > 56** physical qubits.
  [derived]
- The design is a single Iceberg block; two blocks would need ≥ 62 physical qubits, and inter-block
  logical ZZ would no longer be the native weight-2 gate. So 7×8 cannot be encoded on H2 in any
  variant. [derived]
- Largest lattices that fit 56 physical qubits: 4×13 (56), 5×10 (54), **6×8 (52, closest in shape
  to 7×8)**, 6×6 (40). [derived]
- The project already made exactly this reduction for Q3 (6×6 and 3×4) but never for Q1.

**Decision:** Q1's head-to-head is **encoded vs bare, matched shots, on one reduced lattice that
fits both arms** (6×8 recommended). The released 7×8 data becomes an external reference:
quantitative at step 1 via an exact light-cone finite-size correction (the step-1 Z₂ pair average
moves only slowly with N — 0.7653 at 4×4, 0.7610 at 4×5, 0.7503 at 7×8 [measured]), and a trend
comparison thereafter.

**Still to do:** recompute the η crossover on the chosen non-degenerate lattice (the headline
η\* = 0.25 comes from the degenerate 2×2 4-site ring; η\* rises to 0.36 at 2×3 and 0.44 on a true
4×4 torus, so the margin improves — but the number quoted should match the lattice actually used).

---

## OPEN-3 — Randomized compiling is not implemented

**Status: OPEN. This is a precondition for the Q1 conclusion, not a refinement.**

The "encoding helps at η ≈ 0.05" GO rests explicitly on randomized compiling (decision D-RC,
★ FLAG-0, `report.tex` §Q1, `handoff/11`). There is no twirling implementation in `src/`. It is
disclosed in the handoff, but it gates the headline Q1 claim, so it is recorded here too.

When it is built, re-verify the transparency check (encoded == bare at zero noise) with twirling
switched on.

---

## Applied corrections (no decision needed)

These were wrong independently of the decisions above and have been fixed:

| what | where |
|---|---|
| Defect-density and P_out "Trotter inflation" figures were attributed to the reference circuit; in the published circuits' gate order the bias has the **opposite sign** | `docs/q3_thermalization.md`, `docs/gauss_law_dimers.md`, `docs/findings_vs_questions.md`, `docs/report/report.tex` |
| The circuit sign check compared magnitudes only, while the report claimed it checked gauge signs | `scripts/run_compare.py`, `docs/report/report.tex` |
| Text I/O used the platform default encoding, breaking the project on Windows | all of `src/`, `scripts/`, `main.py`, `config.py` |
| `python -I main.py` failed, though the project documents `-I` as the convention | `main.py` |
| Step-1 H2-vs-simulation gap quoted as ≈3σ; against the exact N = 56 value it is ≈2.0σ | `docs/q1_compare.md` |
| Gate-count penalty for the distance-3/4 codes quoted as 3–7×; matched-lattice value is 6.6–8.6× | `docs/encoded_tfim.md` |
| Assorted doc/data mismatches (13× vs 32×, acceptance ratios, slopes, "one early point", stale memory figures and test counts) | various |

The full review, with the evidence for each item, is in the peer-review reports kept with the
project lead (three independent reviewers, three platforms, three rounds).
