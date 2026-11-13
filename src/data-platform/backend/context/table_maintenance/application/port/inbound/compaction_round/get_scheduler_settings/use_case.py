"""Define the GetSchedulerSettingsUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.compaction_round.get_scheduler_settings.input import (
    GetSchedulerSettingsUseCaseInput,
)
from context.table_maintenance.application.port.inbound.compaction_round.get_scheduler_settings.output import (
    GetSchedulerSettingsUseCaseOutput,
)


class GetSchedulerSettingsUseCase(UseCase[GetSchedulerSettingsUseCaseInput, GetSchedulerSettingsUseCaseOutput]):
    """Read the settings compaction rounds run under: interval, budget, grant lease, weights and SLAs."""

    @abstractmethod
    def execute(self, request: GetSchedulerSettingsUseCaseInput) -> GetSchedulerSettingsUseCaseOutput:
        """Read the settings compaction rounds run under."""
