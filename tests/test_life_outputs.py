"""Pipeline tests with a synthetic cycle-valued model, not a fatigue criterion."""
import contextlib
import io
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from fatigue.models.base import CaseResult
from fatigue.imp import experimental_data as exp
from fatigue.eval.calibration import collect_uniaxial_series_and_fit

ROOT = Path(__file__).resolve().parents[1]


class SyntheticLifeModel:
    name = "SYNTHETIC_LIFE"
    output_quantity = "life_cycles"

    def required_params(self):
        return set()

    def evaluate_case(self, *, S0, **kwargs):
        # Arbitrary deterministic numbers used only to test routing and units.
        return CaseResult(values={"": 1000.0 + float(np.linalg.norm(S0))},
                          output_quantity="life_cycles")


class LifeOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = exp.import_experimental_data_grouped_by_material(ROOT / "Experimental_Data")

    def test_life_result_declares_cycles_without_changing_legacy_default(self):
        self.assertEqual(CaseResult({"": 1.0}).output_quantity, "damage_parameter")
        self.assertEqual(SyntheticLifeModel().evaluate_case(S0=np.eye(3)).output_quantity,
                         "life_cycles")

    def test_generic_collector_refuses_life_and_unconvertible_indices(self):
        model = SyntheticLifeModel()
        for quantity in ["life_cycles", "index"]:
            model.output_quantity = quantity
            with self.subTest(quantity=quantity), self.assertRaisesRegex(ValueError, "damage_parameter"):
                collect_uniaxial_series_and_fit(data=self.data, exp=exp, material_name="AISI316L",
                    uniax_cases=exp.extract_uniaxial_tension(self.data), R_list=None,
                    models=[model], params={})

    def test_runner_rejects_mismatched_units_and_invalid_lives(self):
        for result in [CaseResult({"": 1000.0}),
                       CaseResult({"": -1.0}, output_quantity="life_cycles"),
                       CaseResult({"": float("inf")}, output_quantity="life_cycles")]:
            with self.subTest(result=result), tempfile.TemporaryDirectory() as folder:
                runner = runpy.run_path(str(ROOT / "1_run_material.py"))
                model = SyntheticLifeModel()
                model.evaluate_case = lambda **kwargs: result
                runner["main"].__globals__.update(DATA_FOLDER=str(ROOT / "Experimental_Data"),
                    MATERIAL_NAME="AISI316L", MODEL_NAME=model.name, RESULTS_DIR=folder, MAKE_PLOTS=False)
                with patch.dict(runner["main"].__globals__, get_models=lambda names: [model]), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(ValueError):
                        runner["main"]()
                self.assertFalse(list(Path(folder).glob("*.csv")))

    def test_runner_exports_direct_cycles_without_archive_or_damage_fit(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = runpy.run_path(str(ROOT / "1_run_material.py"))
            runner["main"].__globals__.update(DATA_FOLDER=str(ROOT / "Experimental_Data"),
                CALIBRATIONS_DIR=str(Path(folder) / "absent"), MATERIAL_NAME="AISI316L",
                MODEL_NAME="SYNTHETIC_LIFE", RESULTS_DIR=folder, MAKE_PLOTS=True, PLOT_DIR=folder)
            with patch.dict(runner["main"].__globals__, get_models=lambda names: [SyntheticLifeModel()]), contextlib.redirect_stdout(io.StringIO()):
                runner["main"]()
            result = pd.read_csv(Path(folder) / "SYNTHETIC_LIFE_AISI316L.csv")
            cases = list(self.data["AISI316L"]["cases"].values())
            expected = [1000.0 + np.linalg.norm(c[1][1]["stress"]) for c in cases]
            np.testing.assert_allclose(result.Nf_expected, expected, rtol=1e-15)
            self.assertTrue(result.Metric_mode.eq("Nf_direct").all())
            self.assertTrue(result[["CP_value", "DP_fit", "Error_ln_dp", "Error_log10_dp"]].isna().all().all())
            self.assertTrue(result.Flag.eq(1).all())
            self.assertEqual(result.Test_status.value_counts().to_dict(), {"failure": 31, "runout": 13})
            self.assertTrue(result.loc[result.Test_status == "runout", "Error_ln"].isna().all())
            failed = result[result.Test_status == "failure"]
            np.testing.assert_allclose(failed.Error_ln, np.log(failed.Nf_exp / failed.Nf_expected))
            self.assertTrue((Path(folder) / "SYNTHETIC_LIFE_AISI316L_life_parity.png").is_file())
            compare = runpy.run_path(str(ROOT / "2_compare_results.py"))
            read = compare["read_results_csv"](Path(folder) / "SYNTHETIC_LIFE_AISI316L.csv")
            stats = compare["compute_stats_table"](read)
            self.assertEqual(stats.Metric.tolist(), ["Error_ln"])
            self.assertEqual(int(stats.n.max()), 31)


if __name__ == "__main__":
    unittest.main()
