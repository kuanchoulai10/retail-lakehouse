"""Define the RecordMaintenanceAttemptRunningUseCase port."""

from __future__ import annotations

from abc import abstractmethod

from base import UseCase
from context.table_maintenance.application.port.inbound.table_maintenance_run.record_maintenance_attempt_running.input import (  # noqa: E501
    RecordMaintenanceAttemptRunningUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run.record_maintenance_attempt_running.output import (  # noqa: E501
    RecordMaintenanceAttemptRunningUseCaseOutput,
)


class RecordMaintenanceAttemptRunningUseCase(
    UseCase[RecordMaintenanceAttemptRunningUseCaseInput, RecordMaintenanceAttemptRunningUseCaseOutput]
):
    """Record when the coordinator of a maintenance operation attempt started running."""

    @abstractmethod
    def execute(
        self, request: RecordMaintenanceAttemptRunningUseCaseInput
    ) -> RecordMaintenanceAttemptRunningUseCaseOutput:
        """Record when the coordinator of a maintenance operation attempt started running."""
