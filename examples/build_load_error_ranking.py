"""Build examples/data/load_error_ranking.csv from pipeline output (issue #37).

Per method and material: number, mean, standard deviation and root mean square of the load-equivalent error
Error_load = ln(1/s*) on the assessed failures (Flag = 1), and the fraction within +-20 % of
the load. Regenerate after any model or dataset change:

    uv run multifat-pipeline --material 42CrMo4_QT --material 42CrMo4_Reis --material AISI316L \
        --material Al7075_T6 --material Ti6Al4V --material Ti6Al4V_Berto --material 42CrMo4_FABEST \
        --models all \
        --jobs 4 --results-dir <tmp_dir>
    uv run python examples/build_load_error_ranking.py <tmp_dir>

Check whether the committed CSV and manifest match the current models and workbooks:

    uv run python examples/build_load_error_ranking.py --check

Only base methods are kept (no _ext variants). Methods with fewer than 3 finite errors on a
material are left out for that material.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.homepage_data import (  # noqa: E402
    RANKING_CSV,
    RANKING_MATERIALS,
    check_manifest,
    write_manifest,
)

OUT = RANKING_CSV


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


def write_ranking(results_dir: Path, out_path: Path | None = None) -> tuple[Path, Path]:
    """Build and save the ranking CSV along with its provenance manifest."""
    target = out_path or OUT
    table = build(results_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(target, index=False, float_format="%.6g", lineterminator="\n")
    materials = sorted(table["Material"].astype(str).unique())
    methods = sorted(table["Method"].astype(str).unique())
    manifest = write_manifest(target, materials, methods)
    return target, manifest


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("results_dir", type=Path, nargs="?", help="pipeline output directory")
    parser.add_argument("--check", action="store_true", help="check committed CSV and manifest")
    args = parser.parse_args(argv)
    if args.check:
        problems = check_manifest(OUT, RANKING_MATERIALS)
        for problem in problems:
            print(problem)
        if problems:
            raise SystemExit(
                "stale homepage ranking data: rerun examples/build_load_error_ranking.py"
            )
        print(f"{OUT.name} is current")
        return
    if args.results_dir is None:
        parser.error("results_dir is required unless --check is passed")
    csv_path, manifest_path = write_ranking(args.results_dir)
    table = pd.read_csv(csv_path)
    print(f"{len(table)} rows -> {csv_path} (manifest: {manifest_path.name})")


if __name__ == "__main__":
    main()
