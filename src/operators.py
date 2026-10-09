"""Sparse Pauli operators and the TFIM Hamiltonian builder.

Hamiltonian (research/01-stage1-conventions.md):
    H = -J * sum_<ij> Z_i Z_j  -  h * sum_i X_i

The leading minus signs fix the physics: with J > 0 the ZZ term is
ferromagnetic (aligned Z neighbours lower the energy), and -h X favours the
+X-polarized paramagnet; the competition between the two is the TFIM quantum
phase transition this project probes.

Qubit ordering: site n occupies tensor-factor n, with factor 0 the most
significant bit of the computational basis index (standard Kronecker ordering,
H = op_0 ⊗ op_1 ⊗ ... ⊗ op_{N-1}). This matches the statevector reshape used in
src/trotter.py, where axis k of the (2,)*N tensor is site k.

Construction (addresses qc-reviewer review/01-stage1.md C1): the Hamiltonian is
built directly as a sparse operator from bit arithmetic — the diagonal ZZ part
via per-bond ±1 eigenvalue products, and the X part as a sum of single-bit-flip
permutation matrices (one off-diagonal entry per basis state per site). Nothing
is materialized as a full 2^N-dimensional scipy.sparse.kron product, so the
builder's memory scales with the number of nonzeros (O((nbonds + N) * 2^N)
entries) rather than the dense dimension. The explicit kron helpers below are
retained only as small-N reference operators (used in tests), not in the builder.
"""

from __future__ import annotations

from functools import reduce
from typing import List, Tuple

import numpy as np
import scipy.sparse as sp

# Single-qubit Pauli matrices (sparse, complex128).
_I = sp.identity(2, dtype=np.complex128, format="csr")
_X = sp.csr_matrix(np.array([[0, 1], [1, 0]], dtype=np.complex128))
_Y = sp.csr_matrix(np.array([[0, -1j], [1j, 0]], dtype=np.complex128))
_Z = sp.csr_matrix(np.array([[1, 0], [0, -1]], dtype=np.complex128))

_PAULI = {"I": _I, "X": _X, "Y": _Y, "Z": _Z}


def kron_list(mats: List[sp.spmatrix]) -> sp.spmatrix:
    """Kronecker product of a list of sparse matrices, left-to-right."""
    return reduce(sp.kron, mats, sp.identity(1, dtype=np.complex128, format="csr")).tocsr()


def single_site(pauli: str, site: int, n_sites: int) -> sp.spmatrix:
    """Operator with `pauli` on `site`, identity elsewhere (full 2^N space)."""
    if pauli not in _PAULI:
        raise ValueError(f"unknown Pauli {pauli!r}")
    mats = [_I] * n_sites
    mats[site] = _PAULI[pauli]
    return kron_list(mats)


def two_site(pauli: str, i: int, j: int, n_sites: int) -> sp.spmatrix:
    """Operator with `pauli` on sites i and j, identity elsewhere.

    Small-N reference operator (used in tests); not used by the sparse
    Hamiltonian builder below.
    """
    if pauli not in _PAULI:
        raise ValueError(f"unknown Pauli {pauli!r}")
    mats = [_I] * n_sites
    mats[i] = _PAULI[pauli]
    mats[j] = _PAULI[pauli]
    return kron_list(mats)


def _ising_diagonal(n_sites: int, bonds: List[Tuple[int, int]], J: float) -> np.ndarray:
    """Diagonal of -J sum_<ij> Z_i Z_j in the computational basis.

    Z eigenvalue of site k in basis index b is +1 if bit k is 0 else -1, with
    site 0 the most significant bit (shift = n_sites-1-k), matching the module's
    Kronecker ordering and src.trotter.ising_diagonal. Returns a real length-2^N
    array built from bit arithmetic only — no full-D operator is formed.
    """
    dim = 1 << n_sites
    idx = np.arange(dim, dtype=np.int64)
    diag = np.zeros(dim, dtype=np.float64)
    for (i, j) in bonds:
        zi = 1 - 2 * ((idx >> (n_sites - 1 - i)) & 1)
        zj = 1 - 2 * ((idx >> (n_sites - 1 - j)) & 1)
        diag += zi * zj
    return -J * diag


def tfim_hamiltonian(
    n_sites: int,
    bonds: List[Tuple[int, int]],
    J: float,
    h: float,
) -> sp.spmatrix:
    """Build the sparse TFIM Hamiltonian H = -J sum_<ij> ZZ - h sum_i X.

    `bonds` is the nearest-neighbour edge list (square or triangular) from
    src.lattice (square_bonds / triangular_bonds); the builder is geometry-agnostic.
    Returns a CSR matrix of shape (2^n_sites, 2^n_sites).

    Genuinely sparse construction (review/01-stage1.md C1): the ZZ term is the
    real diagonal from `_ising_diagonal`; the field term -h sum_i X_i is the sum
    of single-bit-flip permutations, i.e. for each site i every basis state b is
    connected to b XOR (bit i) with amplitude -h. These off-diagonal entries are
    assembled once in COO form (N * 2^N entries) and summed, so peak memory
    tracks the nonzero count, not the dense 2^N x 2^N size.
    """
    dim = 1 << n_sites
    idx = np.arange(dim, dtype=np.int64)

    # Diagonal Ising part.
    diag = _ising_diagonal(n_sites, bonds, J).astype(np.complex128)
    H = sp.diags(diag, offsets=0, shape=(dim, dim), dtype=np.complex128, format="coo")

    # Transverse field: -h sum_i X_i. X on site i flips bit (n_sites-1-i).
    if n_sites > 0 and h != 0.0:
        rows = np.empty(n_sites * dim, dtype=np.int64)
        cols = np.empty(n_sites * dim, dtype=np.int64)
        for i in range(n_sites):
            flipped = idx ^ (1 << (n_sites - 1 - i))
            rows[i * dim:(i + 1) * dim] = idx
            cols[i * dim:(i + 1) * dim] = flipped
        data = np.full(n_sites * dim, -h, dtype=np.complex128)
        X_part = sp.coo_matrix((data, (rows, cols)), shape=(dim, dim), dtype=np.complex128)
        H = (H + X_part)

    return H.tocsr()
