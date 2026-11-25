"""Tests for the OperationAttempt value object and its AttemptStatus."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.shared import ComputeSize
from context.table_maintenance.application.domain.model.table_maintenance_run import (
    AttemptStatus,
    OperationAttempt,
    RunStatusName,
)

T0 = datetime(2026, 10, 24, tzinfo=UTC)


def _an_attempt(status: object = AttemptStatus.QUEUED) -> OperationAttempt:
    return OperationAttempt.model_validate({"attempt": 1, "size": ComputeSize.S, "status": status, "started_at": T0})


def test_an_attempt_takes_only_an_attempt_status():
    """An attempt is queued, running, succeeded or failed; the run-only statuses are refused."""
    assert {s.value for s in AttemptStatus} == {"queued", "running", "succeeded", "failed"}
    for refused in ("pending", "skipped", RunStatusName.PENDING, RunStatusName.SKIPPED):
        with pytest.raises(InvariantViolation):
            _an_attempt(status=refused)


@pytest.mark.parametrize(
    ("status", "finished"),
    [
        (AttemptStatus.QUEUED, False),
        (AttemptStatus.RUNNING, False),
        (AttemptStatus.SUCCEEDED, True),
        (AttemptStatus.FAILED, True),
    ],
)
def test_an_attempt_is_finished_once_it_succeeded_or_failed(status, finished):
    """An attempt has an outcome exactly when it is succeeded or failed."""
    assert _an_attempt(status).finished is finished
