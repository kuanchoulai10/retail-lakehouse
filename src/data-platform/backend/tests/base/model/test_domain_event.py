"""Tests for the Pydantic DomainEvent base type."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from base.model import DomainEvent


class _OrderPlaced(DomainEvent):
    """Test stub for DomainEvent."""

    order_id: str
    total: int


def test_occurred_at_defaults_to_now_in_utc() -> None:
    """``occurred_at`` is set to the current UTC time."""
    before = datetime.now(UTC)
    event = _OrderPlaced(order_id="1", total=100)
    assert event.occurred_at.tzinfo is UTC
    assert before <= event.occurred_at <= datetime.now(UTC)


def test_occurred_at_can_be_given() -> None:
    """``occurred_at`` can be set explicitly."""
    moment = datetime(2026, 1, 1, tzinfo=UTC)
    assert _OrderPlaced(order_id="1", total=100, occurred_at=moment).occurred_at == moment


def test_is_frozen() -> None:
    """An event rejects assignment."""
    event = _OrderPlaced(order_id="1", total=100)
    with pytest.raises(ValidationError):
        event.total = 5


def test_strict_rejects_a_bool_for_an_int() -> None:
    """Strict mode rejects a bool where an int is expected."""
    with pytest.raises(ValidationError):
        _OrderPlaced.model_validate({"order_id": "1", "total": True})


def test_rejects_an_unknown_key() -> None:
    """``extra="forbid"`` rejects a key that is not a field."""
    with pytest.raises(ValidationError):
        _OrderPlaced.model_validate({"order_id": "1", "total": 1, "colour": "red"})


def test_third_level_subclass_is_rejected() -> None:
    """A concrete event extends DomainEvent directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_OrderPlaced):
            pass
