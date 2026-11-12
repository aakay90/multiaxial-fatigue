"""Build examples/data/42CrMo4_Santus_predictions.csv from pipeline output.

Regenerate after any model or dataset change:

    uv run multifat-pipeline --material 42CrMo4_Santus --models all --no-compare \
        --results-dir <tmp_dir>
    uv run python examples/build_predictions_csv.py <tmp_dir>

Check whether the committed CSV and manifest match the current models and workbook:

    uv run python examples/build_predictions_csv.py --check

Methods without a valid prediction for any case (all-NaN) are dropped.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.homepage_data import (  # noqa: E402
    PREDICTIONS_CSV,
    PREDICTIONS_MATERIAL,
    check_manifest,
    write_manifest,
)

COLUMNS = [
    "Material",
    "Method",
    "Method_family",
    "Loading_type",
    "Nf_exp",
    "Nf_expected",
    "Error_ln",
    "Flag",
    "Specimen_id",
]


def build(results_dir: Path, out_path: Path | None = None) -> Path:
    files = sorted(results_dir.glob("*_42CrMo4_Santus.csv"))
    if not files:
        raise FileNotFoundError(f"no *_42CrMo4_Santus.csv in {results_dir}")
    df = pd.concat(pd.read_csv(f) for f in files)[COLUMNS]
    valid = df.groupby("Method")["Nf_expected"].transform(lambda s: s.notna().any())
    df = df[valid].sort_values(["Method", "Specimen_id"]).reset_index(drop=True)
    out_path = out_path or PREDICTIONS_CSV
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, lineterminator="\n")
    methods = sorted(df["Method"].astype(str).unique())
    write_manifest(out_path, [PREDICTIONS_MATERIAL], methods)
    return out_path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results_dir", type=Path, nargs="?", help="pipeline output directory")
    parser.add_argument("--check", action="store_true", help="check committed CSV and manifest")
    args = parser.parse_args(argv)
    if args.check:
        problems = check_manifest(PREDICTIONS_CSV, (PREDICTIONS_MATERIAL,))
        for problem in problems:
            print(problem)
        if problems:
            raise SystemExit(
                "stale homepage predictions data: rerun examples/build_predictions_csv.py"
            )
        print(f"{PREDICTIONS_CSV.name} is current")
        return
    if args.results_dir is None:
        parser.error("results_dir is required unless --check is passed")
    print(build(args.results_dir))


if __name__ == "__main__":
    main()
