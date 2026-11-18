"""Define the TableMaintenanceActivities Temporal activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.activity_payload import (
    activity_payload,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.translate_application_errors import (
    translate_application_errors,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    CreateTableMaintenanceRunUseCaseInput,
    RecordTableMaintenanceOperationResultUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        CreateTableMaintenanceRunUseCase,
        RecordTableMaintenanceOperationResultUseCase,
    )


class TableMaintenanceActivities:
    """Create maintenance runs and record the outcome of their attempts."""

    def __init__(
        self,
        *,
        create_run: CreateTableMaintenanceRunUseCase,
        record_result: RecordTableMaintenanceOperationResultUseCase,
    ) -> None:
        """Bind the use cases."""
        self._create_run = create_run
        self._record_result = record_result

    @activity.defn(name=TableMaintenanceActivity.CREATE_MAINTENANCE_RUN)
    def create_table_maintenance_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create the run with its planned operations."""
        with translate_application_errors():
            output = self._create_run.execute(CreateTableMaintenanceRunUseCaseInput.from_primitives(request))
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.RECORD_MAINTENANCE_OPERATION_RESULT)
    def record_table_maintenance_operation_result(self, request: dict[str, Any]) -> dict[str, Any]:
        """Record the outcome of one operation attempt; an older request reads as a reported result."""
        with translate_application_errors():
            output = self._record_result.execute(
                RecordTableMaintenanceOperationResultUseCaseInput.from_primitives(request)
            )
        return activity_payload(output)
