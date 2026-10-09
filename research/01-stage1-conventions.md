# Research Note 01 — Stage 1 (square, unencoded) conventions

**Purpose:** minimal literature pass in service of coding Stage 1 correctly (SCOPE §14:
"Research is in service of code"). Not a full sweep — that is qc-researcher's job.
Status tags: [established] standard/textbook, [inferred] reasonable from sources,
[unverified] not yet checked against primary source.

## Reproduction target — Haghshenas et al., arXiv:2503.20870
- Verified live: title "Digital quantum magnetism on a trapped-ion quantum computer",
  Nature 653, 56–62 (2026), v3. Abstract fetched 2026-10-06. [established]
- Content relevant to Stage 1: digitized (Trotterized) dynamics of the quantum Ising
  model on Quantinuum H2; square lattice baseline, triangular lattice with periodic
  BC as the frustrated extension; observables centre on thermalization, relaxation of
  an inhomogeneous initial state, emergent hydrodynamics / diffusion constant. [established]
- Exact per-term coefficients, gate-angle conventions, and the specific inhomogeneous
  initial states are in the paper body/supplement — NOT yet extracted here. Numerical
  comparison to their published curves is deferred to qc-researcher + a later milestone.
  Do NOT hardcode any of their numbers. [unverified]

## TFIM Hamiltonian convention used in code [established]
Transverse-field Ising model, nearest-neighbour on a 2D square lattice:

    H = -J * sum_{<i,j>} Z_i Z_j  -  h * sum_i X_i

- J > 0 ferromagnetic coupling; h transverse field. Sign/axis convention is the common
  condensed-matter one (Sachdev). Pauli Z is the Ising/computational axis, X the field.
- Lattice: Lx x Ly square grid, row-major index n = y*Lx + x.
- Boundary conditions: open (OBC) or periodic (PBC), config-switchable. PBC adds the
  wrap bonds in each direction (skip the degenerate wrap when Lx or Ly == 2 to avoid
  double-counting a bond).

## 2nd-order Suzuki–Trotter (Strang splitting) [established]
Split H = A + B with A = -J sum ZZ (diagonal in Z basis), B = -h sum X.
Second-order step of duration dt:

    U2(dt) = exp(-i A dt/2) exp(-i B dt) exp(-i A dt/2)

Local error per step O(dt^3); global error O(dt^2) over fixed total time. Evolving N
steps: half-steps of A merge between consecutive steps, but we keep the explicit
symmetric form for clarity and correctness checks. exp(-i A dt/2) is diagonal;
exp(-i B dt) factorizes over sites as single-qubit X-rotations (tensor product of
2x2 blocks), applied without forming the full 2^N operator.

Expected-results theory for the finite-dt Trotter [established; review/06 A5]: below a
*sharp* Trotter-step threshold, local observables stay faithful and become independent of
system size and total time (Heyl, Hauke, Zoller, Sci. Adv. 5, eaau8342, arXiv:1806.11123);
above it the Floquet dynamics is quantum-chaotic and errors proliferate. Even a *coarse*
2nd-order Trotter prethermalizes, tracking the thermal values of the target Hamiltonian up
to long times before slow heating (Yang et al., PRX Quantum 4, 030320, arXiv:2303.08461).
These justify finite-dt runs for local observables and motivate a dt-convergence/threshold
study (not yet built — a scope decision, review/06 K2).

## Observables (HANDOFF §3) [established definitions]
- Total magnetization along Z: M_z = sum_i <Z_i>; also per-site m_z = M_z / N.
- (Transverse) magnetization along X: M_x = sum_i <X_i>.
- Variance of magnetization: Var(M_z) = <M_z^2> - <M_z>^2.
- Two-point correlations: C_zz(i,j) = <Z_i Z_j> - <Z_i><Z_j> (connected), plus the
  raw <Z_i Z_j>. Distance-resolved average for curves.
- Energy: <H>.
- Relaxation: observable (e.g. local or staggered magnetization) vs Trotter time,
  from a chosen initial product state. Ergodic/infinite-temperature baseline for a
  traceless local observable like <Z_i> is 0; we compare approach to it.

## Backends (SCOPE §5 ceilings)
- Sparse ED (Lanczos): scipy.sparse.linalg.eigsh, ground state + low spectrum.
  Ceiling <=~22–24 spins pending an empirical memory probe (NOT yet frozen).
- Statevector Trotter: dense complex128 state of length 2^N; <=~24 spins pending probe.
  Memory for the state alone: 2^N * 16 bytes (N=24 -> 268 MB; N=26 -> 1.07 GB).
  Operators applied without materializing 2^N x 2^N dense matrices.
- Serial execution only (host ~7.6 GB available).
