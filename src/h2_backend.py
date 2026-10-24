"""Running the H2 circuits: local emulator, Nexus syntax checker, Nexus emulator (handoff/13).

Four tiers, by what they cost, and the gate each one has:

  LE  H2-1LE / H2-2LE   offline, free, no login. `run_le`.
  SC  H2-1SC / H2-2SC   Nexus syntax checker: validates and quotes an HQC cost, spends nothing.
                        `syntax_check`. Pre-approved by the project lead (2026-10-17); it refuses
                        every other device name, so it can never be pointed at one that charges.
  E   H2-1E  / H2-2E    Nexus emulator, SPENDS HQC. `submit_nexus`: allow_hardware=True AND the
                        per-run approval token AND a positive max_cost_hqc AND an estimate under it.
  HW  H2-1   / H2-2     real hardware. Same gate, plus allow_real_hardware=True.

qnexus is imported only inside the SC/E functions, so importing this module (and every test of
the gates) never reaches the network. Nothing in the repo calls `submit_nexus`; that needs the
project lead's go, per run.

The LE has two caveats found in pytket-quantinuum 0.59.3 (docs/quantinuum_issues.md):
QI-2 it ignores `noisy_simulation` -- it builds pytket_pecos.Emulator with no error model, so it is
always noiseless -- hence `run_le(noise=...)` drives the same Emulator with a PECOS
DepolarizingErrorModel instead; and PECOS scales its p1/p2 by 3/2 and 5/4 (average -> total error),
so our rates (total Pauli-error probability, src.backends_qc.Noise) are pre-divided to match.
Every noisy LE number is a classical prediction under an ASSUMED model, not an H2 result.

Two differences from src.backends_qc's local-sim, found in review (review/16), that the user of a
noisy LE number must know:
  p1      is charged by PECOS on every COMPILED native one-qubit op, R1XY and Rz alike (a twirled
          2-site circuit: 272 native ops against 52 authored H gates [measured]); local-sim charges
          only the authored H and leaves twirl Paulis free. So at p1 > 0 the LE is much noisier
          than local-sim, and randomized compiling is NOT a no-op on it (QI-9). p2 and pm agree.
  p_init  is charged on the initial state here too (explicit Resets added, QI-11), as in local-sim.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from pytket import Bit, Circuit

from config import CONFIG
from src.backends import MemoryCeilingError
from src.backends_qc import NEXUS_APPROVAL, Noise, _nexus_preflight

LE_DEVICES = frozenset({"H2-1LE", "H2-2LE"})
SC_DEVICES = frozenset({"H2-1SC", "H2-2SC"})
E_DEVICES = frozenset({"H2-1E", "H2-2E"})
HW_DEVICES = frozenset({"H2-1", "H2-2"})

# anchored to the repo root, not the working directory, so a record is never lost to a cwd change
LEDGER = Path(__file__).resolve().parent.parent / "runs" / "nexus_ledger.jsonl"
TOKEN_ENV = "NEXUS_REFRESH_TOKEN"  # a refresh token in the environment, never in the repo


class DeviceRefused(PermissionError):
    """A device name outside the tier the called function is allowed to touch."""


class LEWidthError(MemoryCeilingError, MemoryError):
    """The local emulator is an exact state vector: refused above SCOPE §5's ceiling."""


def _ledger(entry: dict, path: Path | None = None) -> None:
    """Append one JSON line per Nexus interaction: the record of what was asked and what it cost."""
    p = Path(path) if path is not None else LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **entry}) + "\n")


def _ledger_check_writable(path: Path | None = None) -> None:
    p = Path(path) if path is not None else LEDGER
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8"):
        pass


# --------------------------------------------------------------------------- #
# LE: local emulator
# --------------------------------------------------------------------------- #
def pecos_error_params(noise: Noise) -> dict[str, float]:
    """Our Noise (total probability of a Pauli error after a gate) -> PECOS DepolarizingErrorModel
    parameters. PECOS multiplies p1 by 3/2 and p2 by 5/4 internally (average infidelity -> total
    error, read from its source), so dividing here makes its per-gate error probability equal ours
    [derived; checked numerically in tests/test_h2_backend.py]. p_idle has no PECOS counterpart."""
    if noise.p_idle:
        raise ValueError("the PECOS error model has no idle term; set p_idle = 0")
    return {
        "p1": noise.p1 * 2 / 3,
        "p2": noise.p2 * 4 / 5,
        "p_meas": noise.pm,
        "p_init": noise.p_init,
    }


def offline_compile_backend(device: str = "H2-1LE"):
    """An offline QuantinuumBackend to COMPILE with (no login, no network). The H2-1LE device only
    exists when pecos is installed (.venv-le); in the main environment the offline API lists just
    H1-1, H2-1 and H2-2, so it falls back to offline H2-1, which has the same native gate set and is
    used here only to compile and count [measured: DeviceNotAvailable for H2-1LE without pecos]."""
    from pytket.extensions.quantinuum import QuantinuumAPIOffline, QuantinuumBackend
    from pytket.extensions.quantinuum.backends.quantinuum import DeviceNotAvailable

    try:
        b = QuantinuumBackend(device, api_handler=QuantinuumAPIOffline())
        _ = b.backend_info  # device lookup is lazy: touch it so the failure is HERE
        return b
    except DeviceNotAvailable:
        return QuantinuumBackend("H2-1", api_handler=QuantinuumAPIOffline())


def _with_initial_resets(c: Circuit) -> Circuit:
    """PECOS applies p_init only to explicit Init ops (mid-circuit resets), never to the initial
    allocation, whereas src.backends_qc.Noise (and Selene) charge the initial |0...0> too
    [established, source; measured with a one-qubit test: docs/quantinuum_issues.md QI-11]. A Reset
    on every qubit first makes the noisy run charge it. Used only when noise.p_init > 0."""
    out = Circuit()
    for q in c.qubits:
        out.add_qubit(q)
    for b in c.bits:
        out.add_bit(b)
    for q in c.qubits:
        out.Reset(q)
    out.append(c)
    return out


def _unused_bit_workaround(c: Circuit) -> Circuit:
    """pytket-quantinuum issue 473: pytket->PHIR drops classical bits no command touches. It adds
    redundant SetBits; we do the same when driving the Emulator ourselves."""
    c = c.copy()
    unused = set(c.bits)
    for cmd in c.get_commands():
        unused -= set(cmd.args)
    for b in unused:
        c.add_c_setbits([False], [b])
    return c


def run_le(
    circuit: Circuit,
    cbits: Sequence[Bit],
    shots: int,
    seed: int,
    noise: Noise | None = None,
    device: str = "H2-1LE",
) -> np.ndarray:
    """Run a COMPILED circuit (src.h2_circuits.compile_for_h2) on the local H2 emulator and return
    the (shots, len(cbits)) raw bits.

    noise None / zero: through QuantinuumBackend's own LE (the real device-shaped path).
    noise given: the same PECOS state-vector Emulator with a DepolarizingErrorModel attached --
    the backend's LE cannot do this (QI-2). Both are exact state vectors, so the practical limit
    is SCOPE §5's state-vector ceiling (24 qubits); wider circuits are refused before running."""
    if device not in LE_DEVICES:
        raise DeviceRefused(
            f"run_le only runs local emulators {sorted(LE_DEVICES)}, got {device!r}"
        )
    ceiling = CONFIG.ceilings.statevector_max_spins
    if circuit.n_qubits > ceiling:
        raise LEWidthError(
            f"{circuit.n_qubits}-qubit state vector is beyond the SCOPE §5 ceiling of {ceiling}; "
            "run it on Nexus H2-1E (<= 32 qubits) or reduce the lattice"
        )
    cbits = list(cbits)
    if noise is None or noise.zero:
        from pytket.extensions.quantinuum import QuantinuumAPIOffline, QuantinuumBackend

        b = QuantinuumBackend(device, api_handler=QuantinuumAPIOffline())
        res = b.get_result(b.process_circuit(circuit, n_shots=shots, seed=seed))
        return np.asarray(res.get_shots(cbits=cbits), dtype=np.int8)
    from pecos.error_models.depolarizing_error_model import DepolarizingErrorModel
    from pytket.backends.backendresult import BackendResult
    from pytket_pecos import Emulator

    circ = _unused_bit_workaround(_with_initial_resets(circuit) if noise.p_init else circuit)
    emu = Emulator(
        circ,
        error_model=DepolarizingErrorModel(pecos_error_params(noise)),
        qsim="state-vector",
        seed=seed,
    )
    res = BackendResult(c_bits=circ.bits, shots=emu.run(n_shots=shots))
    return np.asarray(res.get_shots(cbits=cbits), dtype=np.int8)


# --------------------------------------------------------------------------- #
# Nexus: login, SC (free), E (spends HQC)
# --------------------------------------------------------------------------- #
def _nexus_login():
    """Log in with a refresh token from the environment (never stored in the repo) and return
    the qnexus module. A token logs in only for this process."""
    import qnexus as qnx

    token = os.environ.get(TOKEN_ENV)
    if token:
        qnx.auth.login_with_token(token)
    elif not qnx.auth.is_logged_in():
        raise RuntimeError(
            f"not logged in to Nexus: set {TOKEN_ENV} (a refresh token) or run "
            "`qnx.login()` interactively once"
        )
    return qnx


def syntax_check(
    circuits: Sequence[Circuit],
    shots: int,
    project: str,
    device: str = "H2-1SC",
    ledger: Path | None = None,
) -> list[dict]:
    """FREE tier. Submit circuits to a Nexus SYNTAX CHECKER, which validates them for H2 and
    returns the HQC cost it would charge. It refuses any device that is not an SC, so it cannot
    spend credits whatever it is passed. Returns one dict per circuit with the quoted cost.
    [unverified against the live server until the first SC run; written from qnexus 0.51.1.]"""
    if device not in SC_DEVICES:
        raise DeviceRefused(
            f"syntax_check only talks to {sorted(SC_DEVICES)}, got {device!r}: "
            "it must never be able to reach a device that charges HQC"
        )
    qnx = _nexus_login()
    from qnexus.models import QuantinuumConfig

    proj = qnx.projects.get_or_create(name=project)
    cfg = QuantinuumConfig(device_name=device, no_opt=True)
    out: list[dict] = []
    for i, c in enumerate(circuits):
        ref = qnx.circuits.upload(
            circuit=c, name=f"{project}-sc-{int(time.time())}-{i}", project=proj
        )
        # syntax_checker passed explicitly: qnexus 0.51.1's circuits.cost builds "H2-1ESC" from an
        # E config because its .strip("E") discards its result (docs/quantinuum_issues.md QI-5).
        cost = qnx.circuits.cost(
            circuit_ref=ref, n_shots=shots, backend_config=cfg, syntax_checker=device, project=proj
        )
        row = {
            "tier": "SC",
            "device": device,
            "circuit": i,
            "shots": shots,
            "quoted_hqc": cost,
            "n_qubits": c.n_qubits,
        }
        _ledger(row, ledger)
        out.append(row)
    return out


def submit_nexus(
    circuits: Sequence[Circuit],
    shots: int,
    *,
    project: str,
    device: str,
    allow_hardware: bool,
    approval: str | None,
    max_cost_hqc: float,
    estimated_hqc: float,
    allow_real_hardware: bool = False,
    ledger: Path | None = None,
    job_name: str | None = None,
):
    """HQC tier: submit to a Nexus H2 EMULATOR (or hardware). NOTHING in this repo calls this; it
    needs the project lead's explicit go for each run (SCOPE §5, CLAUDE.md).

    Refuses, before importing qnexus, unless: allow_hardware is True; `approval` is the per-run
    token (backends_qc.NEXUS_APPROVAL); max_cost_hqc is positive; the offline `estimated_hqc` for
    the whole job is within it; the device is an E emulator (or hardware with allow_real_hardware);
    and the widest circuit fits H2's 56 qubits. Submits with no_opt=True and the cap passed as
    `max_cost`, which Nexus enforces server-side, and records the job in the ledger.
    `job_name` (additive, 2026-10-24): a deterministic name, so an interrupted submission can be
    found again by name instead of being paid for twice (src/h2_resume.py).
    [unverified against the live server; written from qnexus 0.51.1.]"""
    if device in SC_DEVICES or device in LE_DEVICES:
        raise DeviceRefused(
            f"{device!r} is a free tier; use syntax_check / run_le, not submit_nexus"
        )
    if device in HW_DEVICES:
        if not allow_real_hardware:
            raise DeviceRefused(f"{device!r} is real hardware: also set allow_real_hardware=True")
    elif device not in E_DEVICES:
        raise DeviceRefused(f"unknown device {device!r}; allowed: {sorted(E_DEVICES | HW_DEVICES)}")
    width = max(c.n_qubits for c in circuits)
    _nexus_preflight(
        SimpleNamespace(n_phys=width),
        0,
        shots,
        allow_hardware=allow_hardware is True,  # a truthy "no" or 1 must not open the gate
        approval=approval,
        max_cost_hqc=max_cost_hqc,
        device=device,
    )
    # NaN compares False with everything, so every numeric gate is written as a positive test.
    if isinstance(shots, bool) or not isinstance(shots, int) or shots < 1:
        raise ValueError(f"nexus submission refused: shots must be an int >= 1, got {shots!r}")
    if not (math.isfinite(estimated_hqc) and estimated_hqc > 0):
        raise ValueError(
            f"nexus submission refused: estimated_hqc must be finite and positive, got "
            f"{estimated_hqc!r}"
        )
    if not estimated_hqc <= max_cost_hqc:
        raise ValueError(
            f"nexus submission refused: estimated {estimated_hqc:.1f} HQC exceeds "
            f"max_cost_hqc {max_cost_hqc:.1f}"
        )
    # The record must be writable BEFORE anything is spent: a spent job with no record is worse
    # than a refused one.
    _ledger_check_writable(ledger)
    qnx = _nexus_login()
    from qnexus.models import QuantinuumConfig

    proj = qnx.projects.get_or_create(name=project)
    cfg = QuantinuumConfig(device_name=device, no_opt=True, max_cost=max_cost_hqc)
    # start_execute_job takes uploaded program REFERENCES: qnexus's `accept_circuits_for_programs`
    # only renames the keyword, it does not upload (read in qnexus 0.51.1; found in review).
    refs = _upload_circuits(qnx, circuits, proj, f"{project}-{device}")
    job = qnx.start_execute_job(
        programs=refs,
        n_shots=[shots] * len(circuits),
        backend_config=cfg,
        project=proj,
        name=job_name or f"{project}-{device}-{int(time.time())}",
        max_cost=max_cost_hqc,
    )
    entry = {
        "tier": "E" if device in E_DEVICES else "HW",
        "device": device,
        "shots": shots,
        "n_circuits": len(circuits),
        "estimated_hqc": estimated_hqc,
        "max_cost_hqc": max_cost_hqc,
        "approval": NEXUS_APPROVAL,
        "job_id": str(getattr(job, "id", "")),
        "job_name": job_name,
    }
    try:
        _ledger(entry, ledger)
    except OSError:
        # the job exists and is spending; never let a write error hide its id
        print(f"LEDGER WRITE FAILED for a SUBMITTED job: {entry}", file=sys.stderr)
        raise
    return job


def _upload_circuits(qnx, circuits, proj, prefix):
    stamp = int(time.time())
    return [
        qnx.circuits.upload(circuit=c, name=f"{prefix}-{stamp}-{i}", project=proj)
        for i, c in enumerate(circuits)
    ]


def fetch_nexus(
    job, cbits_list: Sequence[Sequence[Bit]], timeout: float | None = None
) -> list[np.ndarray]:
    """Wait for a Nexus job and return, per circuit, the (shots, len(cbits)) raw bits in the
    order of that circuit's `cbits` -- the same arrays `run_le` returns, so the same
    src.h2_circuits.shot_records post-processing applies. Label what comes back as an H2
    EMULATOR (or hardware) result, never a classical prediction."""
    qnx = _nexus_login()
    qnx.jobs.wait_for(job, timeout=timeout)
    results = qnx.jobs.results(job)
    return [
        np.asarray(r.download_result().get_shots(cbits=list(cb)), dtype=np.int8)
        for r, cb in zip(results, cbits_list, strict=True)
    ]
