"""Test scheduled_workflows, which lists the workflows a schedule's recent actions started."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import cast

from temporalio.client import Client, ScheduleActionExecutionStartWorkflow

from e2e.support import TemporalSession, scheduled_workflows

FIRST = "table-discovery:round-2026-11-27T00:00:00Z"
SECOND = "table-discovery:round-2026-11-27T00:10:00Z"


class _Client:
    def __init__(self, actions: list[object]) -> None:
        self.asked: list[str] = []
        self._actions = actions

    def get_schedule_handle(self, schedule_id: str) -> SimpleNamespace:
        async def describe() -> SimpleNamespace:
            self.asked.append(schedule_id)
            recent = [SimpleNamespace(action=action) for action in self._actions]
            return SimpleNamespace(info=SimpleNamespace(recent_actions=recent))

        return SimpleNamespace(describe=describe)


def _started(workflow_id: str) -> ScheduleActionExecutionStartWorkflow:
    return ScheduleActionExecutionStartWorkflow(workflow_id, f"run-of-{workflow_id}")


def _scheduled(actions: list[object]) -> tuple[list[str], list[str]]:
    client = _Client(actions)
    session = TemporalSession(asyncio.new_event_loop(), cast(Client, client))
    try:
        return scheduled_workflows(session, "table-discovery"), client.asked
    finally:
        session.close()


def test_the_workflow_ids_of_the_recent_actions_come_oldest_first():
    """Each id is the action's workflow id, which Temporal suffixes with the time it was scheduled for."""
    assert _scheduled([_started(FIRST), _started(SECOND)]) == ([FIRST, SECOND], ["table-discovery"])


def test_an_action_that_started_no_workflow_is_left_out():
    """Only an action that started a workflow names one."""
    assert _scheduled([object(), _started(FIRST)])[0] == [FIRST]


def test_a_schedule_that_started_nothing_yet_lists_nothing():
    """A schedule just created has no recent action."""
    assert _scheduled([])[0] == []
