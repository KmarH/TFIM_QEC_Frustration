"""Backend tests: ED vs dense diagonalization, ceiling guards, dispatch."""

import numpy as np
import pytest

from config import RunConfig
from src.backends import (
    MemoryCeilingError,
    run,
    run_ed,
    run_statevector,
)
from src.operators import tfim_hamiltonian


def test_ed_ground_state_matches_dense():
    cfg = RunConfig()
    cfg.backend = "ed"
    cfg.lattice.Lx, cfg.lattice.Ly = 3, 2  # 6 spins
    cfg.lattice.boundary = "open"
    cfg.model.J, cfg.model.h = 1.0, 0.7

    res = run_ed(cfg, k=1)
    H = tfim_hamiltonian(6, res.bonds, cfg.model.J, cfg.model.h).toarray()
    w = np.linalg.eigvalsh(H)
    assert abs(res.eigenvalues[0] - w[0]) < 1e-8


def test_statevector_dispatch_matches_direct():
    cfg = RunConfig()
    cfg.backend = "statevector"
    cfg.lattice.Lx, cfg.lattice.Ly = 2, 2
    cfg.trotter.total_time, cfg.trotter.n_steps = 1.0, 30

    out = run(cfg, init_spec="all_up")
    direct = run_statevector(cfg, init_spec="all_up")
    assert np.allclose(out.final_state, direct.final_state)


def test_ed_ceiling_guard():
    cfg = RunConfig()
    cfg.backend = "ed"
    cfg.ceilings.ed_max_spins = 4
    cfg.lattice.Lx, cfg.lattice.Ly = 3, 2  # 6 > 4
    with pytest.raises(MemoryCeilingError):
        run_ed(cfg)


def test_statevector_ceiling_guard():
    cfg = RunConfig()
    cfg.backend = "statevector"
    cfg.ceilings.statevector_max_spins = 3
    cfg.lattice.Lx, cfg.lattice.Ly = 2, 2  # 4 > 3
    with pytest.raises(MemoryCeilingError):
        run_statevector(cfg)


def test_unknown_backend_raises():
    cfg = RunConfig()
    cfg.backend = "stim"
    with pytest.raises(NotImplementedError):
        run(cfg)
