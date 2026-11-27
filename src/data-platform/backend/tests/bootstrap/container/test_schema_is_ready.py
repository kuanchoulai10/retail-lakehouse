"""Test that the schema counts as ready only once the migrations have created it and seeded the maintenance default."""

from __future__ import annotations

from sqlalchemy import create_engine

from bootstrap.container import build_engine, build_repositories, run_migrations, schema_is_ready
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.domain.model.table_maintenance_policy import DEFAULT_POLICY_ID
from tests.bootstrap.container.container_support import sqlite_settings


def test_schema_is_not_ready_without_tables():
    """A database the migrations never ran on is not ready."""
    assert schema_is_ready(build_engine(sqlite_settings().database)) is False


def test_schema_is_ready_after_migrations():
    """After the migrations the schema is ready."""
    engine = build_engine(sqlite_settings().database)
    run_migrations(engine)

    assert schema_is_ready(engine) is True


def test_the_maintenance_default_alone_is_ready():
    """The maintenance default is the only seed; no discovery policy is needed."""
    engine = build_engine(sqlite_settings().database)
    run_migrations(engine)

    assert build_repositories(engine).table_discovery_policies.list_all() == []
    assert schema_is_ready(engine) is True


def test_tables_without_the_seed_are_not_ready():
    """The tables alone are not enough: the services need the default maintenance policy."""
    engine = build_engine(sqlite_settings().database)
    create_schema(engine)

    assert schema_is_ready(engine) is False


def test_without_the_maintenance_default_it_is_not_ready():
    """A migrated database whose maintenance default is gone is not ready."""
    engine = build_engine(sqlite_settings().database)
    run_migrations(engine)
    build_repositories(engine).table_maintenance_policies.delete(DEFAULT_POLICY_ID)

    assert schema_is_ready(engine) is False


def test_an_unreachable_database_is_not_ready():
    """A database that cannot be reached yet is not ready; the wait goes on rather than failing."""
    assert schema_is_ready(create_engine("postgresql+psycopg://u:p@127.0.0.1:1/db")) is False
