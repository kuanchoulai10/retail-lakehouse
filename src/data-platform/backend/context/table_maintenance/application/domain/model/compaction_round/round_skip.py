"""Define the RoundSkip value object."""

from __future__ import annotations

from pydantic import NonNegativeFloat

from base import ValueObject
from context.table_maintenance.application.domain.model.compaction_candidate import PartitionKey
from context.table_maintenance.application.domain.model.compaction_round.skip_reason import SkipReason
from context.table_maintenance.application.domain.model.table import TableId
from context.table_maintenance.application.domain.model.table_maintenance_policy import MaintenancePriority


class RoundSkip(ValueObject):
    """Say which pending partition a compaction round left for a later round, what it weighed and why.

    ``weighted_score`` is ``score`` times the weight of ``priority``, the key the
    round ranked by; ``estimated_gb_hours`` is what compacting it is estimated to
    cost; ``overdue`` says it had waited longer than its priority's SLA.
    """

    table_uuid: TableId
    partition: PartitionKey
    label: str
    priority: MaintenancePriority
    score: NonNegativeFloat
    weighted_score: NonNegativeFloat
    estimated_gb_hours: NonNegativeFloat
    overdue: bool
    reason: SkipReason
