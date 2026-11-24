"""Test append_retrying, the append that reloads the table and tries again when a commit lost the race."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pyarrow as pa
import pytest
from pyiceberg.exceptions import CommitFailedException

from e2e.support import append_retrying

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyiceberg.table import Table

ROWS = pa.table({"id": [1]})


class _Table:
    def __init__(self, outcomes: list[Exception | None], appended: list[int], loaded: int) -> None:
        self._outcomes = outcomes
        self._appended = appended
        self._loaded = loaded

    def append(self, df: pa.Table) -> None:
        outcome = self._outcomes.pop(0)
        if outcome is not None:
            raise outcome
        self._appended.append(self._loaded)


def _loader(outcomes: list[Exception | None]) -> tuple[list[int], list[int], Callable[[], Table]]:
    loads: list[int] = []
    appended: list[int] = []

    def load() -> Table:
        loads.append(len(loads))
        return cast("Table", _Table(outcomes, appended, len(loads) - 1))

    return loads, appended, load


def test_a_commit_that_lost_the_race_is_tried_again_on_a_fresh_load():
    """Each try loads the table again, so it commits on top of the commit that beat it."""
    loads, appended, load = _loader([CommitFailedException("branch main has changed"), None])
    assert append_retrying(load, ROWS) == 2
    assert loads == [0, 1]
    assert appended == [1]


def test_a_first_try_that_commits_loads_once():
    """No conflict, one load, one append."""
    loads, appended, load = _loader([None])
    assert append_retrying(load, ROWS) == 1
    assert (loads, appended) == ([0], [0])


def test_it_gives_up_after_the_last_attempt_and_raises_the_conflict():
    """A table that keeps changing fails the writer instead of retrying forever."""
    conflicts: list[Exception | None] = [CommitFailedException(f"conflict {n}") for n in range(3)]
    loads, appended, load = _loader(conflicts)
    with pytest.raises(CommitFailedException, match="conflict 2"):
        append_retrying(load, ROWS, attempts=3)
    assert (len(loads), appended) == (3, [])


def test_another_error_is_raised_at_once():
    """Only a lost commit race is retried; anything else is a real failure."""
    loads, _, load = _loader([ValueError("schema mismatch"), None])
    with pytest.raises(ValueError, match="schema mismatch"):
        append_retrying(load, ROWS)
    assert loads == [0]
