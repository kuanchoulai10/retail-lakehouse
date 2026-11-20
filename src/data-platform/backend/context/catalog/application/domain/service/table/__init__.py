"""Table domain services: comparing schemas and partition specs, resolving properties, planning a reset."""

from __future__ import annotations

from context.catalog.application.domain.service.table.compare_partition_specs import compare_partition_specs
from context.catalog.application.domain.service.table.compare_schemas import compare_schemas
from context.catalog.application.domain.service.table.plan_table_property_reset import (
    plan_table_property_reset,
)
from context.catalog.application.domain.service.table.resolve_table_properties import (
    resolve_table_properties,
)

__all__ = [
    "compare_partition_specs",
    "compare_schemas",
    "plan_table_property_reset",
    "resolve_table_properties",
]
