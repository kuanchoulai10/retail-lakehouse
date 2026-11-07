"""Define the Table aggregate root."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from base import AggregateRoot
from context.catalog.application.domain.model.table.sort_order import SortOrder
from context.catalog.application.domain.model.table.table_id import TableId
from context.catalog.application.domain.model.table.table_summary import TableSummary

if TYPE_CHECKING:
    from context.catalog.application.domain.model.shared import Schema
    from context.catalog.application.domain.model.table.partition_spec import PartitionSpec
    from context.catalog.application.domain.model.table.snapshot import Snapshot


@dataclass(eq=False)
class Table(AggregateRoot[TableId]):
    """An Iceberg table as the catalog holds it: uuid, current schema, default spec and order, snapshots, properties.

    The catalog assigns ``uuid``, ``format_version`` and ``last_updated_ms`` and, unless one is
    asked for, ``location`` when it saves the table. A table defined for create (``define``)
    has them as None; every table loaded from the catalog has them.
    """

    id: TableId
    uuid: str | None
    format_version: int | None
    location: str | None
    current_snapshot_id: int | None
    last_updated_ms: int | None
    schema: Schema
    partition_spec: PartitionSpec
    sort_order: SortOrder
    snapshots: list[Snapshot] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)

    @classmethod
    def define(
        cls,
        id: TableId,  # noqa: A002
        schema: Schema,
        partition_spec: PartitionSpec,
        location: str | None,
        properties: dict[str, str],
    ) -> Table:
        """Return a new, unsorted table with no snapshots, for the catalog to create."""
        return cls(
            id=id,
            uuid=None,
            format_version=None,
            location=location,
            current_snapshot_id=None,
            last_updated_ms=None,
            schema=schema,
            partition_spec=partition_spec,
            sort_order=SortOrder.unsorted(),
            snapshots=[],
            properties=dict(properties),
        )

    @property
    def current_snapshot(self) -> Snapshot | None:
        """Return the current snapshot, or None when the table has none."""
        return next((s for s in self.snapshots if s.snapshot_id == self.current_snapshot_id), None)

    @property
    def summary(self) -> TableSummary:
        """Return the record, file and size totals of the current snapshot."""
        return TableSummary.of(self.current_snapshot)
