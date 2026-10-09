"""Stage 2 QEC tests: Iceberg code algebra, Stim syndrome circuits, on-paper codes.

All checks are independent of the implementation's own assertions: they confirm
the stabilizer group, the logical algebra, and the operational distance-2
detection both algebraically (verify.py) and at circuit level (syndrome.py).
"""

import pytest

from src.qec.concatenated import iceberg_detection_distance, min_undetected_weight
from src.qec.iceberg import IcebergCode
from src.qec.on_paper_codes import (
    five_qubit_logicals,
    five_qubit_stabilizers,
    steane_logicals,
    steane_stabilizers,
)
from src.qec.syndrome import clean_run_is_silent, detects_error
from src.qec.verify import verify_code


def _verify_iceberg(k):
    c = IcebergCode(k)
    return verify_code(
        f"Iceberg k={k}",
        c.n,
        c.stabilizers(),
        [c.logical_x(i) for i in range(k)],
        [c.logical_z(i) for i in range(k)],
    )


@pytest.mark.parametrize("k", [2, 4, 6])
def test_iceberg_algebra(k):
    rep = _verify_iceberg(k)
    assert rep.stabilizers_commute
    assert rep.logicals_commute_with_stabilizers
    assert rep.logical_symplectic_ok
    assert rep.all_weight1_detected
    assert rep.ok


def test_iceberg_requires_even_k():
    with pytest.raises(ValueError):
        IcebergCode(3)
    with pytest.raises(ValueError):
        IcebergCode(0)


@pytest.mark.parametrize("k", [2, 4])
def test_iceberg_detection_distance_is_two(k):
    assert iceberg_detection_distance(k, max_weight=3) == 2


@pytest.mark.parametrize("k", [2, 4])
def test_syndrome_clean_run_silent(k):
    assert clean_run_is_silent(IcebergCode(k))


@pytest.mark.parametrize("k", [2, 4])
def test_syndrome_detects_every_weight1_error(k):
    c = IcebergCode(k)
    for q in range(c.n):
        for p in ("X", "Y", "Z"):
            assert detects_error(c, p, q), f"missed {p} on qubit {q} (k={k})"


def test_five_qubit_code_is_distance_three():
    sx, sz = five_qubit_logicals()
    rep = verify_code("[[5,1,3]]", 5, five_qubit_stabilizers(), sx, sz)
    assert rep.stabilizers_commute
    assert rep.logicals_commute_with_stabilizers
    assert rep.all_weight1_detected
    assert min_undetected_weight(5, five_qubit_stabilizers(), max_weight=3) == 3


def test_steane_code_is_distance_three():
    sx, sz = steane_logicals()
    rep = verify_code("[[7,1,3]]", 7, steane_stabilizers(), sx, sz)
    assert rep.stabilizers_commute
    assert rep.logicals_commute_with_stabilizers
    assert rep.all_weight1_detected
    assert min_undetected_weight(7, steane_stabilizers(), max_weight=3) == 3
