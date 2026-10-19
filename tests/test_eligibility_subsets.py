"""Preflight, skip and matched-subset tests on explicit experimental inputs."""
import copy
import contextlib
import io
from pathlib import Path
import runpy
import tempfile
import unittest

import numpy as np
import pandas as pd

from fatigue.eval.calibration import export_calibration
from fatigue.eval.calibration_store import curve_settings
from fatigue.eval.eligibility import assess_eligibility, calibration_readiness, input_requirements
from fatigue.imp.experimental_data import import_experimental_data_grouped_by_material
from fatigue.report.subsets import common_subset, write_subset_reports

ROOT = Path(__file__).resolve().parents[1]


class EligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = import_experimental_data_grouped_by_material(ROOT / 'Experimental_Data/archive/pre-dataset-migration')
        cls.settings = curve_settings(3, 6)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def assess(self, data=None, method='BP'):
        return assess_eligibility(data=data or self.data, material='AISI316L', method=method,
                                 settings=self.settings, folder=self.folder)

    def test_missing_calibration_differs_from_missing_inputs(self):
        status = self.assess()
        self.assertEqual(status['status'], 'calibration_required')
        self.assertTrue(status['can_calibrate'])
        changed = copy.deepcopy(self.data)
        changed['AISI316L']['material']['Torsional_fatigue_limit_MPa'] = None
        status = self.assess(changed)
        self.assertFalse(status['can_calibrate'])
        self.assertIn('Taum1', status['missing_properties'])
        self.assertFalse(status['prediction_available'])

    def test_compatible_and_changed_calibrations(self):
        export_calibration(data=self.data, material='AISI316L', models=['BP'], parameters={},
                           settings=self.settings, folder=self.folder)
        self.assertTrue(self.assess()['prediction_available'])
        changed = copy.deepcopy(self.data)
        changed['AISI316L']['material']['Tensile_strength_MPa'] += 1
        self.assertFalse(self.assess(changed)['prediction_available'])

    def test_runout_only_does_not_produce_a_curve_or_ordinary_errors(self):
        changed = copy.deepcopy(self.data)
        for case in changed['AISI316L']['cases'].values():
            case['meta']['test_status'] = 'runout'
        status = self.assess(changed)
        self.assertFalse(status['can_calibrate'])
        self.assertFalse(status['quantitative_comparison_available'])
        self.assertIn('distinct observed', ' '.join(status['reasons']))

    def test_method_specific_requirements_and_no_nonsteel_empirical_fallback(self):
        changed = copy.deepcopy(self.data)
        changed['AISI316L']['material']['nu'] = None
        self.assertNotIn('nu', input_requirements(changed, 'AISI316L', 'FIN', calibration=True)[0])
        self.assertIn('nu', input_requirements(changed, 'AISI316L', 'FS', calibration=True)[0])
        self.assertIn('sigma_f', input_requirements(self.data, 'Al7075_T6', 'GSA', calibration=True)[0])

    def test_supplied_liu_fatigue_strength_does_not_require_ultimate_strength(self):
        changed = copy.deepcopy(self.data)
        changed['AISI316L']['material'].update(tau_f=300, Tensile_strength_MPa=None)
        missing, _, _ = input_requirements(changed, 'AISI316L', 'LIU2021', calibration=True)
        self.assertNotIn('Su', missing)
        self.assertNotIn('tau_f', missing)

    def test_single_request_warns_and_writes_no_result(self):
        runner = runpy.run_path(str(ROOT / '1_run_material.py'))
        runner['main'].__globals__.update(DATA_FOLDER=str(ROOT / 'Experimental_Data/archive/pre-dataset-migration'),
            MATERIAL_NAME='AISI316L', MODEL_NAME='BP', CALIBRATIONS_DIR=str(self.folder),
            RESULTS_DIR=str(self.folder), MAKE_PLOTS=False, DCMESH_N1=3, DCMESH_N2=6)
        with self.assertWarnsRegex(RuntimeWarning, 'AISI316L/BP'), contextlib.redirect_stdout(io.StringIO()):
            result = runner['main']()
        self.assertFalse(result['prediction_available'])
        self.assertFalse(list(self.folder.glob('*.csv')))

    def test_calibration_batch_skips_only_unavailable_method(self):
        script = runpy.run_path(str(ROOT / '0_calibrate_material_params.py'))
        # Missing tau strength blocks BP but not SWT. A separate method fit must survive.
        from unittest.mock import patch
        changed = copy.deepcopy(self.data)
        changed['AISI316L']['material']['Torsional_fatigue_limit_MPa'] = None
        with patch.object(script['exp'], 'import_experimental_data_grouped_by_material', return_value=changed), \
             self.assertWarns(RuntimeWarning), contextlib.redirect_stdout(io.StringIO()):
            paths = script['main'](['--material', 'AISI316L', '--models', 'BP', 'SWT', '--n1', '3',
                '--n2', '6', '--calibrations-dir', str(self.folder)])
        self.assertEqual(len(paths), 1)
        self.assertTrue(calibration_readiness(changed, 'AISI316L', 'SWT')['can_calibrate'])


class SubsetTests(unittest.TestCase):
    def frame(self):
        rows = []
        for method, ids in [('A', ['1', '2', '3']), ('B', ['2', '3', '4']), ('C', ['3', '4'])]:
            for oid in ids:
                rows.append(dict(Method=method, Material='M', Observation_id=oid, Case_id='load-' + oid,
                    Dataset_fingerprint='dataset', Test_status='failure', Nf_exp=100, Nf_expected=120,
                    Error_ln=-0.18, Error_log10_dp=0.1, Flag=1))
        return pd.DataFrame(rows)

    def test_pairwise_and_group_intersection_preserves_individual_results(self):
        df = self.frame()
        pair = common_subset(df, ['A', 'B'])
        self.assertEqual(set(pair.Observation_id), {'2', '3'})
        self.assertEqual(pair.groupby('Method').size().tolist(), [2, 2])
        self.assertEqual(set(common_subset(df, ['A', 'B', 'C']).Observation_id), {'3'})
        self.assertEqual(len(df), 8)
        with tempfile.TemporaryDirectory() as folder:
            counts, overlaps = write_subset_reports(df, folder)
            self.assertEqual(counts[0]['observations'], 3)
            self.assertTrue(overlaps)

    def test_runouts_invalid_predictions_and_different_datasets_are_excluded(self):
        df = self.frame()
        df.loc[(df.Method == 'B') & (df.Observation_id == '2'), 'Test_status'] = 'runout'
        df.loc[(df.Method == 'B') & (df.Observation_id == '3'), 'Error_ln'] = np.nan
        self.assertTrue(common_subset(df, ['A', 'B']).empty)
        self.assertEqual(set(common_subset(df, ['A', 'B'], 'damage').Observation_id), {'3'})
        df.loc[df.Method == 'B', 'Dataset_fingerprint'] = 'different'
        self.assertTrue(common_subset(df, ['A', 'B'], 'damage').empty)

    def test_ambiguous_and_duplicate_observations_are_rejected(self):
        df = self.frame()
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            common_subset(pd.concat([df, df.iloc[:1]]), ['A', 'B'])
        df.loc[0, 'Observation_id'] = ''
        with self.assertRaisesRegex(ValueError, 'Unresolved'):
            common_subset(df, ['A', 'B'])


@unittest.skipUnless((ROOT / 'Experimental_Data/6_42CrMo4_QT.xlsx').exists(),
                     'Revised workbooks await authorised publication; baseline pipeline tests still run')
class RevisedEndToEndTests(unittest.TestCase):
    def test_new_workbooks_calibration_batch_and_common_comparison(self):
        data = import_experimental_data_grouped_by_material(ROOT / 'Experimental_Data')
        settings = curve_settings(3, 6)
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            for method in ['BP', 'SWT']:
                export_calibration(data=data, material='42CrMo4_QT', models=[method], parameters={},
                                   settings=settings, folder=folder / 'calibrations')
            script = runpy.run_path(str(ROOT / '3_review_subsets.py'))
            with self.assertWarns(RuntimeWarning), contextlib.redirect_stdout(io.StringIO()):
                rows = script['main'](['--data-folder', str(ROOT / 'Experimental_Data'),
                    '--models', 'BP', 'SWT', '--materials', '42CrMo4_QT', 'GGG60', 'CX18',
                    '--n1', '3', '--n2', '6', '--calibrations-dir', str(folder / 'calibrations'),
                    '--run', '--results-dir', str(folder / 'results'), '--report-dir', str(folder / 'reports')])
            self.assertEqual(sum(r['prediction_available'] for r in rows), 2)
            frames = [pd.read_csv(p) for p in (folder / 'results').glob('*.csv')]
            self.assertEqual(len(frames), 2)
            for frame in frames:
                self.assertEqual(len(frame), 56)
                self.assertEqual((frame.Test_status == 'runout').sum(), 11)
                self.assertFalse(frame.Observation_id.isna().any())
                self.assertTrue(frame.loc[frame.Test_status == 'runout', 'Error_ln'].isna().all())
            matched = common_subset(pd.concat(frames), ['BP', 'SWT'])
            self.assertEqual(matched.groupby('Method').size().tolist(), [45, 45])
            # A data-selection defect affects one case only, not the other material-method pairs.
            import copy
            broken = copy.deepcopy(data)
            cid = next(iter(broken['42CrMo4_QT']['cases']))
            broken['42CrMo4_QT']['cases'][cid]['meta']['loading_issues'] = ['Missing stress input']
            status = assess_eligibility(data=broken, material='42CrMo4_QT', method='BP',
                                       settings=settings, folder=folder / 'calibrations')
            self.assertTrue(status['excluded_cases'])
