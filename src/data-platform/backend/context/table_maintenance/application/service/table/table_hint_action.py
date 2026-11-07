"""Define the TableHintAction enumeration."""

from __future__ import annotations

from enum import StrEnum


class TableHintAction(StrEnum):
    """Enumerate what processing a table hint ended up doing."""

    DISCOVERY_REQUESTED = "discovery_requested"
    SIGNALLED = "signalled"
    RENAMED = "renamed"
    REGISTERED = "registered"
    IGNORED = "ignored"
