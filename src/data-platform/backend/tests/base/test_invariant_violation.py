"""Tests for InvariantViolation and the model bases raising it."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Self

import pytest
from pydantic import ValidationError, field_validator, model_validator

from base import DomainEvent, Entity, EntityId, InvariantViolation, ValueObject

if TYPE_CHECKING:
    from collections.abc import Callable


class _Inner(ValueObject):
    """A nested value object with a positive count."""

    count: int

    @field_validator("count")
    @classmethod
    def _count_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value


class _Settings(ValueObject):
    """A value object with a field rule, a nested object and a model rule."""

    min_interval: int
    inner: _Inner | None = None
    enabled: bool = True

    @field_validator("min_interval")
    @classmethod
    def _min_interval_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value

    @model_validator(mode="after")
    def _enabled_needs_inner(self) -> Self:
        if self.enabled and self.inner is None:
            raise ValueError("an enabled setting needs inner")
        return self


class _Wrapper(ValueObject):
    """A value object whose validator builds an inner value object itself."""

    raw_count: int

    @field_validator("raw_count")
    @classmethod
    def _builds_inner(cls, value: int) -> int:
        _Inner(count=value)
        return value


class _ThingId(EntityId):
    """An id for the test entity."""


class _Thing(Entity[_ThingId]):
    """An entity with a positive size."""

    size: int

    @field_validator("size")
    @classmethod
    def _size_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("must be positive")
        return value


class _ThingHappened(DomainEvent):
    """An event naming the thing."""

    thing_id: str


def _pydantic_error(**data: object) -> ValidationError:
    """Return the raw Pydantic error the validator gives for ``data``."""
    with pytest.raises(ValidationError) as caught:
        _Settings.__pydantic_validator__.validate_json(json.dumps(data), by_alias=True, by_name=False)
    return caught.value


def _violation(build: Callable[[], object]) -> InvariantViolation:
    """Run ``build`` and return the InvariantViolation it raised, chained from Pydantic's error."""
    with pytest.raises(InvariantViolation) as caught:
        build()
    assert not isinstance(caught.value, ValidationError)
    assert isinstance(caught.value.__cause__, ValidationError)
    return caught.value


def test_message_is_the_string() -> None:
    """An InvariantViolation built with a line reads as that line."""
    assert str(InvariantViolation("bad value")) == "bad value"


def test_invariant_violation_is_a_value_error() -> None:
    """Callers that catch ValueError keep working."""
    assert issubclass(InvariantViolation, ValueError)


def test_field_error_is_loc_and_message() -> None:
    """A field rule reads ``<field>: <message>`` without Pydantic's prefix."""
    assert str(InvariantViolation.from_error(_pydantic_error(min_interval=0))) == "min_interval: must be positive"


def test_nested_error_uses_a_dotted_loc() -> None:
    """A nested field error names its dotted path."""
    error = _pydantic_error(min_interval=1, inner={"count": 0})
    assert str(InvariantViolation.from_error(error)) == "inner.count: must be positive"


def test_model_error_has_no_loc() -> None:
    """A model-level rule is the message alone."""
    assert str(InvariantViolation.from_error(_pydantic_error(min_interval=1))) == "an enabled setting needs inner"


def test_only_the_first_error_is_reported() -> None:
    """Several errors still give one line."""
    error = _pydantic_error(min_interval=0, enabled="yes")
    assert str(InvariantViolation.from_error(error)) == "min_interval: must be positive"


def test_a_plain_value_error_is_its_text() -> None:
    """Any other ``ValueError`` is its string."""
    assert str(InvariantViolation.from_error(ValueError("bad value"))) == "bad value"


def test_validation_error_without_details_falls_back_to_str() -> None:
    """A ValidationError that lists no errors yields its own text."""
    exc = ValidationError.from_exception_data("Empty", [])
    assert str(InvariantViolation.from_error(exc)) == str(exc)


def test_value_object_construction_raises_invariant_violation() -> None:
    """Building a value object in code with a broken rule raises one InvariantViolation."""
    violation = _violation(lambda: _Settings(min_interval=0, inner=_Inner(count=1)))
    assert str(violation) == "min_interval: must be positive"


def test_from_primitives_raises_invariant_violation() -> None:
    """Wire input with a broken nested rule raises one InvariantViolation naming the dotted field."""
    violation = _violation(lambda: _Settings.from_primitives({"min_interval": 1, "inner": {"count": 0}}))
    assert str(violation) == "inner.count: must be positive"


def test_from_primitives_of_non_json_input_raises_invariant_violation() -> None:
    """Input that is not JSON-compatible is an InvariantViolation too."""
    with pytest.raises(InvariantViolation, match="must be JSON-compatible primitives"):
        _Settings.from_primitives({"min_interval": datetime(2026, 1, 1)})  # noqa: DTZ001


def test_model_validate_raises_invariant_violation() -> None:
    """``model_validate`` of invalid data raises InvariantViolation."""
    violation = _violation(lambda: _Settings.model_validate({"min_interval": 1}))
    assert str(violation) == "an enabled setting needs inner"


def test_model_validate_json_raises_invariant_violation() -> None:
    """``model_validate_json`` of invalid data raises InvariantViolation."""
    violation = _violation(lambda: _Settings.model_validate_json('{"min_interval": 0, "inner": {"count": 1}}'))
    assert str(violation) == "min_interval: must be positive"


def test_with_changes_raises_invariant_violation() -> None:
    """A changed copy that breaks a rule raises InvariantViolation."""
    settings = _Settings(min_interval=1, inner=_Inner(count=1))
    violation = _violation(lambda: settings.with_changes(min_interval=0))
    assert str(violation) == "min_interval: must be positive"


def test_inner_violation_inside_a_validator_comes_out_once() -> None:
    """An inner value object's violation raised inside an outer validator is one InvariantViolation."""
    violation = _violation(lambda: _Wrapper(raw_count=0))
    assert str(violation) == "raw_count: count: must be positive"


def test_entity_assignment_raises_invariant_violation() -> None:
    """An entity assignment that breaks a rule raises InvariantViolation and leaves the entity unchanged."""
    thing = _Thing(id=_ThingId("t"), size=1)
    violation = _violation(lambda: setattr(thing, "size", 0))
    assert str(violation) == "size: must be positive"
    assert thing.size == 1


def test_entity_construction_raises_invariant_violation() -> None:
    """Building an entity with a broken rule raises InvariantViolation."""
    violation = _violation(lambda: _Thing(id=_ThingId("t"), size=0))
    assert str(violation) == "size: must be positive"


def test_entity_id_raises_invariant_violation() -> None:
    """An id built from a non-string raises InvariantViolation."""
    violation = _violation(lambda: _ThingId(1))  # ty: ignore[invalid-argument-type]
    assert str(violation) == "Input should be a valid string"


def test_domain_event_construction_raises_invariant_violation() -> None:
    """An event built with a wrong field type raises InvariantViolation."""
    violation = _violation(lambda: _ThingHappened(thing_id=1))  # ty: ignore[invalid-argument-type]
    assert str(violation) == "thing_id: Input should be a valid string"
