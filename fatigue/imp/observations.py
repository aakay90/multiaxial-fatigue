"""Experimental status and failure-only selection for calibration."""
import math


def test_status(value):
    """Interpret the workbook run-out flag without a cycle-count threshold."""
    text = str(value).strip().lower()
    if text in {"no", "false", "0", "0.0", "failure", "failed"}:
        return "failure"
    if text in {"yes", "true", "1", "1.0", "runout", "run-out"}:
        return "runout"
    return "unknown"


def is_failure(case):
    """Legacy hand-built cases without status retain their failure meaning."""
    meta = case.get("meta", {})
    try:
        n = float(meta["Nf_cycles"])
    except (KeyError, TypeError, ValueError):
        return False
    return (meta.get("test_status", "failure") == "failure" and math.isfinite(n) and n > 0
            and not meta.get("loading_issues"))


def failures_only(data):
    """Return a view-like copy with only usable observed failure lives."""
    return {m: {**b, "cases": {cid: c for cid, c in b["cases"].items() if is_failure(c)}}
            for m, b in data.items()}


def observation_counts(block):
    counts = {"failure": 0, "runout": 0, "unknown": 0}
    for case in block["cases"].values():
        status = case.get("meta", {}).get("test_status", "failure")
        counts[status if status in counts else "unknown"] += 1
    counts["invalid_excluded"] = len(block.get("excluded_observations", []))
    return counts
