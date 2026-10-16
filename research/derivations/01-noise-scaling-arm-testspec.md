# Frozen-test spec — `src/noise_scaling.py` (6×6 noise-scaling arm)

Status: **APPROVED** by the project lead 2026-10-16 (test-first §A), including D5 below. Oracles come from
`research/derivations/01-noise-scaling-arm.md` (the derivation), `research/07-noise-scaling.md` (KB)
and independent code paths. They never come from the module under test.

## Public interface (signatures only)

```python
# src/noise_scaling.py  (new, additive; verified cores untouched)
PauliModel = Dict[str, float]            # 2q Pauli label ("XI", ..., "ZZ"; 15 keys) -> prob per gate

def prior_model(noise: NoiseRates) -> PauliModel
    # p2*(1-eta)/15 on each of the 15 Paulis, + p2*eta on "ZZ" (the to_stim channel)
def insert_paulis(circuit: Circuit, lam: float, model: PauliModel,
                  rng: np.random.Generator) -> Circuit
    # before every ZZPhase: with prob (lam-1)*model[P] insert 2q Pauli P (one draw per gate); lam >= 1
def fold_circuit(circuit: Circuit, lam: int) -> Circuit
    # every ZZPhase(a) -> ZZPhase(a) [ZZPhase(-a) ZZPhase(a)]*(lam-1)/2 ; lam odd >= 1, else ValueError
def scaled_stim_rates(prog, noise: NoiseRates, lam: float,
                      scope: Sequence[str] = ("rot-zz", "syn-cx")) -> Dict[str, float]
    # first-order {"bare_or_undetected": ..., "detected": ...} per step with scoped noise classes x lam
def run_bare_scaled(d, spins0, *, lam: float, method: str, **run_bare_kwargs) -> NoisyRun
    # method "insert" | "fold": noisy_q3.run_bare semantics at noise scale lam
def slope_test(lams, values, ses) -> SlopeResult        # weighted LSQ slope, se, z, resolved (|z| >= z_min)
def extrapolate_exp(lams, values, ses, asymptote: Optional[float]) -> ExtrapResult
    # O(lam) = B + (O0-B) exp(-g lam); O0 = value at lam=0, its se, chi2, dof, consistent (p >= 0.05)
def hqc_cost(n1q: int, n2q: int, nm: int, shots: int) -> float     # 5 + C(N1+10N2+5Nm)/5000
```

`config.py` gains `NoiseScalingConfig`: lams = (1, 2, 3), fold_lam = 3, z_min = 3.0, the validation
cases, trajectories, and time points.

## Behaviours and oracles

| # | behaviour | oracle (independent of the module) | tolerance, and why |
|---|---|---|---|
| T1 | `insert_paulis(lam=1)` and `model={}` change nothing | exact identity: the command list is equal | exact |
| T2 | insertion statistics on a 3×4 bare step (108·k gates) at λ = 3, prior ×10 | count ~ Binomial(n_gates, (λ−1)·Σq); ZZ share of inserted Paulis = η + (1−η)/15 = 0.1133. Discriminating: λ·q vs (λ−1)·q differ by 50% | 4σ binomial |
| T3 | an inserted Pauli acts as P before the gate | dense numpy, 2 qubits, independent code: forced insertion of each of the 15 P equals P applied to the pre-gate state | 1e-12 (machine) |
| T4 | folding is transparent at zero noise | pytket `get_statevector` of `fold_circuit(c, 3)` equals that of c (3×4 bare, 1 step, 12 qubits); λ = 2 raises ValueError | 1e-10 |
| T5 | folding + RC transparent | `twirl_ensemble(fold_circuit(c,3), 8, seed)` + `frame_readout_flips` reproduces c's Z-readout distribution | 1e-10 |
| T6 | gate counts | fold λ = 3: ZZPhase ×3, 1q count unchanged; insert: N2q unchanged | exact |
| T7 | Stim scaling = rescaled noise | bare 3×4 and 6×6: `scaled_stim_rates(λ=3)` equals the existing `undetected_rate_per_step(bare, NoiseRates(p2=3·p2, …))`, a different path. Derivation value 6×6 bare λ = 3: 0.1987; Iceberg undetected ×3.000 | 1e-9 rel; table values ±1e-4 (printed rounding) |
| T8 | λ = 1 reproduces committed rates | 6×6: 0.0691 / 0.1522 / 0.0259 (`data/q3_size.txt`) | ±1e-4 |
| T9 | exponential extrapolation exact on its own model | synthetic O(λ) = B + (O0−B)e^{−gλ}, noise-free: O0 recovered; chi2 = 0 | 1e-8 |
| T10 | fit inconsistency flagged | synthetic data with a quadratic λ-dependence the model cannot fit, small SE → `consistent=False` | p < 0.05 |
| T11 | Richardson cross-check | `gauss_mitigation.richardson((1,2,3))` = (3, −3, 1); exact on quadratics | 1e-12 |
| T12 | slope test | zero-noise runs at λ ∈ {1,2,3} → slope 0, not resolved; synthetic slope s with se → z = s/se | exact / 1e-12 |
| T13 | HQC formula | (N1, N2, Nm, C) = (36, 108, 36, 100) → 30.92; bare 6×6 n = 32 fold/plain weight ratio 106200/37080 = 2.864 | 1e-12 |
| T14 | **3×4 physics validation** (slow mark) | `run_bare_scaled` at λ ∈ {1,2,3}, both methods, t ≤ 8. On the **raw** flippable density the slope is resolved (z ≥ 3) and the extrapolated O0 is closer to the ideal curve than λ = 1, at ≥ 3 of 4 time points. On the **Gauss-conditioned** one: report, don't assert direction | within batch SE |
| T15 | insert ≈ fold under the symmetric prior | at 3×4, λ = 3, both methods agree on raw flippable density at every t | 3 combined SE |
| T16 | labelling | `data/noise_scaling.txt` header contains "CLASSICAL PREDICTION" and "NOT an H2"; the module never imports the nexus path | string check |

## D5 — the fit's asymptote (DECIDED 2026-10-16: fixed at B_W₀)

An exponential fit through 3 points has 3 parameters (O0, amplitude, rate) and therefore 0 degrees of
freedom. The "middle point tests the fit" promise needs one parameter fixed. Proposed:
- fix the asymptote at the measured 6×6 sector baseline **B_W₀ = 0.3088** (MCMC [measured]);
- reason: under the assumed noise the Gauss-conditioned curves drift toward B_W₀ ([measured] at
  3×3 / 3×4; mechanism [inferred]);
- this leaves 2 parameters and 1 dof, so the χ² test works.

For the raw observable, the asymptote is the full-space infinite-T value (flippable density of a
random spin configuration), which is computable exactly.

**Decision D5 (the project lead, 2026-10-16):** keep the extrapolation, with the asymptote **fixed**:
- conditioned observables: B = B_W₀ (6×6: 0.3088, MCMC [measured]); 3×4 validation uses that lattice's own B_W₀ (0.2667);
- raw observables: the full-space infinite-T value.

Report O0 only when the χ² test is consistent (p ≥ 0.05). The reference's own form, O(0)e^{−bλ} with asymptote 0, is
rejected for densities as biased [derived]. Fallback if the HQC budget is tight: diagnostic only, on λ = {1, 3}.

## Amendment D6 (approved by the project lead, 2026-10-16), re-frozen

- **T4, T5** run on the 3×3 torus (9 qubits) instead of 3×4. pytket 2.18.4 `get_statevector` raises "too many qubits" above 11 [measured]. Same oracle and assertions; only the lattice changes.
- **T17, new: the fold survives the H2 compile.** Offline `QuantinuumBackend("H2-1", api_handler=QuantinuumAPIOffline())`, one 3×3 Trotter step (27 ZZ gates).
  - Measured 2Q counts after `get_compiled_circuit`, as (unfolded, folded λ = 3): level 0 **(27, 81)**; level 1 **(27, 27)**; level 2, the default, **(27, 27)**.
  - Oracle: `CONFIG.noise_scaling.compile_opt_level == 0`, the count is ×3 at that level, and equal at level 2 (the discriminating instance).
  - Nothing is submitted.
- Frozen SHA-256 after the amendment: `FED386D4A1BE6B509713E3E1C728288AB91CC8F13C7481D5C31A8C3AE6665EF8` (original: `BAC907FA…26FC`).
