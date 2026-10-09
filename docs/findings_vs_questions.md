# Findings vs questions (SCOPE §13)

Maps each scientific question (SCOPE §2 Q1–Q4) and the Gauss-law thread (SCOPE §3) to the
stage/experiment that answers it and the result that counts as the answer. Status tags follow
the project convention and the write-ups' own labels:
**[established]** (in a checked source), **[derived]** (proved here + tested exhaustively),
**[measured]** (output of this repo's code, with the cited file), **[inferred]** (reasoned,
not tested), **[unverified]** (not checked), **[pending]** (not yet built this run).

"Done" per SCOPE §2 means *evidence with uncertainties, compared to the reference article* —
not plots. Rows below state what evidence exists now and what is still required for "done."

---

## The four questions

### Q1 — Logical vs physical qubits (vs Haghshenas et al., arXiv:2503.20870)
| aspect | where | result | status |
|---|---|---|---|
| Logical machinery exists | `src/qec/iceberg.py`, `concatenated_gadget.py`, `src/encoded_tfim.py`, `src/encoded_codes.py` | Iceberg [[k+2,k,2]] d=2, concatenated [[16,4,4]] d=4, Steane [[7,1,3]], 5-qubit [[5,1,3]] all built + verified; encoded TFIM Trotter circuits run through a backend toggle (local-sim / Selene; nexus stub) | [measured] (review/02, review/03, review/08) |
| Encoded-vs-bare noisy comparison (classical, assumed depolarizing model) | `docs/encoded_tfim.md`, `data/encoded_iceberg.txt`, `data/encoded_codes.txt`, `data/noise_sensitivity.txt` | **Iceberg is the recommended encoded baseline.** Per-step undetected residual ≈0.42–0.50× bare; modest reach gain at p2 ≤ 3e-3, none at p2 = 1e-2. **Crucial conditionality: whether encoding helps *at all* flips once H2's native 2q-error ZZ fraction η ≳ 0.25** (exact crossover **on the 2×2 test lattice**, the most pessimistic case; ≈0.36–0.55 on larger square/triangular tori — review/13 M1, `docs/encoded_tfim.md`; ×1.5 at η=0.5 on 2×2). Code *ranking* robust across all noise variations; "encoding helps" is **not**. | [measured] + [derived], reviewed ACCEPT-WITH-FIXES (review/08); noise model [assumed], never H2-calibrated |
| Quantitative **matched** logical-vs-physical comparison on the **non-frustrated** lattice (encoded Z2 vs 2503.20870's released physical data, same observables) with error bars | — | NOT yet run head-to-head at matched size; local runs are 2–6 logical qubits vs the 56-qubit experiment, no size trim measured | **[pending]** (T-8, T-9) — and the "does encoding help" verdict is gated on HW-1 (ZZ fraction η, over-rotation ε), DEFERRED to hardware/emulator (`handoff/05`) |
| **Done when:** quantitative comparison on the square lattice with error bars. | | encoded baseline + skeptical sensitivity done; matched comparison and the η-dependent go/no-go remain | PARTLY done |

### Q2 — Frustration: triangular vs square
| aspect | where | result | status |
|---|---|---|---|
| Triangular geometry + frustrated triangles | `src/lattice.py:triangular_bonds` | 6-nn torus, 3N bonds, coordination 6, elementary 3-cycles present | [measured] (review/04) |
| Constrained dynamics / dimer picture / winding sectors / constraint violations (the frustration observables) | `src/dimers.py` | dimer n_b, defect D_t, charge, winding W_x/W_y, flippable, H_QDM, C_r, winding FCS — all diagonal; identities proved + exhaustively tested; defect density ∝ (h/|J|)² (slopes 1.96–1.98); sectors (3×4 → 3, 3×3 → 1) | [derived]+[measured] (review/05) |
| **Explicit triangular-vs-square comparison on these observables** | `scripts/compare_frustration.py` → `data/frustration_compare.txt` | square vs triangular ground-state energy density, ⟨M_z⟩, two-point ⟨ZZ⟩, and (triangular) defect density | [measured] (this run; see §"Q2 comparison" below) |
| Distance-resolved connected ⟨ZZ⟩_c, square vs triangular (handoff/09 Part A) | `src/frustration.py`, `scripts/compare_frustration_correlations.py` → `data/frustration_correlations.txt`; `docs/q2_frustration.md` | Exact P-even ground states (= run_ed energies; needed because the 4×4 square Néel pair is quasi-degenerate and a Lanczos vector comes out symmetry-broken). Matched **4×4** pair: square (bipartite) C(1) = −0.94…−1.00 with **no decay across the torus**, triangular C(1) = −0.20…−0.33 and long-distance correlations weak and **field-fragile** (C(2) +0.44 → +0.07 from h = 0.1 to 1.0). The triangular long-distance pattern **changes sign with the torus shape** (3×4 vs 4×4), consistent with the disorder-line / floating-phase caveat. **Correction:** square tori with an odd length (3×4, 4×5) are themselves frustrated (h = 0 E/bond −2/3, −0.8 vs −1 on 4×4), so the 3×4 table above has a frustrated 'square' reference (T-19). Clock-type √3 correlations seen on 3×4; settling them needs K3 (not built; T-20). | **[measured]** — Part A reviewed **ACCEPT-WITH-FIXES** (review/12, independent; fixes applied) |
| **Done when:** triangular-vs-square comparison on the above observables. | | ground-state energy/bond, ⟨ZZ⟩ and distance-resolved C(r) square-vs-triangular done on the matched 4×4 pair (+3×4 flagged); dimer/defect/winding observables are triangular-only by construction; size trend (Part B) **CANCELLED** under PROC-2 — within ED ≤ 20 only 4×4 is a clean square torus (T-21); no clock-order claim (K3 parked) | **DONE at classically reachable sizes (Part A)**; matched H2 frustration data hardware-gated |

**Q2 phase-diagram anchor [established].** The canonical triangular-TFIM phase diagram — an extended BKT critical phase separating the paramagnet from a quantum-fluctuation-driven three-sublattice (clock) ordered phase, with a 3d-XY-universality QCP — is Isakov & Moessner, PRB 68, 104409 (arXiv:cond-mat/0302105) [established]; the explicit clock-order pattern (M, −M/2, −M/2) with M<1 by order-by-disorder is Humeniuk, PRB 93, 104412 (arXiv:1602.02979) [fetched]. **No clock-order claim is graduated as [measured]**: the project currently measures energy/bond, M_z, ⟨ZZ⟩, and defect density, not a 3-sublattice order parameter (building that observable is a scope decision — see review/06 K3).

### Q3 — Thermalization / relaxation
| aspect | where | result | status |
|---|---|---|---|
| Relaxation machinery | `src/trotter.py:evolve` (record_every), `src/dimers.py` quench observables | time-resolved observables under Trotter dynamics exist | [measured] |
| Relaxation curves **vs per-winding-sector ergodic reference values** | `src/mcmc_baseline.py`, `scripts/run_q3_baseline.py` → `data/mcmc_baseline.txt`, `data/q3_relaxation.txt`; write-up `docs/q3_thermalization.md` (handoff/07) | Sector-restricted MCMC baseline BUILT: uniform (infinite-T) ensemble over the flip component of c₀ in its defect-free W₀ sector [derived]; flippable-flip sampler, sector re-checked every sweep; MCMC = brute-force exact within autocorrelation-aware SE on 3×3/3×4/3×6/4×5 (max |z| 1.39 on discriminating observables) [measured]; per-sector baselines up to the reference 9×6 (MCMC only). Noiseless Trotter curves (3×6, 3×4; h = 0.1, 0.3) overlaid with the O((h/|J|)²) leakage band (the repo's P(W≠W₀) ∝ h^2.08 predicts the measured leak to ≈1% on 3×6, 1–25% overall). **Finding [measured]:** the in-sector curves relax, but to the finite-cluster H_QDM diagonal ensemble (3×6 flippable density 0.384 vs DE 0.388), not to the infinite-T sector value (0.331): a finite-size offset from the conserved energy variance (2× for the 3-sublattice start) [derived], expected to vanish with N [inferred]. Dressed O(h²) defect density predicted to 1–9% [derived, first order]. Classical simulation only; no noise, encoding or hardware yet. | **[measured]** classical baseline + ideal curves — **reviewed ACCEPT (review/09, qc-reviewer, independent; T-12 scrutinized sound)** |
| Trotter threshold (K2) + field scan | `src/trotter_threshold.py`, `scripts/run_trotter_threshold.py` → `data/trotter_threshold.txt`; `data/q3_relaxation.txt` (h = 0.1, 0.2, 0.3, 0.5); `docs/q3_thermalization.md` §6, §8 (handoff/08 Part A) | Strang O(dt²) confirmed (local slopes 2.00–2.04, infidelity dt⁴) on 3×3/3×4/3×6 [measured]; threshold dt ≈ 0.32–0.52 = the π/(6\|J\|) Floquet resonance of the n_s = 6 spins, broadened by h [derived + measured]; working dt = 0.25 sits 1.3–2.0× below it for h ≤ 0.3 (absolute and relative criteria), but past the relative threshold at h = 0.5; the Trotter bias of the sector-conditioned verdict quantities is ≤ 0.12 of the verdict tolerance (h ≤ 0.5), while P_out is Trotter-inflated ≈10–25%. Caveat: defect density at dt = 0.25 is Trotter-inflated ≈40% on 3×6 (a blend of Floquet factors, predicted 1.39–1.44× [derived]; circuit, not continuous-time). Field scan: in-sector verdicts stable for h ≤ 0.3; h = 0.5 leaves the weak-field regime (26% weight out of sector) — a stress point, not a result. Classical only. | **[measured]** — Part A reviewed ACCEPT (review/10, independent) |
| Noisy + Iceberg-encoded curves, size story, figures | `src/noisy_q3.py`, `scripts/run_q3_noisy.py` → `data/q3_noisy.txt`, `scripts/run_q3_size.py` → `data/q3_size.txt`, `scripts/plot_q3.py` → `figures/*.png`; `docs/q3_thermalization.md` §9 (handoff/08 Part B) | Under the ASSUMED research/06 H2-prior noise (classical prediction, NOT H2): bare raw curves heat away (3×4 flippable-density error 0.05 early / 0.17 late); **Gauss-law post-selection cuts the error ≈6× (3×3) to ≈20–30× (3×4; ≈9–30× depending on the reference) at ×1.2–4.8 shots**; Iceberg ([[14,12,2]], 3×4) alone ×2.7 for ×3.1 shots and only to t ≈ 12 (8% survival); Iceberg + Gauss reaches ≤ ~0.001, at the statistical floor (not resolved as better than Gauss alone), at ≈2.5× (≈8× by t = 12) the shots. Local-sim survival = Stim first order within statistics. **Noise drifts the conditioned late values toward the infinite-T sector baseline B_W₀ — can mimic thermalization on hardware.** Size story: sector baseline to 12×12 (flippable 0.2947; a+b/N → 0.290 [inferred]); Stim budget linear in N, ≈17 faults/shot over the Q3 window at 9×6; **Iceberg 9×6 needs 58 > 56 H2 qubits**. First figures (FLAG C). | **[measured / classical prediction under assumed noise]** — Part B, reviewed ACCEPT (review/11); figures reproducible; T-17/T-18 decided by Kevin 2026-10-08: encoded H2 Q3 runs on 6×6 (with a noise-scaling arm) + 3×4 (classical predictions exist); noisy H2 curves are always compared with the noise |
| **Done when:** relaxation/observable curves with **per-winding-sector** ergodic (MCMC) baselines and uncertainties. The sector-restricted baseline is the leading reference; because the winding is only an *approximate* (emergent) label under H_TFIM, the project's own measured O((h/\|J\|)²) sector leakage (P(W≠W₀)∝h^2.08, `docs/gauss_law_dimers.md §4`) gives a slow residual approach toward the global value over a finite window — the baseline is not a hard-conserved sector. | | ideal curves (3×3/3×4/3×6, h = 0.1–0.5, Trotter-threshold-checked), noisy bare (3×3, 3×4) and Iceberg-encoded (3×4) curves under the assumed H2 prior, all vs per-sector baselines with leakage band; baselines and noise budget followed to 12×12 / 9×6 classically; quantum curves stop at N = 18 | **DONE at classically reachable sizes** (baseline review/09; threshold + field scan review/10; noisy/encoded curves + size story + figures review/11 — all ACCEPT). H2 curves remain hardware-gated; no thermodynamic-limit claim. |

**Q3 expected-results theory [established citations, no numbers imported].** Below a sharp Trotter-step threshold, local observables stay faithful and size/time-independent (Heyl–Hauke–Zoller, Sci. Adv. 5, eaau8342 [established]); even a coarse 2nd-order Trotter prethermalizes, tracking the thermal values of the *target* Hamiltonian up to long times before slow heating (Yang et al., PRX Quantum 4, 030320 [established]). These set what the relaxation curves should show.

**Q3 expected-behaviour context (NOT a present result; to be tested once the sector-restricted MCMC + curves exist) [fetched]:** an *inexact* constraint (the emergent Gauss law is only approximate) predicts anomalously slow / sector-bottlenecked relaxation rather than prompt thermalization (arXiv:2401.11294 [fetched]); controlled dephasing can act as a within-sector equilibration probe, not only as noise (arXiv:2506.13856 [fetched]) — cross-reference the dephasing verdict in `docs/gauss_law_dimers.md §5`, which stands.

### Q4 — QEC choice (Iceberg d=2, concatenated d=4, 5-qubit d=3, Steane d=3)
| aspect | where | result | status |
|---|---|---|---|
| Which implemented, why each can/can't be used | `docs/qec_feasibility.md`, `docs/encoded_tfim.md`, `src/qec/`, `src/encoded_codes.py` | All four built, verified, and run end-to-end as encoded TFIM circuits (one generic pipeline: schedule → local-sim / Stim / Selene). **None discarded.** | [measured] (review/02, review/03, review/08) |
| Post-selection rate / cost evidence | `data/encoded_codes.txt`, `data/noise_sensitivity.txt`, `data/concat_d4.txt` | Measured per-step undetected-logical probability and acceptance for all four at reduced size; budget table vs ~55 physical qubits (B2). The undetectable residual sits at the **arbitrary-angle rotation gadgets, not the code distance** [derived+measured], so d=3/d=4 buy only ≈1.2× on residual at 3–5× lower acceptance and 3–7× more 2q gates. | [measured], reviewed ACCEPT-WITH-FIXES (review/08); noise model [assumed] |
| **Which works best and why**, backed by data with a *justified* noise model | `docs/encoded_tfim.md` B5 | **Iceberg is recommended.** Steane / 5-qubit / concat-d4 are built but dominated (same residual source, far worse acceptance). The 5-qubit "discard on gate cost" the brief expected is **not** supported by the measured counts — kept, not discarded. Ranking robust across 8 noise scenarios. | [measured]+[derived] |
| **Done when:** implemented path has data + on-paper codes have written feasibility analysis. | | all four now built with measured comparative data; the *H2-calibrated* ranking (and whether encoding helps) still needs HW-1 | **mostly done** (local/classical); hardware-calibrated verdict DEFERRED (`handoff/05`, HW-1/HW-2) |

**Q4 open lever [HW-2].** Steane/5-qubit/concat are run as *detect-and-discard*; **active correction** (decode instead of discard) is the main lever that could raise their acceptance and change the ranking. It would NOT remove the rotation-gadget residual. Not built; deferred to `handoff/05`.

---

## The Gauss-law thread (SCOPE §3) — recorded verdict

Source: `docs/gauss_law_dimers.md` §5, `src/gauss_mitigation.py`; reviewed APPROVE
(`review/05-gauss-law-dimers.md`), citations checked (`research/04-gauss-law-citations.md`).
Noise model: per-qubit-per-step Pauli (depolarizing / dephasing / bit-flip), exact density
matrix on 3×3 + 400-trajectory cross-check on 3×4, **illustrative, NOT H2-calibrated**.

| use of the emergent Gauss law | verdict | basis | status |
|---|---|---|---|
| **Error correction** | **NO for the passive emergent constraint** | distance 1 (undetectable weight-1 Z anywhere, X/Y on flippable spins); no syndrome→recovery; constraint violated by the ideal dynamics itself. *(Separately: with added ancillas coupled to the local generators + mid-circuit measurement + feedback, Z₂-LGT bit-flip correction has been demonstrated in 1+1d — arXiv:2405.18504 [established]; that is an engineered monitored scheme the project did not model, not correction from the bare emergent constraint.)* | [derived]+[measured]; pointer [established] |
| **Error detection / post-selection on defects** | **modest YES, X/Y (bit-flip-type) noise only** | 2–8× bias reduction on spin correlators at p ≤ 3e-3, 1.1–1.8× cost; **floored by an O((h/J)²) physics bias** (~0.013 at h/|J|=0.3); acceptance worsens with size even noiseless | [measured] |
| …under **dephasing** | **NO** | Z errors commute with every D_t (invisible when they occur; ~70× weaker response later); post-selection only moves the residual sign, not the floor | [derived]+[measured] |
| **Depolarizing self-mitigation from the defect density** (the draft's idea) | **NO as a general method** | F_gauss ≠ per-observable decay under *local* noise; makes some observables up to 13× worse; exact only if the channel were *global* depolarizing | [measured] |
| **Exact-symmetry methods** (GUESS, symmetry-adjusted shadows, Cai) | **not applicable** to a Z-product quench | ⟨P⟩=⟨ΠX⟩=0 on a Z-basis product state and Pauli channels keep it 0 — no sector to project; TFIM lacks the U(1) the shadow method needs | [derived] |
| **Which platforms** | **undetermined by this study** | hinges on the X/Y fraction of each platform's *residual* channel; no hardware data used. Gauss-law postselection **has been realized on H2** for an *engineered* one-form syndrome (arXiv:2608.04290 [established — abstract]) — a concrete data point that the mechanism works on the target hardware, and in tension with the draft's "H2-worst" ranking (treat that ranking as **[unverified] and contested**). The project's own thread studies the *emergent/approximate* constraint, which is distinct. loss/erasure (neutral atoms) outside the Pauli model, open | [inferred]/[unverified] + one [established-abstract] data point |

**One-line headline:** mostly **NO**; a narrow, conditional **YES** for post-selection against
bit-flip-type residual noise, floored at O((h/J)²), and only where that residual is X/Y-dominated.

Comparison to alternatives at reference scale (SCOPE §3 benchmark): post-selection is cheap but
weak and floored; **ZNE is the practical baseline** (which the reference itself used, [established]);
PEC is unaffordable beyond p ≈ 1e-3 (γ² ≈ 5.7e3 at 54 qubits/40 steps, p=1e-3) [measured].

### Still open on this thread (not blockers for the verdict)
- 2503.20870's exact winding sign/orientation, which axis is its "9" in 9×6, and its C_r pair
  convention — **unverifiable from source** with current tooling (v3 PDF/Supplement not renderable);
  the repo winding/C_r normalization stays [inferred]/[unverified]. The verdict does not depend on it.
- Noise channels not modelled: coherent, leakage/loss/erasure, correlated two-qubit, SPAM asymmetry.
- Reference-size (9×6, 54 sites) runs are beyond the local ceilings; size trends are [inferred].

---

## Q2 comparison (triangular vs square) — summary of this run's data

Produced by `scripts/compare_frustration.py` → `data/frustration_compare.txt` (small-cluster ED,
3×4 periodic, within SCOPE §5 ceilings), locked by `tests/test_triangular.py`. Fills part of Q2's
"done when". Numbers are [measured].

> **Correction (T-19, 2026-10-08):** the 3×4 *square* torus below has an odd periodic length, so it is
> not bipartite and is itself frustrated (h = 0 E/bond −2/3 vs −1 on the bipartite 4×4). Part of the
> −0.667 vs −0.333 contrast is that odd-length frustration. The clean matched contrast is the 4×4 pair
> in the Q2 row above (`docs/q2_frustration.md` A.2–A.3). The caveat is now in the data file and script.

Headline frustration signature at h=0 (classical AFM limit, J<0), using the basis-independent
**ground-state energy per bond** (the h=0 ground state is degenerate, so single-vector ⟨ZZ⟩/M_z are
basis-dependent and not interpreted):
- **square 3×4 periodic:** E/bond = **−0.667** (24 bonds).
- **triangular 3×4 periodic:** E/bond = **−0.333** (36 bonds) — less negative, the geometric
  frustration: each elementary triangle can satisfy only 1 of its 3 AFM bonds.

Field scan (ground state): the triangular **defect density** (frustration-specific, no square
analogue) is ~0 in the ground manifold and rises with h — 4.8e-4 (h=0.1), 4.2e-3 (0.3), 1.7e-2
(0.6), 4.8e-2 (1.0) — consistent with the (h/|J|)² law measured in `data/gauss_law_scaling.txt`.
See the data file for the full table.

**(Superseded 2026-10-08 by handoff/09 Part A, the Q2 row above; kept for the record.) Still thin for full Q2 "done" at the time:** dimer-correlation and winding-distribution contrasts triangular
*vs* a matched square observable, and larger sizes, are not yet tabulated; and the comparison is
ground-state, not yet the dynamical/thermalization contrast (that overlaps Q3, which needs the
MCMC ergodic baseline — not built).

**Interpretation guard — disorder line / floating phase [established].** The project's triangular
embedding ("square + one diagonal") is exactly the J′=J point of the anisotropic model of
Iglovikov et al., PRB 87, 214415 (arXiv:1303.0883) [established], which hosts a Stephenson disorder
line (Néel→incommensurate) and, at larger J′, an incommensurate floating phase with power-law
correlations. The square-vs-triangular two-point ⟨ZZ⟩ contrast may therefore be incommensurate /
non-monotonic and is finite-size-sensitive at these small clusters — do **not** read a clean
"frustration monotonically weakens order" story into it.

**Classical-frontier caveat [established + fetched].** Local observables of Trotterized 2D-Ising
dynamics at ~50–130 qubits are, so far, classically reachable: sparse-Pauli + tensor-network methods
reproduced the 127-qubit kicked-Ising "utility" observables faster and more accurately than the
quantum experiment (Begušić–Gray–Chan, Sci. Adv. 10, eadk4321, arXiv:2308.05077 [established];
corroborated by belief-propagation TN arXiv:2306.14887 and PEPO arXiv:2308.03082 [fetched]). The
project's defensible contribution is therefore the **frustration/sector physics and the
logical-qubit/QEC methodology**, not beyond-classical dynamics. (Whether to reframe the *headline*
around this, or run a classical BP/sparse-Pauli baseline, is a scope decision — review/06 K4.)
