"""Define the TableDiscoverySignal names."""

from __future__ import annotations

from enum import StrEnum


class TableDiscoverySignal(StrEnum):
    """Name the signals a table discovery workflow receives."""

    REQUEST_RESCAN = "request_rescan"
