"""Test the startup migration that seeds the default maintenance and discovery policies."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import inspect

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


def test_migrate_again_keeps_the_schema_and_the_defaults():
    """A second migrate of a migrated database changes nothing: every table and both defaults stay as they were."""
    engine = build_engine(sqlite_settings())
    run_migrations(engine)
    tables = set(inspect(engine).get_table_names())

    run_migrations(engine)

    assert set(inspect(engine).get_table_names()) == tables
    repositories = build_repositories(engine)
    assert [p.id for p in repositories.table_discovery_policies.list_all()] == [DEFAULT_DISCOVERY_POLICY_ID]
    default = repositories.table_discovery_policies.get(DEFAULT_DISCOVERY_POLICY_ID)
    assert default is not None
    assert default.version == 1


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
