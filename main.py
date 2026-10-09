"""Stage 1 entry point: run the TFIM simulation from config.py.

Reads the single CONFIG object, runs the selected backend, and prints the
HANDOFF §3 observables. This is a thin driver — all tunables live in config.py.
No hardware, no network. Serial execution (SCOPE §5 memory constraint).

Usage:
    python main.py                 # uses CONFIG defaults (statevector)
    (edit config.py to change lattice size, backend, field, Trotter steps)
"""

from __future__ import annotations

import numpy as np

from config import CONFIG, RunConfig
from src.backends import (
    EDResult,
    EvolutionResult,
    product_state,
    run_ed,
    run_statevector,
)
from src.observables import (
    energy,
    magnetization_variance_z,
    total_magnetization_x,
    total_magnetization_z,
    two_point_correlations_z,
)


def report_state(psi: np.ndarray, cfg: RunConfig, bonds) -> None:
    n = cfg.lattice.n_sites
    mz = total_magnetization_z(psi, n)
    mx = total_magnetization_x(psi, n)
    var = magnetization_variance_z(psi, n)
    e = energy(psi, n, bonds, cfg.model.J, cfg.model.h)
    corr = two_point_correlations_z(psi, n, connected=True)

    print(f"  sites            : {n} ({cfg.lattice.Lx}x{cfg.lattice.Ly}, {cfg.lattice.boundary})")
    print(f"  M_z = sum<Z_i>   : {mz:+.6f}")
    print(f"  M_x = sum<X_i>   : {mx:+.6f}")
    print(f"  Var(M_z)         : {var:+.6f}")
    print(f"  <H>              : {e:+.6f}")
    if corr:
        avg_c = sum(corr.values()) / len(corr)
        print(f"  mean connected C_zz over pairs : {avg_c:+.6f}")


def main(cfg: RunConfig = CONFIG) -> None:
    print(f"TFIM Stage 1 — backend = {cfg.backend!r}")
    print(f"model: H = -J sum ZZ - h sum X, J={cfg.model.J}, h={cfg.model.h}")

    if cfg.backend == "ed":
        res: EDResult = run_ed(cfg, k=1)
        gs = res.eigenvectors[:, 0]
        print(f"ground-state energy E0 = {res.eigenvalues[0]:+.6f}")
        report_state(gs, cfg, res.bonds)

    elif cfg.backend == "statevector":
        print(
            f"trotter: T={cfg.trotter.total_time}, n_steps={cfg.trotter.n_steps}, "
            f"order={cfg.trotter.order}"
        )
        res2: EvolutionResult = run_statevector(cfg, init_spec="all_up")
        print("final state observables:")
        report_state(res2.final_state, cfg, res2.bonds)

    else:
        raise SystemExit(
            f"backend {cfg.backend!r} not available in Stage 1 (Stage 2+/hardware)."
        )


if __name__ == "__main__":
    main()
