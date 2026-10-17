"""Run driver for the H2 submission path (handoff/13, docs/nexus_toggle.md): plan, quote, submit.

One place that turns a named run group (G1, Q1, Q4, ...) into compiled H2 circuits with offline HQC
estimates, and executes them at the tier `CONFIG.hardware.nexus_tier` selects:

  dry-run    build + compile + estimate offline; nothing leaves the machine (the default)
  sc         free: quote every circuit on the Nexus syntax checker (H2-1SC/2SC)
  hosted-le  free: run on the Nexus-hosted noiseless emulator (H2-1LE), <= 20 qubits, cost 0
  emulator   SPENDS HQC on H2-1E/2E. Every gate below must pass BEFORE anything is called.

Emulator gates (DriverRefused on the first failure): allow_hardware is True (identity); the per-run
approval token is exact; max_cost_hqc finite and > 0; the device is an E emulator (so real hardware,
SC and LE names are refused even with allow_real_hardware); a Nexus project is named; the widest
circuit fits emulator_max_qubits; every item's shots <= max_shots_per_job and its per-shot HQC <=
max_hqc_per_shot; the offline total is finite, > 0 and <= the cap. Only then is every circuit quoted
on the free SC, the quotes must be finite, > 0 and sum to <= the cap (equal is allowed), and the jobs
are submitted with `estimated_hqc` = the SERVER quote, not the offline estimate.

Switching the emulator on is therefore a config edit (nexus_tier, allow_hardware, max_cost_hqc,
nexus_project) PLUS the approval token at run time; the CLI cannot select the emulator tier itself.
qnexus is imported only inside the default quote/submit/hosted functions of src.h2_backend and
src.h2_hosted, so a dry run never loads it. Nothing here is an H2 result: estimates are offline and
quotes are the server's price, not a measurement.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

from pytket import Circuit

from config import CONFIG
from src.backends_qc import NEXUS_APPROVAL
from src.encoded_codes import EncodedTFIM, make_code
from src.encoded_tfim import IcebergTFIM, twirl_program
from src.h2_backend import E_DEVICES, offline_compile_backend
from src.h2_circuits import (
    bare_h2_circuit,
    codes_h2_circuit,
    compile_for_h2,
    encoded_h2_circuit,
    hqc_estimate,
    native_counts,
)

TIERS = ("dry-run", "sc", "hosted-le", "emulator")
FREE_TIERS = ("dry-run", "sc", "hosted-le")
HOSTED_LE_MAX_QUBITS = 20  # Nexus-hosted emulators [docs, QI-12]; same value as src.h2_hosted


class DriverRefused(PermissionError):
    """A run the driver will not start: a gate failed, so nothing was called."""


@dataclass
class PlannedCircuit:
    label: str
    group: str
    shots: int  # shots for THIS circuit (a randomized-compiling instance gets shots // k)
    circuit: Circuit  # compiled to H2 native gates at TKET level 0
    n_qubits: int
    estimate_hqc: float  # offline, Rz-free, at this item's own shots
    meta: dict = field(default_factory=dict)  # decode info (layout, twirled program, step, ...)


@dataclass
class Plan:
    group: str
    items: list[PlannedCircuit]

    @property
    def total_estimate_hqc(self) -> float:
        return float(sum(i.estimate_hqc for i in self.items))

    @property
    def max_qubits(self) -> int:
        return max(i.n_qubits for i in self.items)


# (label, kind, lattice, steps, randomized compiling)
_G1 = [
    ("Iceberg 2x2, plain", "enc", (2, 2), (1, 2, 3), False),
    ("Iceberg 2x2, RC", "enc", (2, 2), (1, 2, 3), True),
    ("bare 2x2", "bare", (2, 2), (1, 2, 3), False),
]
_Q1 = [
    ("Iceberg 4x5, RC", "enc", (4, 5), tuple(range(1, 7)), True),
    ("bare 4x5", "bare", (4, 5), tuple(range(1, 7)), False),
]
_Q1_ALT = [
    ("Iceberg 4x6, RC", "enc", (4, 6), tuple(range(1, 7)), True),
    ("bare 4x6", "bare", (4, 6), tuple(range(1, 7)), False),
]
_Q4 = [
    ("Steane 1x2", "code:steane", (1, 2), (1, 2, 3), False),
    ("5-qubit 1x2", "code:five", (1, 2), (1, 2, 3), False),
    ("concatenated Iceberg 2x2", "code:concat", (2, 2), (1, 2, 3), False),
]
GROUPS: dict[str, list[tuple]] = {
    "bare-2x2-step1": [("bare 2x2", "bare", (2, 2), (1,), False)],  # cheapest end-to-end check
    "G1": _G1,
    "Q1": _Q1,
    "Q1-alt": _Q1_ALT,
    "Q4": _Q4,
}


def group_names() -> list[str]:
    return list(GROUPS)


def _hw(hw):
    return CONFIG.hardware if hw is None else hw


def _check_shots(shots, hw) -> None:
    if isinstance(shots, bool) or not isinstance(shots, int) or shots < 1:
        raise DriverRefused(f"shots must be an int >= 1, got {shots!r}")
    if shots > hw.max_shots_per_job:
        raise DriverRefused(
            f"{shots} shots exceeds max_shots_per_job {hw.max_shots_per_job} "
            "(Quantinuum H2 hardware limit: 10,000 shots per job)"
        )


def _author(kind: str, lat, n: int, rc_seed: int | None):
    """One uncompiled circuit plus the decode info `shot_records` / `codes_records` will need."""
    E = CONFIG.encoded
    Lx, Ly = lat
    if kind.startswith("code:"):
        prog = EncodedTFIM(make_code(kind[5:], Lx * Ly), Lx, Ly, "periodic", E.J, E.h, E.dt, E.theta)
        c, layout = codes_h2_circuit(prog, n)
        return c, {"layout": layout}
    spec = IcebergTFIM(Lx, Ly, "periodic", E.J, E.h, E.dt, E.theta, 1)
    if kind == "bare":
        c, cbits = bare_h2_circuit(spec, n)
        return c, {"cbits": cbits}
    prog = twirl_program(spec, n, rc_seed) if rc_seed is not None else None
    c, layout = encoded_h2_circuit(spec, n, prog)
    return c, {"layout": layout, "prog": prog, "rc_seed": rc_seed}


def build_plan(group: str, shots: int, *, hw=None) -> Plan:
    """OFFLINE: author, compile (TKET level 0) and price every circuit of `group`. Randomized-
    compiling points split `shots` over CONFIG.encoded.rc_instances twirled circuits (shots // k
    each); everything else gets all `shots`."""
    hw = _hw(hw)
    if group not in GROUPS:
        raise DriverRefused(f"unknown group {group!r}; known: {group_names()}")
    _check_shots(shots, hw)
    backend = offline_compile_backend(hw.le_device)
    k = CONFIG.encoded.rc_instances
    items: list[PlannedCircuit] = []
    for label, kind, lat, steps, rc in GROUPS[group]:
        per = max(shots // k, 1) if rc else shots
        for n in steps:
            for seed in range(k) if rc else (None,):
                c, meta = _author(kind, lat, n, seed)
                c = compile_for_h2(c, backend)
                cnt = native_counts(c)
                tag = f"{label} step {n}" + (f" rc{seed}" if rc else "")
                items.append(
                    PlannedCircuit(
                        label=tag, group=group, shots=per, circuit=c, n_qubits=cnt["nqubits"],
                        estimate_hqc=hqc_estimate(cnt, per), meta={**meta, "step": n},
                    )
                )
    return Plan(group, items)


def _by_shots(items: list[PlannedCircuit]) -> list[tuple[int, list[PlannedCircuit]]]:
    """Items grouped by shot count, groups in first-appearance order, plan order within a group."""
    out: dict[int, list[PlannedCircuit]] = {}
    for it in items:
        out.setdefault(it.shots, []).append(it)
    return list(out.items())


def _finite_pos(x) -> bool:
    return (
        isinstance(x, int | float) and not isinstance(x, bool) and math.isfinite(x) and x > 0
    )


def _quote_all(plan: Plan, hw, quote_fn) -> tuple[float, list[tuple[list[PlannedCircuit], list]]]:
    calls = []
    total = 0.0
    for shots, items in _by_shots(plan.items):
        rows = list(
            quote_fn(
                [i.circuit for i in items], shots, project=hw.nexus_project, device=hw.syntax_checker
            )
        )
        calls.append((items, rows))
        total += sum(float(r["quoted_hqc"]) for r in rows if _finite_pos(r.get("quoted_hqc")))
    return total, calls


def _emulator_gates(plan: Plan, hw, approval) -> None:
    if hw.allow_hardware is not True:
        raise DriverRefused("allow_hardware is not True: set it consciously in config (SCOPE §5)")
    if approval != NEXUS_APPROVAL:
        raise DriverRefused(
            f"missing per-run approval: pass --approval {NEXUS_APPROVAL!r} for THIS run; "
            "a config edit alone never spends"
        )
    if not _finite_pos(hw.max_cost_hqc):
        raise DriverRefused(f"max_cost_hqc must be finite and > 0, got {hw.max_cost_hqc!r}")
    if hw.emulator_device not in E_DEVICES:
        raise DriverRefused(
            f"emulator_device {hw.emulator_device!r} is not an E emulator {sorted(E_DEVICES)}; "
            "real hardware, SC and LE names are never submitted through this tier"
        )
    if not hw.nexus_project:
        raise DriverRefused("nexus_project is empty: name the Nexus project in config")
    if plan.max_qubits > hw.emulator_max_qubits:
        raise DriverRefused(
            f"{plan.max_qubits} qubits exceeds emulator_max_qubits {hw.emulator_max_qubits}"
        )
    for it in plan.items:
        if it.shots > hw.max_shots_per_job:
            raise DriverRefused(f"{it.label}: {it.shots} shots > max_shots_per_job")
        if not _finite_pos(it.estimate_hqc) or (
            it.estimate_hqc / it.shots > hw.max_hqc_per_shot * (1 + 1e-12)
        ):
            raise DriverRefused(
                f"{it.label}: {it.estimate_hqc!r} HQC over {it.shots} shots is not within "
                f"max_hqc_per_shot {hw.max_hqc_per_shot}"
            )
    total = plan.total_estimate_hqc
    if not (math.isfinite(total) and total > 0):
        raise DriverRefused(f"offline estimate must be finite and > 0, got {total!r}")
    if total > hw.max_cost_hqc:
        raise DriverRefused(
            f"offline estimate {total:.1f} HQC exceeds max_cost_hqc {hw.max_cost_hqc:.1f}"
        )


def execute(
    plan: Plan,
    *,
    hw=None,
    tier: str | None = None,
    approval: str | None = None,
    quote_fn: Callable | None = None,
    submit_fn: Callable | None = None,
    hosted_fn: Callable | None = None,
) -> dict:
    """Run `plan` at `tier` (default: hw.nexus_tier). An explicit tier can step DOWN; it can never
    skip the emulator gates."""
    hw = _hw(hw)
    tier = hw.nexus_tier if tier is None else tier
    if tier not in TIERS:
        raise DriverRefused(f"unknown tier {tier!r}; tiers: {TIERS}")
    if tier == "dry-run":
        return {
            "tier": "dry-run",
            "submitted": False,
            "estimate_hqc": plan.total_estimate_hqc,
            "n_circuits": len(plan.items),
            "max_qubits": plan.max_qubits,
        }
    if not hw.nexus_project:
        raise DriverRefused(f"tier {tier!r} needs hardware.nexus_project (the Nexus project name)")
    if tier == "emulator":
        _emulator_gates(plan, hw, approval)
    if tier == "hosted-le" and plan.max_qubits > HOSTED_LE_MAX_QUBITS:
        raise DriverRefused(
            f"{plan.max_qubits} qubits: Nexus-hosted emulators are capped at {HOSTED_LE_MAX_QUBITS}"
        )

    if tier == "hosted-le":
        if hosted_fn is None:
            from src.h2_hosted import submit_hosted_le as hosted_fn
        jobs = [
            hosted_fn([i.circuit for i in items], shots, project=hw.nexus_project, device=hw.le_device)
            for shots, items in _by_shots(plan.items)
        ]
        return {"tier": "hosted-le", "submitted": True, "spent_hqc": 0.0, "jobs": jobs}

    if quote_fn is None:
        from src.h2_backend import syntax_check as quote_fn
    quoted, calls = _quote_all(plan, hw, quote_fn)
    if tier == "sc":
        return {
            "tier": "sc",
            "submitted": False,
            "quoted_hqc": quoted,
            "quotes": [r for _, rows in calls for r in rows],
            "estimate_hqc": plan.total_estimate_hqc,
        }

    # emulator: the server's price must be sane and within the cap BEFORE the first submit
    for _, rows in calls:
        for r in rows:
            if not _finite_pos(r.get("quoted_hqc")):
                raise DriverRefused(f"SC returned an unusable quote: {r!r}")
    if not quoted <= hw.max_cost_hqc:
        raise DriverRefused(
            f"SC quote total {quoted:.2f} HQC exceeds max_cost_hqc {hw.max_cost_hqc:.2f}: nothing submitted"
        )
    if submit_fn is None:
        from src.h2_backend import submit_nexus as submit_fn
    jobs = []
    for items, rows in calls:
        jobs.append(
            submit_fn(
                [i.circuit for i in items],
                items[0].shots,
                project=hw.nexus_project,
                device=hw.emulator_device,
                allow_hardware=True,
                approval=approval,
                max_cost_hqc=hw.max_cost_hqc,
                estimated_hqc=sum(float(r["quoted_hqc"]) for r in rows),
            )
        )
    return {"tier": "emulator", "submitted": True, "quoted_hqc": quoted, "jobs": jobs}


def _print_plan(plan: Plan, tier: str) -> None:
    banner = "DRY RUN (nothing is sent)" if tier == "dry-run" else f"tier: {tier}"
    print(f"{banner} -- group {plan.group}; offline estimates are Rz-free (D-HQC), not quotes")
    print(f"{'label':44}{'qubits':>7}{'shots':>7}{'est HQC':>10}")
    for it in plan.items:
        print(f"{it.label:44}{it.n_qubits:>7}{it.shots:>7}{it.estimate_hqc:>10.2f}")
    print(f"{'total':44}{plan.max_qubits:>7}{'':>7}{plan.total_estimate_hqc:>10.2f}  HQC (offline)")


def cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Plan / quote / run an H2 run group (see src/h2_driver.py)")
    p.add_argument("--group", required=True, choices=group_names())
    p.add_argument("--shots", type=int, default=1000)
    p.add_argument(
        "--tier", choices=FREE_TIERS,
        help="step down to a free tier; the emulator tier is selected only in config (hardware.nexus_tier)",
    )
    p.add_argument("--approval", default=None, help="the per-run approval token (emulator tier only)")
    a = p.parse_args(argv)
    hw = CONFIG.hardware
    tier = a.tier or hw.nexus_tier
    try:
        plan = build_plan(a.group, a.shots, hw=hw)
        _print_plan(plan, tier)
        out = execute(plan, hw=hw, tier=tier, approval=a.approval)
    except DriverRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    print({k: v for k, v in out.items() if k not in ("quotes", "jobs")})
    return 0
