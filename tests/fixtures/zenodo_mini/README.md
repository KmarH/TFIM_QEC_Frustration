# zenodo_mini — SYNTHETIC test fixture (not real data)

A tiny stand-in with the same file names, formats (`%.18e`, no header) and shapes as the
dataset described in `research/05-zenodo-dataset-map.md`, so `tests/test_compare.py` runs
offline. **All observable values here are synthetic ramps/constants, not H2 measurements.**
Only the structure (step-index vectors, M = 12/20/10/8, `dimercorrs` stored [r, step],
`_err` siblings) mirrors the real dataset. `quench1_Z2_znr_unamplified.txt` is deliberately
malformed (11 rows vs 12 steps) to test the loader's shape check.

The real dataset (DOI 10.5281/zenodo.18487089, 12.5 MB) is never committed; point
`CompareConfig.data_path` or `TFIM_ZENODO_DATA` at the unzipped `zenodo_data/`.
