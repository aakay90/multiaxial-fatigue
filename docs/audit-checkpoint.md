# Development continuation checkpoint

Updated 16 October 2026. This is the single development checkpoint. Read this
section, check Git status and recent commits, then verify the recorded state
before changing code. The previous scientific audit remains below as historical
context and must not be repeated for calibration-pipeline work.

## Current objective and recovery state

The JSON calibration, run-out, native-life and recovery workflows are implemented
and tested. Branch `feat/calibration-history-runouts`.
PR [#5](https://github.com/andreachiocca/multiaxial-fatigue/pull/5) is open for
review and has not been merged. The verified implementation commit is
`f0df0a7a9588b59fc7abca051bbf1790da853230`. Use `git log -1` for the later
checkpoint-only commit. The five previous local implementation commits were
recovered rather than reimplemented. Their original local history, including
this session's incremental work, is retained on
`recovery/calibration-workflow-20261016` in the working checkout.

| Requirement | Actual status |
|---|---|
| JSON export, metadata, historical IDs and compatible loading | Implemented and tested successfully |
| Experimental properties separated from fitted coefficients | Implemented and tested successfully |
| Four workbook migrations and byte-identical original archive | Implemented and verified against public main |
| Failure-only fitting, run-out import, statistics and plots | Implemented and tested successfully |
| Native cycle outputs bypass damage fitting | Implemented and tested with a synthetic model |
| Suppression of duplicate equivalent calibrations | Implemented and tested successfully; sequential equivalent exports reuse the stored ID |
| Persistent checkpoint and recovery instructions | Checkpoint committed; mandatory milestone procedure added to `AGENTS.md` |
| Publication | PR #5 open; remote implementation tree verified equal to local tested tree; push and PR CI passed on f0df0a7; human review pending |

## Code and verification

Relevant files are `0_calibrate_material_params.py`, `1_run_material.py`,
`2_compare_results.py`, `fatigue/eval/calibration_store.py`,
`fatigue/eval/calibration.py`, `fatigue/eval/direct_life.py`,
`fatigue/imp/experimental_data.py`, `fatigue/imp/observations.py`,
`fatigue/models/base.py`, `fatigue/report/export_csv.py` and
`fatigue/report/observations.py`. Format and migration details are in
`docs/calibration-workflow.md` and `docs/calibration-verification.md`.

Executed successfully in this session before this checkpoint update

- `MPLBACKEND=Agg python tools/run_tests.py`, 39 tests passed after the portable calibration-fixture correction.
- Baseline and revised `tests/run_material_validation.py`, 64 runs each.
- `python tests/compare_material_regression.py /tmp/wg43-old-20261016 /tmp/wg43-current-20261016`, all 3,936 original failure rows exactly equal, with 672 additional censored rows.
- Ruff, dependency consistency, generated-method documentation and local documentation-link checks passed.
- Failure-only versus failure-plus-run-out coefficient and curve regressions passed.
- Script 0 to JSON to Script 1 and CSV/plot integration passed on AISI316L.
- Repeated Script 0, then Script 1 and Script 2 passed on AISI316L/BP in `/tmp/wg43-final-e2e`; exactly one JSON record, 31 failures and 13 run-outs, with censored errors undefined.
- GitHub Actions passed on `f0df0a7` for both [PR checks](https://github.com/andreachiocca/multiaxial-fatigue/actions/runs/38967518197) and [push checks](https://github.com/andreachiocca/multiaxial-fatigue/actions/runs/38967513186).

These are software tests and numerical regression comparisons. They do not
establish independent experimental validation of the fatigue criteria. Initial
JSON coefficients were transferred without re-optimisation; their original
calibration settings remain unverified. Original `Results/*.csv` are unchanged.

## Blockers and precise next action

Automatic publication review rejected the illustrative PNG. It was removed in
`7dd9f35` and replaced with reproducible plotting instructions. Do not publish
`docs/images/runout-example.png` or a historical tree containing it. All four
cleaned workbooks and the original archive were checked against existing public
repository data. The published PR contains the image-free code, JSON records,
cleaned workbooks, original archive and this checkpoint. No publication blocker
remains for the requested workflow.

Equivalent-export reuse, changed-output history and metadata preservation are
now tested. Modified files in this milestone are `AGENTS.md`, Script 0,
`fatigue/eval/calibration_store.py`, `fatigue/eval/calibration.py`,
`tests/test_calibration_workflow.py`, the workflow and verification documents,
and this checkpoint. No known local test failure remains. These changes are
committed and published. A later CI diagnostic milestone adds
`tools/run_tests.py` and updates `.github/workflows/quality.yml` to expose test
tracebacks as check annotations without changing discovery or test assertions.
The diagnostic runner also passes all 39 tests locally.

On `d7c0c65`, the push CI run succeeded but the PR CI test job failed, while its
catalogue job passed. The connector supplied only exit status and did not expose
the traceback. The diagnostic runner exposed the cause on `2384227`. The old
two-plane MSWT fixture used only five torsion observations, so its objective had
tied coefficient values within floating-point rounding. A three-plane fixture
was generated from the original `e70a8af` checkout, retains all 11 failure points
and has separated objective minima for all five methods. Tests now compare that
baseline and recompute its objective grids. Original fixtures, production search
procedures and fatigue formulations are preserved. The correction passes all 39
tests locally and both push and PR CI checks on `f0df0a7`. No active test or
publication blocker remains for this task.

Next action is to review PR #5, confirm its current checks and check Git status
before making changes. Address concrete review feedback on the same
branch, run the relevant tests, update this checkpoint and commit verified work.
Do not recreate this implementation or open a duplicate PR. Do not merge without
an explicit user instruction. Independent original-paper validation listed in
the historical audit below remains outside this pipeline-refactoring task.
At every later milestone record tests, uncommitted changes, blockers and the next
executable step before committing. Use `git log -1` for the containing checkpoint
commit; a file cannot embed its own commit hash.

## Historical scientific audit, 7 October 2026

## Completed

- Resumed the existing working tree and preserved the previously published Böhme–Papuga and CAIM implementations and their tests. BP and CAIM are distinct formulations and remain separately selectable.
- Reviewed all 20 registered base methods. Corrected engineering shear factors, Findley plane selection, Li mean shear, Liu's removable zero-shear singularity, harmonic strain decomposition, zero-shear cancellation, and critical-plane ties. See [method-audit.md](method-audit.md) for equation-by-equation scope and limitations.
- Disabled CARSPA, DANGVAN, OTT, SWTD and ZHU_EDP, including direct evaluation guards, with reasons and restoration requirements. Removed obsolete ZHU_EDP calibration.
- Added source metadata and a [bibliography](bibliography.md) for every method. CSVs identify the method reference and implementation revision; comparisons exclude disabled and pre-audit results by default.
- Added `Error_log10_dp = log10(DP_e/DP)` to export, statistics and plots for all slopes, including exactly flat curves. Fitting no longer inverts nearly flat curves. Invalid fits/calibration objectives fail explicitly.
- Preserved experimental workbooks and historical result CSVs. Corrected results must be regenerated; fitted method constants need recalibration before quantitative model rankings.

## Verification completed

- `MPLBACKEND=Agg python -m unittest discover -s tests -q`: **20 tests passed**, including the existing BP/CAIM reference cases and new numerical/reporting regressions.
- `MPLBACKEND=Agg python tests/run_material_validation.py /tmp/fatigue-audit`: **64 runs / 3,936 rows passed**, covering 15 retained base models plus FS_ext on all four supplied materials. Checks include finite damage/log ratios, source metadata, ratio recomputation and suppressed life predictions in DP_DIFF mode.
- `MPLBACKEND=Agg python 2_compare_results.py --results_dir /tmp/fatigue-audit --out_dir /tmp/fatigue-audit-plots`: passed, **21 PNG plots**, plus TikZ and statistics. All four materials have log10 damage statistics for 16 variants; the three with usable negative slopes also have life statistics. AISI316L has 496 damage-space rows and no life predictions. Inspected its damage boxplot visually.
- An exactly-flat synthetic curve passed CSV export, plotting and statistics; legacy CSVs missing DP_fit passed the explicit opt-in path without crashing.
- Five retained parameter calibrations passed a coarse-grid smoke check on 42CrMo4_QT: FS, FIN, LI, MGSE_ZHU, MSWT. This is an execution check, not final recalibration of workbook constants.
- Python parsing/compilation and `git diff --check` passed. Final diff reviewed; no raw data or archived Results changes.
- Non-failing warnings: empirical steel-property fallbacks where material coefficients are missing; existing Matplotlib deprecation/marker warnings.

## Unresolved evidence and exact next action

Full original-equation/plane-rule verification is still incomplete for **LIU2021, MGSE_ZHU, MKBM and LI**. MSWT is associated with the reported scalar modified-SWT form and is not claimed to implement Jiang's complete incremental model. These limitations are explicit in the audit; passing implementation tests is not independent scientific validation.

**Next action:** obtain an accessible full original Liu et al. article (DOI `10.1016/j.ijpvp.2021.104532`), inspect Eq. (27) and the definitions of its normal strain and shear ranges, and compare them with `fatigue/models/cp_methods/liu2021.py`. Add an independently calculated published load case, then correct or disable the model if necessary. Continue in order with Zhu 2018 (MGSE_ZHU/MSWT), Li 2011 (MKBM), and Li 2021 (LI), using the DOI mapping already saved in the bibliography. Do not repeat completed BP/CAIM integration or the general audit. Then recalibrate affected parameters and regenerate comparisons before interpreting rankings.

No pending test failure is known. The unresolved item is source completeness, not a failed test. The shared elastic, harmonic and finite-plane-grid limitations are documented in the audit.

## Files changed in this audit

- `0_calibrate_material_params.py`
- `1_run_material.py`
- `2_compare_results.py`
- `README.md`
- `docs/adding-methods.md`
- `docs/architecture.md`
- `docs/audit-checkpoint.md`
- `docs/bibliography.md`
- `docs/method-audit.md`
- `fatigue/eval/evaluator.py`
- `fatigue/eval/fitting.py`
- `fatigue/eval/metrics.py`
- `fatigue/models/cp_methods/car_spa.py`
- `fatigue/models/cp_methods/dangvan.py`
- `fatigue/models/cp_methods/fin.py`
- `fatigue/models/cp_methods/fs.py`
- `fatigue/models/cp_methods/gsa.py`
- `fatigue/models/cp_methods/gse.py`
- `fatigue/models/cp_methods/li.py`
- `fatigue/models/cp_methods/liu2021.py`
- `fatigue/models/cp_methods/mgse_yu.py`
- `fatigue/models/cp_methods/mgse_zhu.py`
- `fatigue/models/cp_methods/mkbm.py`
- `fatigue/models/cp_methods/mswt.py`
- `fatigue/models/energy_based_methods/swtd.py`
- `fatigue/models/energy_based_methods/zhu_edp.py`
- `fatigue/models/invariant_methods/ottosen.py`
- `fatigue/models/references.py`
- `fatigue/models/registry.py`
- `fatigue/models/utils/plane_history.py`
- `fatigue/report/export_csv.py`
- `tests/run_material_validation.py`
- `tests/test_method_audit.py`
