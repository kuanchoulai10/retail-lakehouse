"""Tests for the Pydantic UseCaseInput base type."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from base import InvariantViolation, UseCaseInput

if TYPE_CHECKING:
    from collections.abc import Mapping


class _ListCommitsUseCaseInput(UseCaseInput):
    """An input with an int, an optional datetime and a tuple of nested filters."""

    class Filter(UseCaseInput):
        """One filter of the request."""

        key: str
        value: str

    uuid: str
    limit: int = 100
    since: datetime | None = None
    writers: tuple[str, ...] = ()
    filters: tuple[Filter, ...] = ()


def test_strict_refuses_a_string_for_an_int() -> None:
    """Strict mode refuses ``"1"`` for an int field."""
    with pytest.raises(InvariantViolation, match="limit"):
        _ListCommitsUseCaseInput(uuid="u", limit="1")  # ty: ignore[invalid-argument-type]


def test_strict_refuses_a_bool_for_an_int() -> None:
    """Strict mode refuses ``True`` for an int field."""
    with pytest.raises(InvariantViolation, match="limit"):
        _ListCommitsUseCaseInput(uuid="u", limit=True)


def test_construction_error_is_one_line_chained_from_pydantic() -> None:
    """A refused construction raises InvariantViolation, a ValueError chained from Pydantic's error."""
    with pytest.raises(InvariantViolation) as caught:
        _ListCommitsUseCaseInput(uuid="u", limit="1")  # ty: ignore[invalid-argument-type]
    assert isinstance(caught.value, ValueError)
    assert isinstance(caught.value.__cause__, ValidationError)
    assert "\n" not in str(caught.value)


def test_model_validate_raises_invariant_violation() -> None:
    """``model_validate`` raises InvariantViolation, never Pydantic's ValidationError."""
    with pytest.raises(InvariantViolation):
        _ListCommitsUseCaseInput.model_validate({"uuid": 1})


def test_rejects_an_unknown_key() -> None:
    """``extra="forbid"`` rejects a key that is not a field."""
    with pytest.raises(InvariantViolation, match="colour"):
        _ListCommitsUseCaseInput(uuid="u", colour="red")  # ty: ignore[unknown-argument]


def test_is_frozen() -> None:
    """Assigning to a field raises AttributeError naming the class."""
    request = _ListCommitsUseCaseInput(uuid="u")
    with pytest.raises(AttributeError, match="_ListCommitsUseCaseInput is immutable"):
        request.limit = 5
    assert request.limit == 100


def test_deleting_a_field_raises_attribute_error() -> None:
    """``del`` of a field raises AttributeError."""
    request = _ListCommitsUseCaseInput(uuid="u")
    with pytest.raises(AttributeError, match="is immutable"):
        del request.limit


def test_equal_and_hashable_by_value() -> None:
    """Two inputs with the same values are equal and hash alike."""
    first = _ListCommitsUseCaseInput(uuid="u", writers=("spark",))
    second = _ListCommitsUseCaseInput(uuid="u", writers=("spark",))
    assert first == second
    assert hash(first) == hash(second)


def test_from_primitives_reads_an_iso_datetime() -> None:
    """An ISO 8601 string becomes a ``datetime`` with its offset."""
    request = _ListCommitsUseCaseInput.from_primitives({"uuid": "u", "since": "2026-11-18T09:30:00+00:00"})
    assert request.since == datetime(2026, 11, 18, 9, 30, tzinfo=UTC)


def test_from_primitives_reads_a_list_into_a_tuple_field() -> None:
    """A JSON array becomes a ``tuple`` field."""
    request = _ListCommitsUseCaseInput.from_primitives({"uuid": "u", "writers": ["spark", "flink"]})
    assert request.writers == ("spark", "flink")


def test_from_primitives_reads_nested_classes() -> None:
    """An array of objects becomes a tuple of the nested class."""
    request = _ListCommitsUseCaseInput.from_primitives({"uuid": "u", "filters": [{"key": "k", "value": "v"}]})
    assert request.filters == (_ListCommitsUseCaseInput.Filter(key="k", value="v"),)


def test_from_primitives_stays_strict() -> None:
    """Strict JSON mode still refuses ``"1"`` for an int field."""
    with pytest.raises(InvariantViolation, match="limit"):
        _ListCommitsUseCaseInput.from_primitives({"uuid": "u", "limit": "1"})


def test_from_primitives_rejects_an_unknown_key() -> None:
    """An unknown key is refused at every nesting level."""
    with pytest.raises(InvariantViolation, match="colour"):
        _ListCommitsUseCaseInput.from_primitives({"uuid": "u", "filters": [{"key": "k", "value": "v", "colour": 1}]})


@pytest.mark.parametrize(
    "data",
    [
        MappingProxyType({"uuid": "u"}),
        {"uuid": "u", "since": datetime(2026, 11, 18, tzinfo=UTC)},
        {"uuid": "u", "limit": timedelta(hours=1)},
        {"uuid": "u", "limit": float("nan")},
        {"uuid": "u", "limit": float("inf")},
    ],
)
def test_from_primitives_rejects_non_json_input(data: Mapping[str, Any]) -> None:
    """Input that is not JSON-compatible primitives raises InvariantViolation, a ValueError."""
    with pytest.raises(InvariantViolation, match="JSON-compatible"):
        _ListCommitsUseCaseInput.from_primitives(data)


def test_a_nested_class_is_a_direct_subclass() -> None:
    """A nested class of an input extends UseCaseInput directly."""
    assert _ListCommitsUseCaseInput.Filter.__bases__ == (UseCaseInput,)


def test_second_level_subclass_is_rejected() -> None:
    """A concrete input extends UseCaseInput directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_ListCommitsUseCaseInput):
            pass
