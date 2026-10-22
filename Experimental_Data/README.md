# Material and experimental inputs

The workbook filename stem identifies the material. `Summary` retains material
identification, article references, static properties and independently supplied
fatigue properties. The `Average` named-cell convention is supported; revised files also use the labelled Average row.
The strength ratio `K` remains a derived workbook quantity; the pipeline does not fit it.
Missing properties remain unavailable. Existing empirical fatigue-property estimates are restricted to supported steel inputs and reported explicitly.

`Dataset` retains all original measurements, loading conditions, specimen IDs,
references and geometry information. Current analyses use plain specimens only.
The `Run out (Yes/No)` column determines observation status independently of the
recorded cycle count. `No`, `false`, `0` and `failure` identify a failed specimen;
`Yes`, `true`, `1` and `runout` identify a run-out. Matching ignores case and accepts
`run-out` or `failed`. Other or missing values are unknown, not assumed failures.

The legacy column `Number of cycles to failure` is retained for compatibility.
For a run-out, it contains the number of cycles completed before stopping and
therefore a lower bound on fatigue life. Run-outs are imported with their loading
tensors and specimen metadata, excluded from coefficient optimisation and curve
fitting, and retained for qualitative plots. Unknown statuses are retained in
the imported data but excluded from calibration and analysis exports. Invalid
cycle counts or non-finite loading inputs are reported in exclusion metadata.
Legacy Null stress components retain their inactive-component convention. Revised missing stress components are flagged as unavailable loading information.

The five fitted coefficients `k_FS`, `k_FI`, `L_LI`, `k_MGSE` and `a_MSWT` are not in
the revised workbooks: `multifat-pipeline` calibrates them, or reads them from a
`Calibrations/` record with `--constants`. The retired-model values `alpha_w` and
`xi_ZHU` are preserved in those records as legacy constants with unverified provenance
and units. A legacy workbook that still has such columns is read as before (the values
are used as supplied constants). Material fatigue-strength and strain-life properties remain
experimental inputs when independently supplied; they must not be moved merely
because their names resemble fitted coefficients.

[Original workbooks](archive/pre-json-calibration.zip) are preserved byte-for-byte.
Migration changes only the obsolete Summary cells and associated table definitions.
Dataset cells, retained Summary cells and formula caches are preserved. The importer
does not recurse into `archive/`.

Upstream migrated the old-format workbooks with `tools/migrate_calibrations.py` (archive,
transfer of the cached Average coefficients into `Calibrations/`, removal of the obsolete
cells); see the [upstream workflow](../docs/calibration-workflow.md). That tool is not
needed here, since the importer reads legacy coefficients directly.

The October 2026 active collection contains twelve revised files plus retained
Al7075_T6. The supplied revised workbooks are preserved without editing measured
cells, including their embedded content. The previous repository inputs remain byte-identical in
`archive/pre-dataset-migration/`. Numeric filename prefixes do not form part of
material identity. Unresolved Summary identities and inconsistent fatigue-strength
reference conditions are reported before assessment. See the
[dataset workflow](../docs/dataset-workflow.md) for the current restrictions.

Two batch workbooks were added after the merge, `14_42CrMo4_Reis.xlsx` and
`15_Ti6Al4V_Berto.xlsx`, and some cells of the revised files were corrected; every change
is listed in [PROVENANCE.md](PROVENANCE.md) and carries an Excel comment.
