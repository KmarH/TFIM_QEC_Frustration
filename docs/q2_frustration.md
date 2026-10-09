# Q2 frustration: triangular vs square on shared observables (handoff/09)

**Code:** `src/frustration.py` · **tests:** `tests/test_frustration.py` (14) · **script:** `scripts/compare_frustration_correlations.py` → `data/frustration_correlations.txt` · **settings:** `config.py: Q2FrustrationConfig` (`CONFIG.q2`).

> **Status:** classical exact diagonalization only. Every number is [measured] (exact, so there is no sampling error) or [derived]. **None is an H2 or hardware result.** No noise, no encoding. The clock-order parameter (K3) and diffusion (K5) are **not** built.

Model: H = −J Σ ZZ − h Σ X with **J = −1** (antiferromagnetic in our sign), periodic tori, h ∈ {0, 0.1, 0.3, 0.6, 1.0} (as in `data/frustration_compare.txt`).

## Part A — distance-resolved connected correlations, square vs triangular (reviewed ACCEPT, review/12)

### A.1 Method

**Ground state [derived].** H commutes with the global spin flip P = Π X.
- For h > 0 every off-diagonal element is −h ≤ 0 and every basis state is reachable, so by Perron–Frobenius the ground state is **unique, positive and P-even**, with ⟨Z_i⟩ = 0 exactly.
- On a finite torus, a near-ordered state has a P-odd partner only exponentially higher in energy. On the 4×4 square at h = 0.3, E₁ − E₀ is **below numerical resolution (< 1e-13)**: the measured 4e-14 is noise, and the h = 0.6 and 1.0 gaps (1.8e-10, 5.5e-7) extrapolate to ~1e-15 [inferred]. An unrestricted Lanczos vector there comes out as an **arbitrary** symmetry-broken mixture: |⟨Z_i⟩| ranged from ≈ 0.01 to ≈ 0.5 over repeated `run_ed` calls [measured, internal pre-review]. That corrupts single-vector connected correlators.
- So the ground state is computed **exactly in the P-even sector**, with basis (|r⟩ + |r̄⟩)/√2. Its energy equals `src.backends.run_ed`'s to within **2.6e-12** at every point (the `dE_ED` column; worst case triangular 4×4 at h = 0.1, typically ~1e-13; tested).
- At **h = 0** the ground state is degenerate on both lattices (massively on the triangular one). The h = 0 C(r) is recorded but **not interpreted**.

**Observable.** C(r) = the mean over all pairs at distance r of the **connected** ⟨Z_iZ_j⟩ − ⟨Z_i⟩⟨Z_j⟩, from `src.observables.two_point_correlations_z(connected=True)`. The spread [lo, hi] inside a shell is kept, because inequivalent directions on anisotropic tori differ.

**Distance metric (stated).** Minimal-image **Euclidean** site distance in each lattice's natural embedding, with nearest neighbours at 1.
- Square: (x, y).
- Triangular: x e₁ + y e₂ with e₁ = (1, 0), e₂ = (−½, √3/2), the `src/dimers.py` embedding (`TriangularDimers._pos`).
- Tested: the r = 1 shell is exactly the bond list on both lattices, and the shell counts sum to N(N − 1)/2.
- This is site-spin ⟨ZZ⟩_c, not the dimer C_r of 2503.20870, so the T-7 graph-vs-Euclidean question does not apply here.

### A.2 A correction to the existing Q2 table [measured]

**A square torus with an odd periodic length is not bipartite, so its antiferromagnet is itself frustrated.** The h = 0 energy per bond is:

| torus | E/bond at h = 0 |
|---|---|
| square 4×4 (bipartite) | **−1** |
| square 3×4 | **−2/3** |
| square 4×5 | −0.8 |

`data/frustration_compare.txt` (3×4) and the interpretation in `scripts/compare_frustration.py` call the 3×4 square lattice "unfrustrated". **That is not true at 3×4**: its square reference already carries odd-length frustration. Its −0.667 vs −0.333 energy-per-bond contrast is *partly* boundary frustration.

**The only square torus with both lengths ≥ 3 within the ED ceiling that is a clean unfrustrated reference is 4×4.** 4×4 is therefore the main matched pair here; 3×4 is kept for continuity and flagged. This was not silently changed in the existing files (they are not this brief's files); it is raised as T-19.

### A.3 Results [measured; data/frustration_correlations.txt]

**Matched 4×4 pair** (square bipartite; triangular frustrated, and its torus is not a multiple of 3):

| h | square C(1) | square C(r_max = 2.83) | triangular C(1) | triangular C(√3) | triangular C(r_max = 2) |
|---|---|---|---|---|---|
| 0.1 | −0.999 | +0.999 | −0.332 | −0.055 | +0.442 |
| 0.3 | −0.994 | +0.994 | −0.325 | −0.045 | +0.413 |
| 0.6 | −0.977 | +0.977 | −0.268 | +0.029 | +0.196 |
| 1.0 | −0.936 | +0.936 | −0.204 | +0.053 | +0.068 |

**3×4 pair, for continuity** (square frustrated by its odd length): at h = 0.3, square C(1) = −0.657 (spread −0.98 / −0.33 between the length-4 and the frustrated length-3 direction) and C(√5) = −0.331; triangular C(1) = −0.328, C(√3) = +0.458, C(2) = −0.688.

**Reading.**
- **Nearest-neighbour suppression is robust.**
  - On the matched 4×4 pair the triangular C(1) is 3–5× weaker than on the bipartite square (−0.20…−0.33 vs −0.936…−1.00). On 3×4 the ratio is ≈ 2×, but that square torus is not bipartite.
  - The triangular C(1) is near −1/3 ("one frustrated bond per triangle") at small h and falls to −0.27 (h = 0.6) and −0.20 (h = 1.0).
  - With ⟨Z⟩ = 0, C(1) is exactly the **ZZ part** of the energy per bond (E_ZZ / (−J · n_bonds)). So it restates that signature in correlation form rather than adding to it.
- **What the distance resolution adds.** On the bipartite square the connected correlations **do not decay across the torus**: |C(r)| ≈ 0.94–1.00 at every distance and field scanned (finite-size Néel order). On the triangular lattice they are much weaker at long distance and **fall fast with h** (4×4: C(2) = +0.44 → +0.07 from h = 0.1 to 1.0, while the square stays ≥ 0.935). Caveat on "same h": equal h is not equal distance from each lattice's critical field. The square-lattice TFIM critical field is h_c ≈ 3.04|J| [unverified — recalled standard QMC value; the source usually cited for it, Blöte & Deng, PRE 66, 066110 (2002), was confirmed only at abstract level (a cluster-MC study of the square-lattice transverse Ising model), and the number itself was not re-read; not computed here]; the triangular one is lower, ≈ 1.6|J| in the Isakov–Moessner phase diagram [unverified — recalled, not re-read]. Part of the triangular "field fragility" is that offset.
- **The triangular pattern is torus-shape dependent, as the disorder-line caveat warns.** At h = 0.3 the √3 shell is +0.46 on 3×4 but −0.04 on 4×4, and the r = 2 shell is −0.69 on 3×4 but +0.41 on 4×4: opposite signs.
  - The repo's triangular embedding sits at the J′ = J point of Iglovikov et al. (PRB 87, 214415, arXiv:1303.0883 **[established]**), near a Stephenson disorder line / incommensurate floating phase.
  - A torus whose lengths are not multiples of 3 (4×4) frustrates the three-sublattice pattern differently from one with a length-3 direction (3×4), so the long-distance signs follow the torus shape.
  - **No "frustration monotonically weakens order" story is read into the long-distance triangular numbers.** Only the like-for-like statements above are made: weaker nearest-neighbour correlation, weaker and field-fragile long-range correlation.

### A.4 Flag for the project lead (do not build): the data point at K3

The positive √3 shell on the 3-sublattice-compatible direction (3×4) is the real-space pattern of three-sublattice (clock) correlations. The canonical phase diagram has an order-by-disorder clock phase at small h (Isakov–Moessner, PRB 68, 104409 **[established]**; Humeniuk, PRB 93, 104412 **[fetched]**).

**C(r) alone cannot separate clock correlations from the torus-shape effects of A.3; the observable that would is the clock-order parameter, which is K3 and is undecided.** It is **not built here**, as the brief requires, and per PROC-2 (no new classical depth after handoff/09) it would be the project lead's call anyway. Recorded as T-20.

### A.5 What Part A does not claim

- No thermodynamic-limit or phase statement. These are N = 12–16 exact ground states.
- No clock order.
- No dimer or defect comparison with the square lattice: that structure is triangular-only. (The presence-vs-absence contrast was planned for Part B, which is cancelled.)

*Part B (size trend, error bars, winding/defect presence-vs-absence) was **CANCELLED** by the project lead under PROC-2 (no new classical depth after handoff/09; journal Entry 42). Part A, reviewed ACCEPT in review/12, is the Q2 result. Within ED ≤ 20 a square size trend would have only one clean (bipartite) point, 4×4 (T-21).*
