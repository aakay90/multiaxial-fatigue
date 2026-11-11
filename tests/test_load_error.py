"""Load-equivalent error e_L = ln(1/s*) (issue #37): definition, paths and invariances."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from multifat.eval.endurance import case_from_amplitudes, damage, load_factor, scaled_case
from multifat.eval.load_error import (
    homogeneity_degree,
    master_curve_load_error,
    native_life_load_error,
)
from multifat.models.registry import get_models
from multifat.planes.sampling import build_R_list

R_LIST = build_R_list(n1=20, n2=40)
E, NU = 206000.0, 0.3
PARAMS = {"k_FI": 0.3, "k_FS": 1.0, "Sy": 600.0, "Sigm1": 420.0, "Taum1": 300.0, "Sig0": 650.0}


def _case(axial=250.0, shear=120.0, mean=(80.0, 0.0, 0.0)):
    return case_from_amplitudes(axial=axial, shear=shear, mean=mean, E=E, nu=NU)


@pytest.mark.parametrize("name,degree", [("FIN", 1.0), ("SWT", 2.0), ("CROSSLAND", 1.0)])
def test_degree_of_homogeneous_damage_parameters(name, degree):
    model = get_models([name])[0]
    case = _case()
    dp = damage(model, PARAMS, case, R_LIST)
    assert homogeneity_degree(model, PARAMS, case, R_LIST, dp) == pytest.approx(degree, abs=1e-9)


def test_non_homogeneous_damage_parameter_has_no_degree():
    model = get_models(["FS"])[0]  # gamma_a (1 + k sigma_n,max / Sy): degrees 1 and 2 mixed
    case = _case()
    assert (
        homogeneity_degree(model, PARAMS, case, R_LIST, damage(model, PARAMS, case, R_LIST)) is None
    )


@pytest.mark.parametrize("name", ["FIN", "SWT", "FS", "PCR"])
@pytest.mark.parametrize("ratio", [0.8, 1.0, 1.3])
def test_scaled_load_reaches_the_master_curve(name, ratio):
    """DP(s* x) = DP_fit with s* = exp(-e_L), for closed-form and iterative paths alike."""
    model = get_models([name])[0]
    case = _case()
    dp = damage(model, PARAMS, case, R_LIST)
    DP_fit = ratio * dp
    e_L = master_curve_load_error(model, PARAMS, case, R_LIST, dp, DP_fit)
    reached = damage(model, PARAMS, scaled_case(case, math.exp(-e_L)), R_LIST)
    assert reached == pytest.approx(DP_fit, rel=1e-9)
    assert e_L == pytest.approx(
        -math.log(load_factor(model, PARAMS, case, DP_fit, R_LIST)), abs=1e-9
    )
    # Conservative (e_L > 0) when the model's DP exceeds the curve at the observed life
    assert np.sign(e_L) == np.sign(math.log(dp / DP_fit))


def test_life_error_is_the_load_error_amplified_by_slope_and_degree():
    """ln(N_exp/N_pred) = -d e_L / b = k d e_L for a homogeneous DP on DP = A N^b."""
    model = get_models(["SWT"])[0]
    case = _case()
    A, b, Nf = 2.0, -0.15, 2.0e5
    dp = damage(model, PARAMS, case, R_LIST)
    e_L = master_curve_load_error(model, PARAMS, case, R_LIST, dp, A * Nf**b)
    N_pred = (dp / A) ** (1.0 / b)
    assert math.log(Nf / N_pred) == pytest.approx(-2.0 * e_L / b, rel=1e-9)


def test_native_life_load_error_reaches_the_observed_life():
    from multifat.models.integral_methods.morel import Morel

    model = Morel()
    params = {"Sigm1": 420.0, "Taum1": 300.0}
    fit = {"p": 4.0e4, "q": 2.5e4, "r": 1.0e5}
    case = _case(axial=480.0, shear=230.0, mean=(0.0, 0.0, 0.0))

    def life(scale):
        scaled = scaled_case(case, scale)
        result = model.evaluate_case(
            S0=scaled["S0"], E0=scaled["E0"], S1=scaled["S1"], E1=scaled["E1"], params=params,
            harmonics=scaled["H"],
        )  # fmt: skip
        return float(model.native_life({"dp": result.values[""], **result.aux}, params, fit))

    assert np.isfinite(life(1.0)), "the test load must be above the Morel limit"
    for Nf in (life(1.0) * 0.5, life(1.0) * 3.0):
        e_L = native_life_load_error(model, params, case, None, fit, Nf)
        assert life(math.exp(-e_L)) == pytest.approx(Nf, rel=1e-6)
    assert native_life_load_error(model, params, case, None, fit, life(1.0)) == pytest.approx(
        0.0, abs=1e-9
    )


def test_native_life_load_error_is_nan_when_a_trial_load_leaves_the_scope():
    """A LoadingScopeError at a trial load makes e_L undefined (NaN), not a failed model."""
    from multifat.models.base import CaseResult
    from multifat.models.errors import LoadingScopeError

    class ScopedLife:
        name = "SCOPED"

        def evaluate_case(self, *, S0, E0, S1, E1, params, R_list=None, harmonics=None):
            amplitude = float(np.max(np.abs(harmonics["S_sin"])))
            if amplitude > 300.0:
                raise LoadingScopeError("SCOPED: above 300 MPa")
            return CaseResult(values={"": amplitude}, aux={})

        def native_life(self, aux, params, fit=None):
            return (500.0 / aux["dp"]) ** 10

    case = _case(axial=250.0, shear=0.0, mean=(0.0, 0.0, 0.0))
    assert math.isnan(native_life_load_error(ScopedLife(), {}, case, None, None, 1.0))
    assert np.isfinite(native_life_load_error(ScopedLife(), {}, case, None, None, 2.0**10))


def test_pipeline_exports_the_load_error(tmp_path):
    from multifat.cli.pipeline import run_workbook
    from workbook_factory import write_workbook

    wb = write_workbook(tmp_path / "Le.xlsx")
    run_workbook(wb, models=["FIN", "SWT"], results_dir=tmp_path / "res")
    for name, degree in (("FIN", 1.0), ("SWT", 2.0)):
        df = pd.read_csv(tmp_path / "res" / f"{name}_Le.csv")
        failures = df[df.Flag != 2]
        assert failures.Error_load.notna().all() and df[df.Flag == 2].Error_load.isna().all()
        # Homogeneous DP: e_L = ln(DP / DP_fit) / d, i.e. -ln(10) Error_log10_dp / d
        expected = -math.log(10.0) * failures.Error_log10_dp / degree
        assert np.allclose(failures.Error_load, expected, rtol=1e-9, atol=1e-12)


def test_native_load_error_below_the_limit():
    """A load below the Morel limit (infinite native life) still has a finite load error."""
    from multifat.models.integral_methods.morel import Morel

    model, params = Morel(), {"Sigm1": 420.0, "Taum1": 300.0}
    fit = {"p": 4.0e4, "q": 2.5e4, "r": 1.0e5}
    case = _case(axial=330.0, shear=150.0, mean=(0.0, 0.0, 0.0))
    e_L = native_life_load_error(model, params, case, None, fit, 1.0e6)
    assert np.isfinite(e_L) and e_L < 0.0  # the load must grow to fail: non-conservative


def test_diverging_secant_falls_back_to_bisection():
    """A secant step beyond |ln s| = LOG_S_MAX returns None instead of overflowing (#71)."""
    from multifat.eval.load_error import LOG_S_MAX, _solve_in_log

    # g is flat near 0 and steep far away: the first secant step jumps beyond the bound
    assert _solve_in_log(lambda x: 1.0 + 1e-6 * x) is None
    assert _solve_in_log(lambda x: x - 0.3) == pytest.approx(math.exp(0.3))
    assert LOG_S_MAX == 10.0
