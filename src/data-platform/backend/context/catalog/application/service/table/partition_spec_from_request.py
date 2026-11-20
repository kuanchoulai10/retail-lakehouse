"""Define the partition_spec_from_request function."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from context.catalog.application.exceptions import ValidationError
from context.catalog.application.port.outbound.table import (
    PartitionField,
    PartitionSpec,
    PartitionTransform,
    PartitionTransformKind,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from context.catalog.application.port.inbound.table import CreateTableUseCaseInput
    from context.catalog.application.port.outbound.table import Schema

_FIRST_PARTITION_FIELD_ID = 1000
_TRANSFORM = re.compile(r"^(?:(identity|year|month|day|hour|void)|(bucket|truncate)\[([1-9]\d*)\])$")
_NAME_SUFFIX = {PartitionTransformKind.BUCKET: "bucket", PartitionTransformKind.TRUNCATE: "trunc"}


def _transform(text: str) -> PartitionTransform:
    """Read the form's transform, or raise ValidationError for one that is not an Iceberg partition transform."""
    matched = _TRANSFORM.match(text)
    if matched is None:
        raise ValidationError(
            f"partition transform {text!r} is not one of identity, year, month, day, hour, "
            "void, bucket[N] or truncate[W]"
        )
    plain, numbered, argument = matched.groups()
    if plain is not None:
        return PartitionTransform(kind=PartitionTransformKind(plain))
    return PartitionTransform(kind=PartitionTransformKind(numbered), argument=int(argument))


def _field_name(source: str, transform: PartitionTransform) -> str:
    """Name a partition field the way Iceberg does by default: ``id``, ``ts_day``, ``id_bucket``, ``s_trunc``."""
    if transform.kind is PartitionTransformKind.IDENTITY:
        return source
    return f"{source}_{_NAME_SUFFIX.get(transform.kind, transform.kind)}"


def partition_spec_from_request(
    schema: Schema, partition_fields: Sequence[CreateTableUseCaseInput.PartitionField]
) -> PartitionSpec:
    """Build spec 0 from the form's partition fields, or raise ValidationError.

    Each field reads a top-level column of ``schema`` by name and gets field id 1000, 1001, ...
    """
    fields = []
    for index, requested in enumerate(partition_fields):
        source = schema.field_named(requested.source_column)
        if source is None:
            raise ValidationError(f"partition source column {requested.source_column!r} is not a schema field")
        transform = _transform(requested.transform)
        fields.append(
            PartitionField(
                source_id=source.id,
                field_id=_FIRST_PARTITION_FIELD_ID + index,
                name=_field_name(source.name, transform),
                transform=transform,
            )
        )
    return PartitionSpec(spec_id=0, fields=tuple(fields))
