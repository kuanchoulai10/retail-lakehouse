"""Define the TableReconciliationActivities Temporal activities."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from temporalio import activity

from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.activity_payload import (
    activity_payload,
)
from context.table_maintenance.adapter.hybrid.temporal.inbound.activities.translate_application_errors import (
    translate_application_errors,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    TableMaintenanceActivity,
)
from context.table_maintenance.adapter.hybrid.temporal.contracts.table_reconciliation import (
    TableReconciliationActivity,
)
from context.table_maintenance.application.port.inbound.table_maintenance_run import (
    DeleteMaintenanceJobUseCaseInput,
    GetMaintenanceJobStatusUseCaseInput,
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseInputFilterItem,
)
from context.table_maintenance.application.port.inbound.table import (
    PlanTableMaintenanceUseCaseInput,
)

if TYPE_CHECKING:
    from context.table_maintenance.application.port.inbound.table_maintenance_run import (
        DeleteMaintenanceJobUseCase,
        GetMaintenanceJobStatusUseCase,
        SubmitMaintenanceOperationUseCase,
    )
    from context.table_maintenance.application.port.inbound.table import (
        PlanTableMaintenanceUseCase,
    )


class TableReconciliationActivities:
    """Plan, submit, poll and delete the Spark jobs of maintenance runs.

    Each method wraps exactly one use case. Inputs and outputs are primitive dicts;
    ``now`` travels as an ISO-8601 string taken from ``workflow.now()``.
    """

    def __init__(
        self,
        *,
        plan: PlanTableMaintenanceUseCase,
        submit: SubmitMaintenanceOperationUseCase,
        status: GetMaintenanceJobStatusUseCase,
        delete: DeleteMaintenanceJobUseCase,
        callback_base_url: str,
    ) -> None:
        """Bind the use cases and the base URL Spark jobs call back to."""
        self._plan = plan
        self._submit = submit
        self._status = status
        self._delete = delete
        self._callback_base_url = callback_base_url

    @activity.defn(name=TableReconciliationActivity.PLAN_TABLE_MAINTENANCE)
    def plan_table_maintenance(self, request: dict[str, Any]) -> dict[str, Any]:
        """Plan the maintenance operations of a table."""
        with translate_application_errors():
            output = self._plan.execute(
                PlanTableMaintenanceUseCaseInput(
                    table_uuid=request["table_uuid"],
                    now=datetime.fromisoformat(request["now"]),
                    manual_operations=request.get("manual_operations"),
                )
            )
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION)
    def submit_maintenance_operation(self, request: dict[str, Any]) -> dict[str, Any]:
        """Start one attempt of an operation and submit its Spark job."""
        with translate_application_errors():
            output = self._submit.execute(
                SubmitMaintenanceOperationUseCaseInput(
                    run_id=request["run_id"],
                    operation=request["operation"],
                    attempt=request["attempt"],
                    filters=[
                        SubmitMaintenanceOperationUseCaseInputFilterItem(
                            spec_id=item["spec_id"], where=item["where"]
                        )
                        for item in request["filters"]
                    ],
                    procedure_args=dict(request["procedure_args"]),
                    callback_base_url=self._callback_base_url,
                    now=datetime.fromisoformat(request["now"]),
                )
            )
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.GET_MAINTENANCE_JOB_STATUS)
    def get_maintenance_job_status(self, request: dict[str, Any]) -> dict[str, Any]:
        """Report the state of a Spark maintenance job."""
        with translate_application_errors():
            output = self._status.execute(
                GetMaintenanceJobStatusUseCaseInput(
                    run_id=request["run_id"],
                    operation=request["operation"],
                    attempt=request["attempt"],
                )
            )
        return activity_payload(output)

    @activity.defn(name=TableMaintenanceActivity.DELETE_MAINTENANCE_JOB)
    def delete_maintenance_job(self, request: dict[str, Any]) -> dict[str, Any]:
        """Delete the Spark job of one ``(run_id, operation, attempt)``."""
        with translate_application_errors():
            output = self._delete.execute(
                DeleteMaintenanceJobUseCaseInput(
                    run_id=request["run_id"],
                    operation=request["operation"],
                    attempt=request["attempt"],
                )
            )
        return activity_payload(output)
