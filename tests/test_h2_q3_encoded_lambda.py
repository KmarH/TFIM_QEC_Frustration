"""The Iceberg-encoded H2 circuit at lambda > 1 (DECIDED-9, Stage 6b of the 2026-10-24 pass): the
circuit that would be submitted carries the same lambda insertion as the trajectory simulator
and the Stim rate table - before every two-qubit gate, 196 locations in the one-step N = 12
program (72 preparation CX once; then 60 ZZPhase + 32 syndrome CX per step) - while
its mid-circuit syndrome measurements, resets and conditionals pass through untouched.

Circuit bookkeeping only (no emulator, no Nexus); nothing here is an H2 result.
"""
import collections

import pytest
from pytket import OpType

from config import CONFIG
from src.dimers import TriangularDimers
from src.h2_q3 import iceberg_noise_scaled_circuits, triangular_iceberg_h2_circuit
from src.mcmc_baseline import initial_spins
from src.noise_scaling import _is_2q_gate

Q = CONFIG.q3


@pytest.fixture(scope="module")
def base():
    s0 = initial_spins(TriangularDimers(3, 4), "flippable", CONFIG.ceilings.ed_max_spins)
    c, _ = triangular_iceberg_h2_circuit(3, 4, s0, 1, Q.J, Q.noisy_h, Q.dt)
    return c


def test_encoded_circuit_has_the_196_locations_of_the_simulator_and_stim(base):
    assert sum(1 for cmd in base.get_commands() if _is_2q_gate(cmd)) == 196


def test_lambda_one_is_the_base(base):
    (sc,) = iceberg_noise_scaled_circuits(base, 1)
    assert sc.circuit == base


def test_every_two_qubit_gate_gets_its_insertion_and_nothing_else_moves(base):
    (sc,) = iceberg_noise_scaled_circuits(base, 3, model={"XX": 0.5}, seed=1)   # prob 2 * 0.5 = 1
    cmds = sc.circuit.get_commands()
    extra = collections.Counter(c.op.type for c in cmds) - collections.Counter(
        c.op.type for c in base.get_commands())
    assert extra == collections.Counter({OpType.X: 2 * 196})
    # get_commands() is a topological order, so each QUBIT's sequence is faithful: on both qubits
    # of every two-qubit gate, the command right before it must be an inserted X.
    last: dict = {}
    for cmd in cmds:
        if _is_2q_gate(cmd):
            assert all(last[q].op.type == OpType.X for q in cmd.qubits), str(cmd)
        for q in cmd.qubits:
            last[q] = cmd
    def per_wire(cs):           # each qubit's and bit's own command sequence, X excluded
        seq: dict = collections.defaultdict(list)
        for c in cs:
            if c.op.type != OpType.X:
                for a in c.args:
                    seq[str(a)].append(str(c))
        return dict(seq)
    assert per_wire(cmds) == per_wire(base.get_commands())
    assert [r.name for r in sc.circuit.c_registers] == [r.name for r in base.c_registers]


def test_instances_are_independent_and_reproducible(base):
    a = iceberg_noise_scaled_circuits(base, 3, instances=2, seed=5)
    b = iceberg_noise_scaled_circuits(base, 3, instances=2, seed=5)
    assert [x.circuit for x in a] == [x.circuit for x in b]
    assert a[0].circuit != a[1].circuit
