"""Tests for DomainEvent base type."""

from dataclasses import FrozenInstanceError, dataclass
from datetime import UTC, datetime

import pytest
from base import DomainEvent


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    user_id: str
    email: str


def test_domain_event_is_base_class():
    from abc import ABC

    assert issubclass(DomainEvent, ABC)


def test_has_occurred_at():
    before = datetime.now(UTC)
    event = UserRegistered(user_id="1", email="a@example.com")
    after = datetime.now(UTC)
    assert before <= event.occurred_at <= after


def test_immutable():
    event = UserRegistered(user_id="1", email="a@example.com")
    with pytest.raises(FrozenInstanceError):
        event.user_id = "2"  # type: ignore[misc]  # ty: ignore[invalid-assignment]


def test_equal_by_value():
    ts = datetime(2026, 1, 1, tzinfo=UTC)
    a = UserRegistered(user_id="1", email="a@example.com", occurred_at=ts)
    b = UserRegistered(user_id="1", email="a@example.com", occurred_at=ts)
    assert a == b
