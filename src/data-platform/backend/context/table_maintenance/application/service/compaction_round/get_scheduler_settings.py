"""Define the GetSchedulerSettingsService."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority
from context.table_maintenance.application.port.inbound.compaction_round import (
    GetSchedulerSettingsUseCase,
    GetSchedulerSettingsUseCaseInput,
    GetSchedulerSettingsUseCaseOutput,
)

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import timedelta

    from context.table_maintenance.application.domain.model.compaction_round import PriorityWeights


class GetSchedulerSettingsService(GetSchedulerSettingsUseCase):
    """Report the settings the compaction rounds run under, so people can read a priority as its SLA."""

    def __init__(
        self,
        *,
        weights: PriorityWeights,
        sla: Mapping[MaintenancePriority, timedelta],
        round_seconds: int,
        budget_gb_hours: float,
        grant_lease: timedelta,
    ) -> None:
        """Bind the settings the round service was built with."""
        self._weights = weights
        self._sla = dict(sla)
        self._round_seconds = round_seconds
        self._budget_gb_hours = budget_gb_hours
        self._grant_lease = grant_lease

    def execute(self, request: GetSchedulerSettingsUseCaseInput) -> GetSchedulerSettingsUseCaseOutput:  # noqa: ARG002
        """Return the settings, one priority entry per priority from P0 to P2."""
        return GetSchedulerSettingsUseCaseOutput(
            round_seconds=self._round_seconds,
            budget_gb_hours=self._budget_gb_hours,
            grant_lease_seconds=int(self._grant_lease.total_seconds()),
            priorities=tuple(
                GetSchedulerSettingsUseCaseOutput.Priority(
                    priority=priority.value,
                    weight=self._weights.weight(priority),
                    sla_seconds=int(self._sla[priority].total_seconds()),
                )
                for priority in MaintenancePriority
            ),
        )
