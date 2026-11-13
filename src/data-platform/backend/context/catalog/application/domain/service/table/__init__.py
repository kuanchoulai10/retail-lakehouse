"""Table domain services: resolving a table's properties against their defaults and planning a reset."""

from __future__ import annotations

from context.catalog.application.domain.service.table.plan_table_property_reset import (
    plan_table_property_reset,
)
from context.catalog.application.domain.service.table.resolve_table_properties import (
    resolve_table_properties,
)

__all__ = [
    "plan_table_property_reset",
    "resolve_table_properties",
]
