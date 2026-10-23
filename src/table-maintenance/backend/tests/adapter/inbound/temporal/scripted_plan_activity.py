"""Define a scripted fake of the plan_table_maintenance activity."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from adapter.temporal_contracts.activity_names import PLAN_TABLE_MAINTENANCE

if TYPE_CHECKING:
    from collections.abc import Callable


class ScriptedPlanActivity:
    """Record every plan request and answer it with ``script(request)``.

    ``failures`` counts the next requests that fail non-retryably; ``gate``, when
    set, holds every request (after it is recorded) until the test opens it.
    """

    def __init__(self, script: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self.script = script
        self.failures = 0
        self.gate: asyncio.Event | None = None
        self.requests: list[dict[str, Any]] = []

    @activity.defn(name=PLAN_TABLE_MAINTENANCE)
    async def plan_table_maintenance(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        if self.gate is not None:
            await self.gate.wait()
        if self.failures > 0:
            self.failures -= 1
            raise ApplicationError("plan failed", non_retryable=True)
        return self.script(request)
