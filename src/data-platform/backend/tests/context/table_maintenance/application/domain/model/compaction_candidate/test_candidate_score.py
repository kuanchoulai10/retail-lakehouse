"""Tests for the CandidateScore value object."""

from __future__ import annotations

from typing import Any

import pytest

from base import InvariantViolation
from context.table_maintenance.application.domain.model.compaction_candidate import CandidateScore


def test_score_holds_its_parts():
    """A score keeps the removable files, the data and the estimated cost it was computed from."""
    score = CandidateScore(reducible_files=5, data_bytes=100, estimated_gb_hours=0.25, score=0.5)
    assert (score.reducible_files, score.data_bytes, score.estimated_gb_hours, score.score) == (5, 100, 0.25, 0.5)


@pytest.mark.parametrize(
    "fields",
    [
        {"reducible_files": -1},
        {"data_bytes": -1},
        {"estimated_gb_hours": -0.1},
        {"score": -0.01},
        {"score": 1.01},
    ],
)
def test_score_rejects_values_out_of_range(fields):
    """Counts and cost are never negative and the score stays in [0, 1]."""
    base: dict[str, Any] = {"reducible_files": 1, "data_bytes": 1, "estimated_gb_hours": 0.0, "score": 0.0}
    with pytest.raises(InvariantViolation):
        CandidateScore(**{**base, **fields})
