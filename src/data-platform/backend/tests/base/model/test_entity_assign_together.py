"""Tests for assigning related entity fields together."""

from __future__ import annotations

import pytest
from pydantic import ValidationError, model_validator

from base.model import AggregateRoot, DomainEvent, EntityId


class _RangeId(EntityId):
    """Test stub for EntityId."""


class _Happened(DomainEvent):
    """Test stub for DomainEvent."""

    note: str


class _Range(AggregateRoot[_RangeId]):
    """Test stub: low must stay below high; label has a default."""

    low: int
    high: int
    label: str = "default"

    @model_validator(mode="after")
    def _ordered(self) -> _Range:
        if self.low >= self.high:
            raise ValueError("low must be below high")
        return self


def _range() -> _Range:
    return _Range(id=_RangeId("1"), low=1, high=2)


def test_single_assignments_cannot_move_a_range_past_itself() -> None:
    """Assigning one related field at a time fails on the half-changed state."""
    r = _range()
    with pytest.raises(ValidationError):
        r.low = 10


def test_assign_together_changes_related_fields_at_once() -> None:
    """Two fields that are valid only together can change in one step."""
    r = _range()
    r._assign_together(low=10, high=20)
    assert (r.low, r.high) == (10, 20)


def test_assign_together_keeps_untouched_defaulted_field() -> None:
    """A field that is not named keeps its current, non-default value."""
    r = _range()
    r.label = "custom"
    r._assign_together(low=10, high=20)
    assert r.label == "custom"
    assert "label" in r.model_fields_set


def test_assign_together_invalid_combination_changes_nothing() -> None:
    """An invalid result raises ValidationError and leaves the entity as it was."""
    r = _range()
    r.label = "custom"
    with pytest.raises(ValidationError, match="low must be below high"):
        r._assign_together(low=30, high=20, label="other")
    assert (r.low, r.high, r.label) == (1, 2, "custom")


def test_assign_together_wrong_type_changes_nothing() -> None:
    """A wrong-typed value is rejected and nothing changes."""
    r = _range()
    with pytest.raises(ValidationError):
        r._assign_together(low="x", high=20)
    assert (r.low, r.high) == (1, 2)


def test_assign_together_unknown_field_raises_type_error() -> None:
    """A field name the entity does not have is rejected."""
    with pytest.raises(TypeError):
        _range()._assign_together(nope=1)


def test_assign_together_keeps_pending_events_and_identity() -> None:
    """Pending events survive, and identity and hash do not change."""
    r = _range()
    event = _Happened(note="x")
    r.register_event(event)
    before = hash(r)
    r._assign_together(low=10, high=20)
    assert r.collect_events() == [event]
    assert hash(r) == before
    assert r.id == _RangeId("1")
