"""Compatibility shim for `multifat.cli.compare` (also installed as `multifat-compare`).

Run from the repository root: data and output paths are relative to it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from multifat.cli.compare import main  # noqa: E402

if __name__ == "__main__":
    main()
