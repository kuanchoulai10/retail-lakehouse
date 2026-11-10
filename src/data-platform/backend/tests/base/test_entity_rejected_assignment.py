"""Tests that a rejected assignment leaves an Entity unchanged."""

from __future__ import annotations

import pytest
from pydantic import ValidationError, model_validator

from base import AggregateRoot, DomainEvent, Entity, EntityId


class BoxId(EntityId):
    """Identify a Box."""


class Box(Entity[BoxId]):
    """Hold a low and a high that must stay ordered."""

    low: int = 0
    high: int = 10

    @model_validator(mode="after")
    def _ordered(self) -> Box:
        if self.low > self.high:
            raise ValueError("low must not exceed high")
        return self


class Opened(DomainEvent):
    """Signal that a crate was opened."""


class Crate(AggregateRoot[BoxId]):
    """Hold a size and pending events."""

    size: int = 1

    @model_validator(mode="after")
    def _positive(self) -> Crate:
        if self.size < 0:
            raise ValueError("size must not be negative")
        return self


def test_rejected_cross_field_assignment_keeps_value_and_fields_set():
    """A rejected cross-field assignment changes neither value nor fields_set."""
    box = Box(id=BoxId("b"))
    before = set(box.model_fields_set)
    with pytest.raises(ValidationError):
        box.low = 99
    assert box.low == 0
    assert box.model_fields_set == before


def test_rejected_type_assignment_keeps_value():
    """A rejected wrong-type assignment keeps the old value."""
    box = Box(id=BoxId("b"))
    with pytest.raises(ValidationError):
        box.low = "x"  # ty: ignore[invalid-assignment]
    assert box.low == 0
    assert "low" not in box.model_fields_set


def test_valid_assignment_still_works():
    """A valid assignment is applied."""
    box = Box(id=BoxId("b"))
    box.low = 5
    assert box.low == 5
    assert "low" in box.model_fields_set


def test_pending_events_survive_rejected_assignment():
    """A rejected assignment keeps the pending events."""
    crate = Crate(id=BoxId("c"))
    event = Opened()
    crate.register_event(event)
    with pytest.raises(ValidationError):
        crate.size = -1
    assert crate.size == 1
    assert crate.collect_events() == [event]
