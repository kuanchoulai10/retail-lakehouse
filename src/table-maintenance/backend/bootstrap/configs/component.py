"""Component enumeration for entry point dispatch."""

from __future__ import annotations

from enum import StrEnum


class Component(StrEnum):
    """Identifies which application component to run."""

    API = "api"
    SCHEDULER = "scheduler"
    MESSAGING = "messaging"
