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
   `zne+znr` and `raw_unamplified` curves, with the H2 bootstrap error bars. Each `Series`
   carries an estimator class and optional shot / accepted-shot counts, so a post-selected
   logical arm can be held and labelled next to mitigated physical data (no such arm exists
   yet; nothing here produces logical data).

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

# Estimator classes a Series can carry. Values from different classes are not like-for-like:
# a post-selected logical arm (accepted shots only) vs ZNE+ZNR-mitigated physical data must be
# labelled as such in any comparison (review R-Main-5).
ESTIMATORS = ("raw", "znr", "zne", "zne+znr", "postselected")
ESTIMATOR_OF_MODE = {
    "raw_unamplified": "raw", "raw_amplified": "raw",     # amplified = raw at boosted noise
    "znr_unamplified": "znr", "znr_amplified": "znr",
    "zne": "zne", "zne+znr": "zne+znr",
}


# --------------------------------------------------------------------------- #
# 1. Loader
# --------------------------------------------------------------------------- #
@dataclass
class Series:
    """One observable/mode: values with the step index (and r for dimercorrs).

    Optional provenance (all default to "unknown", so existing constructions are unchanged):
    `shots` executed and `accepted_shots` kept (scalar or per-step array; a post-selected
    logical arm keeps fewer than it runs), and `estimator` in ESTIMATORS. If `estimator` is
    None it is derived from a dataset `mode`; it stays None for an unrecognised mode.
    The released H2 dataset does not state shot counts, so loaded Series have shots=None.
    """

    quench: int
    observable: str
    mode: str
    steps: np.ndarray            # integer Trotter step indices (row key)
    values: np.ndarray
    err: Optional[np.ndarray]    # bootstrap error bar, same shape, or None if absent
    rs: Optional[np.ndarray] = None   # dimercorrs only; values are [r, step]
    shots: Optional[np.ndarray] = None            # shots executed (scalar or per step)
    accepted_shots: Optional[np.ndarray] = None   # shots kept after post-selection
    estimator: Optional[str] = None               # one of ESTIMATORS

    def __post_init__(self):
        if self.estimator is None:
            self.estimator = ESTIMATOR_OF_MODE.get(self.mode)
        elif self.estimator not in ESTIMATORS:
            raise ValueError(f"unknown estimator {self.estimator!r}; expected one of {ESTIMATORS}")
        for name in ("shots", "accepted_shots"):
            v = getattr(self, name)
            if v is not None and np.any(np.asarray(v) < 0):
                raise ValueError(f"{name} must be >= 0")
        if self.accepted_shots is not None:
            if self.shots is None:
                raise ValueError("accepted_shots given without shots: acceptance would be undefined")
            if np.any(np.asarray(self.accepted_shots) > np.asarray(self.shots)):
                raise ValueError("accepted_shots exceeds shots")
        if self.estimator == "postselected" and self.shots is not None and self.accepted_shots is None:
            raise ValueError("a post-selected Series needs accepted_shots (its error bars use them)")

    @property
    def effective_shots(self) -> Optional[np.ndarray]:
        """Shots that actually enter the estimator: accepted shots if post-selected, else
        all shots; None if the source does not state them. Use this, never `shots`, for
        shot-noise error bars."""
        if self.accepted_shots is not None:
            return np.asarray(self.accepted_shots)
        return None if self.shots is None else np.asarray(self.shots)

    @property
    def acceptance(self) -> Optional[np.ndarray]:
        """accepted_shots / shots, or None if either is not stated."""
        if self.accepted_shots is None or self.shots is None:
            return None
        return np.asarray(self.accepted_shots) / np.asarray(self.shots)

    def stderr_from_shot_std(self, shot_std) -> np.ndarray:
        """Standard error of a per-shot sample mean, std / sqrt(effective_shots).
        Raises if the effective shot count is unknown or zero (no error bar is invented)."""
        n = self.effective_shots
        if n is None:
            raise ValueError(f"{self.mode}: shot count not stated; cannot form a shot-noise error bar")
        if np.any(n <= 0):
            raise ValueError(f"{self.mode}: zero effective shots (nothing accepted)")
        return np.asarray(shot_std) / np.sqrt(n)

    def provenance(self) -> str:
        """One-line estimator/shot summary for logs and tables."""
        def fmt(v):
            if v is None:
                return "not stated"
            a = np.asarray(v)
            return f"{int(a)}" if a.ndim == 0 else f"{int(a.min())}..{int(a.max())} (per step)"
        acc = self.acceptance
        acc_s = "n/a" if acc is None else (f"{float(acc):.4f}" if np.ndim(acc) == 0
                                           else f"{acc.min():.4f}..{acc.max():.4f}")
        return (f"{self.mode}: estimator={self.estimator or 'unknown'}, shots={fmt(self.shots)}, "
                f"accepted={fmt(self.accepted_shots)}, acceptance={acc_s}, "
                f"effective shots={fmt(self.effective_shots)}")


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


def _uniform_sign(vals, mag_ok, tol) -> Tuple[Optional[int], List[str]]:
    """Common sign of `vals` (+1/-1, or 0 if every |v| is ~0) plus any problems found."""
    probs = []
    if len(vals) == 0:
        return None, ["no gates"]
    bad = [v for v in vals if not mag_ok(abs(v))]
    if bad:
        probs.append(f"|angle| off target: {sorted({round(v, 6) for v in bad})}")
    signs = {int(np.sign(v)) if abs(v) > tol else 0 for v in vals}
    if len(signs) > 1:
        probs.append(f"mixed signs {sorted({round(v, 6) for v in vals})}")
        return None, probs
    return signs.pop(), probs


def gauge_check_angles(rzz, rx, ry, J: float, h: float, dt: float, theta: float,
                       tol: float = 1e-6, theta_tol: float = 1e-4) -> Tuple[Optional[str], List[str]]:
    """Check signed circuit angles against (J, h, theta), allowing ONLY gauge-equivalent signs.

    A circuit with rzz(a) = exp(-i a/2 ZZ) on every bond, rx(b) half-layers = exp(-i b/2 X)
    (or merged interior rx(2b)) and ry(c) prep is, in our H = -J sum ZZ - h sum X, the literal
    point (J', h', theta') = (-a/(2dt), -b/dt, c) [derived; see module docstring and the
    gate-replay test]. It reproduces our run iff (J', h', theta') is in the gauge orbit
        {(J,h,th), (-J,-h,th), (J,-h,-th), (-J,h,-th)}
    (README identities (J,h,th)->(-J,-h,th), (J,h,th)->(J,-h,-th) and their composition).
    Every gate of a type must share one sign (a mixed-sign rzz layer is a different model,
    not a gauge). Magnitudes: |a| = 2|J|dt, |b| in {|h|dt, 2|h|dt}, |c| = |theta|.

    Returns (label, problems): label names the matched orbit element, e.g. "(-J,-h,theta)";
    problems is empty iff the circuit matches.
    """
    problems = []
    sa, p = _uniform_sign(rzz, lambda m: abs(m - 2 * abs(J) * dt) < tol, tol)
    problems += [f"rzz: {x}" for x in p]
    sb, p = _uniform_sign(rx, lambda m: min(abs(m - abs(h) * dt), abs(m - 2 * abs(h) * dt)) < tol, tol)
    problems += [f"rx: {x}" for x in p]
    sc, p = _uniform_sign(ry, lambda m: abs(m - abs(theta)) < theta_tol, theta_tol)
    problems += [f"ry: {x}" for x in p]
    if problems or None in (sa, sb, sc):
        return None, problems or ["sign undetermined"]
    # literal-point signs relative to (J, h, theta); a zero target leaves its sign free
    rel = []
    for s_lit, ref in ((-sa, J), (-sb, h), (sc, theta)):
        rel.append(0 if (s_lit == 0 or ref == 0) else int(s_lit * np.sign(ref)))
    orbit = {(1, 1, 1): "(J,h,theta)", (-1, -1, 1): "(-J,-h,theta)",
             (1, -1, -1): "(J,-h,-theta)", (-1, 1, -1): "(-J,h,-theta)"}
    for key, label in orbit.items():
        if all(r == 0 or r == k for r, k in zip(rel, key)):
            return label, []
    return None, [f"sign pattern (J',h',theta') = {tuple(('+' if r > 0 else '-') + n for r, n in zip(rel, ('J', 'h', 'theta')))} "
                  "is NOT gauge-equivalent to (J,h,theta)"]


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


def light_cone_z2_step1(Lx: int, Ly: int, boundary: str, J: float, h: float, dt: float,
                        theta: float, max_spins: int) -> float:
    """EXACT Z2 after ONE circuit-order Strang step at any lattice size, via the light cone.

    [derived] For a product initial state, <Z_i Z_j> after rx-half . rzz . rx-half depends only
    on sites S = {i, j} and their bond neighbours, and only on bonds touching i or j (all other
    gates cancel in U^dag Z_i Z_j U). So each pair is a <= 10-site simulation. Checked in tests
    against simulate_z2 on reduced tori; this is how the N = 56 step-1 value is obtained.
    Each cluster is guarded by check_ceiling (the full lattice is never allocated).
    """
    n = Lx * Ly
    bonds = square_bonds(Lx, Ly, boundary)
    total = float(n)                                    # diagonal Z_i^2 = 1
    for i in range(n):
        for j in range(i + 1, n):
            bb = [b for b in bonds if i in b or j in b]
            sites = sorted({i, j} | {q for b in bb for q in b})
            idx = {q: k for k, q in enumerate(sites)}
            local = [(idx[a], idx[b]) for a, b in bb]
            _, psi = next(circuit_trotter_states(len(sites), local, J, h, dt, theta, [1], max_spins))
            zz = ising_diagonal(len(sites), [(idx[i], idx[j])], -1.0)   # diag of Z_i Z_j
            total += 2.0 * float(np.real(np.vdot(psi, zz * psi)))
    return total / n ** 2


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

    def provenance(self) -> List[str]:
        """Estimator class and shot counts of every reference column. The ± in table() are
        the series' own `err`; a column built from shots (e.g. a post-selected logical arm)
        must have taken its err from Series.stderr_from_shot_std, i.e. from ACCEPTED shots."""
        return [ser.provenance() for ser in self.h2.values()]


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
