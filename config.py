"""Single source of truth for ALL settings (SCOPE §2, §5, §8).

Every tunable lives here. Backend switch defaults to local. Hardware is
double-gated: `allow_hardware=True` AND explicit per-run user approval are both
required before any Nexus/H2 path may run (SCOPE §5). Nothing here reaches out
to the network or hardware on import.

Status of values: lattice/Trotter/observable settings are [established] defaults
for Stage 1. Size ceilings are [inferred] proposals from SCOPE §5 and are NOT
frozen until qc-reviewer confirms an empirical memory probe at the chosen size.
"""

from __future__ import annotations

import math
import os

from dataclasses import dataclass, field
from typing import Literal


# --------------------------------------------------------------------------- #
# Backend selection
# --------------------------------------------------------------------------- #
# "statevector" : dense exact Trotter evolution (Stage 1 dynamics)
# "ed"          : sparse exact diagonalization / Lanczos (Stage 1 spectra)
# "stim"        : stabilizer sim for QEC gadget verification (Stage 2+)
# "nexus"       : Quantinuum H2 emulator/hardware — STUBBED, hardware-gated
Backend = Literal["statevector", "ed", "stim", "nexus"]


@dataclass
class HardwareConfig:
    """Hardware access is OFF by default and double-gated (SCOPE §5).

    Submitting a job requires BOTH allow_hardware=True here AND an explicit
    per-run user confirmation at call time. The Nexus path is only stubbed.
    """

    allow_hardware: bool = False
    device: str = "H2-emulator"  # stubbed target; no effect while gated off
    max_shots: int = 0
    # Hard HQC spending cap passed to the backend as `max_cost` on EVERY submission
    # (pytket-quantinuum enforces it server-side and ignores it for local emulators). 0 means
    # unset, and src/backends_qc.py REFUSES to submit while it is 0 -- there is deliberately no
    # "unlimited" value. Raise it consciously, per run, together with the approval token.
    max_cost_hqc: float = 0.0
    # H2 submission path (src/h2_backend.py, docs/nexus_toggle.md). Three tiers, by what they cost:
    #   LE  local emulator, offline, free        -> le_device
    #   SC  Nexus syntax checker, free, no HQC   -> syntax_checker (pre-approved by the project lead)
    #   E   Nexus H2 emulator, spends HQC        -> emulator_device (double-gated, per run)
    # Real H2 hardware is a fourth tier, refused unless allow_real_hardware is set as well.
    le_device: str = "H2-1LE"
    syntax_checker: str = "H2-1SC"
    emulator_device: str = "H2-1E"
    nexus_project: str = "tfim-qec-h2"  # Nexus project name (not a credential); the tier stays dry-run
    # Server-side optimisation OFF: the folded noise-scaling circuits are silently cancelled by
    # TKET at levels 1-2 (D-NS6), so every submission is compiled at level 0 and sent no_opt.
    no_opt: bool = True
    allow_real_hardware: bool = False
    # Run driver (src/h2_driver.py, scripts/run_h2_nexus.py). nexus_tier picks what the driver does:
    #   "dry-run"   build + compile + estimate offline; nothing leaves the machine (default)
    #   "sc"        free H2-1SC quote;  "hosted-le"  free Nexus-hosted noiseless H2-1LE
    #   "emulator"  H2-1E/2E, SPENDS HQC: needs allow_hardware=True, max_cost_hqc > 0, a nexus_project
    #               AND the per-run approval token on the command line (a config edit alone never spends).
    # To switch the emulator on: set nexus_tier="emulator", allow_hardware=True, max_cost_hqc=<cap>,
    # nexus_project="<name>" here, then pass --approval at run time (docs/nexus_toggle.md).
    nexus_tier: str = "dry-run"
    # Limits the driver enforces before any spend. [established, docs.quantinuum.com "H2 Operation",
    # Hardware Credit Limitations, read 2026-10-17] 50 HQC per shot and 10,000 shots per job on hardware;
    # the page does not say whether emulators share them, so they are applied conservatively.
    # [established, emulator pages] H2-1E/2E state vector is <= 32 qubits.
    emulator_max_qubits: int = 32
    max_shots_per_job: int = 10_000
    max_hqc_per_shot: float = 50.0


@dataclass
class LatticeConfig:
    """2D lattice geometry. Stage 1 = square, unencoded.

    Row-major site index: n = y * Lx + x, with 0 <= x < Lx, 0 <= y < Ly.
    boundary: "open" (OBC) or "periodic" (PBC). geometry: "square" (Stage 1) or
    "triangular" (Stage 3, frustrated — live; the reproduction target uses a
    triangular lattice with periodic BC, so set boundary="periodic" for it).
    """

    Lx: int = 3
    Ly: int = 3
    boundary: Literal["open", "periodic"] = "open"
    geometry: Literal["square", "triangular"] = "square"

    @property
    def n_sites(self) -> int:
        return self.Lx * self.Ly


@dataclass
class ModelConfig:
    """TFIM couplings for H = -J sum_<ij> Z_i Z_j - h sum_i X_i (SCOPE/HANDOFF).

    J > 0 ferromagnetic. h is the transverse field strength.
    """

    J: float = 1.0
    h: float = 1.0


@dataclass
class TrotterConfig:
    """Second-order Suzuki–Trotter evolution settings.

    total_time T split into n_steps steps of dt = T / n_steps. order fixed to 2
    for Stage 1 (SCOPE/HANDOFF). The symmetric step is
    U2(dt) = e^{-iA dt/2} e^{-iB dt} e^{-iA dt/2}, A = -J sum ZZ, B = -h sum X.
    """

    total_time: float = 1.0
    n_steps: int = 20
    order: Literal[2] = 2


@dataclass
class CeilingConfig:
    """Size ceilings (SCOPE §5), now PROBE-BACKED on this host (see
    data/stage1_validation.txt and review/01-stage1.md).

    Enforced as guard rails by the backends. The statevector state alone costs
    2^N * 16 bytes (complex128): N=24 -> 268 MB. Caveat (qc-reviewer M1,
    confirmed by probe): real peak RSS runs ~5.7x above that bare-state figure
    at N=24 (and higher at smaller N, where the interpreter baseline dominates:
    6.9x at N=22, 9.5x at N=20) because apply_x_rotations holds transient
    half-state copies — size the host against ~5.7 * 2^N * 16 bytes, not the
    state alone.

    Measured peaks on this host (~7.6 GB free, serial, ru_maxrss), as recorded
    in data/stage1_validation.txt [4] and [5]:
      statevector Trotter: N=22 -> 463 MB, N=24 -> 1543 MB (SAFE at 24).
      ED build+Lanczos:    N=20 -> 1881 MB (SAFE), N=22 -> 7971 MB (near-OOM edge).
    The N=22 ED figure (7971 MB) has no source in data/stage1_validation.txt, whose
    [5] table stops at N=20; it is an unverified earlier measurement. It sits above
    the enforced ed_max_spins=20 ceiling either way, so nothing depends on it.
    Honest caveat on the ED figures: ru_maxrss is a process-lifetime maximum, so
    the ED peaks reported at N=16 and N=18 (both 1543 MB) are the peak carried
    over from the statevector run earlier in the same process, NOT ED-specific
    measurements. Only the N=20 ED figure (1881 MB) exceeds that carried-over
    high-water mark and is therefore ED-specific.
    """

    # ED set to 20: build+Lanczos at N=20 peaks ~1.9 GB (safe). N=22 was measured
    # at ~8 GB maxRSS (144 s Lanczos) — at the memory edge on a 7.6 GB host, so it
    # is NOT frozen as a safe ceiling. The C1 OOM is fixed (builder is now sparse,
    # review/01-stage1.md C1); raising to 22 needs headroom this host lacks.
    ed_max_spins: int = 20           # probe-backed safe ceiling (N=22 is near-OOM)
    statevector_max_spins: int = 24  # probe-backed safe (N=24 peak ~1.5 GB)
    # Stim is unbounded (stabilizer) — no spin ceiling here.


@dataclass
class QECConfig:
    """Concatenated-Iceberg d=4 gadget settings (handoff/01, docs/concatenated_iceberg_d4.md).

    Code: inner Iceberg [[k_inner+2, k_inner, 2]] blocks carrying the qubits of
    k_inner outer Iceberg [[k_outer+2, k_outer, 2]] blocks -> [[n, k, 4]] with
    n = (k_outer+2)(k_inner+2), k = k_inner*k_outer. Default 2,2 -> [[16,4,4]].

    Noise model [illustrative, NOT H2-calibrated]: uniform circuit-level
    depolarizing. After every CX a DEPOLARIZE2(p); after every H a
    DEPOLARIZE1(p * p1_ratio); X_ERROR(p * pm_ratio) before every measurement and
    after every reset; DEPOLARIZE1(p * idle_ratio) on every data qubit once per
    stabilizer measurement block (inner-Z, inner-X, outer-Z, outer-X) per round.
    """

    k_inner: int = 2
    k_outer: int = 2
    rounds: int = 2
    use_flags: bool = True
    p1_ratio: float = 0.1
    pm_ratio: float = 1.0
    idle_ratio: float = 0.1
    # Physical error rates scanned for the discard-rate report (illustrative).
    p_scan: tuple = (1e-4, 3e-4, 1e-3, 3e-3)
    shots: int = 200_000


@dataclass
class GaussLawConfig:
    """Stage 3 dimer / Gauss-law study (handoff/02, docs/gauss_law_dimers.md).

    Frustrated model in OUR convention H = -J sum ZZ - h sum X needs J < 0 (AFM), matching
    arXiv:2503.20870 Sec. V's AFM sign choice.

    h = 0.3, dt = 0.25 here matches the reference's own triangular quench (arXiv:2503.20870
    Fig. 4(e) caption: "All data taken at (h/|J|, dt|J|)=(0.3, 0.25)"; §V body sets the regime
    as weak transverse field, 9x6 torus, also Methods §VII.1) [established]. It is also the
    weak-field point where the emergent-Gauss-law / dimer description below is a controlled
    (first-order in h/|J|) approximation, with sector leakage O((h/|J|)^2) and stable in-sector
    verdicts up to h = 0.3 (docs/gauss_law_dimers.md, docs/q3_thermalization.md) -- this
    corroborates the reference's own choice of regime rather than substituting for it. The
    reference's *released* quench4 circuit files instead carry the square quench's field angle
    (rx(0.5) where rx(0.0375) is expected) and an all-zero initial state; that is a defect in the
    data release, not a second value from the paper (research/05-zenodo-dataset-map.md). So:
    J = -1, h = 0.3, dt = 0.25 here.

    Noise model for the mitigation benchmark [assumption, not hardware-calibrated]:
    after every Trotter step, an independent single-qubit Pauli channel on every
    qubit with total probability p split as (px, py, pz) by `channels`.
    ZNE scales p by lambda (idealised, noise-shape-preserving amplification).
    """

    J: float = -1.0
    h: float = 0.3
    dt: float = 0.25
    h_scan: tuple = (0.025, 0.05, 0.1, 0.2, 0.3)
    # exact density-matrix benchmark cluster and trajectory cross-check cluster
    dm_Lx: int = 3
    dm_Ly: int = 3
    traj_Lx: int = 3
    traj_Ly: int = 4
    traj_n: int = 400
    n_steps: int = 40
    p_scan: tuple = (1e-3, 3e-3, 1e-2)
    channels: tuple = (
        ("depolarizing", (1 / 3, 1 / 3, 1 / 3)),
        ("dephasing", (0.0, 0.0, 1.0)),
        ("bitflip", (0.5, 0.5, 0.0)),
    )
    zne_lambdas: tuple = (1.0, 2.0, 3.0)
    shots: int = 10_000   # per-circuit budget used to convert variance into error bars


@dataclass
class CompareConfig:
    """Q1 harness vs the H2 dataset (handoff/03, research/05-zenodo-dataset-map.md).

    Parameters [established from the dataset QASM]: J*dt = 0.25, h*dt = 0.5 (h/|J| = 2).
    Convention chosen here: |J| = 1, dt = 0.25, h = 2, in our H = -J sum ZZ - h sum X with
    J = +1 (the circuits' (-1, -2) mapped by the README gauge identity (J,h,th)->(-J,-h,th);
    verified by a gate-level replay test). Initial state: ry(theta) on every site.
    Boundary: "periodic" [established 2026-10-07: the published quench1/2 QASM rzz pairs equal
    square_bonds(7, 8, "periodic") under row-major q = y*Lx + x; re-checked on every run]. Reduced sizes must stay <= ceilings.statevector_max_spins.
    """

    data_path: str = field(default_factory=lambda: os.environ.get("TFIM_ZENODO_DATA", ""))
    J: float = 1.0
    h: float = 2.0
    dt: float = 0.25
    theta: dict = field(default_factory=lambda: {1: math.pi / 6, 2: -math.radians(10.0)})
    quenches: tuple = (1, 2)
    sizes: tuple = ((4, 4), (4, 5))
    boundary: str = "periodic"
    modes: tuple = ("zne+znr", "raw_unamplified")
    n_data: int = 56   # qubits in the H2 square lattice (7x8)
    data_Lx: int = 7   # research/05: snapshot matrix rows x cols = Lx x Ly = 7 x 8
    data_Ly: int = 8


@dataclass
class EncodedConfig:
    """Iceberg-encoded square-TFIM run (handoff/04 Part A; src/encoded_tfim.py, src/backends_qc.py).

    Physics matches CompareConfig: J*dt = 0.25, h*dt = 0.5 (h/|J| = 2) in our convention
    (J, h) = (+1, +2), circuit-order Strang step, logical ry(theta) prep.
    Logical lattice: Lx x Ly periodic, k = Lx*Ly logical qubits (even) in ONE Iceberg block;
    physical register n_phys = k + 4 (code k+2, syndrome ancilla, flag); refused above
    ceilings.statevector_max_spins before allocation.

    Noise [ASSUMED generic depolarizing, NOT H2-calibrated]: p2 per 2-qubit gate (scanned);
    p1 = p2 * p1_ratio per 1-qubit gate; pm = p2 * pm_ratio per measurement; p_init = p2 *
    init_ratio per reset. p_idle is local-sim-only and 0 by default so the two executable
    backends see the same parameter set.
    """

    backend: str = "local-sim"            # "local-sim" | "selene" | "nexus" (stub)
    Lx: int = 2
    Ly: int = 3
    boundary: str = "periodic"
    J: float = 1.0
    h: float = 2.0
    dt: float = 0.25
    theta: float = math.pi / 6            # quench1 angle (research/05)
    syndrome_every: int = 1               # QED round after every Trotter step
    steps: tuple = (1, 2, 3, 4, 5, 6)
    p2_scan: tuple = (1e-3, 3e-3, 1e-2)
    p1_ratio: float = 0.1
    pm_ratio: float = 0.1
    init_ratio: float = 0.1
    p_idle: float = 0.0
    shots_local: int = 1000
    shots_selene: int = 1000
    # Clifford-angle instance for the Stim <-> pytket/Guppy consistency check (J dt = pi/4,
    # h dt = pi/2, theta = 0: Z2 alternates 1/k, 1 so the check is discriminating)
    clifford_J: float = math.pi
    clifford_h: float = 2 * math.pi
    clifford_theta: float = 0.0
    # Randomized compiling (Pauli twirling, DECISIONS.md OPEN-3, D-RC; src/twirl.py). A
    # HARDWARE-READINESS switch, OFF by default: this project's noise models are already Pauli
    # channels, so twirling has NO effect on any Pauli-noise prediction in this repo (it is
    # tested to be a no-op in tests/test_twirl.py) -- the point is to be able to emit
    # randomized-compiled circuits once the H2 emulator is switched on, without further circuit
    # work. rc_period documents the reference's cadence (2503.20870 applies RC every two
    # Trotter layers, CLAUDE.md); src/twirl.py twirls every ZZPhase gate regardless of how the
    # circuit is chunked into jobs, so rc_period is job-packaging granularity, not a change to
    # the induced distribution over twirled circuits.
    rc: bool = False
    rc_period: int = 2
    rc_instances: int = 20


@dataclass
class SensitivityConfig:
    """Noise-model sensitivity of the Part B conclusion (handoff/06; scripts/run_noise_sensitivity.py).

    Stim first-order accounting only (no execution), Lx x Ly logical lattice, physics from
    EncodedConfig. Every rate here is an ASSUMED input; every output is a classical prediction
    under that model, NOT an H2 result.

    H2 prior (research/06-h2-noise-prior.md §6) — a PRIOR, not a measurement:
      p2_prior     ~6e-4 per native 2q gate [inferred from published 2q infidelity, 2503.20870]
      p1 = pm = p_init = p2 * p1_ratio (p2/10) [inferred; mildly pessimistic on 1q, HW-4 open]
      zz_bias_prior 0.05, bracket (0.03, 0.08) [inferred, Fig. S3 read-off of 2503.20870]
      overrot_scan sin^2(eps) [assumed; 2q eps unpublished -> scanned, not fixed]
    Stress-test eta values are ~10x the H2 prior and NOT representative of H2 (kept from the
    original Part B sensitivity run for traceability). The legacy block reruns the original
    table at its original rates (p2 = 1e-3) so docs/encoded_tfim.md's first table stays traceable.
    """

    Lx: int = 2
    Ly: int = 2
    accept_steps: int = 3                       # first-order acceptance quoted after this many steps
    p1_ratio: float = 0.1                       # p1 = pm = p_init = p2 * p1_ratio
    p2_prior: float = 6e-4
    zz_bias_prior: float = 0.05
    zz_bias_bracket: tuple = (0.03, 0.08)
    overrot_scan: tuple = (0.0, 1e-5, 1e-4, 1e-3)
    zz_bias_stress: tuple = (0.5, 0.9)          # stress-test only, ~10x the H2 prior
    p2_legacy: float = 1e-3                     # original Part B sensitivity rates [assumed]
    p_idle_legacy: tuple = (1e-4, 1e-3)
    overrot_legacy: tuple = (1e-4, 1e-3)


@dataclass
class Q3BaselineConfig:
    """Q3 thermalization: sector-restricted MCMC ergodic baseline (handoff/07,
    docs/q3_thermalization.md, src/mcmc_baseline.py).

    Ensemble [derived]: uniform (infinite temperature) over the defect-free configurations of
    the initial winding sector W0 that single flippable-spin moves connect to the initial
    state. Model as in GaussLawConfig (J < 0 frustrated, h/|J| = 0.3, dt = 0.25 -- matching the
    reference's own triangular quench, arXiv:2503.20870 Fig. 4(e)/§V/Methods §VII.1
    [established]; see GaussLawConfig's docstring).
    Every number produced is a CLASSICAL statistical/simulated reference, not an H2 result.
    """

    J: float = -1.0
    dt: float = 0.25
    h_curves: tuple = (0.1, 0.2, 0.3, 0.5)   # ideal relaxation curves (0.3 = our working point,
                                             # matching the reference's own value, see
                                             # GaussLawConfig); handoff/08 A2
                                             # broadened from (0.1, 0.3). Leak table covers h <= 0.3:
                                             # its prediction at 0.5 is an extrapolation.
    qdm_times: float = 12.0            # total_time = qdm_times / h (H_QDM time unit is 1/h)
    max_snapshots: int = 80            # record_every chosen so snapshots <= this (memory)
    late_fraction: float = 0.5         # late window = last half of the curve
    # quantum-arm cases (Lx, Ly, initial state); all <= statevector ceiling
    curve_cases: tuple = ((3, 6, "3-sublattice"), (3, 4, "flippable"), (3, 4, "stripe"))
    # clusters where MCMC is checked against brute-force exact enumeration (N <= ED ceiling)
    exact_cases: tuple = ((3, 3, "3-sublattice"), (3, 4, "flippable"), (3, 6, "3-sublattice"),
                          (4, 5, "flippable"))
    # MCMC-only baselines beyond the exact ceiling (9x6 = reference Sec. V lattice size)
    mcmc_only_cases: tuple = ((6, 6, "3-sublattice"), (9, 6, "3-sublattice"))
    n_chains: int = 32                 # independent chains -> autocorrelation-aware errors
    n_sweeps: int = 4000               # measured sweeps per chain (1 sweep = N move attempts)
    burn_in: int = 500                 # sweeps discarded per chain
    n_shells: int = 3                  # dimer-correlation distance shells reported
    leak_table: str = "data/gauss_law_scaling.txt"   # measured P(W != W0) vs h (handoff/02)
    # --- handoff/08 Part A1: Trotter-threshold / dt-convergence study (K2), src/trotter_threshold.py ---
    thr_T: float = 20.0                # fixed physical time of every dt run (units 1/|J|)
    thr_h: tuple = (0.1, 0.2, 0.3, 0.5)
    # dense scan: every Trotter time compared with exact (cheap clusters); dt from (start, stop, step)
    thr_dense_cases: tuple = ((3, 3, "3-sublattice"), (3, 4, "flippable"), (3, 4, "stripe"))
    thr_dense: tuple = (0.02, 1.20, 0.02)
    # coarse scan on the largest exact cluster: compared at multiples of thr_cmp_every (dt must divide it)
    thr_coarse_cases: tuple = ((3, 6, "3-sublattice"),)
    thr_coarse_h: tuple = (0.1, 0.3)
    thr_coarse_dts: tuple = (0.025, 0.05, 0.1, 0.125, 0.2, 0.25, 1 / 3, 0.4, 0.5, 2 / 3, 1.0)
    thr_cmp_every: float = 2.0
    thr_eps: float = 0.05              # [assumed] absolute operational threshold: time-max |error| of the
                                       # flippable density reaches 0.05 (~15% of the 3-sublattice start's
                                       # 0.67 -> 0.38 relaxation, but comparable to the whole signal of the
                                       # 3x4 flippable start), hence also a relative criterion:
    thr_eps_rel: float = 0.1           # [assumed] error reaches 10% of the start's own relaxation signal
                                       # |f(c0) - f_DE| (f_DE = exact H_QDM long-time value; n/a for frozen starts)
    thr_fit_dt_max: float = 0.1        # O(dt^2) slope fitted on dt <= this
    # --- handoff/08 Part B1: noisy + Iceberg-encoded curves (src/noisy_q3.py) ---
    # Noise = the research/06 H2 PRIOR from SensitivityConfig (p2_prior, p1_ratio, zz_bias_prior):
    # an ASSUMED model; every noisy number is a classical prediction, NOT an H2 result.
    noisy_h: float = 0.3                                   # our working field, matching the
                                                           # reference's own value (GaussLawConfig)
    noisy_bare_cases: tuple = ((3, 3, "3-sublattice"), (3, 4, "flippable"))
    noisy_ice_cases: tuple = ((3, 4, "flippable"),)        # Iceberg needs even k: 3x3 (k=9) is out
    noisy_ice_steps: int = 48                              # encoded window (t = 12): post-selection
                                                           # survival is ~1% by then at the prior
    noisy_traj_bare: int = 400
    noisy_traj_ice: int = 300
    noisy_batches: int = 20                                # batch-means SE over fault patterns
    noisy_record_every: int = 2
    noisy_mem_gb: float = 2.0                              # refuse accumulators above this (host ~6 GB)
    # --- handoff/08 Part B2: classical size story ---
    size_stim_cases: tuple = ((3, 4, "flippable"), (3, 6, "3-sublattice"), (6, 6, "3-sublattice"),
                              (9, 6, "3-sublattice"))       # Stim first-order accounting (unbounded)
    size_mcmc_cases: tuple = ((12, 6, "3-sublattice"), (12, 12, "3-sublattice"))   # beyond 9x6
    size_survival: tuple = (0.5, 0.1, 0.01)                # report the time at which these survive


@dataclass
class Q2FrustrationConfig:
    """Q2 frustration thickening (handoff/09, docs/q2_frustration.md, src/frustration.py).

    Classical exact ground states (ED) of H = -J sum ZZ - h sum X on periodic square and
    triangular tori, J < 0 (AFM). Ground state for h > 0 taken in the global-spin-flip-even
    sector (unique and P-even by Perron-Frobenius [derived]); h = 0 is degenerate and its
    single-vector correlators are NOT interpreted. Every number is [measured], not an H2 result.
    """

    J: float = -1.0
    fields: tuple = (0.0, 0.1, 0.3, 0.6, 1.0)          # as data/frustration_compare.txt
    # Part A clusters (Lx, Ly), both geometries. 4x4 is the only bipartite (= truly unfrustrated)
    # square torus with both lengths >= 3 within the ED ceiling; 3x4 is kept for continuity with
    # data/frustration_compare.txt but its square torus has an odd periodic length (frustrated).
    partA_clusters: tuple = ((4, 4), (3, 4))
    distance_decimals: int = 6                         # rounding used to bin pair distances


@dataclass
class NoiseScalingConfig:
    """6x6 noise-scaling arm, T-17 / R-14 (src/noise_scaling.py, docs/q3_noise_scaling.md,
    research/derivations/01-noise-scaling-arm.md). Decisions D1-D5 of 2026-10-16 (the project lead):
    diagnostic first, then extrapolation; Pauli insertion before 2q gates for the lam ladder, plus
    one folded point; bare + Gauss post-selection only; lam = (1, 2, 3); exponential fit with the
    asymptote FIXED at the infinite-T value (sector B_W0 conditioned, full space raw).
    Every number produced is a CLASSICAL PREDICTION under the ASSUMED research/06 prior, not H2.
    """

    lams: tuple = (1, 2, 3)            # D4: insertion ladder (nominal 2q-error scale)
    fold_lam: int = 3                  # D2: the one folded check point (odd: G (G^-1 G)^k)
    z_min: float = 3.0                 # [assumed] slope "resolved" at |z| >= 3
    p_consistent: float = 0.05         # [assumed] fit reported only if chi2 p-value >= this
    fold_scope: tuple = ("rot-zz",)    # D2/spec: fold and insert 2q (logical-ZZ) gates only
    # [measured, offline H2-1 compile, research/derivations/01] TKET optimisation levels 1 and 2
    # (2 = Quantinuum's default) cancel ZZ(a) ZZ(-a) ZZ(a) back to one gate, silently turning the
    # folded lam = 3 point into lam = 1. Folded circuits must compile at level 0 (and be submitted
    # with server-side optimisation off). Guarded by tests/test_noise_scaling.py (T17).
    compile_opt_level: int = 0
    # 6x6 target (T-18) and its sector baseline B_W0 (data/q3_size.txt, MCMC [measured])
    target: tuple = (6, 6, "3-sublattice")
    b_w0_target: float = 0.30884
    # 3x4 classical validation (trajectories exist there; data/q3_noisy.txt) and sigma_1 cases
    val_case: tuple = (3, 4, "flippable")
    val_steps: int = 32                # t <= 8
    val_record_every: int = 4
    val_traj: int = 400
    val_batches: int = 20
    sigma_cases: tuple = ((3, 4, "flippable"), (3, 6, "3-sublattice"))
    # shot plan for the 6x6 arm (illustrative until the project lead fixes the budget)
    plan_times: tuple = (1.0, 2.0, 3.0)  # D7 (2026-10-16): early window only; no late-time 6x6
                                         # thermalization claim. Recompute once G2 is known.
    fold_plan_time: float = 2.0       # [assumed] D2: the ONE folded lam=3 check sits at this t
    plan_shots: int = 500              # [assumed] per circuit per lam point, pre post-selection
    plan_slope: float = 0.005          # [assumed] smallest conditioned slope dO/dlam_eff to resolve

    # --- Phase 2 (handoff/14): the Q3 circuits for H2, shrunk to what the emulator can run (OPEN-4,
    # decided 2026-10-17: 6x6 stays a Stim-only design; the ladder is built at 3x4, the bare size
    # story at 3x6). Times are in units of 1/|J|; a time t is round(t / q3.dt) Trotter steps, at the
    # working point q3.noisy_h, q3.J, q3.dt. src/h2_q3.py, src/h2_driver.py groups "Q3-*".
    h2_bare_times: tuple = (1, 2, 3, 4, 5, 6, 7, 8)     # 3x4 flippable, bare (Gauss post-selection is classical)
    h2_iceberg_times: tuple = (1, 2, 3, 4)               # 3x4 flippable Iceberg, t <= 4 only (survival)
    h2_ladder_times: tuple = (1, 2, 3)                   # 3x4 lambda ladder (bare), = plan_times
    h2_bare36_times: tuple = (1, 2, 3)                   # 3x6 3-sublattice, bare
    insert_instances: int = 10                           # independent Pauli-insertion draws per (lambda>1, t) point; shots split over them
                                       # at z_min (3x4 cond drift ~0.008 at the prior; 6x6 rates 3x)


@dataclass
class Q3ScalingConfig:
    """Q3 generalization study (src/q3_scaling.py, src/noisy_q3_sweep.py, docs/q3_scaling.md).

    The Iceberg-vs-Gauss-law conclusion of docs/q3_thermalization.md §9.2 rests on ONE cell
    (N = 12, h = 0.3, lam = 1). This block holds the axes it is generalized over, per the project
    lead's decision cards D1-D6 of 2026-10-22: D1 size, D2 field, D3 noise scale, D4 Stim
    prefilter before the expensive stage, D5 timing probe before fixing trajectory counts,
    D6 build an encoded lambda runner (src/noise_scaling.run_iceberg_scaled).

    Every number produced is a CLASSICAL PREDICTION under the ASSUMED research/06 H2 prior,
    never an H2 / hardware result.
    """

    # D1: logical sizes. The exact-circuit stage is limited to those whose PHYSICAL Iceberg
    # register (N + 4) fits the state-vector ceiling; 36 and 54 are Stim-only (Stim is unbounded).
    # The (Lx, Ly, start) of each N lives in src/q3_scaling.SIZE_TO_CASE (already-validated cases).
    sizes_exact: tuple = (12, 18, 20)
    sizes_stim_only: tuple = (36, 54)
    # D2: fields, = Q3BaselineConfig.h_curves (no new field values are introduced).
    # D3: insertion ladder, = NoiseScalingConfig.lams, now on BOTH arms (D6).
    lams: tuple = (1, 2, 3)
    # D4: a cell reaches the expensive stage only if its predicted Iceberg post-selection survival
    # is at least this [assumed threshold: below it the encoded arm cannot resolve anything at any
    # affordable trajectory count].
    survival_floor: float = 0.05
    # Encoded window, per size: the largest number of Trotter steps whose predicted survival is
    # still >= survival_floor, capped at Q3BaselineConfig.noisy_ice_steps. The comparison is then
    # reported at MATCHED SURVIVAL rather than a matched window (project lead, 2026-10-22), with
    # the window stated for every cell; the shrinking encoded reach is itself a result.
    ice_window_cap: int = 48
    # D5: timing probe (scripts/probe_q3_scaling_timing.py) before the budget is committed.
    probe_traj: int = 5
    probe_steps: int = 8
    # Trajectory counts and accumulator settings per logical size. The accumulators are
    # n_batches * n_records * 2^N * 8 bytes, so the published 20 batches / record_every 2 would
    # need ~4.2 GB at N = 20 and be refused by noisy_mem_gb: larger N trades record density and
    # batch count for feasibility, and the SE is reported from however many batches remain.
    # Filled from the D5 probe; N = 12 keeps the published settings exactly.
    per_size: dict = field(default_factory=lambda: {
        12: {"traj_bare": 400, "traj_ice": 300, "batches": 20, "record_every": 2, "mem_gb": 2.0},
        18: {"traj_bare": 200, "traj_ice": 100, "batches": 10, "record_every": 4, "mem_gb": 4.0},
        20: {"traj_bare": 120, "traj_ice": 48, "batches": 8, "record_every": 6, "mem_gb": 6.0},
    })
    # D4: the extreme combinations run on top of the one-axis-at-a-time grid (N, h, lam).
    extreme_combos: tuple = ((20, 0.5, 3), (18, 0.1, 3), (12, 0.5, 3))
    # Stim survival levels reported per size (as Q3BaselineConfig.size_survival).
    survival_levels: tuple = (0.5, 0.1, 0.05, 0.01)


@dataclass
class RunConfig:
    """Top-level run configuration — the one object the rest of the code reads."""

    backend: Backend = "statevector"
    lattice: LatticeConfig = field(default_factory=LatticeConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    trotter: TrotterConfig = field(default_factory=TrotterConfig)
    ceilings: CeilingConfig = field(default_factory=CeilingConfig)
    hardware: HardwareConfig = field(default_factory=HardwareConfig)
    qec: QECConfig = field(default_factory=QECConfig)
    gauss: GaussLawConfig = field(default_factory=GaussLawConfig)
    compare: CompareConfig = field(default_factory=CompareConfig)
    encoded: EncodedConfig = field(default_factory=EncodedConfig)
    sensitivity: SensitivityConfig = field(default_factory=SensitivityConfig)
    q3: Q3BaselineConfig = field(default_factory=Q3BaselineConfig)
    q2: Q2FrustrationConfig = field(default_factory=Q2FrustrationConfig)
    noise_scaling: NoiseScalingConfig = field(default_factory=NoiseScalingConfig)
    q3_scaling: Q3ScalingConfig = field(default_factory=Q3ScalingConfig)

    # Reproducibility / IO
    seed: int = 1234
    data_dir: str = "data"
    figures_dir: str = "figures"


# Default run config imported elsewhere. Construct a fresh RunConfig() for tests
# that need to vary parameters without mutating this shared default.
CONFIG = RunConfig()
