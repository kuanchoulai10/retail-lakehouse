"""Test the PartitionTransform value object: a typed transform with its Iceberg text form."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.catalog.application.domain.model.table import PartitionTransform, PartitionTransformKind


@pytest.mark.parametrize(
    ("transform", "text"),
    [
        (PartitionTransform(kind=PartitionTransformKind.IDENTITY), "identity"),
        (PartitionTransform(kind=PartitionTransformKind.YEAR), "year"),
        (PartitionTransform(kind=PartitionTransformKind.MONTH), "month"),
        (PartitionTransform(kind=PartitionTransformKind.DAY), "day"),
        (PartitionTransform(kind=PartitionTransformKind.HOUR), "hour"),
        (PartitionTransform(kind=PartitionTransformKind.VOID), "void"),
        (PartitionTransform(kind=PartitionTransformKind.BUCKET, argument=16), "bucket[16]"),
        (PartitionTransform(kind=PartitionTransformKind.TRUNCATE, argument=4), "truncate[4]"),
        (PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw="zorder[a,b]"), "zorder[a,b]"),
    ],
)
def test_text_is_the_iceberg_form(transform: PartitionTransform, text: str):
    """Each kind writes Iceberg's text form; an unknown transform writes the text it was read from."""
    assert transform.text() == text


def test_kinds_are_the_iceberg_transforms_and_unknown():
    """The kinds are Iceberg's partition transforms, plus one for a transform this backend does not know."""
    assert [kind.value for kind in PartitionTransformKind] == [
        "identity",
        "year",
        "month",
        "day",
        "hour",
        "bucket",
        "truncate",
        "void",
        "unknown",
    ]


@pytest.mark.parametrize(
    "build",
    [
        lambda: PartitionTransform(kind=PartitionTransformKind.BUCKET),
        lambda: PartitionTransform(kind=PartitionTransformKind.TRUNCATE, argument=0),
        lambda: PartitionTransform(kind=PartitionTransformKind.DAY, argument=1),
        lambda: PartitionTransform(kind=PartitionTransformKind.UNKNOWN),
        lambda: PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw=""),
        lambda: PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw="x", argument=2),
        lambda: PartitionTransform(kind=PartitionTransformKind.DAY, raw="day"),
        lambda: PartitionTransform(kind="day"),  # ty: ignore[invalid-argument-type]
    ],
)
def test_a_transform_that_cannot_be_written_is_refused(build):
    """Bucket and truncate need a positive number, no other kind takes one, and only unknown keeps its text."""
    with pytest.raises(InvariantViolation):
        build()


def test_equal_by_value():
    """Two transforms of one kind and number are the same transform; another number is not."""
    assert PartitionTransform(kind=PartitionTransformKind.BUCKET, argument=16) == PartitionTransform(
        kind=PartitionTransformKind.BUCKET, argument=16
    )
    assert PartitionTransform(kind=PartitionTransformKind.BUCKET, argument=16) != PartitionTransform(
        kind=PartitionTransformKind.BUCKET, argument=32
    )
