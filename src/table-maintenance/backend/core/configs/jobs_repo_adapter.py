"""Define the JobsRepoAdapter enumeration."""

from __future__ import annotations

from enum import StrEnum


class JobsRepoAdapter(StrEnum):
    """Enumerate supported JobsRepo implementations."""

    IN_MEMORY = "in_memory"
    SQL = "sql"
