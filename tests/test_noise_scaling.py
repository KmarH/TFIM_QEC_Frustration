"""Frozen tests for src/noise_scaling.py (6x6 noise-scaling arm), written BLIND before the module.

Spec: research/derivations/01-noise-scaling-arm-testspec.md (T1-T16, APPROVED 2026-10-16).
Derivation (oracle values): research/derivations/01-noise-scaling-arm.md.

Every oracle here comes from OUTSIDE src/noise_scaling.py: analytic values, independent dense
numpy, pytket statevectors, the existing Stim path (src/encoded_codes) with rescaled NoiseRates or a
test-local rescaled Stim image, the existing trajectory runner (src/noisy_q3.run_bare), and the
committed numbers in data/q3_size.txt. Every noisy number is a CLASSICAL PREDICTION under the
ASSUMED research/06 H2 prior, NOT an H2 result.

Spec ambiguities resolved here (each also noted at its test):
  A1 ExtrapResult's standard error is the attribute `se` (same name as SlopeResult.se).
  A2 Both standard errors are the UNSCALED weighted-LSQ ones, cov = (J^T W J)^-1 with W = 1/se^2
     (no reduced-chi2 rescaling): the chi2 gate tests consistency separately, and a rescaled se
     would be 0 on noise-free data.
  A3 Pauli labels: label[0] acts on the gate's FIRST qubit (cmd.qubits[0]), as noisy_q3._fault_2q.
  A4 insert_paulis with lam < 1 raises ValueError (the spec says "lam >= 1").
  A5 An inserted Pauli is emitted as 1-qubit gates (T6 requires N2q unchanged); T2 identifies it
     from the gates' unitaries, so X/Y/Z or any phase-equivalent 1q gates are accepted.
  A6 T14: "at >= 3 of 4 time points" applies to both the slope criterion and the closer-to-ideal
     criterion. The fold ladder has only lam in {1, 3} (fold needs odd lam), so its O0 is the
     closed-form two-point exponential with the same fixed B, computed HERE (independent of the
     module); the module's extrapolate_exp is asserted on the insert ladder {1, 2, 3}. The lam = 1
     point is method-independent (no insertion, no folding) and is shared by both ladders.
  A7 T15: compared at the 4 time points t > 0 (t = 0 is before any 2q gate; its SE is 0).
  A8 scaled_stim_rates on the bare program returns "detected" == 0 (no detectors exist).
"""

import ast
import importlib.util
import math
import os
from collections import Counter
from dataclasses import replace

import numpy as np
import pytest
import stim
from pytket import Circuit, OpType
from scipy.optimize import least_squares
from scipy.stats import chi2 as chi2_dist
from src.noise_scaling import (
    extrapolate_exp,
    fold_circuit,
    hqc_cost,
    insert_paulis,
    prior_model,
    run_bare_scaled,
    scaled_stim_rates,
    slope_test,
)

from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates, detected_rate_per_step, to_stim, undetected_rate_per_step
from src.gauss_mitigation import richardson
from src.mcmc_baseline import Shells, initial_spins
from src.noisy_q3 import NoisyRun, TriangularBareTFIM, make_iceberg, run_bare, run_observables
from src.twirl import frame_readout_flips, twirl_ensemble

J, H, DT = -1.0, 0.3, 0.25
PRIOR = NoiseRates(p2=6e-4, p1=6e-5, pm=6e-5, p_init=6e-5, zz_bias=0.05)   # research/06 prior
PRIOR_X10 = NoiseRates(p2=6e-3, p1=6e-4, pm=6e-4, p_init=6e-4, zz_bias=0.05)
LABELS15 = [a + b for a in "IXYZ" for b in "IXYZ" if a + b != "II"]
MAXS = CONFIG.ceilings.ed_max_spins

_I2 = np.eye(2, dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]])
_Z = np.diag([1.0, -1.0]).astype(complex)
PAULI = {"I": _I2, "X": _X, "Y": _Y, "Z": _Z}


# --------------------------------------------------------------------------- #
# Helpers (independent of the module under test)
# --------------------------------------------------------------------------- #
def _zz_angle() -> float:
    """pytket half-turns for exp(+i J dt ZZ): ZZPhase(a) = exp(-i pi a/2 ZZ) -> a = -2 J dt / pi."""
    return -2 * J * DT / np.pi


def _bare_circuit(d: TriangularDimers, n_steps: int = 1, spins0=None,
                  with_rx: bool = True) -> Circuit:
    """Circuit-order Strang step on the triangular torus as a pytket circuit: (X prep on the down
    spins), Rx half, ZZPhase on every bond, Rx half. Non-Clifford angles, so folding with the
    wrong sign or the wrong gate is visible in the statevector."""
    c = Circuit(d.N)
    if spins0 is not None:
        for s, v in enumerate(np.asarray(spins0).reshape(-1)):
            if v < 0:
                c.X(s)
    rx = -H * DT / np.pi                       # exp(+i h dt/2 X) in half-turns
    for _ in range(n_steps):
        if with_rx:
            for q in range(d.N):
                c.Rx(rx, q)
        for i, j in d.bonds:
            c.ZZPhase(_zz_angle(), i, j)
        if with_rx:
            for q in range(d.N):
                c.Rx(rx, q)
    return c


def _sig(c: Circuit):
    return [(cmd.op.type, tuple(float(p) for p in cmd.op.params),
             tuple(q.index[0] for q in cmd.qubits))
            for cmd in c.get_commands()]


def _norm_angle(a: float) -> float:
    """Half-turn angle reduced to (-2, 2] (pytket stores ZZPhase(-a) as 4 - a)."""
    r = math.fmod(float(a), 4.0)
    if r > 2.0:
        r -= 4.0
    if r <= -2.0:
        r += 4.0
    return round(r, 9)


_MAT_CACHE: dict = {}


def _op_matrix(op) -> np.ndarray:
    key = (op.type, tuple(float(p) for p in op.params))
    if key not in _MAT_CACHE:
        c = Circuit(1)
        c.add_gate(op, [0])
        _MAT_CACHE[key] = c.get_unitary()
    return _MAT_CACHE[key]


def _pauli_of(U: np.ndarray) -> str:
    """Single-qubit Pauli label of U up to global phase (fails if U is not a Pauli)."""
    for lab, P in PAULI.items():
        if abs(abs(np.trace(P.conj().T @ U)) / 2 - 1) < 1e-9:
            return lab
    raise AssertionError(f"inserted 1q block is not a Pauli: {U}")


def _inserted_labels(c: Circuit) -> list:
    """For a circuit whose ORIGINAL gates are all ZZPhase, return the 2q Pauli label inserted
    before each ZZPhase (in command order), "II" where none. Tracks pending 1q ops per wire."""
    pending = {q: [] for q in range(c.n_qubits)}
    out = []
    for cmd in c.get_commands():
        qs = [q.index[0] for q in cmd.qubits]
        if cmd.op.type == OpType.ZZPhase:
            lab = ""
            for q in qs:
                U = _I2
                for op in pending[q]:
                    U = _op_matrix(op) @ U
                lab += _pauli_of(U)
                pending[q] = []
            out.append(lab)
        else:
            assert len(qs) == 1, f"inserted op must be 1-qubit (spec: N2q unchanged), got {cmd}"
            pending[qs[0]].append(cmd.op)
    assert all(not v for v in pending.values()), "something was inserted after the last ZZPhase"
    return out


def _scaled_stim_detected(prog, noise: NoiseRates, lam: float, scope) -> float:
    """Independent oracle: the existing Stim image (encoded_codes.to_stim) with every noise
    instruction whose tag class is in `scope` multiplied by lam, then the detected-probability
    slope over steps (1, 2, 3) exactly as encoded_codes.detected_rate_per_step does it."""
    tot = []
    for s in (1, 2, 3):
        src = to_stim(prog.schedule(s, "Z"), noise)
        out = stim.Circuit()
        for ins in src:
            args = ins.gate_args_copy()
            if ins.tag and ins.tag.split(":")[0] in scope:
                args = [a * lam for a in args]
            out.append(stim.CircuitInstruction(ins.name, ins.targets_copy(), args, tag=ins.tag))
        dem = out.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
        tot.append(sum(i.args_copy()[0] for i in dem.flattened() if i.type == "error"
                       and any(t.is_relative_detector_id() for t in i.targets_copy())))
    return float(np.polyfit((1, 2, 3), tot, 1)[0])


def _uniform_run(N: int) -> NoisyRun:
    p = np.full((1, 1, 1 << N), 1.0 / (1 << N))
    return NoisyRun("uniform", np.array([0]), DT, p, np.ones((1, 1)), 1)


@pytest.fixture(scope="module")
def d34():
    d = TriangularDimers(3, 4)
    return d, initial_spins(d, "flippable"), Shells.build(d, 3)


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def test_config_defaults():
    ns = CONFIG.noise_scaling
    assert tuple(ns.lams) == (1, 2, 3)
    assert ns.fold_lam == 3
    assert ns.z_min == 3.0


# --------------------------------------------------------------------------- #
# T1-T3: Pauli insertion
# --------------------------------------------------------------------------- #
def test_t1_insert_identity_cases(d34):
    """lam = 1 (with a large model, so lam*q would insert) and model = {} change nothing."""
    d, s0, _ = d34
    c = _bare_circuit(d, 2, s0)
    big = {k: 0.03 for k in LABELS15}                     # sum 0.45: lam*q would insert ~49 Paulis
    out1 = insert_paulis(c, 1.0, big, np.random.default_rng(1))
    assert _sig(out1) == _sig(c)
    out2 = insert_paulis(c, 3.0, {}, np.random.default_rng(2))
    assert _sig(out2) == _sig(c)
    assert _sig(c) == _sig(_bare_circuit(d, 2, s0))      # input not mutated
    with pytest.raises(ValueError):                       # A4: lam < 1 is refused
        insert_paulis(c, 0.5, big, np.random.default_rng(3))


def test_t2_prior_model_is_the_to_stim_channel():
    m = prior_model(PRIOR)
    assert set(m) == set(LABELS15)
    u = PRIOR.p2 * (1 - PRIOR.zz_bias) / 15
    for k in LABELS15:
        exp = u + (PRIOR.p2 * PRIOR.zz_bias if k == "ZZ" else 0.0)
        assert m[k] == pytest.approx(exp, rel=1e-12, abs=1e-18), k
    assert sum(m.values()) == pytest.approx(PRIOR.p2, rel=1e-12)


def test_t2_insertion_statistics(d34):
    """3x4, 3 bare steps (3 x 36 = 108 ZZ gates per circuit) x K = 1000 independent insertions at
    lam = 3, prior x10 (p2 = 6e-3). Count ~ Binomial(108000, (lam-1) p2 = 0.012): mean 1296,
    sd 35.8, 4 sd = 143; the wrong lam*q gives 1944 (+648). ZZ share of inserted Paulis =
    eta + (1-eta)/15 = 0.1133 (sd 0.0088 at ~1296 draws, 4 sd = 0.035); uniform (1/15 = 0.067) or
    'eta replaces' (0.05) differ by > 0.046. Every one of the 15 labels is checked at 4 sd."""
    d, _, _ = d34
    c = _bare_circuit(d, 3, None, with_rx=False)          # only ZZPhase: every other op is inserted
    n_zz = sum(1 for cmd in c.get_commands() if cmd.op.type == OpType.ZZPhase)
    assert n_zz == 108
    model = prior_model(PRIOR_X10)
    lam, K = 3.0, 1000
    rng = np.random.default_rng(20261016)
    counts: Counter = Counter()
    for _ in range(K):
        labs = _inserted_labels(insert_paulis(c, lam, model, rng))
        assert len(labs) == n_zz
        counts.update(lb for lb in labs if lb != "II")
    n = n_zz * K
    p_ins = (lam - 1) * PRIOR_X10.p2
    total = sum(counts.values())
    assert abs(total - n * p_ins) <= 4 * math.sqrt(n * p_ins * (1 - p_ins)), total
    eta = PRIOR_X10.zz_bias
    share_zz = eta + (1 - eta) / 15
    assert share_zz == pytest.approx(0.1133, abs=1e-4)
    for lb in LABELS15:
        q = share_zz if lb == "ZZ" else (1 - eta) / 15
        assert abs(counts[lb] - total * q) <= 4 * math.sqrt(total * q * (1 - q)), (lb, counts[lb])
    assert set(counts) <= set(LABELS15)


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_t3_inserted_pauli_acts_before_the_gate(order):
    """Forced insertion (model {P: 1}, lam = 2 -> probability 1) of each of the 15 Paulis equals
    P applied to the pre-gate state, by independent dense numpy (qubit 0 = MSB). Both gate
    orientations test A3 (label[0] -> the gate's first qubit). A trailing 1q layer makes
    'inserted before every gate' or 'after the gate' visible."""
    a_zz, r = 0.37, [0.23, -0.61, 0.41, 0.17]
    c = Circuit(2)
    c.Rx(r[0], 0)
    c.Ry(r[1], 1)
    c.Rz(r[2], 0)
    c.ZZPhase(a_zz, *order)
    c.Rx(r[3], 1)

    def rot(P, a):
        return np.cos(np.pi * a / 2) * _I2 - 1j * np.sin(np.pi * a / 2) * P

    pre = np.kron(rot(_Z, r[2]) @ rot(_X, r[0]), rot(_Y, r[1]))
    psi_pre = pre @ np.array([1, 0, 0, 0], dtype=complex)
    zz = np.diag(np.exp(-1j * np.pi * a_zz / 2 * np.array([1, -1, -1, 1])))
    post = np.kron(_I2, rot(_X, r[3]))
    for lab in LABELS15:
        P_on = {order[0]: lab[0], order[1]: lab[1]}
        P = np.kron(PAULI[P_on[0]], PAULI[P_on[1]])
        ref = post @ zz @ P @ psi_pre
        out = insert_paulis(c, 2.0, {lab: 1.0}, np.random.default_rng(5))
        sv = out.get_statevector()
        assert abs(abs(np.vdot(ref, sv)) - 1) < 1e-12, lab
        if lab[0] in "XY" or lab[1] in "XY":              # anticommutes with ZZ ... unless both
            if not (lab[0] in "XY" and lab[1] in "XY"):
                after = post @ P @ zz @ psi_pre           # discriminating: after != before
                assert abs(abs(np.vdot(after, sv)) - 1) > 1e-6, lab


# --------------------------------------------------------------------------- #
# T4-T6: folding
# --------------------------------------------------------------------------- #
def test_t4_fold_is_transparent_and_odd_only():
    # D6 (2026-10-16): 3x3 (9 qubits); pytket 2.18.4 get_statevector caps at 11 qubits, so 3x4
    # could not run. The fold is a per-gate rewrite: lattice size does not change the test.
    d = TriangularDimers(3, 3)
    s0 = initial_spins(d, "3-sublattice")
    c = _bare_circuit(d, 1, s0)                           # 9 qubits, 1 step
    ref = c.get_statevector()
    for lam in (3, 5):
        assert np.max(np.abs(fold_circuit(c, lam).get_statevector() - ref)) < 1e-10, lam
    assert _sig(fold_circuit(c, 1)) == _sig(c)
    for bad in (2, 4, 0, -1):
        with pytest.raises(ValueError):
            fold_circuit(c, bad)


def test_t5_fold_plus_rc_is_transparent():
    """twirl_ensemble(fold_circuit(c, 3), 8, seed) + frame_readout_flips reproduces c's exact
    Z-readout distribution. c uses only H and ZZPhase (the op set src/twirl supports).
    D6 (2026-10-16): on 3x3 (9 qubits), as T4."""
    d = TriangularDimers(3, 3)
    n = d.N
    c = Circuit(n)
    for q in range(n):
        c.H(q)
    for i, j in d.bonds:
        c.ZZPhase(_zz_angle(), i, j)
    for q in range(n):
        c.H(q)
    for i, j in d.bonds[::2]:
        c.ZZPhase(0.29, i, j)
    for q in range(n):
        c.H(q)
    p_ref = np.abs(c.get_statevector()) ** 2
    assert p_ref.max() < 0.9                              # non-trivial distribution
    idx = np.arange(1 << n)
    for inst in twirl_ensemble(fold_circuit(c, 3), 8, seed=11):
        p = np.abs(inst.circuit.get_statevector()) ** 2
        flips = frame_readout_flips(inst.frame, range(n))
        mask = sum(int(f) << (n - 1 - q) for q, f in enumerate(flips))
        p_corr = np.zeros_like(p)
        p_corr[idx ^ mask] = p
        assert np.max(np.abs(p_corr - p_ref)) < 1e-10


def test_t6_gate_counts(d34):
    d, s0, _ = d34
    c = _bare_circuit(d, 2, s0)
    sig = _sig(c)
    n2 = sum(1 for t, _, q in sig if len(q) == 2)
    one_q = Counter((t, p, q) for t, p, q in sig if len(q) == 1)
    zz_orig = Counter((q, _norm_angle(p[0])) for t, p, q in sig if t == OpType.ZZPhase)
    for lam in (3, 5):
        f = _sig(fold_circuit(c, lam))
        assert sum(1 for t, _, q in f if t == OpType.ZZPhase) == lam * n2
        assert sum(1 for t, _, q in f if len(q) == 2) == lam * n2
        assert Counter((t, p, q) for t, p, q in f if len(q) == 1) == one_q     # 1q untouched
        zz_f = Counter((q, _norm_angle(p[0])) for t, p, q in f if t == OpType.ZZPhase)
        k = (lam - 1) // 2
        exp = Counter()
        for (q, a), m in zz_orig.items():
            exp[(q, a)] += (k + 1) * m                     # G (G^dag G)^k: k+1 forward gates
            exp[(q, _norm_angle(-a))] += k * m             # and k inverse gates
        assert zz_f == exp
    heavy = {k: 0.02 for k in LABELS15}                  # (lam-1) sum q = 0.6 per gate
    ins = _sig(insert_paulis(c, 3.0, heavy, np.random.default_rng(4)))
    assert sum(1 for t, _, q in ins if len(q) == 2) == n2
    assert Counter((q, _norm_angle(p[0])) for t, p, q in ins if t == OpType.ZZPhase) == zz_orig
    assert len(ins) > len(sig)                            # ~43 insertions expected on 72 gates
    # the original 1q gates are all still there
    left = Counter((t, p, q) for t, p, q in ins if len(q) == 1)
    assert all(left[k] >= v for k, v in one_q.items())


# --------------------------------------------------------------------------- #
# T7-T8: Stim scaling
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("L", [(3, 4), (6, 6)])
def test_t7_bare_stim_scaling_equals_rescaled_noise(L):
    """Bare: every 2q gate is class rot-zz, so scope x lam == NoiseRates(p2 = lam p2) through the
    existing undetected_rate_per_step path (a different code path). lam = 2 and 3."""
    bare = TriangularBareTFIM(L[0], L[1], "periodic", J, H, DT, 0.0)
    for lam in (2.0, 3.0):
        got = scaled_stim_rates(bare, PRIOR, lam)
        ref = undetected_rate_per_step(bare, replace(PRIOR, p2=lam * PRIOR.p2))["total"]
        assert got["bare_or_undetected"] == pytest.approx(ref, rel=1e-9), lam
        assert abs(got["detected"]) < 1e-15                # A8: no detectors in the bare program
    if L == (6, 6):
        r3 = scaled_stim_rates(bare, PRIOR, 3.0)["bare_or_undetected"]
        assert r3 == pytest.approx(0.1987, abs=1e-4)


def test_t7_iceberg_stim_scaling_6x6():
    """Iceberg 6x6: undetected exactly x lam (all of it comes from logical-ZZ locations) and equal
    to the rescaled-NoiseRates path; detected equals a test-local rescaled Stim image, scope by
    scope; derivation table: 0.4116 (rot-zz + syn-cx), 0.3164 (rot-zz only), undetected 0.0778."""
    d = TriangularDimers(6, 6)
    ice = make_iceberg(d, initial_spins(d, "3-sublattice"), J, H, DT)
    u1 = undetected_rate_per_step(ice, PRIOR)["total"]
    got = scaled_stim_rates(ice, PRIOR, 3.0)
    assert got["bare_or_undetected"] == pytest.approx(3.0 * u1, rel=1e-9)
    ref_u = undetected_rate_per_step(ice, replace(PRIOR, p2=3 * PRIOR.p2))["total"]
    assert got["bare_or_undetected"] == pytest.approx(ref_u, rel=1e-9)
    assert got["bare_or_undetected"] == pytest.approx(0.0778, abs=1e-4)
    ref_d = _scaled_stim_detected(ice, PRIOR, 3.0, ("rot-zz", "syn-cx"))
    assert got["detected"] == pytest.approx(ref_d, rel=1e-9)
    assert got["detected"] == pytest.approx(0.4116, abs=1e-4)
    got_zz = scaled_stim_rates(ice, PRIOR, 3.0, scope=("rot-zz",))
    assert got_zz["detected"] == pytest.approx(_scaled_stim_detected(ice, PRIOR, 3.0, ("rot-zz",)),
                                               rel=1e-9)
    assert got_zz["detected"] == pytest.approx(0.3164, abs=1e-4)
    assert got_zz["bare_or_undetected"] == pytest.approx(3.0 * u1, rel=1e-9)


def test_t8_lambda_one_reproduces_committed_rates():
    """data/q3_size.txt, 6x6 row: bare 0.0691, Iceberg detect 0.1522, undetected 0.0259."""
    d = TriangularDimers(6, 6)
    bare = TriangularBareTFIM(6, 6, "periodic", J, H, DT, 0.0)
    ice = make_iceberg(d, initial_spins(d, "3-sublattice"), J, H, DT)
    rb = scaled_stim_rates(bare, PRIOR, 1.0)
    ri = scaled_stim_rates(ice, PRIOR, 1.0)
    assert rb["bare_or_undetected"] == pytest.approx(0.0691, abs=1e-4)
    assert ri["detected"] == pytest.approx(0.1522, abs=1e-4)
    assert ri["bare_or_undetected"] == pytest.approx(0.0259, abs=1e-4)
    assert ri["detected"] == pytest.approx(detected_rate_per_step(ice, PRIOR), rel=1e-9)


# --------------------------------------------------------------------------- #
# T9-T12: fits and the slope test
# --------------------------------------------------------------------------- #
def _exp_model(lams, O0, g, B):
    return B + (O0 - B) * np.exp(-g * np.asarray(lams, dtype=float))


def _unscaled_se_O0(lams, O0, g, B, ses):
    """A2: se of O0 from (J^T W J)^-1 at the solution, params (O0, g), analytic Jacobian."""
    lam = np.asarray(lams, dtype=float)
    e = np.exp(-g * lam)
    Jm = np.column_stack([e, -(O0 - B) * lam * e]) / np.asarray(ses)[:, None]
    return float(math.sqrt(np.linalg.inv(Jm.T @ Jm)[0, 0]))


@pytest.mark.parametrize("lams", [(1, 2, 3), (1, 2, 3, 5)])
def test_t9_exp_extrapolation_exact_on_its_model(lams):
    """Noise-free data on O = B + (O0-B) e^{-g lam} with B FIXED (D5): O0 recovered, chi2 = 0,
    dof = n - 2. B != 0, so the reference's asymptote-0 form would give a different O0."""
    O0, g, B = 0.284, 0.37, 0.2667
    ses = np.array([0.004, 0.006, 0.009, 0.012][: len(lams)])
    vals = _exp_model(lams, O0, g, B)
    r = extrapolate_exp(lams, vals, ses, asymptote=B)
    assert r.O0 == pytest.approx(O0, abs=1e-8)
    assert r.chi2 == pytest.approx(0.0, abs=1e-8)
    assert r.dof == len(lams) - 2
    assert bool(r.consistent)
    assert r.se == pytest.approx(_unscaled_se_O0(lams, O0, g, B, ses), rel=1e-4)    # A1, A2


def test_t10_fit_inconsistency_is_flagged():
    """Data an exponential with fixed B cannot follow (non-monotone; accelerating decline), small
    SE -> consistent False; 'consistent' is exactly p = chi2.sf(chi2, dof) >= 0.05."""
    lams = (1, 2, 3)
    cases = [
        ([0.35 + 0.08 * x - 0.02 * x * x for x in lams], 0.30),     # 0.41, 0.43, 0.41
        ([0.50 - 0.01 * x - 0.02 * x * x for x in lams], 0.10),     # 0.47, 0.40, 0.29
    ]
    for vals, B in cases:
        r = extrapolate_exp(lams, np.array(vals), np.full(3, 1e-3), asymptote=B)
        assert r.dof == 1
        assert chi2_dist.sf(r.chi2, r.dof) < 0.05
        assert not r.consistent
    # and a consistent case: on-model data shifted by < 1 SE
    vals = _exp_model(lams, 0.40, 0.5, 0.2) + np.array([0.5e-3, -0.4e-3, 0.3e-3])
    r = extrapolate_exp(lams, vals, np.full(3, 1e-3), asymptote=0.2)
    assert bool(r.consistent) == bool(chi2_dist.sf(r.chi2, r.dof) >= 0.05)
    assert r.consistent


def test_t11_richardson_cross_check():
    c = richardson((1, 2, 3))
    assert np.max(np.abs(c - np.array([3.0, -3.0, 1.0]))) < 1e-12
    assert float(np.sum(c ** 2)) == pytest.approx(19.0, abs=1e-12)
    for a, b, q in [(0.3, -0.05, 0.007), (-1.2, 0.4, -0.3)]:
        f = [a + b * x + q * x * x for x in (1, 2, 3)]
        assert float(c @ f) == pytest.approx(a, abs=1e-12)


def _wls(lams, y, se):
    w = 1 / np.asarray(se, dtype=float) ** 2
    lam, y = np.asarray(lams, dtype=float), np.asarray(y, dtype=float)
    lb, yb = (w * lam).sum() / w.sum(), (w * y).sum() / w.sum()
    sxx = (w * (lam - lb) ** 2).sum()
    return (w * (lam - lb) * (y - yb)).sum() / sxx, 1 / math.sqrt(sxx)


def test_t12_slope_test_synthetic():
    """Weighted LSQ slope, unscaled se (A2), z = slope/se, resolved = |z| >= z_min = 3. Data not
    collinear and SEs unequal, so unweighted or chi2-rescaled versions give different numbers."""
    lams = (1, 2, 3)
    ses = np.array([0.002, 0.004, 0.003])
    base = np.array([0.0, 0.0012, -0.0007])
    _, se0 = _wls(lams, base, ses)
    for z_target, resolved in [(2.9, False), (3.1, True), (-5.0, True), (-1.0, False)]:
        vals = 0.25 + base + (z_target * se0 - _wls(lams, base, ses)[0]) * np.array(lams)
        s_ref, se_ref = _wls(lams, vals, ses)
        r = slope_test(lams, vals, ses)
        assert r.slope == pytest.approx(s_ref, abs=1e-12)
        assert r.se == pytest.approx(se_ref, rel=1e-12)
        assert r.z == pytest.approx(s_ref / se_ref, rel=1e-12)
        assert r.z == pytest.approx(z_target, rel=1e-9)
        assert bool(r.resolved) is resolved


def test_t12_zero_noise_runs_have_no_slope(d34):
    """At zero noise every lam and method reproduces the ideal run_bare mixture, so the slope of
    the raw flippable density is 0 and not resolved (nominal SE 0.01: zero-noise runs have none)."""
    d, s0, sh = d34
    kw = dict(J=J, h=H, dt=DT, n_steps=8, noise=NoiseRates(), n_traj=2, n_batches=1, record_every=4,
              max_spins=MAXS)
    ideal = run_bare(d, s0, rng=np.random.default_rng(0), **kw).mixture()
    vals = []
    for lam in (1, 2, 3):
        run = run_bare_scaled(d, s0, lam=lam, method="insert", rng=np.random.default_rng(lam), **kw)
        assert np.max(np.abs(run.mixture() - ideal)) < 1e-10
        vals.append(run_observables(d, s0, sh, run, MAXS).raw["flippable_density"][0])
    for lam in (1, 3):
        run = run_bare_scaled(d, s0, lam=lam, method="fold", rng=np.random.default_rng(9), **kw)
        assert np.max(np.abs(run.mixture() - ideal)) < 1e-10
    vals = np.array(vals)
    for t in range(1, vals.shape[1]):
        r = slope_test((1, 2, 3), vals[:, t], np.full(3, 0.01))
        assert abs(r.slope) < 1e-12 and abs(r.z) < 1e-9
        assert not r.resolved


# --------------------------------------------------------------------------- #
# T13: HQC cost
# --------------------------------------------------------------------------- #
def test_t13_hqc_formula_and_fold_ratio():
    assert hqc_cost(36, 108, 36, 100) == pytest.approx(30.92, abs=1e-12)
    # counts from the 6x6 bare step, plain and folded (fold_circuit itself)
    d = TriangularDimers(6, 6)
    step = _sig(_bare_circuit(d, 1))
    fstep = _sig(fold_circuit(_bare_circuit(d, 1), 3))
    n1, n2 = (sum(1 for *_, q in step if len(q) == k) for k in (1, 2))
    f1, f2 = (sum(1 for *_, q in fstep if len(q) == k) for k in (1, 2))
    assert (n1, n2, f1, f2) == (72, 108, 72, 324)
    n, C = 32, 500

    def weight(n1q, n2q):            # (hqc - 5) * 5000 / C = N1 + 10 N2 + 5 Nm
        return (hqc_cost(n1q * n + 36, n2q * n, 36, C) - 5) * 5000 / C

    assert weight(n1, n2) == pytest.approx(37080, rel=1e-12)
    assert weight(f1, f2) == pytest.approx(106200, rel=1e-12)
    assert weight(f1, f2) / weight(n1, n2) == pytest.approx(106200 / 37080, rel=1e-12)
    assert 106200 / 37080 == pytest.approx(2.864, abs=5e-4)
    # derivation worked example: t = 1..8 (n = 4..32), 500 shots: ~1.68e4 plain, ~4.8e4 folded
    plain = sum(hqc_cost(72 * k + 36, 108 * k, 36, 500) for k in range(4, 33, 4))
    fold = sum(hqc_cost(72 * k + 36, 324 * k, 36, 500) for k in range(4, 33, 4))
    assert plain == pytest.approx(16801.6, rel=1e-12)
    assert fold == pytest.approx(47905.6, rel=1e-12)


# --------------------------------------------------------------------------- #
# T14-T15: 3x4 physics validation (slow)
# --------------------------------------------------------------------------- #
# Sizing [measured with the existing run_bare at the prior, 3x4 flippable, t <= 8, 20 batches]:
# 200 trajectories per lam point give a raw flippable-density batch SE of 0.005-0.008, while the
# raw curve moves by 0.010-0.035 per unit lam (lam = 1 residual vs ideal 0.02-0.07). Slope SE over
# {1, 2, 3} ~ 0.003-0.004 -> z ~ 3 at t = 2 (marginal, hence 3-of-4) and z ~ 5-10 at t = 4..8. A
# p2-rescaled stand-in fit gave |O0 - ideal| = 0.013-0.024 vs |O(1) - ideal| = 0.022-0.073. Cost:
# ~41 ms per trajectory at lam = 1; insert {1,2,3} + fold 3 (ZZ x3, ~2.2x) ~ 1040 trajectory
# equivalents ~ 45 s. T15 at 3 combined SE: SE ~0.009 combined -> tolerance ~0.027, while lam = 1
# vs lam = 3 differ by 0.02-0.065, so the comparison can tell lam = 3 from lam = 1 (asserted).
N_TRAJ, N_BATCH, REC, N_STEPS = 200, 20, 8, 32          # t = 0, 2, 4, 6, 8


@pytest.fixture(scope="module")
def validation(d34):
    d, s0, sh = d34
    kw = dict(J=J, h=H, dt=DT, n_steps=N_STEPS, noise=PRIOR, n_traj=N_TRAJ, n_batches=N_BATCH,
              record_every=REC, max_spins=MAXS)
    obs = {}
    for method, lam, seed in [("insert", 1, 101), ("insert", 2, 102), ("insert", 3, 103),
                              ("fold", 3, 203)]:
        run = run_bare_scaled(d, s0, lam=lam, method=method, rng=np.random.default_rng(seed), **kw)
        assert run.n_traj == N_TRAJ
        obs[(method, lam)] = run_observables(d, s0, sh, run, MAXS)
    obs[("fold", 1)] = obs[("insert", 1)]               # A6: lam = 1 is method-independent
    ideal_run = run_bare(d, s0, rng=np.random.default_rng(0),
                         **{**kw, "noise": NoiseRates(), "n_traj": 1, "n_batches": 1})
    ideal = run_observables(d, s0, sh, ideal_run, MAXS)
    uni = run_observables(d, s0, sh, _uniform_run(d.N), MAXS)
    return obs, ideal, uni


@pytest.mark.slow
def test_t14_3x4_validation(validation):
    obs, ideal, uni = validation
    B_raw = float(uni.raw["flippable_density"][0][0])    # full-space infinite-T value (exact)
    B_cond = float(uni.cond["flippable_density"][0][0])  # uniform over the W0 sector
    assert B_cond == pytest.approx(0.2667, abs=1e-4)     # the spec's 3x4 B_W0
    I_raw = ideal.raw["flippable_density"][0]
    T = range(1, 1 + N_STEPS // REC)
    lam3 = np.array([1.0, 2.0, 3.0])

    def series(method, lams, kind):
        pairs = [getattr(obs[(method, int(lam))], kind)["flippable_density"] for lam in lams]
        return np.array([p[0] for p in pairs]), np.array([p[1] for p in pairs])

    # insert ladder {1, 2, 3}: module slope test + module extrapolation
    v, s = series("insert", lam3, "raw")
    resolved = closer = 0
    for t in T:
        r = slope_test(lam3, v[:, t], s[:, t])
        e = extrapolate_exp(lam3, v[:, t], s[:, t], asymptote=B_raw)
        # independent fit of the same model (scipy, fresh code) must agree with the module
        y_t, s_t = v[:, t], s[:, t]
        fit = least_squares(lambda p, y=y_t, w=s_t: (_exp_model(lam3, p[0], p[1], B_raw) - y) / w,
                            [y_t[0], 0.3], xtol=1e-15, ftol=1e-15, gtol=1e-15)
        assert e.O0 == pytest.approx(fit.x[0], abs=1e-6)
        resolved += bool(r.resolved) and r.z < 0         # noise lowers the raw density
        closer += abs(e.O0 - I_raw[t]) < abs(v[0, t] - I_raw[t])
        print(f"[insert raw] t={t * REC * DT}: O(1..3)={v[:, t]} z={r.z:.2f} O0={e.O0:.4f}"
              f"+-{e.se:.4f} chi2={e.chi2:.2f} ok={e.consistent} ideal={I_raw[t]:.4f}")
    assert resolved >= 3
    assert closer >= 3

    # fold ladder {1, 3}: module slope test; closed-form two-point exponential (A6)
    lf = np.array([1.0, 3.0])
    v, s = series("fold", lf, "raw")
    resolved = closer = 0
    for t in T:
        r = slope_test(lf, v[:, t], s[:, t])
        ratio = (v[1, t] - B_raw) / (v[0, t] - B_raw)
        assert ratio > 0
        O0 = B_raw + (v[0, t] - B_raw) / math.sqrt(ratio)
        resolved += bool(r.resolved) and r.z < 0
        closer += abs(O0 - I_raw[t]) < abs(v[0, t] - I_raw[t])
        print(f"[fold raw] t={t * REC * DT}: O(1,3)={v[:, t]} z={r.z:.2f} O0={O0:.4f}")
    assert resolved >= 3
    assert closer >= 3

    # Gauss-conditioned: report only, no direction asserted (spec T14)
    v, s = series("insert", lam3, "cond")
    I_cond = ideal.cond["flippable_density"][0]
    for t in T:
        r = slope_test(lam3, v[:, t], s[:, t])
        e = extrapolate_exp(lam3, v[:, t], s[:, t], asymptote=B_cond)
        assert np.isfinite(r.z)
        print(f"[insert cond] t={t * REC * DT}: O(1..3)={v[:, t]} z={r.z:.2f} O0={e.O0:.4f} "
              f"chi2={e.chi2:.2f} ok={e.consistent} ideal={I_cond[t]:.4f} "
              "(CLASSICAL prediction, assumed noise)")


@pytest.mark.slow
def test_t15_insert_agrees_with_fold_under_the_symmetric_prior(validation):
    obs, _, _ = validation
    vi, si = obs[("insert", 3)].raw["flippable_density"]
    vf, sf = obs[("fold", 3)].raw["flippable_density"]
    v1, s1 = obs[("insert", 1)].raw["flippable_density"]
    T = range(1, 1 + N_STEPS // REC)                     # A7: the 4 time points t > 0
    for t in T:
        assert abs(vi[t] - vf[t]) <= 3 * math.hypot(si[t], sf[t]), (t, vi[t], vf[t])
    # power: at this size the same comparison separates lam = 3 (fold) from lam = 1
    assert sum(abs(vf[t] - v1[t]) > 3 * math.hypot(sf[t], s1[t]) for t in T) >= 2


# --------------------------------------------------------------------------- #
# T16: labelling and the hardware path
# --------------------------------------------------------------------------- #
def test_t16_module_never_references_the_nexus_path():
    spec = importlib.util.find_spec("src.noise_scaling")
    assert spec is not None and spec.origin
    with open(spec.origin, encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source)
    banned_mods = ("nexus", "qnexus", "quantinuum")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert not any(b in a.name.lower() for b in banned_mods), a.name
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").lower()
            assert not any(b in mod for b in banned_mods), mod
            for a in node.names:
                assert "nexus" not in a.name.lower(), a.name
                if mod.endswith("backends_qc"):
                    # StateVector & co. are fine; the backend dispatcher / hardware gate are not
                    assert a.name not in ("run", "*", "HardwareConfig"), a.name
        elif isinstance(node, ast.Name):
            assert "nexus" not in node.id.lower(), node.id
        elif isinstance(node, ast.Attribute):
            assert "nexus" not in node.attr.lower(), node.attr
            assert node.attr != "allow_hardware"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value.strip().lower() != "nexus"          # no backend="nexus" selection
        elif isinstance(node, ast.keyword):
            assert node.arg not in ("allow_hardware", "approval", "max_cost_hqc"), node.arg
    assert "allow_hardware=True" not in source.replace(" ", "")


def test_t16_data_file_is_labelled():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data",
                        "noise_scaling.txt")
    if not os.path.exists(path):
        pytest.skip("data/noise_scaling.txt not generated yet")
    with open(path, encoding="utf-8") as fh:
        head = "".join(fh.readline() for _ in range(20))
    assert "CLASSICAL PREDICTION" in head
    assert "NOT an H2" in head


def test_t17_fold_survives_h2_compilation():
    """T17 / D6: the fold survives compilation for H2. Quantinuum's compiler optimises by default
    (optimisation_level=2), and an optimiser can cancel G.G^dag.G back to G, silently turning a
    folded lambda=3 run into lambda=1. Hazard checked here: at level 2 the folded circuit compiles
    to the same two-qubit count as the unfolded one; at the pinned level
    (CONFIG.noise_scaling.compile_opt_level == 0) the count is exactly 3x. Offline backend only:
    no login, no network, nothing submitted; only get_compiled_circuit is called. The import must
    not be skipped: the project pins pytket-quantinuum."""
    from pytket.extensions.quantinuum import QuantinuumAPIOffline, QuantinuumBackend

    backend = QuantinuumBackend("H2-1", api_handler=QuantinuumAPIOffline())
    level = CONFIG.noise_scaling.compile_opt_level
    assert level == 0

    d = TriangularDimers(3, 3)
    c = _bare_circuit(d, 1, initial_spins(d, "3-sublattice"))
    folded = fold_circuit(c, 3)

    def n2(circ: Circuit, opt: int) -> int:
        return backend.get_compiled_circuit(circ.copy(), optimisation_level=opt).n_2qb_gates()

    base0, fold0 = n2(c, level), n2(folded, level)
    assert base0 > 0
    assert fold0 == 3 * base0, (base0, fold0)

    base2, fold2 = n2(c, 2), n2(folded, 2)
    assert fold2 == base2, (base2, fold2)    # the default level cancels the fold
