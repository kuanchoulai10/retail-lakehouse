"""Define the DatabaseBackend enumeration."""

from __future__ import annotations

from enum import StrEnum


class DatabaseBackend(StrEnum):
    """Enumerate supported database backends."""

    SQLITE = "sqlite"
    POSTGRES = "postgres"
