# Historical and current results

The tracked CSV files directly in this directory are historical exports from
before the numerical audit. They preserve development evidence, including
disabled formulations; they are not current validation benchmarks. See the
[method audit](../docs/method-audit.md) before comparing them.

Write fresh outputs to `Results/current/` (ignored by Git), and regenerate all
methods being compared with the same code revision and parameter assumptions.
Keep reproducible published validation cases and their provenance with tests;
do not replace these historical CSVs or commit routine plots and run outputs.

`Results/Comparison/` and `Results/validation/` are also ignored. The optional
material sweep accepts a separate output directory and preserves this archive.
