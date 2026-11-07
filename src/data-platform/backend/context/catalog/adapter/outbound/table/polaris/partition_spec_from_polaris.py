"""Define the partition_spec_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.application.port.outbound.table import PartitionField, PartitionSpec

if TYPE_CHECKING:
    from collections.abc import Mapping


def partition_spec_from_polaris(metadata: Mapping[str, Any]) -> PartitionSpec:
    """Map the default partition spec of Iceberg table metadata: ``partition-specs`` at ``default-spec-id``."""
    default_id = metadata.get("default-spec-id", 0)
    spec = next((s for s in metadata.get("partition-specs") or [] if s.get("spec-id") == default_id), None)
    if spec is None:
        return PartitionSpec.unpartitioned()
    return PartitionSpec(
        spec_id=int(spec["spec-id"]),
        fields=tuple(
            PartitionField(
                source_id=int(field["source-id"]),
                field_id=int(field["field-id"]),
                name=str(field["name"]),
                transform=str(field["transform"]),
            )
            for field in spec.get("fields", [])
        ),
    )
