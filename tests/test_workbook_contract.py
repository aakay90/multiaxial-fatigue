"""Workbook input contract: header matching, load-time validation and error messages."""

from __future__ import annotations

import pytest

from multifat.imp import experimental_data as exp
from multifat.imp.schema import WorkbookError, header_key, match_constant_columns
from multifat.cli.run import validate_workbook
from workbook_factory import DATASET_HEADERS, SUMMARY_HEADERS, SUMMARY_VALUES, write_workbook


def test_header_key_strips_units_and_footnotes():
    assert header_key("  b0 (-) ") == "b0"
    assert header_key("Tensile fatigue limit* (MPa)") == "tensile fatigue limit"
    assert header_key("sigma_f") == "sigma_f"


def test_constants_match_whole_header_only():
    headers = ["shear fatigue strength exponent", "b0_old", "tau_f (MPa)", "sigma_f'"]
    cols = match_constant_columns(
        headers, {"b0": ("b0", "shear fatigue strength exponent"), "tau_f": ("tau_f",)}
    )
    assert cols == {"b0": 1, "tau_f": 3}


def test_minimal_workbook_loads(tmp_path):
    fp = write_workbook(tmp_path / "Synth.xlsx")
    data = exp.load_material_workbook(fp)
    assert list(data) == ["Synth"]
    assert len(data["Synth"]["cases"]) == 15  # run-out and notched rows are not failures
    runouts = data["Synth"]["runouts"]
    assert len(runouts) == 1 and runouts[0]["meta"]["test_status"] == "runout"
    assert runouts[0]["meta"]["Nf_cycles"] == 5e6
    rep = validate_workbook(fp)
    assert rep.ok, rep.text()


def test_optional_summary_columns_may_be_absent(tmp_path):
    keep = [i for i, h in enumerate(SUMMARY_HEADERS) if not h.startswith(("k FS", "k FI", "Yield"))]
    fp = write_workbook(
        tmp_path / "NoK.xlsx",
        summary_headers=[SUMMARY_HEADERS[i] for i in keep],
        summary_values=[SUMMARY_VALUES[i] for i in keep],
    )
    mat = exp.load_material_workbook(fp)["NoK"]["material"]
    assert mat["k_FS"] is None and mat["Yield_strength_MPa"] is None


def test_declared_model_constant_is_passed_through(tmp_path):
    fp = write_workbook(tmp_path / "Kphi.xlsx", extra_summary={"k_phi (-)": 0.8, "b0": -0.07})
    mat = exp.load_material_workbook(fp)["Kphi"]["material"]
    assert mat["b0"] == pytest.approx(-0.07)
    assert mat["extra"]["k_phi"] == pytest.approx(0.8)


@pytest.mark.parametrize(
    "kwargs, where",
    [
        (dict(sheets=("Summary",)), "Dataset"),
        (dict(dataset_headers=[h for h in DATASET_HEADERS if "SHEAR" not in h]), "Dataset"),
        (dict(summary_values=SUMMARY_VALUES[:5] + [0.9] + SUMMARY_VALUES[6:]), "Poisson"),
    ],
)
def test_contract_violations_raise_workbook_error(tmp_path, kwargs, where):
    fp = write_workbook(tmp_path / "Bad.xlsx", **kwargs)
    with pytest.raises(WorkbookError, match=where):
        exp.load_material_workbook(fp)


def test_missing_design_set_is_reported(tmp_path):
    rows = [r for r in __import__("workbook_factory").basquin_rows() if r[8] == 0 or r[10] != 0]
    fp = write_workbook(tmp_path / "NoUni.xlsx", rows=rows)
    rep = validate_workbook(fp)
    assert not rep.ok
    assert any("design" in e for e in rep.errors)
