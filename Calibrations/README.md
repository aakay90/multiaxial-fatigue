# Calibration records

Each material directory contains complete JSON records. Script 0 creates a new
record for each successful execution. Records are selected by their declared
UTC creation time and ID, with compatibility checks, rather than file timestamps.

The four initial records transfer the former workbook coefficients without
re-optimising them and reproduce all 15 active methods' master curves. Their
original coefficient-fitting settings are unverified. These records preserve
the previous analysis results and do not establish independent validation.

See the [calibration workflow](../docs/calibration-workflow.md) for the schema,
units, selection rules, provenance and commands. Keep useful new records under
version control, and inspect their provenance before committing them. Routine
plots and analysis exports belong in ignored result directories.
