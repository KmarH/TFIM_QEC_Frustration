"""Simulation backends behind the config switch (SCOPE §5).

- "ed"          : sparse exact diagonalization via Lanczos (scipy eigsh) for the
                  ground state and low-lying spectrum of the TFIM.
- "statevector" : dense exact 2nd-order Trotter evolution of a product state.

Both enforce the SCOPE §5 size ceilings as guard rails: exceeding them raises a
MemoryCeilingError rather than silently allocating. Raising the ceilings beyond
SCOPE §5 requires an empirical memory probe first (SCOPE §14) — not done here.

These backends are geometry-agnostic: they consume whichever nearest-neighbour
bond list `_bonds_for` returns (square = Stage 1, triangular = Stage 3). The
"stim" and "nexus" backends are Stage 2+/hardware and are not dispatched here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import scipy.sparse.linalg as spla

from config import RunConfig
from src.lattice import square_bonds, triangular_bonds
from src.operators import tfim_hamiltonian
from src.trotter import evolve


class MemoryCeilingError(RuntimeError):
    """Raised when a requested system size exceeds a SCOPE §5 ceiling."""


@dataclass
class EDResult:
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray  # columns are eigenvectors
    bonds: List[Tuple[int, int]]


@dataclass
class EvolutionResult:
    final_state: np.ndarray
    snapshots: List[Tuple[float, np.ndarray]]
    bonds: List[Tuple[int, int]]


def _bonds_for(cfg: RunConfig) -> List[Tuple[int, int]]:
    lat = cfg.lattice
    # The TFIM operator / Trotter / observable code is geometry-agnostic: it only
    # consumes a nearest-neighbour bond list. Geometry selection therefore lives
    # entirely here (SCOPE §4 stage order: square = Stage 1, triangular = Stage 3).
    if lat.geometry == "square":
        return square_bonds(lat.Lx, lat.Ly, lat.boundary)
    if lat.geometry == "triangular":
        return triangular_bonds(lat.Lx, lat.Ly, lat.boundary)
    raise NotImplementedError(f"unknown geometry {lat.geometry!r}")


def run_ed(cfg: RunConfig, k: int = 1) -> EDResult:
    """Lanczos diagonalization for the k lowest eigenpairs of the TFIM."""
    n = cfg.lattice.n_sites
    if n > cfg.ceilings.ed_max_spins:
        raise MemoryCeilingError(
            f"ED requested for {n} spins > ceiling {cfg.ceilings.ed_max_spins} "
            "(SCOPE §5; raise only after a memory probe)."
        )
    bonds = _bonds_for(cfg)
    H = tfim_hamiltonian(n, bonds, cfg.model.J, cfg.model.h)

    dim = 1 << n
    if dim <= 4:
        # eigsh needs k < dim-1; fall back to dense for tiny systems.
        vals, vecs = np.linalg.eigh(H.toarray())
        return EDResult(vals[:k], vecs[:, :k], bonds)

    k_eff = min(k, dim - 2)
    vals, vecs = spla.eigsh(H, k=k_eff, which="SA")
    order = np.argsort(vals)
    return EDResult(vals[order], vecs[:, order], bonds)


def product_state(n_sites: int, spec: str = "all_up") -> np.ndarray:
    """Build a computational-basis product state.

    spec:
      "all_up"   -> |00...0>  (all Z = +1)
      "all_down" -> |11...1>  (all Z = -1)
      "neel"     -> |0101...> (staggered), site 0 = MSB.

    Physical intent: "all_up"/"all_down" are eigenstates of the Ising (ZZ) term
    and carry <X>=0, so they are useful as cheap smoke tests but show little
    relaxation. The staggered "neel" state is inhomogeneous and far from any
    eigenstate, making it the right starting point for the Haghshenas-style
    relaxation/thermalization observables (SCOPE Q3), where a local or staggered
    magnetization is tracked as it decays toward its infinite-temperature value.
    """
    dim = 1 << n_sites
    psi = np.zeros(dim, dtype=np.complex128)
    if spec == "all_up":
        index = 0
    elif spec == "all_down":
        index = dim - 1
    elif spec == "neel":
        bits = 0
        for site in range(n_sites):
            if site % 2 == 1:
                bits |= 1 << (n_sites - 1 - site)
        index = bits
    else:
        raise ValueError(f"unknown product-state spec {spec!r}")
    psi[index] = 1.0
    return psi


def run_statevector(
    cfg: RunConfig,
    initial_state: Optional[np.ndarray] = None,
    init_spec: str = "all_up",
    record_every: int = 0,
) -> EvolutionResult:
    """Dense 2nd-order Trotter evolution of a product state under the config."""
    n = cfg.lattice.n_sites
    if n > cfg.ceilings.statevector_max_spins:
        raise MemoryCeilingError(
            f"statevector requested for {n} spins > ceiling "
            f"{cfg.ceilings.statevector_max_spins} (SCOPE §5; probe before raising)."
        )
    bonds = _bonds_for(cfg)
    psi0 = initial_state if initial_state is not None else product_state(n, init_spec)

    final, snaps = evolve(
        psi0,
        n_sites=n,
        bonds=bonds,
        J=cfg.model.J,
        h=cfg.model.h,
        total_time=cfg.trotter.total_time,
        n_steps=cfg.trotter.n_steps,
        record_every=record_every,
    )
    return EvolutionResult(final, snaps, bonds)


def run(cfg: RunConfig, **kwargs) -> object:
    """Dispatch on cfg.backend (SCOPE §5 single switch)."""
    if cfg.backend == "ed":
        return run_ed(cfg, **kwargs)
    if cfg.backend == "statevector":
        return run_statevector(cfg, **kwargs)
    if cfg.backend in ("stim", "nexus"):
        raise NotImplementedError(
            f"backend {cfg.backend!r} is Stage 2+/hardware and not available in Stage 1"
        )
    raise ValueError(f"unknown backend {cfg.backend!r}")
