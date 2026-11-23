"""Test that the model bases pass Pydantic's validation options through, as Pydantic would take them."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

import pytest
from pydantic import Field, ValidationInfo, field_validator

from base import InvariantViolation, ValueObject


class _Sample(ValueObject):
    """A strict value object with an aliased field and a validator that reads the context."""

    count: int
    label: str = Field(default="", alias="name")
    day: date | None = None

    @field_validator("count")
    @classmethod
    def _within_the_context_limit(cls, value: int, info: ValidationInfo) -> int:
        limit = (info.context or {}).get("limit")
        if limit is not None and value > limit:
            raise ValueError(f"count is over {limit}")
        return value


def _by_dict(data: dict[str, Any], **options: Any) -> _Sample:  # noqa: ANN401
    return _Sample.model_validate(data, **options)


def _by_json(data: dict[str, Any], **options: Any) -> _Sample:  # noqa: ANN401
    return _Sample.model_validate_json(json.dumps(data), **options)


def _by_strings(data: dict[str, Any], **options: Any) -> _Sample:  # noqa: ANN401
    return _Sample.model_validate_strings({k: str(v) for k, v in data.items()}, **options)


VALIDATORS = pytest.mark.parametrize("validate", [_by_dict, _by_json, _by_strings], ids=["dict", "json", "strings"])


@pytest.mark.parametrize(
    ("validate", "data"),
    [
        (_by_dict, {"count": "1"}),
        (_by_json, {"count": "1"}),
        (_by_strings, {"count": 1, "day": "2026-01-01T00:00:00"}),
    ],
    ids=["dict", "json", "strings"],
)
def test_strict_false_is_passed_through(validate, data: dict[str, Any]) -> None:  # noqa: ANN001
    """``strict=False`` lets a value through that the strict default refuses."""
    with pytest.raises(InvariantViolation):
        validate(data)
    assert validate(data, strict=False).count == 1


@VALIDATORS
def test_extra_is_passed_through(validate) -> None:  # noqa: ANN001
    """``extra="ignore"`` drops an unknown key the default refuses."""
    with pytest.raises(InvariantViolation):
        validate({"count": 1, "other": 2})
    assert validate({"count": 1, "other": 2}, extra="ignore") == _Sample(count=1)


@VALIDATORS
def test_context_is_passed_through(validate) -> None:  # noqa: ANN001
    """The context reaches the validators."""
    assert validate({"count": 5}).count == 5
    with pytest.raises(InvariantViolation, match="count is over 3"):
        validate({"count": 5}, context={"limit": 3})


@VALIDATORS
def test_by_alias_is_passed_through(validate) -> None:  # noqa: ANN001
    """``by_alias=False`` refuses the alias the default accepts."""
    assert validate({"count": 1, "name": "a"}).label == "a"
    with pytest.raises(InvariantViolation):
        validate({"count": 1, "name": "a"}, by_alias=False, by_name=True)


@VALIDATORS
def test_by_name_is_passed_through(validate) -> None:  # noqa: ANN001
    """``by_name=False`` refuses the field name the default accepts."""
    assert validate({"count": 1, "label": "a"}).label == "a"
    with pytest.raises(InvariantViolation):
        validate({"count": 1, "label": "a"}, by_alias=True, by_name=False)


def test_from_attributes_is_passed_through() -> None:
    """``from_attributes=True`` reads an object's attributes, which the default refuses."""

    class _Source:
        count = 2
        name = "b"

    with pytest.raises(InvariantViolation):
        _Sample.model_validate(_Source())
    assert _Sample.model_validate(_Source(), from_attributes=True) == _Sample(count=2, label="b")
