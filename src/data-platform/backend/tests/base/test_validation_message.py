"""Tests for validation_message."""

from __future__ import annotations

from typing import Self

import pytest
from pydantic import ValidationError, field_validator, model_validator

from base import ValueObject, validation_message


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


def _error(**data: object) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        _Settings.from_primitives(data)
    return caught.value


def test_field_error_is_loc_and_message() -> None:
    """A field rule reads ``<field>: <message>`` without Pydantic's prefix."""
    assert validation_message(_error(min_interval=0)) == "min_interval: must be positive"


def test_nested_error_uses_a_dotted_loc() -> None:
    """A nested field error names its dotted path."""
    assert validation_message(_error(min_interval=1, inner={"count": 0})) == "inner.count: must be positive"


def test_model_error_has_no_loc() -> None:
    """A model-level rule is the message alone."""
    assert validation_message(_error(min_interval=1)) == "an enabled setting needs inner"


def test_only_the_first_error_is_reported() -> None:
    """Several errors still give one line."""
    message = validation_message(_error(min_interval=0, enabled="yes"))
    assert message == "min_interval: must be positive"


def test_a_plain_value_error_is_its_text() -> None:
    """Any other ``ValueError`` is its string."""
    assert validation_message(ValueError("bad value")) == "bad value"
