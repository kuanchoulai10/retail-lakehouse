"""Tests for the RunStatus classes: one class per status, each allowing only its own moves."""

from __future__ import annotations

import pytest

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    InvalidRunTransition,
    PendingRunStatus,
    QueuedRunStatus,
    RetryWaitingRunStatus,
    RunStatus,
    RunStatusFactory,
    RunStatusField,
    RunStatusName,
)

ALLOWED: dict[tuple[object, ...], str] = {
    ("pending", "start_attempt"): "queued",
    ("pending", "cancel"): "cancelled",
    ("pending", "skip"): "skipped",
    ("queued", "mark_running"): "running",
    ("queued", "succeed"): "succeeded",
    ("queued", "fail", False): "failed",
    ("queued", "fail", True): "retry_waiting",
    ("queued", "cancel"): "cancelled",
    ("running", "succeed"): "succeeded",
    ("running", "fail", False): "failed",
    ("running", "fail", True): "retry_waiting",
    ("running", "cancel"): "cancelled",
    ("retry_waiting", "start_attempt"): "queued",
    ("retry_waiting", "cancel"): "cancelled",
}

MOVES: list[tuple[object, ...]] = [
    ("start_attempt",),
    ("mark_running",),
    ("succeed",),
    ("fail", False),
    ("fail", True),
    ("cancel",),
    ("skip",),
]


def _apply(status: RunStatus, move: tuple[object, ...]) -> RunStatus:
    action = move[0]
    if action == "fail":
        return status.fail(retries=bool(move[1]))
    return getattr(status, str(action))()


@pytest.mark.parametrize("name", list(RunStatusName))
@pytest.mark.parametrize("move", MOVES, ids=["-".join(str(part) for part in move) for move in MOVES])
def test_only_the_listed_transitions_are_allowed(name: RunStatusName, move: tuple[object, ...]):
    """An allowed move returns the next status; any other move raises InvalidRunTransition naming the status."""
    status = RunStatusFactory.create(name.value)
    expected = ALLOWED.get((name.value, *move))
    if expected is None:
        with pytest.raises(InvalidRunTransition, match=f"cannot {move[0]} a run that is {name.value}$"):
            _apply(status, move)
    else:
        moved = _apply(status, move)
        assert moved.name == RunStatusName(expected)
        assert moved == RunStatusFactory.create(expected)


@pytest.mark.parametrize(
    ("name", "terminal"),
    [
        (RunStatusName.PENDING, False),
        (RunStatusName.QUEUED, False),
        (RunStatusName.RUNNING, False),
        (RunStatusName.RETRY_WAITING, False),
        (RunStatusName.SUCCEEDED, True),
        (RunStatusName.FAILED, True),
        (RunStatusName.SKIPPED, True),
        (RunStatusName.CANCELLED, True),
    ],
)
def test_only_succeeded_failed_skipped_and_cancelled_are_terminal(name: RunStatusName, terminal: bool):
    """A run waiting to retry is not finished."""
    assert RunStatusFactory.create(name.value).is_terminal is terminal


@pytest.mark.parametrize(
    ("name", "in_flight"),
    [
        (RunStatusName.PENDING, False),
        (RunStatusName.QUEUED, True),
        (RunStatusName.RUNNING, True),
        (RunStatusName.RETRY_WAITING, False),
        (RunStatusName.SUCCEEDED, False),
        (RunStatusName.FAILED, False),
        (RunStatusName.SKIPPED, False),
        (RunStatusName.CANCELLED, False),
    ],
)
def test_only_queued_and_running_are_in_flight(name: RunStatusName, in_flight: bool):
    """Only a run with an attempt submitted is in flight."""
    assert RunStatusFactory.create(name.value).is_in_flight is in_flight


def test_a_status_equals_another_of_the_same_name_only():
    """Two statuses are equal when they are the same status."""
    assert PendingRunStatus() == PendingRunStatus()
    assert hash(PendingRunStatus()) == hash(PendingRunStatus())
    assert PendingRunStatus() != QueuedRunStatus()


def test_every_status_is_a_run_status_value_object():
    """Each status is a RunStatus and a value object, compared by its class."""
    pending = PendingRunStatus()
    assert isinstance(pending, RunStatus)
    assert isinstance(pending, ValueObject)
    assert pending == PendingRunStatus()
    assert pending != QueuedRunStatus()


class _Holder(ValueObject):
    status: RunStatusField


def test_a_field_reads_a_name_and_writes_it_back():
    """A status field reads its name from primitives and writes the name back."""
    holder = _Holder.from_primitives({"status": "retry_waiting"})
    assert holder.status == RetryWaitingRunStatus()
    assert holder.to_primitives() == {"status": "retry_waiting"}


def test_a_field_takes_a_status_or_a_name_in_code():
    """Built in code, a status field takes a status or its name and dumps the name."""
    assert _Holder(status=QueuedRunStatus()).status == QueuedRunStatus()
    assert _Holder.model_validate({"status": "queued"}).status == QueuedRunStatus()
    assert _Holder(status=QueuedRunStatus()).model_dump() == {"status": "queued"}
