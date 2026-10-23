"""Declarative corrections applied to as-supplied experimental workbooks.

An overlay file ``imp/overlay_files/<stem>.overlay.json`` (shipped with the package) lists the
cell-level changes that turn a workbook as supplied by its source into the revised workbook used by
this project. Overlays are found by content: a workbook gets the overlay whose ``base_sha256`` equals
its SHA-256, wherever the file lives and whatever it is called, so a copy keeps its corrections and an
edited file gets none. Every operation checks the value it replaces before writing. The importer
applies the overlay to the loaded worksheet, so everything downstream sees the same data as it does
from the revised workbook.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

OVERLAY_DIR = Path(__file__).with_name("overlay_files")
SCHEMA_VERSION = 1


class OverlayError(ValueError):
    """An overlay operation does not match the workbook it is applied to."""


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def _overlays_by_base_hash() -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in sorted(OVERLAY_DIR.glob("*.overlay.json")):
        base = json.loads(path.read_text(encoding="utf-8"))["base_sha256"]
        if base in index:
            raise OverlayError(f"{path.name} and {index[base].name} name the same base file")
        index[base] = path
    return index


def overlay_path(workbook: str | Path) -> Path | None:
    """The overlay written against this exact file content, or None."""
    return _overlays_by_base_hash().get(sha256_file(workbook))


def load_overlay(path: str | Path) -> dict[str, Any]:
    overlay = json.loads(Path(path).read_text(encoding="utf-8"))
    if overlay.get("schema_version") != SCHEMA_VERSION:
        raise OverlayError(f"{path}: unsupported schema_version {overlay.get('schema_version')!r}")
    return overlay


def _same(current: Any, expected: Any) -> bool:
    if isinstance(current, bool) or isinstance(expected, bool):
        return current is expected
    if isinstance(current, (int, float)) and isinstance(expected, (int, float)):
        return float(current) == float(expected)
    return current == expected


def _column_index(ws, header: str) -> int:
    for cell in ws[1]:
        if cell.value == header:
            return cell.column
    raise OverlayError(f"{ws.title}: no column headed {header!r}")


def _dataset_row(ws, authors: str, specimen: str) -> int:
    rows = [
        r
        for r in range(2, ws.max_row + 1)
        if ws.cell(r, 1).value == authors and ws.cell(r, 4).value == specimen
    ]
    if len(rows) != 1:
        raise OverlayError(f"Dataset: {len(rows)} rows match ({authors!r}, {specimen!r}), need 1")
    return rows[0]


def _apply_one(wb, op: dict[str, Any]) -> None:
    kind = op["op"]
    if kind == "set_summary":
        ws = wb["Summary"]
        cell = ws[f"{op['column']}{op['row']}"]
        if not _same(cell.value, op["from"]):
            raise OverlayError(
                f"Summary!{op['column']}{op['row']} is {cell.value!r}, expected {op['from']!r}"
            )
        cell.value = op["to"]
    elif kind == "set_case":
        ws = wb["Dataset"]
        row = _dataset_row(ws, op["authors"], op["specimen"])
        cell = ws.cell(row, _column_index(ws, op["field"]))
        if not _same(cell.value, op["from"]):
            raise OverlayError(
                f"Dataset row {row} ({op['specimen']}) {op['field']!r} is {cell.value!r}, "
                f"expected {op['from']!r}"
            )
        cell.value = op["to"]
    elif kind == "add_case":
        ws = wb["Dataset"]
        row = op["row"]
        if any(ws.cell(row, c).value is not None for c in range(1, ws.max_column + 1)):
            raise OverlayError(f"Dataset row {row} is not empty; add_case needs a free row")
        for header, value in op["values"].items():
            ws.cell(row, _column_index(ws, header)).value = value
    else:
        raise OverlayError(f"unknown overlay operation {kind!r}")


def apply_overlay_to_workbook(wb, workbook: str | Path) -> dict[str, Any] | None:
    """Apply the overlay of ``workbook`` to the loaded ``wb`` in memory.

    Returns the overlay identity recorded in provenance, or None when there is no overlay for
    this file or the file is not the base it was written against.
    """
    path = overlay_path(workbook)
    if path is None:
        return None
    overlay = load_overlay(path)
    for op in overlay["operations"]:
        _apply_one(wb, op)
    return {
        "name": path.name,
        "sha256": sha256_file(path),
        "base_sha256": overlay["base_sha256"],
        "operations": len(overlay["operations"]),
        "expected_fingerprint": overlay["expected_fingerprint"],
    }
