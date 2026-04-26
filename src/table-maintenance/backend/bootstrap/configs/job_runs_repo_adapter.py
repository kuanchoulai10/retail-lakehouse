"""Define the JobRunsRepoAdapter enumeration."""

from __future__ import annotations

from enum import StrEnum


class JobRunsRepoAdapter(StrEnum):
    """Enumerate supported JobRunsRepo implementations."""

    IN_MEMORY = "in_memory"
    SQL = "sql"
