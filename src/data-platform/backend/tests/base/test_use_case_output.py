"""Tests for the Pydantic UseCaseOutput base type."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from base import InvariantViolation, UseCaseOutput


class _ListCommitsUseCaseOutput(UseCaseOutput):
    """An output of nested commits and a flag."""

    class Commit(UseCaseOutput):
        """One commit of the table."""

        snapshot_id: int
        committed_at: datetime

    commits: tuple[Commit, ...]
    truncated: bool


def _commit() -> _ListCommitsUseCaseOutput.Commit:
    return _ListCommitsUseCaseOutput.Commit(snapshot_id=1, committed_at=datetime(2026, 11, 18, tzinfo=UTC))


def test_builds_with_nested_classes() -> None:
    """An output holds a tuple of its nested class."""
    output = _ListCommitsUseCaseOutput(commits=(_commit(),), truncated=False)
    assert output.commits[0].snapshot_id == 1


def test_strict_refuses_a_string_for_an_int() -> None:
    """Strict mode refuses ``"1"`` for an int field."""
    with pytest.raises(InvariantViolation, match="snapshot_id"):
        _ListCommitsUseCaseOutput.Commit(
            snapshot_id="1",  # ty: ignore[invalid-argument-type]
            committed_at=datetime(2026, 11, 18, tzinfo=UTC),
        )


def test_strict_refuses_a_list_for_a_tuple() -> None:
    """Strict mode refuses a ``list`` for a ``tuple`` field, so services pass the declared type."""
    with pytest.raises(InvariantViolation, match="commits"):
        _ListCommitsUseCaseOutput(commits=[_commit()], truncated=False)  # ty: ignore[invalid-argument-type]


def test_construction_error_is_one_line_chained_from_pydantic() -> None:
    """A refused construction raises InvariantViolation, a ValueError chained from Pydantic's error."""
    with pytest.raises(InvariantViolation) as caught:
        _ListCommitsUseCaseOutput(commits=(), truncated="no")  # ty: ignore[invalid-argument-type]
    assert isinstance(caught.value, ValueError)
    assert isinstance(caught.value.__cause__, ValidationError)
    assert "\n" not in str(caught.value)


def test_rejects_an_unknown_key() -> None:
    """``extra="forbid"`` rejects a key that is not a field."""
    with pytest.raises(InvariantViolation, match="colour"):
        _ListCommitsUseCaseOutput.model_validate({"commits": (), "truncated": False, "colour": "red"})


def test_is_frozen() -> None:
    """Assigning to a field raises AttributeError naming the class."""
    output = _ListCommitsUseCaseOutput(commits=(), truncated=False)
    with pytest.raises(AttributeError, match="_ListCommitsUseCaseOutput is immutable"):
        output.truncated = True
    assert output.truncated is False


def test_deleting_a_field_raises_attribute_error() -> None:
    """``del`` of a field raises AttributeError."""
    output = _ListCommitsUseCaseOutput(commits=(), truncated=False)
    with pytest.raises(AttributeError, match="is immutable"):
        del output.truncated


def test_equal_by_value() -> None:
    """Two outputs with the same values are equal."""
    assert _ListCommitsUseCaseOutput(commits=(_commit(),), truncated=True) == _ListCommitsUseCaseOutput(
        commits=(_commit(),), truncated=True
    )


def test_a_nested_class_is_a_direct_subclass() -> None:
    """A nested class of an output extends UseCaseOutput directly."""
    assert _ListCommitsUseCaseOutput.Commit.__bases__ == (UseCaseOutput,)


def test_second_level_subclass_is_rejected() -> None:
    """A concrete output extends UseCaseOutput directly."""
    with pytest.raises(TypeError, match="max inheritance depth"):

        class _Deeper(_ListCommitsUseCaseOutput):
            pass
