"""Dataset tools ported from upstream 904c619 / 52b061b (A. Chiocca)."""

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from workbook_factory import revised_row, write_revised_workbook

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("tool", ["install_revised_dataset.py", "audit_dataset_migration.py"])
def test_tool_help(tool):
    out = subprocess.run(
        [sys.executable, str(ROOT / "tools" / tool), "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert out.returncode == 0, out.stderr


def test_install_dry_run_and_apply(tmp_path):
    src = write_revised_workbook(
        tmp_path / "6_Synth.xlsx",
        [revised_row({"Number of cycles to failure": n}) for n in (1e5, 1e6)],
    )
    archive = tmp_path / "exp_data.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(src, "New_Exp_data/6_Synth.xlsx")
    dest = tmp_path / "Experimental_Data"
    dest.mkdir()
    old = write_revised_workbook(dest / "Synth.xlsx", [revised_row()])
    old_bytes = old.read_bytes()
    tool = [
        sys.executable,
        str(ROOT / "tools/install_revised_dataset.py"),
        str(archive),
        "--destination",
        str(dest),
    ]
    dry = subprocess.run(tool, capture_output=True, text=True, cwd=ROOT)
    assert dry.returncode == 0, dry.stderr and "Dry run" in dry.stdout
    assert sorted(p.name for p in dest.glob("*.xlsx")) == ["Synth.xlsx"]
    done = subprocess.run(tool + ["--apply"], capture_output=True, text=True, cwd=ROOT)
    assert done.returncode == 0, done.stderr
    assert sorted(p.name for p in dest.glob("*.xlsx")) == ["6_Synth.xlsx"]
    assert (dest / "6_Synth.xlsx").read_bytes() == src.read_bytes()
    assert (dest / "archive/pre-dataset-migration/Synth.xlsx").read_bytes() == old_bytes


def test_install_refuses_to_replace_an_edited_workbook(tmp_path):
    """Minor: --apply must not overwrite an active workbook of the same name edited since."""
    src = write_revised_workbook(tmp_path / "6_Synth.xlsx", [revised_row()])
    archive = tmp_path / "exp_data.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.write(src, "New_Exp_data/6_Synth.xlsx")
    dest = tmp_path / "Experimental_Data"
    dest.mkdir()
    edited = write_revised_workbook(dest / "6_Synth.xlsx", [revised_row({"Specimen name": "E"})])
    before = edited.read_bytes()
    tool = [sys.executable, str(ROOT / "tools/install_revised_dataset.py"), str(archive),
            "--destination", str(dest), "--apply"]  # fmt: skip
    out = subprocess.run(tool, capture_output=True, text=True, cwd=ROOT)
    assert out.returncode != 0 and "--replace-edited" in (out.stdout + out.stderr)
    assert edited.read_bytes() == before
    ok = subprocess.run(tool + ["--replace-edited"], capture_output=True, text=True, cwd=ROOT)
    assert ok.returncode == 0, ok.stderr
