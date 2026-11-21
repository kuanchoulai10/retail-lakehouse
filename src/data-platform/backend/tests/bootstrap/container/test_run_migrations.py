"""Test the startup migration that seeds the default maintenance and discovery policies."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import inspect, text

from bootstrap.container import (
    build_engine,
    build_repositories,
    build_use_cases,
    run_migrations,
)
from context.table_maintenance.application.domain.model.table_maintenance_policy import (
    MaintenancePolicyContent,
)
from context.table_maintenance.application.port.inbound.table_maintenance_policy import (
    ListTableMaintenancePoliciesUseCaseInput,
)
from context.table_maintenance.application.port.outbound.table_discovery_policy import (
    DEFAULT_DISCOVERY_POLICY_ID,
    DiscoveryPolicyContent,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    platform_settings,
    sqlite_settings,
)

if TYPE_CHECKING:
    import pytest


def _use_cases(engine):
    return build_use_cases(
        build_repositories(engine), fake_gateways(), platform_settings=platform_settings(), clock=lambda: NOW
    )


def test_schema_has_no_preset_table():
    """Migrating creates no table for the removed presets."""
    engine = build_engine(sqlite_settings())

    run_migrations(engine)

    assert "table_maintenance_presets" not in inspect(engine).get_table_names()


def test_run_migrations_seeds_default_policy():
    """Migrating creates the default policy once, at version 1."""
    engine = build_engine(sqlite_settings())

    run_migrations(engine)
    run_migrations(engine)

    use_cases = _use_cases(engine)
    items = use_cases.list_table_maintenance_policies.execute(ListTableMaintenancePoliciesUseCaseInput()).items
    assert [(p.name, p.version) for p in items] == [("default", 1)]
    assert items[0].content == MaintenancePolicyContent.platform_default().to_primitives()


def test_run_migrations_seeds_the_default_policy_under_its_fixed_id():
    """The seeded default policy has the fixed id ``mp-00000000000000000000000000``."""
    engine = build_engine(sqlite_settings())

    run_migrations(engine)

    items = _use_cases(engine).list_table_maintenance_policies.execute(ListTableMaintenancePoliciesUseCaseInput()).items
    assert [(p.id, p.name) for p in items] == [("mp-00000000000000000000000000", "default")]


def test_migrate_seeds_the_default_discovery_policy():
    """Migrating twice leaves one discovery policy: the default, at version 1 with the platform content."""
    engine = build_engine(sqlite_settings())

    run_migrations(engine)
    run_migrations(engine)

    policies = build_repositories(engine).table_discovery_policies
    default = policies.get(DEFAULT_DISCOVERY_POLICY_ID)
    assert default is not None
    assert default.is_default
    assert (default.name.value, default.version) == ("default", 1)
    assert default.content == DiscoveryPolicyContent.platform_default()
    assert [p.id for p in policies.list_all()] == [DEFAULT_DISCOVERY_POLICY_ID]
    assert policies.get_version(DEFAULT_DISCOVERY_POLICY_ID, 1) is not None


def test_migrate_adds_the_discovery_policy_tables_to_an_older_database():
    """A database migrated before discovery policies existed gets their tables and the default on the next migrate."""
    engine = build_engine(sqlite_settings())
    run_migrations(engine)
    with engine.begin() as connection:
        for table in (
            "table_discovery_policy_attachments",
            "table_discovery_policy_versions",
            "table_discovery_policies",
        ):
            connection.execute(text(f"DROP TABLE {table}"))

    run_migrations(engine)

    assert build_repositories(engine).table_discovery_policies.get(DEFAULT_DISCOVERY_POLICY_ID) is not None
    assert "table_discovery_policy_attachments" in inspect(engine).get_table_names()


def test_migrate_logs_what_happened_to_both_defaults(caplog: pytest.LogCaptureFixture):
    """The log says whether each default policy was created or kept."""
    engine = build_engine(sqlite_settings())

    with caplog.at_level(logging.INFO, logger="bootstrap.container.run_migrations"):
        run_migrations(engine)
        run_migrations(engine)

    assert [r.getMessage() for r in caplog.records if r.name == "bootstrap.container.run_migrations"] == [
        "schema ready; default maintenance policy created; default discovery policy created",
        "schema ready; default maintenance policy kept; default discovery policy kept",
    ]
