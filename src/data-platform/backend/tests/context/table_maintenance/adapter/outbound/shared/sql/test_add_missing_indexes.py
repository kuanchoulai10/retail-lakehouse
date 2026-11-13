"""Test add_missing_indexes, which brings tables created by an older release up to the current indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import Column, Index, Integer, MetaData, String, Table, create_engine, inspect, text

from context.table_maintenance.adapter.outbound.shared.sql import add_missing_indexes, create_schema

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    """Provide a SQLite database in a temporary file."""
    return create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")


def _schema() -> MetaData:
    schema = MetaData()
    Table("t", schema, Column("id", Integer, primary_key=True), Column("state", String), Index("ix_t_state", "state"))
    return schema


def test_creates_an_index_a_stored_table_lacks(engine: Engine) -> None:
    """An index declared since the table was created is created, and named in the result."""
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY, state VARCHAR)"))

    assert add_missing_indexes(engine, schema=_schema()) == ["t.ix_t_state"]
    assert [i["name"] for i in inspect(engine).get_indexes("t")] == ["ix_t_state"]


def test_creates_nothing_when_up_to_date(engine: Engine) -> None:
    """A table created with its indexes needs none."""
    schema = _schema()
    schema.create_all(engine)
    assert add_missing_indexes(engine, schema=schema) == []


def test_skips_a_table_that_does_not_exist(engine: Engine) -> None:
    """A table not created yet is left to create_all."""
    assert add_missing_indexes(engine, schema=_schema()) == []


def test_create_schema_adds_the_candidate_state_index_to_an_older_database(engine: Engine) -> None:
    """A candidates table stored before its state index existed gets the index the rounds read by."""
    create_schema(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX ix_compaction_candidates_state"))

    create_schema(engine)

    assert "ix_compaction_candidates_state" in {i["name"] for i in inspect(engine).get_indexes("compaction_candidates")}
