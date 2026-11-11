"""Method guides in docs/method-guides: structure, registry names and executable examples.

Every fenced ``python`` block of a guide is executed in a fresh namespace; when it is followed by
an ``Output:`` paragraph and a ``text`` block, the printed output must match that block exactly.
"""

from __future__ import annotations

import ast
import contextlib
import io
import re
from pathlib import Path

import pytest

from multifat.models.registry import _available_cp_methods, _available_direct_models

GUIDES = Path(__file__).resolve().parents[1] / "docs" / "method-guides"
NOT_GUIDES = {"README.md", "TEMPLATE.md"}
SECTIONS = [
    "Overview",
    "Original formulation",
    "Repository implementation",
    "Material constants and inputs",
    "Calibration",
    "Worked example",
    "Comparison capabilities and outputs",
    "Verification and limitations",
    "References",
]
REGISTERED = set(_available_cp_methods()) | set(_available_direct_models())
CP_METHODS = set(_available_cp_methods())


def _guides() -> list[Path]:
    return sorted(p for p in GUIDES.glob("*.md") if p.name not in NOT_GUIDES)


def _examples(text: str) -> list[tuple[str, str | None]]:
    """(python source, expected stdout or None) for each python block of a guide."""
    pattern = re.compile(
        r"```python\n(?P<code>.*?)```(?:\s*\n\s*Output:\s*\n\s*```text\n(?P<out>.*?)```)?",
        re.S,
    )
    return [(m["code"], m["out"]) for m in pattern.finditer(text)]


def _model_names(text: str) -> set[str]:
    """Model names given to --model / --models on the command lines of a guide."""
    names = set()
    for match in re.finditer(r"--models?[ =]([A-Za-z0-9_,]+)", text):
        names |= set(match[1].split(","))
    return names


def test_guides_exist():
    assert _guides(), "no method guide found"


@pytest.mark.parametrize("guide", _guides(), ids=lambda p: p.stem)
def test_guide_names_a_registered_model(guide):
    assert guide.stem in REGISTERED, f"{guide.name}: file name is not a registry name"
    text = guide.read_text(encoding="utf-8")
    assert f"**Registry name:** `{guide.stem}`" in text
    for name in _model_names(text):
        base = name.removesuffix("_ext")
        assert base in REGISTERED, f"{guide.name}: unknown model {name!r} on a command line"
        if name.endswith("_ext"):
            assert base in CP_METHODS, f"{guide.name}: {name!r} has no _ext variant"


@pytest.mark.parametrize("guide", _guides(), ids=lambda p: p.stem)
def test_guide_sections_in_order(guide):
    headings = re.findall(r"^## (.+?)\s*$", guide.read_text(encoding="utf-8"), flags=re.M)
    assert headings == SECTIONS, f"{guide.name}: sections differ from TEMPLATE.md"


@pytest.mark.parametrize("guide", _guides(), ids=lambda p: p.stem)
def test_guide_is_indexed(guide):
    index = (GUIDES / "README.md").read_text(encoding="utf-8")
    assert f"]({guide.name})" in index, f"{guide.name} is missing from the guide index"


METHOD_DIRS = ("cp_methods", "invariant_methods", "integral_methods", "energy_based_methods")
# Shared helpers, not criteria: no source formulation to depart from.
HELPER_MODULES = {
    "cp_methods/fin_harmonic",  # explicit-amplitude Findley entry point; see fin.py
    "invariant_methods/stress_invariants",  # invariant amplitudes shared by several criteria
}
# Method modules whose docstring still lacks the "Repository choices:" paragraph required by
# docs/adding-methods.md (issue #32). Remove an entry when its docstring is completed; the test
# fails if a listed module already complies, so this list can only shrink.
PENDING_DOCSTRINGS = {
    "cp_methods/car_spa",
    "invariant_methods/coin_liwi",
    "invariant_methods/mmmh",
    "invariant_methods/papadopoulos_panoskaltsis",
    "invariant_methods/pbp",
    "invariant_methods/vu_halm_nadot",
    "integral_methods/doudard",
    "integral_methods/flaceliere_morel",
    "integral_methods/robert_fogue_bahuaud",
    "energy_based_methods/banvillet",
    "energy_based_methods/sed_berto_lazzarin",
    "energy_based_methods/zhu_edp",
}


def _method_modules() -> dict[str, Path]:
    src = Path(__file__).resolve().parents[1] / "src" / "multifat" / "models"
    return {
        f"{folder}/{path.stem}": path
        for folder in METHOD_DIRS
        for path in sorted((src / folder).glob("*.py"))
        if path.name != "__init__.py"
    }


def test_method_module_docstrings():
    """Each criterion module documents its source and its departures (docs/adding-methods.md)."""
    modules = _method_modules()
    assert PENDING_DOCSTRINGS <= set(modules), "pending entry names no module"
    missing, done = [], []
    for key, path in modules.items():
        if key in HELPER_MODULES:
            continue
        doc = ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""
        complies = "Repository choices:" in doc
        if not complies and key not in PENDING_DOCSTRINGS:
            missing.append(key)
        if complies and key in PENDING_DOCSTRINGS:
            done.append(key)
    assert not missing, f"module docstring lacks 'Repository choices:': {missing}"
    assert not done, f"docstring completed, remove from PENDING_DOCSTRINGS: {done}"


@pytest.mark.parametrize("guide", _guides(), ids=lambda p: p.stem)
def test_guide_examples_run(guide):
    examples = _examples(guide.read_text(encoding="utf-8"))
    assert examples, f"{guide.name}: no python worked example"
    for code, expected in examples:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exec(compile(code, str(guide), "exec"), {"__name__": "__guide__"})
        if expected is not None:
            assert stdout.getvalue() == expected, f"{guide.name}: printed output differs"
