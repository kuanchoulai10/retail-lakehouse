"""Define scripted fakes of the activities the maintenance workflow calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from adapter.temporal_contracts.activity_names import (
    CREATE_MAINTENANCE_RUN,
    DELETE_MAINTENANCE_JOB,
    GET_MAINTENANCE_JOB_STATUS,
    RECORD_MAINTENANCE_OPERATION_RESULT,
    SUBMIT_MAINTENANCE_OPERATION,
)
from adapter.temporal_contracts.operation_result_signal import OperationResultSignal
from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_OPERATION_RESULT,
    maintenance_workflow_id,
)

if TYPE_CHECKING:
    from temporalio.client import Client


class ScriptedMaintenanceActivities:
    """Record every call and play back scripted callbacks, errors and job states.

    ``callbacks[(operation, attempt)]`` lists the results the fake Spark job sends
    while that attempt is submitted, as ``(attempt, succeeded, error)`` tuples, so a
    script can also send a stale result for another attempt. ``states[app_name]``
    is the job state the status activity reports (RUNNING by default).
    """

    def __init__(self, client: Client) -> None:
        self._client = client
        self.callbacks: dict[tuple[str, int], list[tuple[int, bool, str | None]]] = {}
        self.submit_errors: dict[tuple[str, int], str] = {}
        self.states: dict[str, dict[str, Any]] = {}
        self.created: list[dict] = []
        self.submits: list[dict] = []
        self.records: list[dict] = []
        self.deletes: list[str] = []
        self.status_calls: list[str] = []

    @staticmethod
    def app_name(run_id: str, operation: str, attempt: int) -> str:
        return f"{run_id}-{operation}-{attempt}"

    @activity.defn(name=CREATE_MAINTENANCE_RUN)
    async def create_maintenance_run(self, request: dict) -> dict:
        self.created.append(request)
        return {"run_id": request["run_id"], "status": "running"}

    @activity.defn(name=SUBMIT_MAINTENANCE_OPERATION)
    async def submit_maintenance_operation(self, request: dict) -> dict:
        self.submits.append(request)
        key = (request["operation"], request["attempt"])
        if key in self.submit_errors:
            raise ApplicationError(
                self.submit_errors[key], type="ConflictError", non_retryable=True
            )
        handle = self._client.get_workflow_handle(
            maintenance_workflow_id(request["run_id"])
        )
        for attempt, succeeded, error in self.callbacks.get(key, []):
            await handle.signal(
                SIGNAL_OPERATION_RESULT,
                OperationResultSignal(
                    run_id=request["run_id"],
                    operation=request["operation"],
                    attempt=attempt,
                    succeeded=succeeded,
                    metrics={"files": attempt} if succeeded else {},
                    error=error,
                ),
            )
        return {
            "app_name": self.app_name(request["run_id"], *key),
        }

    @activity.defn(name=GET_MAINTENANCE_JOB_STATUS)
    async def get_maintenance_job_status(self, request: dict) -> dict:
        self.status_calls.append(request["app_name"])
        return self.states.get(request["app_name"], {"state": "RUNNING", "error": None})

    @activity.defn(name=RECORD_MAINTENANCE_OPERATION_RESULT)
    async def record_maintenance_operation_result(self, request: dict) -> dict:
        self.records.append(request)
        return {"run_id": request["run_id"], "status": "running"}

    @activity.defn(name=DELETE_MAINTENANCE_JOB)
    async def delete_maintenance_job(self, request: dict) -> dict:
        self.deletes.append(request["app_name"])
        return {"app_name": request["app_name"]}

    def all(self) -> list:
        return [
            self.create_maintenance_run,
            self.submit_maintenance_operation,
            self.get_maintenance_job_status,
            self.record_maintenance_operation_result,
            self.delete_maintenance_job,
        ]
