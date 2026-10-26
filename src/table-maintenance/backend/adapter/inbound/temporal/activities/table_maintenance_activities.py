"""Define the TableMaintenanceActivities Temporal activities."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from temporalio import activity

from adapter.inbound.temporal.activities.activity_payload import activity_payload
from adapter.inbound.temporal.activities.translate_application_errors import (
    translate_application_errors,
)
from adapter.temporal_contracts.activity_names import (
    CREATE_MAINTENANCE_RUN,
    RECORD_MAINTENANCE_OPERATION_RESULT,
)
from application.port.inbound.maintenance_run.create_maintenance_run import (
    CreateMaintenanceRunUseCaseInput,
)
from application.port.inbound.maintenance_run.record_maintenance_operation_result import (
    RecordMaintenanceOperationResultUseCaseInput,
)

if TYPE_CHECKING:
    from application.port.inbound.maintenance_run.create_maintenance_run import (
        CreateMaintenanceRunUseCase,
    )
    from application.port.inbound.maintenance_run.record_maintenance_operation_result import (
        RecordMaintenanceOperationResultUseCase,
    )


class TableMaintenanceActivities:
    """Create maintenance runs and record the outcome of their attempts."""

    def __init__(
        self,
        *,
        create_run: CreateMaintenanceRunUseCase,
        record_result: RecordMaintenanceOperationResultUseCase,
    ) -> None:
        """Bind the use cases."""
        self._create_run = create_run
        self._record_result = record_result

    @activity.defn(name=CREATE_MAINTENANCE_RUN)
    def create_maintenance_run(self, request: dict[str, Any]) -> dict[str, Any]:
        """Create the run with its planned operations."""
        with translate_application_errors():
            output = self._create_run.execute(
                CreateMaintenanceRunUseCaseInput(
                    run_id=request["run_id"],
                    table_uuid=request["table_uuid"],
                    workflow_id=request["workflow_id"],
                    trigger=request["trigger"],
                    operations=list(request["operations"]),
                    now=datetime.fromisoformat(request["now"]),
                )
            )
        return activity_payload(output)

    @activity.defn(name=RECORD_MAINTENANCE_OPERATION_RESULT)
    def record_maintenance_operation_result(
        self, request: dict[str, Any]
    ) -> dict[str, Any]:
        """Record the outcome of one operation attempt."""
        with translate_application_errors():
            output = self._record_result.execute(
                RecordMaintenanceOperationResultUseCaseInput(
                    run_id=request["run_id"],
                    operation=request["operation"],
                    attempt=request["attempt"],
                    succeeded=request["succeeded"],
                    metrics=dict(request["metrics"]),
                    error=request["error"],
                    now=datetime.fromisoformat(request["now"]),
                )
            )
        return activity_payload(output)
