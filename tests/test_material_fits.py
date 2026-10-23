"""Constants fitted from a workbook's own tests (Phase 3, option D)."""

from __future__ import annotations

import numpy as np
import pytest

from multifat.eval.material_fits import basquin_fill, fit_basquin
from multifat.imp import experimental_data as exp
from workbook_factory import basquin_rows, write_workbook


def test_exact_basquin_is_recovered_and_identifiable():
    N = np.array([1e4, 3e4, 1e5, 3e5, 1e6, 2e6])
    f = fit_basquin(1500.0 * (2 * N) ** -0.09, N)
    assert (
        f["identifiable"]
        and f["coef"] == pytest.approx(1500.0)
        and f["exp"] == pytest.approx(-0.09)
    )


@pytest.mark.parametrize(
    "N, amp, why",
    [
        (
            np.array([1e5, 2e5, 4e5, 8e5, 1.6e6, 2e6]),
            np.array([243, 240, 245, 241, 244, 242.0]),
            "slope",
        ),
        (
            np.array([1e5, 2e5, 4e5, 8e5]),
            900 * (2 * np.array([1e5, 2e5, 4e5, 8e5])) ** -0.1,
            "tests",
        ),
        (
            np.array([1e5, 2e5, 3e5, 4e5, 5e5]),
            900 * (2 * np.array([1e5, 2e5, 3e5, 4e5, 5e5])) ** -0.1,
            "decades",
        ),
    ],
)
def test_unidentifiable_curves_are_rejected(N, amp, why):
    f = fit_basquin(amp, N)
    assert not f["identifiable"] and why in f["reason"]


def test_basquin_fill_from_workbook(tmp_path):
    fp = write_workbook(tmp_path / "S.xlsx", rows=basquin_rows(sf=1500, b=-0.09, tf=860, b0=-0.07))
    out = basquin_fill(exp.load_material_workbook(fp), "S")
    p = out["params"]
    assert p["sigma_f"] == pytest.approx(1500) and p["b_fat"] == pytest.approx(-0.09)
    assert p["tau_f"] == pytest.approx(860) and p["b0"] == pytest.approx(-0.07)
    assert len(out["design_case_ids"]["torsion"]) == 5


def test_flat_minimum_returns_its_smallest_point():
    from multifat.cli.calibrate import minimize_1d_smallest

    x, f, (lo, hi) = minimize_1d_smallest(lambda k: max(2.0 - k, 0.0) + 1.0, (0.0, 5.0))
    assert x == pytest.approx(2.0, abs=1e-5) and f == pytest.approx(1.0, abs=1e-5)
    assert lo == pytest.approx(2.0, abs=1e-5) and hi == pytest.approx(5.0)


def test_isolated_minimum_is_unchanged():
    from multifat.cli.calibrate import minimize_1d_smallest

    x, f, (lo, hi) = minimize_1d_smallest(lambda k: (k - 1.37) ** 2, (0.0, 5.0))
    assert x == pytest.approx(1.37, abs=1e-4) and lo == hi == x


def test_zhu_eq12_elastic_mean():
    from multifat.eval.material_fits import zhu_k_mgse

    # 42CrMo4 and Al7075 Basquin fits of the workbooks (findings F4)
    assert zhu_k_mgse(1498.1, -0.0911, 863.3, -0.0619, 206000, 0.315) == pytest.approx(
        2.34, abs=0.01
    )
    assert zhu_k_mgse(783.4, -0.1069, 368.4, -0.0800, 70500, 0.33) == pytest.approx(0.99, abs=0.01)
    # torsion and tension equivalent by von Mises (tf = sf/sqrt3, b0 = b): k = 2/(1+nu)*... constant
    E, nu = 200000.0, 0.3
    k = zhu_k_mgse(1000.0, -0.1, 1000.0 / 3**0.5, -0.1, E, nu)
    assert k == pytest.approx(2 * (1 + nu) / 3 * 2 - (1 + nu), rel=1e-9)
