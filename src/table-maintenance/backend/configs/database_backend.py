from __future__ import annotations

from enum import StrEnum


class DatabaseBackend(StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"
