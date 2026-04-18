from __future__ import annotations

from enum import StrEnum


class JobsRepoAdapter(StrEnum):
    IN_MEMORY = "in_memory"
    SQL = "sql"
