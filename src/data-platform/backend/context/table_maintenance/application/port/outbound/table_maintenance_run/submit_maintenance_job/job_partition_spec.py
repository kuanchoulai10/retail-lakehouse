"""Define the JobPartitionSpec."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context.table_maintenance.application.port.outbound.table_maintenance_run.submit_maintenance_job.job_partition_field import (  # noqa: E501
        JobPartitionField,
    )


@dataclass(frozen=True)
class JobPartitionSpec:
    """Hold the partitions of one partition spec a compaction rewrites.

    ``values`` holds one tuple per partition, one value per field, in Iceberg's internal form
    (``day`` as days since 1970-01-01, ``bucket`` as the bucket number).
    """

    spec_id: int
    fields: tuple[JobPartitionField, ...]
    values: tuple[tuple[str | int | float | bool | None, ...], ...]
