"""Tests for the Pydantic ValueObject base type."""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Self

import pytest
from pydantic import Field, ValidationError, model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared import WholeSeconds

if TYPE_CHECKING:
    from collections.abc import Mapping


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


class _Plan(ValueObject):
    """A value object nesting another one."""

    schedule: _Schedule


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


def test_from_primitives_rejects_the_field_name() -> None:
    """The wire form accepts only the ``*_seconds`` alias, never the field name."""
    with pytest.raises(ValidationError, match="min_interval_seconds"):
        _Schedule.from_primitives({"unit": "hour", "min_interval": 3600, "retries": 2})


def test_from_primitives_rejects_a_nested_field_name() -> None:
    """A nested value object read from the wire also accepts only its aliases."""
    with pytest.raises(ValidationError, match="schedule.min_interval_seconds"):
        _Plan.from_primitives({"schedule": {"unit": "hour", "min_interval": 3600}})


def test_from_primitives_reads_a_nested_alias() -> None:
    """A nested value object reads its aliases from the wire."""
    plan = _Plan.from_primitives({"schedule": {"unit": "hour", "min_interval_seconds": 3600, "retries": 2}})
    assert plan.schedule == _schedule()


def test_constructor_takes_the_field_name() -> None:
    """Code builds a value object by field name."""
    assert _Schedule(unit=_Unit.HOUR, min_interval=timedelta(hours=1)).min_interval == timedelta(hours=1)


def test_to_primitives_writes_wire_values() -> None:
    """``to_primitives`` writes enum values, integer seconds and the alias key."""
    assert _schedule().to_primitives() == {"unit": "hour", "min_interval_seconds": 3600, "retries": 2}


def test_primitives_round_trip() -> None:
    """``from_primitives`` reads back what ``to_primitives`` wrote."""
    assert _Schedule.from_primitives(_schedule().to_primitives()) == _schedule()


@pytest.mark.parametrize(
    "data",
    [
        MappingProxyType({"unit": "hour", "min_interval_seconds": 3600}),
        {"unit": "hour", "min_interval_seconds": timedelta(hours=1)},
    ],
)
def test_from_primitives_rejects_non_json_input_as_a_value_error(data: Mapping[str, Any]) -> None:
    """Input that is not JSON-compatible primitives is a ValueError (a 422), not a TypeError (a 500)."""
    with pytest.raises(ValueError, match="JSON-compatible"):
        _Schedule.from_primitives(data)


def test_third_level_subclass_is_rejected() -> None:
    """A concrete value object extends ValueObject directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_Schedule):
            pass


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_from_primitives_rejects_non_finite_numbers(bad: float) -> None:
    """NaN and Infinity are not JSON; they raise ValueError."""
    with pytest.raises(ValueError, match="JSON"):
        _Schedule.from_primitives({"unit": "hour", "min_interval_seconds": 3600, "retries": bad})


class _Range(ValueObject):
    """A value object whose model validator checks two fields together."""

    low: int
    high: int

    @model_validator(mode="after")
    def _low_not_above_high(self) -> Self:
        if self.low > self.high:
            raise ValueError("low must not exceed high")
        return self


def test_with_changes_applies_the_changes() -> None:
    """The copy carries the changed field and keeps the others."""
    assert _Range(low=1, high=5).with_changes(high=9) == _Range(low=1, high=9)


def test_with_changes_leaves_the_original_alone() -> None:
    """The original is unchanged."""
    original = _Range(low=1, high=5)
    original.with_changes(high=9)
    assert original == _Range(low=1, high=5)


def test_with_changes_runs_model_validators() -> None:
    """A change that breaks a cross-field rule raises."""
    with pytest.raises(ValidationError, match="low must not exceed high"):
        _Range(low=1, high=5).with_changes(low=7)


def test_with_changes_runs_field_validation() -> None:
    """A change of the wrong type raises."""
    with pytest.raises(ValidationError):
        _Range(low=1, high=5).with_changes(low="7")


def test_with_changes_unknown_field_raises() -> None:
    """A change to a field that does not exist raises, naming the class."""
    with pytest.raises(TypeError, match="_Range has no field colour"):
        _Range(low=1, high=5).with_changes(colour="red")
