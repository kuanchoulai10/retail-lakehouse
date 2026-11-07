"""Map a PyIceberg table to the primitive TableMetadataObservation."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from adapter.outbound.table.pyiceberg.partition_value_to_primitive import (
    partition_value_to_primitive,
)
from application.port.outbound.table import TableMetadataObservation
from pyiceberg.manifest import DataFileContent

if TYPE_CHECKING:
    from pyiceberg.manifest import ManifestFile
    from pyiceberg.partitioning import PartitionSpec
    from pyiceberg.schema import Schema
    from pyiceberg.table import Table
    from pyiceberg.types import IcebergType


def observation_from_table(table: Table) -> TableMetadataObservation:
    """Build the observation of a table's current snapshot."""
    metadata = table.metadata
    snapshot = table.current_snapshot()
    manifests: list[dict[str, Any]] = []
    partitions: list[dict[str, Any]] = []
    if snapshot is not None:
        manifest_files = snapshot.manifests(table.io)
        manifests = [{"length_bytes": m.manifest_length} for m in manifest_files]
        partitions = _partition_stats(table, manifest_files)
    return TableMetadataObservation(
        table_uuid=str(metadata.table_uuid),
        properties=dict(metadata.properties),
        current_snapshot_id=snapshot.snapshot_id if snapshot else None,
        specs=[spec_of(table, spec) for spec in metadata.partition_specs],
        partitions=partitions,
        manifests=manifests,
        snapshots=[
            {
                "snapshot_id": s.snapshot_id,
                "committed_at": datetime.fromtimestamp(
                    s.timestamp_ms / 1000, tz=UTC
                ).isoformat(),
            }
            for s in metadata.snapshots
        ],
    )


def spec_of(table: Table, spec: PartitionSpec) -> dict[str, Any]:
    return {
        "spec_id": spec.spec_id,
        "fields": [
            {
                "field_id": f.field_id,
                "name": f.name,
                "source_column": _source_column(table, f.source_id),
                "source_type": str(_source_field_type(table, f.source_id)),
                "transform": str(f.transform),
            }
            for f in spec.fields
        ],
    }


def _schemas(table: Table) -> list[Schema]:
    current = table.schema()
    others = [s for s in table.metadata.schemas if s.schema_id != current.schema_id]
    return [current, *reversed(others)]


def _source_column(table: Table, source_id: int) -> str:
    for schema in _schemas(table):
        name = schema.find_column_name(source_id)
        if name is not None:
            return name
    raise ValueError(f"Partition source field {source_id} not found in any schema")


def _source_field_type(table: Table, source_id: int) -> IcebergType:
    for schema in _schemas(table):
        if schema.find_column_name(source_id) is not None:
            return schema.find_type(source_id)
    raise ValueError(f"Partition source field {source_id} not found in any schema")


def _partition_stats(
    table: Table, manifest_files: list[ManifestFile]
) -> list[dict[str, Any]]:
    files: Counter[tuple[int, tuple[Any, ...], str]] = Counter()
    sizes: Counter[tuple[int, tuple[Any, ...]]] = Counter()
    seen: set[tuple[int, tuple[Any, ...]]] = set()
    for manifest in manifest_files:
        for entry in manifest.fetch_manifest_entry(table.io, discard_deleted=True):
            data_file = entry.data_file
            key = (
                data_file.spec_id,
                tuple(partition_value_to_primitive(v) for v in data_file.partition),
            )
            seen.add(key)
            content = data_file.content
            files[(*key, content.name)] += 1
            if content == DataFileContent.DATA:
                sizes[key] += data_file.file_size_in_bytes
    return [
        {
            "spec_id": spec_id,
            "values": list(values),
            "data_file_count": files[(spec_id, values, DataFileContent.DATA.name)],
            "position_delete_file_count": files[
                (spec_id, values, DataFileContent.POSITION_DELETES.name)
            ],
            "equality_delete_file_count": files[
                (spec_id, values, DataFileContent.EQUALITY_DELETES.name)
            ],
            "total_data_file_size_bytes": sizes[(spec_id, values)],
        }
        for spec_id, values in sorted(seen, key=lambda k: (k[0], repr(k[1])))
    ]
