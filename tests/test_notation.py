"""The notation guard: one name per concept, as written in ``docs/notation.md``.

The retired synonyms are read from the table in that document, so adding a row there is enough
to forbid the name here. Three structural rules follow the same page: no ``_old = _new`` private
alias, every module docstring opens on the first line, and an override keeps the parameter names
of the method it overrides. The parameter names of the public functions in ``eval/`` and
``models/`` must appear in the table as well, or in ``tests/data/notation_allow.txt`` with the
reason they are not vocabulary. Docstrings also answer to the wording rules of
``docs/adding-methods.md``.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ALLOW = ROOT / "tests" / "data" / "notation_allow.txt"
SCOPE = (SRC / "multifat" / "eval", SRC / "multifat" / "models")
BANNED_PHRASES = ("as given by", "in order to", "Remarks", "Compute ")


def _retired_synonyms() -> dict[str, str]:
    """The retired names of the notation table, mapped to what the page says to use instead."""
    text = (ROOT / "docs" / "notation.md").read_text(encoding="utf-8").splitlines()
    retired: dict[str, str] = {}
    in_table = False
    for line in text:
        if line.startswith("| Retired |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        cells = line.strip().strip("|").split("|")
        if not cells or set(cells[0]) <= set("- "):
            continue
        names = re.findall(r"`([^`]+)`", cells[0])
        replacement = ", ".join(re.findall(r"`([^`]+)`", cells[1])) or cells[1].strip()
        retired.update({name: replacement for name in names})
    return retired


RETIRED = _retired_synonyms()
MODULES = sorted(SRC.rglob("*.py"))


def _bound_names(tree: ast.AST) -> list[tuple[str, int, str]]:
    """Every name a module binds locally: parameters, assignments and loop variables."""
    found: list[tuple[str, int, str]] = []

    def add(node: ast.AST, kind: str) -> None:
        if isinstance(node, ast.arg):
            found.append((node.arg, node.lineno, kind))
        elif isinstance(node, ast.Name):
            found.append((node.id, node.lineno, kind))

    def add_targets(targets, kind: str) -> None:
        for target in targets:
            if isinstance(target, (ast.Tuple, ast.List)):
                add_targets(target.elts, kind)
            else:
                add(target, kind)

    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            add(node, "parameter")
        elif isinstance(node, ast.Assign):
            add_targets(node.targets, "assignment")
        elif isinstance(node, ast.AnnAssign):
            add_targets([node.target], "assignment")
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            add_targets([node.target], "loop")
        elif isinstance(node, ast.withitem) and node.optional_vars is not None:
            add_targets([node.optional_vars], "with")
        elif isinstance(node, ast.comprehension):
            add_targets([node.target], "comprehension")
        elif isinstance(node, ast.NamedExpr):
            add_targets([node.target], "walrus")
        elif isinstance(node, ast.ExceptHandler) and node.name:
            found.append((node.name, node.lineno, "except"))
        elif isinstance(node, ast.keyword) and node.arg:
            found.append((node.arg, node.value.lineno, "keyword"))
    return found


@pytest.mark.parametrize("path", MODULES, ids=lambda path: str(path.relative_to(SRC)))
def test_no_retired_synonyms(path: pathlib.Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = [
        f"{path.relative_to(ROOT)}:{lineno}: {kind} `{name}` -> use {RETIRED[name]}"
        for name, lineno, kind in _bound_names(tree)
        if name in RETIRED
    ]
    assert not offenders, "retired notation synonyms:\n" + "\n".join(offenders)


@pytest.mark.parametrize("path", MODULES, ids=lambda path: str(path.relative_to(SRC)))
def test_no_private_aliases(path: pathlib.Path) -> None:
    """A helper has one name; ``_old = _new`` lines make the tests import a second one."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = [
        f"{path.relative_to(ROOT)}:{node.lineno}"
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Name)
        and node.targets[0].id.startswith("_")
        and node.value.id.startswith("_")
    ]
    assert not offenders, "private alias lines:\n" + "\n".join(offenders)


@pytest.mark.parametrize("path", MODULES, ids=lambda path: str(path.relative_to(SRC)))
def test_module_docstring_opens_on_first_line(path: pathlib.Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    first = tree.body[0] if tree.body else None
    if not (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        pytest.skip("no module docstring")
    assert not first.value.value.startswith("\n"), (
        f"{path.relative_to(ROOT)}:{first.lineno}: module docstring starts on the line after "
        'the opening quotes; open it with """Text'
    )


COEFFICIENT_SET = re.compile(r"^([abcd])_([A-Z][A-Za-z0-9]*)$")


def _classes() -> dict[str, ast.ClassDef]:
    """Every class defined in the package, by name (names are unique across the package)."""
    classes: dict[str, ast.ClassDef] = {}
    for path in MODULES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes[node.name] = node
    return classes


def _parameters(function: ast.FunctionDef) -> list[str]:
    args = function.args
    return [
        name.arg
        for name in (*args.posonlyargs, *args.args, *args.kwonlyargs)
        if name.arg not in {"self", "cls"}
    ]


def _same_interface(parent: list[str], own: list[str], owner: str) -> bool:
    """Equal names; a coefficient set may only take the subscript of the overriding criterion."""
    if parent == own:
        return True
    if len(parent) != len(own):
        return False
    for parent_name, own_name in zip(parent, own):
        if parent_name == own_name:
            continue
        parent_set, own_set = COEFFICIENT_SET.match(parent_name), COEFFICIENT_SET.match(own_name)
        if not (
            parent_set
            and own_set
            and parent_set.group(1) == own_set.group(1)
            and own_set.group(2) == owner
        ):
            return False
    return True


def test_overrides_keep_the_base_parameters() -> None:
    """An override renames none of its parameters: ``a_BP..d_BP`` may only become ``a_CAIM..d_CAIM``.

    The paper of each criterion prints the coefficient set with its own subscript, so the
    override keeps the paper's names instead of the base class's; the subscript has to be the
    name of the criterion that overrides.
    """
    classes = _classes()
    offenders = []
    for name, node in classes.items():
        own = {item.name: item for item in node.body if isinstance(item, ast.FunctionDef)}
        for base_expr in node.bases:
            parent_class = classes.get(getattr(base_expr, "id", None))
            if parent_class is None:
                continue
            inherited = {
                item.name: item for item in parent_class.body if isinstance(item, ast.FunctionDef)
            }
            for method, function in own.items():
                if method in inherited and not _same_interface(
                    _parameters(inherited[method]), _parameters(function), name
                ):
                    offenders.append(f"{name}.{method}")
    assert not offenders, "override renames a base parameter:\n" + "\n".join(offenders)


def test_boehme_spelling() -> None:
    """Source and the tables generated from it spell ``Boehme``; no exemptions (rule 5)."""
    generated = [ROOT / "docs" / "workbook-format.md"]
    offenders = [
        f"{path.relative_to(ROOT)}:{lineno}"
        for path in [*MODULES, *generated]
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if "Böhme" in line
    ]
    assert not offenders, "the accented spelling belongs in hand-written documentation only:\n" + (
        "\n".join(offenders)
    )


@pytest.mark.parametrize("path", MODULES, ids=lambda path: str(path.relative_to(SRC)))
def test_no_stray_string_statements(path: pathlib.Path) -> None:
    """A string literal that is not a docstring is a docstring left in the wrong place."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = []
    for node in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            block = getattr(node, field, None)
            if not isinstance(block, list):
                continue
            for index, statement in enumerate(block):
                if not (
                    isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)
                ):
                    continue
                is_docstring = (
                    index == 0
                    and field == "body"
                    and isinstance(
                        node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
                    )
                )
                if not is_docstring:
                    offenders.append(f"{path.relative_to(ROOT)}:{statement.lineno}")
    assert not offenders, "string statements outside the docstring slot:\n" + "\n".join(offenders)


def _endorsed_names() -> set[str]:
    """Names the page endorses.

    The Python name and workbook-key columns of the symbol table, plus the replacement column of
    the retired table.
    """
    lines = (ROOT / "docs" / "notation.md").read_text(encoding="utf-8").splitlines()
    names: set[str] = set()
    for line in lines:
        if not line.startswith("|"):
            continue
        cells = line.strip().strip("|").split("|")
        if len(cells) == 5:
            names.update(re.findall(r"`([^`]+)`", cells[2]))
            key = cells[3].strip()
            if key and key != "-":
                names.add(key)
        elif len(cells) == 2:
            names.update(re.findall(r"`([^`]+)`", cells[1]))
    return names


def _allow_list() -> dict[str, str]:
    """Names outside the table, with the reason recorded in the comment above them.

    A line holds one name; several names may share a line when they share one reason.
    """
    allowed: dict[str, str] = {}
    reason = ""
    for line in ALLOW.read_text(encoding="utf-8").splitlines():
        names, _, comment = line.partition("#")
        reason = comment.strip() or reason
        allowed.update({name: reason for name in names.split()})
    return allowed


def _public_parameters() -> list[tuple[str, str, int]]:
    """Every parameter name of every public function and method in ``eval/`` and ``models/``.

    Nested helpers are implementation detail, so their parameters are not vocabulary.
    """
    found = []
    for folder in SCOPE:
        for path in sorted(folder.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            public = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
            public += [
                method
                for node in tree.body
                if isinstance(node, ast.ClassDef)
                for method in node.body
                if isinstance(method, ast.FunctionDef)
            ]
            for node in public:
                if node.name.startswith("_"):
                    continue
                args = node.args
                for name in (*args.posonlyargs, *args.args, *args.kwonlyargs):
                    if name.arg not in {"self", "cls"}:
                        found.append((str(path.relative_to(ROOT)), name.arg, name.lineno))
    return found


def test_parameters_are_in_the_table_or_the_allow_list() -> None:
    """A new parameter either adds a row to ``docs/notation.md`` or an entry to the allow list."""
    endorsed, allowed = _endorsed_names(), _allow_list()
    offenders = [
        f"{path}:{lineno}: `{name}`"
        for path, name, lineno in _public_parameters()
        if name not in endorsed and name not in allowed
    ]
    assert not offenders, (
        "parameter names outside docs/notation.md; add a table row or an entry with its reason "
        "to tests/data/notation_allow.txt:\n" + "\n".join(sorted(set(offenders)))
    )


def test_allow_list_is_exactly_the_names_outside_the_table() -> None:
    """No entry outlives its name: a rename must shrink the file, as an addition must grow it."""
    used = {name for _, name, _ in _public_parameters()}
    stale = sorted(set(_allow_list()) - used)
    assert not stale, (
        "tests/data/notation_allow.txt lists names that no public parameter uses any more:\n"
        + "\n".join(stale)
    )


@pytest.mark.parametrize("path", MODULES, ids=lambda path: str(path.relative_to(SRC)))
def test_docstrings_follow_the_policy(path: pathlib.Path) -> None:
    """No banned phrase and no "Compute" opening in any docstring (adding-methods.md)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if docstring is None:
            continue
        offenders += [
            f"{path.relative_to(ROOT)}:{node.lineno}: {phrase!r}"
            for phrase in BANNED_PHRASES
            if phrase in docstring
        ]
    assert not offenders, "banned docstring wording (docs/adding-methods.md):\n" + "\n".join(
        offenders
    )


GENERATED_FROM_SOURCE = {ROOT / "docs" / "workbook-format.md"}
HEADING_VARIANTS = ("Repository convention:", "Implementation notes", "Notes on implementation")


def test_hand_written_docs_keep_the_author_spelling() -> None:
    """``Boehme`` belongs to Python source and to the tables generated from it; prose keeps ``Böhme``."""
    pages = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", *sorted((ROOT / "docs").rglob("*.md"))]
    offenders = []
    for path in pages:
        if path in GENERATED_FROM_SOURCE:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "Boehme" in re.sub(r"`[^`]*`", "", line):
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    assert not offenders, (
        "hand-written documentation keeps the author's `Böhme` (docs/adding-methods.md):\n"
        + "\n".join(offenders)
    )


def test_module_docstrings_use_the_documented_choices_heading() -> None:
    """A departures paragraph is headed ``Repository choices:``, not a variant (adding-methods.md)."""
    offenders = []
    for path in sorted((SRC / "multifat" / "models").rglob("*.py")):
        docstring = (
            ast.get_docstring(ast.parse(path.read_text(encoding="utf-8")), clean=False) or ""
        )
        offenders += [
            f"{path.relative_to(ROOT).as_posix()}: {variant!r}"
            for variant in HEADING_VARIANTS
            if variant in docstring
        ]
    assert (
        not offenders
    ), "a departures paragraph uses the documented heading `Repository choices:`:\n" + "\n".join(
        offenders
    )
