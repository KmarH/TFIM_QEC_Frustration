# RESOLVED-1 - the triangular field, full evidence trail

**Split out of `DECISIONS.md` on 2026-10-23** as part of a context-size reduction pass.
The question is settled (h/|J| = 0.3); `DECISIONS.md` carries the verdict and links here.
Nothing below was rewritten - it is the original text, verbatim.

---

## RESOLVED-1, formerly OPEN-1 then DECIDED-1 — The triangular field: h/|J| = 0.3 or 2?

**Status: RESOLVED 2026-10-15 on evidence. h/|J| = 0.3 is CORRECT, and this project's triangular
configuration (h/|J| = 0.3, dt|J| = 0.25, 9×6) MATCHES the reference's §V. The `h/|J| = 2`
reading came from the released quench4 circuit files, and those files are defective: they carry
the reference's own *square*-quench field value. Nothing in the configuration needed changing —
it was right all along.**

**The one-line version.** The paper's Figure 4(e) states, verbatim, *"All data taken at
(h/|J|, dt|J|)=(0.3, 0.25)."* §V's body sets the regime as a weak transverse field, and the
lattice is 9×6. The project's own `research/04` read this correctly from the start. The circuit
files disagree, and the circuit files are wrong.

**Why this entry has three statuses.** It was opened as OPEN-1 when the peer review found the
conflict; it was closed on 2026-10-15 as DECIDED-1 by choosing to treat the work as a
self-contained weak-field study (because the paper's §V body appeared unreadable, so the
circuits were the only hard evidence); and it was reopened and resolved the same day once the
full text was finally retrieved. The earlier DECIDED-1 framing — that the work does *not*
reproduce the reference — was an over-correction and has been withdrawn from the documentation.
The sequence is kept here deliberately: the conflict was hard to find precisely because earlier
records were tidied rather than annotated.

### The evidence (2026-10-15)

**The paper** (arXiv:2503.20870v3, read in full):

- §V, *"Emergent gauge theory on a frustrated lattice"*, sets the regime: **"For weak transverse
  field (0 < h ≪ J)"**. [established]
- **Figure 4(e) caption: "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)."** [established]
- The triangular lattice is **9×6** (§V, and again Methods §VII.1) — 54 sites. [established]
- There is **one** triangular run at **one** field. The maximal and minimal winding sectors are
  two initial states within it, not separate runs. [established]
- The paper states the **square** quenches use **h = 2|J|**, explicitly a different system.
  [established]

Earlier fetch attempts failed only because the HTML is 244,452 characters and truncated before
Figure 4 — not because the value was missing. `research/04`'s caveat that §V's body was never
reached is now closed.

**The released circuits** (read from `~/zenodo_18487089/zenodo_data/circuits/`):

| file | rzz | rx (two half-layers) | ry | qreg |
|---|---|---|---|---|
| `quench1_step1.qasm` (square 7×8) | 112 × `rzz(0.5)` | 112 × `rx(0.5)` | 56 × `ry(π/6)` | 56 |
| `quench4_step1.qasm` (triangular 9×6) | **162 × `rzz(0.5)`** | **108 × `rx(0.5)`** | 54 × `ry(0)` | 54 |

- The gate **counts are correct** for 9×6: 162 = 3N bonds, 108 = two half-layers on 54 qubits. The
  geometry really is the triangular one. [measured]
- The **angles are the square quench's**. With dt|J| = 0.25 that is h·dt = 0.5, i.e. h/|J| = 2.
  At the paper's h/|J| = 0.3 each half-layer would be **`rx(0.0375)`**, about 13× smaller.
  [measured]
- The dataset's gauge identities only flip **signs** of (J, h, θ); they cannot change a magnitude.
  So this is not a gauge artefact. [derived]
- **The release already documents these circuits as not the experiment's.** README, verbatim:
  *"For quench4, the circuits in the folder are initialized to the |0...0> state, while the
  experiments initialized to two different bitstring configurations."* The wrong field is a
  second, undocumented instance. The same README offers the circuits "to cross-check against the
  gate angles and circuit geometry we used" — which is exactly the use that misled this project.
  [established]

**The physics agrees with the paper, not the circuits.** §V's whole subject is an emergent Z₂
Gauss law and dimer description that exists only for h ≪ J. At h/|J| = 2 there is nothing of the
kind to observe: three independent reviewers measured, noiselessly, that the in-sector probability
collapses from 1.0 to 0.13–0.63 within a **single** Trotter step, with in-sector weight falling
with size (0.55 at N = 9, 0.11 at N = 12). A paper reporting dimer correlations relaxing toward
Markov-chain Monte Carlo values cannot have been at h/|J| = 2. [measured]

### Consequences

- **`research/04` was right.** Its reading stands; the caveat added to it earlier on 2026-10-15 is
  corrected.
- **`research/05` read the files correctly**; only its inference about the experiment was wrong,
  because the files misrepresent the experiment. It is now the detailed home for this finding.
- **Q3 and the Gauss-law thread may again be described as matching the reference's §V**, now cited
  to Figure 4(e) rather than assumed.
- **The weak-field physics argument is kept**, reframed: it explains why the reference's own choice
  of a weak field is the right regime and why the conclusions are safe at 0.3. It corroborates the
  value instead of substituting for it.
- **New finding, recorded in `research/05`:** the released quench4 circuits are inconsistent with
  the paper's stated parameters in both field and initial state. Do not use them to infer the
  triangular experiment's parameters; use the paper.
- **T-5 narrows.** The two winding sectors **are** identified in the release, as the
  `quench4_min_winding_*` and `quench4_max_winding_*` data files. What is missing is the explicit
  initial bitstrings and circuits matching them.

### What did not change

No physics constant, no code, no number. `h = 0.3` and `dt = 0.25` were correct before any of
this and are untouched; the suite stays at 274/274 on three platforms. Only the claims about what
the work corresponds to moved — back to the project's original position, sourced this time.

### How the conflict arose (history, kept for the record)

Everything from here on describes the state of knowledge **before** the resolution above. It is
kept because the failure mode is instructive, not because it is current.

Q2, Q3 and the Gauss-law thread all run at h/|J| = 0.3, described in several places as "matching
arXiv:2503.20870 §V". For a time that description could not be defended, because the project's own
two research threads independently derived **opposite** values from the same paper and never
cross-checked each other:

| source | value | basis |
|---|---|---|
| the paper's own prose (abstract, intro, §V), read twice independently | h/\|J\| = 0.3 | `research/04-gauss-law-citations.md` item 3 [established] |
| the paper's own **released quench4 circuits** | **h/\|J\| = 2** | `research/05-zenodo-dataset-map.md`; `rzz(0.5)`, `rx(0.5)`/`rx(1.0)`, identical to the square quenches, in all 80 QASM files [established] |

`research/04` additionally states that §V's body text was never actually reached, which at the time
appeared to weaken the prose reading — the opposite of the truth, as it turned out: §V's body and
Figure 4(e) both confirm 0.3. `research/05` concluded "the 0.3 appears to be an error in the brief"
but that finding never propagated to `GaussLawConfig` / `Q3BaselineConfig`, and every later entry
kept both the 0.3 value and the "matching the reference" framing. In the end the config was right
and the propagation failure was harmless, but only by luck: nobody had checked which source was
authoritative.

**The lesson worth keeping.** A released artefact that *looks* like primary evidence — a circuit
file, published by the authors, offered expressly for cross-checking gate angles — outranked the
paper's own text in two independent analyses here. It should not have. When an artefact and the
publication disagree, the publication describes the experiment; the artefact describes whatever was
exported. Check the physics for which one is coherent: at h/|J| = 2 the phenomenon §V reports
cannot occur, and that alone should have settled it without needing the full text at all.

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
  they encode *neither* candidate winding-sector initial state. (Narrowed by the resolution above:
  the two sectors *are* identified in the release, as the `quench4_min_winding_*` and
  `quench4_max_winding_*` data files; it is the explicit bitstrings and matching circuits that are
  absent. See T-5.) [measured]

**The decision taken at the time, since superseded.** With §V's body believed unreadable, the
options were:

- **(a) CHOSEN 2026-10-15, then WITHDRAWN the same day.** Keep h ≤ 0.5 and state the work as a
  deliberately chosen, self-contained study of the weak-field regime with no published
  counterpart, dropping every "matching §V" claim. **Withdrawn** once Figure 4(e) was read: the
  published counterpart exists and the match is real, so this framing understated the work.
- **(b) Not chosen, and now moot.** Build a genuine h/|J| = 2 study. There is no reason to: the
  reference's triangular experiment is itself at 0.3.

**The weak-field argument, which survives the reversal.** It no longer carries the choice of
h/|J| = 0.3 — Figure 4(e) does that — but it remains true, and it is why the reference's own
choice of a weak field is the right regime and why this thread's conclusions are safe there:

- The sector-restricted / quantum-dimer description is an effective theory to **first order in
  h/|J|**. It needs h ≪ |J| to be a controlled approximation at all.
- Leakage out of the defect-free sector scales as about **h²** (the measured exponent is 2.08),
  so at h ≤ 0.3 the in-sector population stays dominant and conditioning on it is a correction
  rather than a reinterpretation.
- The project's own field scan already shows the in-sector verdicts stable for h ≤ 0.3 and
  straining at h = 0.5 (26% of the weight out of sector) — so 0.3 sits inside the validated range
  and 0.5 is its stress point.
- At h/|J| = 2 none of that holds: noiselessly the in-sector probability collapses to 0.13–0.63
  within a *single* Trotter step, and the in-sector weight falls with system size (0.55 at N = 9,
  0.11 at N = 12), so on the reference's 7×8 torus Gauss-law post-selection would retain an
  exponentially small share of shots even with zero noise. [measured]

This is also the decisive consistency argument: the phenomenon §V reports — dimer correlations
relaxing toward Markov-chain Monte Carlo values inside winding sectors — cannot occur at
h/|J| = 2. That alone identified which of the two conflicting sources had to be wrong, before the
paper's text was ever retrieved.

**Scope of the documentation change, as it now stands.** No physics constant was changed at any
point, and no number moved: `h = 0.3` and `dt = 0.25` are exactly as they always were, and the
suite is unchanged at 274/274 on three platforms. The net effect on the documentation is:

- Q3 and the Gauss-law write-ups describe the configuration as matching the reference's §V, cited
  to Figure 4(e), and additionally carry the weak-field argument above.
- Q2 is relabelled as a **ground-state** exact-diagonalization result — a genuine improvement that
  survives independently of all this — and noted to be robust either way: the 3–5× weakening also
  holds at h/|J| = 2 (4.98 on the matched 4×4 pair, against 4.59 at h = 1). [measured]
- The released quench4 circuits are documented as unsafe for inferring the experiment's
  parameters, in `research/05-zenodo-dataset-map.md`.
- `config.py`'s triangular blocks, the report, the findings map and the README cite the reference
  for the field again, with Figure 4(e) as the source.
- The research notes and handoff briefs that recorded the original readings were **not
  rewritten** — they are dated records, and rewriting them is what would make a conflict like
  this hard to find again. Each carries a dated note pointing here. The notes added on
  2026-10-15 under the withdrawn framing were themselves corrected rather than layered over,
  since they were a day old and wrong.

**T-5, narrowed (independent of the field question).** The released quench4 circuits prepare
`ry(0)` on all 54 qubits with zero `x` gates, so the circuits encode neither candidate
winding-sector initial state. But the two sectors **are** identified in the release, as the
`quench4_min_winding_*` and `quench4_max_winding_*` data files. So what is missing is the explicit
initial bitstrings and circuits matching them, not the sector identification itself. [measured]
