"""Define the integrity_violation_of function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.adapter.outbound.shared.sql.integrity_violation import IntegrityViolation

if TYPE_CHECKING:
    from sqlalchemy.exc import IntegrityError

_KINDS = {
    "23505": IntegrityViolation.UNIQUE,
    "23503": IntegrityViolation.FOREIGN_KEY,
    "SQLITE_CONSTRAINT_PRIMARYKEY": IntegrityViolation.UNIQUE,
    "SQLITE_CONSTRAINT_UNIQUE": IntegrityViolation.UNIQUE,
    "SQLITE_CONSTRAINT_FOREIGNKEY": IntegrityViolation.FOREIGN_KEY,
}


def integrity_violation_of(error: IntegrityError) -> IntegrityViolation:
    """Return which kind of constraint the refused write broke, read from the driver's error code.

    Postgres gives the SQLSTATE (psycopg's ``sqlstate``: 23505 a duplicate key, 23503 a missing
    foreign key) and SQLite its extended error name (``sqlite_errorname``). The message text is never
    read, so a driver that names neither gives ``OTHER``.
    """
    code = getattr(error.orig, "sqlstate", None) or getattr(error.orig, "sqlite_errorname", None)
    return _KINDS.get(code, IntegrityViolation.OTHER) if isinstance(code, str) else IntegrityViolation.OTHER
