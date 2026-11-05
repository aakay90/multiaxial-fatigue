"""Build examples/data/load_error_ranking.csv from pipeline output (issue #37).

Per method and material: number, mean, standard deviation and root mean square of the load-equivalent error
Error_load = ln(1/s*) on the assessed failures (Flag = 1), and the fraction within +-20 % of
the load. Regenerate after any model or dataset change:

    uv run multifat-pipeline --material 42CrMo4_QT --material 42CrMo4_Reis --material AISI316L \
        --material Al7075_T6 --material Ti6Al4V --material Ti6Al4V_Berto --models all \
        --jobs 4 --results-dir <tmp_dir>
    uv run python examples/build_load_error_ranking.py <tmp_dir>

Only base methods are kept (no _ext variants). Methods with fewer than 3 finite errors on a
material are left out for that material.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.style import DATA_DIR

OUT = DATA_DIR / "load_error_ranking.csv"


def build(results_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(results_dir.glob("*.csv")):
        frame = pd.read_csv(path)
        if "Error_load" not in frame or "Flag" not in frame:
            continue
        method = str(frame["Method"].iloc[0])
        if method.endswith("_ext"):
            continue
        errors = pd.to_numeric(frame.loc[frame["Flag"] == 1, "Error_load"], errors="coerce")
        errors = errors[np.isfinite(errors)].to_numpy()
        if errors.size < 3:
            continue
        rows.append(
            dict(
                Material=str(frame["Material"].iloc[0]),
                Method=method,
                n=int(errors.size),
                Error_load_mean=float(errors.mean()),
                Error_load_sd=float(errors.std(ddof=1)),
                # bias and scatter together: on a torsion-only assessment set every method has
                # the same SD (one tension/torsion ratio each), only its bias differs
                Error_load_rms=float(np.sqrt(np.mean(errors**2))),
                Within_20pct=float(np.mean(np.abs(np.expm1(errors)) <= 0.2)),
            )
        )
    return pd.DataFrame(rows).sort_values(["Material", "Method"])


if __name__ == "__main__":
    table = build(Path(sys.argv[1]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT, index=False, float_format="%.6g")
    print(f"{len(table)} rows -> {OUT}")
