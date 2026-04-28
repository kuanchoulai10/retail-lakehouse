"""Define the Table aggregate root."""

from __future__ import annotations

from dataclasses import dataclass

from base.aggregate_root import AggregateRoot
from application.domain.model.catalog.branch import Branch
from application.domain.model.catalog.snapshot import Snapshot
from application.domain.model.catalog.table_id import TableId
from application.domain.model.catalog.table_properties.table_properties import (
    TableProperties,
)
from application.domain.model.catalog.table_schema import TableSchema
from application.domain.model.catalog.tag import Tag


@dataclass(eq=False)
class Table(AggregateRoot[TableId]):
    """The Table aggregate root — Iceberg table metadata (analogous to a Git repository)."""

    id: TableId
    namespace: str
    name: str
    location: str
    current_snapshot_id: int | None
    schema: TableSchema
    snapshots: tuple[Snapshot, ...]
    branches: tuple[Branch, ...]
    tags: tuple[Tag, ...]
    properties: TableProperties
