"""Randomized compiling / Pauli twirling (DECISIONS.md OPEN-3, D-RC): the 16-Pauli ZZPhase/
XXPhase classification, exact frame-propagation identities, the Pauli-noise no-op property,
a coherent-error case, transparency with twirling on, and the (currently unused) rc_period knob.

Exact checks use pytket get_unitary()/get_statevector() directly -- never sampling -- so they
have no seed-dependent flakiness. Statistical checks (no-op under sampled Pauli noise) use many
shots/instances and assert on signal spread, not just a loose tolerance, for test power.
"""

import numpy as np
import pytest
from pytket import Circuit, OpType

from src import twirl
from src.backends_qc import Noise, build_guppy_program_twirled, local_exact_logical_z2, run_twirled
from src.encoded_tfim import IcebergTFIM, accepted, build_stim, twirl_program, z2_from_logical

I2 = np.eye(2, dtype=complex)
_X = np.array([[0, 1], [1, 0]], dtype=complex)
_Y = np.array([[0, -1j], [1j, 0]])
_Z = np.diag([1.0, -1.0]).astype(complex)
PAULI = {"I": I2, "X": _X, "Y": _Y, "Z": _Z}
LABELS = ("I", "X", "Y", "Z")


def full_pauli(frame, n):
    out = np.ones((1, 1), dtype=complex)
    for q in range(n):
        out = np.kron(out, PAULI[frame.get(q, "I")])
    return out


def equal_up_to_phase(a, b, atol=1e-8):
    k = int(np.argmax(np.abs(a)))
    if np.abs(b[k]) < 1e-12:
        return np.allclose(a, 0, atol=atol) and np.allclose(b, 0, atol=atol)
    phase = a[k] / b[k]
    return np.isclose(abs(phase), 1.0, atol=1e-6) and np.allclose(a, phase * b, atol=atol)


def spec(Lx=2, Ly=1, theta=0.4, J=0.83, h=1.31, dt=0.21):
    return IcebergTFIM(Lx, Ly, "periodic", J, h, dt, theta)


# --------------------------------------------------------------------------- #
# Step 1: the independently-derived 16-Pauli table
# --------------------------------------------------------------------------- #
def _commutes(p1, p2, gen):
    m = np.kron(PAULI[p1], PAULI[p2])
    n = np.kron(PAULI[gen], PAULI[gen])
    return np.allclose(m @ n, n @ m)


@pytest.mark.parametrize("p1", LABELS)
@pytest.mark.parametrize("p2", LABELS)
def test_zzphase_16_pauli_table(p1, p2):
    """Derived independently of src/twirl.py: P1(x)P2 commutes with Z#Z iff both or neither of
    P1, P2 is in {X,Y} (established Pauli algebra); commuting -> gate unchanged, anticommuting
    -> angle negated. Checked against the implementation's actual emitted angle."""
    expect_commute = _commutes(p1, p2, "Z")
    c = Circuit(2)
    c.ZZPhase(0.37, 0, 1)
    res = twirl.twirl_circuit(c, np.random.default_rng(0), {0: p1, 1: p2})
    got = float([cmd for cmd in res.circuit.get_commands() if cmd.op.type == OpType.ZZPhase][0].op.params[0])
    unchanged = np.isclose((got - 0.37) % 4.0, 0.0)
    negated = np.isclose((got + 0.37) % 4.0, 0.0)
    assert unchanged or negated
    assert unchanged == expect_commute


@pytest.mark.parametrize("p1", LABELS)
@pytest.mark.parametrize("p2", LABELS)
def test_xxphase_16_pauli_table(p1, p2):
    """Same table for XXPhase (generator X#X): commuting iff both/neither of P1,P2 in {Y,Z}."""
    expect_commute = _commutes(p1, p2, "X")
    c = Circuit(2)
    c.XXPhase(0.41, 0, 1)
    res = twirl.twirl_circuit(c, np.random.default_rng(0), {0: p1, 1: p2})
    got = float([cmd for cmd in res.circuit.get_commands() if cmd.op.type == OpType.XXPhase][0].op.params[0])
    unchanged = np.isclose((got - 0.41) % 4.0, 0.0)
    negated = np.isclose((got + 0.41) % 4.0, 0.0)
    assert unchanged or negated
    assert unchanged == expect_commute


# --------------------------------------------------------------------------- #
# H / CX frame-update rules, brute force against the actual conjugation
# --------------------------------------------------------------------------- #
_H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
_CX = np.eye(4, dtype=complex)[[0, 1, 3, 2]]


@pytest.mark.parametrize("p", LABELS)
def test_h_frame_update_matches_conjugation(p):
    c = Circuit(1)
    c.H(0)
    res = twirl.twirl_circuit(c, np.random.default_rng(0), {0: p})
    brute = _H @ PAULI[p] @ _H.conj().T
    assert any(np.allclose(brute, ph * PAULI[res.frame.get(0, "I")]) for ph in (1, -1, 1j, -1j))


@pytest.mark.parametrize("pc", LABELS)
@pytest.mark.parametrize("pt", LABELS)
def test_cx_frame_update_matches_conjugation(pc, pt):
    c = Circuit(2)
    c.CX(0, 1)
    res = twirl.twirl_circuit(c, np.random.default_rng(0), {0: pc, 1: pt})
    brute = _CX @ np.kron(PAULI[pc], PAULI[pt]) @ _CX.conj().T
    target = np.kron(PAULI[res.frame.get(0, "I")], PAULI[res.frame.get(1, "I")])
    assert any(np.allclose(brute, ph * target) for ph in (1, -1, 1j, -1j))


# --------------------------------------------------------------------------- #
# Identity: exact statevector comparison, non-Clifford angle, chained through
# a mid-circuit measurement point (the syndrome segment's A/F ancillas)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", range(12))
def test_identity_unitary_prep_and_trotter(seed):
    """Non-Clifford theta/J/h (spec() defaults). U_twirled == P_out . U_ideal . P_in exactly,
    for a random incoming frame, on prep_segment and trotter_segment (which contain the H.H
    ZZPhase H.H sandwich -- the case that caught the missing-gate bug)."""
    s = spec()
    n = s.n_phys
    rng = np.random.default_rng(seed)
    frame_in = {q: rng.choice(LABELS) for q in range(n)}
    for seg in (s.prep_segment(), s.trotter_segment()):
        res = twirl.twirl_circuit(seg, rng, dict(frame_in))
        u_ideal = seg.get_unitary()
        u_tw = res.circuit.get_unitary()
        pin = full_pauli(frame_in, n)
        pout = full_pauli(res.frame, n)
        lhs = u_tw
        rhs = pout @ u_ideal @ pin
        # compare as operators: equal up to global phase
        k = np.unravel_index(np.argmax(np.abs(lhs)), lhs.shape)
        phase = lhs[k] / rhs[k]
        assert np.isclose(abs(phase), 1.0, atol=1e-6)
        assert np.allclose(lhs, phase * rhs, atol=1e-7)


@pytest.mark.parametrize("seed", range(10))
def test_identity_through_mid_circuit_measurement(seed):
    """Chain trotter_segment -> syndrome_segment("Z") -> syndrome_segment("X") with one
    continuous frame (exactly twirl_program's pattern), then perform an EXACT (not sampled)
    Z-basis measurement of the ancilla A: the joint probability of every outcome in the
    twirled/physical run equals the untwirled/ideal run's probability of the SAME outcome with
    A's bit flipped according to the final frame's x-component -- i.e. frame_readout_flips is
    exactly the correction a real mid-circuit measurement needs, not an approximation."""
    s = spec()
    n = s.n_phys
    rng = np.random.default_rng(seed)
    frame_in = {q: rng.choice(LABELS) for q in range(n)}
    frame = dict(frame_in)
    ideal = Circuit(n)
    tw = Circuit(n)
    for seg in (s.trotter_segment(), s.syndrome_segment("Z"), s.syndrome_segment("X")):
        res = twirl.twirl_circuit(seg, rng, frame)
        frame = res.frame
        ideal.append(seg)
        tw.append(res.circuit)

    pre = Circuit(n)
    rng2 = np.random.default_rng(seed + 10_000)
    for q in range(n):
        pre.Ry(float(rng2.random()), q)
        pre.Rz(float(rng2.random()), q)
    psi_in_ideal = pre.get_statevector()
    psi_in_phys = full_pauli(frame_in, n) @ psi_in_ideal

    full_ideal = pre.copy(); full_ideal.append(ideal)
    psi_ideal = full_ideal.get_statevector()
    psi_phys = tw.get_unitary() @ psi_in_phys

    # the joint distribution over ALL qubits (not just A, F) must match once every qubit's
    # bit is relabeled by its own final frame's X-component -- a nontrivial frame anywhere in
    # the register changes which computational-basis amplitude ends up where.
    flip = twirl.frame_readout_flips(frame, list(range(n)))
    dist_ideal = np.abs(psi_ideal.reshape((2,) * n)) ** 2
    dist_phys = np.abs(psi_phys.reshape((2,) * n)) ** 2

    for q, f in enumerate(flip):
        if f:
            dist_ideal = np.flip(dist_ideal, axis=q)
    assert np.allclose(dist_ideal, dist_phys, atol=1e-9)

    # the A, F ancillas specifically (the ones actually measured mid-circuit by the protocol)
    # must be correctly covered by this same flip vector -- sanity on frame_readout_flips' API.
    af_flip = twirl.frame_readout_flips(frame, [s.A, s.F])
    assert tuple(af_flip) == (flip[s.A], flip[s.F])


def test_frame_tracking_required_for_measurement_correction():
    """A case that FAILS if frame tracking (the readout-flip correction) is removed: a single
    ZZPhase that flips the ancilla's frame to X, followed directly by a Z-basis readout. Without
    frame_readout_flips, the raw twirled measurement disagrees with the ideal one on every
    outcome; with it, they agree exactly. (Manually confirmed during development that deleting
    the correction from src/twirl.py's call sites makes this -- and the measurement test above
    -- fail; see the audit report.)"""
    c = Circuit(2)
    c.ZZPhase(0.37, 0, 1)   # non-Clifford, so the ideal state is a genuine superposition
    rng = np.random.default_rng(0)
    res = twirl.twirl_circuit(c, rng, {0: "X", 1: "I"})   # forces an anticommuting incoming frame

    pre = Circuit(2)
    pre.Ry(0.6, 0); pre.Ry(1.1, 1)
    full_ideal = pre.copy(); full_ideal.append(c)
    psi_in_phys = full_pauli({0: "X", 1: "I"}, 2) @ pre.get_statevector()

    psi_ideal = full_ideal.get_statevector()
    # physical run: apply the twirled unitary directly to the physical (frame-twisted) input
    u_tw = res.circuit.get_unitary()
    psi_phys = u_tw @ psi_in_phys

    dist_ideal = np.abs(psi_ideal.reshape(2, 2)) ** 2
    dist_phys = np.abs(psi_phys.reshape(2, 2)) ** 2
    flip = twirl.frame_readout_flips(res.frame, [0, 1])

    # WITH the correction: relabel and match exactly
    corrected = dist_ideal.copy()
    for q, f in zip((0, 1), flip):
        if f:
            corrected = np.flip(corrected, axis=q)
    assert np.allclose(corrected, dist_phys, atol=1e-9)

    # WITHOUT the correction (simulating the bug of skipping frame_readout_flips): the
    # uncorrected ideal distribution generally disagrees with the physical one.
    if flip.any():
        assert not np.allclose(dist_ideal, dist_phys, atol=1e-6)


def test_reset_clears_frame_so_later_gate_sign_is_unaffected():
    """clear_frame on a qubit must make a LATER twirled gate on that qubit behave as if the
    pre-reset frame never existed. Fails if clear_frame is skipped and the stale frame leaks
    into the next gate's commute/anticommute decision."""
    rng = np.random.default_rng(0)
    frame = {0: "X", 1: "I"}
    twirl.clear_frame(frame, [0])
    assert frame[0] == "I"
    # a fresh ZZPhase on (0,1) now sees frame_in = I on qubit 0, not X
    c = Circuit(2)
    c.ZZPhase(0.29, 0, 1)
    res = twirl.twirl_circuit(c, rng, frame)
    got = float(res.circuit.get_commands()[0].op.params[0]) if res.circuit.get_commands()[0].op.type == OpType.ZZPhase \
        else float([cmd for cmd in res.circuit.get_commands() if cmd.op.type == OpType.ZZPhase][0].op.params[0])
    # I#I commutes with Z#Z -> angle unchanged (if frame[0] had stayed "X", it would anticommute
    # and the angle would be negated instead)
    assert np.isclose((got - 0.29) % 4.0, 0.0)


# --------------------------------------------------------------------------- #
# Pauli-noise no-op: twirled ensemble reproduces the untwirled result exactly
# (at zero noise) and within statistics (under sampled Pauli noise)
# --------------------------------------------------------------------------- #
def test_round0_flip_always_trivial():
    """Nothing has been twirled yet at round 0 (syndrome_segment has no ZZPhase/XXPhase), so
    the very first syndrome round's classical correction must always be a no-op. Pins down a
    structural fact about twirl_program that the rest of the suite relies on."""
    s = spec(2, 2)
    prog = twirl_program(s, 3, seed=5)
    assert prog.round0_flip == (0, 0, 0, 0)


def test_transparency_with_rc_on_zero_noise():
    """Encoded == bare transparency (CLAUDE.md, DECISIONS.md OPEN-3) still holds with twirling
    switched on: many independent twirl instances, many shots each, all accepted, matching the
    exact untwirled logical Z2 within statistical error."""
    s = spec(2, 2, theta=np.pi / 6, J=1.0, h=2.0, dt=0.25)
    n_steps = 2
    exact = local_exact_logical_z2(s, n_steps)
    instances = run_twirled(s, n_steps, 500, Noise(), noise_seed=1, max_spins=24,
                             rc_seed=11, n_instances=8)
    zs = []
    for recs in instances:
        assert all(accepted(r) for r in recs)
        z, se = z2_from_logical(s.logical_from_bits(np.array([r.final for r in recs])))
        assert abs(z - exact) < 5 * se + 1e-9
        zs.append(z)
    assert len(set(np.round(zs, 6))) > 1   # genuinely different instances, not one circuit reused


def test_pauli_noise_ensemble_reproduces_untwirled():
    """Under the project's Pauli noise model, many twirled instances' pooled logical Z2 must
    match the untwirled run's Z2 within statistics, with enough shots/instances for the test to
    have power, and the twirl draws must actually be spread across the Pauli group (not stuck
    returning the same frame)."""
    s = spec(2, 2, theta=np.pi / 6, J=1.0, h=2.0, dt=0.25)
    n_steps = 2
    noise = Noise(p2=0.01, p1=0.001, pm=0.001, p_init=0.001)

    from src.backends_qc import run as run_untwirled
    untw = run_untwirled(s, n_steps, 4000, noise, "local-sim", seed=1, max_spins=24)
    untw_acc = [r for r in untw if accepted(r)]
    z_ref, se_ref = z2_from_logical(s.logical_from_bits(np.array([r.final for r in untw_acc])))

    n_instances, shots = 25, 200
    instances = run_twirled(s, n_steps, shots, noise, noise_seed=2, max_spins=24,
                             rc_seed=99, n_instances=n_instances)
    pooled_final, pooled_acc = [], []
    for recs in instances:
        for r in recs:
            pooled_acc.append(accepted(r))
            pooled_final.append(r.final)
    pooled_final = np.array(pooled_final)[np.array(pooled_acc)]
    assert len(pooled_final) > 500          # enough accepted shots for the comparison to bite
    z_tw, se_tw = z2_from_logical(s.logical_from_bits(pooled_final))
    se = np.sqrt(se_ref ** 2 + se_tw ** 2)
    assert abs(z_tw - z_ref) < 5 * se + 1e-9

    # power check: the twirl draws are actually spread across the group, not degenerate.
    signs = set()
    for seed in range(n_instances):
        prog = twirl_program(s, n_steps, seed=1000 + seed)
        last_layer = prog.trotter_layers[-1]
        angles = tuple(round(float(c.op.params[0]) % 4.0, 6) for c in last_layer.get_commands()
                        if c.op.type == OpType.ZZPhase)
        signs.add(angles)
    assert len(signs) > 1


def test_coherent_overrotation_twirls_toward_pauli_prediction():
    """Small, EXACTLY-computable case (no sampling, the full 16-element Pauli group, not a
    random sample of it): model a FIXED, sign-independent stray coupling of size eps that the
    device adds after whatever ZZPhase(alpha) the compiler actually requested (a cross-talk-like
    hardware error, NOT a fractional mis-scaling of the requested angle -- a mis-scaling would
    flip sign with the twirl's own sign flip and the frame correction would cancel it exactly,
    which would not demonstrate anything). Twirling the alpha gate randomizes its compiled sign
    while the eps error stays fixed, so after frame correction the eps error's effect on the
    LOGICAL state differs from shot to shot and its average coherence (off-diagonal density
    matrix weight) shrinks relative to the single untwirled run -- the textbook RC benefit."""
    alpha = 0.4
    eps = 0.15   # a deliberately large, easily-distinguished stray coupling

    base = Circuit(2); base.ZZPhase(alpha, 0, 1)
    pre = Circuit(2); pre.Ry(0.7, 0); pre.Ry(1.3, 1)
    psi0 = pre.get_statevector()

    ideal = Circuit(2); ideal.ZZPhase(alpha, 0, 1)
    psi_ideal = ideal.get_unitary() @ psi0
    rho_ideal = np.outer(psi_ideal, psi_ideal.conj())

    # untwirled hardware: no twirl means frame_in=I always, so the fixed eps is just additive
    err = Circuit(2); err.ZZPhase(alpha + eps, 0, 1)
    psi_err = err.get_unitary() @ psi0
    rho_untwirled = np.outer(psi_err, psi_err.conj())

    rho_sum = np.zeros((4, 4), dtype=complex)
    for p1 in LABELS:
        for p2 in LABELS:
            frame_in = {0: p1, 1: p2}
            res = twirl.twirl_circuit(base, np.random.default_rng(0), dict(frame_in))
            hw = res.circuit.copy()
            hw.ZZPhase(eps, 0, 1)   # the SAME fixed stray coupling, independent of the twirl sign
            pin = full_pauli(frame_in, 2)
            pout = full_pauli(res.frame, 2)
            psi_hw = hw.get_unitary() @ (pin @ psi0)
            psi_logical = pout.conj().T @ psi_hw
            rho_sum += np.outer(psi_logical, psi_logical.conj())
    rho_twirled_avg = rho_sum / 16.0

    diff_untwirled = np.linalg.norm(rho_untwirled - rho_ideal)
    diff_twirled = np.linalg.norm(rho_twirled_avg - rho_ideal)

    # the stray coupling is clearly present and sizeable for a single untwirled shot...
    assert diff_untwirled > 0.1
    # ...but twirling cuts the coherence error (off-diagonal weight) substantially, moving the
    # averaged channel toward the Pauli-twirled (dephased) prediction. Diagonal populations
    # (measurement-basis probabilities) are exactly unaffected either way.
    assert np.allclose(np.diag(rho_untwirled), np.diag(rho_ideal), atol=1e-9)
    assert np.allclose(np.diag(rho_twirled_avg), np.diag(rho_ideal), atol=1e-9)
    off_ideal = rho_ideal - np.diag(np.diag(rho_ideal))
    off_untwirled = rho_untwirled - np.diag(np.diag(rho_untwirled))
    off_twirled = rho_twirled_avg - np.diag(np.diag(rho_twirled_avg))
    assert np.linalg.norm(off_twirled - off_ideal) < 0.5 * np.linalg.norm(off_untwirled - off_ideal)


# --------------------------------------------------------------------------- #
# Period: the reference cadence (CLAUDE.md: RC every two Trotter layers) is NOT
# implemented -- lock in and flag the current (continuous, per-gate) behaviour.
# --------------------------------------------------------------------------- #
def test_rc_period_config_is_not_wired_to_twirl_granularity():
    """EncodedConfig.rc_period (config.py) documents the reference's 2-layer cadence, but
    twirl_program takes no period argument and draws independent randomness at EVERY twirled
    gate (continuous, per-gate granularity), not once per rc_period Trotter layers. This test
    locks in that CURRENT behaviour so a future change is a deliberate decision, not a silent
    regression -- see the audit report for why this is flagged open, not fixed here."""
    import inspect

    sig = inspect.signature(twirl_program)
    assert "period" not in sig.parameters

    s = spec(2, 2)
    prog = twirl_program(s, 4, seed=3)
    # consecutive trotter layers generically differ (continuous re-randomization), not just
    # every rc_period=2 of them
    sign_patterns = []
    for layer in prog.trotter_layers:
        pat = tuple(round(float(c.op.params[0]) % 4.0, 6) for c in layer.get_commands()
                    if c.op.type == OpType.ZZPhase)
        sign_patterns.append(pat)
    assert len(set(sign_patterns)) > 1   # not all four layers identical


# --------------------------------------------------------------------------- #
# default-off / unchanged-execution-paths guarantee for build_stim
# --------------------------------------------------------------------------- #
def test_build_stim_twirled_none_is_unchanged():
    s = spec(2, 2)
    for basis in ("Z", "X"):
        a = build_stim(s, 2, basis=basis)
        b = build_stim(s, 2, basis=basis, twirled=None)
        assert str(a) == str(b)


def test_build_stim_with_twirled_clean_run_silent():
    """Kept as a smoke check only. It CANNOT fail on its own: see
    test_build_stim_twirled_final_readout_matches_untwirled for why, and for the real check."""
    s = spec(2, 2, theta=np.pi / 6, J=1.0, h=2.0, dt=0.25)
    prog = twirl_program(s, 2, seed=4)
    for basis in ("Z", "X"):
        circ = build_stim(s, 2, basis=basis, twirled=prog)
        d, _ = circ.compile_detector_sampler(seed=0).sample(200, separate_observables=True)
        assert not d.any()


@pytest.mark.parametrize("basis,field", [("Z", "final_flip"), ("X", "final_flip_x")])
def test_build_stim_twirled_final_readout_matches_untwirled(basis, field):
    """The twirled Stim image must reproduce the untwirled circuit's final data-measurement
    distribution in BOTH readout bases.

    Why this compares raw measurement records rather than detectors: Stim's
    `compile_detector_sampler` reference-subtracts, so a noiseless deterministic circuit gives
    all-zero detectors whatever the final correction is. An independent review showed the
    detector-based check above cannot fail -- corrupting every bit of the correction went
    undetected 0/36 -- and that this hid a real bug: `basis="X"` applied the Z-basis mask (the
    frame's X-component) although the data is conjugated by H first, so the X readout is flipped
    by the frame's Z-component instead. Every seed was wrong in basis X.

    So: compare raw records, and assert the correction is actually load-bearing.
    """
    s = spec(2, 2, theta=np.pi / 6, J=1.0, h=2.0, dt=0.25)
    n_data = len(s.data)
    ref = build_stim(s, 2, basis=basis).compile_sampler(seed=0).sample(400)
    want = {tuple(r) for r in ref[:, -n_data:].astype(int)}

    for seed in range(6):
        prog = twirl_program(s, 2, seed=seed)
        got = build_stim(s, 2, basis=basis, twirled=prog).compile_sampler(seed=0).sample(400)
        assert {tuple(r) for r in got[:, -n_data:].astype(int)} == want, (
            f"twirled basis={basis} seed={seed}: final data distribution differs from untwirled")

    caught = 0
    for seed in range(3):
        for bit in range(n_data):
            prog = twirl_program(s, 2, seed=seed)
            getattr(prog, field)[bit] ^= 1
            got = build_stim(s, 2, basis=basis, twirled=prog).compile_sampler(seed=0).sample(400)
            caught += {tuple(r) for r in got[:, -n_data:].astype(int)} != want
    assert caught == 3 * n_data, f"only {caught}/{3 * n_data} corruptions of {field} detected"


def test_selene_accepts_twirled_program_at_zero_noise():
    """Exercises the Guppy/Selene path (CLAUDE.md: Selene rejects pytket XXPhase; this checks
    it accepts the twirl's explicit X/Y/Z Pauli gates too)."""
    from selene_sim import DepolarizingErrorModel, Quest

    from src.backends_qc import _parse_selene

    s = spec(2, 2, theta=np.pi / 6, J=1.0, h=2.0, dt=0.25)
    n_steps = 2
    prog = twirl_program(s, n_steps, seed=3)
    main_fn = build_guppy_program_twirled(s, prog)
    em = DepolarizingErrorModel(random_seed=0, p_1q=0, p_2q=0, p_meas=0, p_init=0)
    res = (main_fn.emulator(n_qubits=s.n_phys).with_shots(40).with_simulator(Quest())
           .with_seed(0).with_error_model(em).run())
    recs = [_parse_selene(entry.entries) for entry in res.results]
    assert all(accepted(r) for r in recs)
    exact = local_exact_logical_z2(s, n_steps)
    z, se = z2_from_logical(s.logical_from_bits(np.array([r.final for r in recs])))
    assert abs(z - exact) < 5 * se + 1e-9
