"""Tests that changing an immutable model, or deleting a field, raises AttributeError.

A frozen model changed in place, or a field deleted from any model, is a programming error, not refused
data: it raises Python's ``AttributeError`` (as a frozen dataclass does), never ``InvariantViolation``,
so it surfaces as a server error rather than a 422.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import PrivateAttr

from base import DomainEvent, Entity, EntityId, InvariantViolation, ValueObject

if TYPE_CHECKING:
    from collections.abc import Callable


class _Counter(ValueObject):
    """A value object of one count."""

    value: int


class _CounterChanged(DomainEvent):
    """An event naming a counter."""

    counter_id: str


class _CounterId(EntityId):
    """An id for the test entity."""


class _Tally(Entity[_CounterId]):
    """An entity with a count and a private note."""

    count: int
    _note: str = PrivateAttr(default="")


def _attribute_error(change: Callable[[], object]) -> AttributeError:
    """Run ``change`` and return the AttributeError it raised."""
    with pytest.raises(AttributeError) as caught:
        change()
    assert not isinstance(caught.value, InvariantViolation)
    return caught.value


def test_assigning_to_a_value_object_points_at_with_changes() -> None:
    """A value object changed in place raises AttributeError naming the class and ``with_changes``."""
    counter = _Counter(value=1)
    error = _attribute_error(lambda: setattr(counter, "value", 2))
    assert str(error) == "_Counter is immutable; build a changed copy with with_changes()"
    assert counter.value == 1


def test_assigning_to_a_domain_event_raises_attribute_error() -> None:
    """A domain event changed in place raises AttributeError naming the class."""
    event = _CounterChanged(counter_id="c")
    error = _attribute_error(lambda: setattr(event, "counter_id", "other"))
    assert str(error) == "_CounterChanged is immutable"


def test_assigning_to_an_entity_id_raises_attribute_error() -> None:
    """An entity id changed in place raises AttributeError naming the class."""
    counter_id = _CounterId("c")
    error = _attribute_error(lambda: setattr(counter_id, "root", "other"))
    assert str(error) == "_CounterId is immutable"


def test_deleting_a_value_object_field_raises_attribute_error() -> None:
    """``del`` of a value object's field raises AttributeError and keeps the field."""
    counter = _Counter(value=1)
    error = _attribute_error(lambda: delattr(counter, "value"))
    assert str(error) == "_Counter is immutable; build a changed copy with with_changes()"
    assert counter.value == 1


def test_deleting_a_domain_event_field_raises_attribute_error() -> None:
    """``del`` of a domain event's field raises AttributeError."""
    event = _CounterChanged(counter_id="c")
    error = _attribute_error(lambda: delattr(event, "counter_id"))
    assert str(error) == "_CounterChanged is immutable"


def test_deleting_an_entity_id_root_raises_attribute_error() -> None:
    """``del`` of an entity id's root raises AttributeError."""
    counter_id = _CounterId("c")
    error = _attribute_error(lambda: delattr(counter_id, "root"))
    assert str(error) == "_CounterId is immutable"


def test_deleting_an_entity_field_raises_attribute_error_and_keeps_it() -> None:
    """``del`` of an entity's field raises AttributeError instead of silently removing it."""
    tally = _Tally(id=_CounterId("t"), count=1)
    error = _attribute_error(lambda: delattr(tally, "count"))
    assert str(error) == "_Tally.count is a field and cannot be deleted; assign a new value instead"
    assert tally.count == 1


def test_deleting_an_entity_id_field_raises_attribute_error() -> None:
    """``del`` of an entity's ``id`` raises AttributeError."""
    tally = _Tally(id=_CounterId("t"), count=1)
    _attribute_error(lambda: delattr(tally, "id"))
    assert tally.id == _CounterId("t")


def test_an_entity_private_attribute_can_still_be_deleted() -> None:
    """Private attributes are not fields: deleting one resets it as Pydantic does."""
    tally = _Tally(id=_CounterId("t"), count=1)
    tally._note = "kept"
    del tally._note
    with pytest.raises(AttributeError):
        _ = tally._note


def test_refused_entity_assignment_still_raises_invariant_violation() -> None:
    """An entity assignment of the wrong type is refused data, so it stays an InvariantViolation."""
    tally = _Tally(id=_CounterId("t"), count=1)
    with pytest.raises(InvariantViolation, match="^count: Input should be a valid integer$"):
        tally.count = "two"  # ty: ignore[invalid-assignment]
    assert tally.count == 1
