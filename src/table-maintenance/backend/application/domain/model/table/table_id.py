"""Define the TableId identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class TableId(EntityId):
    """Identify a table by its Iceberg table-uuid."""
