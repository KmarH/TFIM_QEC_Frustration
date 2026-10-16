# 01 — The 6×6 noise-scaling arm (T-17 / R-14): what scaling does, what it costs, what it can see

Status: derivation for `research-flow` Stage 2, 2026-10-16. Feeds the D1–D5 decision cards.
Every rate below is a **classical first-order accounting under the ASSUMED research/06 H2 prior**
(p2 = 6e-4, η = 0.05, p1 = pm = p_init = 6e-5; h = 0.3, dt = 0.25, J = −1). **Not an H2 result.**
Sources are rows of `research/07-noise-scaling.md` (cited by arXiv ID).

## Statement

On the 6×6 triangular torus (N = 36), the arm runs the Q3 circuit at noise scale λ ∈ Λ and reads
the Gauss-conditioned dimer observables O(t; λ). Two uses:
- **diagnostic**: if O(t; λ) is independent of λ within error, the observed value is not noise-driven
  at that t; a resolved slope ∂O/∂λ means it is;
- **estimate**: extrapolate O(t; λ) to λ = 0 (ZNE).

The derivation answers: (a) does folding or Pauli insertion actually scale the error by λ;
(c) how far in t each arm survives at each λ; (d) what slope must be resolved; (e) the HQC cost.

## Assumptions

- A1 [assumed] Device noise after RC is a stochastic Pauli channel per gate location (D-RC; 1512.01098).
- A2 [assumed] The research/06 prior as above; no idle, leakage, crosstalk.
- A3 [established, 2005.10921] Unitary folding G → G(G†G)^k gives nominal λ = 2k+1 and scales only folded gates; SPAM is not scaled.
- A4 [established, 2503.20870 §VII.2] The reference amplified by **Pauli insertion**: Paulis drawn from a learned 2Q noise model (averaged over U_ZZ(±2J dt)) inserted with probability (α−1)p_j before 2Q gates only; two-point exponential fit; triangular quench α = 4 nominal, α′ = 8.2 effective, 200 shots per step, leakage post-selection.
- A5 [established, 2305.03828 Fig. 3] H2's ZZPhase(θ) infidelity depends on θ with a nonzero θ→0 floor; the −θ gate's error is not separately published.
- A6 [established, Quantinuum docs via research/07] HQC = 5 + C·(N1q + 10·N2q + 5·Nm)/5000 per circuit, C = shots; Nm counts prep, mid-circuit and final measurements and resets.

## Derivation

**(a) Folding under a Pauli channel.** Let E = Σ_P q_P P·P† follow each gate. In the fold G·G†·G the
faults after G†, and after the inner G, are conjugated by the remaining gates before they rejoin the
unfolded frame. If P commutes with Z⊗Z, conjugation by ZZ(θ) leaves it alone. If it anticommutes,
G P G† = P·exp(iθ ZZ), which after twirling is P with weight cos²θ and P·ZZ with weight sin²θ (A1).
The total first-order rate is conserved by conjugation, so **the twirled total error is ×λ exactly to
first order, for any Pauli channel and any θ**. The **composition** is ×λ only when q_P = q_{P·ZZ} for
every anticommuting P. That holds for uniform depolarizing and for the ZZ-biased prior (A2), and fails
for a generic channel. Under A5 the per-gate rate of the inserted −θ gate is not that of +θ, so on H2
the total is not ×λ either. [derived; A5-based conclusion inferred]

**(b) Pauli insertion.** Inserting P with probability (λ−1)q_P before each 2Q gate gives λ·q_P per
component to first order, with O(q²) composition corrections. It is exact for the *model*, and wrong by
whatever the model misses (A4). It scales neither 1Q nor SPAM nor idle noise. The model is not
available to this project: η and p2 of H2's native gate are G2 / HW-1, still open. [derived]

**Effective λ.** Scaling 2Q locations only gives λ_eff = 1 + f₂(λ−1), where f₂ is the 2Q share of the
fault budget. For bare 6×6 under A2, f₂ = 0.938, so nominal λ = 3 means λ_eff = 2.876. [derived; measured below]

**(c) Survival at 6×6** (Stim first-order rates, scaled per tag class; scratch `fold_rates.py`):

| scope | λ | bare fault/step | Iceberg detect/step | Iceberg undetected/step | t(Iceberg survival 10%) | t(bare clean 10%) |
|---|---|---|---|---|---|---|
| — | 1 | 0.0691 | 0.1522 | 0.0259 | 3.78 | 8.33 |
| logical ZZ only | 3 | 0.1987 | 0.3164 | 0.0778 | 1.82 | 2.90 |
| all 2Q (incl. syndrome CX) | 3 | 0.1987 | 0.4116 | 0.0778 | 1.40 | 2.90 |
| all gates | 3 | 0.2074 | 0.4556 | 0.0778 | 1.26 | 2.78 |

[derived accounting] The Iceberg undetected rate is exactly ×λ in every scope, since all of it
comes from the logical-ZZ locations. *Limit (review A, 2026-10-16):* Stim treats rotations as
identity, so it cannot see the cos²θ / sin²θ mixing of P into P·ZZ derived in (a). The
detected/undetected totals are unaffected, because P and P·ZZ share stabilizer commutation (ZZ is a
logical operator). The trivial-vs-logical split of `undetected_logical` is affected, though, so the
exact ×λ for the Iceberg undetected rate holds for insertion but is only first-order-total for
folding. Dormant under D3 (Iceberg runs at λ = 1); state it if Iceberg is ever scaled. Gauss post-selection on bare: at 3×4 the sector weight p_in
falls at 0.0129/step against a fault rate of 0.0230/step, so ≈ 56% of faults leave the sector.
Applying that fraction at 6×6 [inferred, not computed at 6×6] gives p_in = 10% at t ≈ 15 (λ = 1)
and t ≈ 5.2 (λ_eff = 2.88).
*Note, 2026-10-16 (Stage 5):* `scripts/run_noise_scaling.py` measured the fraction directly as
f_G = 0.617 (400 trajectories, λ = 1 sector decay against the Stim bare rate), not 0.56. With it,
the times become t ≈ 13.5 (λ = 1) and 4.7 (λ = 3). The data file and the docs use the measured value.

**(d) What the diagnostic must resolve.** At 3×4 [measured, `data/q3_noisy.txt`]:
- the Gauss-conditioned bare curve deviates from the ideal conditioned curve by 0.0006–0.007, while
  the raw curve deviates by 0.03–0.20;
- the late-window gap between ideal conditioned and the sector baseline B_W₀ is ≈ 0.015 (0.284 vs
  0.267), and the noise moved it by 0.008.

So noise moves the **raw** observable a lot, and the λ-slope there is trivially resolved. On the
**conditioned** observable it moves O by about 10⁻³–10⁻² per unit λ. At 6×6 the per-step fault
rate is 3× that of 3×4, so the conditioned shift per unit λ is of order 10⁻². That is [inferred],
because 6×6 cannot be simulated. Resolving a slope s over Δλ at z = 3 needs
n_acc ≈ 2(3σ₁/(sΔλ))² accepted shots per λ point, where σ₁ is the per-shot SD of the observable.
σ₁ at 6×6 is [unverified]: it will be measured from ideal 3×4 / 3×6 sampling in Stage 5, not
assumed here.

**Extrapolant.** Under A1 the conditioned observable decays roughly as O₀ + A·e^{−γλt}
[established form, 2005.10921 / 2503.20870 two-point exponential]. With Λ = {1, 3} only a two-point
fit is possible, and its bias is untestable without a third point. Richardson on {1, 2, 3} (c = 3, −3, 1) is
exact for quadratics, but at equal shots per point it amplifies variance by Σc_i² = 19. Matching a
single unmitigated point's SE then takes ≈ 57× the total shots, the same 57× that
`docs/gauss_law_dimers.md` measured. A two-point linear fit on {1, 3} costs Σc² = 2.5, i.e. ≈ 5× the
shots. [derived]

**(e) Cost** (A6, counts measured from the Stim image of the 6×6 programs, scratch `gate_counts.py`):
- **bare** per step: N2q = 108, N1q = 72; per shot N1q += 36 (prep), Nm = 36. So the weight per shot to step n is u(n) = 1152n + 216.
- **Iceberg** per step: N2q = 180 + 80, N1q = 368, Nm = 8 (4 meas + 4 reset). So u(n) ≈ 3008n + prep, i.e. 2.6× bare per step before acceptance.
- **Folding**, 2Q scope: bare u_λ(n) = (72 + 1080λ)n + 216. At λ = 3 that is ×2.864 per circuit (106200/37080 at n = 32).
- **Pauli insertion**: N2q unchanged. The inserted Paulis merge into the RC twirl Paulis already present, so ≈ ×1.0 per circuit. [inferred from the twirl construction]

Worked example (illustrative, not a decision): bare 6×6, eight time points t = 1…8 (n = 4…32),
500 shots each, at λ = 1 → ≈ 1.68×10⁴ HQC. Each additional λ point costs the same again by
insertion, or ≈ 4.8×10⁴ by folding at λ = 3. [derived from A6; shot count assumed]

## Checks

1. **Independent dense 2-qubit check** (numpy, fresh code, scratch `fold_check.py`): twirled
   G·G†·G with the channel after each gate, θ ∈ {0.1, 0.5, 1, π/2}, p = 1e-3.
   - Total error ×2.994–2.997 (second-order deficit): **pass**.
   - Every component exactly ×3 under uniform depolarizing and the η = 0.05 prior: **pass**.
   - Under X⊗I only, weight moves into Y⊗Z by θ (θ = π/2: XI 2.00, YZ 1.00; θ = 0.1: XI 2.98): matches (a).
   - Caveat: uniform depolarizing commutes with every unitary, so it is not a discriminating instance; the X⊗I case is.
2. **Wrapper reproduces the committed numbers**: at λ = 1 every scope gives 0.0691 / 0.1522 / 0.0259, identical to `data/q3_size.txt`: **pass**.
3. **Effective-λ consistency**: 0.1987 / 0.0691 = 2.876 = 1 + 0.938·2: **pass**. The Iceberg undetected rate is ×3.000 in all scopes (limit check: all undetected faults come from ZZ locations): **pass**.
4. **Limit λ → 1**: insertion probability (λ−1)q → 0, folding k = 0. Both are the identity: **pass**, trivially.

None failed.

## Consequences for code (oracles for `test-first`)

- A folded or inserted program at zero noise reproduces the unscaled readout distribution exactly, with RC on and off.
- Stim first-order rate of a scaled program = unscaled + (λ−1)·(the scoped class rates), to round-off.
- Under the prior, 2Q-scope folding scales the bare per-step rate by 1 + 0.938(λ−1) at 6×6, and the Iceberg undetected rate by exactly λ.
- At 3×4, where trajectories exist: Gauss-conditioned O(t; λ) moves with λ by the amount the simulator gives, and the extrapolant reduces |O − O_ideal| below the λ = 1 residual within SE. Do it both ways (fold and insert).
- Every output carries the classical / assumed-noise / not-H2 label.

## Decisions taken on this derivation (the project lead, 2026-10-16)

- **D1** purpose: both, **diagnostic first**. The λ-slope test is the primary output. The λ → 0 extrapolation is reported only when the slope is resolved and the fit is stable.
- **D2** amplification: **Pauli insertion** for the λ ladder (as 2503.20870), plus **one folded λ = 3 point** as a check of the insertion model.
- **D3** arms: **bare + Gauss post-selection** only. Iceberg runs at λ = 1 only.
- **D4** λ = **{1, 2, 3}**, **exponential** fit; the middle point tests the fit, with Richardson as a cross-check.
- **D5** fit asymptote **fixed at B_W₀** (raw observables: the full-space infinite-T value), giving 1 dof and a χ² gate on reporting O0. Literature basis: research/07 Q4/Q5 (the reference's two-point O(0)e^{−bλ}; Kim 2023's 3-point exponential; Cai 2020's multi-exponential bias; Perrin 2024's diagnostic-only precedent).
- Still open: time points and shots per point. They follow from σ₁, which Stage 5 measures.
- **D6** (Stage 5): frozen tests T4/T5 moved to 3×3, because pytket 2.18.4's `get_statevector` caps at 11 qubits. Added T17, which checks that the fold survives the H2 compile. [measured] An offline H2-1 compile at TKET levels 1 and 2 cancels ZZ(a)·ZZ(−a)·ZZ(a) to one gate, while level 0 keeps it. Folded circuits compile at level 0 (`NoiseScalingConfig.compile_opt_level`).
- **D7**: the 6×6 plan covers t = 1–3 at a slope resolution of 0.005. All t = 1–8 would cost ≈ 1.7×10⁶ HQC under the prior. No late-time 6×6 thermalization claim. Recompute once G2 is known.
- σ₁ at 6×6: √N scaling failed its check (σ₁ grows from N = 12 to 18). It is replaced by the MCMC sector-ensemble value times the ideal/ensemble ratio at N = 18; the ratio's transfer to N = 36 is [assumed].
