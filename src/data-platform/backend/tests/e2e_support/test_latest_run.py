"""Test latest_run, which reads the id and status of a workflow's latest run."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

import pytest
from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.service import RPCError, RPCStatusCode

from e2e.support import TemporalSession, latest_run


class _Client:
    def __init__(self, answer: SimpleNamespace | RPCError) -> None:
        self.asked: list[str] = []
        self._answer = answer

    def get_workflow_handle(self, workflow_id: str) -> SimpleNamespace:
        async def describe() -> SimpleNamespace:
            self.asked.append(workflow_id)
            if isinstance(self._answer, RPCError):
                raise self._answer
            return self._answer

        return SimpleNamespace(describe=describe)


def _latest(answer: SimpleNamespace | RPCError) -> tuple[tuple[str, WorkflowExecutionStatus] | None, list[str]]:
    client = _Client(answer)
    session = TemporalSession(asyncio.new_event_loop(), cast(Client, client))
    try:
        return latest_run(session, "table-discovery:catalog=c"), client.asked
    finally:
        session.close()


def test_the_latest_run_is_its_run_id_and_status():
    """The workflow asked for answers the run Temporal describes."""
    described = SimpleNamespace(run_id="r-2", status=WorkflowExecutionStatus.COMPLETED)
    assert _latest(described) == (("r-2", WorkflowExecutionStatus.COMPLETED), ["table-discovery:catalog=c"])


def test_a_workflow_temporal_does_not_know_has_no_run():
    """NOT_FOUND is the answer "never ran", not an error."""
    assert _latest(RPCError("gone", RPCStatusCode.NOT_FOUND, b""))[0] is None


def test_any_other_failure_is_raised():
    """A Temporal that does not answer is never read as "never ran"."""
    with pytest.raises(RPCError):
        _latest(RPCError("down", RPCStatusCode.UNAVAILABLE, b""))
