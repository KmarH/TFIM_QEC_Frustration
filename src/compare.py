"""Q1 comparison harness: H2 reference data (arXiv:2503.20870) vs this repo's simulation.

Spec: research/05-zenodo-dataset-map.md (frozen) and handoff/03. Three parts:

1. `ZenodoData` — loads the published `.txt` files from a configurable local path
   (the unzipped `zenodo_data/`; never committed). Rows are keyed by
   `quenchN_steps.txt` (non-uniform, M = 12/20/10/8), never assumed to be 20.
   `dimercorrs` is stored [r, step] (transpose of the README's generic M x L rule) and
   is returned in that orientation after a shape check against rs/steps.

2. `simulate_z2` — reduced-lattice statevector simulation at the dataset's
   dimensionless parameters. Gate order follows the QASM circuits (research/05 §3):
   per step rx half-layer -> rzz layer -> rx half-layer, i.e.
       U_step = exp(-i B dt/2) exp(-i A dt) exp(-i B dt/2),  A = -J sum ZZ, B = -h sum X,
   preceded once by ry(theta) on every site. (src/trotter.py's step puts A outside;
   that is a different 2nd-order splitting, so it is NOT reused here and is left
   untouched.) Sign mapping [derived, checked in tests by a literal gate-level replay]:
   rzz(phi)=exp(-i phi/2 ZZ), rx(phi)=exp(-i phi/2 X) with rzz(0.5), rx(0.5) means
   H_circ = +J_c ZZ + h_c X, J_c dt = 0.25, h_c dt = 0.5, i.e. our (J, h) = (-1, -2) at
   dt = 0.25. The README gauge identity (J,h,theta) -> (-J,-h,theta) maps this to
   (J, h) = (+1, +2) with the SAME theta, which is what config uses.

3. `compare_z2` — table of simulated Z2 at the dataset's step indices against the H2
   `zne+znr` and `raw_unamplified` curves, with the H2 bootstrap error bars.

HONESTY CONSTRAINT (handoff/03, SCOPE §12): the H2 square data is N = 56; exact
simulation here is capped at CeilingConfig.statevector_max_spins (24). The comparison
is a REDUCED-LATTICE, matched-dimensionless-parameter TREND comparison. It is never a
same-system fidelity number, and every output says so. Over-ceiling sizes are refused
before any allocation.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.backends import MemoryCeilingError
from src.lattice import square_bonds
from src.observables import total_z_sq_normalized
from src.trotter import apply_x_rotations, ising_diagonal

MODES = ("raw_unamplified", "raw_amplified", "znr_unamplified", "znr_amplified", "zne", "zne+znr")


# --------------------------------------------------------------------------- #
# 1. Loader
# --------------------------------------------------------------------------- #
@dataclass
class Series:
    """One observable/mode: values with the step index (and r for dimercorrs)."""

    quench: int
    observable: str
    mode: str
    steps: np.ndarray            # integer Trotter step indices (row key)
    values: np.ndarray
    err: Optional[np.ndarray]    # bootstrap error bar, same shape, or None if absent
    rs: Optional[np.ndarray] = None   # dimercorrs only; values are [r, step]


class ZenodoData:
    """Reader for the unzipped `zenodo_data/` directory of DOI 10.5281/zenodo.18487089."""

    def __init__(self, root: str):
        if not root or not os.path.isdir(root):
            raise FileNotFoundError(
                f"zenodo_data directory not found: {root!r}. Set CompareConfig.data_path "
                "(or env TFIM_ZENODO_DATA) to the unzipped dataset; it is not in the repo."
            )
        self.root = root

    def _path(self, name: str) -> str:
        return os.path.join(self.root, name)

    def _load(self, name: str) -> np.ndarray:
        p = self._path(name)
        if not os.path.isfile(p):
            raise FileNotFoundError(f"dataset file missing: {name}")
        return np.loadtxt(p, ndmin=1)

    def steps(self, quench: int) -> np.ndarray:
        s = self._load(f"quench{quench}_steps.txt")
        steps = np.rint(s).astype(int)
        if not np.allclose(s, steps):
            raise ValueError(f"quench{quench}_steps.txt holds non-integer step indices")
        return steps

    def rs(self) -> np.ndarray:
        return np.rint(self._load("quench4_rs.txt")).astype(int)

    def _err_name(self, stem: str, mode: str) -> Optional[str]:
        # research/05 describes the sibling as "X_err"; the MODE suffix comes last in every
        # value file, so the expected name is <stem>_err_<mode>.txt [inferred]. The other
        # placement is accepted too; if neither exists, load() raises (require_err).
        for name in (f"{stem}_err_{mode}.txt", f"{stem}_{mode}_err.txt"):
            if os.path.isfile(self._path(name)):
                return name
        return None

    def load(self, quench: int, observable: str, mode: str,
             initstate: Optional[str] = None, require_err: bool = True) -> Series:
        """Load (quench, observable, mode[, initstate]) with its error bar and step index.

        observable in {"Z2", "ZZnn", "ZZnn_fft", "ZZnn_fft_decayrates", "dimercorrs"};
        initstate in {"min_winding", "max_winding"} for quench 4 only.
        """
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
        if (quench == 4) != (initstate is not None):
            raise ValueError("initstate is required for quench 4 and only for quench 4")
        stem = f"quench{quench}_" + (f"{initstate}_" if initstate else "") + observable
        values = self._load(f"{stem}_{mode}.txt")
        err_name = self._err_name(stem, mode)
        if err_name is None and require_err:
            # research/05: every X has an X_err; quench4 only for raw_*/zne (which are also
            # the only quench4 dimercorr modes), so an absent error bar is always a surprise.
            raise FileNotFoundError(
                f"no error-bar file for {stem}_{mode} (tried {stem}_err_{mode}.txt and "
                f"{stem}_{mode}_err.txt); pass require_err=False only if that is intended")
        err = self._load(err_name) if err_name else None
        steps = self.steps(quench)
        M = len(steps)
        rs = None

        if observable == "ZZnn_fft_decayrates":
            values = values.reshape(-1)            # indexed by q mode, not by step
        elif observable == "dimercorrs":
            rs = self.rs()
            values = np.atleast_2d(values)
            if values.shape != (len(rs), M):       # [r, step], NOT the generic M x L rule
                raise ValueError(f"{stem}: shape {values.shape}, expected [r, step] = {(len(rs), M)}")
        elif observable == "Z2":
            values = values.reshape(-1)
            if values.shape != (M,):
                raise ValueError(f"{stem}: {values.shape[0]} rows but {M} steps in quench{quench}_steps.txt")
        else:                                      # ZZnn, ZZnn_fft: M x L
            values = np.atleast_2d(values)
            if values.shape[0] != M:
                raise ValueError(f"{stem}: {values.shape[0]} rows but {M} steps")
        if err is not None:                         # same layout rules as values, no reshaping
            err = err.reshape(-1) if values.ndim == 1 else np.atleast_2d(err)
            if err.shape != values.shape:
                raise ValueError(f"{err_name}: shape {err.shape} != values shape {values.shape}")
        return Series(quench, observable, mode, steps, values, err, rs)


# --------------------------------------------------------------------------- #
# QASM reader (verifies geometry/angles against the published circuits)
# --------------------------------------------------------------------------- #
_GATE = re.compile(r"^\s*(rzz|rx|ry)\(([^)]*)\)\s+(.*?);")


_PI_FORM = re.compile(r"^(-?)\s*([0-9.eE+-]*)\s*\*?\s*pi\s*(?:/\s*([0-9.eE+-]+))?$")


def _angle(expr: str) -> float:
    """Parse a QASM angle: a plain number, or [-][c*]pi[/d] (no general expression evaluation)."""
    expr = expr.strip()
    try:
        return float(expr)
    except ValueError:
        pass
    m = _PI_FORM.match(expr)
    if not m:
        raise ValueError(f"unsupported QASM angle expression {expr!r}")
    sign = -1.0 if m.group(1) else 1.0
    coef = float(m.group(2)) if m.group(2) else 1.0
    den = float(m.group(3)) if m.group(3) else 1.0
    return sign * coef * np.pi / den


def read_qasm(path: str) -> Dict[str, list]:
    """Return {'rzz': [(a, b, angle)], 'rx': [(q, angle)], 'ry': [(q, angle)]} from a QASM file."""
    out: Dict[str, list] = {"rzz": [], "rx": [], "ry": []}
    arity = {"rzz": 2, "rx": 1, "ry": 1}
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            m = _GATE.match(line)
            if not m:
                if re.match(r"^\s*(rzz|rx|ry)\b", line):
                    raise ValueError(f"{path}:{lineno}: unparsed gate line {line.strip()!r}")
                continue
            gate, ang, args = m.group(1), _angle(m.group(2)), m.group(3)
            qs = [int(x) for x in re.findall(r"q\[(\d+)\]", args)]
            if len(qs) != arity[gate]:
                raise ValueError(f"{path}:{lineno}: {gate} expects {arity[gate]} indexed qubit(s), got {line.strip()!r}")
            out[gate].append((*qs, ang))
    return out


def qasm_step_bonds(path: str) -> List[Tuple[int, int]]:
    """Distinct rzz qubit pairs of one circuit file (the bond list actually executed)."""
    return sorted({(min(a, b), max(a, b)) for a, b, _ in read_qasm(path)["rzz"]})


# --------------------------------------------------------------------------- #
# 2. Reduced-lattice simulation
# --------------------------------------------------------------------------- #
def check_ceiling(n_sites: int, max_spins: int) -> None:
    """Refuse an exact statevector run above the SCOPE §5 ceiling BEFORE allocating."""
    if n_sites > max_spins:
        raise MemoryCeilingError(
            f"exact statevector run for {n_sites} spins refused: ceiling is {max_spins} "
            "(SCOPE §5). The 56-qubit H2 lattice cannot be simulated exactly here; use a "
            "reduced lattice and treat the result as a finite-size trend comparison."
        )


def ry_product_state(n_sites: int, theta: float, max_spins: int) -> np.ndarray:
    """ry(theta) on every qubit of |0...0>: (cos(theta/2), sin(theta/2)) per site, |0> = Z=+1.
    Refuses n_sites > max_spins before building the 2^N vector."""
    check_ceiling(n_sites, max_spins)
    single = np.array([np.cos(theta / 2), np.sin(theta / 2)], dtype=np.complex128)
    psi = np.ones(1, dtype=np.complex128)
    for _ in range(n_sites):
        psi = np.kron(psi, single)
    return psi


def circuit_trotter_states(
    n_sites: int, bonds, J: float, h: float, dt: float, theta: float,
    record_steps: Sequence[int], max_spins: int,
):
    """Yield (step, psi) for each requested step of the circuit-order Strang evolution."""
    check_ceiling(n_sites, max_spins)
    want = sorted(set(int(s) for s in record_steps))
    if want and want[0] < 0:
        raise ValueError("step indices must be >= 0")
    phase = np.exp(-1j * dt * ising_diagonal(n_sites, bonds, J))   # exp(-i A dt)
    half_x = -h * dt / 2                                           # exp(-i B dt/2) = exp(+i h dt/2 sum X)
    psi = ry_product_state(n_sites, theta, max_spins)
    step = 0
    for target in want:
        while step < target:
            psi = apply_x_rotations(psi, n_sites, theta=half_x)
            psi = phase * psi
            psi = apply_x_rotations(psi, n_sites, theta=half_x)
            step += 1
        yield step, psi.copy()    # apply_x_rotations works in place; never hand out a live buffer


def simulate_z2(Lx: int, Ly: int, boundary: str, J: float, h: float, dt: float,
                theta: float, steps: Sequence[int], max_spins: int) -> np.ndarray:
    """Z2(step) = <(sum Z)^2>/N^2 on an Lx x Ly square lattice at the given step indices."""
    n = Lx * Ly
    bonds = square_bonds(Lx, Ly, boundary)
    vals = {s: total_z_sq_normalized(psi, n)
            for s, psi in circuit_trotter_states(n, bonds, J, h, dt, theta, steps, max_spins)}
    return np.array([vals[int(s)] for s in steps])


def pair_average_from_z2(z2: np.ndarray, n: int) -> np.ndarray:
    """mean_{i != j} <Z_i Z_j> = (N Z2 - 1)/(N - 1). [derived] Z2 contains a trivial 1/N
    self-term (Z_i^2 = 1) that differs between N=56 and a reduced lattice; this removes ONLY
    that term. The pair correlations themselves still depend on size. Applied to both sides."""
    return (n * np.asarray(z2) - 1.0) / (n - 1.0)


# --------------------------------------------------------------------------- #
# 3. Comparison
# --------------------------------------------------------------------------- #
@dataclass
class Z2Comparison:
    quench: int
    theta: float
    steps: np.ndarray
    sim_sizes: List[Tuple[int, int]]
    sim: Dict[Tuple[int, int], np.ndarray]      # Z2 per reduced lattice
    h2: Dict[str, Series]                        # mode -> dataset series
    n_data: int
    dt: float = 0.25

    def table(self) -> List[str]:
        big = max(self.sim, key=lambda s: s[0] * s[1])
        lines = []
        hdr = f"{'step':>4} {'t|J|':>6} " + " ".join(
            f"{'sim Z2 ' + f'{a}x{b}':>14}" for a, b in self.sim_sizes)
        hdr += "  " + "  ".join(f"{'H2 ' + m:>26}" for m in self.h2)
        hdr += f"  {'pair-avg sim':>12}  " + "  ".join(f"{'pair-avg H2 ' + m:>26}" for m in self.h2)
        lines.append(hdr)
        nb = big[0] * big[1]
        for k, s in enumerate(self.steps):
            row = f"{s:>4d} {s * self.dt:>6.2f} " + " ".join(f"{self.sim[sz][k]:>14.4f}" for sz in self.sim_sizes)
            for m, ser in self.h2.items():
                e = ser.err[k] if ser.err is not None else np.nan
                row += f"  {ser.values[k]:>14.4f} ± {e:<9.4f}"
            row += f"  {pair_average_from_z2(self.sim[big][k], nb):>12.4f}  "
            for m, ser in self.h2.items():
                e = ser.err[k] * self.n_data / (self.n_data - 1) if ser.err is not None else np.nan
                row += f"  {pair_average_from_z2(ser.values[k], self.n_data):>14.4f} ± {e:<9.4f}"
            lines.append(row)
        return lines


def compare_z2(data: ZenodoData, quench: int, theta: float, sizes: Sequence[Tuple[int, int]],
               boundary: str, J: float, h: float, dt: float, max_spins: int,
               modes: Sequence[str] = ("zne+znr", "raw_unamplified"), n_data: int = 56) -> Z2Comparison:
    """Simulate Z2 at the dataset's step indices on each reduced lattice and pair with H2 data."""
    for (a, b) in sizes:                       # refuse the whole run up front
        check_ceiling(a * b, max_spins)
    steps = data.steps(quench)
    h2 = {m: data.load(quench, "Z2", m) for m in modes}
    sim = {(a, b): simulate_z2(a, b, boundary, J, h, dt, theta, steps, max_spins) for a, b in sizes}
    return Z2Comparison(quench, theta, steps, list(sizes), sim, h2, n_data, dt)


CAVEAT = (
    "CAVEAT [SCOPE §12]: H2 data is a 7x8 = 56-qubit lattice; the simulation is a REDUCED "
    "lattice (sizes listed) at the same J*dt=0.25, h*dt=0.5 (h/|J|=2) and initial ry(theta). "
    "This is a finite-size TREND comparison, NOT a same-system fidelity or logical-vs-physical "
    "number. The spread between the reduced sizes is reported, but it is NOT a bound on the "
    "gap to N=56; no simulation-side error bar is claimed."
)
