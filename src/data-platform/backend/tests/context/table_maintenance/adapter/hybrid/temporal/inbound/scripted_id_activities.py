"""Define scripted fakes of the activities the table reconciliation workflow takes its ids from."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)
from context.table_maintenance.application.domain.model.shared import TableMaintenanceRunId, TableReconciliationId

if TYPE_CHECKING:
    import asyncio


class ScriptedIdActivities:
    """Issue fresh ids as the application does, and keep every id issued, in order.

    ``reconciliation_ids`` keeps each reconciliation id issued and ``run_ids`` each batch of run ids.
    ``requests`` counts every request received; ``reconciliation_gate`` and ``run_ids_gate``, when set, hold
    each issue of that kind until the test opens them.
    """

    def __init__(self) -> None:
        """Start with nothing issued and no gate."""
        self.reconciliation_ids: list[str] = []
        self.run_ids: list[list[str]] = []
        self.requests: list[str] = []
        self.reconciliation_gate: asyncio.Event | None = None
        self.run_ids_gate: asyncio.Event | None = None

    @activity.defn(name=TableReconciliationActivity.ISSUE_RECONCILIATION_ID)
    async def issue_reconciliation_id(self, request: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        """Issue and keep a new reconciliation id, once the gate is open."""
        self.requests.append("reconciliation_id")
        if self.reconciliation_gate is not None:
            await self.reconciliation_gate.wait()
        self.reconciliation_ids.append(TableReconciliationId.new().value)
        return {"reconciliation_id": self.reconciliation_ids[-1]}

    @activity.defn(name=TableReconciliationActivity.ISSUE_RUN_IDS)
    async def issue_run_ids(self, request: dict[str, Any]) -> dict[str, Any]:
        """Issue and keep ``count`` new run ids, once the gate is open."""
        self.requests.append("run_ids")
        if self.run_ids_gate is not None:
            await self.run_ids_gate.wait()
        self.run_ids.append([TableMaintenanceRunId.new().value for _ in range(request["count"])])
        return {"run_ids": self.run_ids[-1]}

    def all(self) -> list:
        """Return both activities for worker registration."""
        return [self.issue_reconciliation_id, self.issue_run_ids]
