"""FROZEN test spec (test-first) for src/noisy_q3_sweep.py: the noisy bare + Iceberg Q3 sweep
over (case, h, lam). Written BEFORE the module exists; the implementation must make these pass
WITHOUT editing this file.

Every noisy number is a CLASSICAL PREDICTION under the ASSUMED research/06 H2 prior
(Pauli-trajectory simulation), never an H2 result.

Interface under test (black box):
    run_noisy_sweep(cases, h_values, lams, *, n_traj_bare, n_traj_ice, n_batches, seed,
                    noise=<research/06 prior>, return_meta=False, steps=None) -> dict

    cases: sequence of (Lx, Ly, start_label), e.g. (3, 4, "flippable").

Return shape FIXED by this spec (the implementer must produce exactly this):
    result[(Lx, Ly, start_label, h, lam)] = cell, with
      cell["bare"] = {"times": 1-D array (t = step * dt),
                      "flippable_density": 1-D array, RAW (not Gauss-conditioned), aligned with times,
                      "flippable_density_se": 1-D array, batch-means SE, aligned with times}
      cell["ice"]  = same three keys for the Iceberg-encoded, detector-post-selected arm,
                     or None when the case has no Iceberg arm (odd N).
      cell["meta"] = {"physical_qubits": int}     present only when return_meta=True;
                     the Iceberg register size actually used (code + ancillas).
    Keyword-only extras the implementer must wire:
      noise:       a src.encoded_codes.NoiseRates; default = the research/06 prior
                   (config.SensitivityConfig, as scripts/run_q3_noisy.py:34-35). Test 2.2 passes
                   NoiseRates() (all rates 0) to request the ideal circuit.
      return_meta: bool, default False.
      steps:       int or None, default None. None = the full default windows (unchanged
                   behaviour); an int caps BOTH arms at that many Trotter steps (runtime cap,
                   coordinator decision 2026-10-22; used by 2.3).
    With steps=None the time grid must contain every integer t of data/q3_noisy.txt's 3x4 table
    (bare t = 0..40, Iceberg t = 0..12), i.e. the bare window is qdm_times / h and the Iceberg
    window is q3.noisy_ice_steps, as in that run.
"""

import math

import numpy as np
import pytest
from src.noisy_q3_sweep import run_noisy_sweep

from config import CONFIG
from src.dimers import TriangularDimers
from src.encoded_codes import NoiseRates
from src.mcmc_baseline import initial_spins
from src.trotter import circuit_trotter2_step, ising_diagonal

J = CONFIG.q3.J            # -1.0 (config.Q3BaselineConfig; data/q3_noisy.txt:4 "J=-1.0")
DT = CONFIG.q3.dt          # 0.25
CASE = (3, 4, "flippable")
H = 0.3
SEED = 0                   # documented constant; the implementation's seed convention is not fixed
SHORT_STEPS = 8            # runtime cap for 2.3 (coordinator decision 2026-10-22)

# --------------------------------------------------------------------------- 2.1 oracle
# Copied verbatim from data/q3_noisy.txt lines 58-98 (section "## 3x4 start=flippable W0=(0, 2),
# h=0.3", line 53; 400 bare / 300 Iceberg trajectories, 20 batches). Columns kept: t, then the
# flippable-density "bare raw" value±SE and "ice raw" value±SE ("-" = n/a beyond the Iceberg
# window t = 12). Values printed to 4 decimals.
_TABLE_3x4 = """
 0.0 +0.3332 0.0000 +0.3327 0.0006
 1.0 +0.2866 0.0028 +0.2981 0.0016
 2.0 +0.2483 0.0041 +0.2637 0.0019
 3.0 +0.2312 0.0046 +0.2534 0.0022
 4.0 +0.2259 0.0055 +0.2531 0.0036
 5.0 +0.2290 0.0054 +0.2632 0.0061
 6.0 +0.2294 0.0059 +0.2755 0.0034
 7.0 +0.2151 0.0061 +0.2626 0.0059
 8.0 +0.1979 0.0055 +0.2358 0.0113
 9.0 +0.1917 0.0055 +0.2305 0.0148
10.0 +0.1891 0.0057 +0.2303 0.0169
11.0 +0.1849 0.0058 +0.2299 0.0190
12.0 +0.1791 0.0059 +0.2338 0.0190
13.0 +0.1706 0.0063 - -
14.0 +0.1610 0.0060 - -
15.0 +0.1560 0.0065 - -
16.0 +0.1533 0.0066 - -
17.0 +0.1519 0.0064 - -
18.0 +0.1470 0.0064 - -
19.0 +0.1408 0.0060 - -
20.0 +0.1356 0.0059 - -
21.0 +0.1343 0.0060 - -
22.0 +0.1326 0.0063 - -
23.0 +0.1254 0.0056 - -
24.0 +0.1192 0.0055 - -
25.0 +0.1157 0.0053 - -
26.0 +0.1117 0.0051 - -
27.0 +0.1086 0.0051 - -
28.0 +0.1068 0.0049 - -
29.0 +0.1034 0.0046 - -
30.0 +0.1012 0.0043 - -
31.0 +0.0981 0.0045 - -
32.0 +0.0948 0.0044 - -
33.0 +0.0918 0.0043 - -
34.0 +0.0891 0.0043 - -
35.0 +0.0879 0.0044 - -
36.0 +0.0861 0.0043 - -
37.0 +0.0851 0.0043 - -
38.0 +0.0833 0.0044 - -
39.0 +0.0813 0.0043 - -
40.0 +0.0784 0.0041 - -
"""

ROUND = 5e-5   # half a unit in the 4th decimal (both the printed value and the printed SE)


def _parse_table():
    bare, ice = [], []
    for line in _TABLE_3x4.strip().splitlines():
        t, bv, bs, iv, isd = line.split()
        bare.append((float(t), float(bv), float(bs)))
        if iv != "-":
            ice.append((float(t), float(iv), float(isd)))
    return bare, ice


def _lookup(times, t):
    idx = np.nonzero(np.isclose(np.asarray(times, dtype=float), t, atol=1e-9))[0]
    assert len(idx) == 1, f"t={t} missing from (or duplicated in) the returned time grid"
    return int(idx[0])


def _statistical_agreement(arm, rows, label):
    """2-sigma agreement of two independent Monte-Carlo estimates of the same curve.

    The literal brief asked for |new - file| <= 2 * SE_file at every point. That is NOT a 2-sigma
    test of two independent estimates: the difference has SD ~ sqrt(SE_file^2 + SE_new^2)
    (~ sqrt(2) SE_file at equal trajectory counts), so each point fails with p ~ 0.16, and over
    ~41 (correlated) points an honest implementation would fail most runs. The check below is
    the 2-sigma test of the DIFFERENCE, with printed-rounding allowance, required at >= 90 % of
    the points, plus a hard 4-sigma bound at every point (catches a real bias).
    """
    within2, n = 0, 0
    for t, ref, se_ref in rows:
        k = _lookup(arm["times"], t)
        new = float(arm["flippable_density"][k])
        se_new = float(arm["flippable_density_se"][k])
        assert math.isfinite(new) and math.isfinite(se_new) and se_new >= 0
        sd = math.hypot(se_ref + ROUND, se_new)
        diff = abs(new - ref)
        assert diff <= 4 * sd + ROUND, f"{label} t={t}: {new:.4f} vs file {ref:.4f} (4-sigma {4 * sd:.4f})"
        within2 += diff <= 2 * sd + ROUND
        n += 1
    assert within2 >= 0.9 * n, f"{label}: only {within2}/{n} points within 2 sigma of data/q3_noisy.txt"


@pytest.mark.slow
def test_sweep_reproduces_q3_noisy_3x4_flippable_within_two_sigma():
    """2.1: (3x4 flippable, h = 0.3, lam = 1) at the data-file trajectory counts reproduces the
    bare-raw and Iceberg-raw flippable-density curves of data/q3_noisy.txt statistically
    (soft 2-sigma check; seed convention not fixed). Cost [measured in the data file header,
    line 53]: ~186 s bare + ~559 s Iceberg on the 2-core host."""
    res = run_noisy_sweep([CASE], [H], [1], n_traj_bare=400, n_traj_ice=300, n_batches=20, seed=SEED)
    cell = res[(*CASE, H, 1)]
    bare_rows, ice_rows = _parse_table()
    _statistical_agreement(cell["bare"], bare_rows, "bare raw")
    assert cell["ice"] is not None
    _statistical_agreement(cell["ice"], ice_rows, "ice raw")


# --------------------------------------------------------------------------- 2.2
def _ideal_flippable_curve(Lx, Ly, label, h, n_steps):
    """Independent ideal reference: circuit-order Strang (X half, ZZ, X half) state vector via
    src/trotter.circuit_trotter2_step (not the noisy_q3 / pytket path), flippable density from
    src/dimers. Cross-checked 2026-10-22 against data/q3_noisy.txt's 'ideal' column at
    t = 0,1,2,3,4,8,12,20,40: agreement within the printed 5e-5 [measured, scratch check]."""
    d = TriangularDimers(Lx, Ly)
    s0 = initial_spins(d, label)
    psi = np.zeros(1 << d.N, dtype=np.complex128)
    psi[d.product_state_index(s0)] = 1.0
    diag = ising_diagonal(d.N, d.bonds, J)
    flips = sum(d.flippable(s).astype(np.float64) for s in range(d.N)) / d.N
    out = [float(np.abs(psi) ** 2 @ flips)]
    for _ in range(n_steps):
        psi = circuit_trotter2_step(psi, d.N, diag, h, DT)
        out.append(float(np.abs(psi) ** 2 @ flips))
    return np.array(out)


def test_zero_noise_sweep_equals_ideal_circuit():
    """2.2: transparency. With all noise rates 0 (noise=NoiseRates()), both arms reproduce the
    ideal circuit-order curve to 1e-8 absolute at every returned time (the Iceberg arm is
    transparent at zero noise, docs/q3_thermalization.md §9.1)."""
    res = run_noisy_sweep([CASE], [H], [1], n_traj_bare=2, n_traj_ice=2, n_batches=2, seed=SEED,
                          noise=NoiseRates())
    cell = res[(*CASE, H, 1)]
    assert cell["ice"] is not None
    n_max = max(round(float(t) / DT) for arm in (cell["bare"], cell["ice"]) for t in arm["times"])
    ref = _ideal_flippable_curve(*CASE, H, n_max)
    for name in ("bare", "ice"):
        arm = cell[name]
        times = np.asarray(arm["times"], dtype=float)
        assert len(times) > 1
        steps = np.rint(times / DT).astype(int)
        assert np.allclose(steps * DT, times, atol=1e-12)
        got = np.asarray(arm["flippable_density"], dtype=float)
        assert got.shape == times.shape
        err = np.max(np.abs(got - ref[steps]))
        assert err <= 1e-8, f"{name}: max |zero-noise - ideal| = {err:.2e}"


# --------------------------------------------------------------------------- 2.3
@pytest.mark.slow
@pytest.mark.parametrize("case", [(3, 6, "3-sublattice"), (4, 5, "flippable")])
def test_iceberg_physical_register_is_n_plus_4(case):
    """2.3: Iceberg [[N+2, N, 2]] plus 2 syndrome ancillas = N + 4 physical qubits
    (data/q3_noisy.txt:53 '[[14,12,2]] (16 physical)'; docs/q3_thermalization.md:339 '6x6 (40
    physical)'). N = 18 -> 22, N = 20 -> 24 (= the state-vector ceiling, CeilingConfig).
    Minimal trajectory counts and a capped window (steps=8): this checks the register, not the
    statistics; the full 24-qubit Iceberg window could take tens of minutes [inferred]."""
    Lx, Ly, _ = case
    n_logical = Lx * Ly
    assert n_logical + 4 <= CONFIG.ceilings.statevector_max_spins
    res = run_noisy_sweep([case], [H], [1], n_traj_bare=1, n_traj_ice=1, n_batches=1, seed=SEED,
                          return_meta=True, steps=SHORT_STEPS)
    cell = res[(*case, H, 1)]
    assert cell["meta"]["physical_qubits"] == n_logical + 4
    # the cap was honoured on both arms
    for name in ("bare", "ice"):
        assert max(round(float(t) / DT) for t in cell[name]["times"]) == SHORT_STEPS
