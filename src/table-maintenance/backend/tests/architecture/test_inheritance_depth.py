"""Guard tests: enforce DDD inheritance depth limits on base classes.

Inheritance depth is the number of class-extension layers between a concrete
class and its DDD base, computed as the shortest path through ``__bases__``.
``class B(A)`` has depth 1 from ``A``; ``class C(B)`` has depth 2 from ``A``.

Limits derive from DDD best practices:

  - Domain primitives (ValueObject, EntityId, Entity, AggregateRoot,
    DomainEvent) — flat hierarchies, max depth 1.
  - Outbound ports (Repository, Store, Gateway) — port + adapter, max depth 2.
  - Inbound ports (UseCase) — port interface + service implementation,
    symmetric to the outbound port/adapter pattern, max depth 2.
  - EventHandler — concrete handlers extend it directly, max depth 1.
  - EventDispatcher — concrete utility, must not be subclassed.

Bases with an intermediate abstract layer in ``base/`` (e.g. ``EntityId``
under ``ValueObject``; ``AggregateRoot`` under ``Entity``) exclude that
subtree from their own check — the subtree is governed by its own
intermediate base's contract.
"""

from __future__ import annotations

import importlib
from collections import deque
from pathlib import Path

import pytest

from base.aggregate_root import AggregateRoot
from base.domain_event import DomainEvent
from base.entity import Entity
from base.entity_id import EntityId
from base.event_dispatcher import EventDispatcher
from base.event_handler import EventHandler
from base.gateway import Gateway
from base.repository import Repository
from base.store import Store
from base.use_case import UseCase
from base.value_object import ValueObject

BACKEND = Path(__file__).resolve().parents[2]
SOURCE_PACKAGES = ("base", "application", "adapter", "bootstrap")


def _import_all_modules() -> None:
    """Import every backend module so subclasses register on their bases."""
    for package_name in SOURCE_PACKAGES:
        package_dir = BACKEND / package_name
        if not package_dir.is_dir():
            continue
        for py_file in package_dir.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            rel = py_file.relative_to(BACKEND).with_suffix("")
            module_path = ".".join(rel.parts)
            if module_path.endswith(".__init__"):
                module_path = module_path[: -len(".__init__")]
            try:
                importlib.import_module(module_path)
            except Exception:  # noqa: BLE001 — best-effort import for discovery
                continue


_import_all_modules()


def _all_subclasses(cls: type) -> set[type]:
    """Return all transitive subclasses of cls (excluding cls itself)."""
    found: set[type] = set()
    stack: list[type] = list(cls.__subclasses__())
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        stack.extend(current.__subclasses__())
    return found


def _shortest_depth(cls: type, base: type) -> int:
    """Shortest inheritance distance from cls to base via ``__bases__``."""
    if cls is base:
        return 0
    queue: deque[tuple[type, int]] = deque([(cls, 0)])
    visited: set[type] = {cls}
    while queue:
        current, depth = queue.popleft()
        for parent in current.__bases__:
            if parent is base:
                return depth + 1
            if (
                parent not in visited
                and isinstance(parent, type)
                and issubclass(parent, base)
            ):
                visited.add(parent)
                queue.append((parent, depth + 1))
    raise AssertionError(f"{cls!r} is not a subclass of {base!r}")


def _qualified_name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


# (base, max_depth, exclude_subtrees)
DEPTH_CONTRACTS: list[tuple[type, int, tuple[type, ...]]] = [
    (ValueObject, 1, (EntityId,)),
    (EntityId, 1, ()),
    (Entity, 1, (AggregateRoot,)),
    (AggregateRoot, 1, ()),
    (DomainEvent, 1, ()),
    (Repository, 2, ()),
    (Store, 2, ()),
    (Gateway, 2, ()),
    (UseCase, 2, ()),
    (EventHandler, 1, ()),
]


@pytest.mark.parametrize(
    "base,max_depth,exclude_subtrees",
    DEPTH_CONTRACTS,
    ids=[c[0].__name__ for c in DEPTH_CONTRACTS],
)
def test_inheritance_depth(
    base: type, max_depth: int, exclude_subtrees: tuple[type, ...]
) -> None:
    excluded: set[type] = set()
    for sub_base in exclude_subtrees:
        excluded.add(sub_base)
        excluded.update(_all_subclasses(sub_base))

    violations: list[tuple[str, int]] = []
    for cls in _all_subclasses(base):
        if cls in excluded:
            continue
        depth = _shortest_depth(cls, base)
        if depth > max_depth:
            violations.append((_qualified_name(cls), depth))

    if violations:
        violations.sort()
        formatted = "\n".join(f"  {name} (depth={d})" for name, d in violations)
        pytest.fail(
            f"{base.__name__} subclasses exceed max depth {max_depth}:\n{formatted}"
        )


def test_event_dispatcher_has_no_subclasses() -> None:
    subclasses = _all_subclasses(EventDispatcher)
    if subclasses:
        formatted = "\n".join(
            f"  {_qualified_name(c)}" for c in sorted(subclasses, key=_qualified_name)
        )
        pytest.fail(f"EventDispatcher must not be subclassed:\n{formatted}")


def test_aggregate_repos_extend_repository() -> None:
    """Every ``*Repo`` port class must extend ``base.repository.Repository``."""
    port_dir = BACKEND / "application" / "port" / "outbound"
    found: list[type] = []
    for py_file in port_dir.rglob("*_repo.py"):
        rel = py_file.relative_to(BACKEND).with_suffix("")
        module_path = ".".join(rel.parts)
        module = importlib.import_module(module_path)
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if (
                isinstance(obj, type)
                and obj.__module__ == module_path
                and attr_name.endswith("Repo")
            ):
                found.append(obj)

    violations = [_qualified_name(c) for c in found if not issubclass(c, Repository)]
    if violations:
        formatted = "\n".join(f"  {v}" for v in sorted(violations))
        pytest.fail(
            f"These *Repo port classes must extend base.repository.Repository:\n{formatted}"
        )
