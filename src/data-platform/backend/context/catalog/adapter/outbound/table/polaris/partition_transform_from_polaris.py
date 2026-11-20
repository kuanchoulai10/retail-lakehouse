"""Define the partition_transform_from_polaris function."""

from __future__ import annotations

import re

from context.catalog.application.port.outbound.table import PartitionTransform, PartitionTransformKind

_NUMBERED = re.compile(r"^(bucket|truncate)\[([1-9]\d*)\]$")
_PLAIN = {
    kind.value: kind
    for kind in (
        PartitionTransformKind.IDENTITY,
        PartitionTransformKind.YEAR,
        PartitionTransformKind.MONTH,
        PartitionTransformKind.DAY,
        PartitionTransformKind.HOUR,
        PartitionTransformKind.VOID,
    )
}


def partition_transform_from_polaris(text: str) -> PartitionTransform:
    """Read an Iceberg REST transform string (``day``, ``bucket[16]``, ``truncate[4]``) as a PartitionTransform.

    Any other text, a transform this backend does not know, reads as ``unknown`` with its text
    kept, so writing it back sends Polaris what it sent.
    """
    if text in _PLAIN:
        return PartitionTransform(kind=_PLAIN[text])
    numbered = _NUMBERED.match(text)
    if numbered is not None:
        return PartitionTransform(kind=PartitionTransformKind(numbered[1]), argument=int(numbered[2]))
    return PartitionTransform(kind=PartitionTransformKind.UNKNOWN, raw=text)
