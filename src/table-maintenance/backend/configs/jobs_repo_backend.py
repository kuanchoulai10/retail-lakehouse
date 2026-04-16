from __future__ import annotations

from enum import StrEnum


class JobsRepoBackend(StrEnum):
    POSTGRES = "postgres"
    SQLITE = "sqlite"
    IN_MEMORY = "in_memory"
