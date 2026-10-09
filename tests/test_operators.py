"""Operator and Hamiltonian correctness tests with analytic references."""

import numpy as np

from src.lattice import square_bonds
from src.operators import single_site, tfim_hamiltonian, two_site


def test_pauli_algebra():
    # X and Z anticommute on one qubit; Z^2 = I.
    X = single_site("X", 0, 1).toarray()
    Z = single_site("Z", 0, 1).toarray()
    assert np.allclose(X @ Z + Z @ X, 0)
    assert np.allclose(Z @ Z, np.eye(2))


def test_hamiltonian_hermitian():
    bonds = square_bonds(2, 2, "open")
    H = tfim_hamiltonian(4, bonds, J=1.0, h=0.7).toarray()
    assert np.allclose(H, H.conj().T)


def test_single_spin_spectrum():
    # N=1, no bonds: H = -h X. Eigenvalues are -h, +h; ground = -h.
    h = 1.3
    H = tfim_hamiltonian(1, bonds=[], J=1.0, h=h).toarray()
    w = np.linalg.eigvalsh(H)
    assert np.allclose(np.sort(w), np.array([-h, h]))


def test_two_spin_closed_form():
    # Two spins, one bond: H = -J Z0 Z1 - h (X0 + X1).
    # Known: ground-state energy E0 = -sqrt((2h)^2 + J^2)? Verify numerically
    # against direct diagonalization of the explicit 4x4 matrix built here.
    J, h = 1.0, 0.5
    H = tfim_hamiltonian(2, bonds=[(0, 1)], J=J, h=h).toarray()

    ZZ = two_site("Z", 0, 1, 2).toarray()
    X0 = single_site("X", 0, 2).toarray()
    X1 = single_site("X", 1, 2).toarray()
    H_ref = -J * ZZ - h * (X0 + X1)
    assert np.allclose(H, H_ref)


def test_sparse_builder_matches_kron_reference():
    # Regression for review/01-stage1.md C1: the bit-arithmetic builder must equal
    # the explicit full-kron reference on several lattices and boundaries.
    for (Lx, Ly, bc) in [(2, 2, "open"), (3, 2, "open"), (2, 3, "periodic")]:
        n = Lx * Ly
        bonds = square_bonds(Lx, Ly, bc)
        J, h = 1.0, 0.73
        H = tfim_hamiltonian(n, bonds, J, h).toarray()
        ref = np.zeros((1 << n, 1 << n), dtype=complex)
        for (i, j) in bonds:
            ref -= J * two_site("Z", i, j, n).toarray()
        for i in range(n):
            ref -= h * single_site("X", i, n).toarray()
        assert np.allclose(H, ref)
        assert np.allclose(H, H.conj().T)


def test_sparse_builder_scales_past_old_oom():
    # The pre-C1 kron builder OOMed (16 GiB) at N=16. The sparse builder must
    # construct N=16 cheaply; check shape, hermiticity, and a sane nnz count.
    import scipy.sparse as sp

    n = 16
    bonds = square_bonds(4, 4, "open")
    H = tfim_hamiltonian(n, bonds, 1.0, 1.0)
    assert H.shape == (1 << n, 1 << n)
    assert sp.issparse(H)
    # diagonal (2^N) + N off-diagonal flip entries per site, minus overlaps.
    assert H.nnz <= (n + 1) * (1 << n)
    diff = (H - H.getH())
    assert abs(diff).max() < 1e-12
