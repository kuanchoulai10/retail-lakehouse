"""Guard test: no domain model field holds a collection that can be edited in place.

A list, dict or set field lets any holder change an aggregate without calling its methods
(``table.operation_states[op] = state``). Domain model fields hold ``tuple[X, ...]``,
``frozenset[X]`` or ``ReadOnlyMapping[K, V]`` instead, all the way down, so the only way to
change one is to assign a new collection, which only the aggregate's own methods do.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import MutableMapping, MutableSequence, MutableSet
from typing import Any, TypeAliasType, get_args, get_origin

import pytest

from base import AggregateRoot, DomainEvent, Entity, ReadOnlyMapping, ValueObject
from tests.architecture.contexts import context_module, context_names

_MUTABLE = (MutableMapping, MutableSequence, MutableSet)
_BASES = (Entity, AggregateRoot, ValueObject, DomainEvent)


def mutable_collection_fields(cls: type[Any]) -> list[str]:
    """Return ``"<field>: <annotation>"`` for each field of ``cls`` whose type holds a mutable collection."""
    return [
        f"{name}: {field.annotation}"
        for name, field in cls.model_fields.items()
        if _holds_mutable_collection(field.annotation)
    ]


def _holds_mutable_collection(annotation: object) -> bool:
    origin = get_origin(annotation)
    if origin is ReadOnlyMapping:
        return any(_holds_mutable_collection(arg) for arg in get_args(annotation))
    if isinstance(origin, TypeAliasType):
        return _holds_mutable_collection(origin.__value__) or any(
            _holds_mutable_collection(arg) for arg in get_args(annotation)
        )
    if isinstance(annotation, TypeAliasType):
        return _holds_mutable_collection(annotation.__value__)
    head = origin if origin is not None else annotation
    if isinstance(head, type) and issubclass(head, _MUTABLE):
        return True
    return any(_holds_mutable_collection(arg) for arg in get_args(annotation))


def _domain_models() -> list[type[Any]]:
    found: dict[str, type[Any]] = {}
    for name in context_names():
        model = importlib.import_module(f"{context_module(name)}.application.domain.model")
        for info in pkgutil.walk_packages(model.__path__, prefix=f"{model.__name__}."):
            module = importlib.import_module(info.name)
            for value in vars(module).values():
                if (
                    isinstance(value, type)
                    and issubclass(value, _BASES)
                    and value not in _BASES
                    and value.__module__ == module.__name__
                ):
                    found[f"{value.__module__}.{value.__qualname__}"] = value
    return [found[key] for key in sorted(found)]


_MODELS = _domain_models()


def test_the_scan_finds_models_of_every_context() -> None:
    """Every context contributes models, so an empty scan cannot pass for a safe one."""
    for name in context_names():
        assert any(cls.__module__.startswith(context_module(name)) for cls in _MODELS), name


@pytest.mark.parametrize("cls", _MODELS, ids=lambda cls: cls.__qualname__)
def test_domain_model_collections_are_immutable(cls: type[Any]) -> None:
    """No field of any domain model holds a list, dict or set, however deep."""
    assert mutable_collection_fields(cls) == []


class _Flagged(ValueObject):
    """Test stub: every field holds a mutable collection somewhere."""

    a: list[int]
    b: dict[str, int] | None
    c: tuple[list[int], ...]
    d: ReadOnlyMapping[str, list[int]]
    e: set[str]
    f: ReadOnlyMapping[str, tuple[dict[str, int], ...]]


class _Fine(ValueObject):
    """Test stub: no field holds a mutable collection."""

    a: tuple[int, ...]
    b: frozenset[str]
    c: ReadOnlyMapping[str, int]
    d: str
    e: int | None
    f: ReadOnlyMapping[str, tuple[ReadOnlyMapping[str, int], ...]] | None


def test_the_check_flags_every_mutable_collection() -> None:
    """A list, dict or set anywhere in a field's type is flagged, inside unions, tuples and mappings too."""
    assert [entry.split(":")[0] for entry in mutable_collection_fields(_Flagged)] == ["a", "b", "c", "d", "e", "f"]


def test_the_check_passes_immutable_collections() -> None:
    """Tuples, frozensets, read-only mappings and scalars pass."""
    assert mutable_collection_fields(_Fine) == []
