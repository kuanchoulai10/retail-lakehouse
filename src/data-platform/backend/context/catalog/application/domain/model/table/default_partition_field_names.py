"""Define the DefaultPartitionFieldNames policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.catalog.application.domain.model.table.partition_transform_kind import PartitionTransformKind

if TYPE_CHECKING:
    from context.catalog.application.domain.model.table.partition_transform import PartitionTransform

_UNIT_SUFFIX = {
    PartitionTransformKind.YEAR: "_year",
    PartitionTransformKind.MONTH: "_month",
    PartitionTransformKind.DAY: "_day",
    PartitionTransformKind.HOUR: "_hour",
}
_NUMBERED_SUFFIX = {PartitionTransformKind.BUCKET: "_bucket", PartitionTransformKind.TRUNCATE: "_trunc"}


class DefaultPartitionFieldNames:
    """The names Iceberg's writers give a partition field when the user names none.

    The Iceberg table format itself defines no names; these are what its Java and Python writers
    do. The name starts with the source column's name, a nested column's full path joined by dots.
    An identity field takes that name alone. A year, month, day or hour field appends ``_year``,
    ``_month``, ``_day`` or ``_hour``. A bucket field appends ``_bucket`` and a truncate field
    ``_trunc``: the Java writer stops there for a field created with the table, while a field
    added to an existing table, and every field the Python writer names, also carries its number
    (``_bucket_16``, ``_trunc_4``). Both forms count. A void or unknown transform, and a source
    column no schema holds, have no default name.
    """

    def is_default(self, name: str, transform: PartitionTransform, source_path: tuple[str, ...] | None) -> bool:
        """Tell whether ``name`` is a default name for ``transform`` on the column at ``source_path``."""
        if source_path is None:
            return False
        return name in self._names(transform, ".".join(source_path))

    @staticmethod
    def _names(transform: PartitionTransform, source: str) -> frozenset[str]:
        if transform.kind is PartitionTransformKind.IDENTITY:
            return frozenset({source})
        if transform.kind in _UNIT_SUFFIX:
            return frozenset({f"{source}{_UNIT_SUFFIX[transform.kind]}"})
        if transform.kind in _NUMBERED_SUFFIX:
            suffix = _NUMBERED_SUFFIX[transform.kind]
            return frozenset({f"{source}{suffix}", f"{source}{suffix}_{transform.argument}"})
        return frozenset()
