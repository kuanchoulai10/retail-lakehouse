"""Define the IntegrityViolation enum."""

from __future__ import annotations

from enum import StrEnum


class IntegrityViolation(StrEnum):
    """Name the kind of constraint a refused write broke, whatever the database."""

    UNIQUE = "unique"
    FOREIGN_KEY = "foreign_key"
    OTHER = "other"
