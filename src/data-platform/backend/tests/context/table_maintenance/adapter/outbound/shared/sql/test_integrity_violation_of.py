"""Test how a refused write is told apart, on SQLite (the tests) and on Postgres (the cluster)."""

from __future__ import annotations

import sqlite3

import psycopg.errors
import pytest
from sqlalchemy.exc import IntegrityError

from context.table_maintenance.adapter.outbound.shared.sql import IntegrityViolation, integrity_violation_of


def _sqlite_refusal(statement: str) -> sqlite3.IntegrityError:
    """Run ``statement`` against a small schema with foreign keys on, and return the refusal it raises."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("CREATE TABLE policies (id TEXT PRIMARY KEY)")
    conn.execute(
        "CREATE TABLE places (id TEXT PRIMARY KEY, name TEXT UNIQUE NOT NULL, policy TEXT REFERENCES policies)"
    )
    conn.execute("INSERT INTO places VALUES ('p1', 'one', NULL)")
    with pytest.raises(sqlite3.IntegrityError) as refused:
        conn.execute(statement)
    return refused.value


def _wrapped(orig: BaseException) -> IntegrityError:
    return IntegrityError("INSERT ...", {}, orig)


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("INSERT INTO places VALUES ('p1', 'two', NULL)", IntegrityViolation.UNIQUE),
        ("INSERT INTO places VALUES ('p2', 'one', NULL)", IntegrityViolation.UNIQUE),
        ("INSERT INTO places VALUES ('p2', 'two', 'gone')", IntegrityViolation.FOREIGN_KEY),
        ("INSERT INTO places VALUES ('p2', NULL, NULL)", IntegrityViolation.OTHER),
    ],
    ids=["sqlite-primary-key", "sqlite-unique", "sqlite-foreign-key", "sqlite-not-null"],
)
def test_a_sqlite_refusal_is_told_apart(statement: str, expected: IntegrityViolation):
    """SQLite names the constraint kind in the extended error name."""
    assert integrity_violation_of(_wrapped(_sqlite_refusal(statement))) == expected


@pytest.mark.parametrize(
    ("orig", "expected"),
    [
        (psycopg.errors.UniqueViolation("duplicate key"), IntegrityViolation.UNIQUE),
        (psycopg.errors.ForeignKeyViolation("violates foreign key"), IntegrityViolation.FOREIGN_KEY),
        (psycopg.errors.NotNullViolation("null value"), IntegrityViolation.OTHER),
    ],
    ids=["postgres-unique", "postgres-foreign-key", "postgres-not-null"],
)
def test_a_postgres_refusal_is_told_apart(orig: BaseException, expected: IntegrityViolation):
    """Postgres names the constraint kind in the SQLSTATE psycopg carries."""
    assert integrity_violation_of(_wrapped(orig)) == expected


def test_a_refusal_from_a_driver_naming_no_kind_is_other():
    """A driver error that carries neither a SQLSTATE nor a SQLite error name is not guessed from its text."""
    assert integrity_violation_of(_wrapped(Exception("UNIQUE constraint failed"))) == IntegrityViolation.OTHER
