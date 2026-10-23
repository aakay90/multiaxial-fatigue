"""tools/regression_snapshot.py: compare on the base snapshot's columns, data-folder option."""

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "regression_snapshot", ROOT / "tools/regression_snapshot.py"
)
snap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(snap)


def _snapshot(path: Path, csv_text: str) -> Path:
    (path / "runs").mkdir(parents=True)
    f = path / "runs" / "FS_X.csv"
    f.write_text(csv_text, encoding="utf-8")
    files = {"runs/FS_X.csv": hashlib.sha256(f.read_bytes()).hexdigest()}
    (path / "manifest.json").write_text(json.dumps({"codes": {}, "files": files}))
    return path


def test_compare_ignores_appended_columns(tmp_path):
    base = _snapshot(tmp_path / "a", "Material,Nf_exp\nX,100\nX,200\n")
    new = _snapshot(tmp_path / "b", "Material,Nf_exp,Test_status\nX,100,failure\nX,200,runout\n")
    assert snap.compare(base, new) == 0


def test_compare_flags_changed_base_column(tmp_path):
    base = _snapshot(tmp_path / "a", "Material,Nf_exp\nX,100\n")
    new = _snapshot(tmp_path / "b", "Material,Nf_exp,Test_status\nX,101,failure\n")
    assert snap.compare(base, new) == 1


def test_compare_flags_added_rows(tmp_path):
    base = _snapshot(tmp_path / "a", "Material,Nf_exp\nX,100\n")
    new = _snapshot(tmp_path / "b", "Material,Nf_exp\nX,100\nX,300\n")
    assert snap.compare(base, new) == 1


def test_material_args_from_data_folder(tmp_path):
    (tmp_path / "6_A.xlsx").write_bytes(b"")
    (tmp_path / "B.xlsx").write_bytes(b"")
    assert snap.material_args(tmp_path) == [str(tmp_path / "6_A.xlsx"), str(tmp_path / "B.xlsx")]


def test_calibrate_main_takes_data_folder(tmp_path):
    import pytest

    from multifat.cli import calibrate

    with pytest.raises(FileNotFoundError, match=tmp_path.name):
        calibrate.main(["--data-folder", str(tmp_path)])
