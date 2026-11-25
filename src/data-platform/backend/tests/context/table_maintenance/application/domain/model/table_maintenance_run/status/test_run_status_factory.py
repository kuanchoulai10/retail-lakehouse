"""Tests for RunStatusFactory."""

from __future__ import annotations

import pytest

from base import InvariantViolation, ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    CancelledRunStatus,
    FailedRunStatus,
    PendingRunStatus,
    QueuedRunStatus,
    RetryWaitingRunStatus,
    RunningRunStatus,
    RunStatusFactory,
    RunStatusField,
    RunStatusName,
    SkippedRunStatus,
    SucceededRunStatus,
)


def test_every_name_creates_its_one_status():
    """Each of the eight names creates the status of that name."""
    assert {RunStatusFactory.create(n.value).name for n in RunStatusName} == set(RunStatusName)


@pytest.mark.parametrize(
    ("name", "status_class"),
    [
        ("pending", PendingRunStatus),
        ("queued", QueuedRunStatus),
        ("running", RunningRunStatus),
        ("retry_waiting", RetryWaitingRunStatus),
        ("succeeded", SucceededRunStatus),
        ("failed", FailedRunStatus),
        ("skipped", SkippedRunStatus),
        ("cancelled", CancelledRunStatus),
    ],
)
def test_a_name_creates_its_status_class(name: str, status_class: type):
    """A name creates an instance of its own status class."""
    assert type(RunStatusFactory.create(name)) is status_class


def test_an_unknown_name_is_refused():
    """A name that is no run status raises ValueError."""
    with pytest.raises(ValueError, match="partially_failed"):
        RunStatusFactory.create("partially_failed")


class _Holder(ValueObject):
    status: RunStatusField


@pytest.mark.parametrize("refused", ["partially_failed", 1, None])
def test_a_field_refuses_what_is_no_run_status(refused: object):
    """A status field refuses an unknown name or a value that is not a name."""
    with pytest.raises(InvariantViolation):
        _Holder.model_validate({"status": refused})
    with pytest.raises(InvariantViolation):
        _Holder.from_primitives({"status": refused})
