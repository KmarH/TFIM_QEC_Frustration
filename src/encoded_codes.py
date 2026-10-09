"""Generic encoded-TFIM pipeline for any stabilizer block code (handoff/04 Part B).

Codes: Iceberg [[k+2,k,2]] (same block as Part A), Steane [[7,1,3]], 5-qubit [[5,1,3]],
concatenated Iceberg [[16,4,4]]. Logical lattice qubits are packed into blocks (k_block
logicals per block); the register is all data qubits followed by one syndrome / rotation
ancilla A and one flag F:  n_phys = n_blocks * n_block + 2.

Program (prep basis "Z" is what is executed; "X" exists only as a Stim verification image):
  1. all qubits |0> (|+> on data for the X image)
  2. round 0: measure every stabilizer (flagged, basis-changed to Z parity). Stabilizers that
     are deterministic in the prep basis are DETECTORS; for the others the outcome is random and
     a FEEDFORWARD Pauli correction (the stabilizer's pure error, chosen to commute with every
     logical operator) sets the frame to +1. After this every stabilizer is +1, so logical
     operators may be represented by minimum-weight stabilizer-equivalent Pauli strings.
  3. logical ry(theta) = exp(-i theta/2 Ybar) per logical qubit
  4. per Trotter step (circuit-order Strang, as src/compare.py): exp(+i h dt/2 Xbar) per logical,
     exp(+i J dt Zbar Zbar) per bond, exp(+i h dt/2 Xbar); then a syndrome round (all detectors)
  5. Z readout of the data; logical Zbar from pure-Z readout representatives; final detectors
     from pure-Z stabilizers.
Logical Pauli rotation exp(-i phi P) (P a signed physical Pauli string):
  weight 2 -> basis change + one ZZPhase + undo (no ancilla; Iceberg's native gate);
  weight >2 -> basis change, CNOT the support (interleaved across blocks) onto A, Rz on A,
  uncompute, undo basis change, MEASURE A (must read 0: a detector) and reset it.
A Pauli fault passes a Pauli rotation unchanged (only the angle sign flips), so in the Stim
image every rotation is the identity for fault propagation [derived]; a 'clifford' image maps
Clifford angles to Clifford gates for the execution-consistency check.

Noise [ASSUMED generic depolarizing, never H2-calibrated]: p2 after each 2-qubit gate, p1
after each 1-qubit gate, pm on each measurement, p_init on each reset. Frame corrections are
Pauli-frame updates, applied noiselessly in local-sim and Stim; Selene executes them as
physical x/y/z gates and so applies its p_1q to them [stated difference].
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import stim
from pytket import Circuit, OpType

from src.encoded_tfim import check_physical_ceiling
from src.lattice import square_bonds


# --------------------------------------------------------------------------- #
# Codes
# --------------------------------------------------------------------------- #
@dataclass
class BlockCode:
    name: str
    n: int                                   # data qubits per block
    stabilizers: List[stim.PauliString]      # generators on the block (sign +1)
    orders: List[List[int]]                  # CNOT order of each stabilizer's support
    logical_x: List[stim.PauliString]        # per logical in the block
    logical_z: List[stim.PauliString]

    @property
    def k(self) -> int:
        return len(self.logical_x)


def _ps(s: str) -> stim.PauliString:
    return stim.PauliString(s)


def _support(p: stim.PauliString) -> List[int]:
    return [i for i in range(len(p)) if p[i]]


def iceberg_code(k: int) -> BlockCode:
    from src.qec.iceberg import IcebergCode
    c = IcebergCode(k)
    st = c.stabilizers()
    return BlockCode(f"Iceberg[[{k + 2},{k},2]]", c.n, st, [_support(s) for s in st],
                     [c.logical_x(i) for i in range(k)], [c.logical_z(i) for i in range(k)])


def steane_code() -> BlockCode:
    from src.qec.on_paper_codes import steane_logicals, steane_stabilizers
    st = steane_stabilizers()
    lx, lz = steane_logicals()
    return BlockCode("Steane[[7,1,3]]", 7, st, [_support(s) for s in st], lx, lz)


def five_qubit_code() -> BlockCode:
    from src.qec.on_paper_codes import five_qubit_logicals, five_qubit_stabilizers
    st = five_qubit_stabilizers()
    lx, lz = five_qubit_logicals()
    return BlockCode("5-qubit[[5,1,3]]", 5, st, [_support(s) for s in st], lx, lz)


def concat_d4_code() -> BlockCode:
    from src.qec.concatenated import ConcatenatedIceberg
    c = ConcatenatedIceberg(2, 2)
    st = c.stabilizers()
    orders = ([c.inner_support(j) for j in range(c.n_outer)] + [c.outer_support("X", a) for a in range(c.k_inner)]
              + [c.inner_support(j) for j in range(c.n_outer)] + [c.outer_support("Z", a) for a in range(c.k_inner)])
    return BlockCode("ConcatIceberg[[16,4,4]]", c.n, st, orders, c.logical_x(), c.logical_z())


def make_code(name: str, k_lattice: int) -> BlockCode:
    """Block code by name; Iceberg packs the whole logical lattice into one block."""
    if name == "iceberg":
        return iceberg_code(k_lattice)
    return {"steane": steane_code, "five": five_qubit_code, "concat": concat_d4_code}[name]()


# --------------------------------------------------------------------------- #
# GF(2) helpers: pure errors and minimum-weight representatives
# --------------------------------------------------------------------------- #
def _sym(p: stim.PauliString) -> np.ndarray:
    x, z = p.to_numpy()
    return np.concatenate([x, z]).astype(np.uint8)


def _solve_gf2(A: np.ndarray, b: np.ndarray) -> Optional[np.ndarray]:
    A = A.copy() % 2
    b = b.copy() % 2
    m, n = A.shape
    piv_cols, r = [], 0
    for c in range(n):
        rows = [i for i in range(r, m) if A[i, c]]
        if not rows:
            continue
        A[[r, rows[0]]] = A[[rows[0], r]]
        b[[r, rows[0]]] = b[[rows[0], r]]
        for i in range(m):
            if i != r and A[i, c]:
                A[i] ^= A[r]
                b[i] ^= b[r]
        piv_cols.append(c)
        r += 1
        if r == m:
            break
    if any(b[i] for i in range(r, m)):
        return None
    x = np.zeros(n, dtype=np.uint8)
    for i, c in enumerate(piv_cols):
        x[c] = b[i]
    return x


def pure_errors(code: BlockCode) -> List[stim.PauliString]:
    """e_i anticommuting with stabilizer i only, commuting with all logicals [derived, GF(2)].

    WHY these constraints: e_i is the Pauli the program feeds forward in round 0 to reset a
    random stabilizer's eigenvalue to +1. It must anticommute with stabilizer i (so it flips
    that one syndrome) and commute with every other stabilizer (so it disturbs no other
    syndrome) and with every logical (so the correction is a pure gauge move that never touches
    the encoded state). Those conditions are linear over GF(2) in the symplectic representation,
    so a solution always exists when the generators are independent."""
    n = code.n
    rows = code.stabilizers + code.logical_x + code.logical_z
    # Symplectic (mod-2) inner product <e, r> = x_e . z_r + z_e . x_r is 0 iff e commutes with r.
    # Swapping each row's (x|z) halves turns that bilinear form into a plain dot product acting on
    # the unknown e = [x_e | z_e], so a single GF(2) linear solve per stabilizer gives e_i.
    A = np.array([np.concatenate([_sym(r)[n:], _sym(r)[:n]]) for r in rows], dtype=np.uint8)
    out = []
    for i in range(len(code.stabilizers)):
        b = np.zeros(len(rows), dtype=np.uint8)
        b[i] = 1
        e = _solve_gf2(A, b)
        if e is None:
            raise ValueError(f"{code.name}: no pure error for stabilizer {i}")
        out.append(stim.PauliString.from_numpy(xs=e[:n].astype(bool), zs=e[n:].astype(bool)))
    return out


def min_weight_rep(op: stim.PauliString, stabs: List[stim.PauliString],
                   pure: Optional[str] = None) -> stim.PauliString:
    """Minimum-weight stabilizer-equivalent representative (exhaustive over the group).
    Valid only because the frame is corrected to +1 for every stabilizer (module docstring).

    WHY minimum weight AND why the frame must be +1: a logical rotation exp(-i phi P) is driven
    by a physical Pauli string P that represents the logical operator. Any stabilizer multiple of
    P is the SAME logical operator, but it is a DIFFERENT physical gate (fewer/more qubits, and a
    different overall sign). Minimum weight is chosen so the gadget touches the fewest qubits
    (cheapest, least fault-exposed). The sign matters: on the +1 stabilizer frame set up in round
    0, every representative carries sign +1 on the code space, so exp(-i phi P) applies the
    intended angle. Without that frame, a representative could carry sign -1 on some shots, which
    would flip phi -> -phi and silently run the wrong rotation [derived]. pure="Z" restricts the
    search to pure-Z strings, needed so the destructive Z readout can reconstruct Zbar."""
    best = None
    for bits in itertools.product((0, 1), repeat=len(stabs)):
        p = op.copy()
        for b, s in zip(bits, stabs):
            if b:
                p *= s
        if pure and any(p[i] not in (0, {"X": 1, "Z": 3}[pure]) for i in range(len(p))):
            continue
        if best is None or p.weight < best.weight:
            best = p
    if best is None:
        raise ValueError("no representative of the requested form")
    return best


# --------------------------------------------------------------------------- #
# Encoded program
# --------------------------------------------------------------------------- #
@dataclass
class EncodedTFIM:
    """An encoded TFIM program for `code` on an Lx x Ly logical lattice."""

    code: BlockCode
    Lx: int
    Ly: int
    boundary: str
    J: float
    h: float
    dt: float
    theta: float

    def __post_init__(self) -> None:
        self.k = self.Lx * self.Ly
        kb = self.code.k
        self.n_blocks = -(-self.k // kb)
        self.nb = self.code.n
        self.n_data = self.n_blocks * self.nb
        self.A, self.F = self.n_data, self.n_data + 1
        self.bonds = square_bonds(self.Lx, self.Ly, self.boundary)
        self.pe = pure_errors(self.code)
        # global stabilizers (with their CNOT orders) and per-logical operators
        self.stabs, self.orders, self.errs = [], [], []
        for blk in range(self.n_blocks):
            for s, o, e in zip(self.code.stabilizers, self.code.orders, self.pe):
                self.stabs.append(self._lift(s, blk))
                self.orders.append([blk * self.nb + q for q in o])
                self.errs.append(self._lift(e, blk))
        self.lx = [self._lift(self.code.logical_x[l % kb], l // kb) for l in range(self.k)]
        self.lz = [self._lift(self.code.logical_z[l % kb], l // kb) for l in range(self.k)]

    @property
    def n_phys(self) -> int:
        return self.n_data + 2

    def _lift(self, p: stim.PauliString, blk: int) -> stim.PauliString:
        out = stim.PauliString(self.n_data)
        for i in range(len(p)):
            out[blk * self.nb + i] = p[i]
        out.sign = p.sign
        return out

    def _block_stabs(self, blocks: Sequence[int]) -> List[stim.PauliString]:
        nst = len(self.code.stabilizers)
        return [self.stabs[b * nst + i] for b in blocks for i in range(nst)]

    def _blocks_of(self, *ls) -> List[int]:
        return sorted({l // self.code.k for l in ls})

    # representatives (cached; exhaustive search over the involved blocks' stabilizer group)
    def _cached(self, key, fn):
        cache = self.__dict__.setdefault("_rep_cache", {})
        if key not in cache:
            cache[key] = fn()
        return cache[key]

    def rep_x(self, l):
        return self._cached(("x", l), lambda: min_weight_rep(self.lx[l], self._block_stabs(self._blocks_of(l))))

    def rep_y(self, l):
        def f():
            # Ybar = i Xbar Zbar: the logical Y used by the ry(theta) prep. Multiplying the two
            # commuting logical strings and the i phase yields a Hermitian (sign +-1) Pauli, which
            # rotation() requires; min_weight_rep then picks its cheapest +1-frame representative.
            y = self.lx[l] * self.lz[l]
            y *= 1j                                # Ybar = i Xbar Zbar (Hermitian, sign +-1)
            return min_weight_rep(y, self._block_stabs(self._blocks_of(l)))
        return self._cached(("y", l), f)

    def rep_zz(self, a, b):
        # Zbar_a Zbar_b drives the logical bond exp(+i J dt Zbar Zbar). On Iceberg this reduces to
        # a weight-2 string (one native ZZPhase); on the d>=3 codes it is weight 6 (a parity gadget).
        return self._cached(("zz", a, b), lambda: min_weight_rep(
            self.lz[a] * self.lz[b], self._block_stabs(self._blocks_of(a, b))))

    def readout_z(self, l):
        return self._cached(("rz", l), lambda: min_weight_rep(
            self.lz[l], self._block_stabs(self._blocks_of(l)), pure="Z"))

    def readout_x(self, l):
        return self._cached(("rx", l), lambda: min_weight_rep(
            self.lx[l], self._block_stabs(self._blocks_of(l)), pure="X"))

    # ------------------------------------------------------------------ segments
    def _basis_in(self, c: Circuit, q: int, p: int) -> None:      # map P -> Z
        if p == 1:
            c.H(q)
        elif p == 2:
            c.Sdg(q)
            c.H(q)

    def _basis_out(self, c: Circuit, q: int, p: int) -> None:
        if p == 1:
            c.H(q)
        elif p == 2:
            c.H(q)
            c.S(q)

    def _interleave(self, qs: List[int]) -> List[int]:
        # Order the parity-gadget CNOTs so the support is woven across blocks round-robin. WHY:
        # a single fault on the ancilla mid-gadget propagates back onto the CNOTs already applied,
        # i.e. onto a *prefix* of this order. Interleaving guarantees no proper prefix forms a
        # logical operator of any one block, so such a fault stays detectable [derived].
        by_blk: Dict[int, List[int]] = {}
        for q in qs:
            by_blk.setdefault(q // self.nb, []).append(q)
        cols = list(by_blk.values())
        return [c[i] for i in range(max(map(len, cols))) for c in cols if i < len(c)]

    def rotation(self, P: stim.PauliString, phi: float) -> Tuple[Circuit, bool]:
        """exp(-i phi P). Returns (segment, uses_ancilla).

        Two forms, selected by the weight of P (the WHY behind the three-way physics result):
          weight 2 -> basis-change the support, one ZZPhase (Iceberg's native two-qubit gate),
            undo. No ancilla, so a post-gate fault can leave the gate's own weight-2 generator,
            which is a logical operator the code cannot see.
          weight > 2 -> parity gadget: basis-change, CNOT the (interleaved) support onto ancilla
            A, Rz(2 phi/pi) on A, uncompute, undo basis change. The caller then measures A (a
            detector that must read 0) and resets it.
        In BOTH forms the undetectable residual sits right at this rotation, not in the code, so
        it is independent of code distance [derived] (see undetected_logical)."""
        if P.sign not in (1, -1):
            raise ValueError("rotation generator must be Hermitian")
        # Fold the representative's +-1 sign into the angle: exp(-i phi (-P)) = exp(-i (-phi) P).
        # Because the frame is +1 on the code space (min_weight_rep docstring), this sign is the
        # intended one, so no spurious angle flip reaches the logical state [derived].
        phi = phi * float(P.sign.real)
        sup = _support(P)
        c = Circuit(self.n_phys)
        for q in sup:
            self._basis_in(c, q, P[q])
        if len(sup) == 2:
            c.ZZPhase(2 * phi / np.pi, sup[0], sup[1])
            anc = False
        else:
            order = self._interleave(sup)
            for q in order:
                c.CX(q, self.A)
            c.Rz(2 * phi / np.pi, self.A)
            for q in reversed(order):
                c.CX(q, self.A)
            anc = True
        for q in sup:
            self._basis_out(c, q, P[q])
        return c, anc

    def stabilizer_segment(self, i: int) -> Circuit:
        """Flagged parity measurement of stabilizer i onto A (flag F for weight >= 3).

        The stabilizer's X/Y components are basis-changed to Z so the whole generator is read as
        a Z-parity on ancilla A. For weight >= 3 a single flag qubit F (Chao-Reichardt placement:
        the F-A CNOTs bracket the data CNOTs at positions 0 and w-2) catches the hook errors where
        one ancilla fault would otherwise spread to a weight-2 data error and masquerade as a
        correctable single fault; F reading 1 is a detector [established pattern]."""
        P, order = self.stabs[i], self.orders[i]
        A, F = self.A, self.F
        c = Circuit(self.n_phys)
        w = len(order)
        flagged = w >= 3
        for q in order:
            self._basis_in(c, q, P[q])
        if flagged:
            c.H(F)
        for idx, q in enumerate(order):
            c.CX(q, A)
            if flagged and idx in (0, w - 2):
                c.CX(F, A)
        if flagged:
            c.H(F)
        for q in order:
            self._basis_out(c, q, P[q])
        return c

    # ------------------------------------------------------------------ schedule
    def schedule(self, n_steps: int, basis: str = "Z") -> "Schedule":
        """The program as an ordered item list (see Schedule).

        The schedule is backend-agnostic ON PURPOSE: this single object is replayed by local-sim,
        imaged into Stim, and generated into a Guppy/Selene program. Keeping one source of truth
        means the three forms can only ever disagree on noise semantics, never on the circuit, so
        the Stim fault-tolerance claims apply to exactly what local-sim and Selene execute."""
        sch = Schedule(self.n_phys)
        if basis == "X":
            sch.basis_prep = list(range(self.n_data))
        nst = len(self.stabs)
        det_pure = {"Z": 3, "X": 1}[basis]

        def deterministic(i):
            # A stabilizer is deterministic in the prep basis iff it is a pure-basis Pauli on the
            # data (all Z for Z-prep |0^n>, all X for X-prep |+^n>): then |prep> is its +1
            # eigenstate and its outcome is a true detector. Mixed-type stabilizers have random
            # round-0 outcomes and instead need the frame correction below.
            P = self.stabs[i]
            return all(P[q] in (0, det_pure) for q in range(self.n_data))

        def syn_round(r):
            for i in range(nst):
                sch.unitary(self.stabilizer_segment(i), "syn")
                ka = sch.measure(self.A, f"r{r}s{i}")
                flagged = len(self.orders[i]) >= 3
                if flagged:
                    kf = sch.measure(self.F, f"r{r}f{i}")
                    sch.detect([kf])
                if r == 0 and not deterministic(i):
                    # Round 0 only: the random-sign stabilizers are fixed to +1 by feeding forward
                    # their pure error when they read -1. After this ALL stabilizers are +1, which
                    # is the precondition that makes min_weight_rep's signed representatives valid.
                    sch.correct(ka, self.errs[i])       # feedforward frame -> +1
                else:
                    # Every later round, and the deterministic stabilizers in round 0, are
                    # detectors: a +1 frame means a flip signals a fault and the shot is discarded.
                    sch.detect([ka])
                sch.reset(self.A)
                if flagged:
                    sch.reset(self.F)
            sch.idle(list(range(self.n_data)))

        def rot(P, phi, tag):
            seg, anc = self.rotation(P, phi)
            sch.unitary(seg, "rot")
            if anc:
                # Parity-gadget ancilla must return to 0; a 1 means a fault entered the gadget,
                # so this measurement is a detector that discards the shot.
                ka = sch.measure(self.A, f"{tag}a")
                sch.detect([ka])
                sch.reset(self.A)

        syn_round(0)
        for l in range(self.k):
            rot(self.rep_y(l), self.theta / 2, f"p{l}")
        phx, phz = -self.h * self.dt / 2, -self.J * self.dt
        for s in range(1, n_steps + 1):
            # Circuit-order Strang step (X half / ZZ / X half), matching src/compare.py. The
            # symmetric split is second-order accurate in dt; this exact ordering is the one the
            # published H2 circuits use at h*dt = 0.5, so transparency can be checked against them.
            for l in range(self.k):
                rot(self.rep_x(l), phx, f"s{s}x{l}")
            for (a, b) in self.bonds:
                rot(self.rep_zz(a, b), phz, f"s{s}z{a}_{b}")
            for l in range(self.k):
                rot(self.rep_x(l), phx, f"s{s}X{l}")
            sch.idle(list(range(self.n_data)))
            syn_round(s)
        # readout
        keys = [sch.measure(q, f"d{q}", readout_basis=basis) for q in range(self.n_data)]
        for i in range(nst):
            # Only pure-basis stabilizers can be reconstructed from the single-basis destructive
            # readout; their parity is a final detector that closes out the last syndrome round.
            if deterministic(i):
                sch.detect([keys[q] for q in _support(self.stabs[i])])
        # Logical Zbar (or Xbar) read from a pure-basis min-weight representative: the frame-+1
        # guarantee makes the parity of these data bits the signed logical eigenvalue.
        reps = [self.readout_z(l) if basis == "Z" else self.readout_x(l) for l in range(self.k)]
        sch.logicals = [[keys[q] for q in _support(r)] for r in reps]
        return sch


@dataclass
class Schedule:
    """Ordered program items shared by local-sim, Stim and the Selene code generator.

    items: ("U", Circuit, cls) | ("M", qubit, key, basis) | ("R", qubit) |
           ("C", key, PauliString)  feedforward: apply the Pauli if measurement `key` read 1 |
           ("D", [keys])  detector: XOR of the keys must be 0 (else the shot is discarded) |
           ("I", [qubits]) idle-noise point.
    """

    n: int
    items: list = field(default_factory=list)
    basis_prep: List[int] = field(default_factory=list)   # data qubits prepared in |+> (X image)
    logicals: List[List[str]] = field(default_factory=list)

    def unitary(self, c, cls):
        self.items.append(("U", c, cls))

    def measure(self, q, key, readout_basis="Z"):
        self.items.append(("M", q, key, readout_basis))
        return key

    def reset(self, q):
        self.items.append(("R", q))

    def correct(self, key, P):
        self.items.append(("C", key, P))

    def detect(self, keys):
        self.items.append(("D", list(keys)))

    def idle(self, qs):
        self.items.append(("I", list(qs)))


# --------------------------------------------------------------------------- #
# Stim image (verification) and the measured undetected-logical accounting
# --------------------------------------------------------------------------- #
@dataclass
class NoiseRates:
    # [ASSUMED generic depolarizing model, never H2-calibrated]. Every noisy number produced
    # with these rates is a classical prediction under this model, NOT an H2 hardware result.
    # Typical scan choice is p1 = pm = p_init = p2/10 (see docs/encoded_tfim.md).
    p2: float = 0.0        # depolarizing prob after each 2-qubit gate
    p1: float = 0.0        # depolarizing prob after each 1-qubit gate
    pm: float = 0.0        # bit-flip prob on each measurement
    p_init: float = 0.0    # X-error prob after each reset/init
    p_idle: float = 0.0    # depolarizing prob at each idle-noise point
    # Sensitivity options (Stim accounting only; 0 = the Part B baseline). These probe how the
    # "encoding helps" conclusion survives H2-like channels; the quantities they model (ZZ
    # fraction, coherent over-rotation) must be MEASURED from H2 before any machine claim.
    zz_bias: float = 0.0   # fraction eta of each 2q error that is Z(x)Z; the rest stays uniform.
                           # [inferred] A ZZ error on a logical-ZZ gate IS that logical operator,
                           # so no code here can detect it: this is what can reverse the advantage.
    overrot: float = 0.0   # Pauli-twirled coherent over-rotation: every rotation applies its own
                           # generator with this probability (= sin^2 eps). A real coherent error
                           # can accumulate faster than this twirled stand-in [inferred].


# Clifford images of the rotation angles, used ONLY in mode="clifford" for the Stim<->execution
# consistency check at Clifford-angle instances. Half-turn convention: exp(-i pi alpha/2 P), so
# alpha = 0.5 -> sqrt(P), 1.0 -> P, 1.5 -> sqrt(P)^dagger. In the default "identity" mode these
# tables are unused because a Pauli rotation is the identity for Pauli-fault propagation [derived].
_CLIFF_RZ = {0.0: [], 0.5: ["S"], 1.0: ["Z"], 1.5: ["S_DAG"]}
_CLIFF_ZZ = {0.0: [], 0.5: ["SQRT_ZZ"], 1.0: ["SQRT_ZZ", "SQRT_ZZ"], 1.5: ["SQRT_ZZ_DAG"]}


def _cliff(table, alpha):
    r = alpha % 2.0                       # exp(-i pi alpha/2 P) up to global phase, period 2
    q = round(r * 2) / 2 % 2.0            # snap to the nearest quarter-turn (Clifford) angle
    q = round(r * 2) / 2 % 2.0
    if abs(r - q) > 1e-9 and abs(r - q - 2) > 1e-9:
        raise ValueError(f"non-Clifford angle {alpha}")
    return table[q]


def to_stim(sch: Schedule, noise: NoiseRates, mode: str = "identity") -> stim.Circuit:
    """Stim image of a schedule. Every noise instruction carries a tag 'cls:item:cmd' that is
    identical between the Z and X images, so error locations can be matched across them."""
    c = stim.Circuit()
    rec: Dict[str, int] = {}
    nmeas = 0

    def tgt(key):
        return stim.target_rec(rec[key] - nmeas)

    c.append("R", list(range(sch.n)))
    if sch.basis_prep:
        c.append("H", sch.basis_prep)
    for it_i, it in enumerate(sch.items):
        kind = it[0]
        if kind == "U":
            seg, cls = it[1], it[2]
            for ci, cmd in enumerate(seg.get_commands()):
                typ = cmd.op.type
                qs = [q.index[0] for q in cmd.qubits]
                sub = {OpType.CX: "cx", OpType.ZZPhase: "zz"}.get(typ, "1q")
                tag = f"{cls}-{sub}:{it_i}:{ci}"
                if typ == OpType.H:
                    c.append("H", qs)
                elif typ == OpType.S:
                    c.append("S", qs)
                elif typ == OpType.Sdg:
                    c.append("S_DAG", qs)
                elif typ == OpType.CX:
                    c.append("CX", qs)
                elif typ == OpType.Rz:
                    # A Pauli fault commutes through a Pauli rotation unchanged (only phi's sign
                    # flips), so for fault propagation the rotation is exactly the identity: emit
                    # nothing in "identity" mode. In "clifford" mode replace it by its Clifford
                    # image so the tableau check sees the real unitary.
                    if mode == "clifford":
                        for g in _cliff(_CLIFF_RZ, float(cmd.op.params[0])):
                            c.append(g, qs)
                elif typ == OpType.ZZPhase:
                    # Same reasoning as Rz: identity for Pauli-fault propagation [derived].
                    if mode == "clifford":
                        for g in _cliff(_CLIFF_ZZ, float(cmd.op.params[0])):
                            c.append(g, qs)
                else:
                    raise ValueError(f"unexpected op {typ}")
                if noise.overrot and typ == OpType.ZZPhase:
                    # Twirled coherent over-rotation on a native ZZ gate: with prob overrot apply
                    # the gate's own ZZ generator (component index 15 of PAULI_CHANNEL_2 = ZZ),
                    # which is a logical operator -> an undetectable logical fault at the gadget.
                    c.append(stim.CircuitInstruction("PAULI_CHANNEL_2", qs, [0.0] * 14 + [noise.overrot],
                                                     tag=f"overrot:{it_i}:{ci}"))
                elif noise.overrot and typ == OpType.Rz and cls.startswith("rot"):
                    gen = "X_ERROR" if cls == "rotx" else "Z_ERROR"    # bare Rx placeholder -> X
                    c.append(stim.CircuitInstruction(gen, qs, [noise.overrot], tag=f"overrot:{it_i}:{ci}"))
                if len(qs) == 2 and noise.p2 and noise.zz_bias:
                    # Biased 2q channel: weight (1-eta) uniformly over the 14 non-ZZ components and
                    # add eta into the ZZ component. Models an H2-like gate whose dominant error is
                    # along its own ZZ axis [inferred].
                    u = noise.p2 * (1 - noise.zz_bias) / 15
                    c.append(stim.CircuitInstruction("PAULI_CHANNEL_2", qs,
                                                     [u] * 14 + [u + noise.p2 * noise.zz_bias], tag=tag))
                elif len(qs) == 2 and noise.p2:
                    c.append(stim.CircuitInstruction("DEPOLARIZE2", qs, [noise.p2], tag=tag))
                elif len(qs) == 1 and noise.p1:
                    c.append(stim.CircuitInstruction("DEPOLARIZE1", qs, [noise.p1], tag=tag))
        elif kind == "M":
            _, q, key, rb = it
            if rb == "X":
                c.append("H", [q])
            if noise.pm:
                c.append(stim.CircuitInstruction("X_ERROR", [q], [noise.pm], tag=f"meas:{it_i}:0"))
            c.append("M", [q])
            rec[key] = nmeas
            nmeas += 1
        elif kind == "R":
            c.append("R", [it[1]])
            if noise.p_init:
                c.append(stim.CircuitInstruction("X_ERROR", [it[1]], [noise.p_init], tag=f"reset:{it_i}:0"))
        elif kind == "C":
            # Frame correction as a classically-controlled Pauli (CX/CY/CZ off the measurement
            # record). In the Stim image this is a noiseless Pauli-frame update; Selene instead
            # runs it as physical x/y/z gates and charges p_1q on them [stated difference].
            _, key, P = it
            for q in _support(P):
                c.append({1: "CX", 2: "CY", 3: "CZ"}[P[q]], [tgt(key), q])
        elif kind == "D":
            c.append("DETECTOR", [tgt(k) for k in it[1]])
        elif kind == "I":
            if noise.p_idle:
                c.append(stim.CircuitInstruction("DEPOLARIZE1", it[1], [noise.p_idle], tag=f"idle:{it_i}:0"))
    for li, keys in enumerate(sch.logicals):
        c.append("OBSERVABLE_INCLUDE", [tgt(k) for k in keys], li)
    return c


_COMPONENT = {"DEPOLARIZE2": 1 / 15, "DEPOLARIZE1": 1 / 3, "X_ERROR": 1.0, "Z_ERROR": 1.0}


def _component_prob(loc) -> float:
    """Probability of the single Pauli component behind an explained error location."""
    it = loc.instruction_targets
    if it.gate != "PAULI_CHANNEL_2":
        return float(it.args[0]) * _COMPONENT[it.gate]
    qa, qb = (t.gate_target.value for t in it.targets_in_range)
    lab = {t.gate_target.value: t.gate_target.pauli_type for t in loc.flipped_pauli_product}
    code = {"I": 0, "X": 1, "Y": 2, "Z": 3}
    return float(it.args[4 * code[lab.get(qa, "I")] + code[lab.get(qb, "I")] - 1])


def undetected_logical(prog, n_steps: int, noise: NoiseRates) -> Dict[str, float]:
    """MEASURED first-order probability that one fault flips a logical observable while firing
    no detector, summed over distinct fault components (gate location + Pauli), union over the
    Z and X images (a component flipping both is counted once). Returned per fault class."""
    seen: Dict[Tuple[str, int, str], Tuple[str, float]] = {}
    for basis in ("Z", "X"):
        circ = to_stim(prog.schedule(n_steps, basis), noise)
        dem = circ.detector_error_model(decompose_errors=False, approximate_disjoint_errors=True)
        bad = stim.DetectorErrorModel()
        for inst in dem.flattened():
            if inst.type != "error":
                continue
            tg = inst.targets_copy()
            if not any(t.is_relative_detector_id() for t in tg) and any(t.is_logical_observable_id() for t in tg):
                bad.append(inst)
        if not len(bad):
            continue
        for e in circ.explain_detector_error_model_errors(dem_filter=bad, reduce_to_one_representative_error=False):
            for loc in e.circuit_error_locations:
                it = loc.instruction_targets
                key = (loc.noise_tag, it.target_range_start, str(loc.flipped_pauli_product))
                p = _component_prob(loc)
                seen[key] = (loc.noise_tag.split(":")[0], p)
    out: Dict[str, float] = {}
    for cls, p in seen.values():
        out[cls] = out.get(cls, 0.0) + p
    out["total"] = sum(v for k, v in out.items())
    return out


def undetected_rate_per_step(prog, noise: NoiseRates, steps=(1, 2, 3)) -> Dict[str, float]:
    """Slope of the measured undetected-logical probability vs Trotter steps (per step)."""
    rows = [undetected_logical(prog, s, noise) for s in steps]
    classes = sorted({k for r in rows for k in r})
    out = {c: float(np.polyfit(steps, [r.get(c, 0.0) for r in rows], 1)[0]) for c in classes}
    return {c: (v if abs(v) > 1e-15 else 0.0) for c, v in out.items()}     # drop fit round-off


def detected_rate_per_step(prog, noise: NoiseRates, steps=(1, 2, 3)) -> float:
    """MEASURED first-order probability per Trotter step that a fault fires >= 1 detector in the
    executed (Z-prep) program: sum of DEM mechanism probabilities with a detector, slope over
    steps. exp(-rate * steps) is the first-order acceptance prediction where execution is not
    possible (budget-size lattices)."""
    tot = []
    for s in steps:
        dem = to_stim(prog.schedule(s, "Z"), noise).detector_error_model(
            decompose_errors=False, approximate_disjoint_errors=True)
        tot.append(sum(inst.args_copy()[0] for inst in dem.flattened() if inst.type == "error"
                       and any(t.is_relative_detector_id() for t in inst.targets_copy())))
    return float(np.polyfit(steps, tot, 1)[0])


def detected_total(prog, noise: NoiseRates, n_steps: int) -> float:
    """First-order total detection probability of the whole executed program (prep included);
    exp(-value) is the first-order acceptance prediction."""
    dem = to_stim(prog.schedule(n_steps, "Z"), noise).detector_error_model(
        decompose_errors=False, approximate_disjoint_errors=True)
    return float(sum(inst.args_copy()[0] for inst in dem.flattened() if inst.type == "error"
                     and any(t.is_relative_detector_id() for t in inst.targets_copy())))


def gate_counts(prog, n_steps: int = 1) -> Dict[str, int]:
    """Physical operation counts per Trotter step (difference of n+1 and n step programs)."""
    def count(s):
        sch = prog.schedule(s, "Z")
        c = {"2q": 0, "1q": 0, "meas": 0}
        for it in sch.items:
            if it[0] == "U":
                for cmd in it[1].get_commands():
                    c["2q" if len(cmd.qubits) == 2 else "1q"] += 1
            elif it[0] == "M":
                c["meas"] += 1
        return c
    a, b = count(n_steps), count(n_steps + 1)
    return {k: b[k] - a[k] for k in a}


# --------------------------------------------------------------------------- #
# Bare reference with the same accounting (every fault is unprotected)
# --------------------------------------------------------------------------- #
@dataclass
class BareTFIM:
    """The same logical evolution on k bare qubits: ry prep, Rx field, ZZPhase bonds."""

    Lx: int
    Ly: int
    boundary: str
    J: float
    h: float
    dt: float
    theta: float

    def __post_init__(self):
        self.k = self.Lx * self.Ly
        self.bonds = square_bonds(self.Lx, self.Ly, self.boundary)

    def schedule(self, n_steps: int, basis: str = "Z") -> Schedule:
        sch = Schedule(self.k)
        if basis == "X":
            sch.basis_prep = list(range(self.k))
        c = Circuit(self.k)
        for q in range(self.k):                       # ry as a 1-qubit location (identity in Stim)
            c.Rz(0.0, q)
        sch.unitary(c, "rot1q")
        phx, phz = -self.h * self.dt / 2, -self.J * self.dt
        for _ in range(n_steps):
            t = Circuit(self.k)
            fx = Circuit(self.k)
            for q in range(self.k):
                fx.Rz(0.0, q)                         # stands for Rx(2 phx/pi): a 1q location
            sch.unitary(fx, "rotx")
            zz = Circuit(self.k)
            for a, b in self.bonds:
                zz.ZZPhase(2 * phz / np.pi, a, b)
            sch.unitary(zz, "rot")
            sch.unitary(fx.copy(), "rotx")
            sch.idle(list(range(self.k)))
        keys = [sch.measure(q, f"d{q}", readout_basis=basis) for q in range(self.k)]
        sch.logicals = [[k] for k in keys]
        return sch


# --------------------------------------------------------------------------- #
# Execution: local-sim interpreter and exact zero-noise evaluation
# --------------------------------------------------------------------------- #
from src.backends_qc import _CX, _H, _PAULI, StateVector  # noqa: E402

_S = np.diag([1, 1j])


def _apply_segment(sv: StateVector, seg: Circuit, rng, noise: NoiseRates) -> None:
    def pauli_noise(qs, p):
        if p and rng.random() < p:
            while True:
                draw = [("IXYZ")[rng.integers(4)] for _ in qs]
                if any(x != "I" for x in draw):
                    break
            for q, x in zip(qs, draw):
                if x != "I":
                    sv.apply1(_PAULI[x], q)

    for cmd in seg.get_commands():
        typ = cmd.op.type
        qs = [q.index[0] for q in cmd.qubits]
        if typ == OpType.H:
            sv.apply1(_H, qs[0])
        elif typ == OpType.S:
            sv.apply1(_S, qs[0])
        elif typ == OpType.Sdg:
            sv.apply1(_S.conj(), qs[0])
        elif typ == OpType.Rz:
            a = np.pi * float(cmd.op.params[0]) / 2
            sv.apply1(np.diag([np.exp(-1j * a), np.exp(1j * a)]), qs[0])
        elif typ == OpType.CX:
            sv.apply2(_CX, qs[0], qs[1])
        elif typ == OpType.ZZPhase:
            a = np.pi * float(cmd.op.params[0]) / 2
            sv.apply2(np.diag(np.exp(-1j * a * np.array([1, -1, -1, 1]))), qs[0], qs[1])
        else:
            raise ValueError(f"local-sim: unsupported op {typ}")
        pauli_noise(qs, noise.p2 if len(qs) == 2 else noise.p1)


def run_local(sch: Schedule, noise: NoiseRates, rng, exact_final: bool = False):
    """One shot of a schedule. Returns (accepted, logical +-1 array) or, with exact_final, the
    final state vector (noiseless use only) after the program up to readout."""
    sv = StateVector(sch.n, rng)
    meas: Dict[str, int] = {}
    ok = True
    for it in sch.items:
        kind = it[0]
        if kind == "U":
            _apply_segment(sv, it[1], rng, noise)
        elif kind == "M":
            _, q, key, rb = it
            if key.startswith("d") and exact_final:
                break                                   # stop before the destructive readout
            bit = sv.measure(q)
            if noise.pm and rng.random() < noise.pm:
                bit ^= 1
            meas[key] = bit
        elif kind == "R":
            sv.reset(it[1])
            if noise.p_init and rng.random() < noise.p_init:
                sv.apply1(_PAULI["X"], it[1])
        elif kind == "C":
            if meas[it[1]]:
                P = it[2]
                for q in _support(P):
                    sv.apply1(_PAULI["IXYZ"[P[q]]], q)
        elif kind == "D":
            if sum(meas[k] for k in it[1]) % 2:
                ok = False
        elif kind == "I":
            if noise.p_idle:
                for q in it[1]:
                    if rng.random() < noise.p_idle:
                        sv.apply1(_PAULI["XYZ"[rng.integers(3)]], q)
    if exact_final:
        return sv
    vals = np.array([1 - 2 * (sum(meas[k] for k in keys) % 2) for keys in sch.logicals], dtype=np.int8)
    return ok, vals


def exact_logical_z2(prog: "EncodedTFIM", n_steps: int, seed: int = 0, max_spins: int = 24) -> float:
    """Noiseless, sampling-free logical Z2 from the final state (transparency check)."""
    check_physical_ceiling(prog.n_phys, max_spins)
    sch = prog.schedule(n_steps, "Z")
    sv = run_local(sch, NoiseRates(), np.random.default_rng(seed), exact_final=True)
    probs = np.abs(sv.flat()) ** 2
    n = sch.n
    idx = np.arange(1 << n)
    M = np.zeros(1 << n)
    for l in range(prog.k):
        par = np.zeros(1 << n, dtype=np.int64)
        for q in _support(prog.readout_z(l)):
            par ^= (idx >> (n - 1 - q)) & 1
        M += 1 - 2 * par
    return float(np.sum(probs * M ** 2)) / prog.k ** 2


def stim_exact_z2(prog: "EncodedTFIM", n_steps: int, seed: int = 0) -> float:
    """Exact logical Z2 of the CLIFFORD-angle program via Stim's tableau simulator."""
    sch = prog.schedule(n_steps, "Z")
    cut = next(i for i, it in enumerate(sch.items) if it[0] == "M" and it[2].startswith("d"))
    head = Schedule(sch.n, sch.items[:cut])
    sim = stim.TableauSimulator(seed=seed)
    sim.do(to_stim(head, NoiseRates(), mode="clifford"))
    k = prog.k
    tot = float(k)
    reps = [prog.readout_z(l) for l in range(k)]
    for a in range(k):
        for b in range(k):
            if a != b:
                ps = stim.PauliString(sch.n)
                for q in set(_support(reps[a])) ^ set(_support(reps[b])):
                    ps[q] = "Z"
                tot += sim.peek_observable_expectation(ps)
    return tot / k ** 2


# --------------------------------------------------------------------------- #
# Selene: generated Guppy program (mid-circuit measurement + feedforward)
# --------------------------------------------------------------------------- #
_REG: Dict[str, List[Circuit]] = {}


def guppy_program(sch: Schedule, tag: str):
    """Generate a Guppy module for the schedule and return its `main`. Every measurement is
    mid-circuit (project_z + read); frame corrections and detector checks are evaluated in the
    program, and once a detector fires every later quantum operation is skipped."""
    import importlib.util
    import os
    import tempfile

    segs = [it[1] for it in sch.items if it[0] == "U"]
    _REG[tag] = segs
    keys = [it[2] for it in sch.items if it[0] == "M"]
    var = {k: f"m{i}" for i, k in enumerate(keys)}
    L = ["from guppylang import guppy",
         "from guppylang.std.builtins import array, result, comptime",
         "from guppylang.std.quantum import qubit, reset, discard_array, project_z, x, y, z, h",
         "from src.encoded_codes import _REG",
         f"_C = _REG[{tag!r}]"]
    for i in range(len(segs)):
        L.append(f"seg{i} = guppy.load_pytket('seg{i}_{tag}', _C[{i}])")
    L += ["", "@guppy", "def main() -> None:",
          f"    q = array(qubit() for _ in range({sch.n}))",
          "    ok = True"]
    L += [f"    {v} = False" for v in var.values()]
    if sch.basis_prep:
        raise ValueError("only the executed Z-prep program runs on selene")
    si = 0
    for it in sch.items:
        kind = it[0]
        if kind == "U":
            L += ["    if ok:", f"        seg{si}(q)"]
            si += 1
        elif kind == "M":
            q, key = it[1], it[2]
            if key.startswith("d"):
                L.append(f"    {var[key]} = project_z(q[{q}]).read()")   # readout always runs
                L.append(f"    result('d', {var[key]})")
            else:
                L += ["    if ok:", f"        {var[key]} = project_z(q[{q}]).read()"]
        elif kind == "R":
            L += ["    if ok:", f"        reset(q[{it[1]}])"]
        elif kind == "C":
            P = it[2]
            body = [f"            {'xyz'[P[q] - 1]}(q[{q}])" for q in _support(P)]
            L += ["    if ok:", f"        if {var[it[1]]}:"] + body
        elif kind == "D":
            expr = " != ".join(var[k] for k in it[1]) if len(it[1]) > 1 else var[it[1][0]]
            if len(it[1]) > 2:                       # XOR chain for parity of many bits
                acc = var[it[1][0]]
                for k in it[1][1:]:
                    acc = f"({acc} != {var[k]})"
                expr = acc
            L += [f"    if {expr}:", "        ok = False"]
    L += ["    result('accepted', ok)", "    discard_array(q)", ""]
    d = tempfile.mkdtemp(prefix="guppy_gen_")
    path = os.path.join(d, f"prog_{tag}.py")
    with open(path, "w") as fh:
        fh.write("\n".join(L))
    spec = importlib.util.spec_from_file_location(f"prog_{tag}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.main


def run_selene(prog: "EncodedTFIM", n_steps: int, shots: int, noise: NoiseRates, seed: int,
               max_spins: int, tag: Optional[str] = None, n_processes: int = 1):
    """Run on Selene (Quest). Returns list of (accepted, logical +-1 array)."""
    from selene_sim import DepolarizingErrorModel, Quest
    check_physical_ceiling(prog.n_phys, max_spins)
    if noise.p_idle:
        raise ValueError("selene's DepolarizingErrorModel has no idle term")
    sch = prog.schedule(n_steps, "Z")
    tag = tag or f"{prog.code.name.split('[')[0].replace('-', '')}_{n_steps}_{seed}_{abs(hash(id(sch)))}"
    main = guppy_program(sch, tag)
    em = DepolarizingErrorModel(random_seed=seed, p_1q=noise.p1, p_2q=noise.p2,
                                p_meas=noise.pm, p_init=noise.p_init)
    res = (main.emulator(n_qubits=sch.n).with_shots(shots).with_simulator(Quest())
           .with_seed(seed).with_error_model(em).with_n_processes(n_processes).run())
    dq = {int(it[2][1:]): i for i, it in enumerate([x for x in sch.items if x[0] == "M" and x[2].startswith("d")])}
    out = []
    for shot in res.results:
        bits = [int(v) for k, v in shot.entries if k == "d"]
        acc = bool([v for k, v in shot.entries if k == "accepted"][0])
        vals = np.array([1 - 2 * (sum(bits[dq[int(k[1:])]] for k in keys) % 2) for keys in sch.logicals],
                        dtype=np.int8)
        out.append((acc, vals))
    return out


def logical_pauli_table(prog: "EncodedTFIM", n_steps: int, seed: int = 0, max_spins: int = 24):
    """Stim <-> execution consistency on the WHOLE clean-run logical state (Clifford instance):
    for every logical Pauli product (4^k of them), the expectation from Stim's tableau and from
    local-sim's state vector. Returns (labels, stim_values, local_values)."""
    check_physical_ceiling(prog.n_phys, max_spins)
    sch = prog.schedule(n_steps, "Z")
    cut = next(i for i, it in enumerate(sch.items) if it[0] == "M" and it[2].startswith("d"))
    head = Schedule(sch.n, sch.items[:cut])
    sim = stim.TableauSimulator(seed=seed)
    sim.do(to_stim(head, NoiseRates(), mode="clifford"))
    psi = run_local(sch, NoiseRates(), np.random.default_rng(seed), exact_final=True).flat()
    n, labels, sv, lv = sch.n, [], [], []
    xs = [_pad(prog.lx[l], n) for l in range(prog.k)]
    zs = [_pad(prog.lz[l], n) for l in range(prog.k)]
    for word in itertools.product("IXYZ", repeat=prog.k):
        P = stim.PauliString(n)
        for l, c in enumerate(word):
            if c in "XY":
                P *= xs[l]
            if c in "ZY":
                P *= zs[l]
            if c == "Y":
                P *= 1j                       # Y = i X Z
        labels.append("".join(word))
        sv.append(sim.peek_observable_expectation(P) if P.sign in (1, -1) else np.nan)
        lv.append(float(np.real(np.vdot(psi, _apply_pauli(P, psi, n)))))
    return labels, np.array(sv, float), np.array(lv, float)


def _pad(p: stim.PauliString, n: int) -> stim.PauliString:
    out = stim.PauliString(n)
    for i in range(len(p)):
        out[i] = p[i]
    out.sign = p.sign
    return out


def _apply_pauli(P: stim.PauliString, psi: np.ndarray, n: int) -> np.ndarray:
    v = psi.reshape((2,) * n).copy()
    for q in range(n):
        if P[q]:
            v = np.moveaxis(np.tensordot(_PAULI["IXYZ"[P[q]]], v, axes=([1], [q])), 0, q)
    return complex(P.sign) * v.reshape(-1)
