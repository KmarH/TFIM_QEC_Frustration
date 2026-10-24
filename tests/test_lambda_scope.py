"""FROZEN test spec (test-first, written 2026-10-24 BEFORE the change) for DECIDED-9: the noise
multiplier lambda amplifies EVERY two-qubit gate, identically in the trajectory simulator, the Stim
rate table and the pytket circuit (review/18 F3, F11).

SPEC
 L1 `src.q3_scaling.CANONICAL_2Q_SCOPE` is the sorted tuple of every two-qubit noise-tag class
    (tags ending "-cx" or "-zz") present in the bare and Iceberg Q3 programs, and
    `_NAMED_SCOPES["2q"]` equals it. [measured 2026-10-24: ("rot-cx", "rot-zz", "syn-cx")]
 L2 The count of two-qubit commands in the encoded schedule (what run_iceberg_scaled amplifies)
    equals the count of two-qubit Stim noise locations in that scope (196 at N = 12, one step).
 L3 `src.noise_scaling.scaled_stim_rates`'s default scope and `config.noise_scaling.fold_scope` are
    the canonical scope; `prefilter_grid` accepts `scope=` and defaults to "2q".
 L4 `src.noise_scaling.insert_paulis` inserts before EVERY two-qubit gate (CX as well as
    ZZPhase), at the same place as run_iceberg_scaled (before the gate); on a ZZPhase-only circuit
    it is identical, draw for draw, to the previous ZZPhase-only behaviour.
 L5 lambda = 1 changes nothing.

Classical bookkeeping only; nothing here is an H2 result.
"""
import collections
import inspect

import numpy as np
from pytket import Circuit, OpType

import src.encoded_codes as ec
from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates
from src.noise_scaling import _draw, insert_paulis, scaled_stim_rates
from src.noisy_q3 import TriangularBareTFIM, make_iceberg
from src.q3_scaling import (
    _NAMED_SCOPES,
    CANONICAL_2Q_SCOPE,
    SIZE_TO_CASE,
    initial_spins,
    prefilter_grid,
)

NOISE = NoiseRates(p2=1e-3, p1=1e-4, pm=1e-4, p_init=1e-4, zz_bias=0.3)


def _programs(n):
    Lx, Ly, kind = SIZE_TO_CASE[n]
    d = TriangularDimers(Lx, Ly)
    s0 = initial_spins(d, kind, CONFIG.ceilings.ed_max_spins)
    q3 = CONFIG.q3
    return (make_iceberg(d, s0, q3.J, q3.noisy_h, q3.dt),
            TriangularBareTFIM(Lx, Ly, "periodic", q3.J, q3.noisy_h, q3.dt, 0.0))


def _stim_2q_counts(prog):
    cnt = collections.Counter()
    for ins in ec.to_stim(prog.schedule(1, "Z"), NOISE).flattened():
        if ins.tag:
            cls = ins.tag.split(":")[0]
            if cls.endswith(("-cx", "-zz")):
                cnt[cls] += len(ins.targets_copy()) // 2
    return cnt


def test_l1_canonical_scope_is_every_two_qubit_class():
    ice, bare = _programs(12)
    classes = set(_stim_2q_counts(ice)) | set(_stim_2q_counts(bare))
    assert tuple(sorted(classes)) == CANONICAL_2Q_SCOPE
    assert tuple(sorted(_NAMED_SCOPES["2q"])) == CANONICAL_2Q_SCOPE


def test_l2_simulator_and_stim_amplify_the_same_number_of_locations():
    ice, _ = _programs(12)
    n_sim = 0
    for it in ice.schedule(1, "Z").items:
        if it[0] == "U":
            n_sim += sum(1 for cmd in it[1].get_commands() if len(cmd.qubits) == 2)
    cnt = _stim_2q_counts(ice)
    n_stim = sum(v for k, v in cnt.items() if k in CANONICAL_2Q_SCOPE)
    assert n_sim == n_stim == 196, (n_sim, n_stim, dict(cnt))


def test_l3_defaults_are_the_canonical_scope():
    default = inspect.signature(scaled_stim_rates).parameters["scope"].default
    assert tuple(sorted(default)) == CANONICAL_2Q_SCOPE
    assert tuple(sorted(CONFIG.noise_scaling.fold_scope)) == CANONICAL_2Q_SCOPE
    assert inspect.signature(prefilter_grid).parameters["scope"].default == "2q"


def test_l4_insertion_reaches_cx_and_lands_before_the_gate():
    c = Circuit(2)
    c.CX(0, 1)
    c.ZZPhase(0.3, 0, 1)
    out = insert_paulis(c, 2.0, {"XX": 1.0}, np.random.default_rng(0))
    types = [cmd.op.type for cmd in out.get_commands()]
    assert types == [OpType.X, OpType.X, OpType.CX, OpType.X, OpType.X, OpType.ZZPhase], types


def _old_insert(circuit, lam, model, rng):
    """The pre-DECIDED-9 behaviour, kept here as the oracle for ZZPhase-only circuits."""
    ops = {"X": OpType.X, "Y": OpType.Y, "Z": OpType.Z}
    out = Circuit(circuit.n_qubits, circuit.n_bits)
    for cmd in circuit.get_commands():
        if cmd.op.type == OpType.ZZPhase:
            lab = _draw(model, lam - 1, rng)
            if lab:
                for q, x in zip(cmd.qubits, lab, strict=True):
                    if x != "I":
                        out.add_gate(ops[x], [q])
        out.add_gate(cmd.op, cmd.args)
    return out


def test_l4_zzphase_only_circuits_are_unchanged_draw_for_draw():
    c = Circuit(4)
    for _ in range(5):
        for q in range(4):
            c.Rx(0.1, q)
        for i, j in ((0, 1), (1, 2), (2, 3), (3, 0)):
            c.ZZPhase(0.2, i, j)
    model = {"ZZ": 0.05, "XI": 0.03, "IY": 0.02}
    new = insert_paulis(c, 3.0, model, np.random.default_rng(11))
    old = _old_insert(c, 3.0, model, np.random.default_rng(11))
    assert new.get_commands() == old.get_commands()


def test_l5_lambda_one_changes_nothing():
    c = Circuit(2)
    c.CX(0, 1)
    c.ZZPhase(0.3, 0, 1)
    out = insert_paulis(c, 1.0, {"XX": 0.5}, np.random.default_rng(0))
    assert out.get_commands() == c.get_commands()
