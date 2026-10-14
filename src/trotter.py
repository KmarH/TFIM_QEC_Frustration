"""Second-order Suzuki–Trotter statevector evolution for the TFIM.

Split H = A + B with
    A = -J sum_<ij> Z_i Z_j   (diagonal in the computational/Z basis)
    B = -h sum_i X_i          (sum of commuting single-site terms)

Symmetric (Strang) step of duration dt:
    U2(dt) = exp(-i A dt/2) exp(-i B dt) exp(-i A dt/2)

Local error O(dt^3), global error O(dt^2) at fixed total time. The symmetric
(ABA) ordering is what buys the second order: the first-order error term of the
naive e^{-iA dt} e^{-iB dt} splitting cancels by the symmetry, leaving the
leading error at O(dt^3) per step. Consecutive A half-steps could be merged into
one full step between adjacent Trotter steps, but we keep the explicit symmetric
form for clarity and for step-by-step correctness checks. Each factor is unitary,
so the state norm is conserved up to rounding — a drifting norm signals a bug,
not Trotter error (which instead shows up as O(dt^2) drift in conserved <H>).

Memory: operators are applied to the length-2^N statevector directly, never
forming a 2^N x 2^N matrix. exp(-iA dt/2) is a diagonal phase (an elementwise
multiply). exp(-iB dt) factorizes into independent single-qubit X-rotations,
each applied by reshaping the state so the target site is its own axis. Peak
memory is O(2^N) complex128.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np


def ising_diagonal(n_sites: int, bonds: List[Tuple[int, int]], J: float) -> np.ndarray:
    """Diagonal of A = -J sum_<ij> Z_i Z_j in the computational basis.

    Z eigenvalue of site k in basis state b is +1 if bit k is 0, else -1, using
    the Kronecker ordering where site 0 is the most significant bit (consistent
    with src.operators). Returns a real array of length 2^n_sites.
    """
    dim = 1 << n_sites
    idx = np.arange(dim, dtype=np.int64)
    # z[:, k] = +1/-1 eigenvalue of Z on site k for each basis index.
    # site 0 is the MSB: shift = (n_sites - 1 - k).
    diag = np.zeros(dim, dtype=np.float64)
    for (i, j) in bonds:
        zi = 1 - 2 * ((idx >> (n_sites - 1 - i)) & 1)
        zj = 1 - 2 * ((idx >> (n_sites - 1 - j)) & 1)
        diag += zi * zj
    return -J * diag


def apply_x_rotations(state: np.ndarray, n_sites: int, theta: float) -> np.ndarray:
    """Apply exp(-i theta sum_k X_k) = prod_k exp(-i theta X_k) to `state`.

    exp(-i theta X) = cos(theta) I - i sin(theta) X. For each site, reshape the
    state to expose that site's axis and mix the two components. O(2^N) memory,
    O(N 2^N) time.
    """
    c = np.cos(theta)
    s = -1j * np.sin(theta)
    psi = state.reshape((2,) * n_sites)
    for k in range(n_sites):
        psi = np.moveaxis(psi, k, 0)
        a = psi[0].copy()
        b = psi[1].copy()
        psi[0] = c * a + s * b
        psi[1] = s * a + c * b
        psi = np.moveaxis(psi, 0, k)
    return psi.reshape(-1)


def trotter2_step(
    state: np.ndarray,
    n_sites: int,
    ising_diag: np.ndarray,
    h: float,
    dt: float,
) -> np.ndarray:
    """One second-order Trotter step U2(dt) applied to `state`.

    ising_diag is the precomputed diagonal of A (from ising_diagonal). The field
    half-angle uses B = -h sum X, so exp(-iB dt) = exp(i h dt sum X), i.e.
    theta = -h * dt in exp(-i theta sum X).

    This is the ZZ-outside (ABA) splitting: exp(-iA dt/2) exp(-iB dt) exp(-iA dt/2).
    It is unitarily conjugate to the X-outside splitting the published H2 circuits
    use (same quasienergies, hence the same threshold location), but observables
    read in the two frames differ (review/ordering finding, docs/q3_thermalization.md
    §8). For any claim about those circuits, use `circuit_trotter2_step` instead.
    """
    half_phase = np.exp(-0.5j * dt * ising_diag)
    state = half_phase * state
    state = apply_x_rotations(state, n_sites, theta=-h * dt)
    state = half_phase * state
    return state


def circuit_trotter2_step(
    state: np.ndarray,
    n_sites: int,
    ising_diag: np.ndarray,
    h: float,
    dt: float,
) -> np.ndarray:
    """One second-order Trotter step in the CIRCUIT (X-outside) frame:
    exp(-iB dt/2) exp(-iA dt) exp(-iB dt/2), B = -h sum X, A = -J sum ZZ.

    This is the splitting the published H2 circuits (arXiv:2503.20870) actually
    implement (X half-layer, ZZ layer, X half-layer per step) and is the same
    formula `src/compare.py:circuit_trotter_states` evaluates gate-by-gate; use
    THIS function (not `trotter2_step`) for any claim about those circuits or
    about quantities read out in their frame (e.g. defect density, P_out).
    `trotter2_step`'s ZZ-outside splitting gives a different reading of the same
    physical state at the published h*dt = 0.5 — see docs/q3_thermalization.md §8.

    Signature matches `trotter2_step` so one can be swapped for the other.
    """
    half_x = -h * dt / 2
    state = apply_x_rotations(state, n_sites, theta=half_x)
    full_phase = np.exp(-1j * dt * ising_diag)
    state = full_phase * state
    state = apply_x_rotations(state, n_sites, theta=half_x)
    return state


def evolve(
    state: np.ndarray,
    n_sites: int,
    bonds: List[Tuple[int, int]],
    J: float,
    h: float,
    total_time: float,
    n_steps: int,
    record_every: int = 0,
) -> Tuple[np.ndarray, List[Tuple[float, np.ndarray]]]:
    """Evolve `state` for total_time in n_steps 2nd-order Trotter steps.

    If record_every > 0, snapshots (time, state_copy) are collected every
    record_every steps (and at t=0), useful for relaxation curves. Returns
    (final_state, snapshots).
    """
    if n_steps <= 0:
        raise ValueError("n_steps must be positive")
    dt = total_time / n_steps
    ising_diag = ising_diagonal(n_sites, bonds, J)

    state = np.asarray(state, dtype=np.complex128).copy()
    snapshots: List[Tuple[float, np.ndarray]] = []
    if record_every > 0:
        snapshots.append((0.0, state.copy()))

    for step in range(1, n_steps + 1):
        state = trotter2_step(state, n_sites, ising_diag, h, dt)
        if record_every > 0 and step % record_every == 0:
            snapshots.append((step * dt, state.copy()))

    return state, snapshots
