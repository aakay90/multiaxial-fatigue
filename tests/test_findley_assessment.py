"""Production Findley algorithm selection and calibration-path compatibility."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from fatigue.eval.calibration import export_calibration
from fatigue.eval.calibration_store import curve_settings, load_calibration
from fatigue.eval.eligibility import assess_eligibility
from fatigue.imp import experimental_data as exp
from fatigue.models.utils.shear_amplitude import DEFINITION_VERSION
from fatigue.planes.sampling import build_R_list


ROOT = Path(__file__).resolve().parents[1]


class FindleyAssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = exp.import_experimental_data_grouped_by_material(
            ROOT / "Experimental_Data/archive/pre-dataset-migration")
        cls.material = "AISI316L"

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.settings = curve_settings(3, 6)
        self.runner = runpy.run_path(str(ROOT / "1_run_material.py"))
        self.globals = self.runner["main"].__globals__
        self.globals.update(
            MATERIAL_NAME=self.material, MODEL_NAME="FIN",
            CALIBRATIONS_DIR=str(self.folder / "calibrations"),
            RESULTS_DIR=str(self.folder / "results"),
            MAKE_PLOTS=False, DCMESH_N1=3, DCMESH_N2=6,
            CALIBRATION_ID=None, SHEAR_AMPLITUDE_ALGORITHM="method_default")

    def calibrate(self, selection):
        record, _ = export_calibration(
            data=self.data, material=self.material, models=["FIN"],
            parameters={"k_FI": .75}, settings=self.settings,
            folder=self.folder / "calibrations",
            shear_amplitude_algorithm=selection)
        return record

    def assess(self, selection="method_default"):
        self.globals["SHEAR_AMPLITUDE_ALGORITHM"] = selection
        with contextlib.redirect_stdout(io.StringIO()):
            return self.runner["main"](self.data)

    def test_strict_production_path_selects_only_matching_records(self):
        legacy = self.calibrate("method_default")
        harmonic_mce = self.calibrate("mce_harmonic")
        harmonic_mcc = self.calibrate("mcc_harmonic")
        self.assertEqual(len({r["calibration_id"] for r in
                              (legacy, harmonic_mce, harmonic_mcc)}), 3)
        for selection, path, expected in (
            ("method_default", "legacy", legacy),
            ("mce_harmonic", "harmonic", harmonic_mce),
            ("rss", "harmonic", harmonic_mce),
            ("mcc_harmonic", "harmonic", harmonic_mcc),
        ):
            kwargs = dict(data=self.data, material=self.material, model="FIN",
                          settings=self.settings, folder=self.folder / "calibrations",
                          shear_amplitude_algorithm=selection,
                          required_evaluation_path=path)
            self.assertEqual(load_calibration(**kwargs)[0]["calibration_id"],
                             expected["calibration_id"])
            for wrong in (legacy, harmonic_mce, harmonic_mcc):
                if wrong is not expected:
                    with self.assertRaisesRegex(ValueError, "incompatible"):
                        load_calibration(**kwargs, calibration_id=wrong["calibration_id"])
        with self.assertRaisesRegex(ValueError, "No compatible.*harmonic path"):
            load_calibration(data=self.data, material=self.material, model="FIN",
                settings=curve_settings(), folder=ROOT / "Calibrations",
                shear_amplitude_algorithm="mce_harmonic",
                required_evaluation_path="harmonic")

    def test_default_and_explicit_results_are_distinct_and_traceable(self):
        records = {selection: self.calibrate(selection)
                   for selection in ("method_default", "mcc_harmonic", "mce_harmonic")}
        paths = {}
        for selection in records:
            status = self.assess(selection)
            self.assertEqual(status["status"], "evaluated")
            csv = Path(status["csv_path"])
            paths[selection] = csv
            result = pd.read_csv(csv)
            label = ("FIN" if selection == "method_default" else f"FIN.{selection}")
            self.assertEqual(set(result["Method"]), {label})
            self.assertEqual(set(result["Calibration_id"]),
                             {records[selection]["calibration_id"]})
            metadata = json.loads(csv.with_suffix(".meta.json").read_text())
            self.assertEqual(metadata["selected_option"], selection)
            self.assertEqual(metadata["resolved_algorithm"],
                             "mce_harmonic" if selection == "method_default" else selection)
            self.assertEqual(metadata["definition_version"], DEFINITION_VERSION)
            self.assertEqual(metadata["evaluation_path"],
                             "legacy" if selection == "method_default" else "harmonic")
            self.assertEqual(metadata["calibration_id"], records[selection]["calibration_id"])
            self.assertEqual(metadata["calibration_formulation_fingerprint"],
                             records[selection]["formulation_fingerprints"]["FIN"])
            self.assertEqual(metadata["calibration_source"], records[selection]["source"])
            self.assertEqual(metadata["calibration_software"], records[selection]["software"])
            self.assertEqual(metadata["csv_sha256"], hashlib.sha256(csv.read_bytes()).hexdigest())
        self.assertEqual(len(set(paths.values())), 3)
        before = pd.read_csv(paths["mce_harmonic"])
        alias = self.assess("rss")
        self.assertEqual(Path(alias["csv_path"]), paths["mce_harmonic"])
        pd.testing.assert_frame_equal(pd.read_csv(paths["mce_harmonic"]), before, check_exact=True)
        self.assertEqual(json.loads(paths["mce_harmonic"].with_suffix(".meta.json").read_text())
                         ["selected_option"], "rss")
        comparison = runpy.run_path(str(ROOT / "2_compare_results.py"))
        combined = comparison["collect_all_results"](self.folder / "results")
        self.assertEqual(set(combined["Method"]),
                         {"FIN", "FIN.mcc_harmonic", "FIN.mce_harmonic"})
        self.globals["MODEL_NAME"] = "FIN_ext"
        extended = self.assess("mcc_harmonic")
        self.assertEqual(set(pd.read_csv(extended["csv_path"])["Method"]),
                         {"FIN.mcc_harmonic_ext"})

    def test_missing_matching_path_and_unsupported_methods_fail_cleanly(self):
        self.calibrate("mcc_harmonic")
        with self.assertWarnsRegex(RuntimeWarning, "mce_harmonic.*legacy path"):
            status = self.assess()
        self.assertFalse(status["prediction_available"])
        self.assertFalse(list((self.folder / "results").glob("*.csv")))
        self.globals["MODEL_NAME"] = "FS"
        with self.assertRaisesRegex(ValueError, "only for FIN"):
            self.assess("mcc_harmonic")
        self.globals["MODEL_NAME"] = "FIN"
        with self.assertRaisesRegex(ValueError, "Unknown Findley"):
            self.assess("unknown")

    def test_original_harmonics_are_required_before_endpoint_fallback(self):
        self.calibrate("mcc_harmonic")
        data = {name: block.copy() for name, block in self.data.items()}
        data[self.material] = {**data[self.material],
                               "cases": {cid: case.copy() for cid, case in
                                         data[self.material]["cases"].items()}}
        runout = next(cid for cid, case in data[self.material]["cases"].items()
                      if case["meta"]["test_status"] == "runout")
        data[self.material]["cases"][runout].pop("harmonics")
        result = assess_eligibility(
            data=data, material=self.material, method="FIN", settings=self.settings,
            folder=self.folder / "calibrations",
            shear_amplitude_algorithm="mcc_harmonic")
        self.assertTrue(result["prediction_available"])
        exclusion = next(item for item in result["excluded_cases"] if item["case_id"] == runout)
        self.assertIn("S_sin", " ".join(exclusion["reasons"]))
        self.globals["SHEAR_AMPLITUDE_ALGORITHM"] = "mcc_harmonic"
        with patch.object(self.globals["exp"], "extract_tensor",
                          wraps=self.globals["exp"].extract_tensor) as extractor, \
             self.assertWarnsRegex(RuntimeWarning, "Skipping.*S_sin"), \
             contextlib.redirect_stdout(io.StringIO()):
            status = self.runner["main"](data)
        self.assertEqual(status["status"], "evaluated")
        self.assertNotIn(runout, [call.args[2] for call in extractor.call_args_list])

    def test_nonproportional_production_damage_matches_independent_plane_svd(self):
        material = "Al7075_T6"
        self.globals["MATERIAL_NAME"] = material
        for selection in ("mcc_harmonic", "mce_harmonic"):
            export_calibration(
                data=self.data, material=material, models=["FIN"],
                parameters={"k_FI": .75}, settings=self.settings,
                folder=self.folder / "calibrations",
                shear_amplitude_algorithm=selection)
        results = {}
        for selection in ("mcc_harmonic", "mce_harmonic"):
            self.globals["SHEAR_AMPLITUDE_ALGORITHM"] = selection
            with contextlib.redirect_stdout(io.StringIO()):
                status = self.runner["main"](self.data)
            results[selection] = pd.read_csv(status["csv_path"])
        case_id, case = next((cid, case) for cid, case in
                             self.data[material]["cases"].items()
                             if case["meta"].get("specimen_id") == "Plain_multi_32")
        S0, _, S1, _, H = exp.extract_tensor(self.data, material, case_id, node=1,
                                              include_harmonics=True)
        mean = (S0 + S1) / 2
        reference = {}
        for selection in results:
            plane_damage = []
            for rotation in build_R_list(n1=3, n2=6):
                sine = rotation.T @ H["S_sin"] @ rotation
                cosine = rotation.T @ H["S_cos"] @ rotation
                singular = np.linalg.svd(np.column_stack(
                    (sine[:2, 2], cosine[:2, 2])), compute_uv=False)
                amplitude = (singular[0] if selection == "mcc_harmonic"
                             else np.hypot(*singular))
                normal = (rotation.T @ mean @ rotation)[2, 2]
                normal += np.hypot(sine[2, 2], cosine[2, 2])
                plane_damage.append(amplitude + .75 * normal)
            reference[selection] = max(plane_damage)
            row = results[selection].loc[
                (results[selection]["Specimen_id"] == "Plain_multi_32")
                & (results[selection]["Flag"] == 1)]
            self.assertEqual(len(row), 1)
            self.assertAlmostEqual(float(row.iloc[0]["CP_value"]),
                                   reference[selection], places=11)
        self.assertGreater(reference["mce_harmonic"] - reference["mcc_harmonic"], 20.)


if __name__ == "__main__":
    unittest.main()
