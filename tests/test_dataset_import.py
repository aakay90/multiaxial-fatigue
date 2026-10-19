"""Workbook schema and missing-data regression checks."""
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
from openpyxl import load_workbook

from fatigue.imp.experimental_data import import_experimental_data_grouped_by_material
from fatigue.imp.schema import material_id, dataset_column
from fatigue.eval.calibration_store import input_fingerprint

ROOT = Path(__file__).resolve().parents[1]


class DatasetImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.path = self.folder / '8_AISI316L.xlsx'
        shutil.copy(ROOT / 'Experimental_Data/archive/pre-dataset-migration/AISI316L.xlsx', self.path)

    def test_filename_prefix_does_not_change_calibration_identity(self):
        baseline = import_experimental_data_grouped_by_material(ROOT / 'Experimental_Data/archive/pre-dataset-migration')
        current = import_experimental_data_grouped_by_material(self.folder)
        self.assertEqual(input_fingerprint(baseline, 'AISI316L'), input_fingerprint(current, 'AISI316L'))
        self.assertEqual(material_id('2_CX18'), 'CX18')
        self.assertEqual(material_id('Ti6Al4V_andrea_(AXIAL)'), 'Ti6Al4V_andrea_(AXIAL)')

    def test_header_mapping_is_explicit_and_position_independent(self):
        self.assertEqual(dataset_column(['Mean AXIAL load (N)', 'Mean AXIAL stress  (MPa)'], 'mean_ax'),
                         'Mean AXIAL stress  (MPa)')
        with self.assertRaises(KeyError):
            dataset_column(['Mean AXIAL load (N)'], 'mean_ax')

    def test_missing_elastic_property_preserves_stress_and_runouts(self):
        w = load_workbook(self.path)
        s = w['Summary']
        for row in s:
            if str(row[0].value).lower() == 'average':
                row[5].value = 'Null'
        w.save(self.path)
        block = import_experimental_data_grouped_by_material(self.folder)['AISI316L']
        self.assertIsNone(block['material']['nu'])
        self.assertEqual(len(block['cases']), 44)
        self.assertTrue(any(c['meta']['test_status'] == 'runout' for c in block['cases'].values()))
        case = next(iter(block['cases'].values()))
        self.assertTrue(np.isfinite(case[1][1]['stress']).all())
        self.assertTrue(np.isnan(case[1][1]['strain']).all())

    def test_reordered_stress_columns_preserve_imported_tensors(self):
        before = import_experimental_data_grouped_by_material(self.folder)['AISI316L']
        w = load_workbook(self.path, data_only=True)
        sheet = w['Dataset']
        a, b = 1, 22
        for row in range(1, sheet.max_row + 1):
            first, second = sheet.cell(row, a).value, sheet.cell(row, b).value
            sheet.cell(row, a).value, sheet.cell(row, b).value = second, first
        w.save(self.path)
        after = import_experimental_data_grouped_by_material(self.folder)['AISI316L']
        for cid in before['cases']:
            np.testing.assert_array_equal(before['cases'][cid][1][1]['stress'], after['cases'][cid][1][1]['stress'])

    def test_axial_phase_is_the_reference(self):
        w = load_workbook(self.path)
        s = w['Dataset']
        c = s.max_column + 1
        s.cell(1, c, 'Phase AXIAL load (°)')
        for row in range(2, s.max_row + 1):
            s.cell(row, c, 30)
        w.save(self.path)
        block = import_experimental_data_grouped_by_material(self.folder)['AISI316L']
        case = next(iter(block['cases'].values()))
        self.assertEqual(case['meta']['phase_rad_deg'], -30)
        self.assertEqual(case['meta']['phase_tor_deg'], -30)
        self.assertEqual(block['source']['format'], 'revised')


@unittest.skipUnless((ROOT / 'Experimental_Data/6_42CrMo4_QT.xlsx').exists(),
                     'Revised workbooks await authorised publication; synthetic schema tests still run')
class RevisedCollectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = import_experimental_data_grouped_by_material(ROOT / 'Experimental_Data')

    def test_all_materials_import_without_fabricating_missing_properties(self):
        self.assertEqual(len(self.data), 13)  # twelve revised files plus retained Al7075_T6
        self.assertEqual(len(self.data['GGG60']['cases']), 27)
        self.assertTrue(all(c['meta']['test_status'] == 'runout' for c in self.data['GGG60']['cases'].values()))
        self.assertIsNone(self.data['25CrMo4']['material']['nu'])
        self.assertTrue(self.data['CX18']['identity_issues'])
        self.assertTrue(self.data['Ti6Al4V']['identity_issues'])
        self.assertTrue(self.data['AISI316L']['property_issues']['Sigm1'])
        self.assertFalse(self.data['En3B']['cases'])
        self.assertTrue(self.data['En3B']['scope_exclusions'])

    def test_equivalent_loading_rows_preserve_stresses_and_use_revised_elastic_properties(self):
        old = import_experimental_data_grouped_by_material(ROOT / 'Experimental_Data/archive/pre-dataset-migration')
        previous = old['42CrMo4_QT']['cases']
        current = self.data['42CrMo4_QT']['cases']
        matched = 0
        for case in current.values():
            matches = [c for c in previous.values()
                       if c['meta']['specimen_id'] == case['meta']['specimen_id']
                       and c['meta']['Nf_cycles'] == case['meta']['Nf_cycles']]
            if len(matches) != 1:
                continue
            for step in (1, 2):
                np.testing.assert_array_equal(case[1][step]['stress'], matches[0][1][step]['stress'])
                stress = case[1][step]['stress']
                props = self.data['42CrMo4_QT']['material']
                E, nu = props['E_MPa'], props['nu']
                expected = ((1 + nu) * stress - nu * np.trace(stress) * np.eye(3)) / E
                np.testing.assert_allclose(case[1][step]['strain'], expected, rtol=1e-15, atol=1e-18)
            matched += 1
        self.assertGreater(matched, 20)
