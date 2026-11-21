"""Define scripted fakes of the activities the table reconciliation workflow creates and skips runs with."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)

if TYPE_CHECKING:
    import asyncio


class ScriptedRunsActivities:
    """Keep every create and skip request the reconciliation sends for a plan's runs.

    ``created`` keeps each create request; while ``create_failures`` is above zero, the next creates
    fail non-retryably (the request is still kept), and ``create_gate``, when set, holds each create
    until the test opens it. ``skips`` keeps each skip request; ``skip_failures`` fails the next skips
    likewise.
    """

    def __init__(self) -> None:
        """Start with no requests, no failures and no gate."""
        self.created: list[dict[str, Any]] = []
        self.skips: list[dict[str, Any]] = []
        self.create_failures = 0
        self.skip_failures = 0
        self.create_gate: asyncio.Event | None = None

    @activity.defn(name=TableReconciliationActivity.CREATE_MAINTENANCE_RUNS)
    async def create_maintenance_runs(self, request: dict[str, Any]) -> dict[str, Any]:
        """Keep the request and reply with its run ids, or fail while failures remain."""
        self.created.append(request)
        if self.create_gate is not None:
            await self.create_gate.wait()
        if self.create_failures > 0:
            self.create_failures -= 1
            raise ApplicationError("db down", type="ConflictError", non_retryable=True)
        return {"run_ids": [run["run_id"] for run in request["runs"]]}

    @activity.defn(name=TableReconciliationActivity.SKIP_MAINTENANCE_RUNS)
    async def skip_maintenance_runs(self, request: dict[str, Any]) -> dict[str, Any]:
        """Keep the request and reply with every run skipped, or fail while failures remain."""
        self.skips.append(request)
        if self.skip_failures > 0:
            self.skip_failures -= 1
            raise ApplicationError("db down", type="ConflictError", non_retryable=True)
        return {"runs": [{"run_id": r, "status": "skipped", "skipped": True} for r in request["run_ids"]]}

    def all(self) -> list:
        """Return both activities for worker registration."""
        return [self.create_maintenance_runs, self.skip_maintenance_runs]
