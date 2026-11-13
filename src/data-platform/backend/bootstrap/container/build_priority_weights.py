"""Provide the build_priority_weights function."""

from __future__ import annotations

from typing import TYPE_CHECKING

from context.table_maintenance.application.domain.model.compaction_round import PriorityWeights

if TYPE_CHECKING:
    from bootstrap.configs import SchedulerSettings


def build_priority_weights(settings: SchedulerSettings) -> PriorityWeights:
    """Return the weights a compaction round multiplies scores by, as the settings say.

    A weight the domain refuses (zero or below) fails here, when the component
    starts, not on the first round.
    """
    weights = settings.priority_weights
    return PriorityWeights(p0=weights.p0, p1=weights.p1, p2=weights.p2)
