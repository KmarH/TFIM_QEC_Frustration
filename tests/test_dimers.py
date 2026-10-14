"""Stage 3 dimer / winding / Gauss-law observables (handoff/02) and the noisy-mitigation kit.

Every identity in src/dimers.py's docstring is checked exhaustively over the full basis on
small tori, the sector structure is cross-checked against ED/statevector dynamics, and the
(h/J)^2 scaling of the Gauss-law violation is MEASURED (fitted), not assumed.
"""

import numpy as np
import pytest
import scipy.sparse as sp
import scipy.sparse.linalg as sla

from src.dimers import TriangularDimers
from src.gauss_mitigation import (
    Targets, evolve_dm, evolve_trajectories, pauli_channel_dm, pec_gamma_single,
    richardson, single_error_detection, trotter_unitary,
)
from src.operators import tfim_hamiltonian
from src.trotter import evolve, ising_diagonal, trotter2_step

J_AFM = -1.0  # frustrated triangular model in our H = -J sum ZZ - h sum X convention


@pytest.fixture(scope="module", params=[(3, 3), (3, 4), (4, 3)])
def d(request):
    return TriangularDimers(*request.param)


def test_requires_periodic_torus():
    with pytest.raises(ValueError):
        TriangularDimers(2, 3)


def test_triangles_cover_each_bond_once_per_sublattice(d):
    seen = {b: [] for b in d.bonds}
    for sub, sites, bonds in d.triangles:
        assert len(set(sites)) == 3
        for b in bonds:
            assert b[0] in sites and b[1] in sites
            seen[b].append(sub)
    assert len(d.triangles) == 2 * d.N
    assert all(sorted(v) == ["A", "B"] for v in seen.values())  # honeycomb is bipartite


def test_hexagon_consecutive_pairs_close_triangles(d):
    tri_sets = {frozenset(s) for _, s, _ in d.triangles}
    for site in range(d.N):
        hx = d.hexagon(site)
        assert len(set(hx)) == 6
        for k in range(6):
            assert frozenset((site, hx[k], hx[(k + 1) % 6])) in tri_sets


def test_gauss_law_identities_exhaustive(d):
    G = [sum(d.dimer(b).astype(int) for b in bs) for _, _, bs in d.triangles]
    assert all(set(np.unique(g)) <= {1, 3} for g in G)            # one or three dimers
    D = d.total_defects()
    nb = sum(d.dimer(b).astype(np.int32) for b in d.bonds)
    assert np.array_equal(nb, d.N + D)                             # sum n_b = N + sum D
    assert np.array_equal(d.total_defects("A"), d.total_defects("B"))  # net charge 0
    assert np.array_equal(sum(d.charge(t) for t in range(2 * d.N)), np.zeros_like(D))
    E = tfim_hamiltonian(d.N, d.bonds, J_AFM, 0.0).diagonal().real
    assert np.allclose(E, -d.N + 2 * D)                            # Ising energy = defects


def test_ferromagnet_is_not_frustrated(d):
    # Sign check: with J>0 (our default) the all-up state has zero Ising frustration.
    E = tfim_hamiltonian(d.N, d.bonds, +1.0, 0.0).diagonal().real
    assert E.min() == pytest.approx(-3 * d.N)                      # every bond satisfied


def test_winding_integer_and_sector_label_on_constrained_subspace(d):
    free = d.total_defects() == 0
    assert free.any()
    for w in [d.winding_x(y) for y in range(d.Ly)] + [d.winding_y(x) for x in range(d.Lx)]:
        assert w.dtype.kind == "i"
    for y in range(1, d.Ly):
        assert np.array_equal(d.winding_x(0)[free], d.winding_x(y)[free])
    for x in range(1, d.Lx):
        assert np.array_equal(d.winding_y(0)[free], d.winding_y(x)[free])


def test_winding_row_difference_equals_strip_charge():
    d = TriangularDimers(3, 4)
    for y in range(d.Ly):
        strip_A = sum(d.defect(2 * (y * d.Lx + x)).astype(int) for x in range(d.Lx))
        strip_B = sum(d.defect(2 * (y * d.Lx + x) + 1).astype(int) for x in range(d.Lx))
        diff = d.winding_x((y + 1) % d.Ly).astype(int) - d.winding_x(y)
        assert np.array_equal(diff, 6 * (strip_B - strip_A))


def test_reference_sector_values():
    # stripe = maximal sector (2Lx, -Ly) -> (18, -6) on the reference's 9x6;
    # 3-sublattice state = (0, 0). Checked on small tori with the same rules.
    d = TriangularDimers(3, 6)
    i = d.product_state_index(d.stripe_spins())
    assert (d.total_defects()[i], d.winding_x()[i], d.winding_y()[i]) == (0, 6, -6)
    i = d.product_state_index(d.three_sublattice_spins())
    assert (d.total_defects()[i], d.winding_x()[i], d.winding_y()[i]) == (0, 0, 0)


def test_qdm_commutes_exactly_with_constraints_and_windings(d):
    H = d.qdm_hamiltonian(0.7)
    assert abs(H - H.T).max() == 0
    ops = [d.defect(t) for t in range(2 * d.N)] + [d.winding_x(0), d.winding_y(0)]
    for o in ops:
        O = sp.diags(o.astype(float))
        assert abs(H @ O - O @ H).max() == 0


def test_tfim_does_not_commute_with_gauss_law(d):
    H = tfim_hamiltonian(d.N, d.bonds, J_AFM, 0.3)
    O = sp.diags(d.total_defects().astype(float))
    assert abs(H @ O - O @ H).max() > 0.1


def test_winding_conserved_under_qdm_dynamics_but_leaks_under_tfim():
    d = TriangularDimers(3, 4)
    free = np.nonzero(d.total_defects() == 0)[0]
    wx, wy = d.winding_x(), d.winding_y()
    i0 = int(free[0])
    psi0 = np.zeros(1 << d.N, complex)
    psi0[i0] = 1
    other = (wx != wx[i0]) | (wy != wy[i0])
    # QDM: exact
    psi = sla.expm_multiply(-1j * 5.0 * d.qdm_hamiltonian(0.3).tocsc(), psi0)
    p = np.abs(psi) ** 2
    assert p[other].sum() < 1e-12 and d.defect_density(psi) < 1e-12
    # TFIM Trotter: small but nonzero leakage (O((h/J)^2), measured in data/gauss_law_scaling.txt)
    psi, _ = evolve(psi0, d.N, d.bonds, J_AFM, 0.1, 5.0, 20)
    p = np.abs(psi) ** 2
    assert 1e-6 < p[other].sum() < 0.05
    assert 1e-6 < d.defect_density(psi) < 0.05


def test_ed_ground_state_is_almost_constrained_and_scales_as_h_squared():
    d = TriangularDimers(3, 4)
    hs = np.array([0.025, 0.05, 0.1])
    dens = []
    for h in hs:
        v = sla.eigsh(tfim_hamiltonian(d.N, d.bonds, J_AFM, h), k=1, which="SA")[1][:, 0]
        dens.append(d.defect_density(v))
    slope = np.polyfit(np.log(hs), np.log(dens), 1)[0]
    assert abs(slope - 2) < 0.1
    assert max(dens) < 1e-2


def test_stripe_quench_matches_first_order_prediction():
    # Stripe state: every spin sees 2 parallel + 4 antiparallel neighbours, flip costs
    # 4|J| and creates 2 defects -> time-averaged defects per triangle = (h/|J|)^2 / 8.
    d = TriangularDimers(3, 4)
    i0 = d.product_state_index(d.stripe_spins())
    Dn = d.total_defects() / (2 * d.N)
    diag = ising_diagonal(d.N, d.bonds, J_AFM)
    h, dt = 0.025, 0.025
    psi = np.zeros(1 << d.N, complex)
    psi[i0] = 1
    vals = []
    for s in range(800):
        psi = trotter2_step(psi, d.N, diag, h, dt)
        vals.append(np.abs(psi) ** 2 @ Dn)
    assert np.mean(vals) == pytest.approx(h * h / 8, rel=0.05)


def test_dimer_correlation_by_distance_counts_all_pairs():
    d = TriangularDimers(3, 3)
    psi = np.zeros(1 << d.N, complex)
    psi[d.product_state_index(d.three_sublattice_spins())] = 1
    out = d.dimer_correlation_by_distance(psi)
    nb = len(d.bonds)
    assert sum(n for n, _ in out.values()) == nb * (nb - 1) // 2
    assert all(abs(c) < 1e-12 for _, c in out.values())   # product state: no connected corr.
    assert min(out) == pytest.approx(0.5)                # side midpoints of one unit triangle
    assert sum(d.winding_distribution(psi).values()) == pytest.approx(1)


# ----------------------------------------------------------------- mitigation kit
def _small():
    d = TriangularDimers(3, 3)
    sp0 = d.three_sublattice_spins()
    psi0 = np.zeros(1 << d.N, complex)
    psi0[d.product_state_index(sp0)] = 1
    return d, sp0, psi0


def test_density_matrix_noiseless_matches_statevector():
    d, _, psi0 = _small()
    U = trotter_unitary(d.N, d.bonds, J_AFM, 0.3, 0.25)
    dg = evolve_dm(psi0, d.N, U, 8, (0, 0, 0))
    psi, _ = evolve(psi0, d.N, d.bonds, J_AFM, 0.3, 2.0, 8)
    assert np.allclose(dg[-1], np.abs(psi) ** 2, atol=1e-12)


def test_pauli_channel_is_trace_preserving_and_y_correct():
    rng = np.random.default_rng(0)
    a = rng.normal(size=(8, 8)) + 1j * rng.normal(size=(8, 8))
    rho = a @ a.conj().T
    rho /= np.trace(rho)
    out = pauli_channel_dm(rho, 3, 1, (0, 1.0, 0))
    Y = np.kron(np.kron(np.eye(2), np.array([[0, -1j], [1j, 0]])), np.eye(2))
    assert np.allclose(out, Y @ rho @ Y.conj().T)
    assert np.trace(pauli_channel_dm(rho, 3, 2, (0.1, 0.2, 0.3))) == pytest.approx(1)


def test_trajectories_agree_with_density_matrix():
    d, _, psi0 = _small()
    U = trotter_unitary(d.N, d.bonds, J_AFM, 0.3, 0.25)
    px = (0.01, 0.0, 0.01)
    exact = evolve_dm(psi0, d.N, U, 10, px)[-1]
    mean, batch = evolve_trajectories(psi0, d.N, d.bonds, J_AFM, 0.3, 0.25, 10, px, 600, 3)
    D = d.total_defects() / (2 * d.N)
    se = np.std([b[-1] @ D for b in batch], ddof=1) / np.sqrt(len(batch))
    assert abs(mean[-1] @ D - exact @ D) < 4 * se + 1e-4


def test_z_errors_are_invisible_to_the_gauss_law_instantaneously():
    d, _, psi0 = _small()
    det = single_error_detection(d, np.abs(psi0) ** 2)
    assert det["Z"] == 0.0 and det["X"] > 0.3


def test_postselect_on_a_hand_built_distribution():
    """Direct unit test of Targets.postselect (review: it had none, yet the Gauss-law
    'qualified yes' verdict rests on it; its only callers were in scripts/run_gauss_law.py).

    Hand-built distribution on 3x3: weight 0.5 on the 3-sublattice state c0 (defect-free),
    0.3 on c1 = c0 with ONE spin flipped (still defect-free), 0.2 on a defective state. The
    acceptance must then be exactly 0.8 and the pattern-memory estimator
    m = (1/N) sum_i s_i(0) Z_i must equal the hand-computed
        (0.5 * 1 + 0.3 * (N - 2)/N) / 0.8,
    since m(c0) = 1 by definition and flipping one of the N = 9 spins costs 2/N. Spins are
    read back from the basis index with independent bit arithmetic (site 0 = MSB,
    bit = (1 - s)/2), so the expected value does not reuse the estimator's own value arrays.
    """
    d = TriangularDimers(3, 3)
    s0 = d.three_sublattice_spins()
    T = Targets.build(d, s0)
    N = d.N
    defects = d.total_defects()

    i0 = d.product_state_index(s0)
    s1 = np.array(s0, copy=True)
    s1[0, 0] *= -1                                     # flippable in the 3-sublattice state
    i1 = d.product_state_index(s1)
    i2 = int(np.nonzero(defects > 0)[0][0])
    assert defects[i0] == 0 and defects[i1] == 0 and defects[i2] > 0

    p = np.zeros(1 << N)
    p[i0], p[i1], p[i2] = 0.5, 0.3, 0.2

    vals, acc = T.postselect(p)
    assert acc == pytest.approx(0.8)

    def memory(index):                                 # independent of gauss_mitigation
        z = np.array([1 - 2 * ((index >> (N - 1 - i)) & 1) for i in range(N)])
        return float(np.sum(np.asarray(s0).reshape(-1) * z) / N)

    assert memory(i0) == pytest.approx(1.0)
    assert memory(i1) == pytest.approx((N - 2) / N)
    assert vals[0] == pytest.approx((0.5 * 1.0 + 0.3 * (N - 2) / N) / 0.8)

    # The rejected (defective) branch must not influence the estimate at all...
    q = p.copy()
    q[i2] = 5.0
    q /= q.sum()
    vals_q, acc_q = T.postselect(q)
    assert np.allclose(vals_q, vals)
    assert acc_q == pytest.approx(0.8 / 5.8)
    # ... on a distribution supported only on defect-free states it equals the raw mean ...
    r = np.zeros(1 << N)
    r[i0], r[i1] = 0.25, 0.75
    assert np.allclose(T.postselect(r)[0], T.raw(r))
    assert T.postselect(r)[1] == pytest.approx(1.0)
    # ... and it is discriminating: the raw mean of p is not the post-selected one.
    assert abs(T.raw(p)[0] - vals[0]) > 0.05


def test_estimators_are_exact_on_ideal_global_depolarizing():
    # If the noise really were GLOBAL depolarizing with known floor, self-mitigation is exact.
    d, sp0, psi0 = _small()
    U = trotter_unitary(d.N, d.bonds, J_AFM, 0.3, 0.25)
    pi = evolve_dm(psi0, d.N, U, 12, (0, 0, 0))[-1]
    T = Targets.build(d, sp0)
    F = 0.7
    pn = F * pi + (1 - F) / pi.size
    est, Fhat = T.selfmit(pn, T.defect_density(pi))
    assert Fhat == pytest.approx(F)
    assert np.allclose(est, T.raw(pi))


def test_richardson_and_pec_gamma():
    c = richardson([1, 2, 3])
    assert np.allclose(c, [3, -3, 1])
    assert pec_gamma_single((0, 0, 0)) == pytest.approx(1)
    assert pec_gamma_single((1e-3, 1e-3, 1e-3)) > 1
