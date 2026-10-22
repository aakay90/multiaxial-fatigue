# Execution Shims

This directory contains standalone execution shims for the `multifat` command-line interfaces.

While the modern workflow installs console entry points via `uv` or `python -m pip install -e .` (`multifat-pipeline`, `multifat-run`, `multifat-calibrate`, `multifat-compare`), these scripts provide direct invocation paths:

- `0_calibrate_material_params.py`: Calibrate required material parameters (shim for `multifat-calibrate`).
- `1_run_material.py`: Run one material with a chosen criterion (shim for `multifat-run`).
- `2_compare_results.py`: Compare multi-method evaluation results (shim for `multifat-compare`).
- `3_pipeline.py`: Run the full pipeline for a workbook or collection (shim for `multifat-pipeline`).
- `3_review_subsets.py`: Review matched observation subsets (shim for `multifat-compare`).

## Usage

Run any script from the repository root:

```bash
python scripts/3_pipeline.py --material AISI316L
```
