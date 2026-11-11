"""Define the RuleAction enumeration."""

from __future__ import annotations

from enum import StrEnum


class RuleAction(StrEnum):
    """Enumerate what a deciding discovery rule does to a table."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
