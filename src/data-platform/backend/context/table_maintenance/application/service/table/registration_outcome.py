"""Define the RegistrationOutcome enumeration."""

from __future__ import annotations

from enum import StrEnum


class RegistrationOutcome(StrEnum):
    """Enumerate what registering one discovered table amounted to."""

    MANAGED = "managed"
    UNMANAGED = "unmanaged"
