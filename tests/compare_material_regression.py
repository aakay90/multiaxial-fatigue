"""Compare baseline and revised sweeps without modifying reference CSV files.

Run each checkout's tests/run_material_validation.py with separate output folders,
then run this script with those two folders as positional arguments.
"""
from pathlib import Path
import sys

import numpy as np
import pandas as pd


def compare(baseline, revised):
    paths = sorted(Path(baseline).glob("*.csv"))
    if not paths:
        raise ValueError("No baseline result CSV files found")
    failures, runouts = 0, 0
    for path in paths:
        old = pd.read_csv(path)
        new = pd.read_csv(Path(revised) / path.name)
        failed = new.loc[new.Test_status == "failure"].reset_index(drop=True)
        assert len(old) == len(failed), (path.name, "failure count changed")
        for column in old:
            if pd.api.types.is_numeric_dtype(old[column]):
                np.testing.assert_allclose(old[column], failed[column], rtol=0, atol=0,
                                           equal_nan=True, err_msg=f"{path.name}/{column}")
            else:
                pd.testing.assert_series_equal(old[column], failed[column], check_names=False)
        censored = new.loc[new.Test_status == "runout"]
        assert censored[["DP_fit", "Error_ln", "Error_ln_dp", "Error_log10_dp"]].isna().all().all()
        failures += len(failed)
        runouts += len(censored)
    print(f"PASS {len(paths)} runs; {failures} unchanged failure rows; {runouts} run-out rows")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python tests/compare_material_regression.py BASELINE_DIR REVISED_DIR")
    compare(*sys.argv[1:])
