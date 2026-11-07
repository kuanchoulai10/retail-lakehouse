"""Define the RuleEffect enumeration."""

from __future__ import annotations

from enum import StrEnum


class RuleEffect(StrEnum):
    """Enumerate what a matching discovery rule does to a table."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
