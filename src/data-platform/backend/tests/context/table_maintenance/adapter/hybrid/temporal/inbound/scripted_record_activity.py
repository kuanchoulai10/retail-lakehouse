"""Define a recording fake of the record_table_reconciliation activity."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class ScriptedRecordActivity:
    """Keep every reconciliation the workflow records.

    ``failures`` counts the next requests that fail non-retryably; a failed request
    is not kept in ``records``. ``hook``, when set, is awaited with each request
    before it is answered.
    """

    def __init__(self) -> None:
        """Start with no records, no failures and no hook."""
        self.failures = 0
        self.records: list[dict[str, Any]] = []
        self.hook: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    @activity.defn(name=TableReconciliationActivity.RECORD_TABLE_RECONCILIATION)
    async def record_table_reconciliation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Keep the request, or fail while failures remain."""
        if self.hook is not None:
            await self.hook(request)
        if self.failures > 0:
            self.failures -= 1
            raise ApplicationError("record failed", non_retryable=True)
        self.records.append(request)
        return {"recorded": True}
