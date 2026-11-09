"""Define the ConditionCombine enumeration."""

from __future__ import annotations

from enum import StrEnum


class ConditionCombine(StrEnum):
    """Enumerate how the conditions of an operation combine into its verdict."""

    ALL = "all"
    ANY = "any"
