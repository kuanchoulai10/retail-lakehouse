"""Test the startup migration that seeds the default maintenance preset."""

from __future__ import annotations

from bootstrap.container import (
    build_engine,
    build_repositories,
    build_use_cases,
    run_migrations,
)
from context.table_maintenance.adapter.outbound.shared.sql import create_schema
from context.table_maintenance.application.domain.model.shared import (
    MaintenanceSettings,
)
from context.table_maintenance.application.port.inbound.table_discovery_rule import (
    ListTableDiscoveryRulesUseCaseInput,
)
from context.table_maintenance.application.port.inbound.table_maintenance_preset import (
    CreateTableMaintenancePresetUseCaseInput,
    ListTableMaintenancePresetsUseCaseInput,
)
from context.table_maintenance.application.service.shared import (
    maintenance_settings_to_dict,
)
from tests.bootstrap.container.container_support import (
    NOW,
    fake_gateways,
    sqlite_settings,
)


def _use_cases(engine):
    return build_use_cases(build_repositories(engine), fake_gateways(), clock=lambda: NOW)


def test_migrate_seeds_default_preset_once():
    """Migrating creates the default preset with default settings and no discovery rules."""
    engine = build_engine(sqlite_settings())

    run_migrations(engine)
    run_migrations(engine)

    use_cases = _use_cases(engine)
    presets = use_cases.list_table_maintenance_presets.execute(ListTableMaintenancePresetsUseCaseInput()).items
    rules = use_cases.list_table_discovery_rules.execute(ListTableDiscoveryRulesUseCaseInput())
    assert [t.name for t in presets] == ["default"]
    assert presets[0].settings == maintenance_settings_to_dict(MaintenanceSettings())
    assert rules.items == []


def test_migrate_does_not_seed_when_a_preset_exists():
    """Migrating leaves the presets alone when one already exists."""
    engine = build_engine(sqlite_settings())
    create_schema(engine)
    _use_cases(engine).create_table_maintenance_preset.execute(CreateTableMaintenancePresetUseCaseInput(name="nightly"))

    run_migrations(engine)

    presets = _use_cases(engine).list_table_maintenance_presets.execute(ListTableMaintenancePresetsUseCaseInput()).items
    assert [t.name for t in presets] == ["nightly"]
