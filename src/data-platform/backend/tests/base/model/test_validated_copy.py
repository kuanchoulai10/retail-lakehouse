"""Tests for validated_copy."""

from __future__ import annotations

from typing import Self

import pytest
from pydantic import ValidationError, model_validator

from base.model import ValueObject, validated_copy


class _Range(ValueObject):
    """A value object whose model validator checks two fields together."""

    low: int
    high: int

    @model_validator(mode="after")
    def _low_not_above_high(self) -> Self:
        if self.low > self.high:
            raise ValueError("low must not exceed high")
        return self


def test_applies_the_changes() -> None:
    """The copy carries the changed field and keeps the others."""
    assert validated_copy(_Range(low=1, high=5), high=9) == _Range(low=1, high=9)


def test_leaves_the_original_alone() -> None:
    """The original is unchanged."""
    original = _Range(low=1, high=5)
    validated_copy(original, high=9)
    assert original == _Range(low=1, high=5)


def test_runs_model_validators() -> None:
    """A change that breaks a cross-field rule raises."""
    with pytest.raises(ValidationError, match="low must not exceed high"):
        validated_copy(_Range(low=1, high=5), low=7)


def test_runs_field_validation() -> None:
    """A change of the wrong type raises."""
    with pytest.raises(ValidationError):
        validated_copy(_Range(low=1, high=5), low="7")


def test_unknown_field_raises() -> None:
    """A change to a field that does not exist raises."""
    with pytest.raises(TypeError, match="colour"):
        validated_copy(_Range(low=1, high=5), colour="red")
