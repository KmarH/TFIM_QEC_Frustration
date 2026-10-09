"""TFIM logical-qubit simulation — Stage 1 (square lattice, unencoded).

Modules:
  lattice      — site indexing and nearest-neighbour bond enumeration
  operators    — sparse Pauli operators and the TFIM Hamiltonian builder
  trotter      — second-order Suzuki–Trotter statevector evolution
  backends     — ED (Lanczos) and statevector backends behind the config switch
  observables  — magnetization, variance, two-point correlations, energy, relaxation
"""
