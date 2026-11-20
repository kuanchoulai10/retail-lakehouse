"""Test reading an Iceberg REST partition transform string into a typed PartitionTransform."""

from __future__ import annotations

import pytest

from context.catalog.adapter.outbound.table.polaris import partition_transform_from_polaris
from context.catalog.application.port.outbound.table import PartitionTransform, PartitionTransformKind


@pytest.mark.parametrize(
    ("text", "kind", "argument"),
    [
        ("identity", PartitionTransformKind.IDENTITY, None),
        ("year", PartitionTransformKind.YEAR, None),
        ("month", PartitionTransformKind.MONTH, None),
        ("day", PartitionTransformKind.DAY, None),
        ("hour", PartitionTransformKind.HOUR, None),
        ("void", PartitionTransformKind.VOID, None),
        ("bucket[16]", PartitionTransformKind.BUCKET, 16),
        ("truncate[4]", PartitionTransformKind.TRUNCATE, 4),
    ],
)
def test_known_transforms_read_as_their_kind_and_number(text: str, kind: PartitionTransformKind, argument: int | None):
    """Each Iceberg transform reads as its kind, bucket and truncate with their number, and writes back the same."""
    transform = partition_transform_from_polaris(text)
    assert transform == PartitionTransform(kind=kind, argument=argument)
    assert transform.text() == text


@pytest.mark.parametrize("text", ["zorder", "bucket", "bucket[0]", "bucket[x]", "truncate[04]", "Day", "day[1]"])
def test_any_other_text_is_unknown_and_kept(text: str):
    """A transform this backend does not know is unknown, keeps its text, and writes it back unchanged."""
    transform = partition_transform_from_polaris(text)
    assert transform == PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw=text)
    assert transform.text() == text
