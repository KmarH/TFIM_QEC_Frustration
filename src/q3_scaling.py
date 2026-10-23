"""Q3 generalization study: Stim first-order rate table, survival curve and the (N, h, lam)
prefilter grid (research-flow decision cards D1-D5, 2026-10-22).

Purpose. The Iceberg-vs-Gauss-law result of docs/q3_thermalization.md §9.2 rests on a single
cell (N = 12 logical sites, h = 0.3, noise scale lam = 1). This module is the CHEAP stage of
its generalization: Stim first-order fault accounting, which needs no state vector and so runs
at any N (Stim is unbounded, SCOPE §5). It says which (N, h, lam) cells keep a usable Iceberg
post-selection survival, so the expensive exact-circuit stage (src/noisy_q3_sweep.py) is only
spent where it can resolve anything.

EVERY number produced here is a CLASSICAL PREDICTION under the ASSUMED research/06 H2 prior
(first-order fault accounting), NEVER an H2 / hardware result.

Reuse only: the rates come from src/noisy_q3.size_row and src/encoded_codes.detected_total, and
the lam axis from src/noise_scaling._scaled_stim. No fault-counting logic is reimplemented here.

The h axis. Stim treats Pauli rotations as the identity (exact for Pauli-fault propagation,
CLAUDE.md), so the per-step rates do NOT depend on h. h enters only through WHICH step count
matters: `survival`/`keep` are reported at the fixed reference window qdm_times / dt (the window
the existing N = 12 Iceberg baseline actually used, t = 12), and `survival_physics` /
`physics_steps` additionally report the h-dependent physics window qdm_times / h, which is the
window Q3BaselineConfig defines and where the Iceberg arm never survived even at h = 0.3.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

import src.encoded_codes as ec
from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates, detected_total
from src.mcmc_baseline import initial_spins
from src.noise_scaling import _scaled_stim
from src.noisy_q3 import TriangularBareTFIM, make_iceberg, size_row

# D1 (2026-10-22): the logical sizes of the study, each mapped to an ALREADY VALIDATED
# (Lx, Ly, initial state) of Q3BaselineConfig (exact_cases / curve_cases / size_stim_cases /
# mcmc_only_cases). No new lattice or initial-state design. Iceberg needs an even number of
# logical qubits, so every size here is even.
SIZE_TO_CASE: dict[int, tuple[int, int, str]] = {
    12: (3, 4, "flippable"),        # the existing baseline cell (data/q3_noisy.txt)
    18: (3, 6, "3-sublattice"),     # new Iceberg size point (22 physical, fits the 24 ceiling)
    20: (4, 5, "flippable"),        # new Iceberg size point (24 physical, AT the ceiling)
    36: (6, 6, "3-sublattice"),     # Stim-only (beyond the state-vector ceiling)
    54: (9, 6, "3-sublattice"),     # Stim-only, the reference Sec. V lattice size
}

# The three lam scopes of research/derivations/01-noise-scaling-arm.md "(c) Survival at 6x6".
# "all" scales every noise class present (that table's "all gates" row); the others are the
# narrower rows, kept because the derivation defines them.
_NAMED_SCOPES: dict[str, tuple[str, ...] | None] = {
    "all": None,                              # resolved per program: every tag class present
    "2q": ("rot-zz", "syn-cx"),               # "all 2Q (incl. syndrome CX)"
    "logical-zz": ("rot-zz",),                # "logical ZZ only"
}

# Step counts at which the prep offset is solved for. detected_total(steps) is exactly affine in
# steps [measured, 2026-10-22], so two points determine it; these are small enough to stay cheap
# at N = 54 and inside the range where the affine form was checked.
_OFFSET_STEPS = (8, 16)

_RATE_CACHE: dict[tuple, StimRates] = {}


@dataclass(frozen=True)
class StimRates:
    """First-order per-Trotter-step fault probabilities [derived accounting, ASSUMED noise].

    `iceberg_detect_prep_offset` is the step-INDEPENDENT part of the Iceberg detection
    probability (state preparation and final readout; src/encoded_codes.detected_total is
    documented "prep included"). Iceberg survival is
    exp(-(iceberg_detect_prep_offset + iceberg_detect_per_step * steps)); the bare and
    undetected rates are plain per-step rates with no offset.
    """

    bare_fault_per_step: float
    iceberg_detect_per_step: float
    iceberg_undetected_per_step: float
    iceberg_detect_prep_offset: float = 0.0


@dataclass
class GridCell:
    """One (N, h, lam) cell of the prefilter.

    `survival` / `keep` are at the fixed reference window (`steps` = qdm_times / dt);
    `survival_physics` / `physics_steps` are at the h-dependent Q3 physics window
    (qdm_times / h), reported for information — see the module docstring on the h axis.
    """

    N: int
    h: float
    lam: float
    survival: float
    keep: bool
    steps: int = 0
    physics_steps: int = 0
    survival_physics: float = float("nan")
    rates: StimRates | None = field(default=None, repr=False)


def _case_for(n_logical: int) -> tuple[int, int, str]:
    if n_logical % 2:
        raise ValueError(f"Iceberg needs an even number of logical qubits, got N={n_logical}")
    try:
        return SIZE_TO_CASE[n_logical]
    except KeyError:
        raise ValueError(
            f"no validated (Lx, Ly, start) for N={n_logical}; D1 fixed "
            f"{sorted(SIZE_TO_CASE)}. Add one to SIZE_TO_CASE only with the project lead's "
            "decision (it is a new lattice/initial-state choice)."
        ) from None


def _noise_key(noise: NoiseRates) -> tuple:
    return (noise.p2, noise.p1, noise.pm, noise.p_init, noise.zz_bias,
            getattr(noise, "overrot", 0.0), getattr(noise, "p_idle", 0.0))


def _tag_classes(progs: Sequence, noise: NoiseRates) -> tuple[str, ...]:
    """Every noise tag class present in the programs' unscaled Stim images (tags are
    'cls:item:cmd', src/encoded_codes.to_stim).

    The union over BOTH arms is required: the bare program carries 1q classes the encoded one
    does not ('rot1q-1q', 'rotx-1q' vs 'rot-1q', 'syn-1q') [measured], so resolving "all" from
    the Iceberg program alone would leave the bare arm's 1q noise at lam = 1 and silently
    reproduce the narrower "all 2Q" row of research/derivations/01 instead of "all gates".
    """
    seen = set()
    for prog in progs:
        for basis in ("Z", "X"):
            for ins in ec.to_stim(prog.schedule(1, basis), noise).flattened():
                if ins.tag:
                    seen.add(ins.tag.split(":")[0])
    return tuple(sorted(seen))


def _resolve_scope(scope: str | Sequence[str], progs: Sequence, noise: NoiseRates) -> tuple[str, ...]:
    if isinstance(scope, str):
        if scope not in _NAMED_SCOPES:
            raise ValueError(f"unknown scope {scope!r}; known: {sorted(_NAMED_SCOPES)}")
        named = _NAMED_SCOPES[scope]
        return _tag_classes(progs, noise) if named is None else named
    return tuple(scope)


def _prep_offset(prog, noise: NoiseRates, detect_per_step: float) -> float:
    """Step-independent part of detected_total, solved from its affine form at _OFFSET_STEPS.

    Raises if the two step counts disagree beyond first-order round-off, rather than silently
    averaging away a nonlinearity.
    """
    offsets = [detected_total(prog, noise, n) - detect_per_step * n for n in _OFFSET_STEPS]
    spread = max(offsets) - min(offsets)
    scale = max(abs(o) for o in offsets) or 1.0
    if spread > 1e-6 * max(scale, 1.0) + 1e-12:
        raise AssertionError(
            f"detected_total is not affine in steps at {_OFFSET_STEPS}: offsets {offsets} "
            f"(spread {spread:.3e}); the survival formula assumes offset + rate*steps"
        )
    return float(sum(offsets) / len(offsets))


def stim_rate_table(n_logical: int, lam: float, noise: NoiseRates, *,
                    scope: str | Sequence[str] = "all") -> StimRates:
    """First-order per-step rates of the bare and Iceberg triangular Q3 programs at N logical
    sites and noise scale `lam` [derived accounting, ASSUMED noise; NOT an H2 result].

    `lam` multiplies the probabilities of the noise classes in `scope` (Pauli insertion /
    folding to first order, src/noise_scaling._scaled_stim). h-independent: Stim treats Pauli
    rotations as the identity.
    """
    if lam < 1:
        raise ValueError(f"lam must be >= 1, got {lam}")
    Lx, Ly, kind = _case_for(n_logical)
    key = (n_logical, float(lam), str(scope), _noise_key(noise))
    if key in _RATE_CACHE:
        return _RATE_CACHE[key]

    q3 = CONFIG.q3
    d = TriangularDimers(Lx, Ly)
    s0 = initial_spins(d, kind, CONFIG.ceilings.ed_max_spins)
    prog = make_iceberg(d, s0, q3.J, q3.noisy_h, q3.dt)
    bare_prog = TriangularBareTFIM(Lx, Ly, "periodic", q3.J, q3.noisy_h, q3.dt, 0.0)
    classes = _resolve_scope(scope, (prog, bare_prog), noise)

    def _rates() -> StimRates:
        row = size_row(Lx, Ly, s0, J=q3.J, h=q3.noisy_h, dt=q3.dt, noise=noise)
        offset = _prep_offset(prog, noise, row.ice_detected)
        return StimRates(float(row.bare_unprotected), float(row.ice_detected),
                         float(row.ice_undetected), offset)

    if lam == 1:
        out = _rates()
    else:
        with _scaled_stim(lam, classes):
            out = _rates()
    _RATE_CACHE[key] = out
    return out


def survival_curve(rates: StimRates, steps) -> np.ndarray:
    """Iceberg detector survival (post-selection acceptance) after `steps` Trotter steps:
    exp(-(prep offset + detect rate * steps)) [derived accounting, first order]."""
    s = np.asarray(steps, dtype=float)
    return np.exp(-(rates.iceberg_detect_prep_offset + rates.iceberg_detect_per_step * s))


def prefilter_grid(sizes: Sequence[int], lams: Sequence[float], hs: Sequence[float],
                   noise: NoiseRates, qdm_times: float, dt: float,
                   survival_floor: float = 0.05) -> list[GridCell]:
    """Cross (sizes x lams x hs) and report the Iceberg survival of every cell.

    `survival` / `keep` are at the fixed reference window qdm_times / dt steps; a cell is kept
    when its survival is at or above `survival_floor`, i.e. when the expensive exact-circuit
    stage could still resolve the encoded arm there. `survival_physics` additionally reports the
    h-dependent Q3 physics window (qdm_times / h). Cheap: Stim only, no state vector.
    """
    ref_steps = round(qdm_times / dt)
    cells: list[GridCell] = []
    for n in sizes:
        for lam in lams:
            rates = stim_rate_table(n, lam, noise)
            ref = float(survival_curve(rates, np.array([ref_steps]))[0])
            for h in hs:
                phys_steps = round((qdm_times / h) / dt)
                phys = float(survival_curve(rates, np.array([phys_steps]))[0])
                cells.append(GridCell(N=int(n), h=float(h), lam=lam, survival=ref,
                                      keep=bool(ref >= survival_floor), steps=ref_steps,
                                      physics_steps=phys_steps, survival_physics=phys,
                                      rates=rates))
    return cells


def window_steps(total_time: float, dt: float) -> int:
    """Trotter steps of a physical time window (units of 1/|J|)."""
    return round(total_time / dt)


def faults_per_window(rates: StimRates, steps: int) -> float:
    """Expected bare faults over a window [derived accounting]: rate * steps."""
    return rates.bare_fault_per_step * steps


def time_to_survival(rates: StimRates, level: float, dt: float) -> float:
    """Physical time (units of 1/|J|) at which Iceberg survival falls to `level`, prep offset
    included. inf when the offset alone is already below the level at zero steps."""
    if not 0 < level <= 1:
        raise ValueError(f"level must be in (0, 1], got {level}")
    budget = -math.log(level) - rates.iceberg_detect_prep_offset
    if budget <= 0:
        return 0.0
    return dt * budget / rates.iceberg_detect_per_step
