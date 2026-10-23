"""Exported CSVs must be UTF-8 on every platform (references contain non-ASCII text)."""

import numpy as np
import pandas as pd

from multifat.report.export_csv import save_fatigue_csv


def test_csv_is_utf8_with_non_ascii_reference(tmp_path):
    path = save_fatigue_csv(
        out_dir=str(tmp_path),
        method_name="SWT",
        material_name="m",
        N_exp=[1e5],
        CP=[1.0],
        N_pred=[np.nan],
        basquin_meta={"A_surv": 1.0, "b": -0.1},
        metric_mode="Nf",
    )
    text = open(path, encoding="utf-8").read()  # raises if written in a legacy code page
    assert "767–778" in text


def test_runouts_appended_with_flag_2_and_no_errors(tmp_path):
    common = dict(
        out_dir=str(tmp_path),
        method_name="SWT",
        material_name="m",
        N_exp=[1e5],
        CP=[1.0],
        N_pred=[2e5],
        DP_fit=[1.1],
        metric_mode="Nf",
    )
    plain = open(save_fatigue_csv(**common), encoding="utf-8").read()
    path = save_fatigue_csv(
        **common,
        N_runout=[5e6],
        CP_runout=[0.8],
        N_pred_runout=[3e6],
        DP_fit_runout=[0.7],
        loading_type_runout=["Tensile"],
    )
    text = open(path, encoding="utf-8").read()
    assert text.startswith(plain)  # failure rows unchanged, run-outs only appended
    df = pd.read_csv(path)
    run = df[df.Flag == 2]
    assert len(run) == 1 and run.Nf_exp.iloc[0] == 5e6 and run.CP_value.iloc[0] == 0.8
    assert run[["Error_ln", "Error_ln_dp", "Error_log10_dp"]].isna().all().all()
