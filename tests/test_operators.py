"""Operator and Hamiltonian correctness tests with analytic references."""

import numpy as np
import pytest

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
    """Two spins, one bond: H = -J Z0 Z1 - h (X0 + X1) (this project's convention).

    Analytic ground-state energy [derived]: in the symmetric sector with basis
    |00>, (|01>+|10>)/sqrt2, |11> the Hamiltonian is
        [[-J, -sqrt2 h, 0], [-sqrt2 h, +J, -sqrt2 h], [0, -sqrt2 h, -J]],
    and (|00> - |11>)/sqrt2 is an exact eigenvector with eigenvalue -J. In the
    remaining 2x2 block spanned by (|00>+|11>)/sqrt2 and (|01>+|10>)/sqrt2 the
    matrix is [[-J, -2h], [-2h, +J]], whose eigenvalues are +-sqrt(J^2 + 4h^2).
    The antisymmetric state (|01>-|10>)/sqrt2 is decoupled at energy +J. Hence
        E0 = -sqrt(J^2 + 4h^2),
    the lowest of {-sqrt(J^2+4h^2), -J, +J, +sqrt(J^2+4h^2)}.

    Review fix: this test previously built its reference from the same primitives
    it tests and never asserted the closed form, so it could not catch a wrong
    overall convention. The full spectrum is now checked against the analytic one.
    """
    J, h = 1.0, 0.5
    H = tfim_hamiltonian(2, bonds=[(0, 1)], J=J, h=h).toarray()

    ZZ = two_site("Z", 0, 1, 2).toarray()
    X0 = single_site("X", 0, 2).toarray()
    X1 = single_site("X", 1, 2).toarray()
    H_ref = -J * ZZ - h * (X0 + X1)
    assert np.allclose(H, H_ref)

    # The analytic closed form, asserted (not just "verified numerically").
    for J, h in [(1.0, 0.5), (1.0, 0.0), (0.0, 0.73), (1.0, 2.0), (-1.0, 0.4)]:
        w = np.linalg.eigvalsh(tfim_hamiltonian(2, bonds=[(0, 1)], J=J, h=h).toarray())
        root = np.sqrt(J * J + 4 * h * h)
        assert w[0] == pytest.approx(-root)
        assert np.allclose(np.sort(w), np.sort([-root, -J, J, root]))


def test_neel_product_state_is_a_checkerboard():
    """Regression (review): `product_state(..., "neel")` selected spins by `site % 2`,
    which for row-major n = y*Lx + x with EVEN Lx is `x % 2` — column stripes, giving
    sum_<ij> <Z_iZ_j> = 0 on the 4x4 periodic lattice instead of -32. A true
    checkerboard flips the (x + y) % 2 sublattice, so every one of the 32 bonds is
    anti-aligned. Measured here as the J=1, h=0 energy (= -sum ZZ) of the state."""
    from src.backends import product_state

    Lx = Ly = 4
    n = Lx * Ly
    bonds = square_bonds(Lx, Ly, "periodic")
    assert len(bonds) == 32
    H = tfim_hamiltonian(n, bonds, J=1.0, h=0.0)
    psi = product_state(n, "neel", Lx=Lx)
    sum_zz = -float(np.real(psi.conj() @ (H @ psi)))
    assert sum_zz == pytest.approx(-len(bonds))
    # all_up is the opposite extreme, and the 1D default still alternates.
    up = product_state(n, "all_up")
    assert -float(np.real(up.conj() @ (H @ up))) == pytest.approx(len(bonds))
    chain = product_state(4, "neel")
    assert np.argmax(np.abs(chain)) == 0b0101


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
