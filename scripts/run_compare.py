"""Q1 run: simulated Z2(step) on reduced square lattices vs the H2 dataset (handoff/03).

Usage:
    python scripts/run_compare.py --data /path/to/zenodo_data      # or env TFIM_ZENODO_DATA
    python scripts/run_compare.py --data tests/fixtures/zenodo_mini  # synthetic smoke test

Writes data/q1_compare.txt for the real dataset. A fixture whose README says SYNTHETIC is
run to stdout only and every line is labelled, so synthetic numbers never land in data/.
All parameters come from config.CONFIG.compare. Local only; refuses over-ceiling sizes.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402
import scipy.sparse.linalg as sla  # noqa: E402

from config import CONFIG  # noqa: E402
from src.compare import (  # noqa: E402
    CAVEAT, ZenodoData, check_ceiling, compare_z2, gauge_check_angles, qasm_step_bonds,
    read_qasm, ry_product_state,
)
from src.lattice import square_bonds  # noqa: E402
from src.observables import total_z_sq_normalized  # noqa: E402
from src.operators import tfim_hamiltonian  # noqa: E402


def is_synthetic(root: str) -> bool:
    p = os.path.join(root, "README.md")
    if not os.path.isfile(p):
        return False
    with open(p, encoding="utf-8") as fh:
        return "SYNTHETIC" in fh.read()


def _inside(path: str, parent: str) -> bool:
    path, parent = os.path.realpath(path), os.path.realpath(parent)
    return os.path.commonpath([path, parent]) == parent


def source_status(root: str):
    """(synthetic, trusted_source) for a data directory. trusted_source is the positive check
    BEFORE circuit verification: not synthetic (README marker or under tests/fixtures) and it
    carries the dataset README. main() additionally requires verify_circuits for every quench."""
    synthetic = is_synthetic(root) or _inside(root, os.path.join(REPO, "tests", "fixtures"))
    trusted = not synthetic and os.path.isfile(os.path.join(root, "README.md"))
    return synthetic, trusted


def verify_circuits(root: str, quench: int, theta: float, log) -> bool:
    """Check the published QASM against the harness parameters; abort on a real mismatch.

    Angles are compared WITH their signs: only the gauge-equivalent patterns of (J, h, theta)
    pass (src.compare.gauge_check_angles); a non-gauge pairing or a mixed-sign layer aborts.
    Returns True only if angles match and the bond set equals one candidate index map."""
    c = CONFIG.compare
    path = os.path.join(root, "circuits", f"quench{quench}_step1.qasm")
    if not os.path.isfile(path):
        log(f"  [unverified] {path} not found: gate angles and bond list NOT re-checked")
        return False
    g = read_qasm(path)
    bonds = set(qasm_step_bonds(path))
    rzz = [a for *_, a in g["rzz"]]
    rx = [a for _, a in g["rx"]]
    ry = [a for _, a in g["ry"]]
    log(f"  QASM quench{quench}_step1: {len(bonds)} distinct rzz pairs, signed angles: rzz "
        f"{sorted({round(a, 6) for a in rzz})}, rx {sorted({round(a, 6) for a in rx})}, "
        f"ry {sorted({round(a, 6) for a in ry})}")
    label, problems = gauge_check_angles(rzz, rx, ry, c.J, c.h, c.dt, theta)
    if problems:
        raise SystemExit(f"QASM quench{quench} does not match CompareConfig (J={c.J}, h={c.h}, "
                         f"dt={c.dt}, theta={theta:+.6f}) up to gauge: {problems} — refusing to compare.")
    log(f"  signs: literal circuit is {label} of CompareConfig, gauge-equivalent [derived]")
    # Bond SET under the two plausible (x,y)->qubit maps; the true map is not in the dataset.
    Lx, Ly = c.data_Lx, c.data_Ly
    ours = set(square_bonds(Lx, Ly, c.boundary))                 # q = y*Lx + x (repo row-major)
    col = {tuple(sorted(((i % Lx) * Ly + i // Lx, (j % Lx) * Ly + j // Lx))) for i, j in ours}  # q = x*Ly + y
    log(f"  bond set equals square_bonds({Lx},{Ly},{c.boundary!r}) with q=y*Lx+x: {bonds == ours}; "
        f"with q=x*Ly+y: {bonds == col}")
    if not (bonds == ours or bonds == col):
        log("  [unverified] QASM bond set matches neither index map: the reduced-lattice boundary "
            "condition is NOT confirmed by the circuits; treat the comparison as unanchored.")
        return False
    return True


def trotter_vs_exact(Lx: int, Ly: int, theta: float, steps, log) -> None:
    """Brief option 2: how far the Trotter CIRCUIT (the device's target) is from exact H dynamics."""
    from src.compare import simulate_z2
    c = CONFIG.compare
    n = Lx * Ly
    check_ceiling(n, CONFIG.ceilings.statevector_max_spins)
    circ = simulate_z2(Lx, Ly, c.boundary, c.J, c.h, c.dt, theta, steps, CONFIG.ceilings.statevector_max_spins)
    H = tfim_hamiltonian(n, square_bonds(Lx, Ly, c.boundary), c.J, c.h).tocsc()
    psi0 = ry_product_state(n, theta, CONFIG.ceilings.statevector_max_spins)
    exact = np.array([total_z_sq_normalized(sla.expm_multiply(-1j * c.dt * s * H, psi0), n) for s in steps])
    log(f"  internal check {Lx}x{Ly}: max |Z2_Trotter-circuit - Z2_exact-H| over dataset steps = "
        f"{np.abs(circ - exact).max():.4f}  (the circuit, not continuous H, is what H2 ran)")


def main(argv=None) -> bool:
    """Run the comparison; returns True iff data/q1_compare.txt was written."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=CONFIG.compare.data_path)
    args = ap.parse_args(argv)
    c = CONFIG.compare
    data = ZenodoData(args.data)          # clear error if missing
    # Positive check, not just a synthetic blacklist: data/ is written only for a source that
    # carries the dataset README and whose published circuits verified for every quench.
    synthetic, trusted = source_status(args.data)
    out = []

    tag = "[SYNTHETIC FIXTURE] " if synthetic else ("" if trusted else "[UNVERIFIED SOURCE] ")

    def log(s=""):
        for part in s.split("\n"):
            line = tag + part
            print(line, flush=True)
            out.append(line)

    log(f"# Q1 Z2 comparison — generated {time.strftime('%Y-%m-%d %H:%M')} by scripts/run_compare.py")
    log(f"# data: {os.path.abspath(args.data)}")
    log(f"# sim: H = -J sum ZZ - h sum X, J={c.J}, h={c.h}, dt={c.dt} (J*dt={c.J * c.dt}, h*dt={c.h * c.dt}), "
        f"circuit-order Strang step, ry(theta) prep, boundary={c.boundary}, sizes={list(c.sizes)}")
    log("# " + CAVEAT)
    log("# Z2 = <(sum Z)^2>/N^2 (second moment). 'pair-avg' = (N Z2 - 1)/(N - 1) = mean_{i!=j}<ZiZj>, "
        "applied to both sides to remove the 1/N self-term that differs between N=56 and the reduced N.")
    log("# H2 error bars: dataset bootstrap '_err' (1-sigma vs CI not stated in README: [unverified]).")
    for q in c.quenches:
        theta = c.theta[q]
        log(f"\n## quench{q}: theta = {theta:+.6f} rad ({np.degrees(theta):+.1f} deg)")
        trusted = verify_circuits(args.data, q, theta, log) and trusted
        cmp = compare_z2(data, q, theta, c.sizes, c.boundary, c.J, c.h, c.dt,
                         CONFIG.ceilings.statevector_max_spins, c.modes, c.n_data)
        for line in cmp.provenance():
            log("  estimator/shots — " + line)
        for line in cmp.table():
            log("  " + line)
        a, b = c.sizes[0], c.sizes[-1]
        spread = np.abs(cmp.sim[a] - cmp.sim[b]).max()
        log(f"  finite-size spread max|Z2({a[0]}x{a[1]}) - Z2({b[0]}x{b[1]})| = {spread:.4f}")
        trotter_vs_exact(*c.sizes[0], theta, cmp.steps, log)

    if not trusted:
        print("NOT written to data/: source is synthetic, lacks the dataset README, or its circuits "
              "were not verified. Output above is for inspection only.", file=sys.stderr)
        return False
    out_dir = os.path.join(REPO, CONFIG.data_dir)   # repo-relative, whatever the cwd
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "q1_compare.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    return True


if __name__ == "__main__":
    main()
