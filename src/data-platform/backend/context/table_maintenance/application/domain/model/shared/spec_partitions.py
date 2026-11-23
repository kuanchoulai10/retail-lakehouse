"""Define the SpecPartitions value object."""

from __future__ import annotations

from pydantic import model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.partition_spec_info import (
    PartitionSpecInfo,
)


class SpecPartitions(ValueObject):
    """Hold the partitions of one partition spec that a compaction rewrites.

    ``values`` holds one tuple per partition, a value per field of ``spec`` in Iceberg's internal form
    (a ``day`` value is days since 1970-01-01, a ``bucket`` value its bucket number). A spec with only
    ``void`` fields filters nothing, so it is never selected: compacting it means the whole table.
    """

    spec: PartitionSpecInfo
    values: tuple[tuple[str | int | float | bool | None, ...], ...]

    @model_validator(mode="after")
    def _partitions_fit_the_spec(self) -> SpecPartitions:
        if self.spec.is_unpartitioned:
            raise ValueError(f"spec {self.spec.spec_id} is unpartitioned, so it selects no partitions")
        if not self.values:
            raise ValueError("a selection holds at least one partition")
        for values in self.values:
            if len(values) != len(self.spec.fields):
                raise ValueError(
                    f"a partition has {len(values)} values but spec {self.spec.spec_id} "
                    f"has {len(self.spec.fields)} fields"
                )
        return self
