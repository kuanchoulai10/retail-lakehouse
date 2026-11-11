"""Define the CompactionScope value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.compaction_unit import CompactionUnit


class CompactionScope(ValueObject):
    """Say over which unit a compaction runs."""

    unit: CompactionUnit
