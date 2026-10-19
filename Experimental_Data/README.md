# Material and experimental inputs

The workbook filename stem identifies the material. `Summary` retains material
identification, article references, static properties and independently supplied
fatigue properties. The `Average` named-cell convention is supported; revised files also use the labelled Average row.
The strength ratio `K` remains a derived workbook quantity; Script 0 does not fit it.
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

The five fitted coefficients `k_FS`, `k_FI`, `L_LI`, `k_MGSE` and `a_MSWT` have
moved to JSON. The retired-model values `alpha_w` and `xi_ZHU` are preserved there
as legacy constants with unverified provenance and units. None is read from the
live workbook. Material fatigue-strength and strain-life properties remain
experimental inputs when independently supplied; they must not be moved merely
because their names resemble fitted coefficients.

[Original workbooks](archive/pre-json-calibration.zip) are preserved byte-for-byte.
Migration changes only the obsolete Summary cells and associated table definitions.
Dataset cells, retained Summary cells and formula caches are preserved. The importer
does not recurse into `archive/`.

For an old-format workbook, run `python tools/migrate_calibrations.py`. It archives
the originals, transfers the cached Average coefficients, fits the existing
failure-only master curves and then removes the obsolete cells. It refuses to
replace an archive containing different originals. The importer warns about old
coefficient columns and ignores their values, so Excel and JSON are never competing
sources. See the [workflow](../docs/calibration-workflow.md) before migration.

The October 2026 active collection contains twelve revised files plus retained
Al7075_T6. The supplied revised workbooks are preserved without editing measured
cells, including their embedded content. The previous repository inputs remain byte-identical in
`archive/pre-dataset-migration/`. Numeric filename prefixes do not form part of
material identity. Unresolved Summary identities and inconsistent fatigue-strength
reference conditions are reported before assessment. See the
[dataset workflow](../docs/dataset-workflow.md) for the current restrictions.
