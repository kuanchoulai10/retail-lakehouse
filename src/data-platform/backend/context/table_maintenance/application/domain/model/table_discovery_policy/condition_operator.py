"""Define the ConditionOperator enumeration."""

from __future__ import annotations

from enum import StrEnum


class ConditionOperator(StrEnum):
    """Enumerate how a discovery condition matches the attribute it reads against its values."""

    GLOB = "glob"
