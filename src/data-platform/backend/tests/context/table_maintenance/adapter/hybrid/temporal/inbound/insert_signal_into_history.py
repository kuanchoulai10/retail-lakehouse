"""Define the helper that adds a signal an older worker received, and ignored, into a recorded history."""

from __future__ import annotations

import base64
import json
from typing import Any

_ADDED = 4


def insert_signal_into_history(history_json: str, *, after_event_id: int, signal: str, arg: dict[str, Any]) -> str:
    """Return the history with ``signal`` delivered right after event ``after_event_id``.

    The signal is followed by one workflow task that completed with no command,
    which is what a worker whose workflow had no handler for it recorded (the
    Python SDK buffers such a signal). Later events are renumbered, and every
    ``...EventId`` reference to them follows.
    """
    history = json.loads(history_json)
    events: list[dict[str, Any]] = history["events"]
    index = next(i for i, e in enumerate(events) if int(e["eventId"]) == after_event_id)
    for event in events:
        _shift(event, after_event_id)
    at = events[index]["eventTime"]
    first = after_event_id + 1
    payload = {
        "metadata": {"encoding": base64.b64encode(b"json/plain").decode()},
        "data": base64.b64encode(json.dumps(arg).encode()).decode(),
    }
    added = [
        {
            "eventId": str(first),
            "eventTime": at,
            "eventType": "EVENT_TYPE_WORKFLOW_EXECUTION_SIGNALED",
            "workflowExecutionSignaledEventAttributes": {
                "signalName": signal,
                "input": {"payloads": [payload]},
                "identity": "old-worker",
            },
        },
        {
            "eventId": str(first + 1),
            "eventTime": at,
            "eventType": "EVENT_TYPE_WORKFLOW_TASK_SCHEDULED",
            "workflowTaskScheduledEventAttributes": {
                "taskQueue": {"name": "table-maintenance"},
                "startToCloseTimeout": "10s",
                "attempt": 1,
            },
        },
        {
            "eventId": str(first + 2),
            "eventTime": at,
            "eventType": "EVENT_TYPE_WORKFLOW_TASK_STARTED",
            "workflowTaskStartedEventAttributes": {"scheduledEventId": str(first + 1), "identity": "old-worker"},
        },
        {
            "eventId": str(first + 3),
            "eventTime": at,
            "eventType": "EVENT_TYPE_WORKFLOW_TASK_COMPLETED",
            "workflowTaskCompletedEventAttributes": {
                "scheduledEventId": str(first + 1),
                "startedEventId": str(first + 2),
                "identity": "old-worker",
                "sdkMetadata": {},
                "meteringMetadata": {},
            },
        },
    ]
    history["events"] = events[: index + 1] + added + events[index + 1 :]
    return json.dumps(history)


def _shift(node: Any, after: int) -> None:  # noqa: ANN401
    """Renumber, in place, every event id and event id reference past ``after``."""
    if isinstance(node, dict):
        for key, value in node.items():
            if (key == "eventId" or key.endswith("EventId")) and isinstance(value, str) and value.isdigit():
                if int(value) > after:
                    node[key] = str(int(value) + _ADDED)
            else:
                _shift(value, after)
    elif isinstance(node, list):
        for item in node:
            _shift(item, after)
