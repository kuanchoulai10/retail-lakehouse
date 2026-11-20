"""Define the PrefixMismatchMode enumeration."""

from __future__ import annotations

from enum import StrEnum


class PrefixMismatchMode(StrEnum):
    """Enumerate how ``remove_orphan_files`` treats a file whose prefix differs from the table's."""

    ERROR = "ERROR"
    IGNORE = "IGNORE"
    DELETE = "DELETE"
