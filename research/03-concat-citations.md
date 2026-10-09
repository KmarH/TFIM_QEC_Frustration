# Citation check — concatenated Iceberg d=4 write-up

Scope: confirm the two `[cite-unverified]` references in
`docs/concatenated_iceberg_d4.md`. Method: fetched the Nature DOI landing page and
arXiv abstract/HTML directly (2026-10-06). Per SCOPE §11: IDs reported as-found; nothing
invented or "fixed."

Status legend: **verified** (resolves and supports the attached claim) /
**corrected-locator** / **unresolved**.

---

## A. Knill — C4/C6 concatenation scheme

- Cited in write-up §1: "This multi-block interleaving is the same pattern as Knill's
  C4/C6 scheme (Nature 434, 39 (2005))."
- As given: E. Knill, "Quantum computing with realistically noisy devices," Nature 434, 39 (2005).

**Status: VERIFIED. Locator correct.**

- Resolves: **yes.** DOI `10.1038/nature03350`, `https://www.nature.com/articles/nature03350`.
- Locator: **correct.** Nature **volume 434, pages 39–44 (2005)**, published 03 March 2005.
  Issue 7029. (The write-up's "39" is the first page; full range 39–44.)
- arXiv preprint of the same work: `quant-ph/0410199` (ADS bibcode 2005Natur.434...39K).
- Supports the claim: **yes.** The paper is the canonical C4/C6 reference. Its **Figure 1 is
  titled "Block structure of C4/C6 concatenated codes,"** and the architecture is a
  distance-2 code (C4 = the [[4,2,2]] code) concatenated — with C6 at the next level — using
  multi-block/postselected teleportation-based error correction (Figs. 2–4 cover
  postselection and error-correction performance). This matches the write-up's use: it is
  cited only as a precedent for the *multi-block interleaving pattern* of concatenating a
  distance-2 code, not for any quantitative claim.

Caveat (not a defect): the write-up's construction concatenates the **Iceberg [[k+2,k,2]]**
code with itself, whereas Knill's C4 is the [[4,2,2]] code and the scheme adds C6 and
postselected teleportation. The citation is an analogy ("same pattern"), which the source
supports; it is not claimed to be the identical construction.

**May drop `[cite-unverified]`: YES.** Suggested final form:
E. Knill, "Quantum computing with realistically noisy devices," Nature **434**, 39–44 (2005),
doi:10.1038/nature03350.

---

## B. Chao & Reichardt — single-flag FT syndrome extraction

- Cited in write-up §4: "Every stabilizer uses one ancilla + one flag (Chao–Reichardt single
  flag, arXiv:1705.02329)."
- As given: arXiv:1705.02329.

**Status: VERIFIED (resolves and supports the claim). Recommend tightening the title/framing.**

- Resolves: **yes.** `https://arxiv.org/abs/1705.02329`, submitted 5 May 2017.
- Title: **"Quantum error correction with only two extra qubits"** (R. Chao, B. W. Reichardt).
  Note: the write-up labels it "single flag," which is accurate for the mechanism (one syndrome
  ancilla + one flag qubit = the "two extra qubits" of the title), but the paper's own title/framing
  is "two extra qubits." This is the paper usually credited (alongside Chamberland–Beverland
  1708.02246) with single-flag FT error correction.
- Journal reference: **Phys. Rev. Lett. 121, 050502 (2018)**, doi:10.1103/PhysRevLett.121.050502.
- Supports the claim: **yes.** Abstract and §I: the procedures "add 'flags' to the
  syndrome-extraction circuits in order to catch the faults that can lead to correlated errors
  on the data" — i.e. exactly the hook-error detection the gadget relies on. Introduction states
  "Provided that syndromes are extracted in a careful order, detecting the possible presence of a
  correlated error is enough to correct it," which matches the write-up's claim that an ancilla
  fault spreading to ≥2 data qubits flips the flag and the careful CNOT order is what makes it work.
- Direct relevance bonus (worth noting, not required): the paper has a dedicated section
  **"V. Two-qubit fault-tolerant error detection for [[n, n−2, 2]] codes"** — the Iceberg family
  itself. So the flag technique is applied in the source to exactly the distance-2 code class the
  write-up concatenates, strengthening the citation.

Caveats (not defects, two accuracy nuances):
1. The paper's main results target **distance-3 codes** (correction with two extra qubits). The
   write-up uses only the *flag mechanism* (detect-only, one ancilla + one flag), which the paper
   supports both in general and specifically for [[n,n−2,2]] codes in §V.
2. "Single flag" vs the paper's "two extra qubits": consistent (1 syndrome ancilla + 1 flag), but
   consider citing by exact title to avoid ambiguity.

**May drop `[cite-unverified]`: YES.** Suggested final form:
R. Chao and B. W. Reichardt, "Quantum error correction with only two extra qubits,"
Phys. Rev. Lett. **121**, 050502 (2018), arXiv:1705.02329. (A single syndrome ancilla + single
flag; see §V for the [[n,n−2,2]] detection case directly applicable to Iceberg.)

---

## Summary

| # | Citation | Resolves | Locator | Supports claim | Drop [cite-unverified]? |
|---|----------|----------|---------|----------------|-------------------------|
| A | Knill, Nature 434, 39 (2005) | yes | correct (434, 39–44, 2005; doi:10.1038/nature03350) | yes — Fig. 1 "Block structure of C4/C6 concatenated codes" | **yes** |
| B | Chao–Reichardt, arXiv:1705.02329 | yes | correct; add PRL 121, 050502 (2018) | yes — flag syndrome extraction, incl. §V [[n,n−2,2]] | **yes** (recommend citing by exact title) |

Both citations are confirmed from primary sources; neither ID was altered. The write-up may drop
both `[cite-unverified]` tags. Recommended hygiene when finalizing: cite B by its exact title
("...only two extra qubits") rather than "single flag," add the PRL journal reference, and add the
page range + DOI to A. These are editorial, not correctness, issues.

## Open questions for overseer / user
- Review condition (m3) asks to add `[cite-unverified]` to the two **src docstrings** to match the
  write-up. Given both are now verified, the better reconciliation is to **drop the tags everywhere**
  (write-up and docstrings) and use the finalized citation forms above — not to propagate the
  unverified tag into src. Confirm which direction you want before the docstring edit lands.
- Confirm whether the report should cite the arXiv preprint (quant-ph/0410199) alongside the Nature
  DOI for Knill, for readers without journal access.
