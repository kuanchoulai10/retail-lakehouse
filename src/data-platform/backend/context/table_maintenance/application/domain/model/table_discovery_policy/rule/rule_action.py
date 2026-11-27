"""Define the RuleAction enumeration."""

from __future__ import annotations

from enum import StrEnum


class RuleAction(StrEnum):
    """What a discovery rule does to the tables it matches: bring them under management or leave them out."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
