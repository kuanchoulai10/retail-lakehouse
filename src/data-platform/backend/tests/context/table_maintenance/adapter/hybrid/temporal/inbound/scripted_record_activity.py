"""Define a recording fake of the record_table_reconciliation activity."""

from __future__ import annotations

from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)


class ScriptedRecordActivity:
    """Keep every reconciliation the workflow records.

    ``failures`` counts the next requests that fail non-retryably; a failed request
    is not kept in ``records``.
    """

    def __init__(self) -> None:
        """Start with no records and no failures."""
        self.failures = 0
        self.records: list[dict[str, Any]] = []

    @activity.defn(name=TableReconciliationActivity.RECORD_TABLE_RECONCILIATION)
    async def record_table_reconciliation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Keep the request, or fail while failures remain."""
        if self.failures > 0:
            self.failures -= 1
            raise ApplicationError("record failed", non_retryable=True)
        self.records.append(request)
        return {"recorded": True}
