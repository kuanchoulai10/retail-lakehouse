"""Define scripted fakes of the activities the table maintenance workflow calls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from context.table_maintenance.adapter.hybrid.temporal.contracts.table_maintenance import (
    OperationResultSignal,
    TableMaintenanceActivity,
    TableMaintenanceSignal,
)

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Awaitable, Callable
    from datetime import datetime, timedelta

    from temporalio.client import Client


class ScriptedMaintenanceActivities:
    """Record every call and play back scripted callbacks, errors and job states.

    ``callbacks[(operation, attempt)]`` lists the results the fake Spark job sends
    while that attempt is submitted, as ``(attempt, succeeded, error)`` tuples, so a
    script can also send a stale result for another attempt. ``states[app_name]``
    is the job state the status activity reports (RUNNING by default); a list plays
    its states in order and then repeats the last one. ``record_errors`` lists the
    ``(operation, attempt)`` outcomes whose recording fails non-retryably,
    ``record_replies[(operation, attempt)]`` is merged into that record's reply
    (the decision the record use case would return), and
    ``create_gate``, ``submit_gate`` and ``status_gate``, when set, hold that
    activity until the test opens them; ``status_hook`` runs inside each status
    call with the app name and the call's scheduled time.

    The pods activity reports the attempt's live pods: none by default; a job in
    ``pods_live_polls[app_name]`` reports one live pod for that many polls, and a job
    in ``pods_live_for[app_name]`` reports one while less than that long has passed
    since its first delete. ``pods_hook``, when set, runs inside each pods call.
    ``delete_failures[app_name]`` makes that many deletes of the job fail
    non-retryably before one succeeds; ``delete_times`` keeps the first delete
    that succeeded.
    """

    def __init__(self, client: Client) -> None:
        """Hold the client plus the scripts, gates and call records tests configure and inspect."""
        self._client = client
        self.callbacks: dict[tuple[str, int], list[tuple[int, bool, str | None]]] = {}
        self.submit_errors: dict[tuple[str, int], str] = {}
        self.states: dict[str, dict[str, Any] | list[dict[str, Any]]] = {}
        self.record_errors: set[tuple[str, int]] = set()
        self.record_replies: dict[tuple[str, int], dict[str, Any]] = {}
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
        self.pods_live_polls: dict[str, int] = {}
        self.pods_live_for: dict[str, timedelta] = {}
        self.pods_hook: Callable[[str], Awaitable[None]] | None = None
        self.pods_calls: list[str] = []
        self.pods_times: list[datetime] = []
        self.delete_times: dict[str, datetime] = {}
        self.delete_failures: dict[str, int] = {}

    @staticmethod
    def app_name(run_id: str, operation: str, attempt: int) -> str:
        """Build the application name of a run, operation and attempt."""
        return f"{run_id}-{operation}-{attempt}"

    def _workflow_id_of(self, run_id: str) -> str:
        """Look the workflow up on the created run, as the callback path does."""
        return next(c["execution_ref"] for c in self.created if c["run_id"] == run_id)

    @activity.defn(name=TableMaintenanceActivity.CREATE_MAINTENANCE_RUN)
    async def create_table_maintenance_run(self, request: dict) -> dict:
        """Return a running run for the request."""
        self.created.append(request)
        if self.create_gate is not None:
            await self.create_gate.wait()
        return {"run_id": request["run_id"], "status": "running"}

    @activity.defn(name=TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION)
    async def submit_maintenance_operation(self, request: dict) -> dict:
        """Submit the operation, or fail with the scripted submit error for it."""
        self.submits.append(request)
        if self.submit_gate is not None:
            await self.submit_gate.wait()
        key = (request["operation"], request["attempt"])
        if key in self.submit_errors:
            raise ApplicationError(self.submit_errors[key], type="ConflictError", non_retryable=True)
        handle = self._client.get_workflow_handle(self._workflow_id_of(request["run_id"]))
        for attempt, succeeded, error in self.callbacks.get(key, []):
            await handle.signal(
                TableMaintenanceSignal.OPERATION_RESULT,
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
            "job_name": self.app_name(request["run_id"], *key),
        }

    @activity.defn(name=TableMaintenanceActivity.GET_MAINTENANCE_JOB_STATUS)
    async def get_maintenance_job_status(self, request: dict) -> dict:
        """Return the scripted job status for the attempt and record the poll."""
        app_name = self.app_name(request["run_id"], request["operation"], request["attempt"])
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

    @activity.defn(name=TableMaintenanceActivity.RECORD_MAINTENANCE_OPERATION_RESULT)
    async def record_table_maintenance_operation_result(self, request: dict) -> dict:
        """Record the operation result, or fail when the script says the database is down."""
        self.records.append(request)
        key = (request["operation"], request["attempt"])
        if key in self.record_errors:
            raise ApplicationError("db down", type="ConflictError", non_retryable=True)
        return {"run_id": request["run_id"], "status": "running", **self.record_replies.get(key, {})}

    @activity.defn(name=TableMaintenanceActivity.DELETE_MAINTENANCE_JOB)
    async def delete_maintenance_job(self, request: dict) -> dict:
        """Record the job deletion and echo its attempt."""
        app_name = self.app_name(request["run_id"], request["operation"], request["attempt"])
        self.deletes.append(app_name)
        if self.deletes.count(app_name) <= self.delete_failures.get(app_name, 0):
            raise ApplicationError("apiserver unavailable", type="RuntimeError", non_retryable=True)
        self.delete_times.setdefault(app_name, activity.info().scheduled_time)
        return {
            "run_id": request["run_id"],
            "operation": request["operation"],
            "attempt": request["attempt"],
        }

    @activity.defn(name=TableMaintenanceActivity.GET_MAINTENANCE_JOB_PODS)
    async def get_maintenance_job_pods(self, request: dict) -> dict:
        """Report the scripted live pods of the attempt and record the poll."""
        app_name = self.app_name(request["run_id"], request["operation"], request["attempt"])
        scheduled = activity.info().scheduled_time
        self.pods_calls.append(app_name)
        self.pods_times.append(scheduled)
        if self.pods_hook is not None:
            await self.pods_hook(app_name)
        live = self.pods_calls.count(app_name) <= self.pods_live_polls.get(app_name, 0)
        deleted_at = self.delete_times.get(app_name)
        if app_name in self.pods_live_for and deleted_at is not None:
            live = live or scheduled - deleted_at < self.pods_live_for[app_name]
        return {"live_pods": [f"{app_name}-driver"] if live else []}

    def all(self) -> list:
        """Return every scripted activity for worker registration."""
        return [
            self.create_table_maintenance_run,
            self.submit_maintenance_operation,
            self.get_maintenance_job_status,
            self.record_table_maintenance_operation_result,
            self.delete_maintenance_job,
            self.get_maintenance_job_pods,
        ]
