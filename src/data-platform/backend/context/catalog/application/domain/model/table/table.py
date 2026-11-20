"""Define the Table aggregate root."""

from __future__ import annotations

from pydantic import Field, model_validator

from base import AggregateRoot
from context.catalog.application.domain.model.shared import Schema
from context.catalog.application.domain.model.table.partition_spec import PartitionSpec
from context.catalog.application.domain.model.table.snapshot import Snapshot
from context.catalog.application.domain.model.table.sort_order import SortOrder
from context.catalog.application.domain.model.table.table_id import TableId
from context.catalog.application.domain.model.table.table_summary import TableSummary


class Table(AggregateRoot[TableId]):
    """An Iceberg table as the catalog holds it: uuid, every schema and partition spec, order, snapshots, properties.

    ``schemas`` and ``partition_specs`` hold every version in ascending id order, each id once.
    ``current_schema_id`` and ``default_spec_id`` name the current schema and the default spec,
    which need not be the highest id: Iceberg reuses an existing id when a change produces a
    schema or spec it already has. ``current_schema`` and ``default_partition_spec`` return them.

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
    schemas: tuple[Schema, ...]
    current_schema_id: int
    partition_specs: tuple[PartitionSpec, ...]
    default_spec_id: int
    sort_order: SortOrder
    snapshots: list[Snapshot] = Field(default_factory=list)
    properties: dict[str, str] = Field(default_factory=dict)

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
            schemas=(schema,),
            current_schema_id=schema.schema_id,
            partition_specs=(partition_spec,),
            default_spec_id=partition_spec.spec_id,
            sort_order=SortOrder.unsorted(),
            snapshots=[],
            properties=dict(properties),
        )

    @model_validator(mode="after")
    def _versions_are_ordered_and_current_ones_exist(self) -> Table:
        schema_ids = [schema.schema_id for schema in self.schemas]
        if schema_ids != sorted(set(schema_ids)):
            raise ValueError(f"schema ids must be unique and in ascending order, not {schema_ids}")
        spec_ids = [spec.spec_id for spec in self.partition_specs]
        if spec_ids != sorted(set(spec_ids)):
            raise ValueError(f"partition spec ids must be unique and in ascending order, not {spec_ids}")
        if self.current_schema_id not in schema_ids:
            raise ValueError(f"current_schema_id {self.current_schema_id} matches no schema")
        if self.default_spec_id not in spec_ids:
            raise ValueError(f"default_spec_id {self.default_spec_id} matches no partition spec")
        return self

    @property
    def current_schema(self) -> Schema:
        """Return the schema ``current_schema_id`` names."""
        return next(schema for schema in self.schemas if schema.schema_id == self.current_schema_id)

    @property
    def default_partition_spec(self) -> PartitionSpec:
        """Return the spec ``default_spec_id`` names."""
        return next(spec for spec in self.partition_specs if spec.spec_id == self.default_spec_id)

    def schema_by_id(self, schema_id: int) -> Schema | None:
        """Return the schema with this id, or None."""
        return next((schema for schema in self.schemas if schema.schema_id == schema_id), None)

    def previous_schema(self, schema_id: int) -> Schema | None:
        """Return the schema with the largest id below ``schema_id``, or None for the first one."""
        return next((schema for schema in reversed(self.schemas) if schema.schema_id < schema_id), None)

    def partition_spec_by_id(self, spec_id: int) -> PartitionSpec | None:
        """Return the partition spec with this id, or None."""
        return next((spec for spec in self.partition_specs if spec.spec_id == spec_id), None)

    def previous_partition_spec(self, spec_id: int) -> PartitionSpec | None:
        """Return the spec with the largest id below ``spec_id``, or None for the first one."""
        return next((spec for spec in reversed(self.partition_specs) if spec.spec_id < spec_id), None)

    def column_paths(self) -> dict[int, tuple[str, ...]]:
        """Return every field id of every schema with its path: the current schema's paths win, then higher ids."""
        paths: dict[int, tuple[str, ...]] = {}
        for schema in (*self.schemas, self.current_schema):
            paths.update({walked.field.id: walked.path for walked in schema.walk()})
        return paths

    @property
    def current_snapshot(self) -> Snapshot | None:
        """Return the current snapshot, or None when the table has none."""
        return next((s for s in self.snapshots if s.snapshot_id == self.current_snapshot_id), None)

    @property
    def summary(self) -> TableSummary:
        """Return the record, file and size totals of the current snapshot."""
        return TableSummary.of(self.current_snapshot)
