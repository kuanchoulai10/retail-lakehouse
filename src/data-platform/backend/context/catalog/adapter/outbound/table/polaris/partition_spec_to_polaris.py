"""Define the partition_spec_to_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from context.catalog.application.port.outbound.table import PartitionSpec


def partition_spec_to_polaris(spec: PartitionSpec) -> dict[str, Any]:
    """Map a partition spec to its Iceberg REST body."""
    return {
        "spec-id": spec.spec_id,
        "fields": [
            {"source-id": f.source_id, "field-id": f.field_id, "name": f.name, "transform": f.transform}
            for f in spec.fields
        ],
    }
