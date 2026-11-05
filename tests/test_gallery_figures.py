"""README figures: the damage sphere agrees with the production critical-plane search."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.plot_damage_sphere import K_FI, SIGMA_A, TAU_A, findley_on_sphere  # noqa: E402
from multifat.eval.evaluator import best_cp_for_case  # noqa: E402
from multifat.models.cp_methods.fin import Findley  # noqa: E402
from multifat.planes.sampling import build_R_list  # noqa: E402


@pytest.mark.parametrize("phase", [0, 90])
def test_sphere_maximum_matches_the_refined_search(phase):
    shear = np.array([[0.0, TAU_A, 0.0], [TAU_A, 0.0, 0.0], [0.0, 0.0, 0.0]])
    axial = np.diag([SIGMA_A, 0.0, 0.0])
    S_sin, S_cos = (axial + shear, np.zeros((3, 3))) if phase == 0 else (axial, shear)
    _, damage = findley_on_sphere(S_sin, S_cos)
    zero = np.zeros((3, 3))
    best = best_cp_for_case(
        S0=S_sin, E0=zero, S1=-S_sin, E1=zero, R_list=build_R_list(), method=Findley(),
        params={"k_FI": K_FI}, S_sin=S_sin, S_cos=S_cos,
    )  # fmt: skip
    # the 1.5-degree sphere grid reaches the refined maximum to a few parts in ten thousand
    assert damage.max() <= best.ext * (1 + 1e-9)
    assert damage.max() == pytest.approx(best.ext, rel=2e-3)


def test_ranking_data_is_consistent():
    table = pd.read_csv(
        Path(__file__).resolve().parents[1] / "examples" / "data" / "load_error_ranking.csv"
    )
    assert {"Material", "Method", "n", "Error_load_mean", "Error_load_rms"} <= set(table.columns)
    rms2 = table.Error_load_rms**2
    var = table.Error_load_sd**2 * (table.n - 1) / table.n + table.Error_load_mean**2
    assert np.allclose(rms2, var, rtol=1e-4)  # RMS^2 = mean^2 + population variance
    assert not table.Method.str.endswith("_ext").any()
