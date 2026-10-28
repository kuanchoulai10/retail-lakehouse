"""Provide the create_schema function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.table_discovery_settings.sql.table_discovery_settings_table import (
    table_discovery_settings_table as _table_discovery_settings_table,
)
from adapter.outbound.table_discovery_rule.sql.table_discovery_rules_table import (
    table_discovery_rules_table as _table_discovery_rules_table,
)
from adapter.outbound.table_maintenance_run.sql.table_maintenance_runs_table import (
    table_maintenance_runs_table as _table_maintenance_runs_table,
)
from adapter.outbound.table.sql.tables_table import (
    tables_table as _tables_table,
)
from adapter.outbound.table_maintenance_preset.sql.table_maintenance_presets_table import (
    table_maintenance_presets_table as _table_maintenance_presets_table,
)
from adapter.outbound.shared.sql.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy import Engine

_REGISTERED = (
    _table_discovery_settings_table,
    _table_discovery_rules_table,
    _table_maintenance_runs_table,
    _tables_table,
    _table_maintenance_presets_table,
)


def create_schema(engine: Engine) -> None:
    """Create every control-plane table that does not exist yet."""
    metadata.create_all(engine)
