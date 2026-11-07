"""Define the partition_spec_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.port.outbound.table import PartitionField, PartitionSpec

if TYPE_CHECKING:
    from collections.abc import Mapping


def _field(field: Mapping[str, Any]) -> PartitionField:
    return PartitionField(
        source_id=int(field["source-id"]),
        field_id=int(field["field-id"]),
        name=str(field["name"]),
        transform=str(field["transform"]),
    )


def partition_spec_from_polaris(metadata: Mapping[str, Any]) -> PartitionSpec:
    """Map the default partition spec of Iceberg table metadata: ``partition-specs`` at ``default-spec-id``.

    Without ``default-spec-id`` (format v1) the single ``partition-spec`` field list is spec 0,
    and with neither the table is unpartitioned. A default id that matches no spec raises
    ValueError instead of yielding an unpartitioned spec.
    """
    if "default-spec-id" not in metadata:
        return PartitionSpec(spec_id=0, fields=tuple(_field(f) for f in metadata.get("partition-spec") or []))
    default_id = metadata["default-spec-id"]
    for spec in metadata["partition-specs"]:
        if spec["spec-id"] == default_id:
            return PartitionSpec(spec_id=int(default_id), fields=tuple(_field(f) for f in spec["fields"]))
    raise ValueError(f"default-spec-id {default_id} matches no partition spec")
