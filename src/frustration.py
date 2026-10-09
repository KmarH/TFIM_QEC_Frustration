"""Q2 frustration: distance-resolved connected correlations, square vs triangular (handoff/09).

Write-up: docs/q2_frustration.md. Classical exact diagonalization only; every number [measured],
never an H2 result.

Ground state [derived]. H = -J sum ZZ - h sum X commutes with the global flip P = prod_i X_i.
For h > 0 its off-diagonal elements in the Z basis are all -h <= 0 and every basis state is reached
by single flips, so by Perron-Frobenius the ground state is UNIQUE with positive amplitudes, hence
P-even, and <Z_i> = 0 exactly. On a finite torus with long-range-ordered tendencies (the square
Neel pair) the P-odd partner sits only exponentially above it, and an unrestricted Lanczos vector
can come out as an arbitrary symmetry-broken mixture (4x4 square, h = 0.3: |<Z_i>| from ~0.01 to ~0.5
across repeated run_ed calls [measured]; the E1 - E0 gap there is below numerical resolution),
which corrupts single-vector connected correlators. So the ground state is computed EXACTLY in the
P-even sector: basis |e_r> = (|r> + |~r>)/sqrt 2 over representatives r < 2^(N-1), with
<e_r|H|e_s> = H[r, s] + H[r, ~s]. Its energy is checked against src.backends.run_ed (tests).
At h = 0 the ground state is degenerate on both lattices (massively on the triangular one), so no
single vector is meaningful there: h = 0 correlators are recorded but not interpreted.

Distance metric (stated, and the same in spirit on both lattices): minimal-image EUCLIDEAN distance
between sites in each lattice's natural embedding, nearest neighbours at distance 1:
  square     site (x, y) -> (x, y);
  triangular site (x, y) -> x e1 + y e2, e1 = (1, 0), e2 = (-1/2, sqrt3/2): the convention of
             src/dimers.py (TriangularDimers._pos / torus_distance), so the six bond directions
             (1,0), (0,1), (1,1) of src/lattice.triangular_bonds all have length 1.
The nearest-neighbour shell equals the bond list exactly (tested).

Square-torus caveat [measured]. A square torus with an ODD periodic length is not bipartite, so the
AFM is itself frustrated there (h = 0 energy per bond -2/3 on 3x4, -0.8 on 4x5, vs -1 on 4x4).
Only even x even square tori are the unfrustrated reference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import scipy.sparse.linalg as sla

from src.backends import MemoryCeilingError
from src.dimers import TriangularDimers
from src.lattice import coord, square_bonds, triangular_bonds
from src.observables import expval_z, two_point_correlations_z
from src.operators import tfim_hamiltonian


def bonds_for(geometry: str, Lx: int, Ly: int) -> List[Tuple[int, int]]:
    if geometry == "square":
        return square_bonds(Lx, Ly, "periodic")
    if geometry == "triangular":
        return triangular_bonds(Lx, Ly, "periodic")
    raise ValueError(f"unknown geometry {geometry!r}")


def is_bipartite_torus(geometry: str, Lx: int, Ly: int) -> bool:
    """Unfrustrated AFM reference iff square with both periodic lengths even [derived]."""
    return geometry == "square" and Lx % 2 == 0 and Ly % 2 == 0


def check_ed_ceiling(n_sites: int, max_spins: int) -> None:
    if n_sites > max_spins:
        raise MemoryCeilingError(f"ED for {n_sites} spins refused: ceiling is {max_spins} (SCOPE §5).")


@dataclass
class GroundState:
    energy: float
    psi: np.ndarray            # full 2^N real vector, P-even, normalised
    n: int
    bonds: List[Tuple[int, int]]


def even_sector_ground_state(geometry: str, Lx: int, Ly: int, J: float, h: float,
                             max_spins: int, tol: float = 1e-12) -> GroundState:
    """Exact ground state restricted to the global-spin-flip-even sector (module docstring)."""
    n = Lx * Ly
    check_ed_ceiling(n, max_spins)
    bonds = bonds_for(geometry, Lx, Ly)
    H = tfim_hamiltonian(n, bonds, J, h).tocsr().real
    half = 1 << (n - 1)
    He = (H[:half, :half] + H[:half, half:][:, ::-1]).tocsr()
    w, v = sla.eigsh(He, k=1, which="SA", tol=tol)
    vr = v[:, 0]
    psi = np.concatenate([vr, vr[::-1]]) / math.sqrt(2.0)
    psi /= np.linalg.norm(psi)
    return GroundState(float(w[0]), psi, n, bonds)


def spectral_gaps(geometry: str, Lx: int, Ly: int, J: float, h: float, max_spins: int, k: int = 3) -> np.ndarray:
    """E_1 - E_0, E_2 - E_0 in the FULL space (degeneracy / quasi-degeneracy indicator)."""
    n = Lx * Ly
    check_ed_ceiling(n, max_spins)
    w = np.sort(sla.eigsh(tfim_hamiltonian(n, bonds_for(geometry, Lx, Ly), J, h).tocsr(), k=k, which="SA",
                          return_eigenvectors=False))
    return w[1:] - w[0]


def site_distance(geometry: str, Lx: int, Ly: int, i: int, j: int) -> float:
    """Minimal-image Euclidean site distance in the lattice's natural embedding (module docstring)."""
    (x1, y1), (x2, y2) = coord(i, Lx), coord(j, Lx)
    best = math.inf
    for mx in (-1, 0, 1):
        for my in (-1, 0, 1):
            dx, dy = x2 - x1 + mx * Lx, y2 - y1 + my * Ly
            if geometry == "square":
                d = math.hypot(dx, dy)
            else:
                d = float(np.linalg.norm(TriangularDimers._pos(dx, dy)))
            best = min(best, d)
    return best


@dataclass
class Shell:
    r: float
    n_pairs: int
    mean: float          # mean connected <Z_i Z_j>_c over the pairs at this distance
    lo: float            # min over the pairs (spread inside a shell, e.g. inequivalent directions)
    hi: float


def correlation_by_distance(psi: np.ndarray, geometry: str, Lx: int, Ly: int, decimals: int = 6) -> List[Shell]:
    """C(r): connected <Z_i Z_j> - <Z_i><Z_j> (src.observables.two_point_correlations_z) binned by
    the stated distance metric. Returns shells sorted by r."""
    n = Lx * Ly
    corr = two_point_correlations_z(psi, n, connected=True)
    bins: Dict[float, List[float]] = {}
    for (i, j), c in corr.items():
        bins.setdefault(round(site_distance(geometry, Lx, Ly, i, j), decimals), []).append(c)
    return [Shell(r, len(v), float(np.mean(v)), float(min(v)), float(max(v))) for r, v in sorted(bins.items())]


def max_abs_magnetization(psi: np.ndarray, n: int) -> float:
    return max(abs(expval_z(psi, n, i)) for i in range(n))
