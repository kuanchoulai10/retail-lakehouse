"""Define a recording fake of the release_compaction_candidates activity."""

from __future__ import annotations

from typing import Any

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)


class ScriptedReleaseActivity:
    """Keep every release of unstarted compaction candidates the workflow asks for."""

    def __init__(self) -> None:
        """Start with no releases."""
        self.requests: list[dict[str, Any]] = []

    @activity.defn(name=TableReconciliationActivity.RELEASE_COMPACTION_CANDIDATES)
    async def release_compaction_candidates(self, request: dict[str, Any]) -> dict[str, Any]:
        """Keep the request and report one candidate released."""
        self.requests.append(request)
        return {"released": 1}
