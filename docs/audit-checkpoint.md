# Development continuation checkpoint

## Current phase, independent harmonic shear amplitudes

Updated 19 October 2026. Branch `feat/shear-amplitude-harmonic` starts at
`1154f86`, the stable main merge of dataset PR #6. The working tree was clean.
Experimental inputs, JSON records and previous implementation are preserved.
No existing independent two-component amplitude API was found. Existing private
RSS range and BP major-semiaxis expressions remain untouched.

Current objective is a standalone MCC/MCE library, analytical and reference-code
tests, and one short technical note. No production integration or configuration
change is authorised in this phase.

Reference inspection found active MCC and commented MCE expressions in the two
algebraic MATLAB Ca.m files. MOI/Ca.m uses path-length quadrature and is a different
definition. PragTic MCCM_IM/MCEM_IM process sampled polygons iteratively and are
not the harmonic solver to port. The full PDF is absent; supplied equation
transcriptions and MATLAB sources are available. Do not claim a full PDF review
or native MATLAB execution.

Baseline `1154f86` passed all 58 existing tests before implementation. The new
`fatigue/models/utils/shear_amplitude.py` supplies vectorised `shear_amplitude`
with explicit mcc_harmonic/mce_harmonic identifiers and the rss alias. It uses a
scaled closed-form Gram eigenvalue for MCC and the scaled Frobenius norm for MCE.
It rejects incompatible shapes, non-real/non-finite inputs and unrepresentable
outputs; exact zero is the only zero threshold. No production import was added.

The 12 tests in `tests/test_shear_amplitude.py` passed. They cover analytical
values, degeneracy, rotations/reflections and phase shifts, mean translation,
time sampling and LCM, batched inputs, SVD cross-checks, float64 extreme scales,
input rejection, existing RSS/engineering-strain conventions, BP equivalence,
and two MATLAB-equation load reconstructions. Ruff passed for both new files.
Tests first failed on the absent module, then passed after implementation.

The tested numerical milestone is published as `88229e93e2a2fb3527f23164537e2ab0c513351f`.
The technical note is [Independent harmonic shear amplitudes](shear-amplitude.md).
The complete suite passed all 70 tests (58 existing plus 12 new), without skips.
Ruff, documentation links, generated method catalogue and diff checks passed.
A final input-validation check also rejects nonzero extended-precision values
that would silently become zero when converted to float64.

A protected-path diff against `1154f86` confirmed unchanged production helpers,
numbered scripts, methods, criteria, requirements, calibrations, Excel inputs and
reference results. Only the new module, tests, note and this checkpoint belong to
this phase. The new module is not imported by any production file. Thus the
existing numerical implementation and its calibration fingerprints are preserved.
No new independent experimental fatigue validation is claimed.

The algebraic MATLAB files have identical SHA-256 `e96f70827fc0ce5c158ab56ade21af3a9eb8e4b72e47f205c5f3c93ab08092e5`.
Their active expression and commented alternative were reconstructed in two test
cases. Neither native MATLAB/Octave nor the PragTic application was executed.
The appendix MAT comparison array was inspected for scope, not used as a pure
amplitude benchmark. A 100,000-path timing comparison measured about 0.020 s for
scaled MCC versus 0.062 s for NumPy SVD; it is a local observation only.

Phase 1 is complete in [PR #7](https://github.com/andreachiocca/multiaxial-fatigue/pull/7),
open without merge. Verified implementation commit is
`2a17791d06e951a557c3d8707c2d156dbbb49f09`; a later commit only records this status
and clarifies a test comment. Both GitHub workflows passed, push run 39242032913
and PR run 39242046649. The published tree matches the tested local tree exactly.
The PR contains only four files: the amplitude module, its tests, the technical
note and this existing checkpoint. The previous experimental-data work remains
preserved on main and is not part of the PR diff.

Next action is human review of PR #7. Keep it open without merge. Do not integrate
these algorithms into a criterion until that separate phase is authorised. Phase 2 must separately review method-specific
integration, effective-algorithm metadata and dependency-scoped compatibility.
The following dataset checkpoint is a retained record of completed earlier work.

## Previous dataset workflow checkpoint

Updated 19 October 2026. Branch `feat/dataset-eligibility`, based on `022b6c0`.
PR #5 was merged into main before this session. The recovered JSON/run-out
implementation is preserved. No uncommitted changes existed at session start.

## Current objective and actual status

The revised dataset importer, method preflight, safe batch skips and observation
subset reporting are implemented. Draft PR [#6](https://github.com/andreachiocca/multiaxial-fatigue/pull/6) is open without merge. JSON history, formulations and family labels
are preserved. The remote branch exists; its first importer milestone
is `dfb514da82bd2792dd1d4da86fc0bb9dc9891e79`. Direct Git push has no credentials;
publication uses the GitHub connector. Local milestone history is retained.

- The tested local migration used 12 revised workbooks plus unchanged Al7075_T6, absent from
  the revised collection. The user explicitly approved publication on 19 October 2026; the revised collection is now installed locally for publication on the same PR. Four previous active files remain byte-identical in
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
using `tools/audit_dataset_migration.py`; the detailed structured audit was
generated locally and can be regenerated from the supplied source files. All 56 shared 42CrMo4_QT and 44 AISI316L
observations retain the supplied stresses. AISI316L properties changed.

Script 0 with n1=3, n2=6, grid=7, refine=2 explicitly generated/reused all 15
method calibrations on revised 42CrMo4_QT under `/tmp/wg43-new-calibrations`.
Script 3 assessed all 15 base methods plus FS_ext and skipped 48 unsupported
pairs in the selected four-material batch. BP/SWT common life comparison used
45 failure observations per method. Eleven run-outs per method remain in
individual outputs with undefined conventional errors. These are software and
regression checks, not independent scientific validation or final calibration.
Temporary example records are not installed as default production calibrations.

The exact published implementation `904c61994e1bb10e5808ac3dd73f99ac794b53b7`
was checked in `/tmp/wg43-public-check`. The suite passed with 58 discovered
checks, 55 executed successfully and 3 full-collection tests skipped because the
withheld workbooks were absent. Ruff, documentation links and catalogue passed.
GitHub Actions succeeded for both push run 39235075215 and PR run 39235140578.
The archived-input end-to-end runner completed 60 combinations and 4,290 rows
(3,646 failures, 644 run-outs); four GSA/LIU2021 combinations on Al/Ti were
explicitly skipped because the steel empirical estimate is unsupported there.
This runner checks execution, counts and recomputed errors. The frozen numerical
fixtures separately check unchanged coefficients and method results; a new exact
full-table comparison against main was not performed this session.
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

The previous raw-workbook publication block was resolved by the user's explicit
"si autorizzo" on 19 October 2026, answering the request to publish all twelve
workbooks, raw observations and embedded content in the public repository.
The same PR #6 is used without merge. The supplied ZIP was installed with
`tools/install_revised_dataset.py --apply`; the detailed migration audit and
eligibility snapshots are regenerated. Original workbook bytes are preserved.
The complete pre-publication recovery history remains at local branch
`recovery/revised-dataset-local-20261019` (`4111686`).

Automatic review accepted workbook publication under this approval but rejected
the additional detailed audit of source-property data. That optional JSON export
is excluded from the publication; its generator remains available. Do not publish
that extra report without separate approval. This does not block publishing the
explicitly authorised twelve workbooks.

The fresh 58-test run passed without skips after installation of the authorised
collection. Ruff, documentation links, the method catalogue and diff checks
passed. The eligibility snapshot was regenerated. Commit
`52b061b87d351be310d4e10127c085a5c985b24b` publishes the twelve workbooks on PR #6.
Every published workbook was compared byte for byte with `New_Exp_data/` in the
supplied ZIP. The public migration excludes only the additional detailed
source-property audit. Historical workbooks, JSON records and reference results
remain preserved. GitHub CI passed for the data commit on both the push
(run 39237587054) and PR (run 39237595131) workflows, with the complete revised
collection available.

Current publication is complete and verified. PR #6 remains open without merge.
Next action is human review of PR #6; no further dataset publication step is pending. Future scientific
work should address the source identity and mixed-fatigue-strength restrictions
above before interpreting affected method/material comparisons. No repeated
implementation or further permission for the twelve workbooks is required.
Resume from here, not the historical audit.

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
