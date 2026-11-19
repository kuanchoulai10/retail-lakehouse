"""Tests for the Pydantic UseCaseOutput base type."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from base import UseCaseOutput


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
    """Strict mode refuses ``"1"`` for an int field of a nested class."""
    with pytest.raises(TypeError, match="snapshot_id"):
        _ListCommitsUseCaseOutput.Commit(
            snapshot_id="1",  # ty: ignore[invalid-argument-type]
            committed_at=datetime(2026, 11, 18, tzinfo=UTC),
        )


def test_strict_refuses_a_list_for_a_tuple() -> None:
    """Strict mode refuses a ``list`` for a ``tuple`` field, so services pass the declared type."""
    with pytest.raises(TypeError, match="commits"):
        _ListCommitsUseCaseOutput(commits=[_commit()], truncated=False)  # ty: ignore[invalid-argument-type]


def test_refused_construction_is_a_server_bug_not_a_client_error() -> None:
    """A refused output raises builtin TypeError chained from Pydantic, never InvariantViolation.

    InvariantViolation is a ValueError that every edge answers as a client
    error (422, non-retryable); a TypeError reaches the edge as a 500 or a
    retryable failure, and is logged.
    """
    with pytest.raises(TypeError) as caught:
        _ListCommitsUseCaseOutput(commits=(), truncated="no")  # ty: ignore[invalid-argument-type]
    assert not isinstance(caught.value, ValueError)
    assert isinstance(caught.value.__cause__, ValidationError)
    assert "\n" not in str(caught.value)
    assert str(caught.value).startswith("_ListCommitsUseCaseOutput ")


def test_model_validate_refusal_raises_type_error() -> None:
    """``model_validate`` with an unknown key raises TypeError chained from Pydantic."""
    with pytest.raises(TypeError, match="colour") as caught:
        _ListCommitsUseCaseOutput.model_validate({"commits": (), "truncated": False, "colour": "red"})
    assert isinstance(caught.value.__cause__, ValidationError)


def test_model_validate_json_refusal_raises_type_error() -> None:
    """``model_validate_json`` with a mistyped value raises TypeError chained from Pydantic."""
    with pytest.raises(TypeError, match="truncated") as caught:
        _ListCommitsUseCaseOutput.model_validate_json('{"commits": [], "truncated": "no"}')
    assert isinstance(caught.value.__cause__, ValidationError)


def test_model_validate_strings_refusal_raises_type_error() -> None:
    """``model_validate_strings`` with a refused value raises TypeError chained from Pydantic."""
    with pytest.raises(TypeError, match="snapshot_id") as caught:
        _ListCommitsUseCaseOutput.Commit.model_validate_strings(
            {"snapshot_id": "one", "committed_at": "2026-11-18T00:00:00Z"}
        )
    assert isinstance(caught.value.__cause__, ValidationError)


def test_a_refused_nested_dict_raises_one_type_error_from_the_outer_output() -> None:
    """A refused nested class built from a dict inside the outer output raises one TypeError naming its path."""
    with pytest.raises(TypeError, match=r"commits\.0\.snapshot_id"):
        _ListCommitsUseCaseOutput.model_validate(
            {"commits": ({"snapshot_id": "1", "committed_at": datetime(2026, 11, 18, tzinfo=UTC)},), "truncated": False}
        )


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
