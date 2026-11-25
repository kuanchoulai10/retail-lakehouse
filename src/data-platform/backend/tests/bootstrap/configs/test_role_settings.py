"""Test that each role's settings class holds only its blocks and that every block refuses unknown keys."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bootstrap import configs
from bootstrap.configs import (
    ApiSettings,
    EventConsumerSettings,
    MaintenanceSettings,
    MigrateSettings,
    ServiceSettings,
    SettingsBlock,
    WorkerSettings,
)


def test_each_role_holds_only_its_blocks():
    """A role reads only the settings it needs."""
    assert set(MigrateSettings.model_fields) == {"log_level", "database"}
    assert set(EventConsumerSettings.model_fields) == {"log_level", "database", "temporal", "catalog", "kafka"}
    assert set(ServiceSettings.model_fields) == {
        "log_level",
        "database",
        "temporal",
        "catalog",
        "spark",
        "maintenance",
        "discovery",
        "metrics",
    }
    assert set(ApiSettings.model_fields) - set(ServiceSettings.model_fields) == {"http"}
    assert set(WorkerSettings.model_fields) - set(ServiceSettings.model_fields) == {"callback_base_url"}


BLOCKS = sorted(
    (value for value in vars(configs).values() if isinstance(value, type) and issubclass(value, SettingsBlock)),
    key=lambda block: block.__name__,
)


@pytest.mark.parametrize("block", BLOCKS, ids=lambda block: block.__name__)
def test_every_block_refuses_unknown_keys(block: type[SettingsBlock]):
    """A misspelt key in any block fails, not only at the top level."""
    assert block.model_config.get("extra") == "forbid"


def test_there_are_blocks_to_check():
    """The parametrized check above runs over the real blocks."""
    assert {block.__name__ for block in BLOCKS} >= {
        "CatalogSettings",
        "DatabaseSettings",
        "DiscoverySettings",
        "HttpSettings",
        "KafkaSettings",
        "MaintenanceSettings",
        "MetricsSettings",
        "PostgresSettings",
        "SparkSettings",
        "SparkSizeSettings",
        "SparkVolcanoSettings",
        "SqliteSettings",
        "TemporalSettings",
    }


def test_maintenance_keeps_the_defaults_and_bounds():
    """The maintenance block keeps the defaults and bounds the flat fields had."""
    assert MaintenanceSettings().max_attempts == 3
    assert MaintenanceSettings().compaction_partitions_per_job == 10
    with pytest.raises(ValidationError):
        MaintenanceSettings(max_attempts=0)
    with pytest.raises(ValidationError):
        MaintenanceSettings(compaction_partitions_per_job=1001)
