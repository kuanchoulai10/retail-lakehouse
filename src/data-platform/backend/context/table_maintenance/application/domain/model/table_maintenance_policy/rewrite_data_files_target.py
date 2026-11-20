"""Define the RewriteDataFilesTarget value object."""

from __future__ import annotations

from base import ValueObject
from context.table_maintenance.application.domain.model.table_maintenance_policy.at_most import AtMost
from context.table_maintenance.application.domain.model.table_maintenance_policy.compaction_unit import (
    CompactionUnit,
)


class RewriteDataFilesTarget(ValueObject):
    """The compaction target: reducible files stay at or under ``reducible_files``, per partition or per table."""

    reducible_files: AtMost
    per: CompactionUnit = CompactionUnit.PARTITION
