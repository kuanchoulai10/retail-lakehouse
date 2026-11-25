"""Test that the schema counts as ready only once the migrations have created it and seeded both defaults."""

from __future__ import annotations

from sqlalchemy import create_engine

from bootstrap.container import build_engine, build_repositories, run_migrations, schema_is_ready
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.domain.model.table_discovery_policy import DEFAULT_DISCOVERY_POLICY_ID
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


def test_tables_without_the_seeds_are_not_ready():
    """The tables alone are not enough: the services need both default policies."""
    engine = build_engine(sqlite_settings().database)
    create_schema(engine)

    assert schema_is_ready(engine) is False


def test_the_discovery_default_alone_is_not_ready():
    """Both defaults must exist, not only one of them."""
    engine = build_engine(sqlite_settings().database)
    run_migrations(engine)
    repositories = build_repositories(engine)
    repositories.table_maintenance_policies.delete(DEFAULT_POLICY_ID)

    assert repositories.table_discovery_policies.get(DEFAULT_DISCOVERY_POLICY_ID) is not None
    assert schema_is_ready(engine) is False


def test_an_unreachable_database_is_not_ready():
    """A database that cannot be reached yet is not ready; the wait goes on rather than failing."""
    assert schema_is_ready(create_engine("postgresql+psycopg://u:p@127.0.0.1:1/db")) is False


def test_the_maintenance_default_alone_is_not_ready():
    """Without the default discovery policy the schema is not ready either."""
    engine = build_engine(sqlite_settings().database)
    run_migrations(engine)
    repositories = build_repositories(engine)
    repositories.table_discovery_policies.delete(DEFAULT_DISCOVERY_POLICY_ID)

    assert repositories.table_maintenance_policies.get(DEFAULT_POLICY_ID) is not None
    assert schema_is_ready(engine) is False
