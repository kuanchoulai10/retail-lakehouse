"""Define the PriorityWeights value object."""

from __future__ import annotations

from pydantic import PositiveFloat

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority


class PriorityWeights(ValueObject):
    """Say how much each priority multiplies a candidate's score when a compaction round ranks candidates.

    Every weight is above zero, so a lower priority waits behind a higher one
    with a similar score but is never left out of the ranking.
    """

    p0: PositiveFloat = 4.0
    p1: PositiveFloat = 2.0
    p2: PositiveFloat = 1.0

    def weight(self, priority: MaintenancePriority) -> float:
        """Return the weight of ``priority``."""
        return {
            MaintenancePriority.P0: self.p0,
            MaintenancePriority.P1: self.p1,
            MaintenancePriority.P2: self.p2,
        }[priority]
