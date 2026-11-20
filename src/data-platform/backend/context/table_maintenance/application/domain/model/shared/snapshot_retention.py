"""Define the SnapshotRetention value object."""

from __future__ import annotations

from pydantic import PositiveInt

from base import ValueObject
from context.table_maintenance.application.domain.model.shared.positive_duration import PositiveDuration


class SnapshotRetention(ValueObject):
    """The snapshots a table keeps: at least ``min_snapshots_to_keep``, and every one younger than the age.

    Both values are measured and passed to the procedure, so the check and the run agree.
    """

    min_snapshots_to_keep: PositiveInt
    max_snapshot_age: PositiveDuration
