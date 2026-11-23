"""Guard test: services and adapters change an aggregate only through its own methods.

An aggregate keeps its invariants only if every change goes through a method of its own, so the
code around it (application services and adapters) never assigns or deletes an attribute of an
object it was handed (``table.status = …``, ``run.attempts += …``, ``run.attempts[0] = …``) and
never calls another object's private method (``table._assign_together(…)``). Assigning its own
attributes (``self._repo = repo``) and Starlette's ``app.state`` are allowed.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

import pytest

from tests.architecture.contexts import BACKEND, context_dir, context_names

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

_OWN = frozenset({"self", "cls"})


def _targets(node: ast.stmt) -> list[ast.expr]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        return [node.target]
    if isinstance(node, ast.Delete):
        return list(node.targets)
    return []


def _flattened(target: ast.expr) -> Iterator[ast.expr]:
    if isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _flattened(elt)
    elif isinstance(target, ast.Starred):
        yield from _flattened(target.value)
    else:
        yield target


def _is_foreign(target: ast.expr) -> bool:
    """Tell whether ``target`` is an attribute, or an item of an attribute, of something other than ``self`` or ``cls``.

    The attribute's direct owner counts, so ``self.run.status`` is another object's attribute
    reached through ``self``; ``self.items[0]`` is an item of the object's own attribute.
    """
    node: ast.expr = target
    while isinstance(node, ast.Subscript):
        node = node.value
    if not isinstance(node, ast.Attribute):
        return False
    if isinstance(node.value, ast.Attribute) and node.value.attr == "state":
        return False
    return not (isinstance(node.value, ast.Name) and node.value.id in _OWN)


def foreign_assignments(source: str) -> list[str]:
    """Return ``<line>: <target>`` for each assignment or deletion of another object's attribute."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.stmt):
            continue
        for target in _targets(node):
            found += [f"{node.lineno}: {ast.unparse(t)}" for t in _flattened(target) if _is_foreign(t)]
    return found


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _is_own(receiver: ast.expr) -> bool:
    if isinstance(receiver, ast.Name):
        return receiver.id in _OWN
    return isinstance(receiver, ast.Call) and isinstance(receiver.func, ast.Name) and receiver.func.id == "super"


def foreign_private_calls(source: str) -> list[str]:
    """Return ``<line>: <call>`` for each call of a private method on something other than ``self``, ``cls`` or ``super()``."""  # noqa: E501
    return [
        f"{node.lineno}: {ast.unparse(node.func)}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and _is_private(node.func.attr)
        and not _is_own(node.func.value)
    ]


def _scanned_files() -> list[Path]:
    files: list[Path] = []
    for name in context_names():
        root = context_dir(name)
        for part in (root / "application" / "service", root / "adapter"):
            files += [p for p in part.rglob("*.py") if "__pycache__" not in p.parts]
    return sorted(files)


_FILES = _scanned_files()
_IDS = [str(p.relative_to(BACKEND)) for p in _FILES]


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_services_and_adapters_assign_only_their_own_attributes(path: Path) -> None:
    """A service or adapter assigns or deletes only its own attributes, never those of an object it holds."""
    found = foreign_assignments(path.read_text())
    assert not found, f"{path.relative_to(BACKEND)} changes another object's state: {found}"


@pytest.mark.parametrize("path", _FILES, ids=_IDS)
def test_services_and_adapters_call_no_private_method_of_another_object(path: Path) -> None:
    """A service or adapter calls private methods only on itself, never on an object it holds."""
    found = foreign_private_calls(path.read_text())
    assert not found, f"{path.relative_to(BACKEND)} calls another object's private method: {found}"


def test_the_scan_covers_services_and_adapters_of_every_context() -> None:
    """Every context's services and adapters are scanned."""
    for name in context_names():
        root = context_dir(name)
        assert any(p.is_relative_to(root / "application" / "service") for p in _FILES), name
        assert any(p.is_relative_to(root / "adapter") for p in _FILES), name


@pytest.mark.parametrize(
    "source",
    [
        "table.status = x",
        "run.attempts += (a,)",
        "a.b.c = 1",
        "run.attempts[0] = a",
        "del table.priority",
        "table.priority: str = 'P1'",
        "x, table.status = 1, 2",
        "self.repo.table.status = x",
    ],
)
def test_the_assignment_check_flags_another_objects_attributes(source: str) -> None:
    """Assigning, extending or deleting an attribute of anything but ``self`` or ``cls`` is flagged."""
    assert foreign_assignments(source)


@pytest.mark.parametrize(
    "source",
    ["self._repo = repo", "cls.count = 1", "x = 1", "rows[0] = r", "app.state.use_cases = u", "self.items[0] = a"],
)
def test_the_assignment_check_allows_own_and_local_state(source: str) -> None:
    """Own attributes, local names and their items, and ``app.state`` are allowed."""
    assert foreign_assignments(source) == []


def test_the_assignment_check_names_the_line_and_the_target() -> None:
    """A finding names its line and the target as written."""
    assert foreign_assignments("x = 1\nrun.attempts[0] = a\n") == ["2: run.attempts[0]"]


@pytest.mark.parametrize("source", ["t._assign_together(id=x)", "repo.table._set(1)", "make()._f()"])
def test_the_call_check_flags_another_objects_private_methods(source: str) -> None:
    """A private method called on anything but ``self``, ``cls`` or ``super()`` is flagged."""
    assert foreign_private_calls(source)


@pytest.mark.parametrize("source", ["self._f()", "cls._g()", "super()._f()", "t.__init__()", "t.public()", "_f()"])
def test_the_call_check_allows_own_private_and_public_calls(source: str) -> None:
    """Own private calls, dunders, public methods and plain functions are allowed."""
    assert foreign_private_calls(source) == []
