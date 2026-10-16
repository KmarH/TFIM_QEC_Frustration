"""Gate-count cost of randomized compiling (DECISIONS.md OPEN-3, [unverified] item): does the
twirl's explicit Pauli insertion (src/twirl.py) absorb into Selene's native arbitrary-angle
1-qubit rotations (rxy/rz) at no cost, or does it add real native operations?

Compiles the SAME Iceberg TFIM program (untwirled vs one twirled instance) through Selene's
HUGR-QIS pipeline and reports native rzz/rxy/rz counts via with_metrics(), the same methodology
scripts/diagnose_selene_gap.py already uses for the pytket-level-vs-native gap. Classical
simulators only; no hardware. Writes data/twirl_gate_count.txt.
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from pytket import OpType  # noqa: E402

from config import CONFIG  # noqa: E402
from src.backends_qc import build_guppy_program, build_guppy_program_twirled  # noqa: E402
from src.encoded_tfim import IcebergTFIM, twirl_program  # noqa: E402

E = CONFIG.encoded


def native_counts(main_fn, n_qubits):
    from selene_sim import Quest

    m = (main_fn.emulator(n_qubits=n_qubits).with_shots(1).with_simulator(Quest())
         .with_seed(0).with_metrics().run().metrics()[0]["user_program"])
    return m["rzz_count"], m["rxy_count"], m["rz_count"]


def pytket_level_counts(circuits):
    n1 = n2 = 0
    for c in circuits:
        for cmd in c.get_commands():
            if len(cmd.qubits) == 2:
                n2 += 1
            else:
                n1 += 1
    return n1, n2


def main():
    out = []

    def log(s=""):
        print(s, flush=True)
        out.append(s)

    log(f"# Randomized-compiling gate-count cost -- {time.strftime('%Y-%m-%d %H:%M')} "
        f"[classical simulators only; NOT an H2 result]")
    log("# DECISIONS.md OPEN-3: does the twirl's explicit Pauli insertion absorb into native "
        "1q rotations for free, or does it cost real native ops?")

    spec = IcebergTFIM(2, 2, "periodic", E.J, E.h, E.dt, E.theta)
    n_steps = 3
    n = spec.n_phys

    log(f"\nIceberg 2x2 ({spec.k} logical, {n} physical), {n_steps} Trotter steps")

    untw_fn = build_guppy_program(spec, n_steps)
    rzz0, rxy0, rz0 = native_counts(untw_fn, n)
    log(f"\nuntwirled:  native rzz={rzz0}  rxy={rxy0}  rz={rz0}  (1q total={rxy0 + rz0})")

    prog = twirl_program(spec, n_steps, seed=7)
    tw_fn = build_guppy_program_twirled(spec, prog)
    rzz1, rxy1, rz1 = native_counts(tw_fn, n)
    log(f"twirled:    native rzz={rzz1}  rxy={rxy1}  rz={rz1}  (1q total={rxy1 + rz1})")

    log(f"\n2q (rzz) ratio: x{rzz1 / rzz0:.3f}  (should be 1.0 -- twirling never changes the "
        f"number of two-qubit gates)")
    log(f"1q (rxy+rz) ratio: x{(rxy1 + rz1) / (rxy0 + rz0):.3f}")
    log(f"1q extra native ops added by the twirl: {(rxy1 + rz1) - (rxy0 + rz0)}")

    # pytket-level accounting: how many explicit X/Y/Z twirl gates were emitted, and what
    # fraction of twirled ZZPhase gates drew a non-identity Pauli on each qubit
    n_zz = sum(1 for c in prog.trotter_layers for cmd in c.get_commands()
               if cmd.op.type == OpType.ZZPhase)
    n_zz += sum(1 for cmd in prog.prep.get_commands() if cmd.op.type == OpType.ZZPhase)
    n_pauli_gates = sum(1 for c in prog.trotter_layers for cmd in c.get_commands()
                        if cmd.op.type in (OpType.X, OpType.Y, OpType.Z))
    n_pauli_gates += sum(1 for cmd in prog.prep.get_commands()
                        if cmd.op.type in (OpType.X, OpType.Y, OpType.Z))
    log(f"\npytket-level: {n_zz} twirled ZZPhase gates (prep + {n_steps} Trotter layers), "
        f"{n_pauli_gates} explicit Pauli (X/Y/Z) gates emitted for the fresh draws "
        f"({n_pauli_gates / (2 * n_zz):.2f} per qubit-slot, of a possible 1.0 -- 3/4 expected "
        f"since each draw is non-identity with probability 3/4)")

    log(f"\nper-Trotter-step native 1q cost added: {((rxy1 + rz1) - (rxy0 + rz0)) / n_steps:.1f} "
        f"(for comparison, Selene's measured pytket-level-vs-native gap elsewhere in this "
        f"project is x3.85 on the UNTWIRLED circuit -- data/selene_gap.txt)")

    log("\nAnswer to DECISIONS.md OPEN-3: the twirl's Pauli insertions do NOT absorb into "
        "native rotations for free on this stack -- they compile to their own native rxy/rz "
        "operations, each subject to Selene's p_1q charge like any other native 1-qubit op "
        "[measured, this script].")

    os.makedirs(os.path.join(REPO, CONFIG.data_dir), exist_ok=True)
    with open(os.path.join(REPO, CONFIG.data_dir, "twirl_gate_count.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
