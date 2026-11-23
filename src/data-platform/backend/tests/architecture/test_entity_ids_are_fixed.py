"""Guard test: no entity of any context can have its id reassigned.

Every real entity redeclares ``id`` with its own id type, so the guard must hold for a
redeclared field, not only for the one ``Entity`` declares.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

from base import AggregateRoot, Entity
from tests.architecture.contexts import context_module, context_names


def _entity_classes() -> list[type[Entity]]:
    found: dict[str, type[Entity]] = {}
    for name in context_names():
        model = importlib.import_module(f"{context_module(name)}.application.domain.model")
        for info in pkgutil.walk_packages(model.__path__, prefix=f"{model.__name__}."):
            module = importlib.import_module(info.name)
            for value in vars(module).values():
                if (
                    isinstance(value, type)
                    and issubclass(value, Entity)
                    and value not in (Entity, AggregateRoot)
                    and value.__module__ == module.__name__
                ):
                    found[f"{value.__module__}.{value.__qualname__}"] = value
    return [found[key] for key in sorted(found)]


_ENTITIES = _entity_classes()


def test_the_scan_finds_the_entities_of_every_context() -> None:
    """Every context contributes entities, so an empty scan cannot pass for a safe one."""
    for name in context_names():
        assert any(cls.__module__.startswith(context_module(name)) for cls in _ENTITIES), name


@pytest.mark.parametrize("cls", _ENTITIES, ids=lambda cls: cls.__qualname__)
def test_an_entitys_id_cannot_be_reassigned(cls: type[Entity]) -> None:
    """Assigning the id of any real entity raises ``AttributeError``, whatever the value."""
    entity = cls.model_construct(id=object())
    with pytest.raises(AttributeError, match=f"^{cls.__name__} is immutable"):
        entity.id = object()
