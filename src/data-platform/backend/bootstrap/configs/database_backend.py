"""Define the DatabaseBackend enumeration."""

from __future__ import annotations

from enum import StrEnum


class DatabaseBackend(StrEnum):
    """Identifies the SQL database the control plane stores its state in."""

    POSTGRES = "postgres"
    SQLITE = "sqlite"
