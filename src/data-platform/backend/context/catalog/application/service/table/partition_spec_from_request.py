"""Define the partition_spec_from_request function."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.outbound.table import PartitionField, PartitionSpec

if TYPE_CHECKING:
    from context.catalog.application.port.inbound.table import CreateTableUseCaseInputPartitionField
    from context.catalog.application.port.outbound.table import TableSchema

_FIRST_PARTITION_FIELD_ID = 1000
_TRANSFORM = re.compile(r"^(identity|year|month|day|hour|void|bucket\[[1-9]\d*\]|truncate\[[1-9]\d*\])$")
_NAME_SUFFIX = {"bucket": "bucket", "truncate": "trunc"}


def _field_name(source: str, transform: str) -> str:
    """Name a partition field the way Iceberg does by default: ``id``, ``ts_day``, ``id_bucket``, ``s_trunc``."""
    if transform == "identity":
        return source
    base = transform.split("[", 1)[0]
    return f"{source}_{_NAME_SUFFIX.get(base, base)}"


def partition_spec_from_request(
    schema: TableSchema, partition_fields: list[CreateTableUseCaseInputPartitionField]
) -> PartitionSpec:
    """Build spec 0 from the form's partition fields, or raise ValidationError.

    Each field reads a top-level column of ``schema`` by name and gets field id 1000, 1001, ...
    """
    fields = []
    for index, requested in enumerate(partition_fields):
        source = schema.field_named(requested.source_column)
        if source is None:
            raise ValidationError(f"partition source column {requested.source_column!r} is not a schema field")
        if not _TRANSFORM.match(requested.transform):
            raise ValidationError(
                f"partition transform {requested.transform!r} is not one of identity, year, month, day, hour, "
                "void, bucket[N] or truncate[W]"
            )
        fields.append(
            PartitionField(
                source_id=source.id,
                field_id=_FIRST_PARTITION_FIELD_ID + index,
                name=_field_name(source.name, requested.transform),
                transform=requested.transform,
            )
        )
    return PartitionSpec(spec_id=0, fields=tuple(fields))
