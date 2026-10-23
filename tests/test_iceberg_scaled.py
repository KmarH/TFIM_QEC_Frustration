"""FROZEN test spec (test-first) for src/noise_scaling.run_iceberg_scaled: the lambda-amplified
ENCODED (Iceberg) trajectory runner. Written BEFORE the function exists; the implementation must
make these pass WITHOUT editing this file.

Decision D6 (project lead, 2026-10-22): the Q3 generalization study's noise-strength axis gets a
real encoded runner, instead of taking Iceberg's lambda dependence from Stim accounting alone.
Until now src/noise_scaling had `run_bare_scaled` only (decision D-NS3 ran Iceberg at lam = 1),
and src/noisy_q3_sweep raised rather than label lam = 1 Iceberg numbers as lam > 1.

Every noisy number here is a CLASSICAL PREDICTION under an ASSUMED noise model
(Pauli-trajectory simulation), never an H2 / hardware result.

Interface under test (black box), mirroring run_bare_scaled:

    run_iceberg_scaled(d, spins0, *, lam, method, J, h, dt, n_steps, noise, n_traj, n_batches,
                       record_every, rng, max_spins, mem_gb=2.0, model=None) -> NoisyRun

SPEC, as decided before implementing:

 S1 Amplification is PAULI INSERTION on the two-qubit gates, the same mechanism and the same
    channel as run_bare_scaled's method="insert": before every 2-qubit gate of the encoded
    circuit (the logical ZZ rotations AND the syndrome-extraction CX gates, i.e. the
    ("rot-zz", "syn-cx") scope of scaled_stim_rates) a Pauli P drawn from `model` is inserted
    with probability (lam - 1) * model[P], one draw per gate. Default model = the prior channel
    of `noise` (src/noise_scaling.prior_model). It scales the 2q channel and nothing else: 1q,
    SPAM and idle noise stay at lam = 1, exactly as insert_paulis documents for the bare arm.
 S2 lam = 1 is a no-op: with the same rng seed the run is BITWISE identical to
    src/noisy_q3.run_iceberg. An implementation that consumes randomness for an insertion that
    cannot happen fails this, and would make the lam ladder's lam = 1 rung incomparable to the
    published data/q3_noisy.txt cell.
 S3 Zero noise stays zero noise: amplifying an all-zero channel inserts nothing, so the encoded
    curve equals the ideal circuit-order curve (transparency, docs/q3_thermalization.md §9.1).
 S4 method: only "insert" is supported. "fold" RAISES NotImplementedError: folding the encoded
    circuit would also fold the syndrome-extraction CX gates, which changes the code's detection
    structure rather than only its error rate; that is a separate design question, not a scope
    this function may silently assume.
 S5 Post-selection responds to amplification: with a weight-1 insertion model the Iceberg
    detectors (distance 2 detects any weight-1 error [established]) must reject more at lam > 1.
 S6 Ceilings are refused before allocating (SCOPE §5, the PHYSICAL register counts), and lam < 1
    is a ValueError.
 S7 First-order cross-check: the measured detector survival at lam agrees with the INDEPENDENT
    Stim first-order prediction exp(-(offset + detected_rate(lam) * steps)) from
    src/noise_scaling.scaled_stim_rates on the same ("rot-zz", "syn-cx") scope — a different code
    path (Stim fault propagation, not trajectories).
 S8 The sweep is wired: src/noisy_q3_sweep.run_noisy_sweep no longer raises for lam > 1 on the
    encoded arm, and returns an Iceberg cell whose acceptance falls with lam.
"""

import math

import numpy as np
import pytest

from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates, detected_total
from src.mcmc_baseline import initial_spins
from src.noise_scaling import _scaled_stim, run_iceberg_scaled
from src.noisy_q3 import make_iceberg, run_iceberg
from src.noisy_q3_sweep import prior_noise, run_noisy_sweep
from src.trotter import circuit_trotter2_step, ising_diagonal

J = CONFIG.q3.J            # -1.0 (config.Q3BaselineConfig)
DT = CONFIG.q3.dt          # 0.25
H = 0.3                    # the working field (DECISIONS.md RESOLVED-1)
CASE = (3, 4, "flippable")  # N = 12 -> 16 physical qubits, the published baseline cell
SEED = 0
SCOPE = ("rot-zz", "syn-cx")   # the 2q classes insertion scales (S1)


def _setup(case=CASE):
    Lx, Ly, kind = case
    d = TriangularDimers(Lx, Ly)
    return d, initial_spins(d, kind)


def _kw(**over):
    kw = {"J": J, "h": H, "dt": DT, "record_every": 1, "max_spins": 24, "mem_gb": 2.0}
    kw.update(over)
    return kw


# --------------------------------------------------------------------------- S2
def test_lam_one_is_bitwise_identical_to_run_iceberg():
    """S2: lam = 1 must not perturb the trajectory stream at all."""
    d, s0 = _setup()
    noise = prior_noise()
    ref = run_iceberg(d, s0, n_steps=4, noise=noise, n_traj=8, n_batches=2,
                      rng=np.random.default_rng(SEED), **_kw())
    got = run_iceberg_scaled(d, s0, lam=1, method="insert", n_steps=4, noise=noise, n_traj=8,
                             n_batches=2, rng=np.random.default_rng(SEED), **_kw())
    assert got.arm == ref.arm
    assert np.array_equal(got.steps, ref.steps)
    assert np.array_equal(got.acc, ref.acc), "lam = 1 changed the accumulated distributions"
    assert np.array_equal(got.wsum, ref.wsum), "lam = 1 changed the post-selection weights"


# --------------------------------------------------------------------------- S3
def _ideal_flippable_curve(d, s0, h, n_steps):
    """Independent ideal reference: circuit-order Strang (X half, ZZ, X half) state vector via
    src/trotter.circuit_trotter2_step, flippable density from src/dimers."""
    psi = np.zeros(1 << d.N, dtype=np.complex128)
    psi[d.product_state_index(s0)] = 1.0
    diag = ising_diagonal(d.N, d.bonds, J)
    flips = sum(d.flippable(s).astype(np.float64) for s in range(d.N)) / d.N
    out = [float(np.abs(psi) ** 2 @ flips)]
    for _ in range(n_steps):
        psi = circuit_trotter2_step(psi, d.N, diag, h, DT)
        out.append(float(np.abs(psi) ** 2 @ flips))
    return np.array(out)


@pytest.mark.parametrize("lam", [1, 3])
def test_zero_noise_equals_ideal_circuit(lam):
    """S3: amplifying an all-zero channel is still the ideal circuit, to 1e-8, at any lam."""
    d, s0 = _setup()
    n_steps = 4
    run = run_iceberg_scaled(d, s0, lam=lam, method="insert", n_steps=n_steps,
                             noise=NoiseRates(), n_traj=2, n_batches=1,
                             rng=np.random.default_rng(SEED), **_kw())
    flips = sum(d.flippable(s).astype(np.float64) for s in range(d.N)) / d.N
    mix = run.mixture()
    ref = _ideal_flippable_curve(d, s0, H, n_steps)
    assert np.allclose(run.acceptance(), 1.0, atol=1e-12), "zero noise lost shots"
    for k, step in enumerate(run.steps):
        got = float(mix[k] @ flips)
        assert abs(got - ref[int(step)]) <= 1e-8, f"lam={lam} step={step}: {got} vs {ref[int(step)]}"


# --------------------------------------------------------------------------- S4, S6
def test_fold_is_refused_on_the_encoded_arm():
    """S4: folding would fold the syndrome CX gates too — out of scope, must raise."""
    d, s0 = _setup()
    with pytest.raises(NotImplementedError):
        run_iceberg_scaled(d, s0, lam=3, method="fold", n_steps=1, noise=prior_noise(), n_traj=1,
                           n_batches=1, rng=np.random.default_rng(SEED), **_kw())


def test_bad_lam_and_method_are_rejected():
    """S6: lam < 1 is a ValueError; an unknown method is a ValueError."""
    d, s0 = _setup()
    for bad in ({"lam": 0.5, "method": "insert"}, {"lam": 2, "method": "stretch"}):
        with pytest.raises(ValueError):
            run_iceberg_scaled(d, s0, n_steps=1, noise=prior_noise(), n_traj=1, n_batches=1,
                               rng=np.random.default_rng(SEED), **bad, **_kw())


def test_physical_ceiling_is_refused_before_allocating():
    """S6: the PHYSICAL register (code + ancillas) is what counts (SCOPE §5). 4x5 -> 24 physical,
    so a 20-spin ceiling must refuse."""
    d, s0 = _setup((4, 5, "flippable"))
    with pytest.raises(Exception) as exc:
        run_iceberg_scaled(d, s0, lam=2, method="insert", n_steps=1, noise=prior_noise(),
                           n_traj=1, n_batches=1, rng=np.random.default_rng(SEED),
                           **_kw(max_spins=20))
    assert "ceiling" in str(exc.value).lower() or "20" in str(exc.value)


# --------------------------------------------------------------------------- S5
def test_weight_one_insertion_model_lowers_acceptance_with_lam():
    """S5: a weight-1 insertion model ('IX' = single X on the gate's second qubit) is exactly what
    a distance-2 code detects, so post-selection must reject more as lam grows. With gate noise
    off, lam = 1 keeps every shot (no insertion at lam = 1, S2)."""
    d, s0 = _setup()
    model = {"IX": 0.02}
    kw = dict(method="insert", n_steps=8, noise=NoiseRates(), n_traj=24, n_batches=4,
              **_kw(record_every=4))
    one = run_iceberg_scaled(d, s0, lam=1, rng=np.random.default_rng(SEED), model=model, **kw)
    amp = run_iceberg_scaled(d, s0, lam=5, rng=np.random.default_rng(SEED), model=model, **kw)
    assert np.allclose(one.acceptance(), 1.0, atol=1e-12), "lam = 1 inserted something"
    a_end = float(amp.acceptance()[-1])
    assert a_end < 1.0 - 5 * math.sqrt(0.25 / 24), f"lam = 5 kept {a_end:.3f} of shots"
    assert np.all(np.diff(amp.acceptance()) <= 1e-12), "survival must be non-increasing in time"


# --------------------------------------------------------------------------- S7
@pytest.mark.slow
@pytest.mark.parametrize("lam", [2, 3])
def test_survival_matches_stim_first_order_prediction(lam):
    """S7: measured detector survival vs the INDEPENDENT Stim first-order prediction on the same
    2q scope (src.encoded_codes.detected_total inside the scaled-image context: prep, steps and
    readout included). First order and the trajectory estimate differ by higher-order terms in
    both directions, and the estimate carries binomial noise, so the band is 3 sigma plus the
    0.05 / 0.20 allowance of the local-sim-vs-Stim agreement already reported in
    docs/q3_thermalization.md §9.2."""
    d, s0 = _setup()
    noise, n_steps, n_traj = prior_noise(), 4, 96
    prog = make_iceberg(d, s0, J, H, DT)
    with _scaled_stim(lam, SCOPE):
        total = float(detected_total(prog, noise, n_steps))
    run = run_iceberg_scaled(d, s0, lam=lam, method="insert", n_steps=n_steps, noise=noise,
                             n_traj=n_traj, n_batches=8, rng=np.random.default_rng(SEED), **_kw())
    acc = float(run.acceptance()[-1])
    pred = math.exp(-total)
    se = math.sqrt(max(acc * (1 - acc), 0.01) / n_traj)
    assert acc <= pred + 3 * se + 0.05, f"lam={lam}: measured {acc:.3f} above first order {pred:.3f}"
    assert acc >= pred - 3 * se - 0.20, f"lam={lam}: measured {acc:.3f} far below {pred:.3f}"


# --------------------------------------------------------------------------- S8
@pytest.mark.slow
def test_sweep_runs_the_encoded_arm_at_lam_above_one():
    """S8: D6 wiring. run_noisy_sweep must no longer raise for lam > 1 on the encoded arm, and the
    encoded acceptance must fall with lam."""
    res = run_noisy_sweep([CASE], [H], [1, 3], n_traj_bare=4, n_traj_ice=16, n_batches=4,
                          seed=SEED, steps=6)
    acc = {}
    for lam in (1, 3):
        cell = res[(*CASE, H, lam)]
        assert cell["ice"] is not None, f"lam={lam} returned no Iceberg arm"
        ice = cell["ice"]
        assert "acceptance" in ice, "the sweep must keep the encoded acceptance (shot cost)"
        acc[lam] = float(np.asarray(ice["acceptance"])[-1])
    assert acc[3] < acc[1], f"acceptance did not fall with lam: {acc}"
