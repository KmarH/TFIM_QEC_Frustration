# Review 05 — Handoff 02: triangular dimers / winding / emergent Gauss law / mitigation verdict

**Reviewer:** qc-reviewer (independent milestone review)
**Date:** 2026-10-06
**Scope reviewed:** `src/dimers.py` (`TriangularDimers`), `src/gauss_mitigation.py`,
`config.py: GaussLawConfig`, `scripts/run_gauss_law.py`, `tests/test_dimers.py` (34 tests),
`data/gauss_law_scaling.txt`, `data/gauss_law_mitigation.txt`, `docs/gauss_law_dimers.md`.
Supporting reads: `handoff/02-triangular-dimer-gauss-law.md`, `SCOPE.md §3/§12`,
`research/03-stage3-triangular.md`, `review/04-stage3-triangular.md`.
**Rule:** I did not edit any src/tests/config file. Every number below is from a command I ran
myself; where I reconstructed an identity I did so independently of the repo's own asserts.

**Verdict: APPROVE.** The §3 identities are proved and I reproduced them exhaustively over the
full basis; the (h/|J|)² scaling is a genuine fit to data that I re-fit; §5 cleanly separates the
physics floor from the noise signal under a stated model; and the mitigation verdict is defensible
and, if anything, understated. No invented numbers; no platform overclaim. Findings are all MINOR
(documentation / scope hygiene). SCOPE §3's skeptical prior is respected — the headline is "mostly
NO, a narrow conditional YES."

---

## Environment

```
$ . /home/opc/KiroTest-project/.venv/bin/activate
$ python -c "import numpy,scipy,stim,sys; print(sys.version.split()[0]); print(numpy.__version__,scipy.__version__,stim.__version__)"
3.12.14
2.5.3 1.18.1 1.16.0
$ python -m pytest -q
93 passed in 11.12s
$ python -m pytest tests/test_dimers.py -q
34 passed in 6.24s
$ python -m pytest tests/test_dimers.py --collect-only -q | grep -c "::"
34
```
Serial, local. Full suite **93/93**, dimer file **34/34** (brief says 34 — matches). Python is
3.12.14, not the 3.11 pinned in SCOPE §7 — a pre-existing environment note already raised in
review/04 (Minor-3 there), repeated here only for the record.

---

## What passes plainly (independently verified)

### 1. §3 exact identities — PROVED and reproduced exhaustively (Doc §7 item 1, brief item 1)

Proof sketches are present inline in `src/dimers.py`'s module docstring and `docs/gauss_law_dimers.md §3`
(G_t∈{1,3} because a triangle has 1 or 3 parallel pairs; Σn_b=N+ΣD by counting; energy corollary;
A/B charge neutrality from the honeycomb being bipartite; winding row-difference = enclosed charge;
QDM commutators from flippable moves preserving all six surrounding triangles). These are derivations,
not citations, and are correctly tagged `[derived]`.

I re-derived the two the brief singled out (energy identity, charge neutrality) **from a fresh
triangle enumeration and raw Z-strings over the full 2¹²=4096 basis on a 3×4 torus**, not from
`TriangularDimers`' own asserts:
```
G_t values over full basis: [1, 3]            -> expect {1,3}
sum_b n_b == N + sum_t D_t  : True
charge neutral  DA==DB      : True
Ising energy == |J|(2 sumD - N): True   max|diff|= 0.0
defects always even: True
```
All exact. The repo's own exhaustive test (`test_gauss_law_identities_exhaustive`) runs the same
checks over 3×3/3×4/4×3 and passes.

Winding as a row/column-independent sector label, the commutators, and the reference sector values,
again reconstructed independently:
```
3x4 defect-free count: 68
winding row/col-independent on free subspace: True
3x4 distinct (Wx,Wy) sectors: [(0,-4),(0,2),(6,-4)]  n=3
3x3 free count: 42  sectors: [(0,0)]               <- single sector; winding needs >=3x4 (caveat correct)
3x6 stripe   (D,Wx,Wy): (0, 6, -6)   formula (2Lx,-Ly)=(6,-6)   -> (18,-6) on 9x6
3x6 3-sublat (D,Wx,Wy): (0, 0, 0)
max|[H_QDM,O]| over all D_t,Wx,Wy: 0.0
|[H_TFIM, sum D]| max: 1.8
```
[H_QDM, D_t]=[H_QDM,W]=0 to machine zero (exactly 0.0, not ~1e-15 — the QDM matrix is integer-signed
and the operators are integer-diagonal, so this is a true algebraic zero), while [H_TFIM, ΣD]≠0.
The 3×3-single-sector caveat is stated in §3 and §4 of the doc and enforced in practice (winding
work uses ≥3×4). **All of brief item 1 confirmed.**

### 2. (h/|J|)² scaling is a fit to data; stripe prefactor matches first-order theory (Doc §7 item 2, brief item 2)

I independently re-fit the ED ground-state defect-density log–log slope and re-ran the stripe quench:
```
3x4 ED gs slope=1.984   dens=[3.02e-05 1.20e-04 4.77e-04 1.88e-03 4.18e-03]
3x6 ED gs slope=1.963
stripe h=0.025 dt=0.025: <D/tri>=7.852e-05  pred(h^2/8)=7.813e-05  ratio=1.005
stripe h=0.3   dt=0.025: ratio=1.016
stripe h=0.3   dt=0.25 : ratio=1.105
```
Slopes 1.98 (3×4) / 1.96 (3×6) sit inside the brief's expected 1.96–2.05 band and match the overseer's
1.986. Stripe time-averaged defect density / (h/|J|)²/8 = **1.005** at small h (matches the overseer's
1.005); at the reference dt=0.25 the ratio rises to ~1.10, which the doc explicitly attributes to Trotter
error ("about 10% higher"). The data file reports slopes directly from the scan, and the test
`test_ed_ground_state_...scales_as_h_squared` asserts |slope−2|<0.1. **Scaling is measured, not assumed.
Confirmed.**

### 3. §5 separates physics floor from noise signal; Z invisible; verdict supported (Doc §7 item 3, brief item 3)

Noise model is stated in `config.GaussLawConfig` and §5.1 (per-qubit-per-step Pauli channel;
depolarizing / dephasing / bit-flip; p∈{1e-3,3e-3,1e-2}; exact DM on 3×3, 400-trajectory cross-check on
3×4; 10⁴ shots for bars). Every mitigation row prints the noiseless **floor** alongside the noisy value,
and `err = sqrt(bias² + cost·Var/shots)` carries shot noise. I verified the kit's correctness and the
headline detection facts:
```
single_error_detection initial: {'X':0.3333,'Y':0.3333,'Z':0.0}      <- Z exactly 0, X/Y>0
pure X: dD/dp=+36.575   pure Y: dD/dp=+36.867   pure Z: dD/dp=+0.522  <- ~70x asymmetry (matches data)
Y-channel exact (vs explicit kron Y): True;  trace preserved: True
DM == statevector noiseless: True
global-depol selfmit Fhat=0.7000 (expect 0.7), est matches ideal: True
noiseless postselect keeps 0.9789, NNN<ZZ> floor bias=+0.0135
dephasing p1e-3 t10 NNN<ZZ>: raw bias=-0.0459 -> postselect bias=-0.0312  (barely moves)
```
And the trajectory cross-check row reproduces exactly:
```
depol 3e-3 t10 NNN<ZZ>: raw bias=-0.1975+-0.0089 -> postselect=+0.0151+-0.0010
```
These match `data/gauss_law_mitigation.txt` line-for-line. The verdict holds against the data:
- **Correction NO** — distance 1 (undetectable weight-1 Z anywhere, X/Y on flippable spins), no
  syndrome→recovery, constraint violated by the ideal dynamics. Structurally correct.
- **Postselection modest-YES, X/Y only, floored O((h/J)²)** — supported: 2–8× bias cut on spin
  correlators at p≤3e-3, residual pinned at the ~0.013 physics floor; under dephasing it only moves the
  sign (−0.046→−0.031), i.e. the residual is floor not noise.
- **Depolarizing self-mitigation NO as a general method** — supported: F_gauss ≠ per-observable true F
  (data rows show it making m worse by up to 13×); the test confirms the estimator is exact *only* under
  true global depolarizing, so the failure is the noise model, not the code.
- **Exact-symmetry methods N/A for a Z-product quench** — correct: ⟨P⟩=⟨ΠX⟩=0 on a Z-basis product
  state and a Pauli channel keeps it 0, so there is no sector to project; U(1)-shadow methods need a
  symmetry the TFIM lacks. Properly `[derived]`.
- **Platforms undetermined** — see item 4.

**All of brief item 3 confirmed; the verdict is if anything understated (it leads with the negatives).**

### 4. No platform claim beyond the §5.4 conditional (Doc §7 item 4, brief item 4)

A text scan found four platform mentions; every one is tagged `[unverified]` (the draft's
neutral-atoms-best / H2-worst ranking), marked **open** (loss/erasure outside the Pauli model), or is a
citation-table fidelity figure. The "where (platforms)" line is explicitly **"undetermined by this
study"**, conditioned on the residual channel's X/Y fraction, with "no hardware data was used." The
draft's own numbers (per-Pauli ε, Cai Eq. 40, calibration transfer, "2–7×, up to 24×") are left
`[unverified]` in §5.5. **No hardware-calibrated assertion. Confirmed.**

### 5. Winding normalization & reference sectors; suite still 93/93 (Doc §7 item 5, brief item 5)

W = 3·flux − L. Stripe → (2Lx, −Ly) = (18,−6)-type maximal sector; 3-sublattice → (0,0); both reproduced
above and asserted in `test_reference_sector_values`. The 3×3-single-sector caveat is stated and
observed. Full suite **93/93** (shown in Environment). **Confirmed.**

### 6. PEC overheads & reference-scale context

Reproduced independently: γ² at (54 qubits, 40 steps) = **5.67e3 / 1.85e11 / 4.46e37** for
p=1e-3/3e-3/1e-2 — matches the data file and §5.3 item 4. Richardson coeffs for λ=(1,2,3) = [3,−3,1]
(exact), ZNE cost 57× as reported.

---

## Findings

### Critical
None.

### Major
None.

### Minor

- **Minor-1 (one `[fetched]` citation needs qc-researcher sign-off, not reviewer-verifiable here).**
  `src/dimers.py` docstring and doc §2 attribute the spin→dimer map to "Moessner–Sondhi (PRB 63, 224401
  (2001), **journal ref to be confirmed by qc-researcher**)" and the operator/sector forms to
  arXiv:2503.20870 §V, tagged `[fetched]` (automated summary, not line-checked) and `[inferred]` (the
  winding normalization). This is correctly flagged in-text, and the *mathematics* is independently
  proved and tested here regardless of the citation. No action in code; the open item is simply that
  qc-researcher must close the Moessner–Sondhi journal ref and confirm the reference's exact winding
  orientation/sign (doc §2 already says "whether its '9' is our Lx is unverified"). Does not block.

- **Minor-2 (naming: "self-mitigation NO" is proven only for the two floors implemented).**
  §5.3 item 2 and the verdict say depolarizing self-mitigation fails "as a general method." The evidence
  (F_gauss ≠ true per-observable F under *local* noise; data rows) fully supports that for the oracle and
  naive floors coded in `Targets.selfmit`. The claim is correctly scoped to "global-depolarizing
  rescaling from the defect density" and not overstated, but a reader skimming the one-line verdict could
  read it as broader than the single estimator family tested. Suggest (doc-only, qc-annotator) a half-
  sentence pointing the verdict line back to "the global-depolarizing rescaling of §5.3." Not a
  correctness issue.

- **Minor-3 (pre-existing, carried) Python pin.** SCOPE §7 pins 3.11; venv is 3.12.14. Already raised in
  review/04; flagged again for environment-freeze reconciliation. No effect on this milestone's
  correctness.

- **Minor-4 (stray non-ASCII identifier in nothing shipped — N/A to repo).** During my own throwaway
  reconstruction I noticed how easy it is to typo the Greek-looking defect accumulators; the *shipped*
  code uses clean ASCII (`DA`, `DB`) and is fine. No action — noted only so it is clear I inspected the
  accumulation logic and it is correct.

---

## Notes on design choices (not findings)

- Keeping every observable **diagonal** on the row-major index (Z-strings, defects, winding, QDM as a
  signed permutation) is what makes the exhaustive full-basis identity tests and the exact-DM mitigation
  benchmark cheap and exact. Good choice; it is why the commutators come out as algebraic zeros.
- `most_flippable_state` reduces to the 3-sublattice state when Lx,Ly are both divisible by 3 (confirmed:
  `3x3 most_flippable == 3-sublattice: True`), and otherwise searches the defect-free set — a sensible,
  reproducible way to pick the richest constrained initial state.
- The mitigation benchmark correctly uses the **exact density matrix** on 3×3 as ground truth and the
  trajectory sim only as a larger-N cross-check; the two agree within batch SE (`test_trajectories_...`).
- Size limits are honestly stated in §5.5 (3×3 exact / 3×4 trajectories vs the reference's 9×6; size
  trends `[inferred]`), consistent with SCOPE §5 ceilings.

---

## Open items

1. (Minor-1) qc-researcher: close the Moessner–Sondhi journal ref and confirm arXiv:2503.20870's exact
   winding orientation/sign and dimer-pair convention from the supplement; until then §2's normalization
   stays `[inferred]`. The derivation and tests do not depend on this.
2. (Minor-2) qc-annotator (doc-only): tie the one-line "self-mitigation NO" verdict back to the specific
   global-depolarizing-rescaling estimator in §5.3 so it cannot be read more broadly than tested.
3. (Minor-3) Reconcile the Python 3.11 pin (SCOPE §7) with the 3.12 venv before any environment freeze.
4. (Carried) The draft's unreplicated numbers (per-Pauli ε, Cai Eq. 40, calibration transfer, the
   "2–7×/24×" gains) remain `[unverified]`; the mitigation study does not rely on them, and the verdict
   is independent of them.

**Verdict: APPROVE.** The identities are proved and I reproduced them exhaustively; the h² scaling is a
real fit (slopes 1.96–1.98, stripe prefactor 1.005); §5 separates physics floor from noise signal under a
stated model with shot-noise bars; the mitigation verdict (correction NO; postselection a narrow
X/Y-only, floored YES; self-mit NO as a general method; exact-symmetry N/A; platforms undetermined) is
supported by the data and keeps SCOPE §3's skeptical prior. All findings are minor documentation/scope
hygiene and do not block the milestone.
