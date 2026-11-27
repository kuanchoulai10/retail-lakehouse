"""Test the startup migration that seeds the default maintenance policy, and no discovery policy."""

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
    engine = build_engine(sqlite_settings().database)

    run_migrations(engine)

    assert "table_maintenance_presets" not in inspect(engine).get_table_names()


def test_run_migrations_seeds_default_policy():
    """Migrating creates the default policy once, at version 1."""
    engine = build_engine(sqlite_settings().database)

    run_migrations(engine)
    run_migrations(engine)

    use_cases = _use_cases(engine)
    items = use_cases.list_table_maintenance_policies.execute(ListTableMaintenancePoliciesUseCaseInput()).items
    assert [(p.name, p.version) for p in items] == [("default", 1)]
    assert items[0].content == MaintenancePolicyContent.platform_default().to_primitives()


def test_run_migrations_seeds_the_default_policy_under_its_fixed_id():
    """The seeded default policy has the fixed id ``mp-00000000000000000000000000``."""
    engine = build_engine(sqlite_settings().database)

    run_migrations(engine)

    items = _use_cases(engine).list_table_maintenance_policies.execute(ListTableMaintenancePoliciesUseCaseInput()).items
    assert [(p.id, p.name) for p in items] == [("mp-00000000000000000000000000", "default")]


def test_migrate_seeds_no_discovery_policy():
    """Migrating twice leaves no discovery policy: there is no discovery default."""
    engine = build_engine(sqlite_settings().database)

    run_migrations(engine)
    run_migrations(engine)

    assert build_repositories(engine).table_discovery_policies.list_all() == []


def test_migrate_again_keeps_the_schema_and_the_default():
    """A second migrate of a migrated database changes nothing: every table and the default stay as they were."""
    engine = build_engine(sqlite_settings().database)
    run_migrations(engine)
    tables = set(inspect(engine).get_table_names())

    run_migrations(engine)

    assert set(inspect(engine).get_table_names()) == tables
    items = _use_cases(engine).list_table_maintenance_policies.execute(ListTableMaintenancePoliciesUseCaseInput()).items
    assert [(p.name, p.version) for p in items] == [("default", 1)]


def test_migrate_logs_what_happened_to_the_default(caplog: pytest.LogCaptureFixture):
    """The log says whether the default maintenance policy was created or kept."""
    engine = build_engine(sqlite_settings().database)

    with caplog.at_level(logging.INFO, logger="bootstrap.container.run_migrations"):
        run_migrations(engine)
        run_migrations(engine)

    assert [r.getMessage() for r in caplog.records if r.name == "bootstrap.container.run_migrations"] == [
        "schema ready; default maintenance policy created",
        "schema ready; default maintenance policy kept",
    ]
