"""Define scripted fakes of the activities the table maintenance workflow calls."""

from __future__ import annotations

import asyncio
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
    table_maintenance_workflow_id,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import datetime

    from temporalio.client import Client


class ScriptedMaintenanceActivities:
    """Record every call and play back scripted callbacks, errors and job states.

    ``callbacks[(operation, attempt)]`` lists the results the fake Spark job sends
    while that attempt is submitted, as ``(attempt, succeeded, error)`` tuples, so a
    script can also send a stale result for another attempt. ``states[app_name]``
    is the job state the status activity reports (RUNNING by default); a list plays
    its states in order and then repeats the last one. ``record_errors`` lists the
    ``(operation, attempt)`` outcomes whose recording fails non-retryably, and
    ``create_gate``, ``submit_gate`` and ``status_gate``, when set, hold that
    activity until the test opens them; ``status_hook`` runs inside each status
    call with the app name and the call's scheduled time.
    """

    def __init__(self, client: Client) -> None:
        self._client = client
        self.callbacks: dict[tuple[str, int], list[tuple[int, bool, str | None]]] = {}
        self.submit_errors: dict[tuple[str, int], str] = {}
        self.states: dict[str, dict[str, Any] | list[dict[str, Any]]] = {}
        self.record_errors: set[tuple[str, int]] = set()
        self.create_gate: asyncio.Event | None = None
        self.submit_gate: asyncio.Event | None = None
        self.status_gate: asyncio.Event | None = None
        self.status_hook: Callable[[str, datetime], Awaitable[None]] | None = None
        self.status_times: list[datetime] = []
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
        if self.create_gate is not None:
            await self.create_gate.wait()
        return {"run_id": request["run_id"], "status": "running"}

    @activity.defn(name=SUBMIT_MAINTENANCE_OPERATION)
    async def submit_maintenance_operation(self, request: dict) -> dict:
        self.submits.append(request)
        if self.submit_gate is not None:
            await self.submit_gate.wait()
        key = (request["operation"], request["attempt"])
        if key in self.submit_errors:
            raise ApplicationError(
                self.submit_errors[key], type="ConflictError", non_retryable=True
            )
        handle = self._client.get_workflow_handle(
            table_maintenance_workflow_id(request["run_id"])
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
        app_name = request["app_name"]
        self.status_calls.append(app_name)
        self.status_times.append(activity.info().scheduled_time)
        if self.status_gate is not None:
            await self.status_gate.wait()
        if self.status_hook is not None:
            await self.status_hook(app_name, activity.info().scheduled_time)
        state = self.states.get(app_name, {"state": "RUNNING", "error": None})
        if isinstance(state, list):
            calls = self.status_calls.count(app_name)
            return state[min(calls, len(state)) - 1]
        return state

    @activity.defn(name=RECORD_MAINTENANCE_OPERATION_RESULT)
    async def record_maintenance_operation_result(self, request: dict) -> dict:
        self.records.append(request)
        if (request["operation"], request["attempt"]) in self.record_errors:
            raise ApplicationError("db down", type="ConflictError", non_retryable=True)
        return {"run_id": request["run_id"], "status": "running"}

    @activity.defn(name=DELETE_MAINTENANCE_JOB)
    async def delete_maintenance_job(self, request: dict) -> dict:
        app_name = self.app_name(
            request["run_id"], request["operation"], request["attempt"]
        )
        self.deletes.append(app_name)
        return {"app_name": app_name}

    def all(self) -> list:
        return [
            self.create_maintenance_run,
            self.submit_maintenance_operation,
            self.get_maintenance_job_status,
            self.record_maintenance_operation_result,
            self.delete_maintenance_job,
        ]
