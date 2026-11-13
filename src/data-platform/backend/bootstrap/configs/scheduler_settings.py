"""Define the SchedulerSettings configuration model."""

from __future__ import annotations

from pydantic import BaseModel, Field

from bootstrap.configs.priority_sla_settings import PrioritySlaSettings
from bootstrap.configs.priority_weight_settings import PriorityWeightSettings


class SchedulerSettings(BaseModel):
    """How the compaction scheduler shares compaction across tables.

    Every ``round_seconds`` a round ranks the pending candidates of every table
    by score times their priority's weight (``priority_weights``) and grants the
    best ones while their estimated GB·hours fit ``budget_gb_hours``. A grant
    lasts ``grant_lease_seconds`` for the table to claim it for a run. A
    candidate waiting longer than its priority's ``sla_seconds`` is shown
    overdue. The newest ``rounds_kept`` rounds are kept for reading.
    """

    round_seconds: int = 120
    budget_gb_hours: float = 0.05
    priority_weights: PriorityWeightSettings = Field(default_factory=PriorityWeightSettings)
    sla_seconds: PrioritySlaSettings = Field(default_factory=PrioritySlaSettings)
    grant_lease_seconds: int = 600
    rounds_kept: int = 500
