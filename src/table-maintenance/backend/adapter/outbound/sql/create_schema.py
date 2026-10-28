"""Provide the create_schema function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.discovery.sql.discovery_settings_table import (
    discovery_settings_table as _discovery_settings_table,
)
from adapter.outbound.discovery_rule.sql.discovery_rules_table import (
    discovery_rules_table as _discovery_rules_table,
)
from adapter.outbound.maintenance_run.sql.add_maintenance_run_workflow_id_column import (
    add_maintenance_run_workflow_id_column,
)
from adapter.outbound.maintenance_run.sql.maintenance_runs_table import (
    maintenance_runs_table as _maintenance_runs_table,
)
from adapter.outbound.table.sql.tables_table import (
    tables_table as _tables_table,
)
from adapter.outbound.table_maintenance_preset.sql.table_maintenance_presets_table import (
    table_maintenance_presets_table as _table_maintenance_presets_table,
)
from adapter.outbound.sql.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy import Engine

_REGISTERED = (
    _discovery_settings_table,
    _discovery_rules_table,
    _maintenance_runs_table,
    _tables_table,
    _table_maintenance_presets_table,
)


def create_schema(engine: Engine) -> None:
    """Create every control-plane table that does not exist yet, then upgrade.

    ``create_all`` only adds missing tables; each upgrade adds what an older
    table lacks and is idempotent.
    """
    metadata.create_all(engine)
    add_maintenance_run_workflow_id_column(engine)
