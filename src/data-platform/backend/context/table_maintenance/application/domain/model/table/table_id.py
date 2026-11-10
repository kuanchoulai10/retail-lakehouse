"""Define the TableId identifier."""

from __future__ import annotations

from base import EntityId


class TableId(EntityId):
    """Identify a table by its Iceberg table-uuid."""
