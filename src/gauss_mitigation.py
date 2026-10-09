"""Skeptical test: can the emergent Gauss law detect / mitigate noise? (SCOPE §3, handoff/02)

Everything here is a LOCAL noisy simulation of the reference-style quench (triangular AFM
TFIM, Trotterised) under an explicit, stated noise model — see config.GaussLawConfig and
docs/gauss_law_dimers.md §5. Nothing is hardware-calibrated.

Noise model: after every Trotter step, every qubit independently suffers X, Y, Z with
probabilities (px, py, pz). Simulated two ways:
  - exact density matrix (small N; observables are diagonal so only diag(rho) is kept
    for analysis, but the full rho is evolved);
  - Monte-Carlo Pauli trajectories (larger N; unbiased, with batch-mean error bars).

Mitigation estimators compared on the SAME noisy data (all target observables diagonal):
  raw          <O>_noisy
  postselect   keep only basis outcomes with zero Gauss-law defects (symmetry-verification
               style, but on an APPROXIMATE constraint -> biased even at p = 0)
  selfmit      global-depolarising rescaling <O> = Obar + (<O>_noisy - Obar)/F, with
               F = (Dbar - D_noisy)/(Dbar - D_floor) from the defect density in the same
               shots (Dbar = 1/4 per triangle = maximally mixed). Two variants: the
               physics floor D_floor taken from the exact noiseless run ("oracle", only
               possible when the circuit is classically simulable) or D_floor = 0 ("naive").
  zne          Richardson extrapolation over idealised noise scalings p -> lambda p.
  pec          unbiased given the exact noise model; only its sampling overhead gamma^2
               is computed (no simulation needed).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np

from src.dimers import TriangularDimers
from src.trotter import apply_x_rotations, ising_diagonal

Pauli3 = Tuple[float, float, float]


# --------------------------------------------------------------------------- #
# Noisy evolution
# --------------------------------------------------------------------------- #
def trotter_unitary(n: int, bonds, J: float, h: float, dt: float) -> np.ndarray:
    """Dense 2nd-order Trotter step U2(dt) (same splitting as src.trotter.trotter2_step)."""
    dim = 1 << n
    half = np.exp(-0.5j * dt * ising_diagonal(n, bonds, J))
    ux = np.eye(dim, dtype=np.complex128)
    for c in range(dim):
        ux[:, c] = apply_x_rotations(ux[:, c].copy(), n, theta=-h * dt)
    return half[:, None] * ux * half[None, :]


def _flip_perm(n: int, q: int) -> np.ndarray:
    return np.arange(1 << n) ^ (1 << (n - 1 - q))


def _zsign(n: int, q: int) -> np.ndarray:
    return (1 - 2 * ((np.arange(1 << n) >> (n - 1 - q)) & 1)).astype(np.float64)


def pauli_channel_dm(rho: np.ndarray, n: int, q: int, pxyz: Pauli3) -> np.ndarray:
    """rho -> (1-p)rho + px XrhoX + py YrhoY + pz ZrhoZ on qubit q."""
    px, py, pz = pxyz
    if px == py == pz == 0:
        return rho
    perm, s = _flip_perm(n, q), _zsign(n, q)
    zz = s[:, None] * s[None, :]
    xrx = rho[perm][:, perm]
    out = (1 - px - py - pz) * rho
    if px:
        out += px * xrx
    if py:
        out += py * (xrx * zz)   # Y rho Y = X Z rho Z X  -> sign pattern applied after the flip
    if pz:
        out += pz * (rho * zz)
    return out


def evolve_dm(psi0: np.ndarray, n: int, U: np.ndarray, steps: int, pxyz: Pauli3) -> List[np.ndarray]:
    """Exact noisy density-matrix evolution; returns diag(rho) after each step (len steps+1)."""
    rho = np.outer(psi0, psi0.conj())
    diags = [np.real(np.diag(rho)).copy()]
    Ud = U.conj().T
    for _ in range(steps):
        rho = U @ rho @ Ud
        for q in range(n):
            rho = pauli_channel_dm(rho, n, q, pxyz)
        diags.append(np.real(np.diag(rho)).copy())
    return diags


def evolve_trajectories(
    psi0: np.ndarray, n: int, bonds, J: float, h: float, dt: float, steps: int,
    pxyz: Pauli3, n_traj: int, seed: int, n_batches: int = 20,
) -> Tuple[np.ndarray, np.ndarray]:
    """Monte-Carlo Pauli trajectories. Returns (mean_probs[step], batch_probs[batch, step])
    so any linear diagonal estimator gets a batch-mean standard error."""
    rng = np.random.default_rng(seed)
    half = np.exp(-0.5j * dt * ising_diagonal(n, bonds, J))
    dim = 1 << n
    perms = [_flip_perm(n, q) for q in range(n)]
    signs = [_zsign(n, q) for q in range(n)]
    cum = np.cumsum([pxyz[0], pxyz[1], pxyz[2]])
    batch = np.zeros((n_batches, steps + 1, dim))
    per = int(np.ceil(n_traj / n_batches))
    for t in range(per * n_batches):
        psi = psi0.astype(np.complex128).copy()
        b = t % n_batches
        batch[b, 0] += np.abs(psi) ** 2
        for s in range(1, steps + 1):
            psi = half * apply_x_rotations(half * psi, n, theta=-h * dt)
            r = rng.random(n)
            for q in np.nonzero(r < cum[2])[0]:
                if r[q] < cum[0]:
                    psi = psi[perms[q]]
                elif r[q] < cum[1]:
                    psi = (signs[q] * psi)[perms[q]]
                else:
                    psi = signs[q] * psi
            batch[b, s] += np.abs(psi) ** 2
    batch /= per
    return batch.mean(axis=0), batch


# --------------------------------------------------------------------------- #
# Estimators (all on probability vectors over the computational basis)
# --------------------------------------------------------------------------- #
@dataclass
class Targets:
    """Diagonal target observables (per-shot value arrays) + Gauss-law bookkeeping."""

    names: List[str]
    values: List[np.ndarray]      # per-basis-state estimator value
    defects: np.ndarray           # sum_t D_t per basis state
    n_triangles: int

    @classmethod
    def build(cls, d: TriangularDimers, spins0: np.ndarray) -> "Targets":
        n = d.N
        z = [d.z(i).astype(np.float64) for i in range(n)]
        s0 = np.asarray(spins0).reshape(-1)
        # O1: memory of the initial pattern, (1/N) sum_i s_i(0) Z_i
        mem = sum(s0[i] * z[i] for i in range(n)) / n
        # O2: farthest-pair dimer-dimer product (1/#pairs) sum <n_a n_b>
        pairs, rmax = [], 0.0
        for i, a in enumerate(d.bonds):
            for b in d.bonds[i + 1:]:
                r = round(d.torus_distance(a, b), 6)
                if r > rmax + 1e-9:
                    rmax, pairs = r, [(a, b)]
                elif abs(r - rmax) < 1e-9:
                    pairs.append((a, b))
        dd = sum(d.dimer(a).astype(np.float64) * d.dimer(b) for a, b in pairs) / len(pairs)
        # O3: next-nearest-neighbour spin correlator (distance sqrt3): (x,y)-(x+2,y+1)
        nnn = [(d.s(x, y), d.s(x + 2, y + 1)) for y in range(d.Ly) for x in range(d.Lx)]
        czz = sum(z[i] * z[j] for i, j in nnn) / len(nnn)
        return cls(["pattern memory m", f"dimer-dimer <nn> r={rmax:.3g}", "NNN <ZZ>"],
                   [mem, dd, czz], d.total_defects().astype(np.float64), 2 * n)

    @property
    def Dbar(self) -> float:
        """Defect density per triangle of the maximally mixed state (= 2/8)."""
        return 0.25

    def defect_density(self, p: np.ndarray) -> float:
        return float(p @ self.defects) / self.n_triangles

    def raw(self, p: np.ndarray) -> np.ndarray:
        return np.array([p @ v for v in self.values])

    def postselect(self, p: np.ndarray) -> Tuple[np.ndarray, float]:
        keep = self.defects == 0
        acc = float(p[keep].sum())
        return np.array([p[keep] @ v[keep] / acc for v in self.values]), acc

    def selfmit(self, p: np.ndarray, floor: float) -> Tuple[np.ndarray, float]:
        """Rescale toward the maximally mixed value assuming a GLOBAL depolarising channel.

        The estimate obar + (<O>_noisy - obar)/F is exact only if the physical channel is
        rho -> F rho + (1-F) I/2^N, where a SINGLE scalar F damps every observable identically.
        Under LOCAL per-qubit Pauli noise that is false: different observables decay at
        different rates (an operator on k qubits sees ~F_1^k, whereas the defect density used
        here to infer F mixes all weights), so the one F read from the Gauss-law defect density
        does not match the true per-observable contraction. Hence it can over- or under-correct
        -- it even worsens the pattern-memory estimator in the data -- which is why self-
        mitigation is rejected as a general method rather than a reliable estimator.
        `floor` is the F=1 defect density: the exact noiseless value ("oracle") or 0 ("naive").
        """
        F = (self.Dbar - self.defect_density(p)) / (self.Dbar - floor)
        obar = np.array([v.mean() for v in self.values])
        return obar + (self.raw(p) - obar) / F, F

    def shot_variance(self, p: np.ndarray) -> np.ndarray:
        """Single-shot variance of each estimator under distribution p."""
        return np.array([p @ v**2 - (p @ v) ** 2 for v in self.values])


def richardson(lambdas: Sequence[float]) -> np.ndarray:
    """Coefficients c with sum_i c_i f(lambda_i) = f(0) exactly for polynomials of degree < k."""
    lam = np.asarray(lambdas, dtype=float)
    V = np.vander(lam, increasing=True)          # rows [1, l, l^2, ...]
    return np.linalg.solve(V.T, np.eye(len(lam))[0])


def pec_gamma_single(pxyz: Pauli3) -> float:
    """One-norm of the quasi-probability inverse of a single-qubit Pauli channel."""
    px, py, pz = pxyz
    p = {"I": 1 - px - py - pz, "X": px, "Y": py, "Z": pz}
    labels = "IXYZ"

    def anti(a, b):
        return a != "I" and b != "I" and a != b

    # Pauli fidelities f_Q = sum_P p_P (-1)^{<P,Q>}
    f = {Q: sum(p[P] * (-1 if anti(P, Q) else 1) for P in labels) for Q in labels}
    # inverse channel: probabilities q_P = 1/4 sum_Q (-1)^{<P,Q>} / f_Q
    q = {P: 0.25 * sum((-1 if anti(P, Q) else 1) / f[Q] for Q in labels) for P in labels}
    return float(sum(abs(v) for v in q.values()))


def single_error_detection(d: TriangularDimers, p: np.ndarray) -> Dict[str, float]:
    """Probability that ONE X (or Z) error on a uniformly random qubit, applied to a state
    with outcome distribution p, changes the measured defect count (Z: exactly 0 because
    Z_q commutes with every D_t; Y acts like X on the computational-basis distribution).

    Why Z is invisible to the Gauss law: every D_t is a product/function of Z operators, so
    [Z_q, D_t] = 0 for all t -- a Z error leaves the whole syndrome unchanged and is never
    flagged. This is the structural reason the mitigation verdict is asymmetric: Gauss-law
    postselection can only catch the X/Y part of the noise (which flips spins and so can move
    a triangle in/out of G_t = 3). Pure dephasing (Z) passes straight through undetected,
    which is why postselection does essentially nothing against a dephasing channel. A general
    depolarising channel has a 1/3 Z component that is likewise uncatchable, so even its
    detectable part is only a fraction of the total error -- correction via this constraint is
    impossible (distance 1: a weight-1 Z anywhere is undetectable).
    """
    D = d.total_defects()
    out = 0.0
    for q in range(d.N):
        perm = _flip_perm(d.N, q)
        out += float(p @ (D[perm] != D))
    return {"X": out / d.N, "Y": out / d.N, "Z": 0.0}
