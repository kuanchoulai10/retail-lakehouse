"""Guard test: ``base`` holds only the allowlisted DDD building blocks, and its private modules stay inside it.

To add a building block, add its name to ``ALLOWED`` and say why in the DDD Base Types section of the backend
``CLAUDE.md``. Everything else (helpers, converters, shared types) belongs to the context that uses it.
"""

from __future__ import annotations

import ast
from pathlib import Path

import base

BACKEND = Path(__file__).resolve().parents[2]
BASE_DIR = BACKEND / "base"
ALLOWED = {
    "ValueObject",
    "Entity",
    "EntityId",
    "AggregateRoot",
    "DomainEvent",
    "InvariantViolation",
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
        elif isinstance(node, ast.Assign):
            names.extend(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign | ast.AugAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
    return [name for name in names if not name.startswith("_") and name not in ALLOWED]


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


def _public_base_modules() -> list[Path]:
    return sorted(path for path in BASE_DIR.glob("*.py") if not path.name.startswith("_") or path.name == "__init__.py")


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
