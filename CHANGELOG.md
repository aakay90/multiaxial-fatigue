# Changelog

All notable changes to this project. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project has no tagged release yet.
Finding IDs (F, U, P, N) refer to the audit ledgers kept with the carry-forward review.

## [Unreleased] (carry-forward of October 2026)

**Licence changed to MIT** (copyright Andrea Chiocca, Michele Sgamma and Tommaso Grossi), superseding
GPL-3.0-or-later. Incorporated third-party code is limited to permissive licences; the earlier rule that
GPL code is not ported still applies.

Branch `dev/tg-developments`, based on `main` at `e70a8af` (15 October 2026). Every method was
checked against its original publication; changes to numerical outputs are listed under
**Changed numerically** and were checked with the regression snapshot before each commit.

### Packaging and tooling

- The package is `multifat` in a `src/` layout with a `pyproject.toml` (hatchling) and a `uv.lock`;
  the requirements files are gone. Console scripts `multifat-calibrate`, `multifat-run`,
  `multifat-compare`, `multifat-pipeline`; the standalone scripts in `scripts/` are thin shims for them.
- Comprehensive User Guide (`docs/user-guide.md`) covering pipeline execution,
  single-step CLI tools, experimental workbook preparation, Python API recipes,
  and troubleshooting.
- All Python code is black-formatted (line length 100); the one-off reformat is listed in
  `.git-blame-ignore-revs`. CI runs ruff, black, the doc generators, the documentation check and the
  tests on Python 3.10-3.13 (and Windows on 3.12).
- `tools/regression_snapshot.py` runs every model on every workbook plus calibration and comparison
  and hashes all outputs, to prove a change output-identical.
- Batched plane evaluation and a per-calibration plane cache (bit-identical outputs): a full
  snapshot dropped from about 21 to about 4 minutes before the calibration moved to all planes.

### Survival probability (issue #16)

- `--survival-probability P_s` on `multifat-run` and `multifat-pipeline` (0.5 <= P_s < 1, default 0.5
  = median, unchanged results): the master curve is shifted by z = Phi^-1(P_s) standard deviations of
  the ln DP residuals (`multifat.eval.fitting.stdnum_for_survival`). Every result CSV ends with a
  `Survival_probability` column, the sidecar records it, and `multifat-compare` refuses to mix
  probabilities. Native life laws and fatigue-limit indices are not shifted.

### Load-equivalent error (issue #37)

- Result CSVs gain `Error_load` = ln(1/s*), the log of the factor on the whole load at which the
  method predicts the observed life (master curve or native law; failures only; not TVEIT2025).
  It does not depend on the S-N slope (Error_ln = k d e_L) nor on the degree d of the DP
  (Error_log10_dp = -d e_L / ln 10), so it is the recommended cross-method ranking metric.
  `multifat-compare` adds its mean, SD and the fractions within +-10 % and +-20 % of the load
  (`Within_10pct`, `Within_20pct` columns of the statistics tables). Existing columns unchanged.

### Calibration history (issue #15)

- Pipeline calibrations get a persistent `calibration_id` (UTC time + content signature) and are
  archived without overwriting (`--calibration-archive`, default `<results-dir>/calibrations`);
  equivalent reruns keep their id. `--calibration-id` reuses a record; records lacking provenance
  or made with another implementation revision are rejected, other data or procedure versions are
  flagged. The run report gains a `calibration_id` column; sidecars record
  `calibration_procedure` (2). Numerical results unchanged.

### Dataset workflow classification (issue #18)

- `multifat.imp.classification.classify_dataset` assigns each workbook a workflow
  (`fatigue_life`, `fatigue_limit`, `ambiguous`, `out_of_scope`) and each plain observation a role
  (`design`, `assessment`, `censored`, `limit_state`); the pipeline writes
  `<MATERIAL>_classification.json` and routes on it, with the previous routing preserved.
  Run-outs below the reference life of the Summary limits are reported (25CrMo4: all 11).

### README figures

- Header figure: Findley damage on the sphere of plane normals with the critical plane
  (`examples/plot_damage_sphere.py`); gallery item 5: all methods ranked by the RMS of the
  load-equivalent error across the six life datasets (`examples/plot_load_error_ranking.py`, data in
  `examples/data/load_error_ranking.csv`). Both are produced by `examples/generate_gallery.py`.

### FatPy alignment

multifat is expected to merge into FatPy (COST CA23109). This change documents the correspondence
of names and records one distinction FatPy makes; no multifat name was renamed.

- `docs/notation.md` has a *FatPy nomenclature* table. It lists the FatPy key (nomenclature v01)
  of each multifat name that has one, and the units that differ (FatPy gives E in GPa; multifat
  stays in MPa).
- A new optional Summary column, `Axial fatigue limit loading`, records for each source row how
  the axial R = -1 fatigue limit was obtained: `push-pull`, `rotating bending`, `plane bending`
  or `bending`.
  - The value is kept with the `Sigm1` source and reported in the validation summary.
  - It maps the limit onto `fat_lim_ten_m1` or `fat_lim_ben_m1`.
  - Limit values, and so numerical outputs, are unchanged.
- `docs/research/fatpy-nomenclature-v01-feedback.md` lists, for the FatPy coordinator:
  - keys that are missing (run-out flag, torsional ultimate strength, per-component loads,
    method constants);
  - ambiguities and unit inconsistencies;
  - spelling issues.

### Methods

- New criterion `ZHANGYAO`, Zhang & Yao (2011), catalogue N06 (issue #13).
  - Formulation: a nonlinear combination of the shear amplitude $C_a$ and the Goodman-corrected
    normal stress on the maximum-$C_a$ plane.
  - Verification: 50 of the 66 fatigue limits of Tables 3–8 within 0.3 points.
  - Finding: the maximum-$C_a$ plane rule is ill-conditioned for this criterion, so results in
    out-of-phase loading depend on the tie rule.
  - Guide: `docs/method-guides/ZHANGYAO.md`.
- New criterion `WANG2022`, Wang et al. (2022), catalogue N05 (issue #13).
  - Formulation: the equivalent shear stress on the maximum-$C_a$ plane, with life from the
    torsional S–N curve; its master curve is fitted on the torsion failures.
  - Verification: the predicted lives of Tables 4–5 are reproduced within 1 %.
  - Finding: Eq. (18) as printed makes a tensile mean stress beneficial. By maintainer decision,
    loading with a mean normal stress on the critical plane is out of scope.
  - Guide: `docs/method-guides/WANG2022.md`.
- The native-life load error (`Error_load`) is NaN, instead of a failed model, when a trial load
  leaves the model's declared scope (`LoadingScopeError`), as the master-curve search already
  does.
- New criterion `LIUMAHADEVAN`, Liu & Mahadevan (2005), catalogue N16 (issue #13).
  - Formulation: normal, shear and hydrostatic amplitudes on the plane at a material angle from
    the maximum normal stress amplitude plane, with a normal mean-stress factor. Its native life
    law (Eq. 23) uses the tension and torsion Basquin curves.
  - Maintainer decisions: the worst plane on the $\alpha$-cone in 3D, the rss shear amplitude and
    the native life.
  - Verification: Eq. (19) and both reversed limits are exact (for $t_{-1}/f_{-1} \ge 0.5$). The
    published Figs. 2–5 are reproduced only in part (strict xfails, unresolved).
  - Guide: `docs/method-guides/LIUMAHADEVAN.md`.
- New criterion `SSF`, stress scale factor of Anes et al. (2014), catalogue N24 (issue #13).
  - Formulation: an equivalent shear stress with an ssf surface depending on the axial stress
    and the amplitude ratio, evaluated along the cycle; life on the pure-shear S–N curve.
  - By maintainer decision only the published 42CrMo4 surface is available
    (`Calibrations/42CrMo4_Reis/SSF_published.json`). On that workbook the results are in-sample.
  - Verification: Tables 5–8 reproduced from the Table 4 trend lines (two misprinted cells), and
    Eq. (31) within 0.06 of Table 9.
  - Guide: `docs/method-guides/SSF.md`.
- `--constants` accepts a published-constants record (`published_constants`, `material_id`,
  `reference`): constants printed in a paper, not a calibration of the data.
- New criterion `MMP`, Manson–McKnight–Papuga, Papuga & Fojtík (2017), catalogue G05 (issue #13).
  - Formulation: a von Mises-type equivalent amplitude and mean with weighted shear terms,
    combined by a Walker correction with the mean-stress factor $\beta_P$ (variant MMP_WP).
  - Verification: all 24 load cases of Table 11 within 0.1 point of the fatigue index error.
  - By maintainer decision, missing $f_0$ and $t_0$ are estimated (as for `PCR` and `MMMH`).
  - Guide: `docs/method-guides/MMP.md`.
- New criterion `KUJAWSKI2021`, Kujawski (2021) mSWT, catalogue N26 (issue #13).
  - Formulation: the SWT product with the maximum stress augmented by $|\sigma_m|/3$ when the
    mean stress is negative (Eq. 11b), applied on the planes of the SWT critical-plane extension
    (maintainer decision; the paper is uniaxial).
  - Verification: closed forms of Eqs. (11a)–(13b) and identity with `SWT` without a
    compressive normal mean; the paper validates on figures only.
  - Guide: `docs/method-guides/KUJAWSKI2021.md`.
- New criterion `GAM`, Gonçalves, Araújo & Mamiya (2005), catalogue N08 (issue #13). It is an
  endurance criterion for hard metals.
  - Formulation: the prismatic-hull deviatoric amplitude plus the maximum principal stress over the
    cycle, Eq. (11); the constants come from $f_{-1}$ and $t_{-1}$.
  - Verification: Tables 1–4 reproduce their 14 in-phase rows. The 27 out-of-phase rows of the
    tables used a phase-free peak principal stress, contrary to Eq. (11); they are strict xfails.
  - Guide: `docs/method-guides/GAM.md`.
- New criterion `NINIC`, the Ninić (2006) Damage Function, catalogue N11 (issue #13).
  - Formulation: a quadratic combination of $\tau_a/T_e$ and $\sigma_{n,\max}/S_e$, maximised
    over all planes in three dimensions.
  - Verification against the tables: 29 of 32 full-search rows of Tables 2–4 within 0.08 points,
    and Table 5 within 0.6 points.
  - Printed planes that are not the maximum of $D$, and load misprints, are strict xfails.
  - Finding: Eq. (4) for $k$ calibrates the uniaxial limit only for $S_e/T_e \ge \sqrt2$, and a
    warning is issued below that ratio.
  - Guide: `docs/method-guides/NINIC.md`.
- New criterion `GOLOS`, the Golos, Dębski & Dębski (2014) modified Gough limit curve, catalogue
  N13 (issue #13).
  - Scope: the curve is defined for in-phase, fully reversed bending–torsion only. A new
    `LoadingScopeError` makes the pipeline report such a model as `skipped` (eligibility
    `out_of_scope`) instead of `failed` when a case lies outside the scope.
  - Finding: the text's coefficients for $\kappa = 2$ contradict Eq. (30).
  - Guide: `docs/method-guides/GOLOS.md`.
- New criterion `MWHS`, the Wu, Li, Fang & Song (2017) modified Wu–Hu–Song strain parameter,
  catalogue N28 (issue #13).
  - Formulation: Eq. (19), with the longest-chord shear range.
  - Verification: Fig. 14 is reproduced, except the normal term at 90°.
  - Calibration: as in the source, the master curve is fitted on the fully reversed pure torsion
    failures. A model now declares this with `design_loading = "torsion"`, which is read through
    `extract_pure_torsion`. A workbook without such tests skips the model (`DesignSetError`).
  - Guide: `docs/method-guides/MWHS.md`.
- New criterion `LIU2025`, Liu, Xie & Hao (2025), a new catalogue record N58 from a
  maintainer-supplied paper (issue #13).
  - Formulation: a von Mises-like combination of the corrected plane amplitudes on the maximum
    shear plane, with Gerber and Serensen mean-stress corrections.
  - Verification: Fig. 3 is reproduced except two points.
  - Guide: `docs/method-guides/LIU2025.md`.
- Paper-reproduction tests for every registered method in `tests/methods/`, with the transcribed
  tables in `tests/data/papers/` (DOI, table, page). Confirmed paper misprints are strict `xfail`s
  with the reason (e.g. Papadopoulos 1997 Table 1 rows computed with sin δ, P1).
- Restored: SWTD, OTT, DANGVAN (Böhme et al. 2026 Eq. 3 form). ZHU_EDP is a kernel of Eqs. (19)-(23)
  and stays disabled (needs measured F_NP and ΔW0); CARSPA stays disabled.
- New registered criteria: CROSSLAND (N01), SINES (N02), PAPADOPOULOS 2001 (N03), MWCM (N04), VHN
  (N20), PBP (N37), PCR and PI (G01, G02), MDC (G06), MMMH (G07, endurance-limit Haigh line), COIN
  LiWI (G08), VSE (G15), EK (G16), MMCCM (G22), MOREL (G23), RFB (G41).
- Unregistered point kernels with their own tests: Flacelière-Morel (G24), Banvillet
  (G26, including the solid-bar tension-torsion closed form), Papadopoulos-Panoskaltsis (G29),
  Berto-Lazzarin SED (G30), Doudard-Hild-Calloch (N34). The catalogue records what each one needs
  before registration; G35 stays a specification.
- `optional_params` declares every constant a model reads with `params.get`; a missing required
  constant raises `MissingParamsError`. Critical-plane methods declare their out-of-phase shear rule
  (`np_shear_rule`) and can opt out of the `_ext` variant.
- Native life laws: MDC, MMCCM and MOREL export `Nf_native` and `Error_log10_native` next to the
  fitted universal curve.

### Experimental-data pipeline

- `multifat-pipeline <workbook> | --material NAME | --all [--jobs N]`: validates a workbook, calibrates
  the constants it lacks (sidecar JSON, never written into the workbook), runs every model and
  variant, compares, and reports skipped models with the reason. Outputs in `Results/current/`.
- Workbook contract in `src/multifat/imp/schema.py`, documented in the generated
  `docs/workbook-format.md`; contract violations raise `WorkbookError` with a validation report.
- Constants the pipeline supplies: Basquin curves fitted on the R = -1 tension and torsion tests
  (accepted only with at least 5 tests, one decade of life and a slope beyond 2 standard errors),
  MMCCM plastic terms from the uniform material law (flagged), k_MGSE from Zhu 2018 Eq. (12), the
  other plane constants by scatter minimisation on all planes.
- Run-outs are imported as censored observations instead of being dropped: evaluated with the
  same constants, exported with `Flag = 2` (recorded cycles as a lower bound, empty errors),
  drawn with arrows in the comparison plots (`--hide-runouts` to omit them), never used in
  calibration, curve fits or statistics. Run-out status also accepts true/false, 1/0 and
  runout/failure.
- The pipeline always writes `<MATERIAL>_calibration.json`, now with a provenance block (workbook
  SHA-256, failure and run-out counts, git commit, versions, numerical settings).
- Robustness: `--constants` takes exactly one workbook; `--material` accepts the full file stem
  and reports an unknown material without a traceback; Excel lock files (`~$*.xlsx`) are ignored;
  a one-workbook run keeps the eligibility matrix of an earlier `--all`; empty specimen or
  frequency cells are empty text; `tools/install_revised_dataset.py --apply` refuses to replace a
  workbook edited after installation unless `--replace-edited`.
- Result CSVs end with the observation identity columns (`Test_status`, `Specimen_id`, `Case_id`,
  `Observation_id`, `Dataset_fingerprint`); `multifat-compare --common-methods` compares methods on
  the failures they all assess; `scripts/3_review_subsets.py` forwards to it.
- `tools/regression_snapshot.py --data-folder DIR` (frozen inputs) and a compare on the base
  snapshot's columns; `multifat-calibrate --data-folder`.
- `Experimental_Data/PROVENANCE.md` traces every workbook row and constant to its source, with the
  open questions for the data owners.
- Notes written into outputs were reworded during the refactor (`constants_source.note` in
  `<MATERIAL>_calibration.json`, the run report, `<MATERIAL>_validation.txt` and the eligibility
  notes): the text changed, the values it describes did not (wording only, checked against the
  pre-refactor baseline).
- Calibration records one status per material, with its reason: `calibrated`, `not_applicable` (no
  plain failures: fatigue-limit or notched-only set), `infeasible` (no finite objective) or `error`.
  It is written to `<MATERIAL>_calibration.json` (`status`, `reason`), printed by
  `multifat-calibrate` as a summary table, and copied to `calibration_status` in the eligibility
  matrix and to `Comparison/calibration_status.csv`. The batch is isolated per material instead of
  stopping at the first failure; an infeasible fit names the block, the parameter and a diagnostic
  measured only when it fails, and the exit code is 1 when any material is `infeasible` or `error`.
  A material whose calibration failed keeps running on the constant's default, and the run report
  says `ok (default constant)` with the block and the default value; models skipped for that
  constant carry the same pointer in their reason. No fitted number, table or figure changes
  (`1_Ti6Al4V` keeps the constants it had); block isolation (`partial`) is deferred.

### Upstream sync (PRs #5-#9, up to ab0e828)

Merged on 19 October 2026 (PRs #5-#7, up to 71eaac3, merge commit a3c1d2e) and 20 October 2026
(PRs #8-#9, up to ab0e828, merge commit b8c84c9); upstream modules, originally developed for the legacy `fatigue/`
layout, were ported to `multifat`, each port naming its upstream commit.

- Data: the revised October 2026 collection (twelve numbered workbooks, `Al7075_T6.xlsx`, archives of
  the previous inputs) and the `Calibrations/` records, as supplied.
- Ported: revised workbook import, material IDs without ordering prefix, relative phases, exclusion of
  rows with unknown loading, identity and stress-ratio checks, optional E and nu (dfb514d, 904c619);
  observation identities, dataset fingerprint and common-subset comparison (`--common-methods`,
  904c619); the eligibility matrix (904c619, as pipeline output); run-out plot details (7a87256); the
  harmonic MCC/MCE shear amplitudes with their tests, unused by the criteria (88229e9, 2a17791); the
  dataset install and audit tools (904c619).
- PRs #8-#9: the isolated harmonic Findley damage evaluation `evaluate_findley` with MCC or MCE
  amplitude on the supplied planes (176ce53, 50dabaf; unregistered, nothing in production imports it),
  and the choice of the Findley shear amplitude in the k_FI calibration (36ff0a1, 0105b69):
  `multifat-calibrate --shear-amplitude-algorithm {method_default, mce_harmonic, rss, mcc_harmonic}`.
  The default and every production result are unchanged; MCC is the `longest_chord` plane rule through
  the established refined search, checked against `evaluate_findley`. The option is not exposed by
  `multifat-pipeline`, and `--constants` rejects a record whose Findley amplitude is not MCE (production
  Findley evaluates MCE). Docs: `docs/shear-amplitude.md`, `docs/calibration-workflow.md`.
- Used as inputs: the `Calibrations/` records through `multifat-pipeline --constants` (dc4fe6d); the
  failure-only `failure_fingerprint` in the calibration sidecar (our hash, not comparable with the
  records' `input_fingerprint`); a record made on a different number of failures is flagged.
- Not ported, by design: the versioned calibration store and record selection, with its method-scoped
  Findley compatibility and fingerprints (the pipeline calibrates in one run and records provenance), the `output_quantity` contract and `direct_life`
  (native lives are exported as `Nf_native`), `tools/migrate_calibrations.py` (the importer reads
  legacy coefficients directly) and `tools/run_tests.py` (pytest). His unittest suites are ported
  where the feature is.

### Fatigue-limit datasets

- A workbook whose plain rows are all limit states (run-outs at the endurance basis) with both R = -1
  fatigue limits is assessed by the fatigue index error of every model (Boehme & Papuga 2024,
  Eqs. 8-9), FI = DP / DP(axial R = -1 limit) - 1, with missing plane constants set so that the axial
  and torsional limits give the same DP (`eval/endurance.py`, outputs in `FatigueLimit/`). FI_load
  = 1/s - 1 (s: load factor at which DP reaches the axial reference) is the stress-scaled index
  for every damage parameter (d063).

### Changed numerically

- **TVEIT2025: end of the block integration** (issue #NN, approved by the maintainer). The
  stopping rule compared only two consecutive blocks, so during a slow shakedown it stopped while
  the damage per block was still decaying to zero and extrapolated 9e7 to 2.4e9 cycles instead of
  an infinite life. Now a block without any damage increment is a shakedown (infinite life), and
  a cyclic steady state is accepted from block 400 on only when the back-stress has no net drift
  over 200 blocks and the mean damage per block is stable (`tveit2025.py` docstring). The rule
  reproduces 16 of 16 histories integrated to 50,000 blocks without a stopping rule
  (`tests/test_tveit2025_end_rule.py`). With the stage-1 constants the failures predicted
  infinite go from 3 to 18 (42CrMo4_QT), 2 to 14 (Al7075_T6) and 2 to 26 (Ti6Al4V_Berto);
  Ti6Al4V does not change; other lives move by less than 1 %. Error_load changes by at most
  0.006. New settings defaults: `min_blocks_TVEIT` 400, `max_blocks_TVEIT` 60000,
  `tol_alpha_TVEIT` 0.01 (net drift over 200 blocks, relative to the path length),
  `tol_damage_TVEIT` 0.001 (mean damage per block between two windows); the four
  `TVEIT2025_stage1.json` files carry them.
- **TVEIT2025: within-cycle failure time.** A failure inside a block is placed in the increment
  that crosses D = 1: (i - 1 + f)/(npts - 1) of the cycle, where the code counted one increment
  more ((i + f)/(npts - 1)). Lives shorten by at most 1/(npts - 1) = 0.001 cycle
  (`docs/audit-checkpoint.md`).
- `k_MGSE` no longer depends on the model selection: Zhu (2018) Eq. (12) on the Basquin fits is used
  whenever those fits are identifiable, also in a run that selects MGSE_ZHU without MDC or MMCCM
  (previously scatter minimisation, e.g. 1.239 instead of 0.988 on Al7075_T6). Full runs are unchanged.
- L_LI search interval widened from [0, 5] to [0, 20]: the minimum lay outside it on 42CrMo4_QT
  (L_LI 5.0 -> 7.07, life-scatter STD 1.153 -> 0.942) and 42CrMo4_Reis (5.0 -> 5.36, 0.368 -> 0.341).
  Interior L_LI values move by at most 3e-6 relative (grid refinement on the wider interval).
  A scatter minimum on an upper bound that only limits the search (all but a_MSWT = 1) is no longer
  used: it is recorded as `unidentified`, and models requiring it are skipped with that reason. On
  Ti6Al4V the wider L_LI interval makes the calibration feasible (L_LI = 11.5) but k_FI and k_FS end
  at 3, so FIN and FS stay skipped, now with that reason; LI, MGSE_ZHU and MSWT use the calibrated
  constants instead of their defaults. A model whose master curve gives no life predictions (slope
  `b >= 0` or `k = -1/b > 15`) is noted in the run report.
- Design flags of calibrated plane constants: the tension and torsion tests of the scatter
  objective behind a pipeline-calibrated `k_FI`, `k_FS`, `L_LI`, `k_MGSE` or `a_MSWT`, and the
  Basquin tests behind a `k_MGSE` from Zhu (2018) Eq. (12), are now `Flag = 0` for the models that
  adopt the constant; they were `Flag = 1` assessment rows, so the assessment statistics included
  the tests that fitted the constant. On the five life datasets 410 rows of FIN, FS, LI, MGSE_ZHU,
  MSWT and their `_ext` change flag; constants, master curves and predicted lives are unchanged
  (differences at most 6.7e-14 relative, from the design-row code path). `--constants` with a
  sidecar of this pipeline keeps its design tests when the `failure_fingerprint` matches.
- F1: result CSVs are written as UTF-8 (only text fields changed; SWT results now enter the
  comparison on Windows).
- F2: the critical-plane search refines the grid maximum (grid + analytical seeds + local
  refinement); the 522-plane grid under-estimated the continuous maximum by up to 1.2 %. F10:
  refinement also starts from tied maxima in different basins (workbook impact at most 2.2e-8).
- F3: the out-of-phase shear range follows each source: longest chord for FS, MKBM, LI and LIU2021,
  RSS for the other critical-plane methods.
- F5-F7, F9: SWTD, OTT and DANGVAN equations corrected before they were re-enabled.
- U2: MSWT uses the printed (1 - a)/2 shear weight of Jiang (2000); the workbook a_MSWT values were
  converted (a' = a/(2 - a)), so lives are unchanged and the damage parameter is rescaled.
- F4: calibration evaluates all planes and returns the smallest point of a flat minimum.
- Workbooks: 42CrMo4 `Plain_multiaxial_9` is proportional (phase 90° -> 0°, N1); AISI316L
  non-proportional rows get their 90° phase (N6), E = 193 GPa and ν = 0.3 from the literature (N7),
  and the 8 Janssens Table 4 points missing from the workbook (N8). Each changed cell carries an
  Excel comment with the source and the old value.
- New data (upstream 71eaac3): every result changes with the revised collection. 42CrMo4_QT and
  Ti6Al4V are the one-batch revised files; the Anes/Reis and Berto rows are the new workbooks
  `14_42CrMo4_Reis.xlsx` (with the printed strain-life constants) and `15_Ti6Al4V_Berto.xlsx` (d055).
  In the revised AISI316L, N6 and N8 are re-applied, Janssens E/nu restored (Braun's 219 GPa / 0.29 are
  XRD constants) and the Braun R = 0 mean stresses restored (d056); nu = 0.3 for four steels (d059).
  The plane constants of every material are calibrated, as the revised workbooks carry none.
- Revised-format import: an empty or `Null` stress excludes the row instead of reading 0; phases are
  relative to the axial phase (34Cr4 has nonzero axial phases); AISI316L's Sigm1, averaged over two
  stress ratios, is not used.
- Without E or nu, the critical-plane evaluator and the plane seeds skip the undefined strain
  tensors (finite inputs unchanged).

### Notation and documentation

- `docs/notation.md` is the symbol table behind the package vocabulary: paper symbol, Python name,
  workbook key and unit for every concept, plus the rule that a function implementing one published
  equation uses that equation's symbols. The code follows it end to end: `f_m1`/`t_m1` for the
  reversed limits, `sigma_z0`/`sigma_z1` for the load-step normal stress, `d_gam`/`d_tau` for the
  ranges, `DP`/`metric` for the plane scalars, `R_list`/`normals` for the plane frames,
  `case`/`refs`/`bounds` in the evaluation layer and `workbook`/`material`/`data`/`params` in the
  command line. The closing pass restored the coefficient sets of the 2026 Böhme-Papuga paper
  (`a_BP`..`d_BP`, `a_CAIM`..`d_CAIM`, `kappa_sq`), the MMMH surface stresses (`sigma_x`, `sigma_y`,
  `tau_xy`, `sigma_z`, `k_a`, `M`) and the evaluation-layer names (`block`, `case`, `key`, `target`,
  `df`, `material`, `amplitude`, `Nf`, `DP`, `eps_e`/`eps_p`). No algorithm, constant, public method
  name, registry key, CLI option or workbook key changed: `regression_snapshot.py` compares
  identical to the previous commit (1708 output files and 410 logs, no differences) and the
  pre-existing tests still pass.
- Python source, its docstrings and the tables generated from it spell the name `Boehme`;
  hand-written documentation keeps the author's spelling `Böhme`, including the method catalogue
  (`docs/catalogue/methods.json`) and everything generated from it, `docs/bibliography.md` and the
  README. The guard rejects `Böhme` in `src/**/*.py` and in `docs/workbook-format.md`.
- `tests/test_notation.py` guards the vocabulary: retired synonyms (read from `docs/notation.md`),
  `_old = _new` private aliases, module docstrings that do not open on their first line, string
  statements left outside the docstring slot, an override that renames the parameters of the method
  it overrides (a coefficient set may only take the subscript of its own criterion, `a_BP`..`d_BP`
  to `a_CAIM`..`d_CAIM`), the banned docstring phrases of `docs/adding-methods.md`, and every
  parameter of a public function or method in `eval/` and `models/` that appears neither in the
  table nor in `tests/data/notation_allow.txt`. That file holds exactly the names outside the
  table, one group per reason, so an entry whose name disappears fails like a missing one. The
  docstring rules themselves are in `docs/adding-methods.md`.
- The review found one logic difference, `pipeline.py` treating an empty constant mapping as absent
  and reloading it from the workbook: it is kept (`is None`) and pinned by
  `test_empty_data_mapping_is_used_as_given`.
- Method guides (issue #32), `docs/method-guides/`: a template, an index with the conventions
  shared by every method (load history, plane search and shear-amplitude rules, master curve,
  calibration of plane constants) and one guide each for FIN, FS, SWT, MATAKE, MCD, MWCM,
  CROSSLAND, SINES, DANGVAN and PAPADOPOULOS: original formulation in LaTeX, repository
  implementation and its departures, constants, original versus repository calibration, an
  executable worked example checked against a hand calculation, comparison capabilities and
  verification evidence. `tests/test_method_guides.py` runs every example and compares its printed
  output, checks the section order, the registry names on the command lines and the index, and
  ratchets the `Repository choices:` paragraph of the method-module docstrings (25 modules still
  pending). Module docstrings added or completed for FIN, FS, SWT, MATAKE, MCD, MWCM, CROSSLAND,
  SINES, DANGVAN and PAPADOPOULOS. Documentation only: `regression_snapshot.py` compares identical
  to `5cd5124`.
- Method guides for the strain and energy critical-plane criteria MKBM, VSE, GSE and GSA (issue
  #32). Each guide gives the torsion-to-tension limit ratio that the criterion implies with elastic
  strains, in closed form: about 0.68 for MKBM at $f/S_y = 0.75$, 0.88 or 0.62 for VSE (mode I or
  II), 0.63 for GSE and 0.55 for GSA. The guides also document two properties of the criteria:
  - VSE has no mean-stress effect;
  - GSA lives do not depend on $\sigma_f'$ when strains are elastic and $\tau_f'$ takes its
    default.

  The MKBM, VSE and GSA module docstrings now carry a `Repository choices:` paragraph, so 19
  modules remain pending. Documentation only, no numerical change.

### Repository

- Licensed under the GNU General Public License v3.0 or later (`LICENSE`, `pyproject.toml`);
  `CITATION.cff` gives the software citation.
- README rewritten for newcomers (quick start through the pipeline, coverage, how to add a method
  or a workbook); CONTRIBUTING covers the snapshot gate and workbook edits.
- The 88 pre-audit result CSVs moved to `Results/archive/pre-audit/`; `multifat-run` writes to
  `Results/current/` by default.
- Removed the 7 October audit checkpoint and the 15 October cleanup audit, superseded by this
  changelog; they remain in the git history. The remaining maintenance items they listed (live
  Issues, repository description and topics, branch protection) need repository-admin access.
