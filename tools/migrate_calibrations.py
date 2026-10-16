"""Move legacy workbook coefficients to JSON without re-optimising them.

Run from the repository root. Original workbook bytes are archived first.
Failure-only master curves are reproduced using the transferred coefficients.
"""
import argparse
import os
from pathlib import Path
import sys
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED
from xml.dom import minidom
from posixpath import normpath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openpyxl import load_workbook
from openpyxl.utils.cell import get_column_letter, range_boundaries
from fatigue.imp import experimental_data as exp
from fatigue.eval.calibration import export_calibration
from fatigue.eval.calibration_store import curve_settings
from fatigue.models.registry import _available_cp_methods, _available_direct_models

HEADERS = {"k fs (-)": "k_FS", "k fi (-)": "k_FI", "l_li": "L_LI",
           "k_mgse": "k_MGSE", "a_mswt": "a_MSWT", "alpha_w": "alpha_w", "xi_zhu": "xi_ZHU"}


def legacy_columns(workbook):
    sheet = workbook["Summary"]
    columns = {cell.column: HEADERS[str(cell.value).strip().lower()]
               for cell in sheet[1] if str(cell.value).strip().lower() in HEADERS}
    row = next((row[0].row for row in sheet.iter_rows() if str(row[0].value).strip().lower() == "average"), None)
    if row is None:
        raise ValueError("Summary has no Average row")
    if columns:
        occupied = [c.column for c in sheet[1] if c.value is not None]
        if set(columns) != set(range(min(columns), max(occupied) + 1)):
            raise ValueError("Legacy coefficients must form the trailing Summary block; this workbook needs a reviewed migration")
    try:
        return columns, {name: float(sheet.cell(row, col).value) for col, name in columns.items()}
    except (TypeError, ValueError) as exc:
        raise ValueError("Legacy coefficient caches are missing or invalid; recalculate the original workbook before migration") from exc


def migrated_workbook(file, target, columns):
    """Edit only Summary cells/table definitions, preserving formula caches."""
    with ZipFile(file) as original, ZipFile(target, "w") as updated:
        book = minidom.parseString(original.read("xl/workbook.xml"))
        rid = next(s.getAttribute("r:id") for s in book.getElementsByTagName("sheet")
                   if s.getAttribute("name") == "Summary")
        rels = minidom.parseString(original.read("xl/_rels/workbook.xml.rels"))
        location = next(r.getAttribute("Target") for r in rels.getElementsByTagName("Relationship")
                        if r.getAttribute("Id") == rid)
        sheet_path = location.lstrip("/") if location.startswith("/") else normpath("xl/" + location)
        letters = {get_column_letter(c) for c in columns}
        for item in original.infolist():
            content = original.read(item.filename)
            if item.filename == sheet_path:
                doc = minidom.parseString(content)
                for cell in list(doc.getElementsByTagName("c")):
                    col = "".join(c for c in cell.getAttribute("r") if c.isalpha())
                    if col in letters:
                        cell.parentNode.removeChild(cell)
                content = doc.toxml(encoding="utf-8")
            elif item.filename.startswith("xl/tables/") and item.filename.endswith(".xml"):
                doc = minidom.parseString(content)
                removed = False
                for column in list(doc.getElementsByTagName("tableColumn")):
                    if column.getAttribute("name").strip().lower() in HEADERS:
                        parent = column.parentNode
                        parent.removeChild(column)
                        parent.setAttribute("count", str(len(parent.getElementsByTagName("tableColumn"))))
                        removed = True
                if removed:
                    table = doc.documentElement
                    left, top, right, bottom = range_boundaries(table.getAttribute("ref"))
                    reference = f"{get_column_letter(left)}{top}:{get_column_letter(right-len(columns))}{bottom}"
                    table.setAttribute("ref", reference)
                    for filt in doc.getElementsByTagName("autoFilter"):
                        filt.setAttribute("ref", reference)
                    content = doc.toxml(encoding="utf-8")
            updated.writestr(item, content)


def migrate(folder="Experimental_Data", calibrations="Calibrations"):
    folder = Path(folder)
    files = sorted(folder.glob("*.xlsx"))
    pending = []
    for file in files:
        workbook = load_workbook(file, data_only=True)
        cols, params = legacy_columns(workbook)
        workbook.close()
        if cols:
            pending.append((file, cols, params))
    if not pending:
        print("No legacy coefficient columns remain")
        return []
    archive = folder / "archive" / "pre-json-calibration.zip"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        with ZipFile(archive) as backup:
            for file, _, _ in pending:
                if backup.read(file.name) != file.read_bytes():
                    raise ValueError(f"Existing archive differs from {file}; preserve a separate backup before migration")
    else:
        with tempfile.NamedTemporaryFile(dir=archive.parent, delete=False) as handle:
            temp = Path(handle.name)
        try:
            with ZipFile(temp, "w", ZIP_DEFLATED) as backup:
                for file in files:
                    backup.writestr(file.name, file.read_bytes())
            os.link(temp, archive)
        finally:
            temp.unlink(missing_ok=True)
    data = exp.import_experimental_data_grouped_by_material(folder)
    models = list(_available_cp_methods()) + list(_available_direct_models())
    paths = []
    for file, columns, parameters in pending:
        data[file.stem]["source"]["original_archive"] = str(archive)
        data[file.stem]["source"]["original_archive_member"] = file.name
        _, record_path = export_calibration(data=data, material=file.stem, models=models,
            parameters=parameters, settings=curve_settings(), folder=calibrations,
            procedure="Legacy workbook migration, no coefficient re-optimisation",
            parameter_origin="Transferred legacy workbook values; original fitting settings unverified")
        workbook = load_workbook(file)
        original_dataset = list(workbook["Dataset"].values)
        original_inputs = [tuple(row[:11]) for row in workbook["Summary"].values]
        with tempfile.NamedTemporaryFile(dir=file.parent, suffix=".xlsx", delete=False) as handle:
            temporary = Path(handle.name)
        try:
            migrated_workbook(file, temporary, columns)
            workbook.close()
            check = load_workbook(temporary)
            assert list(check["Dataset"].values) == original_dataset, "Experimental cells changed"
            assert [tuple(row[:11]) for row in check["Summary"].values] == original_inputs, "Material inputs changed"
            check.close()
            os.replace(temporary, file)
        finally:
            temporary.unlink(missing_ok=True)
        paths.append(record_path)
        print(f"Migrated {file.name} to {record_path}", flush=True)
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-folder", default="Experimental_Data")
    parser.add_argument("--calibrations-dir", default="Calibrations")
    args = parser.parse_args()
    migrate(args.data_folder, args.calibrations_dir)
