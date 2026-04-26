"""Define the TableId value object."""

from __future__ import annotations

from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class TableId(EntityId):
    """Typed identifier for a Table aggregate — '{namespace}.{table_name}'."""
