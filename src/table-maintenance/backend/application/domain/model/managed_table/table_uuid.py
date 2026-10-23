"""Define the TableUuid identifier."""

from __future__ import annotations

from dataclasses import dataclass

from base.entity_id import EntityId


@dataclass(frozen=True)
class TableUuid(EntityId):
    """Identify a managed table by its Iceberg table-uuid."""
