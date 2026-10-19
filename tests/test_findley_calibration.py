"""Calibration, immutable history and production MCE compatibility checks."""
import contextlib
import copy
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch
import warnings

import numpy as np
import pandas as pd

from fatigue.eval.calibration import export_calibration
from fatigue.eval.calibration_store import (
    calibration_signature, curve_settings, findley_amplitude_settings,
    formulation_fingerprint, load_calibration, read_record, save_record, validate_record,
)
from fatigue.eval.eligibility import assess_eligibility, calibration_readiness
from fatigue.eval.findley_calibration import (
    FindleyCalibrationModel, check_amplitude_methods, require_stress_harmonics,
    resolve_findley_algorithm,
)
from fatigue.imp import experimental_data as exp
from fatigue.models.cp_methods.fin_harmonic import evaluate_findley
from fatigue.models.utils.shear_amplitude import DEFINITION_VERSION

ROOT = Path(__file__).resolve().parents[1]


class FindleyCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = exp.import_experimental_data_grouped_by_material(
            ROOT / 'Experimental_Data/archive/pre-dataset-migration')
        cls.material = 'AISI316L'
        cls.baseline = json.loads((ROOT / 'tests/fixtures/parameter_calibration_three_plane_baseline.json').read_text())
        cls.planes = np.asarray(cls.baseline['settings']['planes'])
        cls.script = runpy.run_path(str(ROOT / '0_calibrate_material_params.py'))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.settings = curve_settings(3, 6)

    def optimise(self, algorithm='method_default', data=None):
        return self.script['calibrate_material_params'](
            data=data or self.data, material_name=self.material, R_list=self.planes,
            n_grid_1d=5, n_refine_1d=1, methods=['FIN'],
            shear_amplitude_algorithm=algorithm)

    def export(self, algorithm='method_default', **kwargs):
        return export_calibration(data=kwargs.pop('data', self.data), material=self.material,
            models=kwargs.pop('models', ['FIN']), parameters=kwargs.pop('parameters', {'k_FI': .75}),
            settings=self.settings, folder=self.folder, shear_amplitude_algorithm=algorithm, **kwargs)

    def load(self, algorithm='method_default', **kwargs):
        return load_calibration(data=self.data, material=self.material, model=kwargs.pop('model', 'FIN'),
            settings=self.settings, folder=self.folder, shear_amplitude_algorithm=algorithm, **kwargs)

    def test_resolution_and_method_scope(self):
        for selection, expected in [('method_default', 'mce_harmonic'), ('rss', 'mce_harmonic'),
                                    ('mce_harmonic', 'mce_harmonic'), ('mcc_harmonic', 'mcc_harmonic')]:
            self.assertEqual(resolve_findley_algorithm(selection), expected)
        for bad in (None, [], 'mcc', ''):
            with self.assertRaises(ValueError):
                resolve_findley_algorithm(bad)
        check_amplitude_methods(['FS', 'FIN', 'BP'], 'method_default')
        for name in ('FS', 'MATAKE', 'MCD', 'BP'):
            with self.assertRaisesRegex(ValueError, 'only for FIN'):
                check_amplitude_methods(['FIN', name], 'mcc_harmonic')
            ready = calibration_readiness(self.data, self.material, name,
                                           shear_amplitude_algorithm='mcc_harmonic')
            self.assertFalse(ready['can_calibrate'])
            with self.assertRaisesRegex(ValueError, 'only for FIN'):
                self.load('mce_harmonic', model=name)

    def test_default_and_explicit_proportional_optimisation_against_baseline(self):
        default = self.optimise()
        np.testing.assert_allclose(default['FI']['k_FI'], self.baseline['FI']['k_FI'], rtol=0, atol=0)
        for key in ('A', 'b', 'A_surv', 'STD'):
            np.testing.assert_allclose(default['FI']['fit'][key], self.baseline['FI']['fit'][key], rtol=1e-12)
        for algorithm in ('mcc_harmonic', 'mce_harmonic', 'rss'):
            result = self.optimise(algorithm)
            self.assertEqual(result['selection'], default['selection'])
            self.assertEqual(result['FI']['k_FI'], default['FI']['k_FI'])
            for key in ('A', 'b', 'A_surv', 'STD'):
                np.testing.assert_allclose(result['FI']['fit'][key], default['FI']['fit'][key], rtol=2e-13)
            self.assertEqual(result['amplitude_settings']['FIN']['algorithm'], resolve_findley_algorithm(algorithm))

    def test_same_configured_evaluator_in_both_calibration_stages(self):
        calls = []
        original = FindleyCalibrationModel.evaluate_case

        def capture(model, **kwargs):
            result = original(model, **kwargs)
            expected = evaluate_findley(**kwargs, shear_amplitude_algorithm='mcc_harmonic')
            self.assertEqual(result, expected)
            calls.append(model.algorithm)
            return result

        with patch.object(FindleyCalibrationModel, 'evaluate_case', capture):
            optimisation = self.optimise('mcc_harmonic')
            coefficient_calls = len(calls)
            self.assertGreater(coefficient_calls, 11)
            record, _ = self.export('mcc_harmonic', parameters={'k_FI': optimisation['FI']['k_FI']},
                                    optimisation=optimisation)
            self.assertGreater(len(calls), coefficient_calls)
        self.assertEqual(set(calls), {'mcc_harmonic'})
        self.assertEqual(record['counts']['failures_selected_for_coefficients'], 11)
        self.assertEqual(record['counts']['failures_used_by_curve']['FIN'], 6)
        self.assertEqual(record['counts']['runout'], 13)

    def test_coefficient_objective_uses_mcc_on_nonproportional_diagnostic(self):
        # Probe the actual callable passed to the optimiser, on a prescribed
        # plane, independently of the proportional experimental selection.
        diagnostic = dict(S0=np.diag([0., 0., 7.]), S1=np.diag([0., 0., 7.]),
                          E0=np.zeros((3, 3)), E1=np.zeros((3, 3)))
        a = np.array([[0., 0., 10.], [0., 0., 0.], [10., 0., 3.]])
        b = np.array([[0., 0., 0.], [0., 0., 10.], [0., 10., 4.]])
        diagnostic['H'] = dict(S_sin=a, S_cos=b)
        original = self.script['_calibrate_1d']
        values = []

        def probe(**kwargs):
            values.append(kwargs['dp_eval'](diagnostic, .2))
            return original(**kwargs)

        # Use a real experimental optimisation on a valid plane grid, but replace
        # the diagnostic's global basis so that its local z is the first normal.
        r = self.planes[0]
        for key in ('S0', 'S1', 'E0', 'E1'):
            diagnostic[key] = r @ diagnostic[key] @ r.T
        diagnostic['H'] = {key: r @ value @ r.T for key, value in diagnostic['H'].items()}
        # On the full grid the independent reference uses SVD on every plane.
        def expected(algorithm):
            scores = []
            for rotation in self.planes:
                sr, cr = (rotation.T @ diagnostic['H'][key] @ rotation for key in ('S_sin', 'S_cos'))
                sv = np.linalg.svd(np.column_stack((sr[:2, 2], cr[:2, 2])), compute_uv=False)
                amplitude = sv[0] if algorithm == 'mcc_harmonic' else np.hypot(*sv)
                mean = (rotation.T @ diagnostic['S0'] @ rotation)[2, 2]
                scores.append(amplitude+.2*(mean+np.hypot(sr[2, 2], cr[2, 2])))
            return max(scores)
        for algorithm in ('mcc_harmonic', 'mce_harmonic'):
            with patch.dict(self.script['calibrate_material_params'].__globals__, _calibrate_1d=probe):
                self.optimise(algorithm)
            np.testing.assert_allclose(values[-1], expected(algorithm), rtol=3e-15)
        self.assertGreater(abs(values[0]-values[1]), 1.)

    def test_master_curve_and_metadata_for_both_algorithms_and_rerun(self):
        records = {}
        for algorithm in ('mcc_harmonic', 'mce_harmonic'):
            optimisation = self.optimise(algorithm)
            record, path = self.export(algorithm, parameters={'k_FI': optimisation['FI']['k_FI']},
                                       optimisation=optimisation)
            repeated, repeated_path = self.export(algorithm, parameters=record['parameters'],
                                                  optimisation=optimisation)
            self.assertEqual(repeated_path, path)
            self.assertEqual(repeated, record)
            metadata = record['amplitude_settings']['FIN']
            self.assertEqual(metadata, findley_amplitude_settings(algorithm))
            self.assertEqual(metadata['definition_version'], DEFINITION_VERSION)
            self.assertEqual(metadata['implementation_fingerprint'], record['formulation_fingerprints']['FIN'])
            self.assertEqual(metadata['evaluation_path'], 'harmonic')
            self.assertEqual(record['curves']['FIN']['fit'], record['curves']['FIN']['fit_ext'])
            records[algorithm] = record
        mcc, mce = (records[a] for a in ('mcc_harmonic', 'mce_harmonic'))
        for key in ('N', 'CP', 'CP_ext'):
            np.testing.assert_allclose(mcc['curves']['FIN']['series'][key],
                                       mce['curves']['FIN']['series'][key], rtol=3e-15)
        for key in ('A', 'b', 'A_surv', 'STD'):
            np.testing.assert_allclose(mcc['curves']['FIN']['fit'][key], mce['curves']['FIN']['fit'][key], rtol=2e-13)
        self.assertNotEqual(mcc['calibration_id'], mce['calibration_id'])
        self.assertNotEqual(calibration_signature(mcc), calibration_signature(mce))
        identical_values = copy.deepcopy(mcc)
        identical_values['amplitude_settings']['FIN'] = mce['amplitude_settings']['FIN']
        identical_values['formulation_fingerprints']['FIN'] = mce['formulation_fingerprints']['FIN']
        self.assertEqual(identical_values['curves'], mcc['curves'])
        self.assertNotEqual(calibration_signature(identical_values), calibration_signature(mcc))
        alias, _ = self.export('rss', parameters=mce['parameters'], optimisation=self.optimise('rss'))
        self.assertEqual(alias['calibration_id'], mce['calibration_id'])

    def test_conflicting_optimisation_metadata_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'same amplitude settings'):
            self.export('mcc_harmonic', optimisation=self.optimise('mce_harmonic'))
        self.assertFalse(list(self.folder.rglob('*.json')))

    def test_legacy_record_requires_verified_formulation_and_other_provenance(self):
        # Read the actual historical record rather than assigning legacy meaning
        # to an arbitrary record with a missing metadata field.
        historical, _, _ = load_calibration(data=self.data, material=self.material, model='FIN',
            settings=curve_settings(), folder=ROOT / 'Calibrations')
        self.assertNotIn('amplitude_settings', historical)
        for algorithm in ('method_default', 'mce_harmonic', 'rss'):
            actual, _, _ = load_calibration(data=self.data, material=self.material, model='FIN',
                settings=curve_settings(), folder=ROOT / 'Calibrations', shear_amplitude_algorithm=algorithm)
            self.assertEqual(actual['calibration_id'], historical['calibration_id'])
        with self.assertRaisesRegex(ValueError, 'No compatible.*mcc_harmonic'):
            load_calibration(data=self.data, material=self.material, model='FIN', settings=curve_settings(),
                folder=ROOT / 'Calibrations', shear_amplitude_algorithm='mcc_harmonic')
        changed = copy.deepcopy(historical)
        changed['curve_settings'] = self.settings
        changed['formulation_fingerprints']['FIN'] = '0'*64
        save_record(changed, self.folder)
        with self.assertRaisesRegex(ValueError, 'No compatible'):
            self.load()
        changed['calibration_id'] += '_provenance'
        changed['formulation_fingerprints']['FIN'] = formulation_fingerprint('FIN')
        changed['implementation_revision'] = 'unknown'
        save_record(changed, self.folder)
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            self.load(calibration_id=changed['calibration_id'])

    def test_newest_compatible_algorithm_selected_before_date_or_id(self):
        mce, mce_path = self.export('mce_harmonic')
        mcc, _ = self.export('mcc_harmonic', parameters={'k_FI': 2.})
        for algorithm, expected in [('method_default', mce), ('mce_harmonic', mce), ('mcc_harmonic', mcc)]:
            self.assertEqual(self.load(algorithm)[0]['calibration_id'], expected['calibration_id'])
        mce_path.touch()
        self.assertEqual(self.load('mcc_harmonic')[0]['calibration_id'], mcc['calibration_id'])
        for request, wrong in [('method_default', mcc), ('mce_harmonic', mcc), ('mcc_harmonic', mce)]:
            with self.assertRaisesRegex(ValueError, 'incompatible'):
                self.load(request, calibration_id=wrong['calibration_id'])
        newer_mce = copy.deepcopy(mce)
        newer_mce['calibration_id'] += '_newer'
        newer_mce['created_at'] = '2099-01-01T00:00:00+00:00'
        newer_mce['curves']['FIN']['fit']['A'] *= 1.01
        save_record(newer_mce, self.folder)
        self.assertEqual(self.load()[0]['calibration_id'], newer_mce['calibration_id'])
        self.assertEqual(self.load('mcc_harmonic')[0]['calibration_id'], mcc['calibration_id'])

    def test_unknown_definition_and_implementation_are_rejected(self):
        record, path = self.export('mcc_harmonic')
        for field, invalid in [('definition_version', 'harmonic-shear-future'),
                               ('implementation_fingerprint', '0'*64)]:
            changed = copy.deepcopy(record)
            changed['calibration_id'] += '_'+field
            changed['amplitude_settings']['FIN'][field] = invalid
            save_record(changed, self.folder)
            with self.assertRaisesRegex(ValueError, 'incompatible'):
                self.load('mcc_harmonic', calibration_id=changed['calibration_id'])
        # Removing metadata from an alternative record cannot turn it into legacy MCE.
        stripped = copy.deepcopy(record)
        stripped['calibration_id'] += '_stripped'
        stripped.pop('amplitude_settings')
        save_record(stripped, self.folder)
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            self.load(calibration_id=stripped['calibration_id'])
        self.assertEqual(read_record(path), record)

    def test_relevant_dependency_changes_reject_only_dependent_records(self):
        self.export('mcc_harmonic')
        mce, _ = self.export(models=['FIN', 'BP'])
        old_read = Path.read_text
        for relative in ('fatigue/eval/findley_calibration.py', 'fatigue/models/cp_methods/fin_harmonic.py',
                         'fatigue/models/utils/shear_amplitude.py'):
            target = ROOT / relative

            def changed_read(path, *args, **kwargs):
                content = old_read(path, *args, **kwargs)
                return content+'\n# simulated numerical dependency change' if path == target else content

            with patch.object(Path, 'read_text', changed_read):
                with self.assertRaisesRegex(ValueError, 'No compatible'):
                    self.load('mcc_harmonic')
                self.assertEqual(self.load()[0]['calibration_id'], mce['calibration_id'])
                self.assertEqual(self.load(model='BP')[0]['calibration_id'], mce['calibration_id'])
        # Even an unrelated curve in a valid multi-method record remains usable
        # when the Findley definition version is no longer compatible.
        changed = copy.deepcopy(mce)
        changed['calibration_id'] += '_future'
        changed['amplitude_settings']['FIN']['definition_version'] = 'future'
        save_record(changed, self.folder)
        self.assertEqual(self.load(model='BP', calibration_id=changed['calibration_id'])[0], changed)
        old_text = Path.read_text

        def changed_base(path, *args, **kwargs):
            content = old_text(path, *args, **kwargs)
            return content+'\n# changed Findley equation' if path == ROOT / 'fatigue/models/cp_methods/fin.py' else content

        with patch.object(Path, 'read_text', changed_base):
            for algorithm in ('method_default', 'mcc_harmonic'):
                with self.assertRaisesRegex(ValueError, 'No compatible'):
                    self.load(algorithm)
            self.assertEqual(self.load(model='BP')[0]['calibration_id'], changed['calibration_id'])

    def test_invalid_metadata_is_rejected_without_rewriting_records(self):
        record, _ = self.export()
        for field, invalid in [('algorithm', 'method_default'), ('algorithm', 'rss'),
                               ('evaluation_path', 'unknown'), ('implementation_fingerprint', 'broken')]:
            changed = copy.deepcopy(record)
            changed['amplitude_settings']['FIN'][field] = invalid
            with self.assertRaisesRegex(ValueError, 'Invalid calibration record'):
                validate_record(changed)

    def test_explicit_requests_check_original_histories_not_extractor_fallback(self):
        changed = copy.deepcopy(self.data)
        for case in changed[self.material]['cases'].values():
            case.pop('harmonics', None)
        self.optimise(data=changed)  # The established default fallback remains available.
        self.export(data=changed)
        for algorithm in ('mcc_harmonic', 'mce_harmonic'):
            with self.assertRaisesRegex(ValueError, 'AISI316L/FIN case .*S_sin'):
                self.optimise(algorithm, changed)
            with self.assertRaisesRegex(ValueError, 'AISI316L/FIN case .*S_sin'):
                self.export(algorithm, data=changed)
        case = copy.deepcopy(next(iter(self.data[self.material]['cases'].values())))
        for bad in (None, np.zeros((2, 2)), np.full((3, 3), np.nan), np.eye(3, dtype=complex)):
            case['harmonics']['S_cos'] = bad
            with self.assertRaisesRegex(ValueError, 'S_cos'):
                require_stress_harmonics(case, self.material, 0)

    def test_script0_batch_option_skips_bad_material_and_unsupported_method(self):
        data = {self.material: self.data[self.material], 'missing-history': copy.deepcopy(self.data[self.material])}
        for case in data['missing-history']['cases'].values():
            case.pop('harmonics', None)
        status_path = self.folder / 'status.json'
        with patch.object(self.script['exp'], 'import_experimental_data_grouped_by_material', return_value=data), \
             warnings.catch_warnings(record=True) as caught, contextlib.redirect_stdout(io.StringIO()):
            paths = self.script['main'](['--models', 'FIN', 'FS', '--n1', '3', '--n2', '6',
                '--n-grid', '3', '--n-refine', '1', '--plane-stride', '1',
                '--shear-amplitude-algorithm', 'mcc_harmonic', '--calibrations-dir', str(self.folder),
                '--status-file', str(status_path)])
        self.assertEqual(len(paths), 1)
        self.assertTrue(caught)
        outcomes = json.loads(status_path.read_text())
        self.assertEqual(sum(o['status'] == 'saved' for o in outcomes), 1)
        self.assertEqual(sum(o['status'] == 'skipped' for o in outcomes), 3)
        reasons = ' '.join(' '.join(o['reasons']) for o in outcomes)
        self.assertIn('missing-history/FIN', reasons)
        self.assertIn('only for FIN', reasons)
        self.assertEqual(read_record(paths[0])['amplitude_settings']['FIN']['algorithm'], 'mcc_harmonic')

    def test_coefficient_history_failure_is_skipped_without_stopping_batch(self):
        bad = copy.deepcopy(self.data[self.material])
        # Axial curve preflight succeeds; only a selected torsion history is absent.
        torsion = next(case for case in bad['cases'].values()
                       if case['meta']['test_status'] == 'failure'
                       and self.script['_uniaxial_torsion_filter'](case)[0])
        torsion.pop('harmonics')
        data = {'missing-torsion': bad, self.material: self.data[self.material]}
        status_path = self.folder / 'coefficient-status.json'
        with patch.object(self.script['exp'], 'import_experimental_data_grouped_by_material', return_value=data), \
             self.assertWarnsRegex(RuntimeWarning, 'missing-torsion/FIN'), contextlib.redirect_stdout(io.StringIO()):
            paths = self.script['main'](['--models', 'FIN', '--n1', '3', '--n2', '6', '--n-grid', '3',
                '--n-refine', '1', '--shear-amplitude-algorithm', 'mcc_harmonic',
                '--calibrations-dir', str(self.folder), '--status-file', str(status_path)])
        self.assertEqual(len(paths), 1)
        self.assertEqual([o['status'] for o in json.loads(status_path.read_text())], ['skipped', 'saved'])

    def test_runouts_are_ignored_and_runout_only_cannot_calibrate(self):
        changed = copy.deepcopy(self.data)
        for case in changed[self.material]['cases'].values():
            if case['meta']['test_status'] == 'runout':
                case.pop('harmonics', None)
        original, _ = self.export('mcc_harmonic')
        repeated, _ = self.export('mcc_harmonic', data=changed)
        self.assertEqual(original['calibration_id'], repeated['calibration_id'])
        self.assertEqual(self.optimise('mcc_harmonic')['FI'], self.optimise('mcc_harmonic', changed)['FI'])
        for case in changed[self.material]['cases'].values():
            case['meta']['test_status'] = 'runout'
        ready = calibration_readiness(changed, self.material, 'FIN', shear_amplitude_algorithm='mcc_harmonic')
        self.assertFalse(ready['can_calibrate'])
        self.assertIn('distinct observed', ' '.join(ready['reasons']))

    def test_cli_reuse_requires_matching_algorithm(self):
        mcc, _ = self.export('mcc_harmonic')
        args = ['--material', self.material, '--models', 'FIN', '--n1', '3', '--n2', '6',
                '--reuse-calibration', mcc['calibration_id'], '--calibrations-dir', str(self.folder)]
        with patch.object(self.script['exp'], 'import_experimental_data_grouped_by_material', return_value=self.data), \
             self.assertWarnsRegex(RuntimeWarning, 'incompatible.*mce_harmonic'), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.script['main'](args), [])
        with patch.object(self.script['exp'], 'import_experimental_data_grouped_by_material', return_value=self.data), \
             contextlib.redirect_stdout(io.StringIO()):
            selected = args+['--shear-amplitude-algorithm', 'mcc_harmonic']
            first, second = self.script['main'](selected), self.script['main'](selected)
        self.assertEqual(first, second)
        self.assertEqual(read_record(first[0])['parameters'], mcc['parameters'])

    def test_production_script1_never_selects_newer_or_explicit_mcc(self):
        mce, _ = self.export()
        runner = runpy.run_path(str(ROOT / '1_run_material.py'))
        globals_ = runner['main'].__globals__
        results = self.folder / 'results'
        globals_.update(MATERIAL_NAME=self.material, MODEL_NAME='FIN', CALIBRATIONS_DIR=str(self.folder),
                        RESULTS_DIR=str(results), MAKE_PLOTS=False, DCMESH_N1=3, DCMESH_N2=6)
        with contextlib.redirect_stdout(io.StringIO()):
            runner['main'](self.data)
        output = next(results.glob('*.csv'))
        baseline = pd.read_csv(output)
        mcc, _ = self.export('mcc_harmonic', parameters={'k_FI': 2.})
        with contextlib.redirect_stdout(io.StringIO()):
            runner['main'](self.data)
        pd.testing.assert_frame_equal(pd.read_csv(output), baseline, check_exact=True)
        self.assertEqual(set(baseline['Calibration_id']), {mce['calibration_id']})
        self.assertEqual(assess_eligibility(data=self.data, material=self.material, method='FIN_ext',
            settings=self.settings, folder=self.folder)['calibration_id'], mce['calibration_id'])
        globals_.update(CALIBRATION_ID=mcc['calibration_id'], RESULTS_DIR=str(self.folder / 'rejected'))
        with self.assertWarnsRegex(RuntimeWarning, 'mce_harmonic'), contextlib.redirect_stdout(io.StringIO()):
            status = runner['main'](self.data)
        self.assertFalse(status['prediction_available'])
        self.assertFalse(list((self.folder / 'rejected').glob('*.csv')))

    def test_only_mcc_produces_controlled_mce_compatibility_error(self):
        self.export('mcc_harmonic')
        with self.assertRaisesRegex(ValueError, 'No compatible.*mce_harmonic'):
            self.load()
        result = assess_eligibility(data=self.data, material=self.material, method='FIN',
                                    settings=self.settings, folder=self.folder)
        self.assertFalse(result['prediction_available'])
        self.assertIn('mce_harmonic', ' '.join(result['reasons']))


if __name__ == '__main__':
    unittest.main()
