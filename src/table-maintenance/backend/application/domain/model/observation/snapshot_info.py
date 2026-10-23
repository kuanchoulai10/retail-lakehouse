"""Define the SnapshotInfo value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from base.value_object import ValueObject


@dataclass(frozen=True)
class SnapshotInfo(ValueObject):
    """Identify one snapshot and when it was committed."""

    snapshot_id: int
    committed_at: datetime
