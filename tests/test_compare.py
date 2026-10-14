"""Q1 harness (handoff/03): dataset loader on the synthetic fixture, the new observables,
the circuit-order Trotter sign mapping (checked by a literal gate replay), and the
over-ceiling refusal. Runs offline: tests/fixtures/zenodo_mini is synthetic.
"""

import os
import shutil

import numpy as np
import pytest
import scipy.linalg as la

from src.backends import MemoryCeilingError
from src.compare import (
    CAVEAT, Series, ZenodoData, check_ceiling, circuit_trotter_states, compare_z2,
    gauge_check_angles, light_cone_z2_step1, pair_average_from_z2, qasm_step_bonds, read_qasm,
    ry_product_state, simulate_z2,
)
from src.lattice import square_bonds
from src.observables import (
    expval_zz, magnetization_variance_z, nn_energy_density_x, total_z_sq_normalized,
)

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "zenodo_mini")
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]])
Z = np.diag([1.0, -1.0]).astype(complex)


def _op(M, q, n):
    return np.kron(np.kron(np.eye(2 ** q), M), np.eye(2 ** (n - q - 1)))


def _rand_state(n, seed=0):
    rng = np.random.default_rng(seed)
    v = rng.normal(size=2 ** n) + 1j * rng.normal(size=2 ** n)
    return v / np.linalg.norm(v)


@pytest.fixture(scope="module")
def data():
    return ZenodoData(FIX)


# ----------------------------------------------------------------------- loader
def test_missing_dataset_dir_is_a_clear_error():
    with pytest.raises(FileNotFoundError, match="data_path"):
        ZenodoData("/nonexistent/zenodo_data")
    with pytest.raises(FileNotFoundError):
        ZenodoData("")


def test_steps_are_nonuniform_and_never_assumed_20(data):
    assert [len(data.steps(q)) for q in (1, 2, 3, 4)] == [12, 20, 10, 8]
    s1 = data.steps(1)
    assert s1.dtype.kind == "i" and s1[-1] == 20 and len(s1) != s1[-1]


def test_z2_shape_and_error_bar(data):
    ser = data.load(1, "Z2", "zne+znr")
    assert ser.values.shape == (12,) and ser.err.shape == (12,)
    assert np.array_equal(ser.steps, data.steps(1))
    assert data.load(2, "Z2", "raw_unamplified").values.shape == (20,)


def test_zznn_family_shapes(data):
    assert data.load(3, "ZZnn", "zne+znr").values.shape == (10, 14)
    assert data.load(3, "ZZnn", "zne+znr").err.shape == (10, 14)
    assert data.load(3, "ZZnn_fft", "zne+znr").values.shape == (10, 8)      # 14//2 + 1
    rates = data.load(3, "ZZnn_fft_decayrates", "zne+znr")
    assert rates.values.shape == (4,) and rates.err.shape == (4,)


def test_dimercorrs_are_r_by_step(data):
    ser = data.load(4, "dimercorrs", "zne", initstate="min_winding")
    assert ser.values.shape == (4, 8)                    # [r, step], transpose of M x L rule
    assert np.array_equal(ser.rs, [1, 2, 3, 4]) and len(ser.steps) == 8
    raw = np.loadtxt(os.path.join(FIX, "quench4_min_winding_dimercorrs_zne.txt"))
    assert np.array_equal(ser.values, raw)               # no silent transposition
    assert data.load(4, "dimercorrs", "zne", initstate="max_winding").err.shape == (4, 8)


def test_loader_rejects_bad_arguments_and_shapes(data):
    with pytest.raises(ValueError, match="mode"):
        data.load(1, "Z2", "zne_plus")
    with pytest.raises(ValueError, match="initstate"):
        data.load(4, "dimercorrs", "zne")
    with pytest.raises(ValueError, match="initstate"):
        data.load(1, "Z2", "zne+znr", initstate="min_winding")
    with pytest.raises(ValueError, match="11 rows but 12 steps"):
        data.load(1, "Z2", "znr_unamplified", require_err=False)   # deliberately malformed file
    with pytest.raises(FileNotFoundError):
        data.load(1, "Z2", "zne")


def test_read_qasm_angles_and_bonds():
    g = read_qasm(os.path.join(FIX, "quench9_step1.qasm"))
    assert g["ry"][0] == (0, pytest.approx(np.pi / 6))
    assert g["ry"][1][1] == pytest.approx(-np.radians(10))
    assert {a for *_, a in g["rzz"]} == {0.5} and g["rx"][0][1] == 0.5
    assert qasm_step_bonds(os.path.join(FIX, "quench9_step1.qasm")) == [(0, 1), (0, 2), (0, 3), (1, 2)]


# ------------------------------------------------------------------ observables
@pytest.mark.parametrize("n", [3, 5, 6])
def test_total_z_sq_normalized_matches_dense_operator(n):
    psi = _rand_state(n, seed=n)
    Mz = sum(_op(Z, q, n) for q in range(n))
    brute = np.real(np.vdot(psi, Mz @ Mz @ psi)) / n ** 2
    assert total_z_sq_normalized(psi, n) == pytest.approx(brute, abs=1e-12)


def test_z2_is_second_moment_not_connected_variance():
    n = 4
    up = np.zeros(2 ** n, complex)
    up[0] = 1
    assert total_z_sq_normalized(up, n) == pytest.approx(1.0)   # <M^2>/N^2 = 1
    assert magnetization_variance_z(up, n) == pytest.approx(0.0)  # connected variance = 0


@pytest.mark.parametrize("bc", ["open", "periodic"])
def test_nn_energy_density_matches_per_bond_sum(bc):
    Lx, Ly = 3, 4
    n = Lx * Ly
    psi = _rand_state(n, seed=7)
    bonds = square_bonds(Lx, Ly, bc)
    E = nn_energy_density_x(psi, Lx, Ly, bonds)
    ref = np.zeros(Lx)
    for x in range(Lx):
        for y in range(Ly):
            s = y * Lx + x
            for (i, j) in bonds:
                if s in (i, j):
                    ref[x] += expval_zz(psi, n, i, j) / 4
    assert np.allclose(E, ref, atol=1e-12)
    assert E.sum() == pytest.approx(sum(expval_zz(psi, n, i, j) for i, j in bonds) / 2)


# ---------------------------------------------------- circuit and sign mapping
def _gate_replay(Lx, Ly, theta, steps, rzz=0.5, rx=0.5):
    """Literal QASM-gate replay: ry(theta) prep, then per step rx(rx) / rzz(rzz) on bonds / rx(rx)."""
    n = Lx * Ly
    bonds = square_bonds(Lx, Ly, "periodic")
    psi = np.zeros(2 ** n, complex)
    psi[0] = 1
    RY = la.expm(-1j * theta / 2 * Y)
    for q in range(n):
        psi = _op(RY, q, n) @ psi
    RX = la.expm(-1j * rx / 2 * X)
    out = {}
    for s in range(1, max(steps) + 1):
        for q in range(n):
            psi = _op(RX, q, n) @ psi
        for i, j in bonds:
            psi = la.expm(-1j * rzz / 2 * (_op(Z, i, n) @ _op(Z, j, n))) @ psi
        for q in range(n):
            psi = _op(RX, q, n) @ psi
        if s in steps:
            out[s] = total_z_sq_normalized(psi, n)
    return np.array([out[s] for s in steps])


@pytest.mark.parametrize("theta", [np.pi / 6, -np.radians(10)])
def test_harness_reproduces_literal_qasm_gates(theta):
    steps = [1, 2, 3, 5]
    ref = _gate_replay(3, 3, theta, steps)
    sim = simulate_z2(3, 3, "periodic", 1.0, 2.0, 0.25, theta, steps, max_spins=24)
    assert np.allclose(sim, ref, atol=1e-12)
    # README gauge identities: (J,h,th) -> (-J,-h,th) and (J,h,th) -> (J,-h,-th)
    assert np.allclose(simulate_z2(3, 3, "periodic", -1.0, -2.0, 0.25, theta, steps, 24), ref, atol=1e-12)
    assert np.allclose(simulate_z2(3, 3, "periodic", 1.0, -2.0, 0.25, -theta, steps, 24), ref, atol=1e-12)
    # ... and their composition (J,h,th) -> (-J,h,-th), the fourth element of the orbit
    assert np.allclose(simulate_z2(3, 3, "periodic", -1.0, 2.0, 0.25, -theta, steps, 24), ref, atol=1e-12)
    # the sign mapping matters: the non-gauge pairing is measurably different
    assert np.abs(simulate_z2(3, 3, "periodic", 1.0, -2.0, 0.25, theta, steps, 24) - ref).max() > 0.05


@pytest.mark.parametrize("theta", [np.pi / 6, -np.radians(10)])
def test_gauge_check_agrees_with_literal_replay(theta):
    """gauge_check_angles accepts a signed (rzz, rx, ry) circuit iff its literal gate replay
    reproduces the config run (J, h) = (1, 2) — an independent check of the accepted set."""
    steps = [1, 2, 3]
    ref = simulate_z2(2, 3, "periodic", 1.0, 2.0, 0.25, theta, steps, 24)   # 2x3 torus: fast
    for sa in (1, -1):
        for sb in (1, -1):
            for sc in (1, -1):
                replay = _gate_replay(2, 3, sc * theta, steps, rzz=sa * 0.5, rx=sb * 0.5)
                same = np.allclose(replay, ref, atol=1e-10)
                label, probs = gauge_check_angles([sa * 0.5] * 6, [sb * 0.5] * 6, [sc * theta] * 6,
                                                  1.0, 2.0, 0.25, theta)
                assert (label is not None) == same, (sa, sb, sc)
                assert (probs == []) == same
                if not same:
                    assert np.abs(replay - ref).max() > 0.05     # discriminating, not marginal


def test_gauge_check_rejects_mixed_signs_and_magnitudes():
    ok = dict(J=1.0, h=2.0, dt=0.25, theta=0.5)
    assert gauge_check_angles([0.5, 0.5], [0.5, 1.0], [0.5], **ok) == ("(-J,-h,theta)", [])
    _, p = gauge_check_angles([0.5, -0.5], [0.5], [0.5], **ok)
    assert any("rzz: mixed signs" in x for x in p)
    _, p = gauge_check_angles([0.5], [0.5, -0.5], [0.5], **ok)
    assert any("rx: mixed signs" in x for x in p)
    _, p = gauge_check_angles([0.4], [0.5], [0.5], **ok)
    assert any("rzz: |angle| off target" in x for x in p)
    _, p = gauge_check_angles([], [0.5], [0.5], **ok)
    assert p == ["rzz: no gates"]


# -------------------------------------------- exact N = 56 step 1 via the light cone
@pytest.mark.parametrize("Lx,Ly,bc", [(4, 4, "periodic"), (4, 5, "periodic"), (3, 4, "open")])
def test_light_cone_step1_matches_full_statevector(Lx, Ly, bc):
    th = np.pi / 6
    full = simulate_z2(Lx, Ly, bc, 1.0, 2.0, 0.25, th, [1], 24)[0]
    assert light_cone_z2_step1(Lx, Ly, bc, 1.0, 2.0, 0.25, th, 24) == pytest.approx(full, abs=1e-12)


def test_light_cone_step1_n56_value():
    """[measured] Exact step-1 value on the 7x8 torus quoted in docs/q1_compare.md."""
    z2 = light_cone_z2_step1(7, 8, "periodic", 1.0, 2.0, 0.25, np.pi / 6, 24)
    assert z2 == pytest.approx(0.754759, abs=1e-6)
    assert pair_average_from_z2(z2, 56) == pytest.approx(0.750300, abs=1e-6)
    # the reduced-lattice pair averages the old "about 3 sigma" used, for contrast
    assert pair_average_from_z2(simulate_z2(4, 5, "periodic", 1.0, 2.0, 0.25, np.pi / 6, [1], 24)[0], 20) \
        == pytest.approx(0.7610, abs=5e-5)


def test_ry_product_state():
    th = 0.7
    psi = ry_product_state(3, th, max_spins=24)
    assert np.linalg.norm(psi) == pytest.approx(1)
    from src.observables import expval_z
    assert expval_z(psi, 3, 1) == pytest.approx(np.cos(th))


def test_records_requested_nonuniform_steps_only():
    bonds = square_bonds(2, 3, "periodic")
    got = [s for s, _ in circuit_trotter_states(6, bonds, 1.0, 2.0, 0.25, 0.3, [5, 1, 3, 3], 24)]
    assert got == [1, 3, 5]


# ------------------------------------------------------------- ceiling refusal
def test_over_ceiling_is_refused_before_allocation():
    with pytest.raises(MemoryCeilingError, match="56 spins refused"):
        check_ceiling(56, 24)
    # a 7x8 run must fail immediately (a real attempt would need 2^56 amplitudes)
    with pytest.raises(MemoryCeilingError):
        next(circuit_trotter_states(56, square_bonds(7, 8, "periodic"), 1.0, 2.0, 0.25, 0.5, [1], 24))
    with pytest.raises(MemoryCeilingError):
        simulate_z2(7, 8, "periodic", 1.0, 2.0, 0.25, 0.5, [1], max_spins=24)


def test_compare_refuses_whole_run_if_any_size_over_ceiling(data):
    with pytest.raises(MemoryCeilingError):
        compare_z2(data, 1, np.pi / 6, [(2, 2), (5, 5)], "periodic", 1.0, 2.0, 0.25, max_spins=24)


# ------------------------------------------------------------------ comparison
def test_compare_z2_table_on_fixture(data):
    cmp = compare_z2(data, 1, np.pi / 6, [(2, 2), (2, 3)], "periodic", 1.0, 2.0, 0.25, max_spins=24)
    lines = cmp.table()
    assert len(lines) == 1 + 12                     # header + one row per dataset step
    assert set(cmp.sim) == {(2, 2), (2, 3)}
    assert all(v.shape == (12,) for v in cmp.sim.values())
    assert "NOT a same-system fidelity" in CAVEAT


def test_series_defaults_keep_old_constructions(data):
    s = Series(1, "Z2", "zne+znr", np.arange(3), np.zeros(3), None)       # pre-existing 6-arg form
    assert s.estimator == "zne+znr" and s.shots is None and s.effective_shots is None
    assert s.acceptance is None
    assert data.load(1, "Z2", "raw_unamplified").estimator == "raw"
    assert data.load(1, "Z2", "raw_unamplified").shots is None          # dataset states no shots
    assert Series(1, "Z2", "custom", np.arange(3), np.zeros(3), None).estimator is None
    with pytest.raises(ValueError, match="shot count not stated"):
        s.stderr_from_shot_std(0.3)


def test_series_holds_a_postselected_arm():
    """Structure only: a placeholder Series with made-up counts, not logical data."""
    steps = np.array([1, 2])
    s = Series(1, "Z2", "logical", steps, np.zeros(2), None,
               shots=1000, accepted_shots=np.array([800, 400]), estimator="postselected")
    assert np.array_equal(s.effective_shots, [800, 400])            # accepted, not executed
    assert np.allclose(s.acceptance, [0.8, 0.4])
    assert np.allclose(s.stderr_from_shot_std(0.4), 0.4 / np.sqrt([800, 400]))
    assert "estimator=postselected" in s.provenance() and "accepted=400..800 (per step)" in s.provenance()
    raw = Series(1, "Z2", "physical", steps, np.zeros(2), None, shots=1000, estimator="raw")
    assert raw.effective_shots == 1000 and raw.stderr_from_shot_std(0.4) == pytest.approx(0.4 / np.sqrt(1000))
    with pytest.raises(ValueError, match="exceeds"):
        Series(1, "Z2", "x", steps, np.zeros(2), None, shots=10, accepted_shots=11)
    with pytest.raises(ValueError, match="without shots"):
        Series(1, "Z2", "x", steps, np.zeros(2), None, accepted_shots=5)
    with pytest.raises(ValueError, match="needs accepted_shots"):
        Series(1, "Z2", "x", steps, np.zeros(2), None, shots=10, estimator="postselected")
    with pytest.raises(ValueError, match="unknown estimator"):
        Series(1, "Z2", "x", steps, np.zeros(2), None, estimator="mitigated")
    with pytest.raises(ValueError, match="nothing accepted"):
        Series(1, "Z2", "x", steps, np.zeros(2), None, shots=10, accepted_shots=0,
               estimator="postselected").stderr_from_shot_std(0.1)


def test_comparison_provenance_lists_estimators(data):
    cmp = compare_z2(data, 1, np.pi / 6, [(2, 2)], "periodic", 1.0, 2.0, 0.25, max_spins=24)
    assert [p.split(":")[0] for p in cmp.provenance()] == ["zne+znr", "raw_unamplified"]
    assert "estimator=raw," in cmp.provenance()[1]


def test_pair_average_removes_self_term():
    assert pair_average_from_z2(1.0, 56) == pytest.approx(1.0)        # all aligned
    assert pair_average_from_z2(1 / 56, 56) == pytest.approx(0.0)     # uncorrelated


# ------------------------------------------------- regressions from independent review
def _copy_fixture(tmp_path):
    d = tmp_path / "zd"
    shutil.copytree(FIX, d)
    return d


def test_transposed_error_file_is_rejected(tmp_path):
    d = _copy_fixture(tmp_path)
    name = "quench4_min_winding_dimercorrs_err_zne.txt"
    np.savetxt(d / name, np.loadtxt(d / name).T)          # (8, 4): wrong layout
    with pytest.raises(ValueError, match="shape"):
        ZenodoData(str(d)).load(4, "dimercorrs", "zne", initstate="min_winding")
    np.savetxt(d / "quench3_ZZnn_err_zne+znr.txt", np.zeros((14, 10)))
    with pytest.raises(ValueError, match="shape"):
        ZenodoData(str(d)).load(3, "ZZnn", "zne+znr")


def test_missing_error_file_is_an_error_not_nan(tmp_path):
    d = _copy_fixture(tmp_path)
    os.rename(d / "quench1_Z2_err_zne+znr.txt", d / "quench1_Z2_zne+znr_error.txt")
    with pytest.raises(FileNotFoundError, match="error-bar"):
        ZenodoData(str(d)).load(1, "Z2", "zne+znr")
    assert ZenodoData(str(d)).load(1, "Z2", "zne+znr", require_err=False).err is None


def test_ry_product_state_refuses_over_ceiling():
    with pytest.raises(MemoryCeilingError):
        ry_product_state(56, 0.5, max_spins=24)


def test_yielded_states_are_not_aliased():
    bonds = square_bonds(2, 3, "periodic")
    collected = list(circuit_trotter_states(6, bonds, 1.0, 2.0, 0.25, 0.4, [0, 1, 2], 24))
    for step, psi in collected:
        fresh = next(circuit_trotter_states(6, bonds, 1.0, 2.0, 0.25, 0.4, [step], 24))[1]
        assert np.allclose(psi, fresh, atol=1e-13)


@pytest.mark.parametrize("line", ["ry(-(pi/18)) q[1];", "rx(0.5) q;", "rzz(0.5) q[0];"])
def test_qasm_parser_fails_loudly(tmp_path, line):
    p = tmp_path / "bad.qasm"
    p.write_text("OPENQASM 2.0;\nqreg q[2];\n" + line + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_qasm(str(p))
