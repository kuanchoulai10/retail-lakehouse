"""Define the RecordTableMaintenanceOperationResultUseCaseInput."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from base import UseCaseInput


class RecordTableMaintenanceOperationResultUseCaseInput(UseCaseInput):
    """Carry the request to record the result of a maintenance operation attempt.

    ``ended_by`` names what ended the attempt (an ``AttemptEnding`` value), ``still_running`` says
    its job may still be running, and ``max_attempts`` is how many attempts the operation is allowed.
    ``policy_name``, ``policy_version`` and ``policy_target`` name the policy the run was planned
    under; without them a needs-attention mark is set under the policy that applies when recorded.
    """

    run_id: str
    operation: str
    attempt: int
    succeeded: bool
    metrics: dict[str, int]
    error: str | None
    now: datetime
    ended_by: str = "result"
    still_running: bool = False
    max_attempts: int = 3
    policy_name: str | None = None
    policy_version: int | None = None
    policy_target: dict[str, Any] | None = None
