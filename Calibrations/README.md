# Calibration records

Each material directory contains complete JSON records. Script 0 creates a new
record for each successful execution. Records are selected by their declared
UTC creation time and ID, with compatibility checks, instead of file timestamps.

The four initial records transfer the former workbook coefficients without
re-optimising them and reproduce all 15 active methods' master curves. Their
original coefficient-fitting settings are unverified. These records preserve
the previous analysis results and do not establish independent validation.

See the [calibration workflow](../docs/calibration-workflow.md) for the schema,
units, selection rules, provenance and commands. Keep useful new records under
version control, and inspect their provenance before committing them. Routine
plots and analysis exports belong in ignored result directories.

## Use with multifat-pipeline

`multifat-pipeline <workbook> --constants Calibrations/<material>/<id>.json` takes the plane
constants (k_FS, k_FI, L_LI, k_MGSE, a_MSWT) from a record instead of calibrating them; the
record must belong to the workbook's material ID; a record made on a different number of failures is
used but flagged in the sidecar (`constants_source.warning`). Its a_MSWT is in the weighting of the former
workbooks and is converted to the printed one, a' = a/(2 - a). The calibration sidecar records
the file, its SHA-256 and the calibration ID. The pipeline does not write new records here; its
own results go to `<MATERIAL>_calibration.json` in the results folder, which `--constants` also
accepts. The four records belong to the previous collection (material IDs `42CrMo4_QT`,
`AISI316L`, `Al7075_T6`, `Ti6Al4V_andrea_(AXIAL)`); the revised workbooks change the material
inputs, so a record reproduces former constants, not a calibration of the new data.
