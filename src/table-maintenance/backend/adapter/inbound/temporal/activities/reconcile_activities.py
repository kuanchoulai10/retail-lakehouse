"""Define the ReconcileActivities Temporal activities."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from temporalio import activity

from adapter.inbound.temporal.activities.activity_payload import activity_payload
from adapter.inbound.temporal.activities.translate_application_errors import (
    translate_application_errors,
)
from adapter.temporal_contracts.activity_names import (
    DELETE_MAINTENANCE_JOB,
    GET_MAINTENANCE_JOB_STATUS,
    PLAN_TABLE_MAINTENANCE,
    SUBMIT_MAINTENANCE_OPERATION,
)
from application.port.inbound.reconcile.delete_maintenance_job import (
    DeleteMaintenanceJobUseCaseInput,
)
from application.port.inbound.reconcile.get_maintenance_job_status import (
    GetMaintenanceJobStatusUseCaseInput,
)
from application.port.inbound.reconcile.plan_table_maintenance import (
    PlanTableMaintenanceUseCaseInput,
)
from application.port.inbound.reconcile.submit_maintenance_operation import (
    SubmitMaintenanceOperationUseCaseInput,
    SubmitMaintenanceOperationUseCaseInputFilterItem,
)

if TYPE_CHECKING:
    from application.port.inbound.reconcile.delete_maintenance_job import (
        DeleteMaintenanceJobUseCase,
    )
    from application.port.inbound.reconcile.get_maintenance_job_status import (
        GetMaintenanceJobStatusUseCase,
    )
    from application.port.inbound.reconcile.plan_table_maintenance import (
        PlanTableMaintenanceUseCase,
    )
    from application.port.inbound.reconcile.submit_maintenance_operation import (
        SubmitMaintenanceOperationUseCase,
    )


class ReconcileActivities:
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

    @activity.defn(name=PLAN_TABLE_MAINTENANCE)
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

    @activity.defn(name=SUBMIT_MAINTENANCE_OPERATION)
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

    @activity.defn(name=GET_MAINTENANCE_JOB_STATUS)
    def get_maintenance_job_status(self, request: dict[str, Any]) -> dict[str, Any]:
        """Report the state of a Spark maintenance job."""
        with translate_application_errors():
            output = self._status.execute(
                GetMaintenanceJobStatusUseCaseInput(app_name=request["app_name"])
            )
        return activity_payload(output)

    @activity.defn(name=DELETE_MAINTENANCE_JOB)
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
