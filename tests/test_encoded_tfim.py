"""Iceberg-encoded TFIM (handoff/04 Part A): algebra, transparency, Stim<->execution
consistency, fault-tolerance accounting, backend toggle, feedforward discard, ceilings."""

import re

import numpy as np
import pytest
from pytket import Circuit, OpType

from src.backends import MemoryCeilingError
from src.backends_qc import (
    NEXUS_MSG, LocalSim, Noise, StateVector, _segments, bare_segments, local_exact_logical_z2,
    run, run_bare_local,
)
from src.compare import simulate_z2
from src.encoded_tfim import (
    IcebergTFIM, ShotRecord, accepted, build_stim, single_fault_report, stim_exact_logical_z2,
    weight1_injection_all_detected, z2_from_logical,
)
from src.qec.iceberg import IcebergCode
from src.qec.verify import verify_code

PHYS = dict(boundary="periodic", J=1.0, h=2.0, dt=0.25)


def spec(Lx=2, Ly=3, theta=np.pi / 6, **kw):
    args = {**PHYS, **kw}
    return IcebergTFIM(Lx, Ly, args["boundary"], args["J"], args["h"], args["dt"], theta)


def clifford_spec(Lx=2, Ly=3):
    return IcebergTFIM(Lx, Ly, "periodic", np.pi, 2 * np.pi, 0.25, 0.0)


# ------------------------------------------------------------------- structure / algebra
def test_register_and_even_k():
    s = spec()
    assert (s.k, s.n_phys, s.t, s.b, s.A, s.F) == (6, 10, 6, 7, 8, 9)
    with pytest.raises(ValueError):
        IcebergTFIM(3, 3, "periodic", 1, 2, 0.25, 0.1)       # k = 9 is odd


def test_block_passes_verify_code():
    c = IcebergCode(6)
    assert verify_code("blk", c.n, c.stabilizers(), [c.logical_x(i) for i in range(6)],
                       [c.logical_z(i) for i in range(6)]).ok


def test_logical_segments_commute_with_stabilizers():
    s = spec(2, 1)                                   # k=2 -> 6 physical qubits, 64x64 unitaries
    n = s.n_phys
    X = np.array([[0, 1], [1, 0]]); Z = np.diag([1, -1]); I2 = np.eye(2)

    def stab(P):
        out = np.ones((1, 1))
        for q in range(n):
            out = np.kron(out, P if q in s.data else I2)
        return out

    for seg in (s.prep_segment(), s.trotter_segment()):
        U = seg.get_unitary()
        for S in (stab(X), stab(Z)):
            assert np.allclose(U @ S @ U.conj().T, S, atol=1e-12)


def test_no_xxphase_in_authored_segments():
    # Selene's HUGR-QIS compiler rejects XXPhase; XX rotations are H.H ZZPhase H.H
    for seg in _segments(spec()).values():
        assert all(c.op.type in (OpType.H, OpType.CX, OpType.ZZPhase) for c in seg.get_commands())


# ------------------------------------------------------------------- zero-noise checks
@pytest.mark.parametrize("theta", [np.pi / 6, -np.radians(10)])
@pytest.mark.parametrize("dims", [(2, 2), (2, 3)])
def test_encoding_transparency(theta, dims):
    s = spec(*dims, theta=theta)
    steps = [1, 2, 3]
    enc = [local_exact_logical_z2(s, k) for k in steps]
    bare = simulate_z2(*dims, "periodic", 1.0, 2.0, 0.25, theta, steps, 24)
    assert np.allclose(enc, bare, atol=1e-12)


def test_stim_matches_execution_on_clifford_instance():
    s = clifford_spec()
    vals = []
    for k in (1, 2, 3, 4):
        st = stim_exact_logical_z2(s, k)
        lo = local_exact_logical_z2(s, k)
        ba = simulate_z2(2, 3, "periodic", np.pi, 2 * np.pi, 0.25, 0.0, [k], 24)[0]
        assert st == pytest.approx(lo, abs=1e-12) and lo == pytest.approx(ba, abs=1e-12)
        vals.append(st)
    assert len(set(np.round(vals, 9))) > 1             # discriminating, not a constant


def test_local_engine_matches_pytket_statevector():
    s = spec()
    rng = np.random.default_rng(3)
    for seg in _segments(s).values():
        pre = Circuit(s.n_phys)
        for q in range(s.n_phys):
            pre.Ry(rng.random(), q)
            pre.Rz(rng.random(), q)
        full = pre.copy()
        full.append(seg)
        sv = StateVector(s.n_phys, rng)
        sv.psi = pre.get_statevector().reshape((2,) * s.n_phys).astype(complex)
        LocalSim(Noise(), 0).run_segment(sv, seg)
        assert np.allclose(sv.flat(), full.get_statevector(), atol=1e-12)


# ------------------------------------------------------------------- Stim fault accounting
def test_stim_clean_run_silent_both_bases():
    for b in "ZX":
        d, o = build_stim(spec(), 3, basis=b).compile_detector_sampler(seed=0).sample(128, separate_observables=True)
        assert not d.any() and not o.any()


def test_every_weight1_fault_detected():
    ok, missed = weight1_injection_all_detected(spec(2, 2), 2)
    assert ok, missed


def test_single_fault_accounting_isolates_the_logical_gates():
    s = spec()
    rep = single_fault_report(s, 2)
    for cls in ("cx", "h", "meas", "reset", "idle"):
        assert rep[cls]["undetected_logical"] == 0, cls        # syndrome gadget etc. are FT
    assert rep["rot"]["undetected_logical"] > 0                  # logical gates are NOT
    supports = {frozenset(q.index[0] for q in c.qubits)
                for seg in (s.prep_segment(), s.trotter_segment())
                for c in seg.get_commands() if c.op.type == OpType.ZZPhase}
    for p in rep["rot"]["paulis"]:
        parts = re.findall(r"([XYZ])(\d+)", p)
        assert len(parts) == 2 and parts[0][0] == parts[1][0]   # XX, YY or ZZ
        assert frozenset(int(q) for _, q in parts) in supports  # on a logical gate's support
    assert len(rep["rot"]["paulis"]) == 3 * len(supports)       # all three, on every gate


# ------------------------------------------------------------------- discard predicate
def test_accept_predicate():
    good = ShotRecord([(0, 0, 1, 0), (0, 0, 1, 0)], np.zeros(8, dtype=np.int8))
    assert accepted(good)                                        # sx reference may be 1
    assert not accepted(ShotRecord([(0, 1, 0, 0)], np.zeros(8, dtype=np.int8)))   # flag
    assert not accepted(ShotRecord([(1, 0, 0, 0)], np.zeros(8, dtype=np.int8)))   # S_Z0 != 0
    assert not accepted(ShotRecord([(0, 0, 0, 0), (0, 0, 1, 0)], np.zeros(8, dtype=np.int8)))
    bad_par = np.zeros(8, dtype=np.int8)
    bad_par[0] = 1
    assert not accepted(ShotRecord([(0, 0, 0, 0)], bad_par))     # final parity vs last S_Z


# ------------------------------------------------------------------- backends
def test_local_sim_noiseless_accepts_everything_and_samples_z2():
    s = spec(2, 2)
    recs = run(s, 2, 300, Noise(), "local-sim", seed=1, max_spins=24)
    assert all(accepted(r) for r in recs)
    z, se = z2_from_logical(s.logical_from_bits(np.array([r.final for r in recs])))
    assert abs(z - local_exact_logical_z2(s, 2)) < 5 * se + 1e-9


def test_local_sim_noise_causes_discards():
    recs = run(spec(2, 2), 2, 200, Noise(p2=0.05), "local-sim", seed=2, max_spins=24)
    assert 0 < sum(accepted(r) for r in recs) < 200


def test_selene_feedforward_and_consistency():
    s = clifford_spec(2, 2)
    recs = run(s, 2, 120, Noise(), "selene", seed=5, max_spins=24)
    assert all(accepted(r) for r in recs)
    assert [accepted(r) for r in recs] == [r.in_program_accepted for r in recs]
    z, _ = z2_from_logical(s.logical_from_bits(np.array([r.final for r in recs])))
    assert z == pytest.approx(stim_exact_logical_z2(s, 2), abs=1e-12)   # deterministic value
    noisy = run(spec(2, 2), 3, 150, Noise(p2=0.05), "selene", seed=6, max_spins=24)
    assert [accepted(r) for r in noisy] == [r.in_program_accepted for r in noisy]
    assert any(len(r.rounds) < 4 for r in noisy)     # later rounds skipped once discarded


def test_toggle_nexus_stub_and_unknown_backend():
    with pytest.raises(NotImplementedError, match="credentials"):
        run(spec(), 1, 1, Noise(), "nexus", seed=0, max_spins=24)
    assert "flip toggle" in NEXUS_MSG
    with pytest.raises(ValueError):
        run(spec(), 1, 1, Noise(), "qiskit", seed=0, max_spins=24)
    with pytest.raises(ValueError, match="idle"):
        run(spec(), 1, 1, Noise(p_idle=0.01), "selene", seed=0, max_spins=24)


def test_over_ceiling_physical_register_refused():
    big = spec(4, 6)                                  # k=24 -> n_phys=28 > 24
    with pytest.raises(MemoryCeilingError, match="28 physical"):
        run(big, 1, 1, Noise(), "local-sim", seed=0, max_spins=24)
    with pytest.raises(MemoryCeilingError):
        run(big, 1, 1, Noise(), "selene", seed=0, max_spins=24)


def test_bare_reference_matches_ideal_without_noise():
    s = spec(2, 2)
    zb = run_bare_local(s, 2, 400, Noise(), seed=3, max_spins=24)
    z, se = z2_from_logical(zb)
    assert abs(z - simulate_z2(2, 2, "periodic", 1, 2, 0.25, np.pi / 6, [2], 24)[0]) < 5 * se
    assert set(bare_segments(s)) == {"prep", "trotter"}
