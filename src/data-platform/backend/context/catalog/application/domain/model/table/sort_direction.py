"""Define the SortDirection enum."""

from __future__ import annotations

from enum import StrEnum


class SortDirection(StrEnum):
    """The direction of one sort field."""

    ASC = "asc"
    DESC = "desc"
