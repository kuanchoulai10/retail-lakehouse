"""Define the RecordTableMaintenanceOperationResultUseCaseInput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseInput


class RecordTableMaintenanceOperationResultUseCaseInput(UseCaseInput):
    """Carry the request to record the result of a maintenance operation attempt.

    ``operation`` must be the run's own. ``ended_by`` names what ended the attempt (an ``AttemptEnding``
    value), ``still_running`` says its job may still be running, and ``max_attempts`` is how many attempts
    the run is allowed.
    ``policy_id`` (the policy's ``mp-`` id), ``policy_version`` and ``policy_target`` (None for the
    platform default, which is attached to nothing) point at the policy the run was planned under, and
    ``policy_name`` is its name then, which a needs-attention mark keeps for display.
    """

    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
    now: datetime
    ended_by: str
    still_running: bool
    max_attempts: int
    policy_id: str
    policy_name: str
    policy_version: int
    policy_target: dict[str, Any] | None
