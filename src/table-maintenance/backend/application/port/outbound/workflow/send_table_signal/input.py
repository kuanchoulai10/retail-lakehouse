"""Define the SendTableSignalGatewayInput."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SendTableSignalGatewayInput:
    """Name the table workflow, the signal and its payload."""

    table_uuid: str
    signal: str
    payload: dict[str, Any] = field(default_factory=dict)
    start_if_missing: bool = False
