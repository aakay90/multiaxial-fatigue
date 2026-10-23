"""Build examples/data/42CrMo4_QT_predictions.csv from pipeline output.

Regenerate after any model or dataset change:

    python scripts/3_pipeline.py --material 6_42CrMo4_QT --models all --no-compare \
        --results-dir <tmp_dir>
    python examples/build_predictions_csv.py <tmp_dir>

Methods without a valid prediction for any case (all-NaN) are dropped.
"""

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.style import DATA_DIR

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
    files = sorted(results_dir.glob("*_42CrMo4_QT.csv"))
    if not files:
        raise FileNotFoundError(f"no *_42CrMo4_QT.csv in {results_dir}")
    df = pd.concat(pd.read_csv(f) for f in files)[COLUMNS]
    valid = df.groupby("Method")["Nf_expected"].transform(lambda s: s.notna().any())
    df = df[valid].sort_values(["Method", "Specimen_id"]).reset_index(drop=True)
    out_path = out_path or DATA_DIR / "42CrMo4_QT_predictions.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    return out_path


if __name__ == "__main__":
    print(build(Path(sys.argv[1])))
