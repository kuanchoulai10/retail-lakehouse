"""Tests for the Pydantic ValueObject base type."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

import pytest
from pydantic import Field, ValidationError

from base.model import ValueObject, WholeSeconds


class _Unit(StrEnum):
    """Test enum carried by a value object."""

    HOUR = "hour"
    DAY = "day"


class _Schedule(ValueObject):
    """A value object with an enum, a duration on a ``*_seconds`` key and an int."""

    unit: _Unit
    min_interval: WholeSeconds = Field(
        validation_alias="min_interval_seconds", serialization_alias="min_interval_seconds"
    )
    retries: int = 0


def _schedule() -> _Schedule:
    return _Schedule(unit=_Unit.HOUR, min_interval=timedelta(hours=1), retries=2)


def test_equal_by_value() -> None:
    """Two value objects with the same fields are equal and hash alike."""
    assert _schedule() == _schedule()
    assert hash(_schedule()) == hash(_schedule())


def test_is_frozen() -> None:
    """A value object rejects assignment."""
    schedule = _schedule()
    with pytest.raises(ValidationError):
        schedule.retries = 3


def test_rejects_an_unknown_key() -> None:
    """``extra="forbid"`` rejects a key that is not a field."""
    with pytest.raises(ValidationError, match="extra"):
        _Schedule.from_primitives({"unit": "hour", "min_interval_seconds": 3600, "colour": "red"})


def test_from_primitives_rejects_a_bool_for_an_int() -> None:
    """Strict mode rejects ``true`` where an integer is expected."""
    with pytest.raises(ValidationError, match="retries"):
        _Schedule.from_primitives({"unit": "hour", "min_interval_seconds": 3600, "retries": True})


def test_from_primitives_reads_wire_values() -> None:
    """Enums arrive as their string value and durations as integer seconds."""
    schedule = _Schedule.from_primitives({"unit": "hour", "min_interval_seconds": 3600, "retries": 2})
    assert schedule == _schedule()


def test_from_primitives_accepts_the_field_name() -> None:
    """The field name is accepted beside its ``*_seconds`` alias."""
    schedule = _Schedule.from_primitives({"unit": "hour", "min_interval": 3600, "retries": 2})
    assert schedule.min_interval == timedelta(hours=1)


def test_to_primitives_writes_wire_values() -> None:
    """``to_primitives`` writes enum values, integer seconds and the alias key."""
    assert _schedule().to_primitives() == {"unit": "hour", "min_interval_seconds": 3600, "retries": 2}


def test_primitives_round_trip() -> None:
    """``from_primitives`` reads back what ``to_primitives`` wrote."""
    assert _Schedule.from_primitives(_schedule().to_primitives()) == _schedule()


def test_third_level_subclass_is_rejected() -> None:
    """A concrete value object extends ValueObject directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_Schedule):
            pass
