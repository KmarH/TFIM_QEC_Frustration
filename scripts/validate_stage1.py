"""Stage 1 small-size validation and memory probe (SCOPE §5, §14).

Produces reproducible, recorded numbers (never invented) that cross-check the
statevector and ED backends and empirically probe statevector memory before any
ceiling is frozen. Writes a short report to data/stage1_validation.txt.

Run:  python scripts/validate_stage1.py   (from repo root, venv active)

Checks:
  1. ED ground-state energy vs dense eigh on a small lattice (exact agreement).
  2. Statevector energy conservation under Trotter (|dE| small; H commutes with
     the propagator so <H> is conserved up to Trotter/float error).
  3. Trotter convergence to exact expm with increasing n_steps (O(dt^2)).
  4. Empirical peak-memory probe of a statevector allocation at a target N.
"""

from __future__ import annotations

import os
import sys

import numpy as np
import scipy.sparse.linalg as sla

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from config import RunConfig  # noqa: E402
from src.backends import product_state, run_ed, run_statevector  # noqa: E402
from src.lattice import square_bonds  # noqa: E402
from src.observables import energy  # noqa: E402
from src.operators import tfim_hamiltonian  # noqa: E402
from src.trotter import evolve  # noqa: E402


def check_ed_vs_dense() -> str:
    cfg = RunConfig()
    cfg.backend = "ed"
    cfg.lattice.Lx, cfg.lattice.Ly = 3, 2  # 6 spins
    cfg.model.J, cfg.model.h = 1.0, 0.7
    res = run_ed(cfg, k=1)
    H = tfim_hamiltonian(6, res.bonds, cfg.model.J, cfg.model.h).toarray()
    w = np.linalg.eigvalsh(H)
    diff = abs(res.eigenvalues[0] - w[0])
    return (
        f"[1] ED vs dense (6 spins, J=1.0, h=0.7): "
        f"E0_lanczos={res.eigenvalues[0]:.10f}, E0_dense={w[0]:.10f}, "
        f"|diff|={diff:.2e}"
    )


def check_energy_conservation() -> str:
    cfg = RunConfig()
    cfg.lattice.Lx, cfg.lattice.Ly = 3, 3  # 9 spins
    cfg.model.J, cfg.model.h = 1.0, 1.0
    cfg.trotter.total_time, cfg.trotter.n_steps = 2.0, 200
    bonds = square_bonds(3, 3, "open")
    psi0 = product_state(9, "all_up")
    e0 = energy(psi0, 9, bonds, 1.0, 1.0)
    out = run_statevector(cfg, init_spec="all_up")
    e1 = energy(out.final_state, 9, bonds, 1.0, 1.0)
    return (
        f"[2] Energy conservation (9 spins, T=2.0, 200 steps): "
        f"E(0)={e0:.8f}, E(T)={e1:.8f}, |dE|={abs(e1 - e0):.2e}"
    )


def check_trotter_convergence() -> str:
    n = 4
    bonds = square_bonds(2, 2, "open")
    J, h, T = 1.0, 0.8, 1.0
    H = tfim_hamiltonian(n, bonds, J, h)
    psi0 = product_state(n, "all_up")
    exact = sla.expm_multiply(-1j * T * H, psi0)
    lines = ["[3] Trotter convergence to exact expm (4 spins, T=1.0):"]
    prev = None
    for steps in (10, 20, 40, 80):
        final, _ = evolve(psi0, n, bonds, J, h, T, steps)
        err = float(np.linalg.norm(final - exact))
        ratio = f"{prev / err:.2f}x" if prev else "   -"
        lines.append(f"    n_steps={steps:3d}  ||err||={err:.3e}  (improvement {ratio})")
        prev = err
    lines.append("    (2nd-order expectation: ~4x error reduction per doubling)")
    return "\n".join(lines)


def probe_statevector_memory(sizes=((20, 5, 4), (22, 11, 2), (24, 6, 4))) -> str:
    """Empirical statevector memory probe at/near the ceiling (SCOPE §5, §14).

    Reports resource.getrusage ru_maxrss (real peak RSS, which tracemalloc
    undercounts — qc-reviewer M2) alongside the theoretical 2^N*16-byte state
    size. Each size is probed in THIS process; ru_maxrss is monotonic, so the
    reported peak at a given N already includes earlier (smaller) runs — the
    largest N dominates, which is the number that matters for the ceiling.
    """
    import resource

    lines = ["[4] Statevector memory probe (ru_maxrss, real peak; 2 Trotter steps):"]
    for (n_target, Lx, Ly) in sizes:
        assert Lx * Ly == n_target
        bonds = square_bonds(Lx, Ly, "open")
        psi = product_state(n_target, "all_up")
        final, _ = evolve(psi, n_target, bonds, J=1.0, h=1.0, total_time=0.2, n_steps=2)
        peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        theo = (1 << n_target) * 16 / 1e6
        lines.append(
            f"    N={n_target} ({Lx}x{Ly}): maxRSS={peak_mb:.0f} MB, "
            f"theo_state={theo:.0f} MB (ratio {peak_mb / theo:.1f}x), "
            f"norm(final)={np.linalg.norm(final):.6f}"
        )
    lines.append("    (ru_maxrss is monotonic across sizes; the largest N is the binding peak.)")
    return "\n".join(lines)


def probe_ed_memory(sizes=((16, 4, 4), (18, 6, 3), (20, 5, 4))) -> str:
    """Empirical ED build+Lanczos memory probe (SCOPE §5, §14).

    Validates the sparse Hamiltonian builder (review/01-stage1.md C1 fix) and the
    ed_max_spins ceiling. N=22 is deliberately NOT probed here: it was measured
    separately at ~8 GB maxRSS, which is the memory edge on this ~7.6 GB host, so
    the frozen safe ceiling is N=20.
    """
    import resource

    lines = ["[5] ED build+Lanczos probe (sparse builder; ru_maxrss):"]
    for (n_target, Lx, Ly) in sizes:
        assert Lx * Ly == n_target
        bonds = square_bonds(Lx, Ly, "open")
        H = tfim_hamiltonian(n_target, bonds, 1.0, 1.0)
        nnz = H.nnz
        e0 = float(sla.eigsh(H, k=1, which="SA", return_eigenvectors=False)[0])
        peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
        lines.append(
            f"    N={n_target} ({Lx}x{Ly}): nnz={nnz:,}, E0={e0:+.6f}, maxRSS={peak_mb:.0f} MB"
        )
    lines.append("    (Builder previously OOMed at N=16 before the C1 sparse fix.)")
    return "\n".join(lines)


def main() -> None:
    lines = ["Stage 1 validation — recorded numbers (reproducible, not invented)", "=" * 66]
    lines.append(check_ed_vs_dense())
    lines.append(check_energy_conservation())
    lines.append(check_trotter_convergence())
    lines.append(probe_statevector_memory())
    lines.append(probe_ed_memory())

    report = "\n".join(lines) + "\n"
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    out_path = os.path.join(ROOT, "data", "stage1_validation.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"written to {out_path}")


if __name__ == "__main__":
    main()
