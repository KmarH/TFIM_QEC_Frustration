"""Why Selene's acceptance is below the Stim prediction (encoded TFIM, Iceberg 2x2, 3 steps).

Reproduces: (1) first-order vs exact Stim vs local-sim acceptance; (2) one noise channel at a
time, Selene vs Stim; (3) Selene's native-operation counts (with_metrics) vs the pytket-level
counts the Stim model charges noise on; (4) Stim with noise counts matched to Selene's natives.
Writes data/selene_gap.txt. Assumed rates; classical simulators only.
"""

from __future__ import annotations

import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402

from config import CONFIG  # noqa: E402
from src.encoded_codes import (  # noqa: E402
    EncodedTFIM, NoiseRates, detected_total, guppy_program, make_code, run_local, run_selene, to_stim,
)

E = CONFIG.encoded
MAXS = CONFIG.ceilings.statevector_max_spins


def main():
    out = []

    def log(s=""):
        print(s, flush=True)
        out.append(s)

    prog = EncodedTFIM(make_code("iceberg", 4), 2, 2, "periodic", E.J, E.h, E.dt, E.theta)
    steps = 3

    def stim_acc(nz, n=steps):
        d = to_stim(prog.schedule(n, "Z"), nz).compile_detector_sampler(seed=3).sample(200000)
        return float((~d.any(axis=1)).mean())

    log(f"# Selene acceptance gap — {time.strftime('%Y-%m-%d %H:%M')}; Iceberg 2x2, {steps} steps [assumed rates]")
    log("# classical simulators only (Stim / Selene / local-sim) under an ASSUMED noise model; NOT an H2 result")
    p2 = 3e-3
    nz = NoiseRates(p2=p2, p1=p2 / 10, pm=p2 / 10, p_init=p2 / 10)
    rng = np.random.default_rng(0)
    loc = [run_local(prog.schedule(steps, "Z"), nz, rng)[0] for _ in range(1000)]
    log("\n## 1. Is it the first-order approximation or the local engine? (p2=3e-3, p1=pm=p_init=3e-4)")
    log(f"first-order exp(-D) {np.exp(-detected_total(prog, nz, steps)):.4f} | Stim sampled {stim_acc(nz):.4f} | "
        f"local-sim {np.mean(loc):.3f}±{np.std(loc) / np.sqrt(len(loc)):.3f}  -> neither")

    log("\n## 2. One channel at a time (rate 3e-3), Selene (3000 shots) vs Stim (200k shots)")
    for label, kw in [("2q", dict(p2=3e-3)), ("1q", dict(p1=3e-3)), ("meas", dict(pm=3e-3)), ("init/reset", dict(p_init=3e-3))]:
        nzc = NoiseRates(**kw)
        res = run_selene(prog, steps, 3000, nzc, seed=9, max_spins=MAXS, n_processes=2)
        a = float(np.mean([x for x, _ in res]))
        se = np.sqrt(a * (1 - a) / len(res))
        a_st = stim_acc(nzc)
        log(f"{label:11s} Stim {a_st:.4f} | Selene {a:.4f}±{se:.4f} | {(a - a_st) / se:+.1f} sigma")

    log("\n## 3. Operation counts: Selene natives (with_metrics) vs the pytket-level model")
    from selene_sim import Quest
    sch = prog.schedule(steps, "Z")
    main_fn = guppy_program(sch, "gapdiag")
    m = (main_fn.emulator(n_qubits=sch.n).with_shots(1).with_simulator(Quest()).with_seed(1)
         .with_metrics().run().metrics()[0]["user_program"])
    one_q = sum(len(it[1].get_commands()) for it in sch.items if it[0] == "U") - \
        sum(1 for it in sch.items if it[0] == "U" for c in it[1].get_commands() if len(c.qubits) == 2)
    two_q = sum(1 for it in sch.items if it[0] == "U" for c in it[1].get_commands() if len(c.qubits) == 2)
    resets = sum(1 for it in sch.items if it[0] == "R")
    log(f"2q: Selene rzz {m['rzz_count']} vs model {two_q}")
    log(f"1q: Selene rxy {m['rxy_count']} + rz {m['rz_count']} = {m['rxy_count'] + m['rz_count']} vs model {one_q} "
        f"(x{(m['rxy_count'] + m['rz_count']) / one_q:.2f})")
    log(f"init/reset events: Selene reset {m['reset_count']} (qalloc {m['qalloc_count']}) vs model {resets}")

    f1 = (m["rxy_count"] + m["rz_count"]) / one_q
    log(f"\n## 4. Stim with p1 x{f1:.2f} (native 1q count) and p_init x1.5 (fitted from the init-only row)")
    for p2v, n in [(1e-3, 3), (3e-3, 3), (3e-3, 1), (1e-3, 1)]:
        base = NoiseRates(p2=p2v, p1=p2v / 10, pm=p2v / 10, p_init=p2v / 10)
        adj = NoiseRates(p2=p2v, p1=p2v / 10 * f1, pm=p2v / 10, p_init=p2v / 10 * 1.5)
        res = run_selene(prog, n, 2000, base, seed=21 + n, max_spins=MAXS, n_processes=2)
        a = float(np.mean([x for x, _ in res]))
        log(f"p2={p2v:g} step {n}: Stim pytket-level {stim_acc(base, n):.3f} | Stim native-matched "
            f"{stim_acc(adj, n):.3f} | Selene {a:.3f}±{np.sqrt(a * (1 - a) / len(res)):.3f}")
    with open(os.path.join(REPO, CONFIG.data_dir, "selene_gap.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
