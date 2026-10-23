"""Compatibility shim for upstream Script 3 (A. Chiocca): matched-observation review.

Forwards its arguments to `multifat.cli.compare` (also installed as `multifat-compare`), e.g.

    python scripts/3_review_subsets.py --results_dir Results/current --out_dir Results/current/Common \
        --common-methods BP SWT --comparison-metric life --flag_filter other

The eligibility matrix of upstream Script 3 is written by `multifat-pipeline --all`
(`Comparison/eligibility_matrix.csv`). Run from the repository root.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from multifat.cli.compare import main  # noqa: E402

if __name__ == "__main__":
    main(sys.argv[1:])
