"""Test the startup migration that seeds the default maintenance policy."""

from __future__ import annotations

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
