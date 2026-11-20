"""Define the RaisePrioritySignal workflow contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RaisePrioritySignal:
    """Payload of the raise_priority signal sent to a table maintenance workflow.

    ``priority`` is the priority a manual run asked for; None asks for the table's current priority.
    """

    priority: str | None = None
