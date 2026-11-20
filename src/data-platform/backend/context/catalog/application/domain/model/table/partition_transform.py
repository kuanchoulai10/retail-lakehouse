"""Define the PartitionTransform value object."""

from __future__ import annotations

from pydantic import model_validator

from base import ValueObject
from context.catalog.application.domain.model.table.partition_transform_kind import PartitionTransformKind

_NUMBERED = frozenset({PartitionTransformKind.BUCKET, PartitionTransformKind.TRUNCATE})


class PartitionTransform(ValueObject):
    """How a partition field derives its value from its source column.

    ``argument`` is the bucket count of ``bucket`` and the width of ``truncate``, at least 1, and
    None for every other kind. A transform this backend does not know is ``unknown`` and keeps the
    text it was read from in ``raw``, so nothing is lost; ``raw`` is None for every known kind.
    """

    kind: PartitionTransformKind
    argument: int | None = None
    raw: str | None = None

    @model_validator(mode="after")
    def _argument_and_raw_fit_the_kind(self) -> PartitionTransform:
        if self.kind in _NUMBERED:
            if self.argument is None or self.argument < 1:
                raise ValueError(f"a {self.kind} transform needs a number of at least 1, not {self.argument}")
        elif self.argument is not None:
            raise ValueError(f"a {self.kind} transform takes no number")
        if self.kind is PartitionTransformKind.UNKNOWN:
            if not self.raw:
                raise ValueError("an unknown transform keeps the text it was read from")
        elif self.raw is not None:
            raise ValueError(f"a {self.kind} transform keeps no text of its own")
        return self

    def text(self) -> str:
        """Return Iceberg's text form: ``day``, ``bucket[16]``, ``truncate[4]``, or an unknown transform's own text."""
        if self.kind is PartitionTransformKind.UNKNOWN:
            return str(self.raw)
        if self.kind in _NUMBERED:
            return f"{self.kind}[{self.argument}]"
        return str(self.kind)
