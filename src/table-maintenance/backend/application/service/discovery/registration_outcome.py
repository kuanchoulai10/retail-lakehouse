"""Define the RegistrationOutcome enumeration."""

from __future__ import annotations

from enum import StrEnum


class RegistrationOutcome(StrEnum):
    """Enumerate what registering one discovered table amounted to."""

    REGISTERED = "registered"
    NOT_SELECTED = "not_selected"
    SKIPPED = "skipped"
