"""Findley calibration configuration, independent of calibration persistence."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from fatigue.models.base import CaseResult
from fatigue.models.cp_methods.fin_harmonic import evaluate_findley
from fatigue.models.registry import get_models
from fatigue.models.utils.shear_amplitude import ALGORITHMS, DEFINITION_VERSION


def resolve_findley_algorithm(selection: str = "method_default") -> str:
    """Return the canonical amplitude identifier used by a Findley calibration.

    Args:
        selection: Method default, a harmonic algorithm, or the RSS alias.

    Returns:
        ``mce_harmonic`` for the default/RSS, otherwise the selected algorithm.

    Raises:
        ValueError: If the identifier is unsupported.
    """
    if not isinstance(selection, str) or selection not in (*ALGORITHMS, "rss", "method_default"):
        raise ValueError(f"Unknown Findley shear amplitude algorithm {selection!r}")
    return "mce_harmonic" if selection in {"method_default", "rss"} else selection


def check_amplitude_methods(methods: Iterable[str], selection: str) -> None:
    """Reject an explicit amplitude override for any method other than Findley."""
    resolve_findley_algorithm(selection)
    unsupported = [name for name in methods if name.removesuffix("_ext") != "FIN"]
    if selection != "method_default" and unsupported:
        raise ValueError(f"Shear amplitude override {selection!r} is supported only for FIN; got {unsupported}")


def amplitude_identity(selection: str) -> dict[str, str]:
    """Describe the resolved definition and the numerical path actually used."""
    return {
        "algorithm": resolve_findley_algorithm(selection),
        "definition_version": DEFINITION_VERSION,
        "evaluation_path": "legacy" if selection == "method_default" else "harmonic",
    }


def require_stress_harmonics(case: Mapping[str, Any], material: str, case_id: int) -> None:
    """Check stored coefficients before the extractor can synthesise a fallback.

    Args:
        case: Original experimental case, with an explicit harmonic history.
        material: Material identity for an actionable diagnostic.
        case_id: Selected failure observation identity.

    Raises:
        ValueError: If either real, finite 3 by 3 stress coefficient is missing.
    """
    harmonics = case.get("harmonics")
    for name in ("S_sin", "S_cos"):
        value = harmonics.get(name) if isinstance(harmonics, Mapping) else None
        raw = np.asarray(value)
        if raw.shape != (3, 3) or raw.dtype.kind not in "biuf" or not np.isfinite(raw).all():
            raise ValueError(f"{material}/FIN case {case_id}: missing or invalid {name}; "
                             "explicit amplitude calibration requires stored S_sin and S_cos tensors")


class FindleyCalibrationModel:
    """Adapt the verified Phase 2 evaluator to both calibration fitting stages.

    This callable is constructed explicitly by calibration code. It is absent
    from the production registry and performs no JSON or fatigue-life operations.
    """

    name = "FIN"

    def __init__(self, selection: str) -> None:
        self.algorithm = resolve_findley_algorithm(selection)
        self.requires_stress_harmonics = selection != "method_default"
        self._selection = self.algorithm if self.requires_stress_harmonics else None

    def required_params(self) -> set[str]:
        """Return the existing dimensionless Findley coefficient requirement."""
        return {"k_FI"}

    def evaluate_case(self, *, S0: np.ndarray, E0: np.ndarray, S1: np.ndarray,
                      E1: np.ndarray, params: Mapping[str, float],
                      R_list: np.ndarray | None = None,
                      harmonics: Mapping[str, np.ndarray] | None = None) -> CaseResult:
        """Evaluate the complete Findley expression on every supplied plane."""
        return evaluate_findley(S0=S0, E0=E0, S1=S1, E1=E1, params=params,
                                R_list=R_list, harmonics=harmonics,
                                shear_amplitude_algorithm=self._selection)


def calibration_models(names: list[str], selection: str) -> list[Any]:
    """Build ordinary models, replacing only an explicitly configured Findley."""
    check_amplitude_methods(names, selection)
    if selection == "method_default":
        return get_models(names)
    return [FindleyCalibrationModel(selection)]
