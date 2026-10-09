"""Observables (HANDOFF §3): magnetization, variance, two-point correlations,
energy, and relaxation.

All expectation values are taken on a normalized statevector `psi` (length 2^N,
complex128). Operators are applied via the memory-light helpers in this module
(diagonal Z strings and single-site X mixing), not by building dense matrices,
so these scale as O(2^N) memory like the evolution itself.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np

from src.operators import tfim_hamiltonian


def _z_eigenvalues(n_sites: int, site: int, dim: int) -> np.ndarray:
    """+1/-1 Z eigenvalue of `site` for each basis index (site 0 = MSB)."""
    idx = np.arange(dim, dtype=np.int64)
    return 1 - 2 * ((idx >> (n_sites - 1 - site)) & 1)


def expval_z(psi: np.ndarray, n_sites: int, site: int) -> float:
    """<Z_site>."""
    dim = psi.shape[0]
    z = _z_eigenvalues(n_sites, site, dim)
    return float(np.real(np.sum(z * (np.abs(psi) ** 2))))


def expval_zz(psi: np.ndarray, n_sites: int, i: int, j: int) -> float:
    """<Z_i Z_j>."""
    dim = psi.shape[0]
    zi = _z_eigenvalues(n_sites, i, dim)
    zj = _z_eigenvalues(n_sites, j, dim)
    return float(np.real(np.sum(zi * zj * (np.abs(psi) ** 2))))


def expval_x(psi: np.ndarray, n_sites: int, site: int) -> float:
    """<X_site> = sum of psi* (X flips `site`'s bit)."""
    psi_t = psi.reshape((2,) * n_sites)
    psi_t = np.moveaxis(psi_t, site, 0)
    flipped = psi_t[::-1]  # swap the two components along `site`
    val = np.sum(np.conjugate(psi_t) * flipped)
    return float(np.real(val))


def total_magnetization_z(psi: np.ndarray, n_sites: int) -> float:
    """M_z = sum_i <Z_i>."""
    return sum(expval_z(psi, n_sites, i) for i in range(n_sites))


def total_magnetization_x(psi: np.ndarray, n_sites: int) -> float:
    """M_x = sum_i <X_i>."""
    return sum(expval_x(psi, n_sites, i) for i in range(n_sites))


def magnetization_variance_z(psi: np.ndarray, n_sites: int) -> float:
    """Var(M_z) = <M_z^2> - <M_z>^2, with M_z = sum_i Z_i.

    Physically the fluctuation of the Ising order parameter: it grows with the
    build-up of Z-Z correlations (and diverges with system size at criticality),
    so it is a sensitive probe of the ferromagnetic transition.

    <M_z^2> = sum_i <Z_i^2> + sum_{i!=j} <Z_i Z_j> = N + sum_{i!=j} <Z_i Z_j>,
    since Z_i^2 = I.
    """
    dim = psi.shape[0]
    prob = np.abs(psi) ** 2
    mz_op = np.zeros(dim, dtype=np.float64)
    for i in range(n_sites):
        mz_op += _z_eigenvalues(n_sites, i, dim)
    mean = float(np.sum(mz_op * prob))
    mean_sq = float(np.sum((mz_op ** 2) * prob))
    return mean_sq - mean ** 2


def two_point_correlations_z(
    psi: np.ndarray, n_sites: int, connected: bool = True
) -> Dict[Tuple[int, int], float]:
    """All pairwise correlators. connected=True returns <Z_iZ_j> - <Z_i><Z_j>.

    The connected form subtracts the trivial product of local magnetizations, so
    it isolates genuine two-site correlation: it is zero on any product state and
    its spatial decay with |i-j| gives the correlation length. The distance-
    resolved average of these pairs feeds the correlation curves (HANDOFF §3).
    """
    ez = [expval_z(psi, n_sites, i) for i in range(n_sites)]
    out: Dict[Tuple[int, int], float] = {}
    for i in range(n_sites):
        for j in range(i + 1, n_sites):
            c = expval_zz(psi, n_sites, i, j)
            out[(i, j)] = c - ez[i] * ez[j] if connected else c
    return out


def energy(
    psi: np.ndarray,
    n_sites: int,
    bonds: List[Tuple[int, int]],
    J: float,
    h: float,
) -> float:
    """<H> for H = -J sum ZZ - h sum X, computed termwise (no dense H)."""
    e = 0.0
    for (i, j) in bonds:
        e += -J * expval_zz(psi, n_sites, i, j)
    for i in range(n_sites):
        e += -h * expval_x(psi, n_sites, i)
    return e


def energy_dense(
    psi: np.ndarray,
    n_sites: int,
    bonds: List[Tuple[int, int]],
    J: float,
    h: float,
) -> float:
    """<H> via the sparse Hamiltonian — cross-check for `energy` on small N."""
    H = tfim_hamiltonian(n_sites, bonds, J, h)
    return float(np.real(np.vdot(psi, H @ psi)))


# --------------------------------------------------------------------------- #
# Observables of the Haghshenas et al. dataset (handoff/03, research/05).
# Additive only: nothing above is changed.
# --------------------------------------------------------------------------- #
def total_z_sq_normalized(psi: np.ndarray, n_sites: int) -> float:
    """Z2 = <(sum_i Z_i)^2> / N^2 — the dataset's normalized SECOND MOMENT.

    research/05 [established from the dataset README]: Z2 = <sum_ij Z_i Z_j / N^2>,
    bounded in [0, 1]. This is NOT the connected variance computed by
    `magnetization_variance_z` (no <M_z>^2 subtraction).
    """
    dim = psi.shape[0]
    mz_op = np.zeros(dim, dtype=np.float64)
    for i in range(n_sites):
        mz_op += _z_eigenvalues(n_sites, i, dim)
    return float(np.sum((mz_op ** 2) * (np.abs(psi) ** 2))) / n_sites ** 2


def nn_energy_density_x(
    psi: np.ndarray,
    Lx: int,
    Ly: int,
    bonds: List[Tuple[int, int]],
) -> np.ndarray:
    """E(x) = < sum_y sum_{j nn of (x,y)} Z(x,y) Z_j / 4 >, for x = 0..Lx-1.

    The dataset README's ZZnn profile: for each column x, each site (x, y) contributes
    the sum of Z Z over its nearest neighbours (x±1, y), (x, y±1), divided by 4.
    Neighbours are taken from `bonds` (so the boundary condition is whatever the bond
    list encodes, e.g. square_bonds(..., "periodic")); a site with fewer than 4
    neighbours still divides by 4, as in the README formula.
    [inferred] The README formula sums over y without a further 1/Ly; that reading is
    kept here and must be confirmed against the dataset's quench3 values.
    Edge case: with a periodic side of length 2 the bond list holds the single wrap bond
    once, while the README's literal x+1 / x-1 would count it twice; the data lattices
    (14x4) are unaffected, but do not use this for a periodic side of 2.
    """
    n_sites = Lx * Ly
    out = np.zeros(Lx, dtype=np.float64)
    for (i, j) in bonds:
        c = expval_zz(psi, n_sites, i, j) / 4.0
        # each bond appears in the neighbour sum of both endpoints
        out[i % Lx] += c
        out[j % Lx] += c
    return out
