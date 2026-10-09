"""Concatenated Iceberg d=4 (handoff/01): code algebra, measured distance, FT gadget.

The distance and fault-tolerance claims are MEASURED here (code distance by
enumeration excluding stabilizer elements; circuit fault distance by exact DEM
search and by Stim's own search), never assumed from "2 x 2".
"""

import pytest

from src.qec.concatenated import ConcatenatedIceberg, code_distance
from src.qec.concatenated_gadget import (
    CSSSpec,
    NoiseModel,
    build_memory_circuit,
    discard,
    fault_distance,
    injected_signature,
    sample,
    undetected_low_weight_errors,
)
from src.qec.verify import verify_code

SIZES = [(2, 2), (2, 4), (4, 2)]


@pytest.mark.parametrize("ki,ko", SIZES)
def test_concatenated_algebra(ki, ko):
    c = ConcatenatedIceberg(ki, ko)
    assert (c.n, c.k) == ((ko + 2) * (ki + 2), ki * ko)
    assert len(c.stabilizers()) == c.n - c.k
    assert verify_code("cat", c.n, c.stabilizers(), c.logical_x(), c.logical_z()).ok


@pytest.mark.parametrize("ki,ko", SIZES)
def test_concatenated_code_distance_is_four(ki, ko):
    c = ConcatenatedIceberg(ki, ko)
    d, wit = code_distance(c.n, c.stabilizers(), c.logical_x() + c.logical_z(), max_weight=4)
    assert d == 4
    assert wit.weight == 4


def test_code_distance_probe_excludes_stabilizers():
    # review/02 M2: weight-4 inner stabilizers commute with every stabilizer but are
    # trivial; the witness must be a genuine logical (anticommute with some logical).
    c = ConcatenatedIceberg(2, 2)
    d, wit = code_distance(c.n, c.stabilizers(), c.logical_x() + c.logical_z())
    assert not all(wit.commutes(L) for L in c.logical_x() + c.logical_z())


@pytest.fixture(scope="module")
def spec():
    return CSSSpec.from_concatenated(ConcatenatedIceberg(2, 2))


@pytest.mark.parametrize("basis", ["Z", "X"])
def test_gadget_clean_run_silent(spec, basis):
    gc = build_memory_circuit(spec, basis, rounds=2)
    det, obs = gc.circuit.compile_detector_sampler(seed=1).sample(256, separate_observables=True)
    assert not det.any() and not obs.any()
    assert len(gc.detector_labels) == gc.circuit.num_detectors


def test_gadget_detects_all_weight_le3_errors(spec):
    assert undetected_low_weight_errors(spec, max_weight=3) == []


def test_weight4_logical_is_silent_and_flips_observables(spec):
    # inner X0X1 on blocks 0 and 1 = outer X0X1 on both outer blocks
    det, obs = injected_signature(spec, "Z", [("X", 0), ("X", 1), ("X", 4), ("X", 5)])
    assert not det.any() and obs.all()


@pytest.mark.parametrize("basis", ["Z", "X"])
def test_flagged_gadget_fault_distance_four(spec, basis):
    c = build_memory_circuit(spec, basis, 2, NoiseModel(1e-3)).circuit
    assert fault_distance(c, 3) is None  # no <=3-fault undetected logical
    st = c.search_for_undetectable_logical_errors(
        dont_explore_detection_event_sets_with_size_above=9999,
        dont_explore_edges_with_degree_above=9999,
        dont_explore_edges_increasing_symptom_degree=False,
        canonicalize_circuit_errors=True,
    )
    assert len(st) == 4


def test_unflagged_gadget_is_not_fault_tolerant_to_d4(spec):
    c = build_memory_circuit(spec, "Z", 2, NoiseModel(1e-3), use_flags=False).circuit
    assert fault_distance(c, 3) == 2


def test_fault_search_finds_known_distance3():
    # Steane [[7,1,3]] under code-capacity noise must give fault distance 3.
    h = [[3, 4, 5, 6], [1, 2, 5, 6], [0, 2, 4, 6]]
    st = CSSSpec(7, h, h, [list(range(7))], [list(range(7))],
                 groups=[("inner", "Z", [0, 1, 2]), ("inner", "X", [0, 1, 2])])
    cc = NoiseModel(p=0.01, p1_ratio=0, pm_ratio=0, idle_ratio=1.0, p2_ratio=0)
    assert fault_distance(build_memory_circuit(st, "Z", 2, cc).circuit, 3) == 3


def test_sample_and_discard(spec):
    gc = build_memory_circuit(spec, "Z", 2, NoiseModel(1e-3))
    r = sample(gc, "Z", 1e-3, 2000, seed=7)
    assert 0 < r.kept < r.shots
    lo, hi = r.discard_ci
    assert lo <= r.discard_rate <= hi
    assert discard([[0, 0], [0, 1]]).tolist() == [False, True]
