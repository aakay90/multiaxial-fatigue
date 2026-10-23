"""Compatibility shim for `multifat.cli.run` (also installed as `multifat-run`).

Run from the repository root: data and output paths are relative to it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from multifat.cli.run import cli  # noqa: E402

if __name__ == "__main__":
    cli()
