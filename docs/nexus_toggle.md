# Flipping the encoded-TFIM toggle to `nexus` — what it will take

`src/backends_qc.run(..., backend="nexus")` currently raises `NotImplementedError` by design (handoff/04, SCOPE §5). The program objects are already Nexus-shaped:
- the authored **pytket segments** (`IcebergTFIM.prep_segment / trotter_segment / syndrome_segment`), which contain only `H`, `CX`, `ZZPhase`;
- the **Guppy program** that wraps them (`build_guppy_program`), with mid-circuit measurement, reset and feedforward discard.

Flipping the toggle is integration work, not a rewrite. It requires the following, in order. Items marked **[unverified]** must be confirmed against the live documentation before use; none were exercised here.

1. **Gate on SCOPE §5.** Set `HardwareConfig.allow_hardware = True` **and** get Kevin's explicit per-run approval, because every submission spends credits. The stub must remain the default.
2. **Dependencies.** Add and pin the Quantinuum client stack: `qnexus` and/or `pytket-quantinuum` **[unverified: package names and versions current for Nexus submission; Python 3.12 vs pinned 3.11, FLAG A]**. Neither is installed or pinned now.
3. **Nexus project and authentication.** Log in to Nexus (interactive or token) and select or create a Nexus project for these jobs **[unverified: exact login and project API]**. Credentials never enter the repo or `config.py`.
4. **Target.** Choose an **H2 emulator** first, then hardware, by the device name the account actually exposes **[unverified: device identifiers]**. The emulator should be compared against our `selene` curves before any hardware HQC is spent.
5. **Compilation and submission path.** Either:
   - (a) compile the pytket segments with the backend's default compilation pass and submit them as circuits, which **loses** our in-program feedforward discard (the shot is post-selected classically instead); or
   - (b) submit the **Guppy/HUGR** program so mid-circuit measurement and feedforward run on the device **[unverified: whether and how Nexus accepts Guppy/HUGR programs for H2 at the version we pin]**.

   Path (b) is the one that tests what Part A was built for.
6. **Cost before run.** Request the backend's **HQC cost estimate** for every job and record it next to the approval. The encoded program per Trotter step (2×3 logical lattice) is about 21 ZZPhase logical gates plus 2 flagged syndrome rounds, roughly 24 CX. Shots × steps × p-points multiply quickly, and the measured discard rate (see `data/encoded_iceberg.txt`) divides the useful shots.
7. **Results.** Map Nexus results onto `ShotRecord` (rounds `sz, fz, sx, fx`, final data bits) so the existing `accepted()` and `z2_from_logical()` run unchanged. Label every number as a **hardware** result, distinct from the local classical predictions.

Until steps 1–4 exist, `nexus` stays a stub and no code path contacts Quantinuum.
