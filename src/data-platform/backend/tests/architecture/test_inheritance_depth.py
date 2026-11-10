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

The Pydantic bases in ``base.model`` carry the same contracts. A Pydantic
generic parametrization (``AggregateRoot[TableId]``) is a real class in the
chain but not a layer of the hierarchy, so it does not count towards the depth.
Only classes of the source packages are checked, not test stubs.
"""

from __future__ import annotations

import importlib
from collections import deque
from pathlib import Path

import pytest

from base import (
    AggregateRoot,
    DomainEvent,
    Entity,
    EntityId,
    EventDispatcher,
    EventHandler,
    Gateway,
    Repository,
    Store,
    UseCase,
    ValueObject,
)
from base.model import AggregateRoot as ModelAggregateRoot
from base.model import DomainEvent as ModelDomainEvent
from base.model import Entity as ModelEntity
from base.model import EntityId as ModelEntityId
from base.model import ValueObject as ModelValueObject
from tests.architecture.contexts import context_dir, context_names

BACKEND = Path(__file__).resolve().parents[2]
SOURCE_PACKAGES = ("base", "context", "bootstrap")


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


def _is_parametrization(cls: type) -> bool:
    """Return whether ``cls`` is a Pydantic generic parametrization such as ``Entity[TableId]``."""
    metadata = getattr(cls, "__pydantic_generic_metadata__", None)
    return bool(metadata and metadata.get("origin") is not None)


def _is_source(cls: type) -> bool:
    return cls.__module__.split(".", 1)[0] in SOURCE_PACKAGES


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
    """Shortest inheritance distance from cls to base via ``__bases__``, skipping parametrizations.

    The distance counts the classes on the path from ``cls`` up to, but not
    including, ``base``; a parametrization on the path counts zero.
    """
    if cls is base:
        return 0
    queue: deque[tuple[type, int]] = deque([(cls, _layer(cls))])
    visited: set[type] = {cls}
    while queue:
        current, depth = queue.popleft()
        for parent in current.__bases__:
            if parent is base:
                return depth
            if parent not in visited and isinstance(parent, type) and issubclass(parent, base):
                visited.add(parent)
                if _layer(parent):
                    queue.append((parent, depth + 1))
                else:
                    queue.appendleft((parent, depth))
    raise AssertionError(f"{cls!r} is not a subclass of {base!r}")


def _layer(cls: type) -> int:
    return 0 if _is_parametrization(cls) else 1


def _qualified_name(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


# Each contract is a base, its maximum depth and the subtrees excluded from the count.
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
    (ModelValueObject, 1, ()),
    (ModelEntityId, 1, ()),
    (ModelEntity, 1, (ModelAggregateRoot,)),
    (ModelAggregateRoot, 1, ()),
    (ModelDomainEvent, 1, ()),
]


@pytest.mark.parametrize(
    "base,max_depth,exclude_subtrees",
    DEPTH_CONTRACTS,
    ids=[_qualified_name(c[0]) for c in DEPTH_CONTRACTS],
)
def test_inheritance_depth(base: type, max_depth: int, exclude_subtrees: tuple[type, ...]) -> None:
    """Each base class has no subclass chain deeper than its contract allows."""
    excluded: set[type] = set()
    for sub_base in exclude_subtrees:
        excluded.add(sub_base)
        excluded.update(_all_subclasses(sub_base))

    violations: list[tuple[str, int]] = []
    for cls in _all_subclasses(base):
        if cls in excluded or not _is_source(cls):
            continue
        depth = _shortest_depth(cls, base)
        if depth > max_depth:
            violations.append((_qualified_name(cls), depth))

    if violations:
        violations.sort()
        formatted = "\n".join(f"  {name} (depth={d})" for name, d in violations)
        pytest.fail(f"{base.__name__} subclasses exceed max depth {max_depth}:\n{formatted}")


def test_event_dispatcher_has_no_subclasses() -> None:
    """The event dispatcher has no subclasses."""
    subclasses = _all_subclasses(EventDispatcher)
    if subclasses:
        formatted = "\n".join(f"  {_qualified_name(c)}" for c in sorted(subclasses, key=_qualified_name))
        pytest.fail(f"EventDispatcher must not be subclassed:\n{formatted}")


@pytest.mark.parametrize("context", context_names())
def test_aggregate_repos_extend_repository(context: str) -> None:
    """Every ``*Repo`` port class must extend ``base.repository.Repository``."""
    port_dir = context_dir(context) / "application" / "port" / "outbound"
    found: list[type] = []
    for py_file in port_dir.rglob("*_repo.py"):
        rel = py_file.relative_to(BACKEND).with_suffix("")
        module_path = ".".join(rel.parts)
        module = importlib.import_module(module_path)
        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, type) and obj.__module__ == module_path and attr_name.endswith("Repo"):
                found.append(obj)

    violations = [_qualified_name(c) for c in found if not issubclass(c, Repository)]
    if violations:
        formatted = "\n".join(f"  {v}" for v in sorted(violations))
        pytest.fail(f"These *Repo port classes must extend base.repository.Repository:\n{formatted}")


class _ProbeId(ModelEntityId):
    """An id for the parametrization probe."""


class _Probe(ModelAggregateRoot[_ProbeId]):
    """An aggregate whose chain holds two parametrizations."""


def test_a_parametrization_is_not_a_layer() -> None:
    """``AggregateRoot[_ProbeId]`` and ``Entity[ID]`` on the path count zero."""
    assert _shortest_depth(_Probe, ModelAggregateRoot) == 1
    assert _shortest_depth(_Probe, ModelEntity) == 2
