"""Dimer / Gauss-law / winding observables for the frustrated triangular TFIM (handoff/02).

Derivation and status tags: docs/gauss_law_dimers.md. Summary:

Convention [established, arXiv:2503.20870 Sec. V]: the reference writes
H = J_ref sum ZZ + h sum X with antiferromagnetic J_ref > 0. Our H = -J sum ZZ - h sum X,
so the frustrated model is J = -J_ref < 0. (The sign of h is a gauge choice: conjugating
by prod_i Z_i maps h -> -h and leaves Z-basis states and every observable here unchanged.)
With J > 0 (our default ferromagnet) no triangle is frustrated and this module does not apply.

Spin -> dimer map [established, Moessner-Sondhi picture; reference Sec. V]: a triangular
bond b=(i,j) is FRUSTRATED (AFM order unsatisfied) iff Z_i Z_j = +1; its dual edge on the
honeycomb lattice then carries a dimer,
    n_b = (1 + Z_i Z_j) / 2.
Each elementary triangle t (= honeycomb vertex) holds G_t = sum_{b in t} n_b in {1, 3}.

Gauss law [derived]: G_t = 1 for every t. Its violation is the diagonal defect projector
    D_t = (G_t - 1)/2 = (1 + Z_aZ_b + Z_bZ_c + Z_aZ_c) / 4   (1 iff all three spins equal).
With electric field E_b = n_b - 1/3 oriented from A (lower) to B (upper) triangles, the
charge is Q_t = +-2 D_t (+ on A, - on B). Exact identities on the torus (tests check them):
    sum_b n_b = N + sum_t D_t                     (Ising energy = |J|(2 sum_t D_t - N))
    sum_{t in A} D_t = sum_{t in B} D_t           (net charge 0: defects come in A/B pairs)

Winding numbers [derived; normalisation inferred to match the reference's (18,6)]:
    W_x(y) = 3 * #(frustrated horizontal bonds in row y)    - Lx
    W_y(x) = 3 * #(frustrated vertical   bonds in column x) - Ly
i.e. 3 * electric flux through the non-contractible cut. Integer-valued for any L.
W_x(y+1) - W_x(y) = 6 * (sum_B D - sum_A D over the strip between rows y and y+1), so
on the defect-free subspace W_x is row-independent (a sector label).

Geometry: the repo's periodic triangular embedding (src/lattice.triangular_bonds): bonds
along (1,0), (0,1), (1,1). Plaquette (x,y) splits into
    A (lower) = {(x,y), (x+1,y), (x+1,y+1)},   B (upper) = {(x,y), (x,y+1), (x+1,y+1)}.
Requires periodic boundaries with Lx, Ly >= 3 (honeycomb dual is then a proper torus).

All operators are DIAGONAL in the computational basis and returned as float arrays over
the 2^N basis (site 0 = most significant bit, as in src/observables.py). Expectation
values take a statevector or a probability vector (diag of a density matrix).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Dict, List, Tuple

import numpy as np
import scipy.sparse as sp

from src.lattice import coord, site_index, triangular_bonds

Bond = Tuple[int, int]


def _z(n_sites: int, site: int) -> np.ndarray:
    """+1/-1 Z eigenvalue of `site` over all basis states (site 0 = MSB)."""
    idx = np.arange(1 << n_sites, dtype=np.int64)
    return (1 - 2 * ((idx >> (n_sites - 1 - site)) & 1)).astype(np.int8)


def probabilities(state: np.ndarray) -> np.ndarray:
    """Basis-state probabilities: |psi|^2 for a statevector, or a probability vector as-is."""
    state = np.asarray(state)
    if np.iscomplexobj(state):
        return np.abs(state) ** 2
    return state.astype(np.float64)


def expval_diag(state: np.ndarray, diag: np.ndarray) -> float:
    """<O> for a diagonal operator O given by its eigenvalue array."""
    return float(np.dot(probabilities(state), diag))


@dataclass
class TriangularDimers:
    """Dimer / Gauss-law bookkeeping on a periodic Lx x Ly triangular torus."""

    Lx: int
    Ly: int

    def __post_init__(self) -> None:
        if self.Lx < 3 or self.Ly < 3:
            raise ValueError("dimer mapping needs a periodic torus with Lx, Ly >= 3")
        self.N = self.Lx * self.Ly
        self.bonds: List[Bond] = triangular_bonds(self.Lx, self.Ly, "periodic")
        assert len(self.bonds) == 3 * self.N

    # ------------------------------------------------------------------ geometry
    def s(self, x: int, y: int) -> int:
        return site_index(x % self.Lx, y % self.Ly, self.Lx)

    @staticmethod
    def _b(i: int, j: int) -> Bond:
        return (i, j) if i < j else (j, i)

    def horizontal_bond(self, x: int, y: int) -> Bond:
        return self._b(self.s(x, y), self.s(x + 1, y))

    def vertical_bond(self, x: int, y: int) -> Bond:
        return self._b(self.s(x, y), self.s(x, y + 1))

    def diagonal_bond(self, x: int, y: int) -> Bond:
        return self._b(self.s(x, y), self.s(x + 1, y + 1))

    @cached_property
    def triangles(self) -> List[Tuple[str, Tuple[int, int, int], Tuple[Bond, Bond, Bond]]]:
        """(sublattice 'A'|'B', sites, bonds) for all 2N triangles (honeycomb vertices)."""
        out = []
        for y in range(self.Ly):
            for x in range(self.Lx):
                a = (self.s(x, y), self.s(x + 1, y), self.s(x + 1, y + 1))
                out.append(("A", a, (self.horizontal_bond(x, y),
                                     self.vertical_bond(x + 1, y),
                                     self.diagonal_bond(x, y))))
                b = (self.s(x, y), self.s(x, y + 1), self.s(x + 1, y + 1))
                out.append(("B", b, (self.horizontal_bond(x, y + 1),
                                     self.vertical_bond(x, y),
                                     self.diagonal_bond(x, y))))
        return out

    def hexagon(self, site: int) -> List[int]:
        """The 6 neighbours of `site` in cyclic order; consecutive pairs close a triangle with it."""
        x, y = coord(site, self.Lx)
        return [self.s(x + 1, y), self.s(x + 1, y + 1), self.s(x, y + 1),
                self.s(x - 1, y), self.s(x - 1, y - 1), self.s(x, y - 1)]

    def bond_position(self, b: Bond) -> np.ndarray:
        """Midpoint of bond b in real triangular-lattice coordinates (unit spacing).

        Site (x,y) -> x*e1 + y*e2 with e1=(1,0), e2=(-1/2, sqrt3/2), so all three bond
        directions (1,0),(0,1),(1,1) have length 1. The wrap is taken minimal-image.
        """
        (x1, y1), (x2, y2) = coord(b[0], self.Lx), coord(b[1], self.Lx)
        dx = (x2 - x1 + self.Lx // 2) % self.Lx - self.Lx // 2
        dy = (y2 - y1 + self.Ly // 2) % self.Ly - self.Ly // 2
        return self._pos(x1 + dx / 2, y1 + dy / 2)

    @staticmethod
    def _pos(x: float, y: float) -> np.ndarray:
        return np.array([x - 0.5 * y, (np.sqrt(3) / 2) * y])

    def torus_distance(self, b1: Bond, b2: Bond) -> float:
        """Minimal-image real-space distance between two bond midpoints."""
        d = self.bond_position(b2) - self.bond_position(b1)
        best = np.inf
        for mx in (-1, 0, 1):
            for my in (-1, 0, 1):
                best = min(best, float(np.linalg.norm(d + self._pos(mx * self.Lx, my * self.Ly))))
        return best

    # --------------------------------------------------------------- operators
    @cached_property
    def _zcache(self) -> Dict[int, np.ndarray]:
        return {}

    def z(self, site: int) -> np.ndarray:
        if site not in self._zcache:
            self._zcache[site] = _z(self.N, site)
        return self._zcache[site]

    def dimer(self, b: Bond) -> np.ndarray:
        """n_b = (1 + Z_i Z_j)/2: 1 iff the AFM bond is frustrated (dimer on the dual edge).

        Why frustration == a dimer: with AFM coupling (our J < 0) a bond is SATISFIED when
        the spins antialign (Z_iZ_j = -1 -> n_b = 0) and FRUSTRATED when they align
        (Z_iZ_j = +1 -> n_b = 1), costing +2|J| of exchange energy. The dual honeycomb edge
        pierces exactly this triangular bond, so marking the unsatisfied (energy-carrying)
        bond places the dimer on it: the dimer tracks where the AFM order broke.
        """
        return ((1 + self.z(b[0]) * self.z(b[1])) // 2).astype(np.int8)

    def defect(self, t: int) -> np.ndarray:
        """D_t = (G_t - 1)/2 in {0,1}: Gauss-law violation on triangle t (all spins equal).

        A triangle has either 1 frustrated bond (G_t = 1, the ground-state dimer rule obeyed)
        or 3 (G_t = 3, all three spins equal). D_t = 1 flags the latter: it is a monomer/defect
        where div E != 0, the source term that breaks the one-dimer-per-triangle Gauss law.
        Energy cost: two extra frustrated bonds relative to a satisfied triangle, i.e. 2|J| per
        defect (hence Ising energy = |J|(2 sum_t D_t - N)); this is why defects are gapped and
        rare at small h, giving the O((h/J)^2) defect density the scaling tests check.
        """
        _, (a, b, c), _ = self.triangles[t]
        za, zb, zc = self.z(a), self.z(b), self.z(c)
        return ((1 + za * zb + zb * zc + za * zc) // 4).astype(np.int8)

    def charge(self, t: int) -> np.ndarray:
        """Gauss-law charge Q_t = div E = +2 D_t on A triangles, -2 D_t on B triangles."""
        sign = 2 if self.triangles[t][0] == "A" else -2
        return sign * self.defect(t).astype(np.int16)

    def total_defects(self, sublattice: str = "AB") -> np.ndarray:
        out = np.zeros(1 << self.N, dtype=np.int16)
        for t, (sub, _, _) in enumerate(self.triangles):
            if sub in sublattice:
                out += self.defect(t)
        return out

    def flippable(self, site: int) -> np.ndarray:
        """Pi_s = 1 iff the 6 hexagon neighbours of `site` alternate (zero local field AND
        flipping `site` keeps all six surrounding triangles defect-free)."""
        hx = self.hexagon(site)
        out = np.ones(1 << self.N, dtype=np.int8)
        for k in range(6):
            out *= ((1 - self.z(hx[k]) * self.z(hx[(k + 1) % 6])) // 2).astype(np.int8)
        return out

    def winding_x(self, y: int = 0) -> np.ndarray:
        """W_x(y) = 3 * (frustrated horizontal bonds in row y) - Lx.

        W_x is a good SECTOR LABEL only on the defect-free subspace and only under H_QDM:
        the row-to-row difference equals the enclosed A/B defect imbalance (module docstring),
        so with defects present W_x(y) depends on which cut y you pick and is not conserved.
        Even defect-free, only moves that preserve every triangle leave it invariant -- that is
        exactly H_QDM (flippable flips), which commutes with W. The bare TFIM X term creates
        defects and changes W, so winding is NOT a symmetry of the physical quench, only of the
        emergent constrained dynamics. The caller passes y only to read any single cut; all cuts
        agree on the free subspace.
        """
        cnt = sum(self.dimer(self.horizontal_bond(x, y)).astype(np.int16) for x in range(self.Lx))
        return 3 * cnt - self.Lx

    def winding_y(self, x: int = 0) -> np.ndarray:
        """W_y(x) = 3 * (frustrated vertical bonds in column x) - Ly."""
        cnt = sum(self.dimer(self.vertical_bond(x, y)).astype(np.int16) for y in range(self.Ly))
        return 3 * cnt - self.Ly

    # ------------------------------------------------------- expectation values
    def defect_density(self, state) -> float:
        """<sum_t D_t> / (2N): Gauss-law violations per triangle."""
        return expval_diag(state, self.total_defects()) / (2 * self.N)

    def dimer_densities(self, state) -> Dict[Bond, float]:
        p = probabilities(state)
        return {b: float(p @ self.dimer(b)) for b in self.bonds}

    def dimer_correlation(self, state, b1: Bond, b2: Bond) -> float:
        """Connected <n_a n_b> - <n_a><n_b>."""
        p = probabilities(state)
        n1, n2 = self.dimer(b1), self.dimer(b2)
        return float(p @ (n1 * n2) - (p @ n1) * (p @ n2))

    def dimer_correlation_by_distance(self, state, decimals: int = 6) -> Dict[float, Tuple[int, float]]:
        """C_r = sum_{pairs a<b, |a-b|=r} [<n_a n_b> - <n_a><n_b>]  (reference Sec. V form,
        unordered pairs). Returns {r: (number_of_pairs, C_r)}; divide for the pair mean."""
        p = probabilities(state)
        occ = {b: self.dimer(b) for b in self.bonds}
        mean = {b: float(p @ occ[b]) for b in self.bonds}
        out: Dict[float, Tuple[int, float]] = {}
        for i, a in enumerate(self.bonds):
            for b in self.bonds[i + 1:]:
                r = round(self.torus_distance(a, b), decimals)
                c = float(p @ (occ[a] * occ[b])) - mean[a] * mean[b]
                n, s = out.get(r, (0, 0.0))
                out[r] = (n + 1, s + c)
        return dict(sorted(out.items()))

    def winding_distribution(self, state, direction: str = "x", line: int = 0) -> Dict[int, float]:
        """Full counting statistics P(W) of the winding number through one cut."""
        p = probabilities(state)
        w = self.winding_x(line) if direction == "x" else self.winding_y(line)
        return {int(v): float(p[w == v].sum()) for v in np.unique(w) if p[w == v].sum() > 0}

    # ------------------------------------------------------------ dynamics
    def qdm_hamiltonian(self, h: float) -> sp.csr_matrix:
        """Constraint-preserving effective model H_QDM = -h sum_s Pi_s X_s (Pi_s = flippable).

        First-order degenerate perturbation theory of -h sum X inside the defect-free
        manifold [established, Moessner-Sondhi]: only flippable spins cost no Ising energy.
        Pi_s depends only on the neighbours, so Pi_s X_s is Hermitian and commutes with every
        D_t and every winding number EXACTLY (tests check the commutators).
        """
        dim = 1 << self.N
        idx = np.arange(dim, dtype=np.int64)
        rows, cols = [], []
        for site in range(self.N):
            on = np.nonzero(self.flippable(site))[0]
            rows.append(on ^ (1 << (self.N - 1 - site)))
            cols.append(on)
        r = np.concatenate(rows)
        c = np.concatenate(cols)
        return sp.csr_matrix((np.full(r.shape, -h, dtype=np.float64), (r, c)), shape=(dim, dim))

    # ------------------------------------------------------------ states
    def product_state_index(self, spins: np.ndarray) -> int:
        """Basis index of a +-1 spin configuration given as an (Ly, Lx) array."""
        bits = (1 - np.asarray(spins).reshape(-1)) // 2
        return int("".join(str(int(b)) for b in bits), 2)

    def three_sublattice_spins(self) -> np.ndarray:
        """(up, down, up) on colours c = (x+y) mod 3 — every triangle has all three colours,
        so it is defect-free with W = (0, 0). Needs Lx, Ly divisible by 3."""
        if self.Lx % 3 or self.Ly % 3:
            raise ValueError("3-sublattice state needs Lx, Ly divisible by 3")
        y, x = np.mgrid[0:self.Ly, 0:self.Lx]
        return np.where((x + y) % 3 == 1, -1, 1)

    def stripe_spins(self) -> np.ndarray:
        """Rows alternately up/down (Ly even): every horizontal bond frustrated, every
        vertical/diagonal satisfied -> defect-free, W = (2 Lx, -Ly) (maximal |W_x|)."""
        if self.Ly % 2:
            raise ValueError("stripe state needs even Ly")
        y, _ = np.mgrid[0:self.Ly, 0:self.Lx]
        return np.where(y % 2 == 0, 1, -1)
