"""Tests for DomainEvent base type."""

from abc import ABC
from dataclasses import dataclass
from datetime import UTC, datetime

from core.base import DomainEvent


@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    """Test stub for DomainEvent."""

    order_id: str
    total: int


def test_domain_event_is_abstract():
    """Verify that DomainEvent is a subclass of ABC."""
    assert issubclass(DomainEvent, ABC)


def test_event_has_occurred_at():
    """Verify that a DomainEvent automatically gets a UTC occurred_at timestamp."""
    event = OrderPlaced(order_id="1", total=100)
    assert isinstance(event.occurred_at, datetime)
    assert event.occurred_at.tzinfo == UTC


def test_event_carries_data():
    """Verify that a DomainEvent stores its custom fields."""
    event = OrderPlaced(order_id="1", total=100)
    assert event.order_id == "1"
    assert event.total == 100


def test_event_is_immutable():
    """Verify that DomainEvent fields cannot be reassigned."""
    import pytest

    event = OrderPlaced(order_id="1", total=100)
    with pytest.raises(AttributeError):
        event.order_id = "2"  # type: ignore[misc]  # ty: ignore[invalid-assignment]


def test_equal_events():
    """Verify that two DomainEvents with the same data are equal."""
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    a = OrderPlaced(order_id="1", total=100, occurred_at=ts)
    b = OrderPlaced(order_id="1", total=100, occurred_at=ts)
    assert a == b
