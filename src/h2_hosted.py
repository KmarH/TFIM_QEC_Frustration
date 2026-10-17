"""The FREE hosted tier on Nexus: the Nexus-hosted noiseless emulator H2-1LE (handoff/13).

Quantinuum documents Nexus-hosted emulators as running "without submitting to a Fair Queue or
consuming HQCs" (they bill the Simulation quota in seconds; docs.quantinuum.com "Quantinuum
Emulators", read 2026-10-17). They exercise the same upload / execute / fetch path as
src.h2_backend.submit_nexus, so that path can be proven before any HQC is spent. It is separate
from h2_backend so that module's rule (qnexus referenced only in its named Nexus functions) stays
checkable, and so this tier has its own gate: any device that is not a hosted LE is refused before
qnexus is imported, and `check_hosted_cost` fails loudly if the server ever reports a cost.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

from pytket import Circuit

from src.h2_backend import (
    LE_DEVICES,
    DeviceRefused,
    _ledger,
    _ledger_check_writable,
    _nexus_login,
    _upload_circuits,
)

HOSTED_LE_MAX_QUBITS = 20  # Nexus-hosted emulators are capped at 20 qubits [docs, QI-12]


def submit_hosted_le(
    circuits: Sequence[Circuit],
    shots: int,
    *,
    project: str,
    device: str = "H2-1LE",
    ledger: Path | None = None,
):
    """FREE tier on the Nexus platform: the Nexus-HOSTED noiseless emulator (H2-1LE), which
    Quantinuum documents as running "without submitting to a Fair Queue or consuming HQCs" (it bills
    the Simulation quota in seconds). It exercises the same upload / execute / fetch path as
    submit_nexus, so the path can be proven before any HQC is spent. Refuses every device that is
    not a hosted LE, and anything wider than 20 qubits, before importing qnexus. After the job runs,
    `check_hosted_cost` raises if the server reports any HQC cost, so a wrong assumption is loud.
    [unverified against the live server until the first run; written from qnexus 0.51.1.]"""
    if device not in LE_DEVICES:
        raise DeviceRefused(f"submit_hosted_le only targets {sorted(LE_DEVICES)}, got {device!r}")
    if isinstance(shots, bool) or not isinstance(shots, int) or shots < 1:
        raise ValueError(f"shots must be an int >= 1, got {shots!r}")
    if not circuits:
        raise ValueError("no circuits")
    width = max(c.n_qubits for c in circuits)
    if width > HOSTED_LE_MAX_QUBITS:
        raise ValueError(
            f"hosted emulators are capped at {HOSTED_LE_MAX_QUBITS} qubits, got {width}"
        )
    _ledger_check_writable(ledger)
    qnx = _nexus_login()
    from qnexus.models import QuantinuumConfig

    proj = qnx.projects.get_or_create(name=project)
    # no_opt: server-side optimisation cancels folded ZZ(a)ZZ(-a)ZZ(a) (QI-8); the circuits are already compiled at level 0
    cfg = QuantinuumConfig(device_name=device, no_opt=True)
    refs = _upload_circuits(qnx, circuits, proj, f"{project}-{device}")
    job = qnx.start_execute_job(
        programs=refs,
        n_shots=[shots] * len(circuits),
        backend_config=cfg,
        project=proj,
        name=f"{project}-{device}-{int(time.time())}",
    )
    _ledger(
        {
            "tier": "LE-hosted",
            "device": device,
            "shots": shots,
            "n_circuits": len(circuits),
            "job_id": str(getattr(job, "id", "")),
        },
        ledger,
    )
    return job


def check_hosted_cost(job, ledger: Path | None = None) -> float:
    """After a hosted-LE job completes, read the cost the server reports and fail loudly if it is
    anything but zero or unset: the free-tier claim is the docs', not ours, so we verify it."""
    qnx = _nexus_login()
    status = qnx.jobs.wait_for(job)
    cost = getattr(status, "cost", None)
    _ledger(
        {"tier": "LE-hosted", "job_id": str(getattr(job, "id", "")), "reported_cost": cost}, ledger
    )
    if cost not in (None, 0, 0.0):
        raise RuntimeError(
            f"hosted LE job reported a cost of {cost!r} HQC: STOP and tell the "
            "project lead; the free-tier assumption is wrong"
        )
    return 0.0 if cost is None else float(cost)
