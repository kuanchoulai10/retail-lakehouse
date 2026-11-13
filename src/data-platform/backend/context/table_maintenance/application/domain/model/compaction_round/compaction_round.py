"""Define the CompactionRound aggregate root."""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import NonNegativeFloat, NonNegativeInt, model_validator

from base import AggregateRoot
from context.table_maintenance.application.domain.model.compaction_round.compaction_round_id import (
    CompactionRoundId,
)
from context.table_maintenance.application.domain.model.compaction_round.round_pick import RoundPick
from context.table_maintenance.application.domain.model.compaction_round.round_skip import RoundSkip

if TYPE_CHECKING:
    from context.table_maintenance.application.domain.model.table import TableId

_TOLERANCE = 1e-9


class CompactionRound(AggregateRoot[CompactionRoundId]):
    """Record one round of the compaction scheduler: what it granted, what it left and why.

    A round ranks every pending compaction candidate of every table, takes them
    in order within ``budget_gb_hours`` and at most one run's share per table,
    and grants the picks to their tables. ``used_gb_hours`` is what the picks
    are estimated to cost (it can pass the budget only by the first pick, which
    a round always takes). ``skips`` keeps the first skipped candidates and
    ``skipped_total`` counts all of them. ``busy_skipped`` counts apart the
    pending candidates of tables busy with compaction, which a round never
    ranks, so they never crowd the kept skips (a round recorded before they
    were counted apart has 0, and its busy ones are among its skips).
    """

    id: CompactionRoundId
    started_at: datetime
    budget_gb_hours: NonNegativeFloat
    used_gb_hours: NonNegativeFloat
    picks: tuple[RoundPick, ...]
    skips: tuple[RoundSkip, ...]
    skipped_total: NonNegativeInt
    busy_skipped: NonNegativeInt = 0

    @model_validator(mode="after")
    def _totals_agree(self) -> CompactionRound:
        """Reject a skipped total below the skips kept, or a used budget other than the picks' cost."""
        if self.skipped_total < len(self.skips):
            raise ValueError("a round cannot have skipped fewer candidates than the skips it keeps")
        cost = math.fsum(p.estimated_gb_hours for p in self.picks)
        if abs(cost - self.used_gb_hours) > _TOLERANCE * max(1.0, cost):
            raise ValueError(f"a round's used budget {self.used_gb_hours} is not its picks' cost {cost}")
        return self

    def granted_tables(self) -> tuple[TableId, ...]:
        """Return each table the round granted a partition to, once, in the order of its first pick."""
        return tuple(dict.fromkeys(p.table_uuid for p in self.picks))
