"""Define the CompactionSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel


class CompactionSettings(BaseModel):
    """How a scheduled compaction filters, scores and picks a table's partitions.

    A run compacts the ``partitions_per_run`` best pending partitions. A partition
    with less data than ``min_partition_bytes`` is held as too small; one written
    within ``quiet_seconds`` is held as still being written, but never longer than
    ``max_quiet_wait_seconds`` in a row. The score weighs the files a compaction
    removes (``benefit_reference_files`` scores 1) against its estimated GB-hours
    (``cost_reference_gb_hours`` scores 1). Costs use the throughput of past runs,
    or ``default_throughput_bytes_per_hour`` before there are any; a past
    compaction that rewrote less than ``min_throughput_sample_bytes`` does not
    count, since Spark start-up dominates its time. A run starts at
    least at S up to ``size_s_max_bytes`` of picked data, M up to
    ``size_m_max_bytes``, L above.
    """

    partitions_per_run: int = 10
    min_partition_bytes: int = 0
    quiet_seconds: int = 120
    max_quiet_wait_seconds: int = 3600
    benefit_weight: float = 0.7
    cost_weight: float = 0.3
    benefit_reference_files: int = 100
    cost_reference_gb_hours: float = 1.0
    default_throughput_bytes_per_hour: int = 2 * 1024**3
    min_throughput_sample_bytes: int = 64 * 1024**2
    size_s_max_bytes: int = 256 * 1024**2
    size_m_max_bytes: int = 1024**3
