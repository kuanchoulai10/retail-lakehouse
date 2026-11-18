"""Tests for the score_candidate domain service."""

from __future__ import annotations

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.compaction_candidate import CandidateScoring
from context.table_maintenance.application.domain.service.compaction_candidate import score_candidate

GIB = 1024**3
SCORING = CandidateScoring()


def test_score_weights_benefit_and_cost():
    """50 of 100 reference files and 0.5 of 1.0 reference GB-hours weigh 0.7 x 0.5 + 0.3 x 0.5."""
    score = score_candidate(
        reducible_files=50, data_bytes=GIB, memory_gb=1.0, throughput_bytes_per_hour=2 * GIB, scoring=SCORING
    )
    assert score.reducible_files == 50
    assert score.data_bytes == GIB
    assert score.estimated_gb_hours == pytest.approx(0.5)
    assert score.score == pytest.approx(0.5)


def test_cost_above_reference_scores_zero_cost_term():
    """A cost past the reference bound leaves only the benefit."""
    score = score_candidate(
        reducible_files=100, data_bytes=10 * GIB, memory_gb=1.5, throughput_bytes_per_hour=GIB, scoring=SCORING
    )
    assert score.estimated_gb_hours == pytest.approx(15.0)
    assert score.score == pytest.approx(0.7)


def test_benefit_above_reference_counts_as_full_benefit():
    """More removable files than the reference count as the full benefit, so the score stays at most 1."""
    score = score_candidate(
        reducible_files=10_000, data_bytes=0, memory_gb=1.5, throughput_bytes_per_hour=GIB, scoring=SCORING
    )
    assert score.score == pytest.approx(1.0)


def test_higher_cost_lowers_the_score():
    """Of two partitions with the same benefit, the one costing more scores lower."""
    cheap, dear = (
        score_candidate(
            reducible_files=20, data_bytes=size, memory_gb=1.5, throughput_bytes_per_hour=2 * GIB, scoring=SCORING
        )
        for size in (GIB // 10, GIB)
    )
    assert cheap.score > dear.score


def test_score_is_the_same_for_the_same_partition_on_any_table():
    """The score uses fixed reference bounds, not the spread of one table's partitions."""
    alone = score_candidate(
        reducible_files=30, data_bytes=GIB, memory_gb=1.5, throughput_bytes_per_hour=2 * GIB, scoring=SCORING
    )
    among_others = [
        score_candidate(
            reducible_files=r, data_bytes=b, memory_gb=1.5, throughput_bytes_per_hour=2 * GIB, scoring=SCORING
        )
        for r, b in ((1, 1), (30, GIB), (500, 50 * GIB))
    ][1]
    assert alone == among_others


def test_weights_need_not_sum_to_one():
    """Weights are relative: doubling both leaves the score unchanged."""
    doubled = CandidateScoring(benefit_weight=1.4, cost_weight=0.6)
    one = score_candidate(
        reducible_files=50, data_bytes=GIB, memory_gb=1.0, throughput_bytes_per_hour=2 * GIB, scoring=SCORING
    )
    two = score_candidate(
        reducible_files=50, data_bytes=GIB, memory_gb=1.0, throughput_bytes_per_hour=2 * GIB, scoring=doubled
    )
    assert two.score == pytest.approx(one.score)


@pytest.mark.parametrize(
    "fields",
    [
        {"benefit_weight": -0.1},
        {"benefit_weight": 0.0, "cost_weight": 0.0},
        {"benefit_reference_files": 0},
        {"cost_reference_gb_hours": 0.0},
    ],
)
def test_scoring_rejects_meaningless_settings(fields):
    """Weights are not negative and not both zero; reference bounds are positive."""
    with pytest.raises(InvariantViolation):
        CandidateScoring(**fields)


def test_throughput_must_be_positive():
    """A throughput of zero would make every cost infinite."""
    with pytest.raises(ValueError, match="throughput"):
        score_candidate(reducible_files=1, data_bytes=1, memory_gb=1.0, throughput_bytes_per_hour=0, scoring=SCORING)
