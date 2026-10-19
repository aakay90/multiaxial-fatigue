# Development continuation checkpoint

Updated 19 October 2026. Branch `feat/dataset-eligibility`, based on `022b6c0`.
PR #5 was merged into main before this session. The recovered JSON/run-out
implementation is preserved. No uncommitted changes existed at session start.

## Current objective and actual status

The revised dataset importer, method preflight, safe batch skips and observation
subset reporting are implemented. JSON history, formulations and family labels
are preserved. The remote branch exists; its first importer milestone
is `dfb514da82bd2792dd1d4da86fc0bb9dc9891e79`. Direct Git push has no credentials;
publication uses the GitHub connector. Local milestone history is retained.

- Active inputs are 12 revised workbooks plus unchanged Al7075_T6, absent from
  the revised collection. Four previous active files remain byte-identical in
  `Experimental_Data/archive/pre-dataset-migration` for reproducible regressions.
- Header aliases are explicit. Stress columns remain authoritative; force and
  moment columns are preserved metadata, never silently substituted. Phases are
  relative to the axial phase. Missing elastic properties leave strain undefined.
- Per-method input, conditional approximation, calibration and case checks are in
  `fatigue/eval/eligibility.py`. Script 0 skips each failed pair independently;
  Script 1 issues a controlled warning; Script 3 exports the matrix and can run
  compatible combinations. No automatic recalibration occurs during assessment.
- `fatigue/report/subsets.py` and Script 2 intersect identified failure
  observations separately for life and damage metrics. Individual results remain
  intact. Dataset fingerprints prevent mixing changed inputs; ambiguous IDs and
  duplicate results cannot enter a common comparison.
- New tests cover missing inputs/results, run-out-only data, conditional method
  requirements, batch continuation, and pairwise/group matched observations.

## Verification executed

`MPLBACKEND=Agg python tools/run_tests.py` passed 58 tests. Ruff, documentation
links, method catalogue and `git diff --check` passed. The original numerical
fixtures run against the archived original active workbooks, not substituted
new data. The attached previous collection was compared with the new collection
using `tools/audit_dataset_migration.py`; structured results are in
`docs/data/dataset-migration.json`. All 56 shared 42CrMo4_QT and 44 AISI316L
observations retain the supplied stresses. AISI316L properties changed.

Script 0 with n1=3, n2=6, grid=7, refine=2 explicitly generated/reused all 15
method calibrations on revised 42CrMo4_QT under `/tmp/wg43-new-calibrations`.
Script 3 assessed all 15 base methods plus FS_ext and skipped 48 unsupported
pairs in the selected four-material batch. BP/SWT common life comparison used
45 failure observations per method. Eleven run-outs per method remain in
individual outputs with undefined conventional errors. These are software and
regression checks, not independent scientific validation or final calibration.
Temporary example records are not installed as default production calibrations.
The common parity plot was inspected visually. The installer dry run, byte
preservation, legacy snapshot retirement and conflicting archive checks passed.

## Scientific limitations and precise next action

Do not silently correct measured source data. CX18 declares 30NCD16 in Summary;
Ti6Al4V includes a Summary name Ti64Al4V. Both identity conflicts are flagged.
AISI316L averages fatigue strengths at different R, so methods requiring its
reversed axial fatigue strength are blocked until that input is resolved.
En3B/GJS600 have only notched observations in the revised files and remain in
storage outside the current plain-specimen scope. Missing nu blocks strain
methods; run-out-only observations do not define an S–N curve. Steel empirical
estimates are blocked for non-steels unless the required fatigue properties are
supplied. Published historical results are unchanged.

Publication of the raw workbook tree was rejected by automatic review. The
repository was verified through the connector (owner andreachiocca, admin/push
permission, public visibility); all 12 files match the user-supplied ZIP exactly.
The instructions request replacement of active inputs and GitHub publication,
but the tree operation still requires explicit user confirmation for publishing
raw workbooks and embedded content. Do not bypass the rejection through Git or
an indirect reference. No new-workbook tree was attached to the remote branch.

The code-only publication preserves all previous public active files, adds
byte-identical public baseline archives and excludes the 12 revised files and the
detailed source-property export `docs/data/dataset-migration.json`. Local commit
`866d24d` retains the complete tested migration. The provided attachment and
`tools/install_revised_dataset.py` allow recovery after approval. Three full-data
tests are skipped remotely while the revised files are withheld; do not count
those as remote validation. Source-name restrictions remain as described above.

Next action is to finish final code checks and open the code-only PR, record its
link and ask for explicit publication approval for all twelve raw workbooks and
embedded images. After approval, install the supplied ZIP, regenerate reports,
run all tests, publish the dataset on the same PR and check CI. No merge is authorised.
No PR exists for this new branch yet. Resume from here, not the historical audit.

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
