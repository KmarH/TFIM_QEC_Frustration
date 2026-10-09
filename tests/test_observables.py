"""Observable tests against dense operators and known product states."""

import numpy as np

from src.backends import product_state
from src.lattice import square_bonds
from src.observables import (
    energy,
    energy_dense,
    expval_x,
    expval_z,
    expval_zz,
    magnetization_variance_z,
    total_magnetization_z,
    two_point_correlations_z,
)
from src.operators import single_site, two_site


def test_expvals_on_all_up():
    # |00..0>: every <Z_i> = +1, <X_i> = 0, <Z_iZ_j> = +1.
    n = 4
    psi = product_state(n, "all_up")
    assert all(abs(expval_z(psi, n, i) - 1.0) < 1e-12 for i in range(n))
    assert all(abs(expval_x(psi, n, i)) < 1e-12 for i in range(n))
    assert abs(expval_zz(psi, n, 0, 3) - 1.0) < 1e-12
    assert abs(total_magnetization_z(psi, n) - n) < 1e-12


def test_variance_zero_on_product_eigenstate():
    # M_z is sharp on a Z-product state -> variance 0.
    n = 4
    psi = product_state(n, "neel")
    assert abs(magnetization_variance_z(psi, n)) < 1e-12


def test_expvals_match_dense_operator_random_state():
    n = 3
    rng = np.random.default_rng(1)
    psi = rng.normal(size=1 << n) + 1j * rng.normal(size=1 << n)
    psi /= np.linalg.norm(psi)

    for i in range(n):
        Z = single_site("Z", i, n).toarray()
        X = single_site("X", i, n).toarray()
        assert abs(expval_z(psi, n, i) - np.real(psi.conj() @ (Z @ psi))) < 1e-10
        assert abs(expval_x(psi, n, i) - np.real(psi.conj() @ (X @ psi))) < 1e-10

    ZZ = two_site("Z", 0, 2, n).toarray()
    assert abs(expval_zz(psi, n, 0, 2) - np.real(psi.conj() @ (ZZ @ psi))) < 1e-10


def test_energy_termwise_matches_dense():
    n = 4
    bonds = square_bonds(2, 2, "open")
    rng = np.random.default_rng(2)
    psi = rng.normal(size=1 << n) + 1j * rng.normal(size=1 << n)
    psi /= np.linalg.norm(psi)
    J, h = 1.0, 0.6
    assert abs(energy(psi, n, bonds, J, h) - energy_dense(psi, n, bonds, J, h)) < 1e-10


def test_connected_correlator_vanishes_on_product_state():
    # On a product state connected C_zz(i,j) = <Z_iZ_j> - <Z_i><Z_j> = 0.
    n = 4
    psi = product_state(n, "all_up")
    corr = two_point_correlations_z(psi, n, connected=True)
    assert all(abs(c) < 1e-12 for c in corr.values())
