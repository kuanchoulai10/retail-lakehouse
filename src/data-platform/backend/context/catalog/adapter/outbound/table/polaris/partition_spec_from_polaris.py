"""Define the partition_spec_from_polaris function."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from context.catalog.adapter.outbound.shared.polaris import polaris_integer, polaris_text
from context.catalog.application.port.outbound.table import PartitionField, PartitionSpec

if TYPE_CHECKING:
    from collections.abc import Mapping


def _field(field: Mapping[str, Any]) -> PartitionField:
    return PartitionField(
        source_id=polaris_integer(field["source-id"], "partition field source-id"),
        field_id=polaris_integer(field["field-id"], "partition field field-id"),
        name=polaris_text(field["name"], "partition field name"),
        transform=polaris_text(field["transform"], "partition field transform"),
    )


def _fields(fields: Any) -> tuple[PartitionField, ...]:  # noqa: ANN401
    if not isinstance(fields, list):
        raise TypeError(f"partition fields must be a list, not {fields!r}")
    return tuple(_field(field) for field in fields)


def partition_spec_from_polaris(metadata: Mapping[str, Any]) -> PartitionSpec:
    """Map the default partition spec of Iceberg table metadata: ``partition-specs`` at ``default-spec-id``.

    Without ``default-spec-id`` (format v1) the single ``partition-spec`` field list is spec 0,
    and with neither (or a null one) the table is unpartitioned. A default id that matches no
    spec raises ValueError instead of yielding an unpartitioned spec; an id that is not an
    integer, or a name or transform that is not text, raises TypeError.
    """
    if "default-spec-id" not in metadata:
        v1_fields = metadata.get("partition-spec")
        return PartitionSpec(spec_id=0, fields=() if v1_fields is None else _fields(v1_fields))
    default_id = polaris_integer(metadata["default-spec-id"], "default-spec-id")
    for spec in metadata["partition-specs"]:
        if polaris_integer(spec["spec-id"], "spec-id") == default_id:
            return PartitionSpec(spec_id=default_id, fields=_fields(spec["fields"]))
    raise ValueError(f"default-spec-id {default_id} matches no partition spec")
