"""Issue #16: survival probability of the fitted master curve DP = A N^b."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from multifat.cli.pipeline import run_workbook
from multifat.eval.fitting import fit_power_law_with_survival_std, stdnum_for_survival
from workbook_factory import write_workbook


@pytest.mark.parametrize(
    "P_s,z", [(0.5, 0.0), (0.9, 1.2815516), (0.95, 1.6448536), (0.9772499, 2.0), (0.99, 2.3263479)]
)
def test_survival_probability_is_a_standard_normal_quantile(P_s, z):
    assert stdnum_for_survival(P_s) == pytest.approx(z, abs=1e-6)


@pytest.mark.parametrize("P_s", [0.4, 1.0, float("nan"), -0.1])
def test_invalid_survival_probability_is_rejected(P_s):
    with pytest.raises(ValueError, match="0.5 <= P_s < 1"):
        stdnum_for_survival(P_s)


def test_quantile_direction_and_life_shift():
    """At a given DP the P_s life is the median life times exp(-z STD), STD in ln N."""
    rng = np.random.default_rng(7)
    N = np.logspace(4, 7, 40)
    DP = 500.0 * N**-0.1 * np.exp(rng.normal(0.0, 0.05, N.size))
    z = stdnum_for_survival(0.9)
    median = fit_power_law_with_survival_std(N, DP, stdnum=0.0)
    shifted = fit_power_law_with_survival_std(N, DP, stdnum=z)
    assert shifted["A_surv"] < median["A_surv"] == pytest.approx(median["A"])
    life = lambda fit, dp: (dp / fit["A_surv"]) ** (1.0 / fit["b"])  # noqa: E731
    ratio = life(shifted, 200.0) / life(median, 200.0)
    assert ratio == pytest.approx(np.exp(-z * median["STD"]), rel=1e-12)
    assert ratio < 1.0  # a higher survival probability means a shorter design life


def test_pipeline_reports_and_applies_the_survival_probability(tmp_path):
    wb = write_workbook(tmp_path / "Ps.xlsx")
    median, design = tmp_path / "p50", tmp_path / "p90"
    run_workbook(wb, models=["CROSSLAND"], results_dir=median)
    run_workbook(wb, models=["CROSSLAND"], results_dir=design, survival_probability=0.9)
    a = pd.read_csv(median / "CROSSLAND_Ps.csv")
    b = pd.read_csv(design / "CROSSLAND_Ps.csv")
    assert (a.Survival_probability == 0.5).all() and (b.Survival_probability == 0.9).all()
    assert (a.CP_value == b.CP_value).all()  # the damage parameter itself is unchanged
    rows = (a.Metric_mode == "Nf") & np.isfinite(a.Nf_expected) & np.isfinite(b.Nf_expected)
    assert rows.any()
    ratio = (b.Nf_expected[rows] / a.Nf_expected[rows]).to_numpy()
    assert np.allclose(ratio, ratio[0]) and ratio[0] < 1.0  # one constant life factor
    side = json.loads((design / "Ps_calibration.json").read_text(encoding="utf-8"))
    settings = side["provenance"]["settings"]
    assert settings["master_curve_survival_probability"] == 0.9
    assert settings["master_curve_stdnum"] == pytest.approx(stdnum_for_survival(0.9))
    with pytest.raises(ValueError, match="0.5 <= P_s < 1"):
        run_workbook(wb, models=["CROSSLAND"], results_dir=tmp_path / "bad", survival_probability=1)


def test_compare_refuses_mixed_survival_probabilities(tmp_path):
    from multifat.cli.compare import collect_all_results

    wb = write_workbook(tmp_path / "Mix.xlsx")
    run_workbook(wb, models=["CROSSLAND"], results_dir=tmp_path / "r" / "a")
    run_workbook(wb, models=["SINES"], results_dir=tmp_path / "r" / "b", survival_probability=0.9)
    with pytest.raises(ValueError, match="mixes master curves"):
        collect_all_results(tmp_path / "r")
