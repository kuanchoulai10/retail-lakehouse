"""Define the SendTableSignalGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SendTableSignalGatewayInput:
    """Name the table workflow, the signal and its payload.

    ``table_name`` is the fully qualified ``catalog.namespace.table`` name; it
    becomes the workflow's summary when this signal starts it, and a running
    workflow keeps the summary it started with.
    """

    table_uuid: str
    table_name: str
    signal: str
    payload: dict[str, Any] = field(default_factory=dict)
    start_if_missing: bool = False
