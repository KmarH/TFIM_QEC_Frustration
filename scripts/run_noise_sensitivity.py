"""Noise-model sensitivity of the Part B conclusion (Iceberg vs Steane / 5-qubit / concat-d4).

Stim first-order accounting only (no execution), 2x2 logical lattice. Each scenario changes the
Part B baseline (uniform depolarizing) along one or more of:
  ZZ-biased 2q errors (fraction eta of each 2q error is Z(x)Z on top of the uniform share),
  idle noise on data qubits, Pauli-twirled coherent over-rotation (generator applied w.p. sin^2 eps).

Section 1 (handoff/06): the H2 PRIOR of research/06-h2-noise-prior.md — p2 ~ 6e-4 [inferred],
  p1 = pm = p_init = p2/10, eta = 0.05 with bracket 0.03 / 0.08 [inferred, Fig. S3 read-off],
  sin^2 eps scanned [assumed; unpublished]. eta = 0.5 / 0.9 rows are STRESS-TESTS (~10x the prior).
Section 2: the original Part B sensitivity table at its original rates (p2 = 1e-3), kept for
  traceability with its eta rows relabelled as stress-tests.
All parameters live in config.py (SensitivityConfig, EncodedConfig). Writes data/noise_sensitivity.txt.
Every number is a classical prediction under an ASSUMED noise model, NOT an H2 result.
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
    BareTFIM, EncodedTFIM, NoiseRates, detected_total, make_code, undetected_rate_per_step,
)

E = CONFIG.encoded
S = CONFIG.sensitivity
CODES = ["iceberg", "steane", "five", "concat"]
STRESS = "STRESS-TEST ~10x H2 prior, NOT representative:"


def base_rates(p2):
    p1 = p2 * S.p1_ratio
    return dict(p2=p2, p1=p1, pm=p1, p_init=p1)


def h2_prior_scenarios():
    eta, (lo, hi) = S.zz_bias_prior, S.zz_bias_bracket
    rows = [("uniform depolarizing (eta=0; ZZ share 1/15)", {})]
    rows += [(f"H2 prior eta={eta:g}, sin^2(eps)={s:g}", {"zz_bias": eta, "overrot": s})
             for s in S.overrot_scan]
    rows += [(f"H2 bracket eta={x:g}", {"zz_bias": x}) for x in (lo, hi)]
    worst = max(S.overrot_scan)
    rows += [(f"in-range corner eta={hi:g}, sin^2(eps)={worst:g}", {"zz_bias": hi, "overrot": worst})]
    rows += [(f"{STRESS} eta={x:g}", {"zz_bias": x}) for x in S.zz_bias_stress]
    return rows


def legacy_scenarios():
    (i1, i2), (o1, o2) = S.p_idle_legacy, S.overrot_legacy
    eta_c = S.zz_bias_stress[0]
    rows = [("baseline (uniform depolarizing)", {})]
    rows += [(f"{STRESS} eta={x:g}", {"zz_bias": x}) for x in S.zz_bias_stress]
    rows += [(f"idle noise {x:g} per idle point", {"p_idle": x}) for x in (i1, i2)]
    rows += [(f"over-rotation sin^2(eps)={x:g} (eps~{np.arcsin(np.sqrt(x)):.2f} rad)", {"overrot": x})
             for x in (o1, o2)]
    rows += [(f"{STRESS} eta={eta_c:g}+idle {i1:.0e}+over-rot {o1:.0e}",
              {"zz_bias": eta_c, "p_idle": i1, "overrot": o1})]
    return rows


def main():
    Lx, Ly = S.Lx, S.Ly
    progs = {n: EncodedTFIM(make_code(n, Lx * Ly), Lx, Ly, "periodic", E.J, E.h, E.dt, E.theta) for n in CODES}
    bare = BareTFIM(Lx, Ly, "periodic", E.J, E.h, E.dt, E.theta)
    out = []
    w = 82

    def log(s=""):
        print(s, flush=True)
        out.append(s)

    def table(p2, scenarios):
        log(f"{'scenario':{w}s} | " + " | ".join(f"{c:>23s}" for c in CODES) + f" | {'bare':>9s}")
        for name, extra in scenarios:
            nz = NoiseRates(**base_rates(p2), **extra)
            ub = undetected_rate_per_step(bare, nz)["total"]
            cells = []
            for c in CODES:
                u = undetected_rate_per_step(progs[c], nz)["total"]
                a = np.exp(-detected_total(progs[c], nz, S.accept_steps))
                cells.append(f"{u:.2e} / {a:.2f} (x{u / ub:.2f})")
            log(f"{name:{w}s} | " + " | ".join(f"{x:>23s}" for x in cells) + f" | {ub:.2e}")

    log(f"# Noise sensitivity — {time.strftime('%Y-%m-%d %H:%M')}; {Lx}x{Ly} lattice; Stim first-order accounting")
    log("# CLASSICAL PREDICTION under an ASSUMED noise model; NOT an H2 result. No hardware, no Nexus.")
    log(f"# columns per code: undetected-logical prob per Trotter step / first-order acceptance after {S.accept_steps} steps")
    log("# ratio = code's undetected / bare's unprotected (lower is better; < 1 means encoding helps)")
    log("# zz_bias=eta: each 2q error is uniform w.p. (1-eta) over 15 Paulis plus Z(x)Z w.p. eta, so the total")
    log("#   ZZ share is eta + (1-eta)/15. over-rot: twirled stand-in, adds sin^2(eps) per rotation to code AND bare.")
    log("")
    p2 = S.p2_prior
    log(f"## 1. H2 prior (research/06): p2={p2:g} [inferred], p1=pm=p_init={p2 * S.p1_ratio:g} [inferred],"
        f" eta={S.zz_bias_prior:g} bracket {S.zz_bias_bracket} [inferred, Fig. S3 read-off],"
        f" sin^2(eps) scanned [assumed; unpublished]")
    log("#   a PREDICTION FROM A PRIOR, not an H2 measurement; eta=0.5/0.9 rows are stress-tests only")
    table(p2, h2_prior_scenarios())
    log("")
    p2 = S.p2_legacy
    log(f"## 2. Original Part B sensitivity table (traceability): p2={p2:g}, p1=pm=p_init={p2 * S.p1_ratio:g} [assumed]")
    table(p2, legacy_scenarios())
    with open(os.path.join(REPO, CONFIG.data_dir, "noise_sensitivity.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
