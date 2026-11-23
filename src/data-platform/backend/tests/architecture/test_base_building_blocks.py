"""Guard test: ``base`` holds only the allowlisted DDD building blocks, and its private modules stay inside it.

To add a building block, add its name to ``ALLOWED`` and say why in the DDD Base Types section of the backend
``CLAUDE.md``. Everything else (helpers, converters, shared types) belongs to the context that uses it.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import base
from tests.architecture.contexts import BACKEND

if TYPE_CHECKING:
    from pathlib import Path

BASE_DIR = BACKEND / "base"
ALLOWED = {
    "ValueObject",
    "Entity",
    "EntityId",
    "AggregateRoot",
    "DomainEvent",
    "InvariantViolation",
    "ReadOnlyMapping",
    "Specification",
    "Repository",
    "Store",
    "Gateway",
    "UseCase",
    "UseCaseInput",
    "UseCaseOutput",
    "EventHandler",
    "EventDispatcher",
    "UnitOfWork",
}
OUTSIDE_BASE = ("bootstrap", "context", "tests")


def public_names_outside_allowlist(source: str) -> list[str]:
    """Return the public top-level names ``source`` defines that are not in ``ALLOWED``."""
    names: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            names.append(node.name)
        elif isinstance(node, ast.TypeAlias):
            names.extend(_bound_names(node.name))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names.extend(_bound_names(target))
        elif isinstance(node, ast.AnnAssign | ast.AugAssign):
            names.extend(_bound_names(node.target))
    return [name for name in names if not name.startswith("_") and name not in ALLOWED]


def _bound_names(target: ast.expr) -> list[str]:
    """Return the names an assignment target binds, unpacking tuples, lists and starred names."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, ast.Starred):
        return _bound_names(target.value)
    if isinstance(target, ast.Tuple | ast.List):
        return [name for element in target.elts for name in _bound_names(element)]
    return []


def private_base_imports(source: str) -> list[str]:
    """Return the ``base._<name>`` modules ``source`` imports."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names if _is_private_base_module(alias.name))
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            if node.module == "base":
                found.extend(f"base.{alias.name}" for alias in node.names if alias.name.startswith("_"))
            elif _is_private_base_module(node.module):
                found.append(node.module)
    return found


def _is_private_base_module(dotted: str) -> bool:
    parts = dotted.split(".")
    return parts[0] == "base" and len(parts) > 1 and parts[1].startswith("_")


def _public_base_modules(base_dir: Path = BASE_DIR) -> list[Path]:
    """Return every module under ``base_dir`` with no ``_`` path part, ``__init__.py`` files included."""
    return sorted(
        path
        for path in base_dir.rglob("*.py")
        if not any(part.startswith("_") and part != "__init__.py" for part in path.relative_to(base_dir).parts)
    )


def _modules_outside_base() -> list[Path]:
    files = list(BACKEND.glob("*.py"))
    for package in OUTSIDE_BASE:
        files.extend(path for path in (BACKEND / package).rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def test_base_exports_only_building_blocks():
    """Every name ``base`` exports is on the allowlist."""
    assert set(base.__all__) <= ALLOWED


def test_base_modules_define_nothing_public_outside_the_allowlist():
    """No public base module defines a public top-level name that is not an allowlisted building block."""
    violations = [
        f"{path.relative_to(BACKEND)}: {name}"
        for path in _public_base_modules()
        for name in public_names_outside_allowlist(path.read_text())
    ]
    assert violations == [], "\n".join(violations)


def test_allowlist_rejects_an_extra_name():
    """A helper function, class or constant in a base module is reported."""
    source = "class ValueObject:\n    pass\n\n\ndef helper():\n    pass\n\n\nclass Helper:\n    pass\n\n\nLIMIT = 1\n"
    assert public_names_outside_allowlist(source) == ["helper", "Helper", "LIMIT"]


def test_allowlist_rejects_a_type_alias():
    """A ``type X = ...`` alias in a base module is a definition too."""
    assert public_names_outside_allowlist("type Helper = int\n") == ["Helper"]


def test_allowlist_rejects_names_bound_by_unpacking():
    """Every name a tuple or list unpacking binds is a definition."""
    source = "a, b = 1, 2\n[c, *rest] = [3, 4]\n_private, d = 5, 6\n"
    assert public_names_outside_allowlist(source) == ["a", "b", "c", "rest", "d"]


def test_public_base_modules_are_found_recursively_without_private_ones(tmp_path: Path):
    """The scan walks subpackages of ``base/`` and skips every ``_`` path part except ``__init__.py``."""
    for relative in (
        "__init__.py",
        "entity.py",
        "_rebuild.py",
        "ports/__init__.py",
        "ports/gateway.py",
        "ports/_helper.py",
        "_internal/thing.py",
        "__pycache__/entity.py",
    ):
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text("")
    found = [path.relative_to(tmp_path).as_posix() for path in _public_base_modules(tmp_path)]
    assert found == ["__init__.py", "entity.py", "ports/__init__.py", "ports/gateway.py"]


def test_base_scan_is_not_vacuous():
    """The base scan reads real modules, so its pass means something."""
    modules = _public_base_modules()
    assert modules
    assert BASE_DIR / "value_object.py" in modules


def test_outside_scan_is_not_vacuous():
    """The private-import scan reads modules under both ``tests/`` and ``context/``."""
    tops = {path.relative_to(BACKEND).parts[0] for path in _modules_outside_base()}
    assert {"tests", "context"} <= tops


def test_allowlist_ignores_private_names_and_imports():
    """Private names, dunders and imports are not definitions."""
    source = "from x import helper\n\n__all__ = []\n_CACHE = {}\n\n\ndef _step():\n    pass\n"
    assert public_names_outside_allowlist(source) == []


def test_private_base_modules_stay_inside_base():
    """Nothing outside ``base/`` imports a private ``base._<name>`` module."""
    violations = [
        f"{path.relative_to(BACKEND)}: {module}"
        for path in _modules_outside_base()
        for module in private_base_imports(path.read_text())
    ]
    assert violations == [], "\n".join(violations)


def test_private_import_checker_reports_every_import_form():
    """``from base._x import y``, ``import base._x`` and ``from base import _x`` are all reported."""
    assert private_base_imports("from base._rebuild import rebuild\n") == ["base._rebuild"]
    assert private_base_imports("import base._rebuild\n") == ["base._rebuild"]
    assert private_base_imports("from base import _rebuild\n") == ["base._rebuild"]


def test_private_import_checker_allows_public_imports():
    """Importing public names from ``base`` is fine."""
    assert private_base_imports("from base import ValueObject\nimport base\nfrom base.entity import Entity\n") == []
