"""Provide the create_schema function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from adapter.outbound.discovery.sql.discovery_settings_table import (
    discovery_settings_table as _discovery_settings_table,
)
from adapter.outbound.discovery_rule.sql.discovery_rules_table import (
    discovery_rules_table as _discovery_rules_table,
)
from adapter.outbound.maintenance_run.sql.maintenance_runs_table import (
    maintenance_runs_table as _maintenance_runs_table,
)
from adapter.outbound.managed_table.sql.managed_tables_table import (
    managed_tables_table as _managed_tables_table,
)
from adapter.outbound.policy_template.sql.policy_templates_table import (
    policy_templates_table as _policy_templates_table,
)
from adapter.outbound.sql.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy import Engine

_REGISTERED = (
    _discovery_settings_table,
    _discovery_rules_table,
    _maintenance_runs_table,
    _managed_tables_table,
    _policy_templates_table,
)


def create_schema(engine: Engine) -> None:
    """Create every control-plane table that does not exist yet."""
    metadata.create_all(engine)
