"""FROZEN tests (test-first, blind) for Phase 2: src/h2_q3.py and the "Q3-*" groups of src/h2_driver.py.

Nothing here touches the network, Nexus or HQC: every function under test is offline. Any HQC number
is an OFFLINE estimate, never a quote and never an H2 result; every distribution here is a noiseless
classical computation.

Oracles are independent of the code under test:
  - a dense NumPy Strang step built here from kron/diagonal matrices (H = -J sum ZZ - h sum X,
    exp(+i h dt/2 X) per site, exp(+i J dt Z_i Z_j) per bond, qubit 0 = most significant bit);
  - pytket's own Circuit.get_statevector() (caps at 11 qubits in pytket 2.18.4, so used at 3x3) and
    a small command interpreter written HERE that applies pytket's own Op.get_unitary() matrices
    (cross-checked against get_statevector at 3x3 before it is trusted at 3x4 / 3x6 / 16 qubits);
    for circuits with mid-circuit measure/reset/conditionals it branches exactly on every
    non-deterministic outcome and defers the final data readout to the exact |amp|^2, so the
    transparency check is sampling-free;
  - hand distributions and hand masks for the observables; src.noise_scaling's own insert/fold
    functions for the exact-equality checks; binomial 4-sigma bounds for insertion statistics.

src.h2_q3 is imported inside fixtures, so this file collects before the module exists.
"""

import importlib
import math
from collections import Counter

import numpy as np
import pytest
from pytket import Bit, Circuit, OpType

from config import CONFIG
from src.dimers import TriangularDimers
from src.h2_circuits import CodesLayout, hqc_estimate, native_counts, two_qubit_count
from src.lattice import triangular_bonds
from src.mcmc_baseline import Shells, initial_spins
from src.noise_scaling import fold_circuit, insert_paulis
from src.trotter_threshold import observable_function

J0, H0, DT0 = -1.0, 0.3, 0.25  # the Q3 working point (CONFIG.q3.J, q3.noisy_h, q3.dt)
OBS = ("flippable_density", "C1", "defect_density", "memory")
Q3_GROUPS = ("Q3-bare", "Q3-iceberg", "Q3-ladder", "Q3-bare-3x6")
SHOTS = 1003  # not a multiple of insert_instances: catches shots // k vs rounding


@pytest.fixture(scope="module")
def q3():
    return importlib.import_module("src.h2_q3")


# =========================================================================== oracles
def _spin_index(spins) -> int:
    """Row-major, spin -1 = bit 1, qubit 0 = MSB (written here, not src.dimers)."""
    s = np.asarray(spins).reshape(-1)
    n = len(s)
    return int(sum(((1 - int(v)) // 2) << (n - 1 - q) for q, v in enumerate(s)))


def _dense_state(Lx, Ly, spins0, n_steps, J, h, dt) -> np.ndarray:
    """Dense NumPy circuit-order Strang evolution: X half / ZZ on every bond / X half."""
    N = Lx * Ly
    idx = np.arange(1 << N)
    z = [1 - 2 * ((idx >> (N - 1 - q)) & 1) for q in range(N)]
    E = np.zeros(1 << N)
    for i, j in triangular_bonds(Lx, Ly, "periodic"):
        E += z[i] * z[j]
    zz_phase = np.exp(1j * J * dt * E)  # exp(+i J dt sum Z_i Z_j)
    a = h * dt / 2
    xh = np.array([[np.cos(a), 1j * np.sin(a)], [1j * np.sin(a), np.cos(a)]])  # exp(+i a X)
    psi = np.zeros(1 << N, dtype=complex)
    psi[_spin_index(spins0)] = 1.0

    def xlayer(v):
        t = v.reshape((2,) * N)
        for q in range(N):
            t = np.moveaxis(np.tensordot(xh, t, axes=([1], [q])), 0, q)
        return t.reshape(-1)

    for _ in range(n_steps):
        psi = xlayer(zz_phase * xlayer(psi))
    return psi


def _apply(psi, U, qs):
    m = len(qs)
    t = np.moveaxis(psi, qs, list(range(m)))
    sh = t.shape
    t = (U @ t.reshape(1 << m, -1)).reshape(sh)
    return np.moveaxis(t, list(range(m)), qs)


def _qidx(q) -> int:
    assert q.reg_name == "q"
    return q.index[0]


_SKIP = (OpType.Barrier,)


def _run_unitary(c: Circuit) -> np.ndarray:
    """Statevector of `c` with its Measure commands ignored (they must be final), from pytket's
    per-op unitaries; |0...0> start, qubit 0 = MSB (pytket's ILO-BE)."""
    n = c.n_qubits
    perm = c.implicit_qubit_permutation()
    assert all(k == v for k, v in perm.items()), "implicit qubit permutation not handled"
    last = {}
    for i, cmd in enumerate(c.get_commands()):
        for q in cmd.qubits:
            last[q] = i
    psi = np.zeros((2,) * n, dtype=complex)
    psi[(0,) * n] = 1.0
    for i, cmd in enumerate(c.get_commands()):
        t = cmd.op.type
        if t == OpType.Measure:
            assert last[cmd.qubits[0]] == i, "mid-circuit measurement in a bare circuit"
            continue
        if t in _SKIP:
            continue
        assert t not in (OpType.Reset, OpType.Conditional), t
        psi = _apply(psi, cmd.op.get_unitary(), [_qidx(q) for q in cmd.qubits])
    return psi.reshape(-1)


def _strip_measures(c: Circuit) -> Circuit:
    out = Circuit(c.n_qubits)
    for cmd in c.get_commands():
        if cmd.op.type != OpType.Measure:
            out.add_gate(cmd.op, cmd.args)
    return out


def _exact_codes(c: Circuit, layout: CodesLayout, k: int):
    """Exact zero-noise evaluation of a Z-prep codes circuit: branches on every non-deterministic
    mid-circuit measure/reset outcome, defers each qubit's FINAL measurement to |amp|^2. Returns
    (acceptance, p_logical accepted & renormalised over 2^k, qubit 0 = MSB)."""
    n = c.n_qubits
    cmds = c.get_commands()
    key = {b: i for i, b in enumerate(layout.cbits)}
    last = {}
    for i, cmd in enumerate(cmds):
        for q in cmd.qubits:
            last[q] = i
    psi0 = np.zeros((2,) * n, dtype=complex)
    psi0[(0,) * n] = 1.0
    branches = [(1.0, psi0, {})]
    deferred = {}

    def split(psi, q):
        s0 = [slice(None)] * n
        s1 = [slice(None)] * n
        s0[q], s1[q] = 0, 1
        p1 = float(np.sum(np.abs(psi[tuple(s1)]) ** 2))
        out = []
        for v, pv, keep in ((0, 1 - p1, tuple(s0)), (1, p1, tuple(s1))):
            if pv > 1e-12:
                new = np.zeros_like(psi)
                new[keep] = psi[keep] / math.sqrt(pv)
                out.append((v, pv, new))
        return out

    X = np.array([[0, 1], [1, 0]], dtype=complex)
    for i, cmd in enumerate(cmds):
        t = cmd.op.type
        if t in _SKIP:
            continue
        if t == OpType.Measure:
            q = _qidx(cmd.qubits[0])
            kb = key[cmd.bits[0]]
            if last[cmd.qubits[0]] == i:
                deferred[kb] = q
                continue
            branches = [(w * pv, s, {**bits, kb: v}) for w, psi, bits in branches
                        for v, pv, s in split(psi, q)]
        elif t == OpType.Reset:
            q = _qidx(cmd.qubits[0])
            branches = [(w * pv, _apply(s, X, [q]) if v else s, bits) for w, psi, bits in branches
                        for v, pv, s in split(psi, q)]
        elif t == OpType.Conditional:
            op = cmd.op
            cbits = cmd.args[: op.width]
            U = op.op.get_unitary()
            qs = [_qidx(q) for q in cmd.qubits]
            nb = []
            for w, psi, bits in branches:
                val = sum(bits[key[b]] << j for j, b in enumerate(cbits))
                nb.append((w, _apply(psi, U, qs) if val == op.value else psi, bits))
            branches = nb
        else:
            U = cmd.op.get_unitary()
            qs = [_qidx(q) for q in cmd.qubits]
            branches = [(w, _apply(psi, U, qs), bits) for w, psi, bits in branches]
        assert len(branches) <= 64, "unexpectedly many random mid-circuit outcomes"
    idx = np.arange(1 << n)
    acc_total = 0.0
    p_log = np.zeros(1 << k)
    for w, psi, bits in branches:
        probs = w * np.abs(psi.reshape(-1)) ** 2

        def val(kb, bits=bits):
            if kb in bits:
                return np.full(1 << n, bits[kb], dtype=np.int64)
            return (idx >> (n - 1 - deferred[kb])) & 1

        ok = np.ones(1 << n, dtype=bool)
        for det in layout.detectors:
            ok &= (sum(val(kb) for kb in det) % 2) == 0
        lidx = np.zeros(1 << n, dtype=np.int64)
        for l, ks in enumerate(layout.logicals):
            lidx |= ((sum(val(kb) for kb in ks) % 2) << (k - 1 - l))
        acc_total += float(probs[ok].sum())
        np.add.at(p_log, lidx[ok], probs[ok])
    return acc_total, p_log / acc_total


def _sig(c: Circuit) -> Counter:
    return Counter((str(cmd.op), tuple(repr(a) for a in cmd.args)) for cmd in c.get_commands())


def _n_ops(c: Circuit, typ) -> int:
    return sum(1 for cmd in c.get_commands() if cmd.op.type == typ)


def _spins(Lx, Ly, kind):
    d = TriangularDimers(Lx, Ly)
    return d, initial_spins(d, kind, 20)


# =========================================================================== (a) bare circuit
def test_interpreter_matches_pytket_statevector_3x3(q3):
    """Oracle: pytket get_statevector (<= 11 qubits) == this file's interpreter == dense NumPy, 3x3."""
    _d, s0 = _spins(3, 3, "3-sublattice")
    c, _ = q3.triangular_bare_h2_circuit(3, 3, s0, 2, J0, H0, DT0)
    bare = _strip_measures(c)
    sv = bare.get_statevector()
    assert np.max(np.abs(_run_unitary(c) - sv)) < 1e-10
    ref = _dense_state(3, 3, s0, 2, J0, H0, DT0)
    assert abs(abs(np.vdot(ref, sv)) - 1) < 1e-9


@pytest.mark.parametrize("n_steps", [0, 1, 2])
def test_bare_3x4_matches_dense_numpy(q3, n_steps):
    """Oracle: dense NumPy Strang step -- statevector up to global phase and probabilities to 1e-9."""
    _d, s0 = _spins(3, 4, "flippable")
    c, _cbits = q3.triangular_bare_h2_circuit(3, 4, s0, n_steps, J0, H0, DT0)
    assert c.n_qubits == 12
    psi = _run_unitary(c)
    ref = _dense_state(3, 4, s0, n_steps, J0, H0, DT0)
    assert abs(abs(np.vdot(ref, psi)) - 1) < 1e-9
    assert np.max(np.abs(np.abs(psi) ** 2 - np.abs(ref) ** 2)) < 1e-9
    if n_steps == 0:
        p = np.abs(psi) ** 2
        assert p[_spin_index(s0)] == pytest.approx(1.0, abs=1e-12)


def test_bare_bit_order_discriminates(q3):
    """Oracle: hand index -- an asymmetric 3x4 state lands on its MSB-first index, not the reversed one."""
    d, s0 = _spins(3, 4, "flippable")
    i0 = _spin_index(s0)
    rev = int(format(i0, "012b")[::-1], 2)
    assert rev != i0  # the instance is discriminating
    assert i0 == d.product_state_index(s0)  # the hand convention is the repo's
    c, _ = q3.triangular_bare_h2_circuit(3, 4, s0, 0, J0, H0, DT0)
    p = np.abs(_run_unitary(c)) ** 2
    assert p[i0] == pytest.approx(1.0, abs=1e-12) and p[rev] < 1e-12
    assert _n_ops(c, OpType.X) == int(np.sum(np.asarray(s0) == -1))
    # flat input gives the same circuit statevector as the (Ly, Lx) input
    c_flat, _ = q3.triangular_bare_h2_circuit(3, 4, np.asarray(s0).reshape(-1), 0, J0, H0, DT0)
    assert np.allclose(_run_unitary(c_flat), _run_unitary(c), atol=1e-12)


def test_bare_sign_conventions_discriminate(q3):
    """Oracle: dense NumPy at J=-1 vs J=+1 / h -> -h -- Z probabilities are blind to these signs
    (conjugation x prod Z) [derived], so the statevector overlap must pick the correct one."""
    _d, s0 = _spins(3, 4, "flippable")
    c, _ = q3.triangular_bare_h2_circuit(3, 4, s0, 2, J0, H0, DT0)
    psi = _run_unitary(c)
    good = _dense_state(3, 4, s0, 2, J0, H0, DT0)
    wrongJ = _dense_state(3, 4, s0, 2, -J0, H0, DT0)
    wrongh = _dense_state(3, 4, s0, 2, J0, -H0, DT0)
    assert np.allclose(np.abs(good) ** 2, np.abs(wrongJ) ** 2, atol=1e-12)  # blind in probabilities
    assert abs(abs(np.vdot(good, psi)) - 1) < 1e-9
    assert abs(np.vdot(wrongJ, psi)) < 0.99
    assert abs(np.vdot(wrongh, psi)) < 0.99


def test_bare_structure_and_cbits(q3):
    """Oracle: spec -- per step 2N Rx at ax and one ZZPhase(az) per triangular bond; Measure q -> m[q]."""
    _d, s0 = _spins(3, 4, "flippable")
    n = 3
    c, cbits = q3.triangular_bare_h2_circuit(3, 4, s0, n, J0, H0, DT0)
    assert cbits == [Bit("m", q) for q in range(12)]
    meas = {cmd.qubits[0].index[0]: cmd.bits[0] for cmd in c.get_commands()
            if cmd.op.type == OpType.Measure}
    assert meas == {q: Bit("m", q) for q in range(12)}
    zz = [cmd for cmd in c.get_commands() if cmd.op.type == OpType.ZZPhase]
    az = 2 * (-J0 * DT0) / np.pi
    ax = 2 * (-H0 * DT0 / 2) / np.pi
    assert all(abs(float(z.op.params[0]) - az) < 1e-12 for z in zz)
    pairs = Counter(frozenset(_qidx(q) for q in z.qubits) for z in zz)
    assert pairs == Counter({frozenset(b): n for b in triangular_bonds(3, 4, "periodic")})
    rx = [cmd for cmd in c.get_commands() if cmd.op.type == OpType.Rx]
    assert len(rx) == 2 * 12 * n and all(abs((float(r.op.params[0]) - ax + 2) % 4 - 2) < 1e-12 for r in rx)  # pytket stores angles mod 4 half-turns
    assert two_qubit_count(c) == 36 * n


# =========================================================================== (b) Iceberg transparency
@pytest.mark.parametrize("n_steps", [0, 1])
def test_iceberg_zero_noise_transparency(q3, n_steps):
    """Oracle: exact branching evaluation of the Iceberg circuit vs dense NumPy -- logical Z
    distribution equal to 1e-9 and acceptance 1 (every detector passes) at zero noise."""
    _d, s0 = _spins(3, 4, "flippable")
    c, layout = q3.triangular_iceberg_h2_circuit(3, 4, s0, n_steps, J0, H0, DT0)
    assert isinstance(layout, CodesLayout)
    assert c.n_qubits == 16
    acc, p_log = _exact_codes(c, layout, 12)
    assert acc == pytest.approx(1.0, abs=1e-9)
    ref = np.abs(_dense_state(3, 4, s0, n_steps, J0, H0, DT0)) ** 2
    assert np.max(np.abs(p_log - ref)) < 1e-9
    if n_steps == 0:
        assert p_log[_spin_index(s0)] == pytest.approx(1.0, abs=1e-9)


def test_iceberg_odd_k_refused(q3):
    """Oracle: spec -- the Iceberg code needs an even number of logical qubits (3x3 = 9)."""
    _d, s0 = _spins(3, 3, "3-sublattice")
    with pytest.raises(ValueError):
        q3.triangular_iceberg_h2_circuit(3, 3, s0, 1, J0, H0, DT0)


# =========================================================================== (c) distributions / observables
def test_bits_to_distribution_hand_cases(q3):
    """Oracle: hand counts -- MSB-first index, empirical frequencies, sums to 1."""
    p = q3.bits_to_distribution(np.array([[1, 0, 0]]))
    assert p.shape == (8,) and p[4] == 1.0 and p.sum() == 1.0
    bits = np.array([[0, 0, 1], [0, 0, 1], [1, 1, 1], [0, 1, 0]])
    p = q3.bits_to_distribution(bits)
    exp = np.zeros(8)
    exp[1], exp[7], exp[2] = 0.5, 0.25, 0.25
    assert np.allclose(p, exp, atol=0)
    p = q3.bits_to_distribution(np.array([[1] + [0] * 11]))
    assert len(p) == 4096 and p[2 ** 11] == 1.0


@pytest.mark.parametrize("bad", [np.zeros((0, 3), dtype=int), np.array([1, 0, 1])])
def test_bits_to_distribution_bad_input(q3, bad):
    """Oracle: spec -- zero shots or a non-2D array raise ValueError."""
    with pytest.raises(ValueError):
        q3.bits_to_distribution(bad)


def _hand_mixture():
    """0.5 initial state + 0.3 a one-flip defect state + 0.2 a defect-free OTHER-winding state."""
    d, s0 = _spins(3, 4, "flippable")
    i0 = _spin_index(s0)
    flat = np.asarray(s0).reshape(-1).copy()
    flat[0] *= -1
    i_def = _spin_index(flat)
    i_other = _spin_index(initial_spins(d, "stripe"))
    td, wx, wy = d.total_defects(), d.winding_x(0), d.winding_y(0)
    assert td[i0] == 0 and td[i_def] > 0 and td[i_other] == 0
    assert (wx[i_other], wy[i_other]) != (wx[i0], wy[i0])  # discriminating: winding matters
    p = np.zeros(1 << d.N)
    p[i0], p[i_def], p[i_other] = 0.5, 0.3, 0.2
    return d, s0, i0, i_def, p


def test_q3_observables_raw_and_gauss_hand(q3):
    """Oracle: observable_function for raw; hand mask (p_in = 0.5) and hand values for gauss
    (defect 0, memory 1, C1 0 for the initial basis state) [derived]."""
    d, s0, i0, _i_def, p = _hand_mixture()
    shells = Shells.build(d, 3)
    out = q3.q3_observables(d, s0, shells, p)
    assert set(out) >= {"raw", "gauss", "p_in"}
    ref = observable_function(d, s0, shells)(p)
    for o in OBS:
        assert out["raw"][o] == pytest.approx(ref[o], abs=1e-12), o
    assert out["p_in"] == pytest.approx(0.5, abs=1e-12)
    delta = np.zeros_like(p)
    delta[i0] = 1.0
    g_ref = observable_function(d, s0, shells)(delta)
    g = out["gauss"]
    assert g["defect_density"] == pytest.approx(0.0, abs=1e-12)
    assert g["memory"] == pytest.approx(1.0, abs=1e-12)
    assert g["C1"] == pytest.approx(0.0, abs=1e-12)
    assert g["flippable_density"] == pytest.approx(g_ref["flippable_density"], abs=1e-12)
    assert g["flippable_density"] > 0
    assert out["raw"]["defect_density"] > 0 and out["raw"]["memory"] < 1  # raw != gauss


def test_q3_observables_gauss_nan_when_p_in_zero(q3):
    """Oracle: spec -- all mass on a defect state gives p_in = 0 and NaN gauss values."""
    d, s0, _i0, i_def, _ = _hand_mixture()
    p = np.zeros(1 << d.N)
    p[i_def] = 1.0
    out = q3.q3_observables(d, s0, Shells.build(d, 3), p)
    assert out["p_in"] == 0.0
    assert all(math.isnan(out["gauss"][o]) for o in OBS)
    assert all(math.isfinite(out["raw"][o]) for o in OBS)


# =========================================================================== (d) noise scaling
@pytest.fixture(scope="module")
def base_measured(q3):
    _d, s0 = _spins(3, 4, "flippable")
    return q3.triangular_bare_h2_circuit(3, 4, s0, 2, J0, H0, DT0)[0]


@pytest.fixture(scope="module")
def base_plain(base_measured):
    return _strip_measures(base_measured)


MODEL = {"ZZ": 0.1, "XI": 0.05, "IY": 0.05}  # explicit test model, total 0.2 per unit (lam-1)


def test_scaled_lam1_is_base(q3, base_measured):
    """Oracle: spec -- lam = 1 gives exactly one 'none' item equal to base, whatever `instances`."""
    for method in ("insert", "fold"):
        out = q3.noise_scaled_circuits(base_measured, 1, method, instances=7, seed=3)
        assert len(out) == 1
        s = out[0]
        assert isinstance(s, q3.ScaledCircuit)
        assert s.lam == 1 and s.method == "none" and s.circuit == base_measured


def test_scaled_fold_exact_and_counts(q3, base_plain, base_measured):
    """Oracle: src.noise_scaling.fold_circuit -- one circuit, equal to fold_circuit(base, 3); 2q x lam."""
    out = q3.noise_scaled_circuits(base_plain, 3, "fold", instances=5)
    assert len(out) == 1 and out[0].method == "fold" and out[0].lam == 3
    assert out[0].circuit == fold_circuit(base_plain, 3)
    for lam in (3, 5):
        m = q3.noise_scaled_circuits(base_measured, lam, "fold")
        assert len(m) == 1
        assert two_qubit_count(m[0].circuit) == lam * two_qubit_count(base_measured) == lam * 72
        assert _n_ops(m[0].circuit, OpType.Measure) == 12


def test_scaled_insert_exact_seeds(q3, base_plain):
    """Oracle: insert_paulis(base, lam, model, default_rng((seed, i))) rebuilt here, per instance."""
    out = q3.noise_scaled_circuits(base_plain, 3, "insert", instances=4, seed=9, model=MODEL)
    assert [s.instance for s in out] == [0, 1, 2, 3]
    assert all(s.method == "insert" and s.lam == 3 for s in out)
    for s in out:
        ref = insert_paulis(base_plain, 3, MODEL, np.random.default_rng((9, s.instance)))
        assert s.circuit == ref


def test_scaled_insert_measured_base(q3, base_measured):
    """Oracle: gate multisets -- insertion only ADDS 1q X/Y/Z, keeps 2q count and the m[q] readout;
    deterministic in seed; instances not all equal."""
    a = q3.noise_scaled_circuits(base_measured, 2, "insert", instances=6, seed=1, model=MODEL)
    b = q3.noise_scaled_circuits(base_measured, 2, "insert", instances=6, seed=1, model=MODEL)
    assert len(a) == 6 and all(x.circuit == y.circuit for x, y in zip(a, b, strict=True))
    assert len({str(_sig(s.circuit)) for s in a}) > 1
    base_sig = _sig(base_measured)
    for s in a:
        assert two_qubit_count(s.circuit) == two_qubit_count(base_measured)
        sig = _sig(s.circuit)
        assert not (base_sig - sig)
        added = sig - base_sig
        for (op, args) in added:
            assert op in ("X", "Y", "Z") and len(args) == 1, (op, args)
    # a different seed gives a different set
    c = q3.noise_scaled_circuits(base_measured, 2, "insert", instances=6, seed=2, model=MODEL)
    assert any(x.circuit != y.circuit for x, y in zip(a, c, strict=True))


def test_scaled_default_model_runs(q3, base_measured):
    """Oracle: spec -- model=None uses the prior; 2q count unchanged, 10 instances returned."""
    out = q3.noise_scaled_circuits(base_measured, 3, "insert", instances=10, seed=0)
    assert len(out) == 10
    assert all(two_qubit_count(s.circuit) == 72 for s in out)


def test_scaled_insert_statistics(q3, base_plain):
    """Oracle: binomial 4-sigma -- inserted X, Y, Z counts over 20 x 72 ZZ gates at lam = 3 match
    (lam-1) x the model's per-label probabilities (XI -> X, IY -> Y, ZZ -> two Z)."""
    lam, inst = 3, 20
    out = q3.noise_scaled_circuits(base_plain, lam, "insert", instances=inst, seed=4, model=MODEL)
    n_gates = inst * two_qubit_count(base_plain)
    got = Counter()
    for s in out:
        for cmd in s.circuit.get_commands():
            if cmd.op.type in (OpType.X, OpType.Y, OpType.Z):
                got[cmd.op.type] += 1
    got[OpType.X] -= inst * _n_ops(base_plain, OpType.X)  # the prep X gates are not insertions
    s_ = lam - 1
    for typ, q, w in ((OpType.X, MODEL["XI"], 1), (OpType.Y, MODEL["IY"], 1), (OpType.Z, MODEL["ZZ"], 2)):
        p = s_ * q
        mean, var = n_gates * w * p, n_gates * (w * w * p - (w * p) ** 2)
        assert abs(got[typ] - mean) <= 4 * math.sqrt(var), (typ, got[typ], mean)
    total = got[OpType.X] + got[OpType.Y] + got[OpType.Z] // 2  # insertion events
    p_ev = s_ * sum(MODEL.values())
    assert abs(total - n_gates * p_ev) <= 4 * math.sqrt(n_gates * p_ev * (1 - p_ev))


@pytest.mark.parametrize("lam, method", [(2, "fold"), (4, "fold"), (0, "insert"), (0, "fold"),
                                         (-1, "insert"), (2, "zne"), (3, "")])
def test_scaled_bad_args(q3, base_plain, lam, method):
    """Oracle: spec -- even/odd-violating fold, lam < 1 and unknown methods raise ValueError."""
    with pytest.raises(ValueError):
        q3.noise_scaled_circuits(base_plain, lam, method, model=MODEL)


# =========================================================================== (e) driver groups
@pytest.fixture(scope="module")
def drv():
    return importlib.import_module("src.h2_driver")


@pytest.fixture(scope="module")
def plans(drv):
    return {g: drv.build_plan(g, SHOTS) for g in Q3_GROUPS}


def _steps(t):
    return round(t / CONFIG.q3.dt)


def test_q3_group_names(drv):
    """Oracle: spec -- the four Q3 groups are listed."""
    for g in Q3_GROUPS:
        assert g in drv.group_names()


def test_q3_estimates_and_widths(plans):
    """Oracle: hqc_estimate(native_counts(c), shots) (Rz-free) recomputed for every item; widths."""
    width = {"Q3-bare": 12, "Q3-iceberg": 16, "Q3-ladder": 12, "Q3-bare-3x6": 18}
    for g, plan in plans.items():
        assert plan.group == g
        for it in plan.items:
            assert it.estimate_hqc == pytest.approx(hqc_estimate(native_counts(it.circuit), it.shots),
                                                    rel=1e-12)
            assert it.n_qubits == it.circuit.n_qubits == width[g]
        assert plan.max_qubits == width[g]


def test_q3_bare_group(plans):
    """Oracle: spec -- 8 items in time order, steps 4..32, 36 ZZ per step, 12 readouts into m[q]."""
    items = plans["Q3-bare"].items
    times = CONFIG.noise_scaling.h2_bare_times
    assert len(items) == len(times) == 8
    for it, t in zip(items, times, strict=True):
        assert it.shots == SHOTS
        assert it.meta["time"] == t and it.meta["step"] == _steps(t) == 4 * t
        assert it.meta["case"] == (3, 4, "flippable")
        assert list(it.meta["cbits"]) == [Bit("m", q) for q in range(12)]
        assert set(it.meta["cbits"]) <= set(it.circuit.bits)
        assert two_qubit_count(it.circuit) == 36 * it.meta["step"]
        assert native_counts(it.circuit)["nmeas"] == 12


def test_q3_bare_compiled_physics(plans):
    """Oracle: dense NumPy at the working point (J=-1, h=0.3, dt=0.25, flippable 3x4, 4 steps) vs the
    COMPILED item's probabilities via pytket per-op unitaries, to 1e-9."""
    it = plans["Q3-bare"].items[0]
    _d, s0 = _spins(3, 4, "flippable")
    ref = np.abs(_dense_state(3, 4, s0, 4, J0, H0, DT0)) ** 2
    p = np.abs(_run_unitary(it.circuit)) ** 2
    assert np.max(np.abs(p - ref)) < 1e-9
    assert ref.max() < 0.99  # non-trivial
    wrong_h = np.abs(_dense_state(3, 4, s0, 4, J0, 2 * H0, DT0)) ** 2
    assert np.max(np.abs(wrong_h - ref)) > 1e-3


def test_q3_bare36_group(plans):
    """Oracle: spec + dense NumPy -- 3 items, 18 qubits, 54 ZZ per step; step-4 item reproduces the
    3-sublattice evolution (discriminates the initial state) to 1e-9."""
    items = plans["Q3-bare-3x6"].items
    times = CONFIG.noise_scaling.h2_bare36_times
    assert len(items) == len(times) == 3
    for it, t in zip(items, times, strict=True):
        assert it.shots == SHOTS and it.meta["step"] == _steps(t) and it.meta["time"] == t
        assert two_qubit_count(it.circuit) == 54 * it.meta["step"]
    _d, s0 = _spins(3, 6, "3-sublattice")
    ref = np.abs(_dense_state(3, 6, s0, items[0].meta["step"], J0, H0, DT0)) ** 2
    p = np.abs(_run_unitary(items[0].circuit)) ** 2
    assert np.max(np.abs(p - ref)) < 1e-9


def test_q3_iceberg_group(plans):
    """Oracle: spec -- 4 items (steps 4, 8, 12, 16), 16 qubits, CodesLayout whose keys = measurements."""
    items = plans["Q3-iceberg"].items
    times = CONFIG.noise_scaling.h2_iceberg_times
    assert len(items) == len(times) == 4
    for it, t in zip(items, times, strict=True):
        assert it.shots == SHOTS
        assert it.meta["time"] == t and it.meta["step"] == _steps(t)
        lay = it.meta["layout"]
        assert isinstance(lay, CodesLayout)
        assert native_counts(it.circuit)["nmeas"] == len(lay.keys)
        assert set(lay.cbits) <= set(it.circuit.bits)
        assert len(lay.logicals) == 12
    assert [it.meta["step"] for it in items] == [4, 8, 12, 16]


def test_q3_ladder_structure(plans):
    """Oracle: spec -- 3 plain + 2 lams x 3 times x k insertion instances (shots // k) + 1 fold = 64."""
    items = plans["Q3-ladder"].items
    NS = CONFIG.noise_scaling
    k = NS.insert_instances
    assert k == 10 and len(items) == 3 + 2 * 3 * k + 1 == 64
    kinds = Counter((it.meta["lam"], it.meta["method"]) for it in items)
    assert kinds == Counter({(1, "none"): 3, (2, "insert"): 3 * k, (3, "insert"): 3 * k,
                             (3, "fold"): 1})
    for it in items:
        m = it.meta
        assert m["step"] == _steps(m["time"])
        assert list(m["cbits"]) == [Bit("m", q) for q in range(12)]
        if m["method"] == "insert":
            assert it.shots == SHOTS // k == 100
        else:
            assert it.shots == SHOTS
    assert sorted(it.meta["time"] for it in items if it.meta["lam"] == 1) == list(NS.h2_ladder_times)
    for lam in (2, 3):
        for t in NS.h2_ladder_times:
            inst = sorted(it.meta["instance"] for it in items
                          if it.meta["method"] == "insert" and it.meta["lam"] == lam
                          and it.meta["time"] == t)
            assert inst == list(range(k)), (lam, t)
    fold = [it for it in items if it.meta["method"] == "fold"]
    assert fold[0].meta["time"] == NS.fold_plan_time and fold[0].meta["step"] == 8


def test_q3_ladder_two_qubit_counts(plans):
    """Oracle: two_qubit_count after compile -- fold = 3 x plain at the same step, insertion = plain."""
    items = plans["Q3-ladder"].items
    plain = {it.meta["step"]: two_qubit_count(it.circuit) for it in items if it.meta["lam"] == 1}
    assert plain == {4: 144, 8: 288, 12: 432}
    for it in items:
        n2 = two_qubit_count(it.circuit)
        if it.meta["method"] == "fold":
            assert n2 == 3 * plain[it.meta["step"]] == 864
        elif it.meta["method"] == "insert":
            assert n2 == plain[it.meta["step"]]


def test_q3_ladder_instances_differ_and_deterministic(drv, plans):
    """Oracle: rebuild -- the plan is identical when built twice (fixed seeds); insertion instances
    are not all identical (some (lam, t) group has > 1 distinct circuit)."""
    items = plans["Q3-ladder"].items
    again = drv.build_plan("Q3-ladder", SHOTS).items
    assert len(again) == len(items)
    for a, b in zip(items, again, strict=True):
        assert a.circuit == b.circuit and a.meta["instance"] == b.meta["instance"]
    groups = {}
    for it in items:
        if it.meta["method"] == "insert":
            groups.setdefault((it.meta["lam"], it.meta["time"]), []).append(str(_sig(it.circuit)))
    assert any(len(set(v)) > 1 for v in groups.values())
    plain = {it.meta["step"]: _sig(it.circuit) for it in items if it.meta["lam"] == 1}
    assert any(_sig(it.circuit) != plain[it.meta["step"]] for it in items
               if it.meta["method"] == "insert")


# =========================================================================== (f) offline H2 validity
def test_q3_bare_item_valid_for_offline_h2(plans):
    """Oracle: the offline H2 backend's own valid_circuit predicate on the 3x4 bare step-4 item."""
    from src.h2_backend import offline_compile_backend

    it = plans["Q3-bare"].items[0]
    assert it.meta["step"] == 4
    backend = offline_compile_backend(CONFIG.hardware.le_device)
    assert backend.valid_circuit(it.circuit)
