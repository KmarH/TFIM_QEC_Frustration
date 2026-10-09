"""Sector-restricted MCMC ergodic baseline for Q3 (thermalization) — handoff/07.

Write-up and status tags: docs/q3_thermalization.md. Summary of the design:

Ensemble [derived]. The quench starts from a defect-free Z-basis product state |c0> in winding
sector W0 = (W_x, W_y). For |h| << |J| the dynamics is generated, at first order, by
H_QDM = -h sum_s Pi_s X_s inside the defect-free manifold (src/dimers.py, docs/gauss_law_dimers.md
§4). Every basis state has <c|H_QDM|c> = 0, and each flip changes the number of up spins by one,
so (-1)^{#up} anticommutes with H_QDM and its spectrum is symmetric about 0: a product state sits
at the centre of the band, i.e. at INFINITE TEMPERATURE for the constrained model. The ergodic
(ETH) reference is therefore the UNIFORM average over the configurations H_QDM can reach from c0:
the flip-connected component of c0 inside the defect-free W0 sector. On every torus enumerated
here each non-frozen sector is ONE component (data/mcmc_baseline.txt) [measured, N <= 20].
The per-sector restriction is required because ETH holds only within a winding sector in these
dimer models (Lan & Powell, PRB 96, 115140, arXiv:1706.02601) [established].

Sampler [derived]. Spin configurations, single-site moves: pick a site uniformly; flip it iff it
is flippable (its 6 hexagon neighbours alternate). Flippability of s depends only on its
neighbours, which the flip leaves unchanged, so each move is its own inverse with the same
probability 1/N: the kernel is symmetric, hence doubly stochastic, hence UNIFORM on each
component. A flippable flip keeps every triangle defect-free and leaves every winding cut
unchanged (it is one term of H_QDM, which commutes with D_t and W exactly; tests/test_dimers.py),
so the chain cannot leave W0. The sampler still re-checks the defect count and EVERY row/column
winding cut after every sweep and raises if the sector is ever left.

Observables. All are defined by src/dimers.py. `ConfigEvaluator` re-evaluates the SAME
definitions per configuration (needed beyond 2^N-array sizes), and tests/test_mcmc_baseline.py
checks it equals the dimers.py arrays on every basis state of small tori. The quantum arm and the
exact references use the dimers.py arrays directly. Dimer correlations of BOTH arms go through
one function, `shell_correlations`, which a test checks against
TriangularDimers.dimer_correlation_by_distance (Euclidean bond-midpoint distance; the T-7 metric
question affects both arms identically and is out of scope here).

Dressed defect density [derived, first order]. Inside a sector the bare defect density is
identically 0, so the yardstick for the quantum curve is the O(h^2) DRESSING. Flipping a
non-flippable spin s of a defect-free configuration creates n_s defects (n_s = number of equal
consecutive hexagon pairs, even, in {2, 4, 6}) at Ising cost delta_s = 2|J| n_s. For the Strang
step of src/trotter.py (Ising half-steps outside) the first-order Floquet admixture is
|a_s|^2 = h^2 (dt/2)^2 / sin^2(|J| n_s dt)  (-> h^2/delta_s^2 as dt -> 0). A sudden quench
time-averages to the static dressing of the configurations it visits (sector average) PLUS the
real excitations created at t = 0 (the dressing of c0, which stays because the Ising energy
labels the defect number):
    rho_D(h) ~= h^2 [ <g>_W0 + g(c0) ],   g(c) = (1/2N) sum_s n_s (dt/2)^2 / sin^2(|J| n_s dt).
For the stripe (n_s = 2 everywhere, dt -> 0) this is (h/|J|)^2/8, the value measured in
docs/gauss_law_dimers.md §4.

Errors. M independent chains from c0 after burn-in: SE = std(chain means)/sqrt(M), which already
contains the autocorrelation. The naive 1/sqrt(samples) SE and tau_int = (SE/SE_naive)^2/2 are
reported beside it. Nonlinear correlations use a jackknife over chains.

Leakage [measured + derived]. Under the full TFIM, the weight P_out outside the defect-free W0
sector is O((h/|J|)^2) (P(W != W0) ~ h^2.08, data/gauss_law_scaling.txt). For any diagonal
observable <O> = (1 - P_out) <O>_in + P_out <O>_out, so |<O> - <O>_in| <= P_out * range(O)
EXACTLY. The in-sector conditioned curve <O>_in is the one compared with the sector baseline.

Finite-cluster diagnostic. On the small clusters where the quantum curve can be computed, the
exact infinite-time (diagonal-ensemble) average of H_QDM from c0 is also given. It separates
"relaxed, but the finite-cluster long-time value differs from the infinite-T value" from
"did not relax".

Every number this module produces is a classical statistical or classically simulated reference
under a stated ensemble; none is an H2 / hardware result.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import scipy.sparse.csgraph as csgraph

from src.backends import MemoryCeilingError
from src.dimers import TriangularDimers
from src.trotter import evolve

# Linear (diagonal-expectation) observables, all valued in [0, 1].
SCALARS = ("defect_density", "flippable_density", "rho_h", "rho_v", "rho_d", "memory")
ORIENT = ("h", "v", "d")


# --------------------------------------------------------------------------- #
# Configurations and per-configuration evaluation of the dimers.py observables
# --------------------------------------------------------------------------- #
def spins_from_index(idx, n_sites: int) -> np.ndarray:
    """(M, N) +-1 int8 spins of basis indices (site 0 = most significant bit, as dimers.py)."""
    idx = np.atleast_1d(np.asarray(idx, dtype=np.int64))
    shifts = np.arange(n_sites - 1, -1, -1, dtype=np.int64)
    return (1 - 2 * ((idx[:, None] >> shifts) & 1)).astype(np.int8)


def index_from_spins(z: np.ndarray) -> np.ndarray:
    """Inverse of spins_from_index for (M, N) spins (N <= 62)."""
    z = np.atleast_2d(z)
    bits = (1 - z.astype(np.int64)) // 2
    shifts = np.arange(z.shape[1] - 1, -1, -1, dtype=np.int64)
    return (bits << shifts).sum(axis=1)


class ConfigEvaluator:
    """Per-configuration evaluation of the src/dimers.py observables, batched over (M, N) spins.

    Geometry (bonds, triangles, hexagons, winding cuts) is taken from the TriangularDimers
    object itself, so the definitions cannot drift; only the 2^N-array evaluation is replaced.
    """

    def __init__(self, d: TriangularDimers):
        self.d = d
        self.N = d.N
        self.bonds = np.array(d.bonds, dtype=np.int64)               # (3N, 2)
        pos = {b: k for k, b in enumerate(d.bonds)}
        orient = np.empty(len(d.bonds), dtype=np.int64)
        for y in range(d.Ly):
            for x in range(d.Lx):
                orient[pos[d.horizontal_bond(x, y)]] = 0
                orient[pos[d.vertical_bond(x, y)]] = 1
                orient[pos[d.diagonal_bond(x, y)]] = 2
        self.orient = orient
        self.tri = np.array([sites for _, sites, _ in d.triangles], dtype=np.int64)  # (2N, 3)
        self.hex = np.array([d.hexagon(s) for s in range(self.N)], dtype=np.int64)  # (N, 6)
        self.hrow = [np.array([pos[d.horizontal_bond(x, y)] for x in range(d.Lx)]) for y in range(d.Ly)]
        self.vcol = [np.array([pos[d.vertical_bond(x, y)] for y in range(d.Ly)]) for x in range(d.Lx)]

    # -- dimers.py definitions, one configuration per row -------------------------------
    def dimers(self, z: np.ndarray) -> np.ndarray:
        """n_b = (1 + Z_i Z_j)/2, shape (M, 3N)."""
        return ((1 + z[:, self.bonds[:, 0]] * z[:, self.bonds[:, 1]]) // 2).astype(np.int8)

    def defects(self, z: np.ndarray) -> np.ndarray:
        """sum_t D_t with D_t = (1 + ZaZb + ZbZc + ZaZc)/4, shape (M,)."""
        a, b, c = (z[:, self.tri[:, k]].astype(np.int16) for k in range(3))
        return ((1 + a * b + b * c + a * c) // 4).sum(axis=1)

    def equal_hex_pairs(self, z: np.ndarray) -> np.ndarray:
        """n_s = number of equal consecutive hexagon-neighbour pairs, shape (M, N).
        Pi_s = 1 iff n_s = 0; on a defect-free configuration flipping s creates n_s defects."""
        nb = z[:, self.hex]                                           # (M, N, 6)
        return (nb * np.roll(nb, -1, axis=2) == 1).sum(axis=2)

    def flippable(self, z: np.ndarray) -> np.ndarray:
        """Pi_s = prod_k (1 - Z_k Z_{k+1})/2 over the hexagon of s, shape (M, N)."""
        return (self.equal_hex_pairs(z) == 0).astype(np.int8)

    def winding_x(self, n: np.ndarray, y: int) -> np.ndarray:
        return 3 * n[:, self.hrow[y]].sum(axis=1).astype(np.int64) - self.d.Lx

    def winding_y(self, n: np.ndarray, x: int) -> np.ndarray:
        return 3 * n[:, self.vcol[x]].sum(axis=1).astype(np.int64) - self.d.Ly

    def dressing(self, z: np.ndarray, J: float, dt: float) -> np.ndarray:
        """g(c) = (1/2N) sum_s n_s (dt/2)^2 / sin^2(|J| n_s dt) (module docstring), shape (M,).
        dt = 0 gives the continuous-time limit n_s / (2|J| n_s)^2."""
        ns = self.equal_hex_pairs(z)
        out = np.zeros(ns.shape)
        for k in (2, 4, 6):
            if dt > 0:
                den = math.sin(abs(J) * k * dt) ** 2
                if den < 1e-12:
                    raise ValueError(f"Trotter resonance: |J| n_s dt = {abs(J) * k * dt} is a multiple of pi")
                f = (dt / 2) ** 2 / den
            else:
                f = 1.0 / (2 * abs(J) * k) ** 2
            out += np.where(ns == k, k * f, 0.0)
        return out.sum(axis=1) / (2 * self.N)

    def scalars(self, z: np.ndarray, n0: np.ndarray) -> Dict[str, np.ndarray]:
        """Per-configuration values of SCALARS. n0 = initial dimer pattern (3N,) for `memory`
        (fraction of the initial dimers present; a defect-free c0 has exactly N dimers)."""
        n = self.dimers(z)
        out = {
            "defect_density": self.defects(z) / (2 * self.N),
            "flippable_density": self.flippable(z).sum(axis=1) / self.N,
            "memory": (n.astype(np.int64) @ n0.astype(np.int64)) / self.N,
        }
        for k, o in enumerate(ORIENT):
            out["rho_" + o] = n[:, self.orient == k].mean(axis=1)
        return out


def dimer_pattern(d: TriangularDimers, spins0: np.ndarray) -> np.ndarray:
    """Initial dimer occupations n_b(c0), shape (3N,)."""
    return ConfigEvaluator(d).dimers(np.asarray(spins0, dtype=np.int8).reshape(1, -1))[0]


# --------------------------------------------------------------------------- #
# Dimer correlations by distance: ONE function for both arms
# --------------------------------------------------------------------------- #
@dataclass
class Shells:
    """Bond-pair distance shells, binned exactly as TriangularDimers.dimer_correlation_by_distance."""

    r: List[float]
    pairs: List[Tuple[np.ndarray, np.ndarray]]   # (index_a, index_b) arrays, a < b

    @classmethod
    def build(cls, d: TriangularDimers, n_shells: Optional[int] = None, decimals: int = 6) -> "Shells":
        nb = len(d.bonds)
        acc: Dict[float, Tuple[List[int], List[int]]] = {}
        for i in range(nb):
            for j in range(i + 1, nb):
                r = round(d.torus_distance(d.bonds[i], d.bonds[j]), decimals)
                ia, ib = acc.setdefault(r, ([], []))
                ia.append(i)
                ib.append(j)
        rs = sorted(acc)[:n_shells] if n_shells else sorted(acc)
        return cls(rs, [(np.array(acc[r][0]), np.array(acc[r][1])) for r in rs])


def shell_correlations(shells: Shells, mean: np.ndarray, second: np.ndarray) -> np.ndarray:
    """Per-pair mean connected correlation <n_a n_b> - <n_a><n_b> in each shell.

    mean: (3N,) <n_b>; second: (3N, 3N) <n_a n_b>. (dimer_correlation_by_distance returns the
    pair SUM C_r; this returns C_r / n_pairs.)"""
    return np.array([float(np.mean(second[ia, ib] - mean[ia] * mean[ib])) for ia, ib in shells.pairs])


def moments_from_probabilities(d: TriangularDimers, p: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """(<n_b>, <n_a n_b>) from a probability vector over the 2^N basis, using dimers.py arrays."""
    support = np.nonzero(p)[0]
    occ = np.stack([d.dimer(b)[support] for b in d.bonds], axis=1).astype(np.float64)
    w = p[support]
    return w @ occ, occ.T @ (occ * w[:, None])


# --------------------------------------------------------------------------- #
# Initial states, sector bookkeeping, ceilings
# --------------------------------------------------------------------------- #
def check_exact_ceiling(n_sites: int, max_spins: int) -> None:
    """Refuse brute-force 2^N enumeration above the ED ceiling (SCOPE §5) before allocating."""
    if n_sites > max_spins:
        raise MemoryCeilingError(
            f"exact sector enumeration for {n_sites} spins refused: it builds 2^N arrays and the "
            f"ED ceiling is {max_spins} (SCOPE §5). Use the MCMC estimate at this size.")


def initial_spins(d: TriangularDimers, kind: str, max_spins: int = 20) -> np.ndarray:
    """(Ly, Lx) +-1 initial configuration: '3-sublattice' | 'stripe' | 'flippable'.

    'flippable' = the defect-free basis state with the most flippable spins (lowest index on
    ties; the 3-sublattice state when the torus allows it) — the rule of
    scripts/run_gauss_law.py's most_flippable_state. Off the 3Z x 3Z tori it needs the 2^N
    enumeration, so it is refused above the ED ceiling."""
    if kind == "3-sublattice":
        return d.three_sublattice_spins()
    if kind == "stripe":
        return d.stripe_spins()
    if kind == "flippable":
        if d.Lx % 3 == 0 and d.Ly % 3 == 0:
            return d.three_sublattice_spins()
        check_exact_ceiling(d.N, max_spins)
        free = np.nonzero(d.total_defects() == 0)[0]
        nflip = sum(d.flippable(s)[free].astype(int) for s in range(d.N))
        return spins_from_index(int(free[np.argmax(nflip)]), d.N).reshape(d.Ly, d.Lx)
    raise ValueError(f"unknown initial state {kind!r}")


def winding_of(ev: ConfigEvaluator, z: np.ndarray) -> Tuple[int, int]:
    n = ev.dimers(np.atleast_2d(z))
    return int(ev.winding_x(n, 0)[0]), int(ev.winding_y(n, 0)[0])


# --------------------------------------------------------------------------- #
# Exact (brute-force) references, using the dimers.py 2^N operators
# --------------------------------------------------------------------------- #
@dataclass
class EnsembleValues:
    dim: int
    scalars: Dict[str, float]
    shells: np.ndarray          # per-pair connected correlation per shell
    dressing: float             # <g> over the ensemble


def ensemble_values(d: TriangularDimers, p: np.ndarray, n0: np.ndarray, shells: Shells,
                    J: float, dt: float) -> EnsembleValues:
    """Every observable for a probability vector p over the 2^N basis, via src/dimers.py."""
    dens = d.dimer_densities(p)
    dvec = np.array([dens[b] for b in d.bonds])
    orient = ConfigEvaluator(d).orient
    sc = {
        "defect_density": d.defect_density(p),
        "flippable_density": sum(float(p @ d.flippable(s)) for s in range(d.N)) / d.N,
        "memory": float(dvec @ n0) / d.N,
    }
    for k, o in enumerate(ORIENT):
        sc["rho_" + o] = float(dvec[orient == k].mean())
    mean, second = moments_from_probabilities(d, p)
    support = np.nonzero(p)[0]
    g = ConfigEvaluator(d).dressing(spins_from_index(support, d.N), J, dt)
    return EnsembleValues(int(np.count_nonzero(p)), sc, shell_correlations(shells, mean, second),
                          float(p[support] @ g))


@dataclass
class ExactReferences:
    """Uniform averages over the flip-connected component of c0, its full W0 sector, and the whole
    defect-free manifold ('global': what a winding-blind ergodic average would give)."""

    W0: Tuple[int, int]
    n_components_in_sector: int
    component: EnsembleValues
    sector: EnsembleValues
    global_: EnsembleValues
    masks: Dict[str, np.ndarray] = field(repr=False)


def _component_labels(d: TriangularDimers, free: np.ndarray) -> np.ndarray:
    fidx = np.nonzero(free)[0]
    H = d.qdm_hamiltonian(1.0).tocsr()[fidx][:, fidx]
    _, lab = csgraph.connected_components(H, directed=False)
    full = np.full(1 << d.N, -1)
    full[fidx] = lab
    return full


def exact_references(d: TriangularDimers, spins0: np.ndarray, shells: Shells, J: float, dt: float,
                     max_spins: int) -> ExactReferences:
    """Brute-force enumeration with the src/dimers.py operators (independent of the sampler)."""
    check_exact_ceiling(d.N, max_spins)
    n0 = dimer_pattern(d, spins0)
    i0 = d.product_state_index(spins0)
    free = d.total_defects() == 0
    if not free[i0]:
        raise ValueError("initial configuration is not defect-free")
    wx, wy = d.winding_x(0), d.winding_y(0)
    W0 = (int(wx[i0]), int(wy[i0]))
    sector = free & (wx == W0[0]) & (wy == W0[1])
    lab = _component_labels(d, free)
    component = lab == lab[i0]
    n_comp = len(np.unique(lab[sector]))

    def vals(mask):
        return ensemble_values(d, mask / mask.sum(), n0, shells, J, dt)

    return ExactReferences(W0, n_comp, vals(component), vals(sector), vals(free),
                           {"component": component, "sector": sector, "global": free})


def sector_census(d: TriangularDimers, max_spins: int) -> List[Tuple[Tuple[int, int], int, int, int]]:
    """[(W, sector size, number of flip components, size of the largest)] for every sector."""
    check_exact_ceiling(d.N, max_spins)
    free = d.total_defects() == 0
    wx, wy = d.winding_x(0), d.winding_y(0)
    lab = _component_labels(d, free)
    out = []
    for W in sorted({(int(a), int(b)) for a, b in zip(wx[free], wy[free])}):
        m = free & (wx == W[0]) & (wy == W[1])
        _, counts = np.unique(lab[m], return_counts=True)
        out.append((W, int(m.sum()), len(counts), int(counts.max())))
    return out


def qdm_diagonal_ensemble(d: TriangularDimers, spins0: np.ndarray, component: np.ndarray,
                          max_dim: int = 5000, tol: float = 1e-9, max_spins: int = 20) -> np.ndarray:
    """Infinite-time average of |c0><c0| under H_QDM on a finite cluster, as basis probabilities.

    Exact dense diagonalization on the flip component; degenerate eigenspaces (H_QDM has many
    zero modes) are projected as a whole, so the result is basis-independent. h only sets the
    time scale, so it drops out. A finite-size DIAGNOSTIC (quantum, first-order effective model),
    not the ergodic baseline."""
    check_exact_ceiling(d.N, max_spins)
    idx = np.nonzero(component)[0]
    if len(idx) > max_dim:
        raise MemoryCeilingError(f"flip component of {len(idx)} states > max_dim {max_dim}")
    H = d.qdm_hamiltonian(1.0).tocsr()[idx][:, idx].toarray()
    w, v = np.linalg.eigh(H)
    k0 = int(np.searchsorted(idx, d.product_state_index(spins0)))
    p = np.zeros(len(idx))
    start = 0
    while start < len(w):
        stop = start + 1
        while stop < len(w) and w[stop] - w[start] < tol:
            stop += 1
        proj = v[:, start:stop] @ v[k0, start:stop]
        p += proj ** 2
        start = stop
    full = np.zeros(1 << d.N)
    full[idx] = p
    return full


# --------------------------------------------------------------------------- #
# The sector-restricted MCMC
# --------------------------------------------------------------------------- #
@dataclass
class Estimate:
    value: float
    se: float          # between-chain standard error (autocorrelation-aware)
    se_naive: float    # 1/sqrt(all samples) — shown only to expose the autocorrelation factor
    tau_int: float     # integrated autocorrelation time in sweeps, (se/se_naive)^2 / 2


@dataclass
class MCMCResult:
    W0: Tuple[int, int]
    n_chains: int
    n_sweeps: int
    burn_in: int
    accept_rate: float
    scalars: Dict[str, Estimate]
    dressing: Estimate
    shells: List[Tuple[float, float]]     # (value, jackknife se) per shell
    visits: Optional[np.ndarray] = None   # (n_sweeps, M) basis indices, if requested


def _estimate(trace: np.ndarray) -> Estimate:
    """trace: (n_sweeps, M) per-sweep values of M independent chains."""
    n, m = trace.shape
    chain_means = trace.mean(axis=0)
    se = float(chain_means.std(ddof=1) / math.sqrt(m)) if m > 1 else float("nan")
    se_naive = math.sqrt(float(trace.var()) / (n * m))
    tau = 0.5 * (se / se_naive) ** 2 if se_naive > 0 else float("nan")
    return Estimate(float(chain_means.mean()), se, se_naive, tau)


def sample_sector(d: TriangularDimers, spins0: np.ndarray, shells: Shells, *, J: float, dt: float,
                  n_chains: int, n_sweeps: int, burn_in: int, rng: np.random.Generator,
                  record_visits: bool = False, batch: int = 100) -> MCMCResult:
    """Uniform sampling of the flip component of spins0 (module docstring).

    All chains start at spins0 (the quench's initial state), so a chain that failed to mix would
    show up as residual memory of it. After every sweep (N move attempts) the defect count and
    EVERY row/column winding cut are checked against W0; leaving the sector raises RuntimeError.
    Works on configurations only (no 2^N arrays), so it has no size ceiling.
    """
    ev = ConfigEvaluator(d)
    N, M = d.N, n_chains
    n0 = dimer_pattern(d, spins0)
    z = np.repeat(np.asarray(spins0, dtype=np.int8).reshape(1, N), M, axis=0)
    W0 = winding_of(ev, z[:1])
    rows = np.arange(M)
    nb = len(d.bonds)
    traces = {k: np.empty((n_sweeps, M)) for k in SCALARS}
    gtrace = np.empty((n_sweeps, M))
    sum_n = np.zeros((M, nb))
    sum_nn = np.zeros((M, nb, nb))
    buf: List[np.ndarray] = []
    visits = np.empty((n_sweeps, M), dtype=np.int64) if record_visits else None
    accepted = 0

    for sweep in range(burn_in + n_sweeps):
        for s in rng.integers(N, size=(N, M)):
            # Flippability of s is decided by its 6 hexagon neighbours alone, which the flip of s
            # does not touch; so the reverse move is proposed with the same probability 1/N and is
            # also accepted. The move is its own inverse (involutive) => the kernel is symmetric,
            # hence doubly stochastic, hence the stationary distribution is UNIFORM on the component.
            nbh = z[rows[:, None], ev.hex[s]]                       # (M, 6)
            flip = np.all(nbh * np.roll(nbh, -1, axis=1) == -1, axis=1)
            z[rows[flip], s[flip]] *= -1
            accepted += int(flip.sum())
        n = ev.dimers(z)
        if (np.any(ev.defects(z) != 0)
                or any(np.any(ev.winding_x(n, y) != W0[0]) for y in range(d.Ly))
                or any(np.any(ev.winding_y(n, x) != W0[1]) for x in range(d.Lx))):
            raise RuntimeError("MCMC left the defect-free W0 sector — sampler bug")
        if sweep < burn_in:
            continue
        k = sweep - burn_in
        for key, v in ev.scalars(z, n0).items():
            traces[key][k] = v
        gtrace[k] = ev.dressing(z, J, dt)
        if record_visits:
            visits[k] = index_from_spins(z)
        buf.append(n.astype(np.float64))
        if len(buf) == batch or k == n_sweeps - 1:
            x = np.stack(buf)                                       # (B, M, nb)
            sum_n += x.sum(axis=0)
            sum_nn += np.einsum("bmi,bmj->mij", x, x)
            buf = []

    tot = M * n_sweeps
    full = shell_correlations(shells, sum_n.sum(0) / tot, sum_nn.sum(0) / tot)
    if M > 1:
        jk = np.array([shell_correlations(shells, (sum_n.sum(0) - sum_n[c]) / (tot - n_sweeps),
                                          (sum_nn.sum(0) - sum_nn[c]) / (tot - n_sweeps))
                       for c in range(M)])
        se_jk = np.sqrt((M - 1) / M * ((jk - jk.mean(0)) ** 2).sum(0))
    else:
        se_jk = np.full(len(full), np.nan)
    return MCMCResult(W0, M, n_sweeps, burn_in, accepted / ((burn_in + n_sweeps) * N * M),
                      {k: _estimate(v) for k, v in traces.items()}, _estimate(gtrace),
                      [(float(a), float(b)) for a, b in zip(full, se_jk)], visits)


# --------------------------------------------------------------------------- #
# Quantum arm: Trotter relaxation curve with identical observables
# --------------------------------------------------------------------------- #
@dataclass
class RelaxationCurve:
    times: np.ndarray
    raw: Dict[str, np.ndarray]          # <O>(t) on the full state
    cond: Dict[str, np.ndarray]         # <O>_in(t): conditioned on the defect-free W0 sector
    raw_shells: np.ndarray              # (T, n_shells) instantaneous C(r; t) — for plotting the curve
    cond_shells: np.ndarray
    p_out: np.ndarray                   # 1 - P(defect-free AND W = W0)
    p_wleak: np.ndarray                 # P(W_x(0) != W0_x or W_y(0) != W0_y): the gauss_law_scaling.txt quantity
    shells: Shells = field(repr=False, default=None)
    # first and second dimer moments per snapshot, (T, 3N) and (T, 3N, 3N): a window value of
    # C(r) must be built from WINDOW-AVERAGED moments (classify), not by averaging C(r; t)
    raw_mom: Tuple[np.ndarray, np.ndarray] = field(repr=False, default=None)
    cond_mom: Tuple[np.ndarray, np.ndarray] = field(repr=False, default=None)


def relaxation_curve(d: TriangularDimers, spins0: np.ndarray, shells: Shells, *, J: float, h: float,
                     dt: float, total_time: float, max_snapshots: int, max_spins: int) -> RelaxationCurve:
    """Noiseless 2nd-order Trotter relaxation from spins0 via src/trotter.evolve(record_every=...).

    Classical state-vector simulation of the ideal circuit, not hardware. Observables use the
    src/dimers.py 2^N arrays (plus a 2^N x 3N occupation table), so this is guarded at the ED
    ceiling (pass CeilingConfig.ed_max_spins), not only the state-vector one, before allocating."""
    if d.N > max_spins:
        raise MemoryCeilingError(
            f"relaxation curve for {d.N} spins refused: it builds 2^N x 3N observable tables and the "
            f"ceiling passed is {max_spins} (SCOPE §5).")
    n_steps = int(round(total_time / dt))
    record_every = max(1, math.ceil(n_steps / max_snapshots))
    i0 = d.product_state_index(spins0)
    psi0 = np.zeros(1 << d.N, dtype=np.complex128)
    psi0[i0] = 1.0
    _, snaps = evolve(psi0, d.N, d.bonds, J, h, n_steps * dt, n_steps, record_every=record_every)

    n0 = dimer_pattern(d, spins0)
    free = d.total_defects() == 0
    wx, wy = d.winding_x(0), d.winding_y(0)
    W0 = (int(wx[i0]), int(wy[i0]))
    in_sector = free & (wx == W0[0]) & (wy == W0[1])
    wleak = (wx != W0[0]) | (wy != W0[1])
    orient = ConfigEvaluator(d).orient
    flips = sum(d.flippable(s).astype(np.float64) for s in range(d.N)) / d.N
    occ = np.stack([d.dimer(b) for b in d.bonds], axis=1).astype(np.float64)   # (2^N, 3N)
    D = d.total_defects() / (2 * d.N)

    def obs(p):
        dens = p @ occ
        sc = {"defect_density": float(p @ D), "flippable_density": float(p @ flips),
              "memory": float(dens @ n0) / d.N}
        for k, o in enumerate(ORIENT):
            sc["rho_" + o] = float(dens[orient == k].mean())
        sup = np.nonzero(p > 0)[0]
        second = occ[sup].T @ (occ[sup] * p[sup, None])
        return sc, shell_correlations(shells, dens, second), dens, second

    times, pout, pw, rs, cs = [], [], [], [], []
    rm1, rm2, cm1, cm2 = [], [], [], []
    raw = {k: [] for k in SCALARS}
    cond = {k: [] for k in SCALARS}
    for t, psi in snaps:
        p = np.abs(psi) ** 2
        p_in = float(p[in_sector].sum())
        sc, sh, m1, m2 = obs(p)
        sci, shi, c1, c2 = obs(np.where(in_sector, p, 0.0) / p_in)
        rm1.append(m1)
        rm2.append(m2)
        cm1.append(c1)
        cm2.append(c2)
        times.append(t)
        for k in SCALARS:
            raw[k].append(sc[k])
            cond[k].append(sci[k])
        rs.append(sh)
        cs.append(shi)
        pout.append(1.0 - p_in)
        pw.append(float(p[wleak].sum()))
    a = np.asarray
    return RelaxationCurve(a(times), {k: a(v) for k, v in raw.items()}, {k: a(v) for k, v in cond.items()},
                           a(rs), a(cs), a(pout), a(pw), shells, (a(rm1), a(rm2)), (a(cm1), a(cm2)))


# --------------------------------------------------------------------------- #
# Measured leakage scaling (data/gauss_law_scaling.txt) and the verdict
# --------------------------------------------------------------------------- #
def leak_scaling(path: str, label: str, dt: float) -> Optional[Tuple[float, float]]:
    """(A, s) of the measured time-averaged P(W != W0) = A h^s for the row starting with `label`
    (e.g. '3x6 3-sublattice') at this dt, fitted (log-log least squares, as the file's printed
    slope) to the file's own points; None if the file has no such row."""
    with open(path) as fh:
        text = fh.read()
    m = re.search(r"^h_scan = (.+)$", text, re.M)
    if not m:
        return None
    hs = np.array([float(v) for v in m.group(1).split()])
    for line in text.splitlines():
        if line.startswith(label) and re.search(rf"dt={re.escape(str(dt))}\s", line) and "leak:" in line:
            lk = np.array([float(v) for v in line.split("leak:")[1].split("slope=")[0].split()])
            s, logA = np.polyfit(np.log(hs), np.log(lk), 1)
            return float(math.exp(logA)), float(s)
    return None


@dataclass
class Verdict:
    obs: str
    baseline: float          # sector-ergodic value O_W0 (exact where available, else MCMC)
    baseline_se: float
    global_value: float      # winding-blind defect-free average (nan if not available)
    de_value: float          # finite-cluster H_QDM diagonal ensemble (nan if not computed)
    late_raw: float
    late_cond: float
    late_std: float          # temporal std of the conditioned curve over the late window
    p_out: float             # late-window mean weight outside the defect-free W0 sector
    shift: float             # late_raw - late_cond: the leakage effect, measured
    envelope: float          # p_out * range(O): exact bound on |shift| (linear observables)
    toward_global: float     # p_out * (global - baseline): the shift if leaked weight looked global [inferred]
    label: str


def classify(curve: RelaxationCurve, obs: str, baseline: float, baseline_se: float, *,
             global_value: float = float("nan"), de_value: float = float("nan"),
             late_fraction: float = 0.5, frozen: bool = False, shell: Optional[int] = None) -> Verdict:
    """Operational Q3 verdict over the late window (docs/q3_thermalization.md §5).

    tol = late temporal std of the conditioned curve + 2 * baseline SE (finite clusters fluctuate
    around their long-time value; the deterministic curve has no sampling error).
    For a correlation shell the late value is C(r) of the WINDOW-AVERAGED moments <n_a>, <n_a n_b>
    (the window's mixed state, comparable with an ensemble's connected correlator); averaging the
    instantaneous C(r; t) instead would add the temporal covariance of <n_a>(t) (review fix M1).
    The std is that of C(r; t), as a fluctuation scale.
      frozen                  : c0 has no H_QDM dynamics (its flip component is c0 alone).
      indistinguishable       : within tol of BOTH O_W0 and the DE — the window cannot tell them apart.
      thermalized-in-sector   : |late conditioned mean - O_W0| <= tol.
      finite-size-DE-offset   : fails that, but matches the H_QDM diagonal ensemble within tol:
                                relaxed, yet the finite cluster's long-time value is not infinite-T.
      not-relaxed-in-window   : neither.
    Leakage is reported beside the label: the measured shift raw - conditioned, its exact bound,
    and the inferred drift toward the global average."""
    late = curve.times >= (1.0 - late_fraction) * curve.times[-1]
    if shell is None:
        raw, cond, span = curve.raw[obs][late], curve.cond[obs][late], 1.0
        lr, lc, sd = float(raw.mean()), float(cond.mean()), float(cond.std())
    else:
        span = float("nan")

        def window_c(mom):
            return float(shell_correlations(curve.shells, mom[0][late].mean(0), mom[1][late].mean(0))[shell])

        lr, lc = window_c(curve.raw_mom), window_c(curve.cond_mom)
        sd = float(curve.cond_shells[late, shell].std())
    po = float(curve.p_out[late].mean())
    tol = sd + 2 * baseline_se + 1e-12
    has_de = not math.isnan(de_value)
    if frozen:
        label = "frozen"
    elif has_de and abs(lc - baseline) <= tol and abs(lc - de_value) <= tol and abs(de_value - baseline) > 1e-9:
        label = "indistinguishable"
    elif abs(lc - baseline) <= tol:
        label = "thermalized-in-sector"
    elif has_de and abs(lc - de_value) <= tol:
        # Relaxed to the H_QDM diagonal ensemble, but that long-time value is NOT infinite-T here:
        # on a finite cluster |c0> has a nonzero energy variance within its component, so the
        # diagonal ensemble carries an O(1/N) offset from the band centre [inferred to vanish as
        # N->inf; see docs/q3_thermalization.md T-12]. A finite-size effect, not a failure to relax.
        label = "finite-size-DE-offset"
    else:
        label = "not-relaxed-in-window"
    # envelope = po*span is EXACT, not a fit: a diagonal <O> = (1-po)<O>_in + po<O>_out is a convex
    # combination, so |<O> - <O>_in| = po|<O>_out - <O>_in| <= po*range(O) with no assumption on <O>_out.
    return Verdict(obs, baseline, baseline_se, global_value, de_value, lr, lc, sd, po, lr - lc,
                   po * span, po * (global_value - baseline), label)
