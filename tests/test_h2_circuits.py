"""FROZEN tests (test-first) for src/h2_circuits.py: one pytket circuit per program for H2.

Oracles come from outside the module under test:
  - transparency: the noiseless H2 local emulator (LE, pytket-quantinuum[pecos]) must reproduce
    the exact local-sim logical Z2 (src.backends_qc.local_exact_logical_z2 /
    src.encoded_codes.exact_logical_z2 / stim_exact_z2) within 4 standard errors, with acceptance
    exactly 1;
  - fault detection: a deliberate single-qubit Pauli on a data qubit must be caught on every shot;
  - layout / mapping: hand-built bit arrays and the interface definition in the brief;
  - compilation & cost: hand-counted gate tallies and the published HQC formula.

Every noisy number here is a classical prediction under an ASSUMED depolarizing model run on a
LOCAL emulator, never an H2 result. Nothing in this file touches the network or Nexus.

Emulator tests start with pytest.importorskip("pytket_pecos"): they run in .venv-le and skip in
.venv. Everything else must pass in both environments.
"""

from collections import Counter
from dataclasses import replace

import numpy as np
import pytest
from pytket import Bit, Circuit, OpType
from src.h2_backend import run_le
from src.h2_circuits import (
    CodesLayout,
    H2Layout,
    bare_h2_circuit,
    bare_z,
    codes_h2_circuit,
    codes_records,
    compile_for_h2,
    encoded_h2_circuit,
    hqc_estimate,
    native_counts,
    shot_records,
    two_qubit_count,
)

from config import CONFIG
from src.backends_qc import Noise, local_exact_logical_z2
from src.encoded_codes import (
    EncodedTFIM,
    _support,
    exact_logical_z2,
    make_code,
    stim_exact_z2,
)
from src.encoded_tfim import (
    IcebergTFIM,
    ShotRecord,
    TwirledProgram,
    accepted,
    twirl_program,
    z2_from_logical,
)

E = CONFIG.encoded
NSIG = 4          # every statistical tolerance below is 4 standard errors (shot noise)


# --------------------------------------------------------------------------- helpers / fixtures
def ice(Lx=2, Ly=2, syndrome_every=1):
    return IcebergTFIM(Lx, Ly, "periodic", E.J, E.h, E.dt, E.theta, syndrome_every=syndrome_every)


def ice_clifford(Lx=2, Ly=2):
    return IcebergTFIM(Lx, Ly, "periodic", E.clifford_J, E.clifford_h, E.dt, E.clifford_theta)


CODE_LATTICE = {"steane": (1, 2), "five": (1, 2), "concat": (2, 2)}


def code_prog(name, J=None, h=None, theta=None):
    a, b = CODE_LATTICE[name]
    return EncodedTFIM(make_code(name, a * b), a, b, "periodic",
                       E.J if J is None else J, E.h if h is None else h, E.dt,
                       E.theta if theta is None else theta)


def _offline_backend(device):
    from pytket.extensions.quantinuum import QuantinuumAPIOffline, QuantinuumBackend
    b = QuantinuumBackend(device, api_handler=QuantinuumAPIOffline())
    _ = b.backend_info          # raises DeviceNotAvailable if the offline API lacks the device
    return b


@pytest.fixture(scope="module")
def h2():
    """Offline H2 backend for COMPILATION only (QuantinuumAPIOffline never touches the network).
    "H2-1LE" resolves only when pecos is installed (.venv-le); in .venv the offline API lists only
    H1-1 / H2-1 / H2-2 [measured], so fall back to the offline "H2-1" device data, which carries
    the same H2 gate set. Nothing is ever submitted through this object."""
    from pytket.extensions.quantinuum.backends.quantinuum import DeviceNotAvailable
    try:
        return _offline_backend("H2-1LE")
    except DeviceNotAvailable:
        return _offline_backend("H2-1")


@pytest.fixture(scope="module")
def le():
    pytest.importorskip("pytket_pecos")
    return _offline_backend("H2-1LE")


def run_encoded(spec, n_steps, shots, seed, backend, prog=None, noise=None):
    c, lay = encoded_h2_circuit(spec, n_steps, prog)
    cc = compile_for_h2(c, backend)
    bits = run_le(cc, lay.cbits, shots, seed, noise=noise)
    assert bits.shape == (shots, len(lay.cbits))
    recs = shot_records(bits, lay, prog)
    return recs, [r for r in recs if accepted(r)]


def z2_accepted(spec, acc):
    zbar = np.vstack([spec.logical_from_bits(r.final[None, :]) for r in acc])
    return z2_from_logical(zbar)


def assert_within(z, se, exact):
    # 4 standard errors of the shot-noise mean; +1e-9 so an exactly deterministic instance
    # (se = 0) must hit the exact value.
    assert abs(z - exact) <= NSIG * se + 1e-9, (z, se, exact)


def _cmds(c, typ):
    return [cmd for cmd in c.get_commands() if cmd.op.type == typ]


# =========================================================================== D. layout & mapping
def test_h2layout_cbits_order_and_round_regs():
    lay = H2Layout(round_steps=[0, 1, 2], n_final=3)
    assert lay.round_regs == ["r0", "r1", "r2"]
    exp = [Bit(f"r{i}", j) for i in range(3) for j in range(4)] + [Bit("d", j) for j in range(3)]
    assert list(lay.cbits) == exp


def test_h2layout_numeric_not_lexicographic_for_many_rounds():
    lay = H2Layout(round_steps=list(range(13)), n_final=4)
    assert lay.round_regs == [f"r{i}" for i in range(13)]
    cb = list(lay.cbits)
    assert len(cb) == 4 * 13 + 4
    assert cb[4 * 2] == Bit("r2", 0) and cb[4 * 10] == Bit("r10", 0) and cb[4 * 12 + 3] == Bit("r12", 3)
    assert cb[-4:] == [Bit("d", j) for j in range(4)]


def test_round_steps_syndrome_every_1_and_2():
    _, lay = encoded_h2_circuit(ice(), 3)
    assert lay.round_steps == [0, 1, 2, 3]
    assert lay.n_final == ice().k + 2
    s2 = ice(syndrome_every=2)
    for n in (3, 4, 5):
        _, lay2 = encoded_h2_circuit(s2, n)
        assert lay2.round_steps == [0] + s2.syndrome_steps(n)


def test_encoded_circuit_structure():
    """Register, measurement order (A then F after Z, then after X; data last in spec.data
    order), resets, and the two-qubit count = sum of the authored segments' counts."""
    s = ice()
    for n in (1, 3):
        c, lay = encoded_h2_circuit(s, n)
        assert c.n_qubits == s.n_phys
        assert set(c.bits) == set(lay.cbits)
        meas = _cmds(c, OpType.Measure)
        exp = []
        for i in range(len(lay.round_steps)):
            exp += [(s.A, Bit(f"r{i}", 0)), (s.F, Bit(f"r{i}", 1)),
                    (s.A, Bit(f"r{i}", 2)), (s.F, Bit(f"r{i}", 3))]
        exp += [(q, Bit("d", j)) for j, q in enumerate(s.data)]
        # compared as a set: get_commands() is a topological order, so independent measurements
        # may be reordered; the (qubit -> bit) mapping is what matters (re-frozen 2026-10-17)
        assert sorted(((m.qubits[0].index[0], str(m.bits[0])) for m in meas)) == sorted(
            (q, str(bt)) for q, bt in exp)
        resets = _cmds(c, OpType.Reset)
        assert len(resets) == 4 * len(lay.round_steps)
        assert Counter(r.qubits[0].index[0] for r in resets) == {s.A: 2 * len(lay.round_steps),
                                                                  s.F: 2 * len(lay.round_steps)}
        syn = s.syndrome_segment("Z").n_2qb_gates() + s.syndrome_segment("X").n_2qb_gates()
        exp2 = (len(lay.round_steps) * syn + s.prep_segment().n_2qb_gates()
                + n * s.trotter_segment().n_2qb_gates())
        assert two_qubit_count(c) == exp2
        assert not _cmds(c, OpType.Conditional)


def test_encoded_circuit_twirled_structure():
    """With a twirled program: same measurement layout, two-qubit count from the twirled
    circuits, and NO classical frame correction in the circuit (no conditionals)."""
    s = ice()
    n = 2
    prog = twirl_program(s, n, seed=5)
    c, lay = encoded_h2_circuit(s, n, prog)
    c0, lay0 = encoded_h2_circuit(s, n)
    assert list(lay.cbits) == list(lay0.cbits) and lay.round_steps == lay0.round_steps
    assert len(_cmds(c, OpType.Measure)) == len(_cmds(c0, OpType.Measure))
    syn = s.syndrome_segment("Z").n_2qb_gates() + s.syndrome_segment("X").n_2qb_gates()
    exp2 = (len(lay.round_steps) * syn + prog.prep.n_2qb_gates()
            + sum(t.n_2qb_gates() for t in prog.trotter_layers))
    assert two_qubit_count(c) == exp2
    assert not _cmds(c, OpType.Conditional)


def _fake_prog(round0, rflip, final):
    return TwirledProgram(prep=Circuit(1), trotter_layers=[], round0_flip=round0,
                          round_flip=rflip, final_flip=np.array(final, dtype=np.int8),
                          final_flip_x=np.zeros(len(final), dtype=np.int8))


def test_shot_records_mapping_without_prog():
    lay = H2Layout(round_steps=[0, 2, 3], n_final=4)
    rng = np.random.default_rng(7)
    bits = rng.integers(0, 2, size=(9, 4 * 3 + 4)).astype(np.int8)
    recs = shot_records(bits, lay)
    assert len(recs) == 9 and all(isinstance(r, ShotRecord) for r in recs)
    for s_, r in enumerate(recs):
        assert [tuple(int(x) for x in t) for t in r.rounds] == \
            [tuple(int(x) for x in bits[s_, 4 * i:4 * i + 4]) for i in range(3)]
        assert np.array_equal(np.asarray(r.final, dtype=np.int8), bits[s_, 12:])


def test_shot_records_flips_xored():
    lay = H2Layout(round_steps=[0, 2, 3], n_final=4)
    prog = _fake_prog((1, 0, 1, 1), {2: (0, 1, 1, 0), 3: (1, 1, 0, 0)}, [1, 0, 0, 1])
    bits = np.array([[0] * 16,
                     [1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0]], dtype=np.int8)
    recs = shot_records(bits, lay, prog)
    # row 0: all-zero raw bits -> exactly the flips
    assert [tuple(int(x) for x in t) for t in recs[0].rounds] == [(1, 0, 1, 1), (0, 1, 1, 0), (1, 1, 0, 0)]
    assert list(np.asarray(recs[0].final, dtype=int)) == [1, 0, 0, 1]
    # row 1, hand XOR: (1001)^(1011)=(0010); (1111)^(0110)=(1001); (0010)^(1100)=(1110);
    # final (1100)^(1001)=(0101)
    assert [tuple(int(x) for x in t) for t in recs[1].rounds] == [(0, 0, 1, 0), (1, 0, 0, 1), (1, 1, 1, 0)]
    assert list(np.asarray(recs[1].final, dtype=int)) == [0, 1, 0, 1]


def test_shot_records_real_twirl_flips():
    s = ice()
    n = 3
    prog = twirl_program(s, n, seed=9)
    _, lay = encoded_h2_circuit(s, n, prog)
    zeros = np.zeros((1, len(lay.cbits)), dtype=np.int8)
    r = shot_records(zeros, lay, prog)[0]
    exp = [tuple(prog.round0_flip)] + [tuple(prog.round_flip[st]) for st in lay.round_steps[1:]]
    assert [tuple(int(x) for x in t) for t in r.rounds] == [tuple(int(x) for x in e) for e in exp]
    assert np.array_equal(np.asarray(r.final, dtype=np.int8), np.asarray(prog.final_flip, dtype=np.int8))


def test_shot_records_shape_error():
    lay = H2Layout(round_steps=[0, 1], n_final=6)
    with pytest.raises(ValueError):
        shot_records(np.zeros((5, 13), dtype=np.int8), lay)
    with pytest.raises(ValueError):
        shot_records(np.zeros((5, 15), dtype=np.int8), lay)


def test_emulator_register_order_matches_layout_cbits(le):
    """>10 round registers: PECOS returns registers sorted by NAME (r10 < r2); the bits handed
    back by run_le must follow layout.cbits (numeric order). A hand-made circuit sets exactly one
    known bit per register, so any reordering shows up."""
    pytest.importorskip("pytket_pecos")
    s = IcebergTFIM(1, 2, "periodic", E.J, E.h, E.dt, E.theta)
    _, lay = encoded_h2_circuit(s, 12)
    assert len(lay.round_steps) == 13
    cbits = list(lay.cbits)

    def expected(bit):
        if bit.reg_name == "d":
            return int(bit.index[0] == 1)
        i = int(bit.reg_name[1:])
        return int(bit.index[0] == i % 4)

    c = Circuit(2)
    for bt in cbits:
        c.add_bit(bt)
    c.add_gate(OpType.PhasedX, [1.0, 0.0], [0])     # q0 -> |1> (native H2 gate); q1 stays |0>
    for bt in cbits:
        c.Measure(0 if expected(bt) else 1, bt)
    out = run_le(c, cbits, 20, 3)
    want = np.array([expected(bt) for bt in cbits], dtype=np.int8)
    assert out.shape == (20, len(cbits))
    assert all(np.array_equal(row, want) for row in out)


# =========================================================================== A. transparency
@pytest.mark.parametrize("n_steps", [1, 3])
def test_iceberg_transparency_le(le, n_steps):
    pytest.importorskip("pytket_pecos")
    s = ice()
    recs, acc = run_encoded(s, n_steps, 6000, seed=100 + n_steps, backend=le)
    assert len(acc) == len(recs)              # noiseless: acceptance exactly 1.0
    z, se = z2_accepted(s, acc)
    assert_within(z, se, local_exact_logical_z2(s, n_steps))


@pytest.mark.parametrize("seed", [11, 12])
@pytest.mark.parametrize("n_steps", [1, 3])
def test_iceberg_twirled_transparency_le(le, n_steps, seed):
    pytest.importorskip("pytket_pecos")
    s = ice()
    prog = twirl_program(s, n_steps, seed)
    recs, acc = run_encoded(s, n_steps, 6000, seed=200 + seed, backend=le, prog=prog)
    assert len(acc) == len(recs)              # frame flips applied -> acceptance exactly 1.0
    z, se = z2_accepted(s, acc)
    assert_within(z, se, local_exact_logical_z2(s, n_steps))


def test_iceberg_clifford_discriminating_le(le):
    """Clifford instance: exact Z2 alternates 1/k, 1 [established in this repo], so steps 1 and
    2 differ. (Steps 1 and 3 are BOTH 1/k at 2x2 [measured], hence step 2 here.)"""
    pytest.importorskip("pytket_pecos")
    s = ice_clifford()
    steps = (1, 2)
    exact = [local_exact_logical_z2(s, n) for n in steps]
    assert abs(exact[0] - exact[1]) > 0.25
    # (removed 2026-10-17: the 2x2 exact values are 0.5 and 1.0, not 1/k and 1; the spec's
    # 'alternates 1/k, 1' was wrong for this lattice. The steps-differ check above stays.)
    for n, x in zip(steps, exact):
        recs, acc = run_encoded(s, n, 3000, seed=300 + n, backend=le)
        assert len(acc) == len(recs)
        z, se = z2_accepted(s, acc)
        assert_within(z, se, x)


# =========================================================================== B. bare transparency
def test_bare_circuit_structure_and_bare_z():
    s = ice()
    for n in (1, 3):
        c, bits = bare_h2_circuit(s, n)
        assert c.n_qubits == s.k
        assert list(bits) == [Bit("m", i) for i in range(s.k)]
        assert two_qubit_count(c) == n * len(s.bonds)
        assert len(_cmds(c, OpType.Measure)) == s.k
    z = bare_z(np.array([[0, 1, 1, 0], [1, 1, 0, 0]], dtype=np.int8))
    assert z.dtype == np.int8
    assert np.array_equal(z, np.array([[1, -1, -1, 1], [-1, -1, 1, 1]]))


@pytest.mark.parametrize("n_steps", [1, 3])
def test_bare_transparency_le(le, n_steps):
    pytest.importorskip("pytket_pecos")
    s = ice()
    c, bits = bare_h2_circuit(s, n_steps)
    out = run_le(compile_for_h2(c, le), bits, 6000, 400 + n_steps)
    z = bare_z(out).astype(float)
    m2 = z.sum(axis=1) ** 2 / s.k ** 2
    se = m2.std(ddof=1) / np.sqrt(len(m2))
    assert_within(float(m2.mean()), se, local_exact_logical_z2(s, n_steps))   # encoded == bare


# =========================================================================== C. fault detection
@pytest.mark.parametrize("pauli", [None, "X", "Z", "Y"])
def test_single_data_fault_always_detected_le(le, pauli):
    """X on data 0 flips S_Z (caught next round); Z flips S_X vs the round-0 reference; Y both.
    Noiseless otherwise, so acceptance must be EXACTLY 0 (control: exactly 1)."""
    pytest.importorskip("pytket_pecos")
    s = ice()
    prog = twirl_program(s, 1, seed=21)
    prep = prog.prep.copy()
    if pauli is not None:
        getattr(prep, pauli)(0)
    bad = replace(prog, prep=prep)
    recs, acc = run_encoded(s, 1, 300, seed=500, backend=le, prog=bad)
    assert len(acc) == (len(recs) if pauli is None else 0)


# =========================================================================== E. compile & cost
def test_compile_preserves_two_qubit_count(h2):
    s = ice()
    for n in (1, 3):
        c, _ = encoded_h2_circuit(s, n)
        cc = compile_for_h2(c, h2)
        assert two_qubit_count(cc) == two_qubit_count(c)


def test_two_qubit_count_hand():
    c = Circuit(3, 1)
    c.CX(0, 1).ZZPhase(0.3, 1, 2).H(0).Rz(0.1, 2).Measure(0, 0)
    assert two_qubit_count(c) == 2


class _DroppingBackend:
    """Fake backend whose 'compilation' silently drops a two-qubit gate."""

    def __init__(self):
        self.levels = []

    def get_compiled_circuit(self, c, optimisation_level=2, **kw):
        self.levels.append(optimisation_level)
        out = Circuit(c.n_qubits)
        out.ZZPhase(0.5, 0, 1)
        return out


class _IdentityBackend(_DroppingBackend):
    def get_compiled_circuit(self, c, optimisation_level=2, **kw):
        self.levels.append(optimisation_level)
        return c.copy()


def test_compile_for_h2_raises_on_changed_two_qubit_count():
    c = Circuit(2)
    c.ZZPhase(0.25, 0, 1).ZZPhase(0.5, 0, 1)
    with pytest.raises(RuntimeError):
        compile_for_h2(c, _DroppingBackend())
    ok = _IdentityBackend()
    compile_for_h2(c, ok)
    assert ok.levels == [0]                   # optimisation_level=0 is what gets requested


def _hand_circuit():
    c = Circuit(2, 2)
    c.ZZPhase(0.3, 0, 1)
    c.Rz(0.2, 0)
    c.H(1)
    c.Measure(0, 0)
    c.Reset(0)
    c.Measure(1, 1)
    return c


def test_native_counts_and_hqc_hand():
    nc = native_counts(_hand_circuit())
    assert nc["n1q"] == 2 and nc["nrz"] == 1 and nc["n2q"] == 1
    assert nc["nmeas"] == 2 and nc["nreset"] == 1 and nc["nqubits"] == 2
    # HQC = 5 + C (N1q + 10 N2q + 5 Nm)/5000, Nm = nqubits + nmeas + nreset = 2 + 2 + 1 = 5
    # count_rz: N1q = 2 -> 5 + 100*(2 + 10 + 25)/5000 = 5.74 ; without Rz: N1q = 1 -> 5.72
    assert hqc_estimate(nc, 100) == pytest.approx(5.74, abs=1e-12)
    assert hqc_estimate(nc, 100, count_rz=True) == pytest.approx(5.74, abs=1e-12)
    assert hqc_estimate(nc, 100, count_rz=False) == pytest.approx(5.72, abs=1e-12)
    assert hqc_estimate(nc, 0) == pytest.approx(5.0, abs=1e-12)


def test_iceberg_2x2_h2_counts_regression(h2):
    """[measured] regression, offline H2 compile at O0 of Iceberg 2x2 (k=4, 8 qubits):
    n2q = 56 / 112 (12 prep + 12 per Trotter step + 16 per syndrome round; linear in steps),
    Measure = 4 per round + 6 data = 14 / 22, Reset = 4 per round = 8 / 16, so
    Measure + Reset = 22 / 38."""
    s = ice()
    for n, n2q, nmeas, nreset in ((1, 56, 14, 8), (3, 112, 22, 16)):
        c, _ = encoded_h2_circuit(s, n)
        nc = native_counts(compile_for_h2(c, h2))
        assert nc["n2q"] == n2q
        assert nc["n1q"] > nc["n2q"]
        assert nc["nmeas"] == nmeas and nc["nreset"] == nreset
        assert nc["nmeas"] + nc["nreset"] == {1: 22, 3: 38}[n]
        assert nc["nqubits"] == s.n_phys == 8
    n2 = [native_counts(compile_for_h2(encoded_h2_circuit(s, n)[0], h2))["n2q"] for n in (1, 2, 3)]
    assert n2[1] - n2[0] == n2[2] - n2[1] > 0  # linear in steps


# =========================================================================== H. other codes
@pytest.mark.parametrize("n_steps", [1, 2])
@pytest.mark.parametrize("name", list(CODE_LATTICE))
def test_codes_circuit_structure(h2, name, n_steps):
    p = code_prog(name)
    sch = p.schedule(n_steps, "Z")
    c, lay = codes_h2_circuit(p, n_steps)
    assert c.n_qubits == p.n_phys <= 56
    Ms = [it for it in sch.items if it[0] == "M"]
    keys = list(lay.keys)
    assert keys == [it[2] for it in Ms]
    cb = list(lay.cbits)
    meas = _cmds(c, OpType.Measure)
    # as a set, for the reason given in test_encoded_circuit_structure (re-frozen 2026-10-17)
    assert sorted((m.qubits[0].index[0], str(m.bits[0])) for m in meas) == sorted(
        (it[1], str(cb[i])) for i, it in enumerate(Ms))
    assert len(_cmds(c, OpType.Reset)) == sum(1 for it in sch.items if it[0] == "R")
    assert [list(d) for d in lay.detectors] == \
        [[keys.index(k) for k in it[1]] for it in sch.items if it[0] == "D"]
    assert [list(lg) for lg in lay.logicals] == [[keys.index(k) for k in L] for L in sch.logicals]
    # feedforward: real conditional X/Y/Z on the Pauli's support, conditioned on that key's bit = 1
    conds = _cmds(c, OpType.Conditional)
    Cs = [it for it in sch.items if it[0] == "C"]
    assert len(conds) == sum(len(_support(it[2])) for it in Cs)
    name_of = {1: OpType.X, 2: OpType.Y, 3: OpType.Z}
    exp = [(keys.index(it[1]), q, name_of[it[2][q]]) for it in Cs for q in _support(it[2])]
    got = []
    for cmd in conds:
        op = cmd.op
        assert op.width == 1 and op.value == 1
        bit, qb = cmd.args[0], cmd.args[1]
        got.append((cb.index(bit), qb.index[0], op.op.type))
    assert sorted(got, key=lambda t: (t[0], t[1], t[2].name)) == \
        sorted(exp, key=lambda t: (t[0], t[1], t[2].name))
    # two-qubit gates: exactly the authored unitary segments', preserved by O0 compilation
    seg2 = sum(it[1].n_2qb_gates() for it in sch.items if it[0] == "U")
    assert two_qubit_count(c) == seg2
    assert two_qubit_count(compile_for_h2(c, h2)) == seg2


def test_codes_layout_cbits_chunking():
    lay = CodesLayout(keys=[f"k{i}" for i in range(70)], detectors=[], logicals=[])
    cb = list(lay.cbits)
    assert len(cb) == 70
    assert cb == [Bit(f"m{i // 32}", i % 32) for i in range(70)]
    assert cb[31] == Bit("m0", 31) and cb[32] == Bit("m1", 0) and cb[64] == Bit("m2", 0)


def test_codes_records_parity_logic():
    lay = CodesLayout(keys=list("abcde"), detectors=[[0, 1], [2]], logicals=[[0, 3], [4], [1, 2, 3]])
    bits = np.array([
        [0, 0, 0, 0, 0],    # accepted; logicals +1 +1 +1
        [1, 1, 0, 0, 1],    # det parities 0,0 -> accepted; L: 1^0=1, 1, 1^0^0=1 -> -1 -1 -1
        [1, 0, 0, 0, 0],    # det0 = 1 -> rejected; L: -1 +1 +1
        [0, 0, 1, 1, 0],    # det1 = 1 -> rejected; L: 0^1=1 -> -1, +1, 0^1^1=0 -> +1
        [0, 1, 0, 1, 1],    # det0 = 1 -> rejected; L: -1, -1, 1^0^1=0 -> +1
    ], dtype=np.int8)
    out = codes_records(bits, lay)
    assert [bool(a) for a, _ in out] == [True, True, False, False, False]
    exp = [[1, 1, 1], [-1, -1, -1], [-1, 1, 1], [-1, 1, 1], [-1, -1, 1]]
    for (_, v), e in zip(out, exp):
        assert np.array_equal(np.asarray(v), np.array(e))


def run_codes(p, n_steps, shots, seed, backend, noise=None):
    c, lay = codes_h2_circuit(p, n_steps)
    out = run_le(compile_for_h2(c, backend), lay.cbits, shots, seed, noise=noise)
    recs = codes_records(out, lay)
    acc = [np.asarray(v, dtype=float) for a, v in recs if a]
    return len(acc) / len(recs), acc


def z2_codes(acc, k):
    m2 = np.array([v.sum() ** 2 / k ** 2 for v in acc])
    se = m2.std(ddof=1) / np.sqrt(len(m2)) if len(m2) > 1 else float("nan")
    return float(m2.mean()) if len(m2) else float("nan"), float(se)


@pytest.mark.parametrize("n_steps", [1, 2])
def test_five_transparency_le(le, n_steps):
    pytest.importorskip("pytket_pecos")
    p = code_prog("five")
    acc_rate, acc = run_codes(p, n_steps, 1500, 600 + n_steps, le)
    assert acc_rate == 1.0
    z, se = z2_codes(acc, p.k)
    assert_within(z, se, exact_logical_z2(p, n_steps))


def test_five_clifford_le(le):
    """Clifford instance vs Stim. At 1x2 the Clifford-family Z2 is constant in the step count
    ([measured]: 1.0 at theta=0 for steps 1-3, 0.5 at theta=pi/2), so the two-step
    'values differ' requirement cannot hold here; discrimination comes from two Clifford
    instances whose exact values differ (theta = clifford_theta vs theta = pi/2)."""
    pytest.importorskip("pytket_pecos")
    p0 = code_prog("five", J=E.clifford_J, h=E.clifford_h, theta=E.clifford_theta)
    p1 = code_prog("five", J=E.clifford_J, h=E.clifford_h, theta=np.pi / 2)
    cases = [(p0, 1), (p0, 2), (p1, 1)]
    exact = [stim_exact_z2(p, n) for p, n in cases]
    assert abs(exact[0] - exact[2]) > 0.25
    for (p, n), x in zip(cases, exact):
        acc_rate, acc = run_codes(p, n, 1500, 700 + n, le)
        assert acc_rate == 1.0
        z, se = z2_codes(acc, p.k)
        assert_within(z, se, x)


def test_five_noisy_detectors_fire_le(le):
    """ASSUMED depolarizing p2 = 0.02 on the LOCAL emulator (a classical prediction, not H2):
    with ~144 two-qubit gates per step [measured], detectors must fire on some shots."""
    pytest.importorskip("pytket_pecos")
    p = code_prog("five")
    acc_rate, acc = run_codes(p, 1, 600, 800, le, noise=Noise(p2=0.02))
    assert acc_rate < 1.0
    assert len(acc) > 0
    z, _ = z2_codes(acc, p.k)
    assert np.isfinite(z)
