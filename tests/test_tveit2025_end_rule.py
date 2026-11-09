"""End of the TVEIT2025 block integration: shakedown, cyclic steady state and the failure fraction.

The integration is checked against 50,000-block histories run without any stopping rule
(tests/data/tveit2025_long_histories.csv, stage-1 constants). Every load that shakes down must be
found infinite at the block where the damage increment first vanishes, and every load in a steady
cycle must give the life of the long history. Comparing only two consecutive blocks, the earlier
rule stopped during these shakedowns and returned 9e7 to 2.4e9 cycles.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from multifat.models.invariant_methods.tveit2025 import N_POINTS, tveit2025_life

ROOT = Path(__file__).resolve().parents[1]
HISTORIES = pd.read_csv(ROOT / "tests" / "data" / "tveit2025_long_histories.csv", comment="#")


def _constants(material):
    params = json.loads(
        (ROOT / "Calibrations" / material / "TVEIT2025_stage1.json").read_text(encoding="utf-8")
    )["params"]
    keys = ("Sigm1_TVEIT", "Taum1_TVEIT", "A_TVEIT", "C_TVEIT", "K_TVEIT", "L_TVEIT")
    return [params[k] for k in keys]


def _cycle(loading, R, amplitude):
    S_mean, S_sin = np.zeros((3, 3)), np.zeros((3, 3))
    i, j = (1, 1) if loading == "axial" else (0, 1)
    S_mean[i, j] = S_mean[j, i] = amplitude * (1 + R) / (1 - R)
    S_sin[i, j] = S_sin[j, i] = amplitude
    return S_mean, S_sin, np.zeros((3, 3))


@pytest.mark.parametrize(
    "row",
    list(HISTORIES.itertuples()),
    ids=lambda r: f"{r.material}-{r.loading}-R{r.R:g}-{r.amplitude:g}",
)
def test_long_history_is_reproduced(row):
    life = tveit2025_life(*_cycle(row.loading, row.R, row.amplitude), *_constants(row.material))
    if not math.isnan(row.shakedown_block):
        assert life.termination == "shakedown" and math.isinf(life.Nf)
        # The test needs two blocks; a few blocks of tolerance cover rounding across platforms
        assert abs(life.blocks - max(int(row.shakedown_block), 2)) <= 2
    else:
        expected = 50000 + (1 - row.D_50000) / row.dD_50000
        assert life.termination == "cyclic_steady_state"
        # 2 %: at 50,000 blocks the damage per block of Ti6Al4V at 510 MPa still drifts by 1.4 %
        assert life.Nf == pytest.approx(expected, rel=0.02)


def test_failure_inside_the_first_increment_counts_less_than_one_increment():
    """The life ends inside the increment that crosses D = 1, not one increment later."""
    S_mean, S_sin, S_cos = _cycle("axial", -1.0, 1e5)  # damaging from the first increment on
    life = tveit2025_life(S_mean, S_sin, S_cos, 100.0, 80.0, 0.2, 0.1, 0.1, 50.0)
    assert life.termination == "explicit_failure" and life.blocks == 1
    assert 0.0 < life.Nf < 1.0 / (N_POINTS - 1)
