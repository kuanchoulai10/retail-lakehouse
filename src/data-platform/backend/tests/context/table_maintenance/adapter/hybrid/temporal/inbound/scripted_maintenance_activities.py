"""Define scripted fakes of the activities the table maintenance workflow calls."""

from __future__ import annotations

from datetime import datetime, timedelta
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

    from temporalio.client import Client


class ScriptedMaintenanceActivities:
    """Record every call and play back scripted callbacks, errors and job states.

    ``callbacks[(operation, attempt)]`` lists the results the fake Spark job sends
    while that attempt is submitted, as ``(attempt, succeeded, error)`` tuples, so a
    script can also send a stale result for another attempt. ``states[app_name]``
    is the job state the status activity reports (RUNNING once the driver started, PENDING before,
    by default); a list plays
    its states in order and then repeats the last one. ``record_errors`` lists the
    ``(operation, attempt)`` outcomes whose recording fails non-retryably,
    ``record_replies[(operation, attempt)]`` is merged into that record's reply
    (the decision the record use case would return), and
    ``record_hook``, when set, runs inside each record with the request;
    ``submit_gate`` and ``status_gate``, when set, hold that
    activity until the test opens them; ``status_hook`` runs inside each status
    call with the app name and the call's scheduled time.

    The pods activity reports the attempt's live pods: none by default; a job in
    ``pods_live_polls[app_name]`` reports one live pod for that many polls, and a job
    in ``pods_live_for[app_name]`` reports one while less than that long has passed
    since its first delete. ``pods_hook``, when set, runs inside each pods call, and
    ``delete_hook``, when set, inside each delete, with the app name.
    ``delete_failures[app_name]`` makes that many deletes of the job fail
    non-retryably before one succeeds; ``delete_times`` keeps the first delete
    that succeeded.

    Each status also reports when the job's driver started: at its submit by default.
    ``driver_starts[app_name]`` is ``(reported_after, started_after)``: polls less than
    ``reported_after`` past the submit report no start, later ones report the submit plus
    ``started_after`` (negative for a clock before the submit); ``None`` never reports one.
    An app in ``naive_driver_starts`` reports its start without a time zone.
    ``running_records`` keeps each record of a running attempt, and the attempts in
    ``running_record_errors`` fail that record non-retryably.

    ``raises`` keeps each priority raise request; its reply is ``raise_reply`` when set, else the run
    raised to the requested priority (P0 when none is named), and the requests in
    ``raise_errors`` (by position, from 0) fail non-retryably. ``raise_hook``, when set, runs inside
    each raise with the request. A job reads ``NOT_FOUND`` from the first delete that succeeded after
    its latest submit on, until it is submitted again; one in ``vanish_after_delete[app_name]`` only
    once that long has passed since that delete (a later delete does not move it).

    ``skips`` keeps each skip request; a skip replies with the run skipped, and the runs in
    ``skip_errors`` (by run id) fail their skip as not found, non-retryably. ``cancels`` keeps each
    cancel of a run with no attempt in flight; a cancel replies with the run cancelled, and the runs
    in ``cancel_errors`` (by run id) fail their cancel as not found, non-retryably.
    ``run_priorities`` holds each run's priority as the database would: the one each raise that raised
    it replied, P3 (the plan's default) before that; ``submitted_priorities`` keeps, per submit, its
    run's priority then. A fake Spark job sends its results to the workflow that submitted it.
    """

    def __init__(self, client: Client) -> None:
        """Hold the client plus the scripts, gates and call records tests configure and inspect."""
        self._client = client
        self.callbacks: dict[tuple[str, int], list[tuple[int, bool, str | None]]] = {}
        self.submit_errors: dict[tuple[str, int], str] = {}
        self.states: dict[str, dict[str, Any] | list[dict[str, Any]]] = {}
        self.record_errors: set[tuple[str, int]] = set()
        self.record_replies: dict[tuple[str, int], dict[str, Any]] = {}
        self.skip_errors: set[str] = set()
        self.cancel_errors: set[str] = set()
        self.submit_gate: asyncio.Event | None = None
        self.status_gate: asyncio.Event | None = None
        self.status_hook: Callable[[str, datetime], Awaitable[None]] | None = None
        self.record_hook: Callable[[dict], Awaitable[None]] | None = None
        self.status_times: list[datetime] = []
        self.submits: list[dict] = []
        self.records: list[dict] = []
        self.deletes: list[str] = []
        self.status_calls: list[str] = []
        self.pods_live_polls: dict[str, int] = {}
        self.pods_live_for: dict[str, timedelta] = {}
        self.pods_hook: Callable[[str], Awaitable[None]] | None = None
        self.delete_hook: Callable[[str], Awaitable[None]] | None = None
        self.pods_calls: list[str] = []
        self.pods_times: list[datetime] = []
        self.delete_times: dict[str, datetime] = {}
        self._deleted_since_submit: dict[str, datetime] = {}
        self.delete_failures: dict[str, int] = {}
        self.driver_starts: dict[str, tuple[timedelta, timedelta] | None] = {}
        self.submitted_at: dict[str, datetime] = {}
        self.naive_driver_starts: set[str] = set()
        self.running_records: list[dict] = []
        self.running_record_errors: set[tuple[str, int]] = set()
        self.raises: list[dict] = []
        self.raise_reply: dict[str, Any] | None = None
        self.raise_errors: set[int] = set()
        self.raise_hook: Callable[[dict], Awaitable[None]] | None = None
        self.submit_hook: Callable[[dict], Awaitable[None]] | None = None
        self.vanish_after_delete: dict[str, timedelta] = {}
        self.skips: list[dict] = []
        self.cancels: list[dict] = []
        self.run_priorities: dict[str, str] = {}
        self.submitted_priorities: list[str | None] = []

    @staticmethod
    def app_name(run_id: str, operation: str, attempt: int) -> str:
        """Build the application name of a run, operation and attempt."""
        return f"{run_id}-{operation}-{attempt}"

    @activity.defn(name=TableMaintenanceActivity.SKIP_MAINTENANCE_RUN)
    async def skip_maintenance_run(self, request: dict) -> dict:
        """Record the skip and reply with the run skipped."""
        self.skips.append(request)
        if request["run_id"] in self.skip_errors:
            raise ApplicationError("no such run", type="NotFoundError", non_retryable=True)
        return {"run_id": request["run_id"], "status": "skipped", "skipped": True}

    @activity.defn(name=TableMaintenanceActivity.CANCEL_MAINTENANCE_RUN)
    async def cancel_maintenance_run(self, request: dict) -> dict:
        """Record the cancel and reply with the run cancelled."""
        self.cancels.append(request)
        if request["run_id"] in self.cancel_errors:
            raise ApplicationError("no such run", type="NotFoundError", non_retryable=True)
        return {"run_id": request["run_id"], "status": "cancelled", "cancelled": True}

    @activity.defn(name=TableMaintenanceActivity.SUBMIT_MAINTENANCE_OPERATION)
    async def submit_maintenance_operation(self, request: dict) -> dict:
        """Submit the operation, or fail with the scripted submit error for it."""
        self.submits.append(request)
        self.submitted_priorities.append(self.run_priorities.get(request["run_id"], "P3"))
        self.submitted_at[self.app_name(request["run_id"], request["operation"], request["attempt"])] = (
            datetime.fromisoformat(request["now"])
        )
        if self.submit_gate is not None:
            await self.submit_gate.wait()
        if self.submit_hook is not None:
            await self.submit_hook(request)
        key = (request["operation"], request["attempt"])
        if key in self.submit_errors:
            raise ApplicationError(self.submit_errors[key], type="ConflictError", non_retryable=True)
        workflow_id = activity.info().workflow_id
        assert workflow_id is not None
        handle = self._client.get_workflow_handle(workflow_id)
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
        if self._vanished(app_name, activity.info().scheduled_time):
            return {"state": "NOT_FOUND", "error": None, "started_running_at": None}
        driver_started_at = self._driver_started_at(app_name, activity.info().scheduled_time)
        unscripted = {"state": "RUNNING" if driver_started_at else "PENDING", "error": None}
        state = self.states.get(app_name, unscripted)
        if isinstance(state, list):
            calls = self.status_calls.count(app_name)
            state = state[min(calls, len(state)) - 1]
        return {"started_running_at": driver_started_at, **state}

    def _vanished(self, app_name: str, polled_at: datetime) -> bool:
        deleted_at = self._deleted_since_last_submit(app_name)
        if deleted_at is None:
            return False
        return polled_at - deleted_at >= self.vanish_after_delete.get(app_name, timedelta(0))

    def _driver_started_at(self, app_name: str, polled_at: datetime) -> str | None:
        submitted_at = self.submitted_at[app_name]
        start = self.driver_starts.get(app_name, (timedelta(0), timedelta(0)))
        if start is None or polled_at - submitted_at < start[0]:
            return None
        started = submitted_at + start[1]
        return (started.replace(tzinfo=None) if app_name in self.naive_driver_starts else started).isoformat()

    def _deleted_since_last_submit(self, app_name: str) -> datetime | None:
        deleted_at = self._deleted_since_submit.get(app_name)
        if deleted_at is None or self.submitted_at[app_name] > deleted_at:
            return None
        return deleted_at

    @activity.defn(name=TableMaintenanceActivity.RECORD_MAINTENANCE_ATTEMPT_RUNNING)
    async def record_maintenance_attempt_running(self, request: dict) -> dict:
        """Record that the attempt's driver started, or fail when the script says the database is down."""
        self.running_records.append(request)
        if (request["operation"], request["attempt"]) in self.running_record_errors:
            raise ApplicationError("db down", type="ConflictError", non_retryable=True)
        return {"status": "running", "started_running_at": request["started_running_at"]}

    @activity.defn(name=TableMaintenanceActivity.RAISE_MAINTENANCE_RUN_PRIORITY)
    async def raise_table_maintenance_run_priority(self, request: dict) -> dict:
        """Record the raise and reply with the scripted priority, or fail when the script says so."""
        position = len(self.raises)
        self.raises.append(request)
        if self.raise_hook is not None:
            await self.raise_hook(request)
        if position in self.raise_errors:
            raise ApplicationError("db down", type="ConflictError", non_retryable=True)
        reply = self.raise_reply or {"priority": request["priority"] or "P0", "raised": True}
        if reply["raised"]:
            self.run_priorities[request["run_id"]] = str(reply["priority"])
        return reply

    @activity.defn(name=TableMaintenanceActivity.RECORD_MAINTENANCE_OPERATION_RESULT)
    async def record_table_maintenance_operation_result(self, request: dict) -> dict:
        """Record the operation result, or fail when the script says the database is down."""
        self.records.append(request)
        if self.record_hook is not None:
            await self.record_hook(request)
        key = (request["operation"], request["attempt"])
        if key in self.record_errors:
            raise ApplicationError("db down", type="ConflictError", non_retryable=True)
        return {"run_id": request["run_id"], "status": "running", **self.record_replies.get(key, {})}

    @activity.defn(name=TableMaintenanceActivity.DELETE_MAINTENANCE_JOB)
    async def delete_maintenance_job(self, request: dict) -> dict:
        """Record the job deletion and echo its attempt."""
        app_name = self.app_name(request["run_id"], request["operation"], request["attempt"])
        self.deletes.append(app_name)
        if self.delete_hook is not None:
            await self.delete_hook(app_name)
        if self.deletes.count(app_name) <= self.delete_failures.get(app_name, 0):
            raise ApplicationError("apiserver unavailable", type="RuntimeError", non_retryable=True)
        self.delete_times.setdefault(app_name, activity.info().scheduled_time)
        if self._deleted_since_last_submit(app_name) is None:
            self._deleted_since_submit[app_name] = activity.info().scheduled_time
        return {
            "run_id": request["run_id"],
            "operation": request["operation"],
            "attempt": request["attempt"],
        }

    @activity.defn(name=TableMaintenanceActivity.GET_MAINTENANCE_JOB_PROCESSES)
    async def get_maintenance_job_processes(self, request: dict) -> dict:
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
        return {"live_processes": [f"{app_name}-driver"] if live else []}

    def all(self) -> list:
        """Return every scripted activity for worker registration."""
        return [
            self.submit_maintenance_operation,
            self.get_maintenance_job_status,
            self.record_table_maintenance_operation_result,
            self.delete_maintenance_job,
            self.get_maintenance_job_processes,
            self.record_maintenance_attempt_running,
            self.raise_table_maintenance_run_priority,
            self.skip_maintenance_run,
            self.cancel_maintenance_run,
        ]
