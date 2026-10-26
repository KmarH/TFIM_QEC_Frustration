# RESUME.md — live state of the current pass (untracked; rewrite, don't append)

**Purpose.** Any session (after a usage reset, a crash, or on another machine) reads this file
first and continues without re-deriving context. Keep it short and current: update it whenever a
stage changes state, before ending a turn.

## *** AUTONOMOUS PASS 2026-10-24 - THE LEAD HAS RULED AND IS AWAY. READ THIS FIRST. ***

**Plan (approved):** `C:\Users\kevin\.claude\plans\velvety-percolating-perlis.md`. Work it stage by
stage; record each stage's state HERE before ending a turn. This session owns the loop.

**Rulings (2026-10-24, the lead, in session):**
- **Card 1 -> full 4 modes x 2 references** common-estimand table; a winner only beyond the combined
  error bar (DECIDED-8).
- **Card 2 -> lambda amplifies EVERY 2-qubit gate** (simulator, Stim table and pytket circuit all
  agree; insertion after CX). The article must explain every departure from the literature, with
  an appendix table of all of them (DECIDED-9).
- **Estimator steps 1-4** (no-estimate reporting, trajectory-level resampling, a pre-declared ESS
  floor for all cells, budget solved against acceptance decay) (DECIDED-10). **No cherry-picking:**
  every rule is fixed in config + frozen tests BEFORE any re-score or re-run, identical for all cells.
- **F13** (both N = 20 cells at half budget, unrecorded) - recorded in review/18; fix = provenance +
  budget guard + pre-declared re-runs.
- **Git:** commit AND push to `resultados-espera` as often as needed, NEVER `main`, until revoked.
  **The article (`docs/article_q3/`) is never committed or pushed** (`.git/info/exclude`).
- Still: no hardware, no Nexus HQC, frozen tests + verified cores untouched.

**Stage status:** (update as you go)
| stage | state |
|---|---|
| 0 record F13 + OVM suite + commit 1 | DONE: commit `0888caf`; OVM suite on it 706 passed / 23 skipped / 6 xfailed / 0 failed (58 min). **PUSH BLOCKED** by the auto-mode permission classifier ("Out-of-Place Publication") despite the lead's in-session permission - NOT worked around; commits stay local until the lead adds an allow rule for `git push origin resultados-espera` |
| 1 lit-sweep + derivation | DONE: research/08 (S1-S18), research/derivations/02 (revised after review A) |
| 2 frozen tests | DONE: test_q3_rescore (R7 amended after review A1), test_q3_shards, test_lambda_scope, test_q3_rerun_budget; review regressions test_q3_rescore_review, test_h2_q3_encoded_lambda |
| 3 implementation | DONE (uncommitted): q3_rescore (msd verdict, cond ESS, min_batches), q3_shards, q3_queue, check_q3_replay, run_q3_sweep (provenance/guard/shards/sections 4-6), noisy_q3 ESS accumulators, lambda scope everywhere incl. encoded H2 circuits; config DECIDED-9/10; DECISIONS 8-10 |
| 4 blind review + gate + commit | DONE: review A minor, review B minor, all findings fixed with tests (52 passed + 6 expected xfails locally); commit `bd7d20d` (local only, push blocked); its OVM suite gate runs FIRST in ~/TFIM-q3run/runs/q3_sweep/queue/suite.log, then the OVM workers start |
| 5 launch re-run program | LAUNCHED 2026-10-24 ~17:05 at `bd7d20d`, clean clones: local `C:/Work/~/TFIM-q3run` (2 workers, pids 19520 / 35684, Start-Process detached), OLP `~/TFIM-q3run` (2 workers, `~/TFIM-verify/.venv/bin/python`), OVM `~/TFIM-q3run` (2 workers after the suite). Jobs: local 18 / ovm 25 / olp 44 (scratchpad jobs/*.txt). Est. ~30 h per host [inferred]. STATUS: `bash <scratchpad>/q3_status.sh [--pull]` (its 'workers' count includes the ssh probe itself: subtract 1). Relaunch a dead host: re-run scratchpad/deploy_remote.sh (keeps finished runs) or the local Start-Process loop. WHEN LANDED: --pull; `scripts/check_q3_replay.py --adopt`; `run_q3_sweep.py --merge-shards N:h:lam` x4; `--merge`; `gen_q3_doc_tables.py`; plots; `gen_q3_article_tables.py --out docs/article_q3/tables`; recompile article on OVM; OVM suite; commit |
| 5a progress 18:05 | 5 of 7 N = 12 replays landed (OLP 4, local 1) and REPRODUCE the stored cells to rtol 1e-10; ADOPTED (originals in runs/q3_sweep/superseded/2026-10-24/); replays ran 10-20x faster than the 10-23 originals (559-1207 s), so the ~30 h estimate is likely pessimistic [inferred]. data/q3_sweep.txt + docs/q3_scaling.md 4.0 regenerated (uncommitted). 0 shards landed yet; OVM still on its suite gate. |
| 5b progress 19:06 | N = 12 TIER COMPLETE: all 7 replays reproduce (rtol 1e-10) and are adopted, every N = 12 cell now has jackknife errors. OVM gate on commit `bd7d20d`: 752 passed / 23 skipped / 6 xfailed / 0 failed; OVM workers started after it. Shards landed: 2/80 (OLP, N = 18). |
| 5c progress 20:13 | all 6 workers healthy [measured]: OLP (18,0.1,3) shards 5,100-5,400 s each; OVM (20,0.5,3) shards >1.8 h each, running; local (20,0.3,1) shards ~3 h CPU each so far (model 5.4 h). Shards landed 2/80. LOCAL IS THE BOTTLENECK (17 x ~5.4 h on 2 workers; RAM 1.8 GB free, each 24-qubit shard ~0.92 GB, so no 3rd worker). REBALANCE when OVM or OLP drains: remove unstarted (20,0.3,1) shards from the local jobs.txt FIRST, then append them to the idle host's jobs.txt and start a worker there (claims are per host, so never list a job on two hosts). |
| 5d progress 21:13 | 4/80 shards landed, all (18,0.1,3) from OLP; all workers healthy (OVM shards at 2.8 h, CPU = wall). OBSERVATION, no action (rules fixed): those 4 shards hold 1 surviving trajectory of 84 at the window end vs ~4 expected from Stim (P(<=1 | Poisson 4.1) ~ 0.09); the cell's verdict waits for all 20 shards as pre-declared. |
| 5e progress 22:13 | 7/80 shards (OLP 6 x (18,0.1,3); OVM 1 x (20,0.5,3) = 12,600 s [measured]). Local (20,0.3,1) shards at ~5 CPU-h, running. ETA [inferred]: OLP drains ~Mon 02:00, OVM ~Mon 15:00, local ~Mon 20:00 -> rebalance local's unstarted shards to OLP when it drains, target ~Mon midday. Also committed b6a0957: resumable checkpointed Nexus runs (src/h2_resume.py, scripts/h2_run_resumable.py, 18 tests) at the lead's request. |
| 5f progress 10-25 00:13 | 10/80 shards. Local (20,0.3,1) shards at 7.0 CPU-h each, NOT yet done (model 5.4 h): the laptop is slower than modelled (memory pressure, ~2 GB free [inferred]); the local queue may take ~3+ days alone -> move its unstarted shards to the first host that drains. |
| 5g progress 10-25 01:13 | 12/80 shards. Local (20,0.3,1) shards at 8 CPU-h: scaling the measured OVM (20,0.5,3) shard (12,600 s) by workload gives ~8.5 h [derived] - the old 5.4 h model was optimistic. Remaining ~310 core-h on 6 workers -> ETA ~Tue 27 Oct early morning if balanced [inferred]. WORK-STEALING ready: when OVM or OLP drains, start ONE extra worker there on scratchpad/jobs/steal_local_rev.txt (local's unstarted (20,0.3,1) shards, reversed: s16..s2), e.g. scp it to ~/TFIM-q3run/runs/q3_sweep/queue/steal.txt and nohup setsid <python> -I scripts/q3_queue.py --worker --jobs-file runs/q3_sweep/queue/steal.txt. q3_status.sh --pull mirrors finished shards into the local clone, so the local queue skips stolen ones (same seed -> identical shard; worst case duplicate work, never wrong data). |
| 5h speed-up 10-25 01:28 | at the lead's request: LOCAL now 4 workers (added pids 26344, 13764; laptop Ryzen 9 270, 8C/16T, RAM was the limit), OLP +1 work-stealing worker on runs/q3_sweep/queue/steal.txt (local's (20,0.3,1) s16..s2 reversed; took s16 first). OVM unchanged (2 cores saturated). |
| 5i 10-25 01:34 | lead closed Steam -> LOCAL 5th worker (pid 19180, took (20,0.3,1) s4). Local: 5 workers on s0..s4 (+s16 on OLP). OVM confirmed saturated by the lead (2 Neoverse-N1 cores at ~98%); do NOT suggest resizing it. Watch laptop free RAM: keep >= ~1.5 GB; if it drops below, stop adding (never kill a running shard without need). |
| 5j HQC optimisation check 10-25 ~02:00 | at the lead's question [measured, offline, 500 shots]: TKET level 2 vs the deliberate level 0 (D-NS6) - Q3-bare 5669.6->5502.4 (-2.9%), Q3-ladder 4093.2->4013.0 (-2.0%), Q3-bare-3x6 1453.2->1413.6 (-2.7%), Q3-iceberg 0% usable (level 2 REMOVED 2q gates on all 4, which changes the experiment). 2q gates are 78-92% of every bill. Recommendation: keep level 0 (~2% total not worth a second compile path). Real HQC levers change the experiment (syndrome-round cadence, insertion instances, time points) = lead's decisions. |
| 5k progress 10-25 03:13 | 18/80 shards ((18,0.1,3) 13, (20,0.5,3) 4, (20,0.3,1) 1). First local (20,0.3,1) shard: 39,636 s = 11.0 h with 5 local workers sharing memory bandwidth [measured]. Projected bottleneck is now the OVM (~Mon evening) [inferred]. TWO-WAY STEALING: q3_status.sh --pull now mirrors finished shards to ALL hosts' shards dirs; scratchpad/jobs/steal_ovm_rev.txt = OVM's list reversed ((20,0.5,3) s19..s0, (20,0.3,1) s19,s18,s17). When the laptop or OLP drains its list, start a worker there on steal_ovm_rev.txt (laptop: also the remaining steal_local_rev on OLP). |
| 5l AUTOPILOT 10-25 08:50 | C:/Work/~/TFIM-q3run-ops/autopilot.sh (outside the repo: holds host addresses) does every mechanical step unattended: collect+mirror (q3_status.sh --pull), keep each host at capacity with steal workers (OVM 2, OLP 3, laptop 5 if >= 2.4 GB free), --merge-shards a cell once its 20 shards are in, --merge, gen_q3_doc_tables(+--check), check_42, plots, article tables, then commit+push to resultados-espera only if all checks pass; DONE marker when all four cells are pooled; log autopilot.log; lock dir prevents overlap. Dry-run tested 08:48 (no-op as expected). Registering it as a Windows Scheduled Task was REFUSED by the permission classifier ('Unauthorized Persistence') - not worked around; the lead can register it (command in the lead summary). SESSION TICKS SHOULD NOW JUST RUN `bash C:/Work/~/TFIM-q3run-ops/autopilot.sh` and then do the judgment work (prose, article, RESUME). |
| 5m 10-25 08:53 | The LEAD registered the Windows Scheduled Task `q3-sweep-autopilot` himself (ops/register_task.ps1): hourly from 08:58:24 for 7 days, runs ops/autopilot.sh. Remove with `Unregister-ScheduledTask -TaskName q3-sweep-autopilot -Confirm:$false` once ops/DONE exists. |
| 5n 10-25 11:10 | FIRST SIZE CELL LANDED: the autopilot pooled (18,0.1,3) at 10:59 (20 shards, 420/200 traj, end Kish ESS 16.0 / cond 11.3) and committed+pushed 617e2ba unattended. Result [measured, jackknife]: Ice+G beats bare+G on both refs (-3.0 / -3.2 sigma), bare+G beats Ice alone (+1.4 sigma), cost 15.9 vs 1.44, survival 0.038 vs Stim 0.048. docs 4.0 prose updated by hand. Remaining: (18,0.3,1), (20,0.3,1), (20,0.5,3). |
| 5o 10-25 11:40 | (20,0.3,1) is the long pole: 2/20 shards; with 5 laptop workers a shard takes ~15 h wall (s1: 57,151 s) [measured]. Program ETA ~Tue 27 Oct morning-midday [inferred]. Autopilot healthy (hourly, exit 0). |
| 5p 10-26 08:40 | (20,0.5,3) 20/20 pooled by the autopilot (82ddb49). v2 [measured]: Iceberg+Gauss vs bare+Gauss UNRESOLVED (-0.7s raw, -0.6s cond); bare+Gauss beats Iceberg alone +5.7s cond; cost 16.2 vs 1.94; survival 0.046 vs Stim 0.045 (+0.1s); ESS 21.0/16.7. docs §4.0 prose + article results updated, article recompiled. Remaining: (18,0.3,1) 14/20, (20,0.3,1) 8/20. |
| 5q 10-26 16:08 | (18,0.3,1) 20/20 pooled by the autopilot (c67b0d1; the Claude-side wrapper of that tick was reaped for low laptop RAM, the autopilot process itself finished normally). v2 [measured]: cond Ice+G beats bare+G -3.1s (rms 0.0022 vs 0.0048); raw reverses, bare+G beats Ice+G +1.6s (0.0052 vs 0.0062); bare+G beats Ice alone +1.0s raw / +1.4s cond; cost 11.8 vs 1.42; survival 0.0315 vs Stim 0.0534 (-1.9s, largest so far); ESS 12.0/11.0. docs 4.0 prose + article results updated, article recompiled. Remaining: (20,0.3,1) 12/20. |
| 5r 10-26 16:50 | Lead asked to push idle remote capacity at the last cell. Found: OVM 1/2 and OLP 1/4 cores busy; shard 20:0.3:1/s13 unclaimed anywhere. Cause: autopilot's scp of steal_all.txt passed the host as a source file, so every remote steal worker died (FileNotFoundError) [measured]. Fixed in ops/autopilot.sh (backup .bak-20261026; per-host lists jobs/steal_OVM.txt = s13,s12, steal_OLP.txt = s12). Started s13 on OVM, a duplicate of the laptop's s12 on OLP (deterministic seeds, so the first copy to finish wins and no data can differ). Per-shard wall for this cell [measured]: OVM ~24k s, OLP 58-65k s (3 concurrent), laptop ~57k s (5 concurrent). Remaining: s8-s12 laptop, s13+s19 OVM, s14 OLP (12/20 done). Cell ETA ~Tue 27 Oct early morning [inferred]. |
| 6 interim rescore, figures, article | DONE (preliminary): docs/article_q3/main.pdf, 37 pp, compiled on OVM with tectonic, 0 undefined refs; LE check of encoded lambda=3 circuits: acceptance 0.700 +- 0.073 vs Stim 0.742 (-0.6 sigma), lambda=1 = 1.000 |
| 6b emulator-readiness | DONE as far as free tiers allow: encoded lambda circuits buildable (196 2q locations in the one-step program = sim = Stim; the 72 rot-cx are the PREPARATION, once - review B), LE check passed; SC quotes need NEXUS_REFRESH_TOKEN (absent) |
| 7 handoff + loop | loop armed; plan.md section 32 + RESUME rewrite pending |

**Frozen spec hashes (sha256, first 16):** test_q3_shards b957326255d258f6, test_lambda_scope (re-hash after L3 attribute fix), test_q3_rerun_budget (re-hash after margin revision), test_q3_rescore (re-hash after R7 amendment). Final hashes are recorded at the commit that freezes them.

**Hosts:** OVM python `~/KiroTest-project/.venv/bin/python`, clone `~/TFIM-q3rerun`; OLP python `~/TFIM-verify/.venv/bin/python` (pins match); local `.venv`.

Everything below this block is the 2026-10-23 history; its "never commit" lines are SUPERSEDED by
the git permission above.

**COMMITTED 2026-10-23 ~19:30, branch `resultados-espera` (project lead asked; nothing pushed):**
- `99d6103` QI-16 (Selene hangs on Windows) + `docs/project_gap_analysis.md`
- `b022a17` Q3 generalization machinery — `config.py` `Q3ScalingConfig`, `src/q3_scaling.py`,
  `src/noise_scaling.run_iceberg_scaled`, `src/noisy_q3.py` `apply_u` hook, `src/noisy_q3_sweep.py`,
  the four runner scripts, all five test files, `data/q3_scaling.txt`, `data/q3_hqc.txt`.
  **The four frozen test hashes were re-verified against this file and match exactly**, so the
  freeze is now tamper-evident in git rather than resting on an untracked note.
**Deliberately NOT committed** (still in flight): `data/q3_sweep.txt` (8 of 11 cells),
`docs/q3_scaling.md` (§4.4 PENDING), `DECISIONS.md` and `handoff/plan.md` (§30 IN PROGRESS), and
this file (untracked by design). Stage 6 peer review has not run, so the committed code is
OVM-gated (705 passed / 23 skipped on this tree) but not yet reviewer-gated.

**Pass:** Q3 generalization study — generalizing the single-cell Iceberg-vs-Gauss result of
`docs/q3_thermalization.md` §9.2 over size (D1), field (D2) and noise scale (D3).
**Plan:** `C:\Users\kevin\.claude\plans\eager-yawning-spindle.md` (approved 2026-10-22).
**Branch:** main, nothing committed, nothing pushed. Classical only; no hardware, no HQC.

## CURRENT STATE - 2026-10-23 20:40. READ THIS BLOCK, THEN "Next action". Everything below it is detail.

**Where the pass is.** Stages 0, 1, 2 and 5 (offline HQC) DONE; stage 4 at **10 of 11 cells**;
stage 7 mostly written. Outstanding: **one cell**, then publish, suite, peer review, handoff.

**The one running job.** Local cell **(20, 0.5, 3)**, python **pid 3932**, started 17:31, reduced
counts (60 bare / 24 Iceberg, 6 batches, `record_every` 6), encoded window 12 steps. It is a
**detached OS process: it survives every session being closed**, and it writes
`runs/q3_sweep/cell_N20_h0.5_lam3.json` on its own. It prints nothing until it exits.
**Its ETA IS DISPUTED and neither number should be acted on:** 23:25 tonight (the measured
amplitude-touch model below, whose 24-physical-qubit constant was fitted on the same host and the
same counts) against ~07:30 tomorrow (session 74acfd92). **Check for the JSON; do not infer from a
clock.** If it is absent and pid 3932 is gone, the cell DIED - say so and do not fabricate a row.

**Artifacts are now IN THE REPO, not in a session temp directory** (they were moved 2026-10-23
20:35 so a temp cleanup cannot eat them; all three are untracked):
- `handoff/q3_scaling_4_4_draft.md` - the ready-to-paste 4.3 rows and 4.4 text for the THREE landed
  size-axis cells, every number already verified against `data/q3_sweep.txt`.
- `scripts/check_q3_doc_table_42.py` - re-derives 4.2's 21 number triples from the data file.
- `scripts/check_q3_doc_table_44.py` - the same for 4.4; **exits 2 with a loud message if 4.4 has
  no rows**, so it cannot pass vacuously while 4.4 is still PENDING.

**Three hard gates, in order of how easy they are to trip.**
1. **The project lead decided at 17:40: 4.4 is DRAFTED now and PUBLISHED only when ALL FOUR
   size-axis cells are in.** This session breached it at 20:01 and reverted it at 20:10.
   `docs/q3_scaling.md` 4.3/4.4 are currently in their correct, pre-publication state.
2. **The local suite needs three deselects or it hangs** (QI-16, Selene on Windows) - see the
   LOCAL SUITE section below for the exact command.
3. **Never commit, never push, no hardware, no Nexus, no HQC.** Nothing has been submitted; 0 HQC.

**Superseded sections below - do not act on their numbers.** The derived 2^(physical) per-trajectory
anchor and the "x2.7 calibration" are superseded by MEASURED RUNTIME MODEL (19:55); both STUCK-CHECK
sections are resolved (the cells they were watching have landed); "Superseded guesses" is kept only
for the reasoning trail.

**Session hygiene.** Three sessions were live on 2026-10-23 and that cost a real error (gate 1
above). Run **one** session against this file.

## *** 11th CELL LANDED 23:09:54 exit 0 - AND IT IS NOT A MEASUREMENT (23:30) ***
`runs/q3_sweep/cell_N20_h0.5_lam3.json`, 20,302 s. **Merged: `data/q3_sweep.txt` now has 11 cells**
(`--merge` exit 0). **All four frozen test hashes re-verified and unchanged.** `check_q3_doc_table_42.py`
passes on the re-merged file: **21 triples, 0 mismatches**. Full local suite launched 23:28, **KILLED BY THE
LOW-MEMORY REAPER at ~68 %** - do NOT restart it unasked. **Clean where it got to: 492 passed,
23 skipped, 0 failed, 0 errors** (log `.../a23b8f13-.../scratchpad/suite_full.log`, 522 lines). It
died inside `tests/test_noisy_q3_sweep.py::test_sweep_reproduces_q3_noisy_3x4_flippable_within_two_sigma`,
a SLOW 16-physical-qubit trajectory test, with free RAM at 2.36 GB and nothing of ours running.
**The pass criterion is now independently confirmed by pytest's own collection line:
`collected 728 items / 3 deselected / 725 selected`, and 725 - 23 skipped = exactly 702.**
**THE LOCAL FULL-SUITE GATE IS STILL OWED, and this box may not be able to deliver it:** the reaper
has now killed the suite twice today plus two cell watchers. Options for the project lead - (a) run
it on the idle OVM over ssh for the authoritative 705/23 with Selene coverage; (b) relaunch locally
with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1` in Claude Code's environment (it cannot be set
from a shell command); (c) local non-slow subset only, ~45 min, leaving the slow trajectory tests
ungated locally.

**The cell's encoded arm rests on ONE surviving trajectory of 24** [measured, from the JSON]:
survival 0.0416 at the 12-step window, **3 time points** in the early window (t = 0, 1.5, 3.0)
against 25 at N = 12, `Iceberg` residual **1.01e-07 +- 3.28e-17**, `Iceberg + Gauss`
**5.78e-09 +- 1.13e-17**, and the encoded curve reproduces the **IDEAL** curve to 7-8 digits. At 4 %
survival the accepted ensemble is essentially the **fault-free trajectory**, and since the simulator
computes the readout distribution exactly (**F5**), a fault-free trajectory IS the ideal curve. The
last point's batch SE is `None`/NaN and the runner logged `Degrees of freedom <= 0` - **F9 realised
for the first time** (it was latent with 0 occurrences in the first 10 cells).
**The merge therefore prints `Iceberg better by 0.0008`, which would be the study's first
"Iceberg wins" row and is an artifact.** Rows + full diagnosis appended to
`handoff/q3_scaling_4_4_draft.md`, marked DO NOT PUBLISH. Nothing written to `docs/q3_scaling.md`.
**This cell is a measured demonstration of F1/F5/F9, and it strengthens the hold rather than
lifting it.** A real number at that corner needs far more trajectories or a shot-noise-aware
metric: a re-cut, not a re-run - the project lead's call.
**REGRESSION TESTS WRITTEN 2026-10-24 00:10 - `tests/test_q3_review18_findings.py`, 7 tests, all
behaving as designed: 1 passed, 6 xfailed (strict), 0 failed, 2.9 s.** Written AFTER the code, as a
review artifact, and labelled as such in its docstring - NOT a frozen spec. Each review/18 defect
gets a test stating the CORRECT behaviour under `xfail(strict=True)`, so the suite stays green while
the rulings are pending AND a silent fix becomes impossible: the moment a defect is fixed the test
XPASSes, strict xfail turns that into a FAILURE, and whoever fixed it must come here and drop the
marker. Covered: **F1** (only 6 of 4 modes x 2 references are computed), **F2** (an explicit
`early_t` bounds only the bare arm), **F4** (cost 1/mean(acc) = 1.98 against mean(1/acc) = 50.5 on
acceptance [1.0, 0.01]), **F5** (an epsilon SE passes the `se > 0` guard - written with the 11th
cell's REAL numbers, residual 1.0140736e-07 vs se 3.2823027e-17), **F8** (`n_ice <= n_bare`
unenforced), **F9** (a point whose acceptance is 0 exactly where the arm is wrong is dropped, so the
residual flatters it). One test PASSES and is kept deliberately: `se == 0` exactly DOES report not
resolved, which shows F5 is a gap in an existing guard rather than a missing guard.
All inputs are synthetic and tiny - no lattice, no state vector, no trajectories, nothing written to
`data/` or `runs/`. No frozen spec file and no verified core was touched.

**SUITE COUNT UPDATED [measured, `--collect-only`]: 735 collected** (728 + 7). So the local Windows
gate becomes **703 passed / 23 skipped / 6 xfailed / 0 failed** (735 - 3 QI-16 deselects = 732
selected; 732 - 23 skipped - 6 xfailed = 703), and the Linux/OVM gate becomes **706 passed /
23 skipped / 6 xfailed**. The old 702/705 figures predate this file.

**F6 APPLIED 23:55 (needed no ruling):** `src/noise_scaling.py`'s module docstring now records that
the KB supports insertion only before the 2q ROTATIONS and only with random Pauli twirls; that
`run_iceberg_scaled`'s extension to syndrome CX and rotation-gadget CX in an untwirled trajectory
sim is **[inferred], not [derived]**; the ZZPhase-exact / CX-inexact ordering caveat (F7); and the
three coexisting lambda scopes with the warning not to send a lambda point to the emulator before
the scope is settled. Module imports fine, no line over the file's existing 100-char width. (`ruff`
is not installed in this `.venv`, so the hook's check could not be run locally - docstring-only
change.)

**`gen_rows.py` was extended** to emit an "Iceberg better by" verdict instead of crashing on it
(it raised `IndexError` first, i.e. it refused to mangle the row - the safe failure).

## *** PUBLICATION HOLD, 2026-10-23 22:45 - DO NOT PUBLISH 4.4 WHEN THE CELL LANDS ***
Stage 6's code-half blind review returned **major**, and this session VERIFIED both findings
independently. The 4 verdict column is in question, so the 17:40 "publish when all four cells are
in" condition is necessary but **no longer sufficient**. Merge the cell, generate its rows, write
them to the DRAFT - but 4.3/4.4 stay unpublished until the project lead rules on the two cards
below. Publishing a "better by" column that a verified review calls not like-for-like would be a
worse breach than the 20:01 one.

**V1 [measured by this session, from data/q3_sweep.txt 2 alone - no simulation]. The head-to-head
gap subtracts residuals measured against DIFFERENT reference curves.** 3's
`gap = Iceberg.residual - (bare+Gauss).residual` takes Iceberg's residual against the ideal RAW
curve and bare+Gauss's against the ideal SECTOR-CONDITIONED curve. Each mode is scored against
what it estimates (defensible, and it is the 9.2 metric), but their DIFFERENCE is not an
accuracy comparison. Recomputed over the 10 landed cells
(`.../a23b8f13-.../scratchpad/verify_f1.py`):
- on a common RAW target (bare+Gauss `[vs raw]` vs Iceberg), **1 of 10 verdicts flips**:
  (12, 0.5, 1) goes from "bare+Gauss better by 0.0126" to **"Iceberg better by 0.0070"**;
  (18, 0.1, 3) goes from unresolved to Iceberg by 0.0019; (20, 0.3, 1)'s margin collapses
  0.0060 -> 0.0005 and (12, 0.5, 3)'s 0.0206 -> 0.0009.
- on a common CONDITIONED target (bare+Gauss vs Iceberg+Gauss, the genuinely like-for-like pair):
  **8 of 10 cells are UNRESOLVED**, and Iceberg+Gauss is nominally ahead beyond the combined SE at
  (12, 0.5, 1) by 0.0017, (18, 0.3, 1) by 0.0020 and (18, 0.1, 3) by 0.0161.
- caveat on V1's own arithmetic: `data/q3_sweep.txt` does **not** carry an SE for the `[vs raw]`
  residual, so the common-RAW column's resolution cannot be tested from the data file; the flips
  above are central values. Getting those SEs means re-scoring from the cell JSONs.

**V2 [verified by this session, code read: src/noise_scaling.py:315-324].** `apply_u` inserts a
Pauli before **every** command with `len(qs) == 2`. It does not filter by gate class, so on the
ENCODED arm it also amplifies the CX gates inside the arbitrary-angle rotation gadgets
(`rot-cx`), which the documented scope excludes: the docstring at :287, `src/q3_scaling.py:58`
(`"2q": ("rot-zz","syn-cx")`) and `data/q3_scaling.txt:12` all name the narrower set. Reviewer's
location count [measured, N = 12 Stim image, 1 step]: `syn-cx` 64 + `rot-cx` 72 + `rot-zz` 60 =
196 amplified against the 124 the scope names, **x1.58**. The BARE arm has only `rot-zz` 2q gates,
so it matches its scope exactly - the mismatch is encoded-arm-only.
**Which side is wrong is a PHYSICS call, not a bug fix:** if a `rot-cx` gate carries 2q noise then
amplifying it is right and the Stim table + windows are the optimistic ones; if the intended knob
was the narrower channel then the encoded arm has been over-amplified. Either way the trajectory
runner and the Stim accounting used DIFFERENT lambda scopes, which touches **5 of 11 cells**
(every lambda > 1 cell: 12:0.3:2, 12:0.3:3, 12:0.5:3, 18:0.1:3 and the running 20:0.5:3) and
weakens 4.3's "agrees with Stim within 1.4 sigma" at lambda > 1. **Not re-measured:** no Stim rate
was recomputed for `rot-cx` alone, by the reviewer or by this session.

**Also open:** reviewer's minors - the bare early window is bounded by `t_bare <= t_ice[-1]` while
the Iceberg mask has no window term, so the two arms average over different grids (N = 12 h0.3
lam3: bare 10 points to t = 4.50, Iceberg 11 to t = 4.75); NaN-SE and zero-acceptance points are
latent (0 occurrences in the 10 landed cells) but bias `resolved` toward True if they ever occur;
`data/q3_sweep.txt` 4's header promises a Stim comparison the merge never prints.
**Confirmed clean [measured by the reviewer, independent re-scoring]:** the merge path is verbatim
JSON, and its own arithmetic reproduced two cells' residuals/SEs/costs to 4 dp.

**ADJUDICATED 2026-10-23 23:10 - both reviewers in, full write-up `review/18-q3-scaling-code.md`.**
Theory reviewer returned **major** too (it was resumed after an API session limit and finished from
its own transcript; its derivation was written before it read the scoring code, as required).

- **V1 STANDS, raised independently by both** - F1 in review/18. The theory reviewer sharpened it:
  the symmetric object is 4 modes x 2 references = 8 cells, and `residual` + `residual_vs_raw` fill
  only 6, so **bare-raw-vs-cond and Iceberg-raw-vs-cond are never computed** and the question
  "is Iceberg more accurate than bare+Gauss" has no common-estimand answer at all. The 4 verdict
  column's "better by" phrasing is unsupported as written. **Lead's call (card 1).**
- **V2 DIRECTION REVERSED - the code is RIGHT, this session verified it** (`src/noisy_q3.py:103-107`:
  `_fault_2q` is charged at EVERY 2q command, no class filter), so amplifying every 2q gate is the
  correct reading of "2q error x lambda" and `run_iceberg_scaled` matches its own noise model. The
  code reviewer's 196-vs-124 count was right but it blamed the wrong side. **The actual defect is
  three coexisting lambda scopes**: simulator = every 2q gate; Stim table (`_NAMED_SCOPES["2q"]`,
  hence the survival-matched WINDOWS) = rot-zz + syn-cx; **pytket circuit** (`insert_paulis`,
  `config.py:449 fold_scope`) = **rot-zz only**. The third is the dangerous one: **the circuit we
  would actually submit to H2 is amplified on a NARROWER scope than the simulation predicting it**,
  so a lambda-ladder emulator-vs-prediction comparison would not compare the same ladder. Must be
  fixed before any lambda point goes to the emulator. **Lead's call (card 2).** Nothing submitted,
  0 HQC.
- **NEW major, structural (theory reviewer, F5):** `se` is the batch spread over Pauli TRAJECTORIES
  with the readout distribution computed exactly, so it carries **no shot noise and no
  1/sqrt(acceptance) inflation**. `resolved` therefore tests against a SIMULATION-EFFORT floor while
  `cost` is in HARDWARE SHOTS - the two cannot be combined into "resolved at this shot cost", and no
  field carries the per-accepted-shot variance the cost comparison needs. **Every `resolved` flag in
  4 means less than it looks like.**
- **NEW major, citation (F6):** the KB supports Pauli insertion only before the 2q ROTATIONS, and
  only combined with random Pauli twirls; the encoded runner extends it to syndrome CX with the
  rotation-learned channel in an UNTWIRLED trajectory sim, so `src/noise_scaling.py:11`'s
  `[derived; the 2503.20870 method]` over-claims. Doc correction owed regardless of the cards.
- **Fixable without a ruling:** F2 (window asymmetry - both reviewers), F4 (cost Jensen - both),
  F12 (4's header promises a Stim comparison the merge never prints). Regression tests go in a NEW
  file via `test-first` part A; the four frozen files stay untouched.
- **Latent, not triggered by any landed cell:** F8 (`n_ice <= n_bare` unenforced, bites at h > ~1),
  F9 (zero-acceptance / NaN-SE points dropped), F11 (`prefilter_grid` scope `"all"`).
- **Confirmed clean:** the code reviewer's independent stdlib re-scoring reproduced two cells to
  4 dp; `surv * p_in` is the correct joint acceptance; lambda = 1 is bitwise identical on both arms.


## SESSION HANDOVER, 2026-10-23 21:05 - this session (a23b8f13) is the SINGLE loop owner
**Project lead's decision, 21:05:** this session takes over as the only `/loop` against this file;
the lead closes the others (74acfd92, plus the long-lived 05:16 / 17:24 claude processes). **Any
other session that wakes on this file should STOP and write nothing.**
Plan for the remainder of the pass: `C:\Users\kevin\.claude\plans\velvety-percolating-perlis.md`
(approved 21:05) - it carries the full post-landing sequence (merge, publish 4.3/4.4, both
checkers, suite, peer review, handoff).

**Live probe [measured 21:05; probed directly, NOT inferred from elapsed time]:**
`runs/q3_sweep/cell_N20_h0.5_lam3.json` **ABSENT**; python pid **3932 ALIVE**, **12,594 s CPU**
against ~3 h 34 m wall since the 17:31:31 noisy-arm marker = **98 % of one core**, RSS 0.70 GB,
single-threaded; `serial.log` still ends at that marker (no finer progress signal exists by
construction); free local RAM **1.76 GB** of 15.26. **Slow, not stuck, not dead.** The owed local
suite stays deferred. Both ETAs (23:25 tonight / ~07:30 tomorrow) remain disputed; neither is acted
on.

**SUITE CEILING CORRECTED [established]:** the local Windows full-suite gate is **702 passed /
23 skipped**, NOT 705 - the three QI-16 Selene deselects remove three tests (LOCAL SUITE section
below says so). The project lead approved **702/23 as the local pass criterion** at 21:05. The
authoritative 705/23 remains the OVM Linux run, already discharged on this exact tree.

**STALE LINE, annotated not rewritten:** the resume protocol's "No automated loop is set up: the
project lead declined that" (2026-10-22) is **superseded as of 2026-10-23** - the lead asked for
`/loop` twice that day (~20:15 for session 74acfd92, 21:00 for this one).

## Resume protocol (project lead, 2026-10-22)
- A new session may be started once the chat approaches ~500k tokens, but **only after the current
  task finishes**: never cancel work in flight to start one. If the cap arrives mid-task, let the
  task complete first.
- A session that resumes (after a usage reset, a new session, or another machine) reads **this
  file** first, then the plan, then continues at "Next action". No automated loop is set up: the
  project lead declined that.
- Before ending any turn: update the stage table, "Next action" and "Running jobs" here.

## Decisions already taken (do not relitigate)
- D1 sizes N = 12 (3x4 flippable), 18 (3x6 3-sublattice), 20 (4x5 flippable); Stim-only 36, 54.
- D2 h in {0.1, 0.2, 0.3, 0.5}. D3 lam in {1, 2, 3} on BOTH arms. D4 prefilter first. D5 timing probe.
- **D6 = build `run_iceberg_scaled`** (project lead, 2026-10-22).
- Encoded window = **survival-matched per size** (largest window with predicted survival >= 5 %).
- HQC = offline `hqc_estimate` **plus** free H2-1SC quotes (needs `NEXUS_REFRESH_TOKEN`, NOT set
  on this machine — ask the project lead when Stage 5 is reached). Nothing is ever submitted to a
  paid tier.
- Budget: overnight-scale, work distributed over three machines.

## Frozen tests (NEVER edit; verify hashes before touching anything)
| file | SHA-256 |
|---|---|
| `tests/test_q3_scaling.py` | `2ade0fc46d731edfa5988d9e442e59d6104a563d1050af4266cd8fde110d667f` |
| `tests/test_noisy_q3_sweep.py` | `31866c3c65753f3932b323b516eb7d6340b79a095ee027f3c09e6f5c45341f1b` |
| `tests/test_probe_q3_scaling_timing.py` | `f2a5de13717de7c13a13605dea0702c2b21c8a86608af56dc6ccc08089b6d961` |
| `tests/test_iceberg_scaled.py` (D6 spec) | `30837339279f18a132dcf0493510913aadf832fe9d8cbda75c5ed2035c8d8f99` |

**Not frozen, written after the code (labelled as such in its docstring):**
`tests/test_q3_score_cell.py`, **5 tests, all passing** — regression cover for
`src/noisy_q3_sweep.score_cell`, which carries the §9.2 metric for every number in
`docs/q3_scaling.md` §4 and which the frozen specs predate (they pin the raw curves the sweep
returns, not how those curves are scored). It pins the residual definitions, the Gauss-vs-raw
reference choice, interpolation onto the encoded grid, both shot-cost factors, the SE > 0
`resolved` rule and NaN handling. **Suite count is therefore 705 locally (700 + 5); the 700 figure
quoted from the OVM run predates this file.**

## Machines (tfim-qec skill has the details)
- **local** Windows, 16 cores, 15 GB, `.venv\Scripts\python.exe` (3.12.15) — orchestration + the
  heavy 22/24-qubit encoded cells.
- **OVM** `ssh -i ~/.ssh/oci_vm_key opc@92.5.118.106`, 2 cores, 8 GB free,
  `~/KiroTest-project/.venv/bin/python` (3.12.14).
- **OLP** `ssh pululunga@100.111.130.126`, 4 cores, 8 GB free,
  `~/TFIM-fix/.venv/bin/python` (3.14.4).
- Remotes have the same pinned numerics (numpy 2.5.3, scipy 1.18.1, stim 1.16.0, pytket 2.18.4)
  but OLD checkouts, so a run there needs the current source shipped (tar of `git archive HEAD`
  plus the untracked new files). Run plain python over ssh — no `claude -p` agents, no token cost.

## Stage status
| stage | state | note |
|---|---|---|
| 0 hashes + frozen tests | **DONE** | 24 non-slow pass; 4 slow pass (48 min, exit 0), incl. the 2-sigma reproduction of `data/q3_noisy.txt` |
| 1 D6 `run_iceberg_scaled` | **DONE** | `src/noise_scaling.run_iceberg_scaled` (+ additive `apply_u` hook in `src/noisy_q3.py`; sweep wired; `_arm` keeps acceptance/p_in/cond; `score_cell` added). All 13 spec tests pass (10 non-slow 6 min, 3 slow 4.6 min), incl. the Stim-vs-trajectory cross-check at lam 2 and 3 |
| 2 Stim prefilter | **DONE** | `scripts/run_q3_scaling.py` -> `data/q3_scaling.txt` (6 sections, N = 12-54). Continuity: N = 12, lam = 1 survival 0.0692 at 48 steps = the 0.069 of `data/q3_noisy.txt` |
| 3 D5 timing probe | **KILLED (memory)** | the local probe was stopped by Claude Code's low-memory reaper on 2026-10-23, not by a failure of its own; **do not restart it unasked** (memory may still be short, and the 11 sweep cells are the priority for RAM). It had run ~1 h (output buffered, `probe_local.txt` in the scratchpad is empty); remote probes not run. Counts in `CONFIG.q3_scaling.per_size` were set from the 2^(N+4) scaling argument and must still be CHECKED against the probe, then recorded as D5 evidence in the doc. Everything is memory-bandwidth-bound, not core-bound: 11 concurrent cells contend badly, so do NOT add parallel load |
| 4 the sweep | **10 of 11 DONE** | merged into `data/q3_sweep.txt` (10 cells) and written up in `docs/q3_scaling.md` 4.1-4.2 (field + lam, N = 12) and **4.4 (size axis, NEW)**. Continuity: the h = 0.3, lam = 1 cell reproduces the published bare+Gauss 0.0017 +- 0.0004 at x1.43 to the printed digit on OLP's Python 3.14.4. **Only (20, 0.5, 3) is still running** (local, started 17:31). End-to-end path was validated with a smoke cell that was then deleted; two fixes came out of it (`ModeScore.resolved` requires SE > 0; the merge prints "-" not `nan`) |
| 5 HQC | **offline DONE** | `scripts/run_q3_hqc.py` -> `data/q3_hqc.txt`; write-up `docs/q3_scaling.md` §5. Headline: the study is **155,164 HQC = 3.1x the whole 50k allowance**, so it is classical by necessity; at matched window Iceberg costs **x2.94-3.06 the HQC** of the bare circuit before its x2.8-3.7 shot cost, i.e. ~6x the total resource of bare+Gauss for a worse residual. Only the free SC server quotes are still owed (need `NEXUS_REFRESH_TOKEN`). Nothing submitted, 0 HQC spent |
| 6 blind peer review | TODO | `peer-review` skill, 2 reviewers. **Deliberately not started until the 11th cell lands** — it would only add one row to 4.4, and reviewing a doc that is about to change costs two reviewer passes |
| 7 handoff | **mostly done** | `docs/q3_scaling.md` written through 4.4 (only the 11th cell's row and 5.5's owed SC quotes outstanding), `DECISIONS.md` **DECIDED-7**, `handoff/plan.md` **30** (IN PROGRESS). Left: the 11th cell's row, fold the size-axis finding into 30, final summary to the project lead |

## COST DIAGNOSIS — RESOLVED 2026-10-23 (measured; supersedes the two guesses below)

**Measured split** (`timing_split.py` in the session scratchpad; `run_iceberg` with `n_traj=0`
isolates setup, taken while four heavy cells were competing):

| | N = 12 (16 phys) | N = 18 (22 phys) |
|---|---|---|
| `make_iceberg` + `schedule` + `_boundaries` | 3.1 s | 0.4 s |
| Iceberg table setup (`n_traj=0`) | 0.21 s | 7.1 s |
| one 4-step trajectory | **4.33 s** | **282.5 s** |

**Conclusion: the cost is per-trajectory and scales as 2^(physical qubits), exactly.**
70.6 s/traj-step at N = 18 against 1.08 s at N = 12 is a factor **65 for 2^6 = 64** more
amplitudes. Fixed setup is NOT the problem (7 s), and neither is observable evaluation. Both
earlier hypotheses in this file were wrong and are deleted.

**What was actually wrong: self-inflicted memory-bandwidth contention.** The published baseline
implies 0.039 s/traj-step at N = 12 on a 2-core box; the local measurement under four concurrent
heavy cells was 1.08 s, about **28x worse**. Each cell also spawned BLAS threads (1.5-2.6 cores
each on work that is elementwise). Free RAM was 0.6 GB with the four running and **6 GB within
seconds of killing them**, which is also what had been triggering Claude Code's low-memory reaper
all night (it killed the D5 probe, a `du` scan, a suite launcher and the calibration).

**Function-level confirmation (cProfile, tiny N = 18 cell on OLP, 1290 s total):**

| hot spot | time | share |
|---|---|---|
| `numpy.tensordot`, 68,066 calls, reached from `backends_qc.apply1` (408 s cum) / `apply2` (476 s cum) | 859 s cum / 505 s own | **~68 %** |
| `ndarray.reshape`, **245,354 calls** | 344 s own | (the copies inside the above) |
| `src/trotter_threshold.py:65(obs)` — the observable evaluation, 986 calls at 0.31 s | 306 s | **~24 %** |
| `readout_flip` (21 s), `backends_qc.measure` (42 s) | 63 s | ~5 % |

So the cost is **gate-by-gate state-vector application**: each gate does `moveaxis` → `reshape` →
`tensordot` → reshape back, and because the moved array is not contiguous the reshapes **copy the
whole state** (~67 MB at 22 qubits) about three times per gate. A Trotter step has hundreds of
gates, so one step moves tens of GB. That is why the cells are memory-bandwidth-bound and why four
in parallel destroyed each other's throughput.

**Optimisation opportunity (NOT taken — the project lead's call, and a results run is in flight):**
an in-place / reshape-free gate application (einsum with preallocated output, or strided slice
arithmetic for the diagonal ZZ and single-qubit rotations) could plausibly cut the dominant 68 %
term by 2-3x. `src/backends_qc.py` is not on the verified-core list, but it is load-bearing for
the whole encoded pipeline, so any such change needs the transparency and Stim cross-checks re-run.
The secondary 24 % term scales as (1 + n_batches) x n_records, so coarsening `record_every` (now 6
on the N = 20 cells) already buys part of it.

**Rule for this project's trajectory cells: run them SERIALLY, one per host, with
`OMP_NUM_THREADS=1` (plus the OpenBLAS/MKL/numexpr equivalents). Parallel heavy cells on one host
lose more to bandwidth than they gain in concurrency.**

**Action taken 2026-10-23 07:00:** the four local cells were killed (~10 h of contended progress
discarded deliberately: at the contended rate they would have needed days) and replaced by a
**serial runner** (`serial_cells.cmd` in the scratchpad, launched detached, log
`runs/q3_sweep/logs/serial.log`): 20:0.3:1 then 20:0.5:3, single-threaded, at **reduced counts
(traj 60 bare / 24 Iceberg, 6 batches, `record_every` 6)** — the "reduced counts with honestly
reported error bars on the 24-qubit cells" that the approved budget option allows. **The resulting
SE will be roughly sqrt(2) larger than the N = 12 cells'; say so in the write-up.** The two N = 18
cells stay on OLP, where they are already running single-threaded.
`scripts/run_q3_sweep.py` now prints phase markers, so a long cell is no longer indistinguishable
from a hung one.

## CELL LANDED: 20:0.3:1, 2026-10-23 17:28:58, exit 0 [measured; ASSUMED prior, not an H2 result]
`runs/q3_sweep/cell_N20_h0.3_lam1.json`, 37,531 s of noisy-arm compute (10 h 25 m), reduced counts
(bare 60 / ice 24, 6 batches, `record_every` 6), encoded window 33 steps. Early-window residuals:

| mode | residual | shot cost | resolved |
|---|---|---|---|
| bare raw | 0.0342 ± 0.0056 | ×1.00 | yes |
| **bare + Gauss** | **0.0006 ± 0.0005** | ×1.42 | yes |
| Iceberg | 0.0066 ± 0.0046 | ×2.63 | yes |
| Iceberg + Gauss | 0.0020 ± 0.0013 | ×2.85 | yes |

**The §9.2 verdict survives the largest size run:** bare + Gauss beats Iceberg by 0.0060, larger
than the combined SE, at half the shot cost. Iceberg's residual is *lower* than at N = 12 (0.0066
vs 0.0222), but its window is 33 steps against 48 — the same handicap-in-its-own-favour caveat
§4.2 reading 3 makes for λ. Not written into §4.4 yet: the project lead's rule is that §4.4 waits
for all four size-axis cells.

**CALIBRATION [measured]: the cell cost 2.7× the derived 2^(physical) estimate** (37,531 s against
≈3.8 h predicted). Use 2.7× when projecting the remaining cells, with the caveat that this is one
Windows box running one cell, while OLP runs two cells on four cores under Python 3.14.
Local follow-on **20:0.5:3 started 17:28** (pid 3932, window 12, same reduced counts).

## DECISIONS, 2026-10-23 17:40 (project lead)
- **§4.4: DRAFT now, PUBLISH only when all four size-axis cells are in.** The draft lives at
  `.../ab444dc3-.../scratchpad/q3_scaling_4_4_draft.md` with the landed 20:0.3:1 row at full
  precision and PENDING placeholders; `docs/q3_scaling.md:272-278` is untouched.
- **18:0.1:3: keep it running. When 18:0.3:1 lands, measure OLP's real rate from it, re-project
  18:0.1:3 and bring the re-cut question back to the project lead.** Never kill or re-cut unasked.
  Facts behind the decision [measured, `data/q3_hqc.txt`]: on the emulator that cell would cost
  **≈ 30,839 HQC = 62 % of the whole 50,000 allowance** (bare arm 27,672 of it, forced by the
  480-step window at h = 0.1), against 17,540 for 18:0.3:1 and 18,689 for 20:0.3:1, with 39,853
  already earmarked in `docs/h2_budget.md` — so it is **never** an emulator or hardware run, and
  hardware is not available anyway (the 50k are emulator credits; no hardware allowance is shown).
  Its encoded window is only **13 steps** against a 480-step bare arm, so it is a **cost /
  acceptance** data point — does weak field compound with amplified noise in the Gauss shot cost —
  **not a headline-residual one**. Classically it costs 0 HQC, which is what it is being run as.

## STUCK-CHECK, 2026-10-23 17:00 (project lead asked): none of the three is stuck [measured]
Probed directly rather than inferred from elapsed time:
- **OLP 107889 / 107890:** process state **R** (running), `wchan` **0** (not blocked in any kernel
  wait), **1 thread** each, `utime+stime` advanced **45.1 s of CPU in 45 s of wall time** (100 % of
  a core, both), and **voluntary context switches frozen at 36 / 33** — i.e. they have not waited
  on I/O, a lock or a socket even once in hours. **Minor page faults: ~140,000 per 10 s each**
  (~14 k/s, ~55 MB/s of fresh page touches), which is precisely the signature of the profiled hot
  path (non-contiguous `reshape` copying the whole state vector ~3× per gate). **Swap 0**, 2.6 GB
  free, no thrashing.
- **local 29924:** single thread, `ThreadState` 2 (Running), **44.8 s CPU in 45 s wall**.

**Expected vs actual [derived from the 2^(physical) anchor: 18 phys ≈ 0.16 s, 20 ≈ 0.6 s,
22 ≈ 2.5 s, 24 ≈ 10 s per trajectory-step; bare-arm windows 160 steps at h = 0.3 and 480 at
h = 0.1; λ = 3 multiplies the noisy arms' gate count ≈ ×3]:**

| cell | counts | expected | CPU so far | ratio |
|---|---|---|---|---|
| 18:0.3:1 (w 36) | config defaults, bare 200 / ice 100 | bare 1.4 h + ice 2.5 h ≈ **3.9 h** | 11.3 h | **2.9×** |
| 18:0.1:3 (w 13) | config defaults, bare 200 / ice 100 | bare 12.8 h + ice 2.7 h ≈ **15.5 h** | 11.3 h | **0.73× — not yet due** |
| 20:0.3:1 (w 33) | reduced, bare 60 / ice 24 | bare 1.6 h + ice 2.2 h ≈ **3.8 h** | 9.2 h | **2.4×** |

**Reading.** The two "over" cells are over by 2.4–2.9×, which the derived model's own uncertainty
covers (its anchor was never measured uncontended on these boxes) plus OLP running two cells on
four cores and Python 3.14. **18:0.1:3 is the longest cell of the four by construction** — h = 0.1
gives it a 480-step bare window and λ = 3 triples the gate count — so at 11.3 h it is roughly
three-quarters of the way through its own estimate and killing it at a flat 12 h would discard the
cell that is behaving most as predicted.

**Progress fraction is not observable** for any of them: `scripts/run_q3_sweep.py` prints only two
markers, after the ideal reference and after the *whole* noisy block, so once a cell enters
`run_noisy_sweep` there is no finer signal until it finishes. The local cell printed its first
marker at 07:03 and has been in the noisy arms since. A future re-cut should print per-arm and
per-batch markers.

## Superseded guesses (kept so the reasoning trail is honest)
The size-axis cells cost much more than the D5 scaling argument predicted, and **the reason is not
yet established.**

What is measured: an N = 18 cell with only **2 trajectories** per arm, a 4-step encoded window and
2 batches ran **> 14 min without finishing** on an otherwise idle OLP core. Two trajectories cannot
be the per-trajectory cost, so a large **fixed per-cell cost** is implied - plausibly the
`run_iceberg` setup at 2^(N+4) (the `lidx` parity construction over 4.2 M amplitudes per logical
qubit, `zdet`, the memory check) and/or pytket schedule construction, which `_boundaries` builds
three times. An arithmetic estimate of the other candidate, observable evaluation in
`run_observables` (~(1 + n_batches) x n_records x 2^N full-table passes), comes out at only tens of
seconds at N = 18, so **that hypothesis is probably wrong** - an earlier version of this note
asserted it and should not be trusted.

**Unresolved because both measurements were killed** by the local memory reaper (the D5 probe, then
this calibration). Do not restart either unasked. If the split matters for a re-cut, measure it
deliberately on an idle machine: time `make_iceberg` + `run_iceberg` setup alone, then one
trajectory, then scale. Note that a large FIXED cost would mean re-cutting trajectories or batches
buys little, which is the opposite of what the earlier note implied.

## The D4 cell list (one axis at a time + extremes), with survival-matched encoded windows
Field axis (N = 12, lam = 1): h = 0.1, 0.2, 0.3, 0.5, ice window 48 steps.
Size axis (h = 0.3, lam = 1): N = 18 -> 36, N = 20 -> 33.
Noise axis (N = 12, h = 0.3): lam = 2 -> 28, lam = 3 -> 19.
Extremes: (20, 0.5, 3) -> 12, (18, 0.1, 3) -> 13, (12, 0.5, 3) -> 19.
`data/q3_scaling.txt` §6 lists the FULL 36-cell cross product; the 11 above are what D4 actually runs.

## Next action (in this order)
1. **Wait for (20, 0.5, 3)**, then `.venv\Scripts\python.exe -I scripts/run_q3_sweep.py --merge`
   (idempotent; it rebuilt `data/q3_sweep.txt` from 10 cells at 20:01).
2. Add that cell's row to `docs/q3_scaling.md` 4.4 and its survival row to 4.3, then re-run BOTH
   transcription checkers, now in the repo: `.venv\Scripts\python.exe -I
   scripts/check_q3_doc_table_42.py` (4.2, 21 triples) and `scripts/check_q3_doc_table_44.py`
   (4.4; it exits 2 until 4.4 is actually written). The 4.4 text to paste is
   `handoff/q3_scaling_4_4_draft.md`, which covers the three cells that had landed by 20:00 - add
   the fourth cell's row from the merged data file.
3. Run the full local suite `.venv\Scripts\python.exe -m pytest tests\ -q` (expect 705 passed +
   23 skipped) once the cell has freed its memory.
4. Stage 6: blind `peer-review`, 2 reviewers, on the module + the results.
5. Stage 7: fold the size-axis finding into `handoff/plan.md` 30 and write the lead summary.
6. Still owed regardless: the free H2-1SC quotes (need `NEXUS_REFRESH_TOKEN`, absent here) and the
   `method="fold"` encoded variant (NotImplementedError by design; folding syndrome CX would change
   the detection structure - an open design question, not a bug).

## PUBLICATION STATE of the size-axis text, 2026-10-23 20:10 [corrected]
`docs/q3_scaling.md` 4.3 and 4.4 are **back to their pre-publication state** (4.4 still says
PENDING). An earlier edit this evening published a three-cell 4.4 and three extra 4.3 survival rows,
which **contradicted the project lead's 17:40 decision** ("4.4 is drafted now, published only when
all four size-axis cells are in"); it was reverted as soon as that decision was read. The full text,
with all three landed cells, is drafted at
`C:\Users\kevin\AppData\Local\Temp\claude\C--Work---TFIM-QEC-Frustration\01b3c4d4-9ac8-4e1a-a006-8dda2dc55bef\scratchpad\q3_scaling_4_4_draft_3cells.md`
and supersedes the one-row draft in the ab444dc3 scratchpad. Every number in it was verified against
`data/q3_sweep.txt` (0 mismatches). **`data/q3_sweep.txt` itself IS updated to 10 cells** - that is
the reproducible data file, not the write-up, and the merge is idempotent.

**TWO SESSIONS WERE WRITING THIS FILE.** A second session (ab444dc3 / eed7652b scratchpads) has
been working with the project lead since ~17:00 and wrote the CELL LANDED, DECISIONS, STUCK-CHECK
and MEASURED RUNTIME MODEL sections; this session rewrote "Running jobs" and "Next action" at 20:03
without having seen them. Nothing of theirs was lost (their sections sit outside the two blocks that
were replaced), but **run one loop at a time**: concurrent sessions on one live-state file is how the
4.4 decision came to be missed in the first place.

## THE SIZE-AXIS FINDING (new, 2026-10-23 20:00) - read before writing anything about Q3
`docs/q3_scaling.md` 4.4. At the published field and noise scale the verdict SURVIVES size:
bare+Gauss beats Iceberg at N = 18 (gap 0.0209) and N = 20 (0.0060) as at N = 12 (0.0205), with the
same x1.4 vs x2.6-2.8 shot cost. **But at the extreme corner (18, 0.1, 3) the two arms are a
statistical TIE** - bare+Gauss 0.0185 +- 0.0030 vs Iceberg 0.0163 +- 0.0079, gap 0.0022 against a
combined SE of 0.0085. bare+Gauss's residual there is ~10x its value in every N = 12 cell, because
the h = 0.1 bare window is 480 steps carrying 47.69 faults/shot at lam = 3, so post-selection
rejects almost everything (late-window cost **x303.9**). **So the verdict is CONDITIONAL on the bare
circuit's fault load per shot staying modest, and that condition weakens as N, 1/h and lam are
pushed together.** This is a boundary of 9.2, not a contradiction - and the single published cell
could not have revealed it. Do not restate the Q3 conclusion without this qualification.
**Caveat to carry with the N = 20 row:** reduced counts and a 6-7 point early window (vs 25 at
N = 12), and its measured survival came out 3/24 = 0.125 against the 0.051 the window was matched
to, so that cell is a consistency check, not a precision measurement.

## Cross-check DONE (2026-10-23): measured survival vs Stim first-order
`docs/q3_scaling.md` **§4.3** (the size axis moved to §4.4). All seven landed cells agree within
**1.4 sigma** with `exp(-(prep offset + rate x steps))` from `data/q3_scaling.txt`, no systematic
sign; survival's predicted h-independence also holds (lam = 1 spread 0.050-0.070 across a fivefold
field change = binomial noise about a constant; surviving counts are 15, 17, 21, 21 of 300).
This is the plan's "independent cross-check, a different code path" item, discharged.

## Doc-vs-data transcription check (2026-10-23)
`check_doc_table.py` in the session scratchpad re-derives every number in `docs/q3_scaling.md`
§4.2 from `data/q3_sweep.txt`: **21 triples (residual, SE, shot cost) match exactly, 0 mismatches**,
plus the seven verdict gaps. Re-run it after the size-axis cells land and §4.3 is written — it is
the cheapest guard against a hand-typed table drifting from the data.
`check_doc_44.py` (same scratchpad) does the same for 4.4's size-axis table: **9 triples plus the
verdict, window and physical-qubit columns per cell, 0 mismatches** (2026-10-23 20:02).
One lesson baked into both: the verdict gap is computed from FULL-PRECISION residuals, so comparing
it against the difference of the printed (rounded) values is wrong by up to 1e-4. The first version
of the check flagged h = 0.2 for exactly that reason and the doc was right.

## Suite gate status (2026-10-23)
- **OVM, CURRENT tree: 705 passed, 23 skipped, 0 failures, 48 min** (`.logs/suite2.log`,
  Python 3.12.14 aarch64) — the earlier 700-test run plus the 5 new scorer tests, count reconciling
  exactly. This is the gate for the code as it now stands, including the two reporting fixes.
- Earlier run, same platform, pre-scorer-tests: **700 passed, 23 skipped, 48 min**
  (`~/q3scaling/.logs/suite.log`). The owed Stage-1 gate was discharged there.
  Arithmetic checked: the four new test files contribute **38** tests (`--collect-only`), and
  662 baseline + 38 = 700 exactly, so nothing was lost or silently skipped.
- **OLP: not launched.** The command that was shipping the two updated files and launching both
  suites was killed by Claude Code's local low-memory reaper after the OVM leg, so OLP still has
  the pre-fix `src/noisy_q3_sweep.py` / `scripts/run_q3_sweep.py` and no suite run. Per the
  reaper's instruction it was NOT restarted; relaunch when memory is free or when asked.
- **KILLED BY THE LOW-MEMORY REAPER, 2026-10-23 ~15:40 — do NOT restart either unasked.** Claude
  Code's background-shell reaper stopped **both** the non-slow suite and the cell watcher while the
  session was idle (free RAM 2.1 GB of 15.26 GB, commit 26.8 GB, 2.12 GB held by Windows Memory
  Compression). Neither was a failure of its own. **The suite was clean where it got to: 413
  passed, 23 skipped, 0 failed, 0 errors, at 60 % of the non-slow selection** (it was in
  `tests/test_h2_review_fixes2.py`). The results cell 29924 was untouched. With the watcher gone,
  cell detection falls back to the loop's ~25 min heartbeat poll, which is adequate.
- **Local, 2026-10-23 13:30–14:45: the NON-SLOW suite was running**
  (`pytest tests\ -v -m "not slow"`, single process, `OMP_NUM_THREADS=1`, log
  `.../ab444dc3-.../scratchpad/suite_notslow.log`), per the project lead's call: the slow tests are
  themselves 16–22-qubit trajectory runs and would contend with the live 20-qubit cell. **The full
  705 + 23 gate is still owed** and runs once no heavy cell holds the local box.
- **QI-16 found and logged 2026-10-23: `selene-sim` 0.3.4 `.run()` hangs forever on Windows.**
  A hello-world Guppy program (1 qubit, 1 shot, no noise) blocks in `.run()` with **0 CPU over a
  20 s sample**, a loopback listener in `Listen` state and **no child process** — the simulator is
  never spawned. Minimal reproduction, evidence and the ask upstream are in
  `docs/quantinuum_issues.md` **QI-16**; the repro script is
  `.../ab444dc3-.../scratchpad/selene_min.py`. **No repository result is affected** — all Selene
  numbers were produced on Linux and the OVM suite passes all three Selene tests. On Windows the
  suite now runs with them **deselected** (never skip-marked in the files):
  `test_encoded_codes.py::test_selene_generated_program_feedforward`,
  `test_encoded_tfim.py::test_selene_feedforward_and_consistency`,
  `test_twirl.py::test_selene_accepts_twirled_program_at_zero_noise`. **Consequence for the gate:
  the local Windows suite can only ever reach 705 − 3 = 702 + the slow tests; the authoritative
  full-suite gate for Selene coverage stays the Linux (OVM) run.**
- **TOOL FACT learned 2026-10-23 (not a project bug):** the first attempt **hung after 72 tests**
  — PowerShell `python -m pytest ... | Out-File` launched with `run_in_background`. The process
  was **hard-blocked**, not slow: 0 CPU and 0 page faults over a 20 s sample, main thread in a
  UserRequest handle wait, 116 s CPU total, normal priority. **The tests were not at fault** —
  `tests/test_dimers.py` alone passes 35/35 in 8.5 s — so the block was in the PowerShell pipe
  carrying pytest's stdout, and `-q` dot output made it invisible (dots only flush at 72-char line
  ends, so the log pinned nothing down). Fix, and the pattern to reuse: **`Start-Process` with
  `-RedirectStandardOutput` so the child writes straight to a file with no pipe, `-Wait`/
  `WaitForExit` inside a backgrounded wrapper so completion still notifies, and `-v` so the log
  names the test in flight.** Nothing of the project's was lost; the re-run started at 14:45.
- Note: the two fixes OLP is missing are cosmetic/reporting only (`resolved` requires SE > 0; "-"
  instead of `nan`), so the seven N = 12 cells it produced are unaffected.

## MEASURED RUNTIME MODEL, 2026-10-23 19:55 — supersedes the derived 2^(phys) anchor and the ×2.7 calibration
Fitted to the **eight landed cells' own `provenance.seconds_noisy`** (script
`.../eed7652b-.../scratchpad/project_cells.py`), not to an a-priori scaling argument.

**Model [derived from measured]:** `T_noisy = k_host * W`, with
`W = traj_b*n_bare*2^N*w(lam) + traj_i*n_ice*2^(N+4)*w(lam)` — i.e. amplitude-touches, which is
what the profile said the cost is (gate-by-gate state-vector application). Fitted `w(lam>1) = 1.22`
from the three OLP N = 12 h = 0.3 cells; the encoded arm is **55-86 % of every cell's cost**.

| anchor | k (s per amplitude-step) |
|---|---|
| 16 phys, OLP (4 cells, but **run 4-at-a-time**, so contention-inflated) | 8.9e-6 |
| 16 phys, Rakata | 5.0e-6 |
| 16 phys, OVM | 1.7-2.0e-6 |
| **24 phys, Rakata** (the landed 20:0.3:1) | **1.61e-6** |

**k falls 3.1× from 16 to 24 physical qubits**, so the small cells are per-gate *overhead*-bound and
any k fitted at N = 12 **overestimates** a big cell. That, not a pathology, is why the cells looked
"2.4-3.7× over": the derived anchor was calibrated in the wrong regime.

**Projection of the three in-flight cells** (`T_lo` = 24-phys anchor, `T_mid` = log-interpolated in
physical qubits; honest bracket is `[T_lo, T_mid]`, and the OLP contention caveat pulls OLP toward
or **below** `T_lo`):

| cell | W | T_lo | T_mid | CPU done | frac | remaining |
|---|---|---|---|---|---|---|
| OLP 18:0.3:1 | 2.35e10 | 18.8 h | 25.0 h | 14.4 h | ~57-76 % | **4-11 h** |
| OLP 18:0.1:3 | 3.74e10 | 29.9 h | 39.7 h | 14.4 h | ~36-48 % | **15-25 h** |
| local 20:0.5:3 | 1.33e10 | 5.9 h | 5.9 h | 2.3 h | ~39 % | **~3.6 h** |

**Reading: none of the three is anomalous, and all four size-axis cells can land within ~24 h.**
The earlier "×2.7 calibration" and the ×3.6 "overrun" are artifacts of the superseded anchor.
(20:0.5:3's ≈14 h figure in the Running-jobs note below is from that old anchor; read 5.9 h.)

## MODEL CHECK, 2026-10-23 20:05 [measured] - both OLP cells landed BELOW the bracket
The two N = 18 cells finished at **19:51 and 19:56 local**, minutes after the 19:50 stuck-check, so
that section's "4-11 h / 15-25 h remaining" is resolved, not pending. Measured
`seconds_noisy`: **51,732 s (14.37 h)** for 18:0.3:1 and **51,906 s (14.42 h)** for 18:0.1:3,
against the model's `T_lo` of 18.8 h and 29.9 h - i.e. **0.76x and 0.48x of the low end of the
bracket**. The amplitude-touch model is therefore not yet predictive on OLP: it was conservative,
which is the safe direction, but the second cell was out by 2x.

**The striking fact to explain before the model is reused:** the two cells took the SAME time to
within 0.3 %, although their fitted `W` differs by 1.6x. Likeliest reading [inferred]: the encoded
arm dominates (the model's own fit says 55-86 %), and the two encoded arms are nearly equal work -
18:0.3:1 runs 36 steps at lam = 1, 18:0.1:3 runs 13 steps at lam = 3, so ~36 against ~39
lam-weighted steps on the same 22-qubit state vector. If that is the explanation, the bare-arm term
(which differs 9x in steps between them) contributes far less than the fit assigns it, and `W`
should be re-fitted with the encoded arm as the leading term before it is used to project anything.

## STUCK-CHECK, 2026-10-23 19:50 [measured] — all three busy, none blocked
OLP **107889 / 107890**: state **R**, `wchan` **0**, **1 thread** each, **45.0 s CPU in 45 s wall**
(100 % of a core each), voluntary context switches still frozen at **36 / 33** (never waited on
I/O, a lock or a socket in 14 h), minor faults **+614 k / +624 k per 45 s** (~13.7 k/s — the
profiled non-contiguous-reshape signature), **swap 0**. Local **3932**: 2 h 19 m CPU in 2 h 21 m
wall, RSS 0.86 GB. Free local RAM 1.75 GB of 15.26 GB — still **not enough headroom for the owed
full suite** while the 24-qubit cell holds the box.

## Running jobs
**Checked 2026-10-23 20:03.** Three of the four size-axis cells FINISHED and are merged:
- **(18, 0.3, 1)** on OLP, 51,732 s (14.4 h) -> `cell_N18_h0.3_lam1.json`, scp'd here.
- **(18, 0.1, 3)** on OLP, 51,906 s -> `cell_N18_h0.1_lam3.json`, scp'd here.
- **(20, 0.3, 1)** local serial runner, exit 0 at 17:28 -> `cell_N20_h0.3_lam1.json`.
- OLP is now idle (both pids gone, verified); OVM idle.

**Still running (the only job left):** local **(20, 0.5, 3)**, python pid 3932, started 17:31
(ideal arm 151 s), at 2.5 h CPU and 2.11 GB RSS, single-threaded, reduced counts
(traj 60 bare / 24 Iceberg, 6 batches, `record_every` 6). **Expected total 5.9 h from the MEASURED
amplitude-touch model above, i.e. ~3.6 h left as of 19:55 -> lands ~23:25.** Ignore any "2-3 h" or
"~14 h" figure for this cell: both came from the superseded derived anchor. It is the last of the
11 D4 cells.
- **Local suite is deferred again, deliberately:** only **2.38 GB free** with that cell holding
  2.11 GB, and launching 705 tests risks the low-memory reaper killing a 2.5 h run. The gate is
  already discharged for the CURRENT tree on OVM (705 passed / 23 skipped) and **no Python has
  changed since** — only docs. Run the local suite after the cell lands.
- A finished cell prints its early-window residuals at the end of its log; `runs\q3_sweep\logs\serial.log`
  carries the serial runner's phase markers.

## Project-level gap analysis (written 2026-10-23, outside the Q3 pass)
`docs/project_gap_analysis.md` — stock-take of all four SCOPE questions plus the §3 Gauss thread:
what is simulated, the four missing head-to-heads (A codes-by-distance, B noise-model sensitivity,
C non-diagonal observables, D frustration contrasts), three decision cards (**OPEN-5/6/7**, drafted
NOT recorded in `DECISIONS.md` — the project lead decides), the measured runtime model, and the
recommended order. All four gaps are classical and need **0 HQC**. Key open item it raises:
Gauss-law post-selection may be **structurally** unable to protect off-diagonal observables
(the constraint is diagonal in Z, so post-selection and X-basis readout may be mutually exclusive
within a shot) — flagged [derived, NOT verified], wants the `derive` skill before any code.

## LOCAL SUITE: the ab444dc3 attempt did NOT complete - gate still owed [measured 2026-10-23 20:30]
That session's `suite_notslow.log` (its scratchpad) stops **mid-test at 60 %** with no summary line,
and its `.err` reads `ERROR: file or directory not found: slow` (the `-m "not slow"` marker was
mangled by cmd's `^` continuation). **So the local suite gate is NOT discharged**; the OVM run
(705 passed / 23 skipped on the current tree) is still the only gate.
**Reuse their one real finding when the local suite is finally run:** three Selene tests HANG on
Windows (QI-16), so the local invocation needs
`--deselect tests/test_encoded_codes.py::test_selene_generated_program_feedforward`,
`--deselect tests/test_encoded_tfim.py::test_selene_feedforward_and_consistency`,
`--deselect tests/test_twirl.py::test_selene_accepts_twirled_program_at_zero_noise`,
with `OMP_NUM_THREADS=1` and the OpenBLAS/MKL/numexpr equivalents set. Their `suite_notslow.cmd`
is a working template apart from the marker-quoting bug.

## Q2 AUDIT, 2026-10-23 20:25 [corrected] - Q2 is DONE, and the gap analysis was wrong about it
Audited `docs/q2_frustration.md`, `docs/findings_vs_questions.md`'s Q2 row, `review/12` and the
data files. **Q2 Part A meets SCOPE 2's "done when" and is reviewed ACCEPT; Part B was CANCELLED by
the project lead under PROC-2.** Q2 is deliberately scoped, not thin. Two corrections made:
- `docs/project_gap_analysis.md` **Gap D is withdrawn** with the reasons written out, because its
  earlier text recommended exactly the Part B work PROC-2 cancelled, and the dimer/winding
  observables have no square counterpart to compare against anyway.
- `docs/q2_frustration.md` gained a **section 0 summary** (done-when verdict, the headline numbers,
  what is not claimed, data pointers) and an **open-flags table**; the stale T-19 sentence in A.2 is
  **date-annotated, not rewritten** (T-19 was applied on 2026-10-08 - caveat in the script, data
  regenerated), per the project's "annotate superseded records" rule.
**The one live Q2 question: T-20, the clock-order parameter K3** - the only observable that
separates three-sublattice order from the torus-shape sign effects Part A reports and declines to
interpret. Not built; reopening it means revisiting PROC-2, which is the project lead's call.

## Notes
- The private journal and `open-questions.md` do not exist on this machine: say so, never invent entries.
- `.venv\Scripts\python.exe -m pytest tests\ -q` is the gate before any report (~662 pass + 23 skip baseline).

## INDEPENDENT RE-DERIVATION of the size-axis numbers, 2026-10-23 20:15 (session 74acfd92)

A third session, started by the project lead with `/loop`, re-derived the size-axis table **from
the `runs/q3_sweep/cell_*.json` files directly**, without reading the 20:00 finding first. It
reproduces it exactly [measured]:

- gaps bare+Gauss vs Iceberg: N = 12 **0.0205**, N = 18 **0.0209**, N = 20 **0.0060**;
- (18, 0.1, 3): bare+Gauss 0.0185 ± 0.0030 vs Iceberg 0.0163 ± 0.0079, gap **0.0022** against a
  combined SE of **0.0085** — a statistical tie, Iceberg nominally ahead;
- cost convention validated: the published §4.2 row (12, 0.3, 1) reproduces as
  `0.0017 ± 0.0004 ×1.43` using `cost` (the mean), **not** `cost_final` (which would read ×2.04).

This is two independent paths to the same numbers, so the 20:00 finding is confirmed rather than
merely restated. Draft (superseded by the 01b3c4d4 three-cell draft, kept for the audit trail):
`C:\Users\kevin\AppData\Local\Temp\claude\C--Work---TFIM-QEC-Frustration\74acfd92-92d5-4349-842e-d14ef6893846\scratchpad\q3_section_4_4_draft.md`

**Verified state at 20:15 [measured], nothing changed by this session:**
- OLP: PIDs 107889/107890 **gone**, both N18 JSONs complete (17:51, 17:56 OLP time), full counts
  200/100 × 10 batches — the "~30 h more" projection for (18, 0.1, 3) was over-pessimistic, not a
  truncated run. Host idle. Local copies byte-match the OLP originals (82,670 / 32,939 B).
- Local: PID 3932 (20, 0.5, 3) alive, 9,633 s CPU over 9,741 s elapsed = **99 % of one core**,
  tracking — slow, not stuck. Next 12 h mark ≈ 05:28 tomorrow; projection ≈ 07:30.
- `docs/q3_scaling.md` §4.4 correctly still **PENDING**; `data/q3_sweep.txt` at 10 cells.
- **No commit, no push, no hardware, no Nexus, no HQC.** This session wrote only this section.
