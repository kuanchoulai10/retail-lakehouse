"""Define the CompactionRoundActivities Temporal activities."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.contracts.compaction_round import (
    CompactionRoundActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.activity_payload import (
    activity_payload,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.translate_application_errors import (
    translate_application_errors,
)
from context.table_maintenance.application.port.inbound.compaction_round import (
    ScheduleCompactionRoundUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.compaction_round import (
        ScheduleCompactionRoundUseCase,
    )


class CompactionRoundActivities:
    """Run a round of the compaction scheduler."""

    def __init__(self, *, schedule: ScheduleCompactionRoundUseCase) -> None:
        """Bind the round use case."""
        self._schedule = schedule

    @activity.defn(name=CompactionRoundActivity.SCHEDULE_COMPACTION_ROUND)
    def schedule_compaction_round(self, request: dict[str, Any]) -> dict[str, Any]:
        """Plan, grant and record the round ``round_id`` at ``now``.

        A candidate changed by another writer since the round read it raises a
        retryable error, so the retry plans again on fresh reads.
        """
        with translate_application_errors():
            output = self._schedule.execute(
                ScheduleCompactionRoundUseCaseInput(
                    round_id=request["round_id"], now=datetime.fromisoformat(request["now"])
                )
            )
        return activity_payload(output)
