"""Test that an operation run's attempt history agrees with its attempt count."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from context.table_maintenance.application.domain.model.shared import ComputeSize, MaintenanceOperation
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    OperationAttempt,
    OperationRun,
    OperationRunStatus,
)

T0 = datetime(2026, 11, 13, tzinfo=UTC)


def _attempt(n: int, status: OperationRunStatus = OperationRunStatus.FAILED) -> OperationAttempt:
    return OperationAttempt(attempt=n, size=ComputeSize.S, status=status, started_at=T0)


def _run(attempts: int, *history: OperationAttempt) -> OperationRun:
    return OperationRun(
        operation=MaintenanceOperation.REWRITE_DATA_FILES,
        status=OperationRunStatus.RUNNING,
        attempts=attempts,
        attempt_history=history,
    )


def test_history_ending_at_the_latest_attempt_is_valid():
    """Attempts listed oldest first, the last one the latest attempt, make a valid history."""
    run = _run(3, _attempt(1), _attempt(2), _attempt(3, OperationRunStatus.RUNNING))
    assert [a.attempt for a in run.attempt_history] == [1, 2, 3]


def test_history_from_before_attempt_history_may_miss_earlier_attempts():
    """A run whose earlier attempts predate attempt history lists only the later ones."""
    assert [a.attempt for a in _run(3, _attempt(3)).attempt_history] == [3]


def test_empty_history_is_valid_for_any_attempt_count():
    """A run recorded before attempt history existed has none."""
    assert _run(2).attempt_history == ()


@pytest.mark.parametrize(
    "history",
    [
        (_attempt(1), _attempt(1)),
        (_attempt(2), _attempt(1)),
    ],
)
def test_attempt_numbers_must_increase(history):
    """An attempt listed twice, or out of order, is refused."""
    with pytest.raises(ValidationError, match="increase"):
        _run(2, *history)


def test_last_attempt_must_be_the_latest_attempt():
    """A history whose last attempt is not the operation's latest attempt is refused."""
    with pytest.raises(ValidationError, match="latest attempt"):
        _run(3, _attempt(1), _attempt(2))


def test_history_cannot_hold_an_attempt_beyond_the_count():
    """A history listing an attempt the operation never reached is refused."""
    with pytest.raises(ValidationError, match="latest attempt"):
        _run(1, _attempt(1), _attempt(2))
