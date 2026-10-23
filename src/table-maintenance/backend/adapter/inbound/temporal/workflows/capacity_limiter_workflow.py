"""Define the CapacityLimiterWorkflow."""

from __future__ import annotations

from datetime import datetime, timedelta

from temporalio import workflow
from temporalio.exceptions import FailureError

from adapter.temporal_contracts.capacity_acquire_signal import CapacityAcquireSignal
from adapter.temporal_contracts.capacity_limiter_input import CapacityLimiterInput
from adapter.temporal_contracts.capacity_release_signal import CapacityReleaseSignal
from adapter.temporal_contracts.workflow_names import CAPACITY_LIMITER_WORKFLOW
from application.domain.model.maintenance.workflow_ids import (
    SIGNAL_CAPACITY_ACQUIRE,
    SIGNAL_CAPACITY_GRANTED,
    SIGNAL_CAPACITY_RELEASE,
)


@workflow.defn(name=CAPACITY_LIMITER_WORKFLOW)
class CapacityLimiterWorkflow:
    """Grant a bounded number of Spark capacity slots, first come first served.

    A requester signals ``acquire``; when a slot is free the limiter records it as a
    holder and signals ``capacity_granted(request_id)`` back to the requester. A
    holder frees its slot with ``release``, or loses it once its lease runs out, so
    a crashed requester cannot hold capacity forever. A requester that no longer
    exists when granted is dropped and the next one is granted.
    """

    @workflow.init
    def __init__(self, input: CapacityLimiterInput) -> None:  # noqa: A002
        """Restore the limit, lease, holders and queue carried by the input."""
        self._limit = input.limit
        self._lease_seconds = input.lease_seconds
        self._holders: dict[str, dict] = {
            request_id: dict(holder) for request_id, holder in input.holders.items()
        }
        self._queue: list[dict] = [dict(entry) for entry in input.queue]
        self._regrants: list[str] = []
        self._changed = False

    @workflow.run
    async def run(self, input: CapacityLimiterInput) -> None:  # noqa: A002
        """Grant, evict and wait for signals until continue-as-new is suggested."""
        while True:
            self._changed = False
            self._evict_expired()
            await self._resend_grants()
            await self._grant_free_slots()
            if workflow.info().is_continue_as_new_suggested():
                await workflow.wait_condition(workflow.all_handlers_finished)
                workflow.continue_as_new(
                    CapacityLimiterInput(
                        limit=self._limit,
                        lease_seconds=self._lease_seconds,
                        holders=self._holders,
                        queue=self._queue,
                    )
                )
            try:
                await workflow.wait_condition(
                    lambda: self._changed, timeout=self._time_to_next_expiry()
                )
            except TimeoutError:
                pass

    @workflow.signal(name=SIGNAL_CAPACITY_ACQUIRE)
    def acquire(self, signal: CapacityAcquireSignal) -> None:
        """Queue a request; a held one has its grant re-sent, a queued one is kept."""
        if signal.request_id in self._holders:
            self._regrants.append(signal.request_id)
        elif not any(e["request_id"] == signal.request_id for e in self._queue):
            self._queue.append(
                {
                    "request_id": signal.request_id,
                    "requester_workflow_id": signal.requester_workflow_id,
                }
            )
        self._changed = True

    @workflow.signal(name=SIGNAL_CAPACITY_RELEASE)
    def release(self, signal: CapacityReleaseSignal) -> None:
        """Free a held slot or withdraw a queued request; unknown ids are ignored."""
        self._holders.pop(signal.request_id, None)
        self._queue = [e for e in self._queue if e["request_id"] != signal.request_id]
        self._changed = True

    @workflow.query
    def state(self) -> dict:
        """Report the holders and the queue."""
        return {"holders": self._holders, "queue": self._queue}

    def _evict_expired(self) -> None:
        now = workflow.now()
        for request_id, holder in list(self._holders.items()):
            if self._expires_at(holder) <= now:
                workflow.logger.warning(
                    "capacity lease of %s expired; evicting %s",
                    request_id,
                    holder["requester_workflow_id"],
                )
                del self._holders[request_id]

    async def _resend_grants(self) -> None:
        pending, self._regrants = self._regrants, []
        for request_id in pending:
            holder = self._holders.get(request_id)
            if holder is None:
                continue
            if not await self._notify(holder["requester_workflow_id"], request_id):
                self._holders.pop(request_id, None)

    async def _grant_free_slots(self) -> None:
        while self._queue and len(self._holders) < self._limit:
            entry = self._queue.pop(0)
            request_id = entry["request_id"]
            requester = entry["requester_workflow_id"]
            self._holders[request_id] = {
                "requester_workflow_id": requester,
                "granted_at": workflow.now().isoformat(),
            }
            if not await self._notify(requester, request_id):
                self._holders.pop(request_id, None)

    async def _notify(self, requester_workflow_id: str, request_id: str) -> bool:
        handle = workflow.get_external_workflow_handle(requester_workflow_id)
        try:
            await handle.signal(SIGNAL_CAPACITY_GRANTED, request_id)
        except FailureError as error:
            workflow.logger.warning(
                "requester %s of %s is gone (%s); dropping it",
                requester_workflow_id,
                request_id,
                error,
            )
            return False
        return True

    def _time_to_next_expiry(self) -> timedelta | None:
        if not self._holders:
            return None
        earliest = min(self._expires_at(h) for h in self._holders.values())
        return max(earliest - workflow.now(), timedelta(seconds=1))

    def _expires_at(self, holder: dict) -> datetime:
        granted_at = datetime.fromisoformat(holder["granted_at"])
        return granted_at + timedelta(seconds=self._lease_seconds)
