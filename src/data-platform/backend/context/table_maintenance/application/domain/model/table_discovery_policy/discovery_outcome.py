"""Define the DiscoveryOutcome enumeration."""

from __future__ import annotations

from enum import StrEnum


class DiscoveryOutcome(StrEnum):
    """Enumerate what a discovery decision does to a table: manage it or leave it unmanaged."""

    MANAGE = "manage"
    UNMANAGE = "unmanage"
