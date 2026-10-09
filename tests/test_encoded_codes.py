"""Part B generic encoded-TFIM pipeline (handoff/04): Iceberg, Steane, 5-qubit, concat d=4.

Checks transparency, the whole-logical-state Stim<->execution consistency, the pure-error
frame correction, the MEASURED undetected-logical accounting against its first-order
derivation, the bare reference, and that the generic Iceberg reproduces Part A.
Selene runs are kept to the smallest code (5-qubit, 1x2) to bound test time.
"""

import numpy as np
import pytest

from src.backends import MemoryCeilingError
from src.compare import simulate_z2
from src.encoded_codes import (
    BareTFIM, EncodedTFIM, NoiseRates, exact_logical_z2, gate_counts, logical_pauli_table,
    make_code, min_weight_rep, pure_errors, run_local, run_selene, to_stim, undetected_rate_per_step,
)
from src.qec.verify import verify_code

LATTICE = {"iceberg": (2, 2), "steane": (1, 2), "five": (1, 2), "concat": (2, 2)}
PHYS = dict(boundary="periodic", J=1.0, h=2.0, dt=0.25, theta=np.pi / 6)


def prog(name, theta=np.pi / 6, J=1.0, h=2.0):
    a, b = LATTICE[name]
    return EncodedTFIM(make_code(name, a * b), a, b, "periodic", J, h, 0.25, theta)


@pytest.mark.parametrize("name", list(LATTICE))
def test_code_algebra(name):
    a, b = LATTICE[name]
    c = make_code(name, a * b)
    assert verify_code(c.name, c.n, c.stabilizers, c.logical_x, c.logical_z).ok


@pytest.mark.parametrize("name", list(LATTICE))
def test_pure_errors(name):
    c = make_code(name, 4)
    for i, e in enumerate(pure_errors(c)):
        for j, s in enumerate(c.stabilizers):
            assert e.commutes(s) == (i != j)
        assert all(e.commutes(L) for L in c.logical_x + c.logical_z)


def test_min_weight_reps_are_equivalent_and_short():
    p = prog("steane")
    for rep, op in [(p.rep_x(0), p.lx[0]), (p.readout_z(1), p.lz[1])]:
        quot = rep * op                    # rep = op * stabilizer product -> quotient in the group
        assert all(quot.commutes(s) for s in p.stabs)
        assert all(quot.commutes(L) for L in p.lx + p.lz)
    assert p.rep_x(0).weight == 3 and p.rep_zz(0, 1).weight == 6
    assert all(p.readout_z(l)[q] in (0, 3) for l in range(p.k) for q in range(p.n_data))


@pytest.mark.parametrize("name", list(LATTICE))
def test_encoding_transparency(name):
    p = prog(name)
    a, b = LATTICE[name]
    enc = [exact_logical_z2(p, s) for s in (1, 2)]
    assert np.allclose(enc, simulate_z2(a, b, "periodic", 1.0, 2.0, 0.25, np.pi / 6, [1, 2], 24), atol=1e-12)


@pytest.mark.parametrize("name", list(LATTICE))
def test_whole_logical_state_matches_stim_on_clifford_instance(name):
    p = prog(name, theta=np.pi / 2, J=np.pi, h=2 * np.pi)
    labels, sv, lv = logical_pauli_table(p, 2)
    assert np.allclose(sv, lv, atol=1e-12)
    assert np.sum(np.abs(sv[1:]) > 0.5) == 2 ** p.k - 1        # a full stabilizer state


@pytest.mark.parametrize("name", list(LATTICE))
def test_clean_stim_images_silent(name):
    for basis in "ZX":
        d, o = to_stim(prog(name).schedule(2, basis), NoiseRates()).compile_detector_sampler(seed=0) \
            .sample(64, separate_observables=True)
        assert not d.any() and not o.any()


def test_local_sim_noiseless_accepts_and_noise_discards():
    p = prog("five")
    rng = np.random.default_rng(0)
    sch = p.schedule(1, "Z")
    assert all(run_local(sch, NoiseRates(), rng)[0] for _ in range(20))
    noisy = [run_local(sch, NoiseRates(p2=0.005), rng)[0] for _ in range(60)]   # ~84 2q gates/step
    assert 0 < sum(noisy) < 60


def test_measured_accounting_matches_first_order_derivation():
    p2, p1 = 1e-3, 1e-4
    nz = NoiseRates(p2=p2, p1=p1, pm=p1, p_init=p1)
    # Iceberg 2x2: 12 logical ZZPhase gates per step, 3 of 15 components undetectable
    assert undetected_rate_per_step(prog("iceberg"), nz)["total"] == pytest.approx(12 * p2 * 3 / 15, rel=1e-6)
    # d=3 codes, 1x2: 5 rotation gadgets per step, (2/15 p2 + 1/3 p1) each — distance-independent
    for name in ("steane", "five"):
        r = undetected_rate_per_step(prog(name), nz)
        assert r["total"] == pytest.approx(5 * (2 / 15 * p2 + p1 / 3), rel=1e-6)
        assert set(k for k, v in r.items() if v and k != "total") <= {"rot-cx", "rot-1q"}
    # bare 2x2: every fault on 4 ZZ + 8 one-qubit locations is unprotected
    assert undetected_rate_per_step(BareTFIM(2, 2, **PHYS), nz)["total"] == pytest.approx(4 * p2 + 8 * p1, rel=1e-6)


def test_generic_iceberg_trotter_step_matches_part_a_cost():
    # Part A: 12 logical gates per step on 2x2 (8 field + 4 bonds), each one ZZPhase
    gc = gate_counts(prog("iceberg"))
    zz = sum(1 for it in prog("iceberg").schedule(2, "Z").items if it[0] == "U" and it[2] == "rot") \
        - sum(1 for it in prog("iceberg").schedule(1, "Z").items if it[0] == "U" and it[2] == "rot")
    assert zz == 12 and gc["meas"] == 4


def test_ceiling_refused_before_allocation():
    big = EncodedTFIM(make_code("steane", 4), 2, 2, "periodic", 1, 2, 0.25, 0.3)   # 30 qubits
    with pytest.raises(MemoryCeilingError):
        exact_logical_z2(big, 1, max_spins=24)
    with pytest.raises(MemoryCeilingError):
        run_selene(big, 1, 1, NoiseRates(), seed=0, max_spins=24)


def test_selene_generated_program_feedforward():
    p = prog("five", theta=0.0, J=np.pi, h=2 * np.pi)          # Z2 = 1 on every shot
    res = run_selene(p, 1, 40, NoiseRates(), seed=2, max_spins=24)
    assert all(a for a, _ in res)
    z = np.mean([(v.sum() ** 2) / p.k ** 2 for _, v in res])
    assert z == pytest.approx(exact_logical_z2(p, 1), abs=1e-12)     # deterministic instance
    noisy = run_selene(prog("five"), 1, 60, NoiseRates(p2=0.005), seed=3, max_spins=24)
    assert 0 < sum(a for a, _ in noisy) < 60


def test_noise_sensitivity_options_match_derivation():
    # Iceberg 2x2: 12 native ZZPhase logical gates per step. With a fraction eta of each 2q error
    # being ZZ, the undetectable share per gate is p2*(eta + (1-eta)*3/15) = p2*(0.2 + 0.8*eta);
    # a twirled over-rotation applies the gate's own (logical) generator w.p. overrot.
    p2, p1 = 1e-3, 1e-4
    base = dict(p2=p2, p1=p1, pm=p1, p_init=p1)
    for eta in (0.5, 0.9):
        r = undetected_rate_per_step(prog("iceberg"), NoiseRates(**base, zz_bias=eta))["total"]
        assert r == pytest.approx(12 * p2 * (0.2 + 0.8 * eta), rel=1e-6)
    r = undetected_rate_per_step(prog("iceberg"), NoiseRates(**base, overrot=1e-4))["total"]
    assert r == pytest.approx(12 * p2 * 0.2 + 12 * 1e-4, rel=1e-6)
    # bare: the bias only re-labels which unprotected Pauli occurs -> unchanged total
    b0 = undetected_rate_per_step(BareTFIM(2, 2, **PHYS), NoiseRates(**base))["total"]
    b1 = undetected_rate_per_step(BareTFIM(2, 2, **PHYS), NoiseRates(**base, zz_bias=0.9))["total"]
    assert b1 == pytest.approx(b0, rel=1e-9)
