"""Trotter evolution tests against exact references.

Key validations:
  - exp(-iA dt/2) and the X-rotation layer each act correctly (unitary).
  - the full 2nd-order step converges to the exact propagator exp(-iHt) with
    the expected O(dt^2) global error as n_steps grows.
  - a single spin under H = -h X has a closed-form <Z(t)> we check exactly.
"""

import numpy as np
import scipy.sparse.linalg as sla

from src.lattice import square_bonds
from src.operators import tfim_hamiltonian
from src.trotter import apply_x_rotations, circuit_trotter2_step, evolve, ising_diagonal, trotter2_step
from src.observables import expval_z, total_z_sq_normalized


def test_norm_preserved():
    n = 4
    bonds = square_bonds(2, 2, "open")
    psi0 = np.zeros(1 << n, dtype=np.complex128)
    psi0[0] = 1.0
    final, _ = evolve(psi0, n, bonds, J=1.0, h=0.9, total_time=2.0, n_steps=50)
    assert abs(np.linalg.norm(final) - 1.0) < 1e-10


def test_x_rotation_matches_matrix():
    # exp(-i theta sum X) on N=3 vs dense matrix exponential of the X-sum.
    from src.operators import single_site

    n, theta = 3, 0.37
    psi = np.random.default_rng(0).normal(size=1 << n) + 0j
    psi /= np.linalg.norm(psi)

    got = apply_x_rotations(psi.copy(), n, theta)

    Xsum = sum(single_site("X", k, n) for k in range(n)).toarray()
    want = sla.expm(-1j * theta * Xsum) @ psi
    assert np.allclose(got, want, atol=1e-10)


def test_single_spin_analytic_dynamics():
    # N=1, H = -h X. Start |0> (Z=+1). Heisenberg: <Z(t)> = cos(2 h t).
    h, T = 1.1, 1.7
    psi0 = np.array([1.0, 0.0], dtype=np.complex128)
    final, _ = evolve(psi0, 1, bonds=[], J=1.0, h=h, total_time=T, n_steps=2000)
    got = expval_z(final, 1, 0)
    assert abs(got - np.cos(2 * h * T)) < 1e-4


def test_trotter_converges_to_exact():
    # 2nd-order Trotter error should fall ~ as 1/n_steps^2.
    n = 4
    bonds = square_bonds(2, 2, "open")
    J, h, T = 1.0, 0.8, 1.0
    H = tfim_hamiltonian(n, bonds, J, h)

    psi0 = np.zeros(1 << n, dtype=np.complex128)
    psi0[0] = 1.0
    exact = sla.expm_multiply(-1j * T * H, psi0)

    errs = []
    for steps in (10, 20, 40):
        final, _ = evolve(psi0, n, bonds, J, h, T, steps)
        errs.append(np.linalg.norm(final - exact))

    # Each doubling of steps should cut error by ~4x (2nd order). Allow slack.
    assert errs[0] > errs[1] > errs[2]
    ratio1 = errs[0] / errs[1]
    ratio2 = errs[1] / errs[2]
    assert ratio1 > 3.0 and ratio2 > 3.0
    assert errs[-1] < 1e-2


def test_circuit_trotter2_step_matches_compare_circuit_order():
    # Pin circuit_trotter2_step against src/compare.py's independent, gate-level
    # circuit-order evolution (X half, ZZ, X half) built from the same primitives.
    from src.compare import circuit_trotter_states

    n = 4
    bonds = square_bonds(2, 2, "open")
    J, h, dt = 1.3, 0.9, 0.25
    diag = ising_diagonal(n, bonds, J)

    psi = np.zeros(1 << n, dtype=np.complex128)
    psi[0] = 1.0   # |0...0>, matching compare.ry_product_state(theta=0)
    n_steps = 5
    for _ in range(n_steps):
        psi = circuit_trotter2_step(psi, n, diag, h, dt)

    step, want = next(circuit_trotter_states(
        n, bonds, J, h, dt, theta=0.0, record_steps=[n_steps], max_spins=n))
    assert step == n_steps
    assert np.allclose(psi, want, atol=1e-12)


def test_trotter_orderings_differ_at_reference_dt():
    # The two 2nd-order splittings are unitarily conjugate (same quasienergies),
    # but they read out different observables along the way. At the published
    # dt = 0.25, h*dt = 0.5 this must NOT be negligible, or the two orderings
    # could be silently swapped without anyone noticing (the bug this pins).
    n = 9
    bonds = square_bonds(3, 3, "periodic")
    J, h, dt = 1.0, 2.0, 0.25   # project convention (J, h) = (+1, +2) at dt = 0.25
    diag = ising_diagonal(n, bonds, J)

    theta = np.pi / 6
    single = np.array([np.cos(theta / 2), np.sin(theta / 2)], dtype=np.complex128)
    psi0 = np.ones(1, dtype=np.complex128)
    for _ in range(n):
        psi0 = np.kron(psi0, single)

    psi_zz, psi_circ = psi0.copy(), psi0.copy()
    for _ in range(8):
        psi_zz = trotter2_step(psi_zz, n, diag, h, dt)
        psi_circ = circuit_trotter2_step(psi_circ, n, diag, h, dt)

    z2_zz = total_z_sq_normalized(psi_zz, n)
    z2_circ = total_z_sq_normalized(psi_circ, n)
    assert abs(z2_zz - z2_circ) > 1e-2


def test_ising_diagonal_matches_operator():
    # Diagonal of A = -J sum ZZ vs the sparse operator's diagonal.
    from src.operators import two_site

    n = 3
    bonds = [(0, 1), (1, 2)]
    J = 1.0
    diag = ising_diagonal(n, bonds, J)
    A = sum(-J * two_site("Z", i, j, n) for (i, j) in bonds).toarray()
    assert np.allclose(diag, np.real(np.diag(A)))
