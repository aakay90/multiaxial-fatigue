"""Every calibration record kept under Calibrations/ loads through the pipeline loader.

The records come from the upstream calibration history and are kept unchanged. Each must give
constants for the pipeline, and a Findley amplitude setting, when it has one, must be the production
MCE path (the only one the pipeline accepts).
"""

from pathlib import Path

import pytest

from multifat.cli.pipeline import load_constants

ROOT = Path(__file__).resolve().parents[1]
RECORDS = sorted(p for p in (ROOT / "Calibrations").glob("*/*.json"))


def test_records_are_present():
    assert RECORDS, "Calibrations/ holds no records"


@pytest.mark.parametrize("record", RECORDS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_record_loads_through_the_pipeline_loader(record):
    constants, origin = load_constants(record, record.parent.name)
    assert constants, f"{record.name}: no constants"
    assert all(isinstance(v, float) for v in constants.values())
    assert origin["kind"]


@pytest.mark.parametrize("record", RECORDS, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_findley_amplitude_metadata_is_read(record):
    import json

    payload = json.loads(record.read_text(encoding="utf-8"))
    settings = (payload.get("amplitude_settings") or {}).get("FIN")
    if settings is None:
        # Legacy records predate the amplitude metadata; they are the MCE production path.
        return
    assert settings["algorithm"] == "mce_harmonic"
    # The loader accepts the record only for the production path
    load_constants(record, record.parent.name)
