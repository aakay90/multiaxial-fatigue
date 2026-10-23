# Results

Fresh outputs go to `Results/current/`, which Git ignores. `multifat-pipeline` and `multifat-run`
write there by default. Regenerate every method you compare with the same code revision and the same
constants; the run report and calibration JSON next to the CSVs record both.

`archive/pre-audit/` keeps the 88 CSVs that were tracked here before the numerical audit
(October 2026). They include disabled formulations and pre-audit equations, and the current code does
not reproduce them. They are history, not benchmarks. `multifat-compare` reads `Results/`
recursively and drops these rows unless `--include-legacy` is given. See the
[CHANGELOG](../CHANGELOG.md) for what changed since.

`Results/Comparison/` and `Results/validation/` are also ignored. Keep reproducible published
validation cases with the tests (`tests/methods/`), not here.
