"""Test add_missing_columns, which brings tables created by an older release up to the current columns."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect, text

from context.table_maintenance.adapter.outbound.shared.sql import add_missing_columns

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    """Provide a SQLite database in a temporary file."""
    return create_engine(f"sqlite:///{tmp_path / 'db.sqlite'}")


def _old_table(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE t (id INTEGER PRIMARY KEY)"))
        connection.execute(text("INSERT INTO t (id) VALUES (1)"))


def test_adds_a_column_the_database_lacks(engine: Engine) -> None:
    """A nullable column the stored table lacks is added, and named in the result."""
    _old_table(engine)
    schema = MetaData()
    Table("t", schema, Column("id", Integer, primary_key=True), Column("extra", Integer, nullable=True))
    assert add_missing_columns(engine, schema=schema) == ["t.extra"]
    assert "extra" in {c["name"] for c in inspect(engine).get_columns("t")}


def test_a_column_with_a_server_default_fills_existing_rows(engine: Engine) -> None:
    """A not-null column with a server default is added, and rows already stored take the default."""
    _old_table(engine)
    schema = MetaData()
    Table(
        "t",
        schema,
        Column("id", Integer, primary_key=True),
        Column("version", Integer, nullable=False, server_default="1"),
        Column("priority", String(2), nullable=False, server_default="P2"),
    )
    assert add_missing_columns(engine, schema=schema) == ["t.version", "t.priority"]
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version, priority FROM t")).one() == (1, "P2")


def test_adds_nothing_when_up_to_date(engine: Engine) -> None:
    """A schema just created needs no column."""
    schema = MetaData()
    Table("t", schema, Column("id", Integer, primary_key=True), Column("extra", Integer, nullable=True))
    schema.create_all(engine)
    assert add_missing_columns(engine, schema=schema) == []


def test_skips_a_table_that_does_not_exist(engine: Engine) -> None:
    """A table not created yet is left to create_all."""
    schema = MetaData()
    Table("t", schema, Column("id", Integer, primary_key=True))
    assert add_missing_columns(engine, schema=schema) == []


def test_refuses_a_new_column_that_is_not_nullable_and_has_no_default(engine: Engine) -> None:
    """Rows already stored would have no value, so such a column is refused by name and nothing is added."""
    _old_table(engine)
    schema = MetaData()
    Table(
        "t",
        schema,
        Column("id", Integer, primary_key=True),
        Column("fine", Integer, nullable=True),
        Column("strict", Integer, nullable=False),
    )
    with pytest.raises(ValueError, match=r"t\.strict"):
        add_missing_columns(engine, schema=schema)
    assert {c["name"] for c in inspect(engine).get_columns("t")} == {"id"}
