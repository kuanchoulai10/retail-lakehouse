"""Define the CandidateSelection value object."""

from __future__ import annotations

from pydantic import Field, NonNegativeInt, PositiveFloat, PositiveInt, model_validator

from base import ValueObject
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_filters import (
    CandidateFilters,
)
from context.table_maintenance.application.domain.model.compaction_candidate.candidate_scoring import (
    CandidateScoring,
)

_GIB = 1024**3
_MIB = 1024**2


class CandidateSelection(ValueObject):
    """Say how a table's compaction candidates are filtered, scored and picked for a run.

    A scheduled run compacts the ``partitions_per_run`` best pending candidates.
    The cost estimate uses the throughput measured from past runs, or
    ``default_throughput_bytes_per_hour`` before there are any; a past
    compaction that rewrote less than ``min_throughput_sample_bytes`` does not
    count, since its time is mostly Spark start-up. A run starts at
    least at the size that fits the data it picked: S up to ``size_s_max_bytes``,
    M up to ``size_m_max_bytes``, L above.
    """

    partitions_per_run: PositiveInt = 10
    scoring: CandidateScoring = Field(default_factory=CandidateScoring)
    filters: CandidateFilters = Field(default_factory=CandidateFilters)
    default_throughput_bytes_per_hour: PositiveFloat = 2.0 * _GIB
    min_throughput_sample_bytes: NonNegativeInt = 64 * _MIB
    size_s_max_bytes: PositiveInt = 256 * _MIB
    size_m_max_bytes: PositiveInt = _GIB

    @model_validator(mode="after")
    def _sizes_grow(self) -> CandidateSelection:
        if self.size_s_max_bytes > self.size_m_max_bytes:
            raise ValueError("the S bound cannot be above the M bound")
        return self
