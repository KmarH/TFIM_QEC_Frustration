"""Part B (handoff/04): Steane, 5-qubit, concatenated-d4 (and Iceberg via the same pipeline).

Decisions recorded by the team (2026-10-07): FT standard B = measured accounting, no pass/fail bar;
budget (ii) = H2 ~55 physical qubits for build/discard, Stim at budget size, execution only at
reduced size <= statevector ceiling; residual = MEASURED (Stim) undetected-logical rate.
Writes data/encoded_codes.txt line by line. Every noisy number is a classical prediction under
an ASSUMED generic depolarizing model; none is an H2 result.

Usage: python scripts/run_encoded_codes.py [--skip-exec | --exec-only] [--force]

  (no flag)     regenerate the whole file: sections 1-4 (fast) and section 5 (slow, Selene).
  --exec-only   APPEND section 5 (Selene execution) to an existing data/encoded_codes.txt.
  --skip-exec   regenerate sections 1-4 only. Section 5 of the existing file (the slow
                Selene-executed rows, hours of compute) is PRESERVED and re-appended
                verbatim, tagged with a comment line saying it was carried over. The new
                file is assembled in a temporary path and moved into place only on success,
                so a crash mid-run leaves the committed file untouched.
                Review fix: this used to open the file in mode "w" and so silently
                destroyed section 5 on every --skip-exec run.
  --force       with --skip-exec, DROP the existing section 5 instead of preserving it
                (the old, destructive behaviour — only when you mean it).

Error bars (section 5), review fix: the per-shot Z2 = (sum Z)^2 / k^2 takes values in
{0, 0.25, 1} on k=4 logical qubits and is NOT a binomial proportion, so a Wilson /
Clopper-Pearson interval does not apply to it. Z2 therefore gets a Student-t interval:
+-1 standard error when at least MIN_SHOTS_FOR_SE kept shots support it, and an explicit
95% Student-t half-width tagged "[t95,n=..]" below that, so no misleadingly tight Gaussian
SE is ever printed on a handful of shots (one committed row had 5 kept shots). The
ACCEPTANCE fraction is a genuine binomial proportion and gets a Wilson 95% score interval.
"""

from __future__ import annotations

import math
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

from config import CONFIG  # noqa: E402
from src.backends_qc import Noise, run_bare_local  # noqa: E402
from src.compare import simulate_z2  # noqa: E402
from src.encoded_codes import (  # noqa: E402
    BareTFIM, EncodedTFIM, NoiseRates, detected_total, exact_logical_z2, gate_counts,
    logical_pauli_table, make_code, run_selene, to_stim, undetected_rate_per_step,
)
from src.encoded_tfim import IcebergTFIM  # noqa: E402
from src.qec.verify import verify_code  # noqa: E402

E = CONFIG.encoded
MAXS = CONFIG.ceilings.statevector_max_spins
H2 = 55
CODES = ["iceberg", "steane", "five", "concat"]
REDUCED = {"iceberg": (2, 2), "steane": (1, 2), "five": (1, 2), "concat": (2, 2)}
BUDGET_LATTICES = [(1, 2), (2, 2), (2, 3), (2, 4), (3, 4), (4, 4)]
SHOTS = {"iceberg": 1000, "five": 400, "steane": 300, "concat": 150}

# Below this many kept shots a Gaussian standard error is not a trustworthy interval
# (review): report an explicit 95% Student-t half-width and tag it instead.
MIN_SHOTS_FOR_SE = 20
SECTION5_MARK = "## 5."
CARRIED_OVER = ("# NOTE: section 5 below was PRESERVED from the previous run (--skip-exec does "
                "not regenerate it); its own timestamp above is the run that produced it.")


def z2_interval(vals: np.ndarray) -> str:
    """'<mean>±<halfwidth>' for the per-shot Z2 samples, honest about tiny n.

    Z2 per shot is in {0, 0.25, 1} (k=4) — bounded but NOT a binomial proportion, so no
    Wilson/Clopper-Pearson interval applies. n >= MIN_SHOTS_FOR_SE: ± one standard error
    (unchanged convention). 2 <= n < MIN_SHOTS_FOR_SE: ± the 95% Student-t half-width,
    tagged '[t95,n=..]'. n < 2: no interval at all, tagged '[no-interval,n=..]'.
    """
    n = len(vals)
    if n < 2:
        return f"{(vals.mean() if n else float('nan')):.4f}±nan [no-interval,n={n}]"
    se = float(vals.std(ddof=1) / np.sqrt(n))
    if n >= MIN_SHOTS_FOR_SE:
        return f"{vals.mean():.4f}±{se:.4f}"
    half = float(stats.t.ppf(0.975, n - 1)) * se
    return f"{vals.mean():.4f}±{half:.4f} [t95,n={n}]"


def wilson(k: int, n: int, z: float = 1.959963984540054) -> str:
    """'<p>±<w95 lo,hi>' Wilson 95% score interval for the BINOMIAL acceptance fraction."""
    if n == 0:
        return "nan [w95 nan,nan]"
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{p:.3f} [w95 {max(0.0, centre - half):.3f},{min(1.0, centre + half):.3f}]"


def _preserved_section5(path: str) -> str:
    """The existing file's section 5 (marker line to EOF), '' if the file has none."""
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if line.startswith(SECTION5_MARK):
            return "".join(lines[i:])
    return ""


def main():
    skip_exec = "--skip-exec" in sys.argv
    exec_only = "--exec-only" in sys.argv
    force = "--force" in sys.argv
    if skip_exec and exec_only:
        raise SystemExit("--skip-exec and --exec-only are mutually exclusive")
    path = os.path.join(REPO, CONFIG.data_dir, "encoded_codes.txt")

    # Review fix: --skip-exec must never destroy the slow section 5 it does not regenerate.
    preserved = _preserved_section5(path) if skip_exec else ""
    if skip_exec and preserved and force:
        print("--force: DROPPING the existing section 5 (hours of Selene compute).", flush=True)
        preserved = ""
    elif skip_exec and preserved:
        print(f"--skip-exec: preserving {len(preserved.splitlines())} lines of section 5 "
              "from the existing file (pass --force to drop them).", flush=True)
    # Assemble a skip-exec run in a temporary file and move it into place only on success,
    # so a crash cannot leave the committed data file truncated.
    out_path = path + ".partial" if skip_exec else path
    fh = open(out_path, "a" if exec_only else "w", encoding="utf-8")

    def log(s=""):
        print(s, flush=True)
        fh.write(s + "\n")
        fh.flush()

    if exec_only:
        return execute(log, fh)
    log(f"# Part B encoded-TFIM comparison — {time.strftime('%Y-%m-%d %H:%M')}")
    log("# Standard B (measured accounting, no pass/fail FT bar); budget (ii): H2 ~55 qubits; "
        "Stim at budget size; execution (selene) at reduced size <= 24 qubits.")
    log("# CAVEAT: classical predictions under ASSUMED generic depolarizing noise; not H2 results.")

    # ------------------------------------------------------------- 1. budget table
    log("\n## 1. Physical-qubit budget (data + 1 syndrome/rotation ancilla + 1 flag)")
    log(f"{'code':8s} " + " ".join(f"{f'{a}x{b}':>7s}" for a, b in BUDGET_LATTICES) + "   (<=24 local | <=55 H2)")
    for name in CODES:
        cells = []
        for a, b in BUDGET_LATTICES:
            k = a * b
            if name == "iceberg" and k % 2:
                cells.append("   odd")
                continue
            n = EncodedTFIM(make_code(name, k), a, b, "periodic", E.J, E.h, E.dt, E.theta).n_phys
            mark = "L" if n <= MAXS else ("H" if n <= H2 else "x")
            cells.append(f"{n:>5d}{mark:>2s}")
        log(f"{name:8s} " + " ".join(cells))
    log("   L = runs locally and fits H2; H = fits H2 only (Stim verification only here); x = exceeds ~55")

    # ------------------------------------------------- 2. logical-gate cost per step
    log("\n## 2. Logical operation cost (reduced lattice) — physical ops per Trotter step")
    for name in CODES:
        a, b = REDUCED[name]
        prog = EncodedTFIM(make_code(name, a * b), a, b, "periodic", E.J, E.h, E.dt, E.theta)
        gc = gate_counts(prog)
        log(f"{name:8s} {a}x{b}: weights field Xbar={prog.rep_x(0).weight}, bond ZbarZbar="
            f"{prog.rep_zz(*prog.bonds[0]).weight}, prep Ybar={prog.rep_y(0).weight}; per step: "
            f"{gc['2q']} two-qubit, {gc['1q']} one-qubit, {gc['meas']} measurements; "
            f"stabilizers per round {len(prog.stabs)}")
    bare = BareTFIM(2, 2, "periodic", E.J, E.h, E.dt, E.theta)
    log(f"bare     2x2: per step {len(bare.bonds)} two-qubit, {2 * bare.k} one-qubit")

    # ------------------------------------------------- 3. verification, reduced size
    log("\n## 3. Verification at the reduced (executable) size")
    for name in CODES:
        a, b = REDUCED[name]
        code = make_code(name, a * b)
        rep = verify_code(code.name, code.n, code.stabilizers, code.logical_x, code.logical_z)
        prog = EncodedTFIM(code, a, b, "periodic", E.J, E.h, E.dt, E.theta)
        silent = all(not to_stim(prog.schedule(2, bs), NoiseRates()).compile_detector_sampler(seed=1)
                     .sample(64, separate_observables=True)[i].any() for bs in "ZX" for i in (0, 1))
        trans = max(abs(exact_logical_z2(prog, s) - simulate_z2(a, b, "periodic", E.J, E.h, E.dt, E.theta, [s], MAXS)[0])
                    for s in (1, 2, 3))
        cl = EncodedTFIM(code, a, b, "periodic", E.clifford_J, E.clifford_h, E.dt, np.pi / 2)
        worst = max(np.abs(np.subtract(*logical_pauli_table(cl, s)[1:])).max() for s in (1, 2))
        log(f"{name:8s} {a}x{b}: verify_code {'PASS' if rep.ok else 'FAIL'}; clean Stim images silent {silent}; "
            f"transparency max|dZ2| {trans:.1e}; Stim<->local over all {4 ** prog.k} logical Paulis "
            f"(Clifford instance) max|d| {worst:.1e}")

    # ------------------------------------------------- 4. accounting at budget size
    log("\n## 4. MEASURED undetected-logical probability per Trotter step (Stim, first order)")
    for p2 in E.p2_scan[:2]:
        nz = NoiseRates(p2=p2, p1=p2 * E.p1_ratio, pm=p2 * E.pm_ratio, p_init=p2 * E.init_ratio)
        log(f"\n### p2={p2:g}, p1=pm=p_init={p2 * E.p1_ratio:g} [assumed]")
        for lat in [(1, 2), (2, 2), (2, 3)]:
            a, b = lat
            row = []
            for name in CODES:
                if name == "iceberg" and (a * b) % 2:
                    row.append(f"{name} n/a")
                    continue
                prog = EncodedTFIM(make_code(name, a * b), a, b, "periodic", E.J, E.h, E.dt, E.theta)
                if prog.n_phys > H2:
                    row.append(f"{name} >55")
                    continue
                u = undetected_rate_per_step(prog, nz)
                acc3 = np.exp(-detected_total(prog, nz, 3))
                row.append(f"{name}(n={prog.n_phys}) undetected {u['total']:.2e} acc@3 {acc3:.3f}")
            ub = undetected_rate_per_step(BareTFIM(a, b, "periodic", E.J, E.h, E.dt, E.theta), nz)["total"]
            log(f"{a}x{b}: " + " | ".join(row) + f" | bare unprotected {ub:.2e}")
    log("   acc@3 = exp(-first-order detection probability of the 3-step program incl. prep) [Stim]")

    if skip_exec:
        if preserved:
            fh.write("\n" + CARRIED_OVER + "\n" + preserved.lstrip("\n"))
            fh.flush()
        fh.close()
        os.replace(out_path, path)
        print(f"wrote {path}" + (" (section 5 carried over)" if preserved else ""), flush=True)
        return
    execute(log, fh)


def execute(log, fh):
    # ------------------------------------------------- 5. execution (selene), reduced size
    log(f"\n## 5. Executed on Selene (Quest) at the reduced size; bare = local-sim, same rates "
        f"({time.strftime('%Y-%m-%d %H:%M')})")
    log(f"# accept: Wilson 95% score interval [w95 lo,hi] (binomial). Z2: ± one standard error "
        f"when n_kept >= {MIN_SHOTS_FOR_SE}, otherwise ± the 95% Student-t half-width tagged "
        f"[t95,n=..]; per-shot Z2 is not a binomial proportion, so no Wilson interval applies.")
    for name in CODES:
        a, b = REDUCED[name]
        prog = EncodedTFIM(make_code(name, a * b), a, b, "periodic", E.J, E.h, E.dt, E.theta)
        ideal = simulate_z2(a, b, "periodic", E.J, E.h, E.dt, E.theta, [1, 2, 3], MAXS)
        sp_bare = IcebergTFIM(a, b, "periodic", E.J, E.h, E.dt, E.theta) if (a * b) % 2 == 0 else None
        for p2 in E.p2_scan[:2]:
            nz = NoiseRates(p2=p2, p1=p2 * E.p1_ratio, pm=p2 * E.pm_ratio, p_init=p2 * E.init_ratio)
            for s in (1, 2, 3):
                t = time.time()
                res = run_selene(prog, s, SHOTS[name], nz, seed=11 * s + int(p2 * 1e5), max_spins=MAXS,
                                 n_processes=2)
                acc = np.array([x for x, _ in res])
                vals = np.array([v for x, v in res if x])
                m2 = ((vals.sum(1) ** 2) / prog.k ** 2 if len(vals)
                      else np.zeros(0, dtype=float))
                zfield = z2_interval(m2)
                bl = ""
                if sp_bare is not None:
                    zb = run_bare_local(sp_bare, s, 1000, Noise(p2=nz.p2, p1=nz.p1, pm=nz.pm, p_init=nz.p_init),
                                        seed=500 + s, max_spins=MAXS)
                    mb = (zb.sum(1).astype(float) ** 2) / prog.k ** 2
                    bl = f" | bare Z2 {z2_interval(mb)}"
                log(f"{name:8s} {a}x{b} p2={p2:g} step {s}: "
                    f"accept {wilson(int(acc.sum()), len(acc))} (n={len(acc)}) "
                    f"| enc Z2 {zfield} (n_kept={len(m2)}) | ideal {ideal[s - 1]:.4f}{bl} "
                    f"({time.time() - t:.0f}s)")
    fh.close()


if __name__ == "__main__":
    main()
