"""Define the score_candidate domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_candidate import CandidateScore

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.compaction_candidate import CandidateScoring


def score_candidate(
    *,
    reducible_files: int,
    data_bytes: int,
    memory_gb: float,
    throughput_bytes_per_hour: float,
    scoring: CandidateScoring,
) -> CandidateScore:
    """Return what compacting a partition is worth and costs, as one score in [0, 1].

    The benefit is the files a compaction could remove; the cost is the estimated
    GB-hours, ``memory_gb * data_bytes / throughput_bytes_per_hour``. Both are
    normalised against the fixed reference bounds of ``scoring``; a higher cost
    lowers the score through the cost term ``1 - normalised cost``.
    """
    if throughput_bytes_per_hour <= 0:
        raise ValueError(f"throughput must be positive, got {throughput_bytes_per_hour}")
    gb_hours = memory_gb * data_bytes / throughput_bytes_per_hour
    benefit = min(1.0, reducible_files / scoring.benefit_reference_files)
    cost = min(1.0, gb_hours / scoring.cost_reference_gb_hours)
    weights = scoring.benefit_weight + scoring.cost_weight
    weighted = (scoring.benefit_weight * benefit + scoring.cost_weight * (1.0 - cost)) / weights
    return CandidateScore(
        reducible_files=reducible_files,
        data_bytes=data_bytes,
        estimated_gb_hours=gb_hours,
        score=min(1.0, max(0.0, weighted)),
    )
