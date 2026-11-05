"""Classification of an imported material block into an assessment workflow (issue #18).

One importer, one workbook per material; the classification decides which assessment the data
support and gives every plain observation an explicit role::

    fatigue_life     >= 2 uniaxial tension R = -1 failures with distinct lives (design set):
                     master curve on the design set, other failures assessed, run-outs censored
    fatigue_limit    no plain failure, run-outs present and both R = -1 fatigue limits usable:
                     the run-outs are taken as limit states and judged by the fatigue index
    ambiguous        data that support neither workflow (failures without a design set; run-outs
                     without usable limits); nothing is assessed, the reasons are reported
    out_of_scope     no plain (unnotched) observation

Rules that keep the scientific distinction explicit:

- a run-out is a censored life observation (a lower bound on life), never a failure;
- in a ``fatigue_life`` workbook a run-out is not an established fatigue limit: finite-cycle
  survival and an experimentally established limit need different evidence, so a mixed
  workbook is assessed through its failures, with its run-outs kept as censored rows;
- in a ``fatigue_limit`` workbook every plain run-out is treated as a limit state; a run-out
  stopped below the reference life of the Summary limits is reported in ``diagnostics``.

Repository choices:
  - the classification reproduces the routing of the pipeline before issue #18 for every
    unambiguous workbook (failures -> life path, run-outs only with limits -> limit path);
  - the reference life of a limit is the smallest ``reference_cycles`` among its R = -1 sources.
"""

from __future__ import annotations

from typing import Any

WORKFLOWS = ("fatigue_life", "fatigue_limit", "ambiguous", "out_of_scope")


def classify_dataset(block: dict, material: str) -> dict[str, Any]:
    """Workflow, per-observation roles, counts and diagnostics of one imported material block."""
    from multifat.imp import experimental_data as exp
    from multifat.report.subsets import observation_index

    cases = block.get("cases", {})
    runouts = block.get("runouts", {})
    props = block.get("material", {})
    flagged = block.get("property_issues", {})
    limits = {
        key: props.get(field)
        for key, field in (
            ("Sigm1", "Tensile_fatigue_limit_MPa"),
            ("Taum1", "Torsional_fatigue_limit_MPa"),
        )
    }
    usable_limits = all(v is not None and v > 0 for v in limits.values()) and not (
        {"Sigm1", "Taum1"} & set(flagged)
    )
    points = exp.extract_uniaxial_tension({material: block}).get(material, {}).get("points", [])
    design_ids = sorted(int(pt["case_id"]) for pt in points)
    design_lives = {float(pt["Nf_cycles"]) for pt in points}
    reasons: list[str] = []
    diagnostics: list[str] = []

    if not cases and not runouts:
        workflow = "out_of_scope"
        reasons.append("no plain (unnotched) observation")
    elif cases and len(design_lives) >= 2:
        workflow = "fatigue_life"
        reasons.append(
            f"{len(design_ids)} uniaxial tension R = -1 failures with {len(design_lives)} "
            "distinct lives form the design set"
        )
        if runouts:
            diagnostics.append(
                f"{len(runouts)} run-outs are censored life observations, not fatigue limits"
            )
    elif cases:
        workflow = "ambiguous"
        reasons.append(
            "failures present, but fewer than 2 uniaxial tension R = -1 failures with distinct "
            f"lives (found {len(design_ids)}): no master curve can be fitted"
        )
    elif usable_limits:
        workflow = "fatigue_limit"
        reasons.append(
            f"{len(runouts)} run-outs and no failure: limit states judged at the R = -1 limits "
            f"Sigm1 = {limits['Sigm1']:g} and Taum1 = {limits['Taum1']:g} MPa"
        )
        reference = _reference_life(block)
        if reference is not None:
            short = [
                int(rid)
                for rid, case in runouts.items()
                if float(case["meta"]["Nf_cycles"]) < reference
            ]
            if short:
                diagnostics.append(
                    f"{len(short)} run-outs stopped below the {reference:g}-cycle reference of the "
                    f"Summary limits (ids {short}): finite-cycle survivals, not established limits"
                )
    else:
        workflow = "ambiguous"
        missing = [k for k, v in limits.items() if v is None or v <= 0 or k in flagged]
        reasons.append(
            "run-outs only, and the Summary lacks usable R = -1 fatigue limits "
            f"({', '.join(missing)}): neither a master curve nor a fatigue index can be built"
        )

    ids = observation_index(block)

    def entries(kind: str, keys) -> list[dict]:
        return [{"id": int(k), **ids[(kind, int(k))]} for k in keys]

    design_set = set(design_ids) if workflow == "fatigue_life" else set()
    roles = {
        "design": entries("case", sorted(design_set)),
        "assessment": (
            entries("case", sorted(int(k) for k in cases if int(k) not in design_set))
            if workflow == "fatigue_life"
            else []
        ),
        "censored": entries("runout", sorted(runouts)) if workflow == "fatigue_life" else [],
        "limit_state": entries("runout", sorted(runouts)) if workflow == "fatigue_limit" else [],
    }
    return {
        "material": material,
        "workflow": workflow,
        "reasons": reasons,
        "diagnostics": diagnostics,
        "counts": {
            "failures": len(cases),
            "runouts": len(runouts),
            "design": len(roles["design"]),
            "excluded": len(block.get("excluded_observations", [])),
        },
        "fatigue_limits_usable": usable_limits,
        "source_workbook": block.get("source", {}).get("workbook"),
        "roles": roles,
    }


def _reference_life(block: dict) -> float | None:
    """Smallest reference life of the R = -1 limit sources, or None when none is recorded."""
    lives = [
        float(source["reference_cycles"])
        for sources in (block.get("fatigue_limit_sources") or {}).values()
        for source in sources
        if source.get("reference_cycles")
    ]
    return min(lives) if lives else None
