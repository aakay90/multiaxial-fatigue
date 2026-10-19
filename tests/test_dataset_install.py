"""Reproducible installation using only already public workbook content."""
import contextlib
import io
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'Experimental_Data/archive/pre-dataset-migration'
INSTALL = runpy.run_path(str(ROOT / 'tools/install_revised_dataset.py'))['install']


class DatasetInstallTests(unittest.TestCase):
    def test_dry_run_install_and_conflict_preserve_original_bytes(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            folder = Path(folder)
            active = folder / 'data'
            active.mkdir()
            shutil.copy(BASELINE / 'AISI316L.xlsx', active / 'AISI316L.xlsx')
            shutil.copy(BASELINE / 'Ti6Al4V_andrea_(AXIAL).xlsx', active / 'Ti6Al4V_andrea_(AXIAL).xlsx')
            shutil.copy(BASELINE / 'Al7075_T6.xlsx', active / 'Al7075_T6.xlsx')
            archive = folder / 'inputs.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.write(BASELINE / 'AISI316L.xlsx', 'New_Exp_data/8_AISI316L.xlsx')
                z.writestr('New_Exp_data/../../unexpected.xlsx', 'not a workbook')
            before = (active / 'AISI316L.xlsx').read_bytes()
            INSTALL(archive, active)
            self.assertEqual((active / 'AISI316L.xlsx').read_bytes(), before)
            self.assertFalse((active / '8_AISI316L.xlsx').exists())
            INSTALL(archive, active, apply=True)
            self.assertEqual((active / '8_AISI316L.xlsx').read_bytes(), before)
            self.assertFalse((active / 'AISI316L.xlsx').exists())
            self.assertTrue((active / 'Al7075_T6.xlsx').exists())
            self.assertTrue((active / 'archive/pre-dataset-migration/Ti6Al4V_andrea_(AXIAL).xlsx').exists())
            self.assertFalse((folder / 'unexpected.xlsx').exists())
            # A conflicting archived snapshot stops before changing an active file.
            shutil.copy(BASELINE / 'Ti6Al4V_andrea_(AXIAL).xlsx', active / 'Ti6Al4V_andrea_(AXIAL).xlsx')
            (active / 'archive/pre-dataset-migration/Ti6Al4V_andrea_(AXIAL).xlsx').write_bytes(b'other history')
            with self.assertRaises(FileExistsError):
                INSTALL(archive, active, apply=True)
            self.assertTrue((active / 'Ti6Al4V_andrea_(AXIAL).xlsx').exists())
