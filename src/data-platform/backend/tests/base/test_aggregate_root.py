"""Tests for the Pydantic AggregateRoot base type."""

from __future__ import annotations

import pytest

from base import AggregateRoot, DomainEvent, Entity, EntityId


class _OrderId(EntityId):
    """Test stub for EntityId."""


class _OrderPlaced(DomainEvent):
    """Test stub for DomainEvent."""

    order_id: str


class _Order(AggregateRoot[_OrderId]):
    """Test stub for AggregateRoot."""

    total: int


def _order() -> _Order:
    return _Order(id=_OrderId("1"), total=100)


def test_is_an_entity() -> None:
    """An aggregate root is an entity."""
    assert issubclass(AggregateRoot, Entity)


def test_no_events_initially() -> None:
    """A new aggregate has no pending events."""
    assert _order().collect_events() == []


def test_collect_events_returns_registered_events_once() -> None:
    """Registered events come back once, then the list is empty."""
    order = _order()
    event = _OrderPlaced(order_id="1")
    order.register_event(event)
    assert order.collect_events() == [event]
    assert order.collect_events() == []


def test_events_are_not_dumped() -> None:
    """Pending events never appear in a dump."""
    order = _order()
    order.register_event(_OrderPlaced(order_id="1"))
    assert order.model_dump() == {"id": "1", "total": 100}


def test_events_are_not_compared() -> None:
    """Pending events take no part in equality."""
    order = _order()
    order.register_event(_OrderPlaced(order_id="1"))
    assert order == _order()


def test_events_are_per_instance() -> None:
    """Each aggregate keeps its own pending events."""
    order = _order()
    order.register_event(_OrderPlaced(order_id="1"))
    assert _order().collect_events() == []


def test_third_level_subclass_is_rejected() -> None:
    """A concrete aggregate extends AggregateRoot directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_Order):
            pass
